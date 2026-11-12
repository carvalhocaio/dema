import pytest
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from dema.director.control import ControlStream, CountRequest
from dema.streaming.keys import CONTROL_STREAM

pytestmark = pytest.mark.integration


@pytest.fixture
async def control(redis_client: Redis) -> ControlStream:
    control = ControlStream(redis_client)
    await control.ensure_group()
    await control.ensure_group()
    return control


async def test_delivers_requests_once_and_in_order(control: ControlStream) -> None:
    await control.request(CountRequest(run_id=3, speed=600))
    await control.request(CountRequest(run_id=4))

    first = await control.next("director", block_ms=10)
    second = await control.next("director", block_ms=10)
    empty = await control.next("director", block_ms=10)

    assert first == CountRequest(run_id=3, speed=600.0)
    assert second == CountRequest(run_id=4, speed=None)
    assert empty is None


async def test_acknowledges_what_it_hands_out(
    control: ControlStream, redis_client: Redis
) -> None:
    await control.request(CountRequest(run_id=3))

    await control.next("director", block_ms=10)

    summary = await redis_client.xpending(CONTROL_STREAM, "director")
    assert summary["pending"] == 0


async def test_group_creation_surfaces_unexpected_errors(redis_client: Redis) -> None:
    await redis_client.set(CONTROL_STREAM, "not a stream")

    with pytest.raises(ResponseError, match="WRONGTYPE"):
        await ControlStream(redis_client).ensure_group()
