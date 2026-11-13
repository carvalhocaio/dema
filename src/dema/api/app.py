import asyncio
import secrets
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent
from redis.asyncio import Redis

from dema.api.broadcaster import Broadcaster
from dema.api.schemas import (
    CurrentRunView,
    ReplayView,
    ResultsView,
    RoundStatus,
    RoundView,
    RunRequest,
    RunView,
    StatesView,
    TimelineView,
)
from dema.api.sources import ActiveRound, Archive, PostgresArchive, SnapshotFactory
from dema.config import Settings, get_settings
from dema.domain.election import ElectionNotSetUpError, ElectionRound
from dema.storage.elections import ElectionRecord
from dema.tallying.outcome import decide
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import open_database, open_redis

NOT_READY = "election is not set up yet"
NOT_FOUND = "round {round} is not set up"
NOT_LIVE = "round {round} is not being counted"
RUNS_DISABLED = "new counts are disabled; set DEMA_ALLOW_RUNS=true"
GZIP_MINIMUM_SIZE = 1024
DRAWN_SEEDS = 1_000_000


@dataclass(frozen=True, slots=True)
class Context:
    settings: Settings
    archive: Archive
    broadcaster: Broadcaster[ResultsView]

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
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            redis = await stack.enter_async_context(open_redis(settings))
            resolved = archive or await _postgres_archive(stack, settings, redis)
            active = ActiveRound(resolved, snapshots or _redis_snapshots(redis))
            broadcaster = Broadcaster(
                active.results,
                interval=settings.broadcast_interval,
                ignored_errors=(ElectionNotSetUpError,),
            )
            await broadcaster.refresh()
            task = asyncio.create_task(broadcaster.run())
            app.state.context = Context(settings, resolved, broadcaster)
            yield
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

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
    return app


async def _postgres_archive(
    stack: AsyncExitStack, settings: Settings, redis: Redis
) -> Archive:
    connection = await stack.enter_async_context(open_database(settings))
    return PostgresArchive(connection, redis, settings.year)


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
    async for view in context.broadcaster.subscribe():
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
