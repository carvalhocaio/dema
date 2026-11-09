import asyncio

import pytest

from dema.api.broadcaster import Broadcaster


class Counter:
    def __init__(self, *values: int) -> None:
        self.values = list(values)

    async def __call__(self) -> int:
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


async def test_keeps_latest_loaded_value() -> None:
    broadcaster = Broadcaster(Counter(1, 2), interval=0)

    await broadcaster.refresh()
    await broadcaster.refresh()

    assert broadcaster.latest == 2


async def test_new_subscriber_receives_latest_value_first() -> None:
    broadcaster = Broadcaster(Counter(7), interval=0)
    await broadcaster.refresh()

    subscription = broadcaster.subscribe()

    assert await anext(subscription) == 7
    await subscription.aclose()


async def test_slow_subscriber_skips_stale_values() -> None:
    broadcaster = Broadcaster(Counter(1, 2, 3), interval=0)
    subscription = broadcaster.subscribe()
    pending = asyncio.ensure_future(anext(subscription))
    await asyncio.sleep(0)

    for _ in range(3):
        await broadcaster.refresh()

    assert await pending == 3
    await subscription.aclose()


async def test_skips_unchanged_values() -> None:
    broadcaster = Broadcaster(Counter(5, 5), interval=0)
    subscription = broadcaster.subscribe()
    pending = asyncio.ensure_future(anext(subscription))
    await asyncio.sleep(0)

    await broadcaster.refresh()
    await broadcaster.refresh()

    assert await pending == 5
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(anext(subscription), timeout=0.05)
    await subscription.aclose()


async def test_forgets_closed_subscribers() -> None:
    broadcaster = Broadcaster(Counter(1), interval=0)
    await broadcaster.refresh()
    subscription = broadcaster.subscribe()
    await anext(subscription)

    await subscription.aclose()

    assert broadcaster.subscribers == 0


async def test_survives_ignored_and_unexpected_errors() -> None:
    attempts: list[int] = []

    async def flaky() -> int:
        attempts.append(1)
        if len(attempts) == 1:
            raise LookupError("not ready")
        if len(attempts) == 2:
            raise RuntimeError("boom")
        return 42

    broadcaster = Broadcaster(flaky, interval=0, ignored_errors=(LookupError,))

    for _ in range(3):
        await broadcaster.refresh()

    assert broadcaster.latest == 42
