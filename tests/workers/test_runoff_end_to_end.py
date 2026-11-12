import psycopg
import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.domain.election import ElectionRound
from dema.domain.run import Run
from dema.integrity.signer import BallotSigner
from dema.runtime.active import ActiveRuns
from dema.sections.catalog import SectionCatalog
from dema.services.counting import derive_runoff, simulate
from dema.services.runs import publish_ballots, start_run
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE
from dema.storage.ballots import PostgresBallotRepository
from dema.storage.seed import seed_election
from dema.tallying.outcome import Verdict, decide
from dema.tallying.redis_store import RedisTallyStore
from dema.workers.lanes import ActiveLanes
from dema.workers.tally_worker import TallyWorker
from tests.helpers import SIGNING_KEY

pytestmark = pytest.mark.integration

INSTANT = 1e9


async def test_runoff_run_is_counted_by_workers_following_the_active_run(
    seeded: psycopg.Connection,
    async_connection: AsyncConnection,
    redis_client: Redis,
    small_catalog: SectionCatalog,
    first_run: Run,
) -> None:
    first_round = simulate(DEMA_2026_FIRST_ROUND, small_catalog, 7)
    runoff = derive_runoff(first_round, 7)
    seed_election(seeded, runoff.election, SECOND_ROUND_POLLS_CLOSE)
    active = ActiveRuns(redis_client, async_connection)
    second = await active.runs.create(
        2026,
        ElectionRound.SECOND,
        7,
        [candidate.number for candidate in runoff.election.candidates],
        parent_id=first_run.id,
    )
    record = await start_run(
        active, redis_client, second, len(small_catalog), small_catalog.total_electorate
    )
    signer = BallotSigner(SIGNING_KEY)
    await publish_ballots(redis_client, record, signer, runoff.ballots, INSTANT, 500)
    worker = TallyWorker(
        lanes=ActiveLanes(active, redis_client, async_connection),
        signer=signer,
        consumer="runoff-test",
        batch_size=100,
        block_ms=10,
    )

    while await worker.run_once():
        pass

    tally = await RedisTallyStore(redis_client, record.keys, record.election).snapshot()
    outcome = decide(record.election, tally)
    assert tally.is_complete
    assert outcome.verdict is Verdict.ELECTED
    assert outcome.finalists[0] in runoff.election.candidates
    repository = PostgresBallotRepository(async_connection, record.election, second.id)
    assert await repository.tally() == tally
    family = await active.family()
    assert [item.run.id for item in family] == [first_run.id, second.id]
