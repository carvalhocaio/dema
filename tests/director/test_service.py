import asyncio
import logging

import pytest

from dema.director.control import CountRequest
from dema.director.service import Director


class QueueCommands:
    def __init__(self, *requests: CountRequest | None) -> None:
        self.requests = list(requests)
        self.groups = 0
        self.stop: asyncio.Event | None = None

    async def ensure_group(self) -> None:
        self.groups += 1

    async def next(self, consumer: str, block_ms: int) -> CountRequest | None:
        await asyncio.sleep(0)
        if not self.requests:
            assert self.stop is not None
            self.stop.set()
            return None
        return self.requests.pop(0)


class RecordingCounter:
    def __init__(self, block: bool = False, fail: bool = False) -> None:
        self.started: list[int] = []
        self.finished: list[int] = []
        self.abandoned = 0
        self._block = block
        self._fail = fail

    async def count(self, request: CountRequest) -> None:
        self.started.append(request.run_id)
        if self._fail:
            raise RuntimeError("redis went away")
        if self._block:
            await asyncio.Event().wait()
        self.finished.append(request.run_id)

    async def abandon(self) -> None:
        self.abandoned += 1


async def run_director(commands: QueueCommands, counter: RecordingCounter) -> Director:
    director = Director(commands, counter, block_ms=1)
    commands.stop = asyncio.Event()
    await director.run(commands.stop)
    return director


async def test_counts_each_request_and_supersedes_the_one_in_progress() -> None:
    commands = QueueCommands(CountRequest(1), None, CountRequest(2))
    counter = RecordingCounter(block=True)

    await run_director(commands, counter)

    assert commands.groups == 1
    assert counter.started == [1, 2]
    assert counter.finished == []
    assert counter.abandoned == 2


async def test_lets_a_finished_count_be_without_abandoning_it() -> None:
    counter = RecordingCounter()
    director = Director(QueueCommands(), counter)

    await director.start(CountRequest(5))
    await director.wait()
    await director.start(CountRequest(6))
    await director.wait()

    assert counter.finished == [5, 6]
    assert counter.abandoned == 0


async def test_waiting_without_a_count_returns_at_once() -> None:
    await Director(QueueCommands(), RecordingCounter()).wait()


async def test_logs_counts_that_fail(caplog: pytest.LogCaptureFixture) -> None:
    director = Director(QueueCommands(), RecordingCounter(fail=True))

    with caplog.at_level(logging.ERROR):
        await director.start(CountRequest(9))
        await director.wait()

    assert "run 9 failed" in caplog.text
