import asyncio
import logging
from contextlib import suppress
from typing import Protocol

from dema.director.control import CountRequest

logger = logging.getLogger(__name__)


class Commands(Protocol):
    async def ensure_group(self) -> None: ...

    async def next(self, consumer: str, block_ms: int) -> CountRequest | None: ...


class Counter(Protocol):
    async def count(self, request: CountRequest) -> None: ...

    async def abandon(self) -> None: ...


class Director:
    def __init__(
        self,
        commands: Commands,
        counter: Counter,
        consumer: str = "director",
        block_ms: int = 1_000,
    ) -> None:
        self._commands = commands
        self._counter = counter
        self._consumer = consumer
        self._block_ms = block_ms
        self._task: asyncio.Task[None] | None = None

    async def run(self, stop: asyncio.Event) -> None:
        await self._commands.ensure_group()
        try:
            while not stop.is_set():
                request = await self._commands.next(self._consumer, self._block_ms)
                if request is not None:
                    await self.start(request)
        finally:
            await self._cancel()

    async def start(self, request: CountRequest) -> None:
        await self._cancel()
        logger.info("counting run %s", request.run_id)
        self._task = asyncio.create_task(self._count(request))

    async def wait(self) -> None:
        if self._task is not None:
            await self._task

    async def _count(self, request: CountRequest) -> None:
        try:
            await self._counter.count(request)
        except Exception:
            logger.exception("run %s failed", request.run_id)

    async def _cancel(self) -> None:
        task, self._task = self._task, None
        if task is None or task.done():
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await self._counter.abandon()
