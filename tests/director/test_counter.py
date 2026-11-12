import asyncio
from collections.abc import AsyncIterator
from datetime import datetime

import psycopg
import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.director.control import CountRequest
from dema.director.counter import RunCounter
from dema.domain.election import Election, ElectionRound
from dema.domain.run import RunStatus
from dema.integrity.signer import BallotSigner
from dema.runtime.active import ActiveRuns
from dema.storage.runs import RunRepository
from dema.storage.seed import seed_election_at
from dema.tallying.outcome import Verdict, decide
from dema.tallying.redis_store import RedisTallyStore
from dema.workers import tally_worker
from dema.workers.lanes import ActiveLanes
from dema.workers.tally_worker import TallyWorker
from tests.helpers import SIGNING_KEY

pytestmark = pytest.mark.integration

SIGNER = BallotSigner(SIGNING_KEY)
INSTANT = 1e9
RUNOFF_SEED = 40
LANDSLIDE_SEED = 3


@pytest.fixture
def counter(
    seeded: psycopg.Connection,
    async_connection: AsyncConnection,
    redis_client: Redis,
    database_url: str,
) -> RunCounter:
    async def seed(election: Election, polls_close: datetime) -> None:
        await asyncio.to_thread(seed_election_at, database_url, election, polls_close)

    return RunCounter(
        redis_client,
        async_connection,
        SIGNER,
        seed,
        speed_factor=INSTANT,
        batch_size=100,
        poll_seconds=0.01,
    )


@pytest.fixture
async def worker(
    database_url: str, redis_client: Redis, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[None]:
    monkeypatch.setattr(tally_worker, "RETRY_DELAY_SECONDS", 0.01)
    stop = asyncio.Event()
    connection = await AsyncConnection.connect(database_url, autocommit=True)
    async with connection:
        active = ActiveRuns(redis_client, connection)
        worker = TallyWorker(
            lanes=ActiveLanes(active, redis_client, connection),
            signer=SIGNER,
            consumer="counter-test",
            batch_size=100,
            block_ms=10,
        )
        task = asyncio.create_task(worker.run(stop))
        yield
        stop.set()
        await task


async def statuses(connection: AsyncConnection) -> list[tuple]:
    cursor = await connection.execute(
        "SELECT round, seed, status, parent_id IS NOT NULL FROM runs ORDER BY id"
    )
    return await cursor.fetchall()


async def test_counts_the_first_round_and_then_the_runoff(
    counter: RunCounter,
    worker: None,
    async_connection: AsyncConnection,
    redis_client: Redis,
) -> None:
    run = await RunRepository(async_connection).create_first_round(2026, RUNOFF_SEED)

    await asyncio.wait_for(counter.count(CountRequest(run.id)), timeout=60)

    assert await statuses(async_connection) == [
        (1, RUNOFF_SEED, "complete", False),
        (2, RUNOFF_SEED, "complete", True),
    ]
    record = await ActiveRuns(redis_client, async_connection).current()
    tally = await RedisTallyStore(redis_client, record.keys, record.election).snapshot()
    assert record.election.round is ElectionRound.SECOND
    assert decide(record.election, tally).verdict is Verdict.ELECTED


async def test_stops_after_a_first_round_win(
    counter: RunCounter,
    worker: None,
    async_connection: AsyncConnection,
) -> None:
    run = await RunRepository(async_connection).create_first_round(2026, LANDSLIDE_SEED)

    await asyncio.wait_for(counter.count(CountRequest(run.id, speed=INSTANT)), 60)

    assert await statuses(async_connection) == [(1, LANDSLIDE_SEED, "complete", False)]


async def test_abandoning_a_count_supersedes_its_run(
    counter: RunCounter, async_connection: AsyncConnection
) -> None:
    run = await RunRepository(async_connection).create_first_round(2026, 11)
    task = asyncio.create_task(counter.count(CountRequest(run.id, speed=0.001)))
    while (await RunRepository(async_connection).get(run.id)).status is not (
        RunStatus.COUNTING
    ):
        await asyncio.sleep(0.01)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await counter.abandon()
    await counter.abandon()

    assert (await RunRepository(async_connection).get(run.id)).status is (
        RunStatus.SUPERSEDED
    )
