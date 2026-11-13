import asyncio
from collections.abc import AsyncIterator
from contextlib import aclosing

from dema.api.merge import merge


async def letters(*items: str, delay: float = 0.0) -> AsyncIterator[str]:
    for item in items:
        await asyncio.sleep(delay)
        yield item


async def forever() -> AsyncIterator[str]:
    while True:
        await asyncio.sleep(0.001)
        yield "tick"


async def test_yields_items_from_every_source() -> None:
    events = merge(letters("a", "b"), letters("x", delay=0.01))
    async with aclosing(events):
        received = [await anext(events) for _ in range(3)]

    assert sorted(received) == ["a", "b", "x"]


async def test_stops_the_sources_when_closed() -> None:
    events = merge(forever())
    async with aclosing(events):
        assert await anext(events) == "tick"

    await asyncio.sleep(0.01)
    assert [task for task in asyncio.all_tasks() if not task.done()] == [
        asyncio.current_task()
    ]
