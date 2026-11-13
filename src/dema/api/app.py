import asyncio
import secrets
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack, aclosing, asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent
from redis.asyncio import Redis

from dema.api.broadcaster import Broadcaster
from dema.api.merge import merge
from dema.api.schemas import (
    BallotAuditView,
    CurrentRunView,
    PipelineView,
    RejectionView,
    ReplayView,
    ResultsView,
    RoundStatus,
    RoundView,
    RunRequest,
    RunView,
    StatesView,
    TamperView,
    TimelineView,
)
from dema.api.sources import (
    ActiveRound,
    Archive,
    AuditSource,
    PipelineSource,
    PostgresArchive,
    SnapshotFactory,
    active_record,
)
from dema.audit.ballots import BallotAudit, NothingToTamperError
from dema.config import Settings, get_settings
from dema.domain.election import ElectionNotSetUpError, ElectionRound
from dema.domain.section import SectionKey
from dema.integrity.signer import BallotSigner
from dema.monitoring.pipeline import PipelineCollector
from dema.storage.elections import ElectionRecord
from dema.tallying.outcome import decide
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import build_signer, open_database, open_redis

NOT_READY = "election is not set up yet"
NOT_FOUND = "round {round} is not set up"
NOT_LIVE = "round {round} is not being counted"
RUNS_DISABLED = "new counts are disabled; set DEMA_ALLOW_RUNS=true"
TAMPER_DISABLED = "tampering is disabled; set DEMA_ALLOW_RUNS=true"
INVALID_SECTION = "section keys look like UF-municipality-zone-section"
NOT_COUNTED = "section {key} has not been counted in round {round}"
NONE_COUNTED = "no section has been counted in round {round} yet"
NOTHING_TO_TAMPER = "tampering needs a counted section and one still to count"
NO_AUDIT = "ballot audit needs the database"
GZIP_MINIMUM_SIZE = 1024
DRAWN_SEEDS = 1_000_000


@dataclass(frozen=True, slots=True)
class Context:
    settings: Settings
    archive: Archive
    broadcaster: Broadcaster[ResultsView]
    pipeline: Broadcaster[PipelineView]
    audit: AuditSource | None

    def auditor(self) -> AuditSource:
        if self.audit is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_AUDIT)
        return self.audit

    async def family(self) -> tuple[ElectionRecord, ...]:
        try:
            return await self.archive.family()
        except ElectionNotSetUpError:
            return ()

    async def round(self, round_: ElectionRound) -> tuple[ElectionRecord, bool]:
        family = await self.family()
        for record in family:
            if record.election.round is round_:
                return record, record is family[-1]
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, NOT_FOUND.format(round=int(round_))
        )


def create_app(
    settings: Settings | None = None,
    archive: Archive | None = None,
    snapshots: SnapshotFactory | None = None,
    pipeline: PipelineSource | None = None,
    audit: AuditSource | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            redis = await stack.enter_async_context(open_redis(settings))
            if archive is None:
                connection = await stack.enter_async_context(open_database(settings))
                resolved: Archive = PostgresArchive(connection, redis, settings.year)
                audit_source = audit or BallotAudit(
                    connection, redis, _optional_signer(settings)
                )
            else:
                resolved, audit_source = archive, audit
            active = ActiveRound(resolved, snapshots or _redis_snapshots(redis))
            broadcaster = Broadcaster(
                active.results,
                interval=settings.broadcast_interval,
                ignored_errors=(ElectionNotSetUpError,),
            )
            collector = pipeline or PipelineCollector(
                redis, lambda: active_record(resolved)
            )
            metrics = Broadcaster(
                _pipeline_view(collector),
                interval=settings.pipeline_interval,
                ignored_errors=(ElectionNotSetUpError,),
                only_when_subscribed=True,
            )
            await broadcaster.refresh()
            tasks = [
                asyncio.create_task(broadcaster.run()),
                asyncio.create_task(metrics.run()),
            ]
            app.state.context = Context(
                settings, resolved, broadcaster, metrics, audit_source
            )
            yield
            for task in tasks:
                task.cancel()
            with suppress(asyncio.CancelledError):
                await asyncio.gather(*tasks)

    app = FastAPI(title="dema", lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_SIZE)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"] if settings.allow_runs else ["GET"],
        allow_headers=["*"],
    )
    app.add_api_route("/health", health, methods=["GET"])
    app.add_api_route("/runs/current", current_run, methods=["GET"])
    app.add_api_route("/pipeline", pipeline_metrics, methods=["GET"])
    app.add_api_route(
        "/runs", create_run, methods=["POST"], status_code=status.HTTP_202_ACCEPTED
    )
    app.add_api_route("/rounds", rounds, methods=["GET"])
    app.add_api_route("/rounds/{round_}/results", round_results, methods=["GET"])
    app.add_api_route(
        "/rounds/{round_}/stream",
        round_stream,
        methods=["GET"],
        response_class=EventSourceResponse,
    )
    app.add_api_route("/rounds/{round_}/timeline", round_timeline, methods=["GET"])
    app.add_api_route("/rounds/{round_}/replay", round_replay, methods=["GET"])
    app.add_api_route("/rounds/{round_}/states", round_states, methods=["GET"])
    app.add_api_route(
        "/rounds/{round_}/sections/random", random_section, methods=["GET"]
    )
    app.add_api_route("/rounds/{round_}/sections/{key}", section, methods=["GET"])
    app.add_api_route("/rounds/{round_}/rejected", rejected, methods=["GET"])
    app.add_api_route(
        "/rounds/{round_}/tamper",
        tamper,
        methods=["POST"],
        status_code=status.HTTP_202_ACCEPTED,
    )
    return app


