import asyncio
import hashlib
import hmac
from collections.abc import Sequence

import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.domain.ballot import Ballot
from dema.domain.run import Run
from dema.integrity.signer import BallotSigner, SignedBallot, VerifiedBallot
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.ballots import PostgresBallotRepository
from dema.storage.runs import RunRepository
from dema.streaming.keys import ElectionKeys
from dema.streaming.stream import BallotStream
from dema.tallying.redis_store import RedisTallyStore
from dema.workers import tally_worker
from dema.workers.lanes import FixedLane, Lane
from dema.workers.repository import BallotRepository
from dema.workers.tally_worker import TallyWorker
from tests.helpers import SIGNING_KEY, expected_tally, rejected_entries

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election
SIGNER = BallotSigner(SIGNING_KEY)


@pytest.fixture
def keys(first_run: Run) -> ElectionKeys:
    return ElectionKeys.for_run(first_run)


@pytest.fixture
async def stream(
    redis_client: Redis, keys: ElectionKeys, first_run: Run
) -> BallotStream:
    stream = BallotStream(redis_client, keys, run_id=first_run.id)
    await stream.ensure_group()
    return stream


@pytest.fixture
async def store(
    redis_client: Redis, keys: ElectionKeys, small_catalog: SectionCatalog
) -> RedisTallyStore:
    store = RedisTallyStore(redis_client, keys, ELECTION)
    await store.reset(len(small_catalog), small_catalog.total_electorate)
    return store


@pytest.fixture
def repository(
    async_connection: AsyncConnection, first_run: Run
) -> PostgresBallotRepository:
    return PostgresBallotRepository(async_connection, ELECTION, first_run.id)


def make_worker(
    stream: BallotStream,
    repository: BallotRepository,
    store: RedisTallyStore,
    stale_after_ms: int = 30_000,
    run_id: int | None = None,
) -> TallyWorker:
    lane = Lane(
        run_id=run_id if run_id is not None else stream.run_id or 0,
        stream=stream,
        repository=repository,
        store=store,
    )
    return TallyWorker(
        lanes=FixedLane(lane),
        signer=SIGNER,
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
    keys: ElectionKeys,
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
    [fields] = await rejected_entries(redis_client, keys)
    assert fields[b"reason"] == b"invalid signature"


async def test_rejects_malformed_entries(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    redis_client: Redis,
    keys: ElectionKeys,
) -> None:
    await redis_client.xadd(keys.ballots, {"payload": b"{}"})

    await drain(make_worker(stream, repository, store))

    [fields] = await rejected_entries(redis_client, keys)
    assert fields[b"reason"] == b"malformed entry"


async def test_rejects_authentic_but_invalid_payloads(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    redis_client: Redis,
    keys: ElectionKeys,
) -> None:
    payload = b"{}"
    signature = hmac.new(SIGNING_KEY, payload, hashlib.sha3_256).hexdigest()
    await stream.publish([SignedBallot(payload=payload, signature=signature)])

    await drain(make_worker(stream, repository, store))

    [fields] = await rejected_entries(redis_client, keys)
    assert fields[b"reason"].startswith(b"invalid payload:")


async def test_run_retries_failed_batches_until_stopped(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    worker = make_worker(stream, repository, store)
    stop = asyncio.Event()
    attempts: list[int] = []

    async def fail_then_stop() -> int:
        attempts.append(len(attempts))
        if len(attempts) == 1:
            raise RuntimeError("database went away")
        stop.set()
        return 0

    monkeypatch.setattr(tally_worker, "RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(worker, "run_once", fail_then_stop)

    await worker.run(stop)

    assert attempts == [0, 1]
    assert "batch failed" in caplog.text


class SwitchingRepository:
    def __init__(self, inner: PostgresBallotRepository, switch: RunRepository) -> None:
        self._inner = inner
        self._switch = switch
        self.newer: Run | None = None

    async def save_many(self, verified: Sequence[VerifiedBallot]) -> int:
        run = await self._switch.active()
        assert run is not None
        self.newer = await self._switch.create(
            run.year, run.round, run.seed + 1, run.candidates
        )
        await self._switch.activate(self.newer.id)
        return await self._inner.save_many(verified)


async def test_a_batch_read_before_a_new_run_never_reaches_it(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    async_connection: AsyncConnection,
    redis_client: Redis,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    switching = SwitchingRepository(repository, RunRepository(async_connection))
    await stream.publish([SIGNER.sign(ballot) for ballot in small_ballots[:20]])

    await make_worker(stream, switching, store).run_once()

    assert switching.newer is not None
    newer_keys = ElectionKeys.for_run(switching.newer)
    newer_store = RedisTallyStore(redis_client, newer_keys, ELECTION)
    await newer_store.reset(len(small_catalog), small_catalog.total_electorate)
    assert (await newer_store.snapshot()).counted_sections == 0
    newer = PostgresBallotRepository(async_connection, ELECTION, switching.newer.id)
    assert (await newer.tally()).counted_sections == 0
    cursor = await async_connection.execute("SELECT count(*) FROM ballots")
    assert await cursor.fetchone() == (0,)


async def test_skips_entries_published_for_another_run(
    stream: BallotStream,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
    redis_client: Redis,
    keys: ElectionKeys,
    first_run: Run,
    small_ballots: list[Ballot],
) -> None:
    stale = BallotStream(redis_client, keys, run_id=first_run.id + 100)
    await stale.publish([SIGNER.sign(small_ballots[0])])

    worker = make_worker(stream, repository, store, run_id=first_run.id)
    assert await worker.run_once() == 1

    assert (await store.snapshot()).counted_sections == 0
    assert await rejected_entries(redis_client, keys) == []


class FlippingLanes:
    def __init__(self, *lanes: Lane) -> None:
        self._lanes = list(lanes)

    async def current(self) -> Lane:
        return self._lanes.pop(0) if len(self._lanes) > 1 else self._lanes[0]


async def test_switching_runs_prepares_the_new_stream(
    redis_client: Redis,
    repository: PostgresBallotRepository,
    store: RedisTallyStore,
) -> None:
    first = BallotStream(redis_client, ElectionKeys("dema:test:1"), run_id=1)
    second = BallotStream(redis_client, ElectionKeys("dema:test:2"), run_id=2)
    worker = TallyWorker(
        lanes=FlippingLanes(
            Lane(1, first, repository, store), Lane(2, second, repository, store)
        ),
        signer=SIGNER,
        consumer="worker-test",
        block_ms=10,
    )

    await worker.run_once()
    await worker.run_once()

    groups = await redis_client.xinfo_groups("dema:test:2:ballots")
    assert [group["name"] for group in groups] == [b"tallying"]
