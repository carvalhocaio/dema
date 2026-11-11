import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent

from dema.api.broadcaster import Broadcaster
from dema.api.schemas import (
    ReplayView,
    ResultsView,
    RoundStatus,
    RoundView,
    StatesView,
    TimelineView,
)
from dema.api.sources import ActiveRound, Archive, PostgresArchive, SnapshotFactory
from dema.config import Settings, get_settings
from dema.domain.election import Election, ElectionNotSetUpError, ElectionRound
from dema.storage.elections import ElectionRecord
from dema.streaming.keys import ElectionKeys
from dema.tallying.outcome import decide
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import open_database, open_redis

NOT_READY = "election is not set up yet"
NOT_FOUND = "round {round} is not set up"
NOT_LIVE = "round {round} is not being counted"
GZIP_MINIMUM_SIZE = 1024


@dataclass(frozen=True, slots=True)
class Context:
    settings: Settings
    archive: Archive
    broadcaster: Broadcaster[ResultsView]

    def is_active(self, round_: ElectionRound) -> bool:
        return round_ is self.settings.round

    async def record(self, round_: ElectionRound) -> ElectionRecord:
        try:
            return await self.archive.load(self.settings.year, round_)
        except ElectionNotSetUpError as error:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, NOT_FOUND.format(round=int(round_))
            ) from error


def create_app(
    settings: Settings | None = None,
    archive: Archive | None = None,
    snapshots: SnapshotFactory | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            resolved = archive or await _postgres_archive(stack, settings)
            active = ActiveRound(
                resolved,
                snapshots or await _redis_snapshots(stack, settings),
                settings.year,
                settings.round,
            )
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
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.add_api_route("/health", health, methods=["GET"])
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


async def _postgres_archive(stack: AsyncExitStack, settings: Settings) -> Archive:
    connection = await stack.enter_async_context(open_database(settings))
    return PostgresArchive(connection)


async def _redis_snapshots(
    stack: AsyncExitStack, settings: Settings
) -> SnapshotFactory:
    redis = await stack.enter_async_context(open_redis(settings))

    def snapshots(election: Election) -> RedisTallyStore:
        return RedisTallyStore(redis, ElectionKeys.for_election(election), election)

    return snapshots


def get_context(request: Request) -> Context:
    return request.app.state.context


ContextDependency = Annotated[Context, Depends(get_context)]


async def health() -> dict[str, str]:
    return {"status": "ok"}


async def rounds(context: ContextDependency) -> list[RoundView]:
    return [
        RoundView(
            round=round_,
            status=RoundStatus.LIVE if context.is_active(round_) else RoundStatus.FINAL,
        )
        for round_ in await context.archive.rounds(context.settings.year)
    ]


async def round_results(
    round_: ElectionRound, context: ContextDependency
) -> ResultsView:
    if context.is_active(round_):
        await context.broadcaster.refresh()
        if context.broadcaster.latest is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_READY)
        return context.broadcaster.latest
    election = (await context.record(round_)).election
    tally = await context.archive.tally(election)
    return ResultsView.build(election, tally, decide(election, tally))


def live_context(round_: ElectionRound, context: ContextDependency) -> Context:
    if not context.is_active(round_):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, NOT_LIVE.format(round=int(round_))
        )
    return context


async def round_stream(
    context: Annotated[Context, Depends(live_context)],
) -> AsyncIterator[ServerSentEvent]:
    async for view in context.broadcaster.subscribe():
        yield ServerSentEvent(
            data=view, event="results", id=str(view.progress.counted_sections)
        )


async def round_timeline(
    round_: ElectionRound, context: ContextDependency
) -> TimelineView:
    election = (await context.record(round_)).election
    return TimelineView.build(election, await context.archive.timeline(election))


async def round_replay(round_: ElectionRound, context: ContextDependency) -> ReplayView:
    election = (await context.record(round_)).election
    return ReplayView.build(election, await context.archive.timeline(election))


async def round_states(round_: ElectionRound, context: ContextDependency) -> StatesView:
    election = (await context.record(round_)).election
    return StatesView.build(election, await context.archive.states(election))