def _optional_signer(settings: Settings) -> BallotSigner | None:
    return None if settings.signing_key is None else build_signer(settings)


def _pipeline_view(source: PipelineSource) -> Callable[[], Awaitable[PipelineView]]:
    async def load() -> PipelineView:
        return PipelineView.of(await source.collect())

    return load


def _redis_snapshots(redis: Redis) -> SnapshotFactory:
    def snapshots(record: ElectionRecord) -> RedisTallyStore:
        return RedisTallyStore(redis, record.keys, record.election)

    return snapshots


def get_context(request: Request) -> Context:
    return request.app.state.context


ContextDependency = Annotated[Context, Depends(get_context)]


async def health() -> dict[str, str]:
    return {"status": "ok"}


async def current_run(context: ContextDependency) -> CurrentRunView:
    run = await context.archive.current_run()
    return CurrentRunView(
        run=None if run is None else RunView.of(run),
        runs_enabled=context.settings.allow_runs,
    )


async def create_run(
    context: ContextDependency, request: RunRequest | None = None
) -> RunView:
    if not context.settings.allow_runs:
        raise HTTPException(status.HTTP_403_FORBIDDEN, RUNS_DISABLED)
    request = request or RunRequest()
    seed = secrets.randbelow(DRAWN_SEEDS) if request.seed is None else request.seed
    try:
        run = await context.archive.request_run(seed, request.speed)
    except ElectionNotSetUpError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_READY) from error
    return RunView.of(run)


async def pipeline_metrics(context: ContextDependency) -> PipelineView:
    await context.pipeline.refresh()
    if context.pipeline.latest is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_READY)
    return context.pipeline.latest


async def rounds(context: ContextDependency) -> list[RoundView]:
    family = await context.family()
    return [
        RoundView(
            round=record.election.round,
            status=RoundStatus.LIVE if record is family[-1] else RoundStatus.FINAL,
        )
        for record in family
    ]


async def round_results(
    round_: ElectionRound, context: ContextDependency
) -> ResultsView:
    record, live = await context.round(round_)
    if live:
        await context.broadcaster.refresh()
        if context.broadcaster.latest is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_READY)
        return context.broadcaster.latest
    election = record.election
    tally = await context.archive.tally(record)
    return ResultsView.build(election, tally, decide(election, tally), record.run)


async def live_context(round_: ElectionRound, context: ContextDependency) -> Context:
    family = await context.family()
    if not family or family[-1].election.round is not round_:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, NOT_LIVE.format(round=int(round_))
        )
    return context


async def round_stream(
    round_: ElectionRound,
    context: Annotated[Context, Depends(live_context)],
) -> AsyncIterator[ServerSentEvent]:
    run_id: int | None = None
    events: AsyncGenerator[ResultsView | PipelineView] = merge(
        context.broadcaster.subscribe(), context.pipeline.subscribe()
    )
    async with aclosing(events):
        async for view in events:
            if isinstance(view, PipelineView):
                yield ServerSentEvent(data=view, event="pipeline")
                continue
            if view.run is not None and view.run.id != run_id:
                if run_id is not None:
                    yield ServerSentEvent(data=view.run, event="run")
                run_id = view.run.id
            if view.round != round_:
                return
            yield ServerSentEvent(
                data=view, event="results", id=str(view.progress.counted_sections)
            )


async def round_timeline(
    round_: ElectionRound, context: ContextDependency
) -> TimelineView:
    record, _ = await context.round(round_)
    return TimelineView.build(record.election, await context.archive.timeline(record))


async def round_replay(round_: ElectionRound, context: ContextDependency) -> ReplayView:
    record, _ = await context.round(round_)
    return ReplayView.build(record.election, await context.archive.timeline(record))


async def round_states(round_: ElectionRound, context: ContextDependency) -> StatesView:
    record, _ = await context.round(round_)
    return StatesView.build(record.election, await context.archive.states(record))


async def section(
    round_: ElectionRound, key: str, context: ContextDependency
) -> BallotAuditView:
    record, _ = await context.round(round_)
    try:
        parsed = SectionKey.parse(key)
    except ValueError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, INVALID_SECTION
        ) from error
    audited = await context.auditor().section(record, parsed)
    if audited is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            NOT_COUNTED.format(key=parsed, round=int(round_)),
        )
    return BallotAuditView.of(record.election, audited)


async def random_section(
    round_: ElectionRound, context: ContextDependency
) -> BallotAuditView:
    record, _ = await context.round(round_)
    audited = await context.auditor().random_section(record)
    if audited is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, NONE_COUNTED.format(round=int(round_))
        )
    return BallotAuditView.of(record.election, audited)


async def rejected(
    round_: ElectionRound, context: ContextDependency
) -> list[RejectionView]:
    record, _ = await context.round(round_)
    return [RejectionView.of(item) for item in await context.auditor().rejected(record)]


async def tamper(round_: ElectionRound, context: ContextDependency) -> TamperView:
    if not context.settings.allow_runs:
        raise HTTPException(status.HTTP_403_FORBIDDEN, TAMPER_DISABLED)
    record, live = await context.round(round_)
    if not live:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, NOT_LIVE.format(round=int(round_))
        )
    try:
        tampered = await context.auditor().tamper(record)
    except NothingToTamperError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, NOTHING_TO_TAMPER) from error
    return TamperView(section=tampered.section, source=tampered.source)
