import pytest
from redis.asyncio import Redis

from dema.integrity.signer import BallotSigner
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.streaming.keys import CONSUMER_GROUP, ElectionKeys
from dema.streaming.stream import BallotStream
from tests.factories import make_ballot
from tests.helpers import SIGNING_KEY, rejected_entries

pytestmark = pytest.mark.integration

KEYS = ElectionKeys.for_election(DEMA_2026_FIRST_ROUND.election)


@pytest.fixture
async def stream(redis_client: Redis) -> BallotStream:
    stream = BallotStream(redis_client, KEYS)
    await stream.ensure_group()
    return stream


async def pending(redis_client: Redis) -> int:
    summary = await redis_client.xpending(KEYS.ballots, CONSUMER_GROUP)
    return summary["pending"]


def test_keys_are_scoped_by_election() -> None:
    assert KEYS.ballots == "dema:2026:1:ballots"
    assert KEYS.tally == "dema:2026:1:tally"


async def test_group_creation_is_idempotent(stream: BallotStream) -> None:
    await stream.ensure_group()


async def test_delivers_published_ballots(stream: BallotStream) -> None:
    signed = BallotSigner(SIGNING_KEY).sign(make_ballot())

    assert await stream.publish([signed]) == 1
    entries = await stream.read("worker-1", count=10, block_ms=10)

    assert [entry.signed for entry in entries] == [signed]


async def test_acknowledged_entries_leave_pending_list(
    stream: BallotStream, redis_client: Redis
) -> None:
    await stream.publish([BallotSigner(SIGNING_KEY).sign(make_ballot())])
    entries = await stream.read("worker-1", count=10, block_ms=10)
    assert await pending(redis_client) == 1

    await stream.acknowledge(entries)

    assert await pending(redis_client) == 0


async def test_claims_entries_abandoned_by_other_consumer(stream: BallotStream) -> None:
    await stream.publish([BallotSigner(SIGNING_KEY).sign(make_ballot())])
    abandoned = await stream.read("crashed", count=10, block_ms=10)

    claimed = await stream.claim_stale("rescuer", min_idle_ms=0, count=10)

    assert [entry.id for entry in claimed] == [entry.id for entry in abandoned]


async def test_flags_malformed_entries(
    stream: BallotStream, redis_client: Redis
) -> None:
    await redis_client.xadd(KEYS.ballots, {"payload": b"{}"})

    [entry] = await stream.read("worker-1", count=10, block_ms=10)

    assert entry.signed is None


async def test_moves_rejected_entries_aside(
    stream: BallotStream, redis_client: Redis
) -> None:
    await stream.publish([BallotSigner(SIGNING_KEY).sign(make_ballot())])
    [entry] = await stream.read("worker-1", count=10, block_ms=10)

    await stream.reject(entry, "invalid signature")

    [fields] = await rejected_entries(redis_client, KEYS)
    assert fields[b"reason"] == b"invalid signature"
    assert fields[b"entry"] == entry.id


async def test_clear_removes_streams(stream: BallotStream, redis_client: Redis) -> None:
    await stream.publish([BallotSigner(SIGNING_KEY).sign(make_ballot())])

    await stream.clear()

    assert await redis_client.exists(KEYS.ballots) == 0
