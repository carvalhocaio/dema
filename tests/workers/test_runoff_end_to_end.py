import psycopg
import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.integrity.signer import BallotSigner
from dema.sections.catalog import SectionCatalog
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE, RunoffGenerator
from dema.storage.ballots import PostgresBallotRepository
from dema.storage.elections import ElectionRepository
from dema.storage.seed import seed_election
from dema.streaming.keys import ElectionKeys
from dema.streaming.stream import BallotStream
from dema.tallying.outcome import Verdict, decide
from dema.tallying.redis_store import RedisTallyStore
from dema.workers.tally_worker import TallyWorker
from tests.helpers import SIGNING_KEY

pytestmark = pytest.mark.integration


async def test_runoff_is_counted_and_elects_someone(
    seeded: psycopg.Connection,
    async_connection: AsyncConnection,
    redis_client: Redis,
    small_catalog: SectionCatalog,
) -> None:
    first_round = BallotGenerator(DEMA_2026_FIRST_ROUND, seed=7).generate(small_catalog)
    runoff = RunoffGenerator(DEMA_2026_FIRST_ROUND, seed=7).generate(
        first_round, DEMA_2026_FIRST_ROUND.election
    )
    seed_election(seeded, runoff.election, SECOND_ROUND_POLLS_CLOSE)
    record = await ElectionRepository(async_connection).load(
        2026, runoff.election.round
    )
    keys = ElectionKeys.for_election(record.election)
    store = RedisTallyStore(redis_client, keys, record.election)
    await store.reset(len(small_catalog), small_catalog.total_electorate)
    stream = BallotStream(redis_client, keys)
    await stream.ensure_group()
    signer = BallotSigner(SIGNING_KEY)
    await stream.publish([signer.sign(b) for b in runoff.ballots.in_release_order()])
    worker = TallyWorker(
        stream=stream,
        signer=signer,
        repository=PostgresBallotRepository(async_connection, record.election),
        store=store,
        consumer="runoff-test",
        batch_size=100,
        block_ms=10,
    )

    while await worker.run_once():
        pass

    tally = await store.snapshot()
    outcome = decide(record.election, tally)
    assert tally.is_complete
    assert outcome.verdict is Verdict.ELECTED
    assert outcome.finalists[0] in runoff.election.candidates
    assert (
        await PostgresBallotRepository(async_connection, record.election).tally()
        == tally
    )
