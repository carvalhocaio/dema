import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager, suppress
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.sse import EventSourceResponse, ServerSentEvent

from dema.api.broadcaster import Broadcaster
from dema.api.schemas import ResultsView
from dema.config import Settings, get_settings
from dema.tallying.outcome import decide
from dema.tallying.redis_store import ElectionNotSetUpError, RedisTallyStore
from dema.tallying.tally import Tally
from dema.wiring import ACTIVE_KEYS, ACTIVE_SCENARIO, open_redis

ELECTION = ACTIVE_SCENARIO.election
NOT_READY = "election is not set up yet"


class SnapshotSource(Protocol):
    async def snapshot(self) -> Tally: ...


def create_app(
    source: SnapshotSource | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            store = source or await _redis_store(stack, settings)

            async def load() -> ResultsView:
                tally = await store.snapshot()
                return ResultsView.build(ELECTION, tally, decide(ELECTION, tally))

            broadcaster = Broadcaster(
                load,
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


async def _redis_store(stack: AsyncExitStack, settings: Settings) -> RedisTallyStore:
    redis = await stack.enter_async_context(open_redis(settings))
    return RedisTallyStore(redis, ACTIVE_KEYS, ELECTION)


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
