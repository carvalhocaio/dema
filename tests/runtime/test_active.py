import pytest
from psycopg import AsyncConnection
from redis.asyncio import Redis

from dema.domain.election import ElectionNotSetUpError, ElectionRound
from dema.domain.run import Run
from dema.runtime.active import ActiveRuns
from dema.streaming.keys import ACTIVE_RUN_KEY

pytestmark = pytest.mark.integration


@pytest.fixture
def active(redis_client: Redis, async_connection: AsyncConnection) -> ActiveRuns:
    return ActiveRuns(redis_client, async_connection)


async def test_falls_back_to_postgres_and_mirrors_the_pointer(
    active: ActiveRuns, redis_client: Redis, first_run: Run
) -> None:
    assert await active.current_id() == first_run.id
    assert await redis_client.get(ACTIVE_RUN_KEY) == str(first_run.id).encode()


async def test_reads_the_mirror_first(
    active: ActiveRuns, redis_client: Redis, first_run: Run
) -> None:
    await redis_client.set(ACTIVE_RUN_KEY, 12345)

    assert await active.current_id() == 12345


async def test_reports_when_nothing_was_set_up(active: ActiveRuns) -> None:
    with pytest.raises(ElectionNotSetUpError):
        await active.current()


async def test_caches_records_and_resolves_the_family(
    active: ActiveRuns, first_run: Run
) -> None:
    record = await active.current()

    assert await active.record(first_run.id) is record
    assert await active.family() == (record,)


async def test_activation_moves_the_pointer_to_a_child_run(
    active: ActiveRuns, redis_client: Redis, first_run: Run
) -> None:
    child = await active.runs.create(
        2026, ElectionRound.FIRST, 9, first_run.candidates, parent_id=first_run.id
    )

    activated = await active.activate(child.id)

    assert await redis_client.get(ACTIVE_RUN_KEY) == str(child.id).encode()
    family = await active.family()
    assert [record.run.id for record in family] == [first_run.id, child.id]
    assert family[-1].run == activated
