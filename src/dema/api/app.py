import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent

from dema.api.active import ActiveRound, ElectionSource, SnapshotFactory
from dema.api.broadcaster import Broadcaster
from dema.api.schemas import ResultsView
from dema.config import Settings, get_settings
from dema.domain.election import Election, ElectionNotSetUpError
from dema.storage.elections import ElectionRepository
from dema.streaming.keys import ElectionKeys
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import open_database, open_redis

NOT_READY = "election is not set up yet"


def create_app(
    settings: Settings | None = None,
    elections: ElectionSource | None = None,
    snapshots: SnapshotFactory | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            active = ActiveRound(
                elections or await _repository(stack, settings),
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
            app.state.broadcaster = broadcaster
            yield
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="dema", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.add_api_route("/health", health, methods=["GET"])
    app.add_api_route("/results", results, methods=["GET"])
    app.add_api_route(
        "/results/stream",
        results_stream,
        methods=["GET"],
        response_class=EventSourceResponse,
    )
    return app


async def _repository(stack: AsyncExitStack, settings: Settings) -> ElectionSource:
    connection = await stack.enter_async_context(open_database(settings))
    return ElectionRepository(connection)


async def _redis_snapshots(
    stack: AsyncExitStack, settings: Settings
) -> SnapshotFactory:
    redis = await stack.enter_async_context(open_redis(settings))

    def snapshots(election: Election) -> RedisTallyStore:
        return RedisTallyStore(redis, ElectionKeys.for_election(election), election)

    return snapshots


def get_broadcaster(request: Request) -> Broadcaster[ResultsView]:
    return request.app.state.broadcaster


BroadcasterDependency = Annotated[Broadcaster[ResultsView], Depends(get_broadcaster)]


async def health() -> dict[str, str]:
    return {"status": "ok"}


async def results(broadcaster: BroadcasterDependency) -> ResultsView:
    await broadcaster.refresh()
    if broadcaster.latest is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_READY)
    return broadcaster.latest


async def results_stream(
    broadcaster: BroadcasterDependency,
) -> AsyncIterator[ServerSentEvent]:
    async for view in broadcaster.subscribe():
        yield ServerSentEvent(
            data=view, event="results", id=str(view.progress.counted_sections)
        )
