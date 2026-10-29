import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.domain.ballot import Ballot
from dema.integrity.signer import BallotSigner, SignedBallot
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.ballots import PostgresBallotRepository
from dema.streaming.keys import ElectionKeys
from dema.streaming.stream import BallotStream
from dema.tallying.redis_store import RedisTallyStore
from dema.workers.tally_worker import TallyWorker
from tests.helpers import SIGNING_KEY, expected_tally, rejected_entries

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election
KEYS = ElectionKeys.for_election(ELECTION)
SIGNER = BallotSigner(SIGNING_KEY)


@pytest.fixture
async def stream(redis_client: Redis) -> BallotStream:
    stream = BallotStream(redis_client, KEYS)
    await stream.ensure_group()
    return stream


@pytest.fixture
async def store(redis_client: Redis, small_catalog: SectionCatalog) -> RedisTallyStore:
    store = RedisTallyStore(redis_client, KEYS, ELECTION)
    await store.reset(len(small_catalog), small_catalog.total_electorate)
    return store


@pytest.fixture
def repository(async_connection: AsyncConnection) -> PostgresBallotRepository:
    return PostgresBallotRepository(async_connection, ELECTION)


def make_worker(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    stale_after_ms: int = 30_000,
) -> TallyWorker:
    return TallyWorker(
        stream=stream,
        signer=SIGNER,
        repository=repository,
        store=store,
        consumer="worker-test",
        batch_size=50,
        block_ms=10,
        stale_after_ms=stale_after_ms,
    )


async def drain(worker: TallyWorker) -> None:
    while await worker.run_once():
        pass


async def test_tallies_published_ballots_end_to_end(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    await stream.publish([SIGNER.sign(ballot) for ballot in small_ballots])

    await drain(make_worker(stream, repository, store))

    expected = expected_tally(small_catalog, small_ballots)
    assert await store.snapshot() == expected
    assert await repository.tally() == expected


async def test_counts_republished_ballots_once(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    signed = [SIGNER.sign(ballot) for ballot in small_ballots[:30]]
    await stream.publish(signed + signed)

    await drain(make_worker(stream, repository, store))

    expected = expected_tally(small_catalog, small_ballots[:30])
    assert await store.snapshot() == expected
    assert await repository.tally() == expected


async def test_recovers_ballots_from_crashed_consumer(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    await stream.publish([SIGNER.sign(ballot) for ballot in small_ballots[:30]])
    await stream.read("crashed", count=30, block_ms=10)

    await drain(make_worker(stream, repository, store, stale_after_ms=0))

    assert await store.snapshot() == expected_tally(small_catalog, small_ballots[:30])


async def test_rejects_tampered_ballots(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    redis_client: Redis,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    genuine = SIGNER.sign(small_ballots[0])
    original = SIGNER.sign(small_ballots[1])
    forged = original.payload.replace(b'"blank_votes":', b'"blank_votes":9')
    tampered = SignedBallot(payload=forged, signature=original.signature)
    await stream.publish([genuine, tampered])

    await drain(make_worker(stream, repository, store))

    assert await store.snapshot() == expected_tally(small_catalog, small_ballots[:1])
    [fields] = await rejected_entries(redis_client, KEYS)
    assert fields[b"reason"] == b"invalid signature"
