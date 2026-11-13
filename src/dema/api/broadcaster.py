import asyncio
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable

logger = logging.getLogger(__name__)


class Broadcaster[T]:
    def __init__(
        self,
        load: Callable[[], Awaitable[T]],
        interval: float,
        ignored_errors: tuple[type[Exception], ...] = (),
        only_when_subscribed: bool = False,
    ) -> None:
        self._load = load
        self._only_when_subscribed = only_when_subscribed
        self._interval = interval
        self._ignored_errors = ignored_errors
        self._latest: T | None = None
        self._subscribers: set[asyncio.Queue[T]] = set()

    @property
    def latest(self) -> T | None:
        return self._latest

    @property
    def subscribers(self) -> int:
        return len(self._subscribers)

    async def run(self) -> None:
        while True:
            if self._subscribers or not self._only_when_subscribed:
                await self.refresh()
            await asyncio.sleep(self._interval)

    async def refresh(self) -> None:
        try:
            value = await self._load()
        except self._ignored_errors:
            return
        except Exception:
            logger.exception("failed to load broadcast value")
            return
        if value != self._latest:
            self._latest = value
            for queue in self._subscribers:
                _replace(queue, value)

    async def subscribe(self) -> AsyncGenerator[T]:
        queue: asyncio.Queue[T] = asyncio.Queue(maxsize=1)
        if self._latest is not None:
            queue.put_nowait(self._latest)
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)


def _replace[T](queue: asyncio.Queue[T], value: T) -> None:
    if queue.full():
        queue.get_nowait()
    queue.put_nowait(value)
