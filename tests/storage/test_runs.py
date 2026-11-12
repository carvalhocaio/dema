import pytest
from psycopg import AsyncConnection

from dema.domain.election import ElectionNotSetUpError, ElectionRound
from dema.domain.run import Run, RunStatus
from dema.storage.runs import RunRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def runs(async_connection: AsyncConnection) -> RunRepository:
    return RunRepository(async_connection)


async def test_creates_a_preparing_run_and_reads_it_back(runs: RunRepository) -> None:
    run = await runs.create(2026, ElectionRound.FIRST, 42, [27, 99])

    assert run.status is RunStatus.PREPARING
    assert (run.year, run.round, run.seed) == (2026, ElectionRound.FIRST, 42)
    assert run.candidates == (27, 99)
    assert run.parent_id is None
    assert run.finished_at is None
    assert await runs.get(run.id) == run


async def test_first_round_runs_take_the_candidates_of_the_election(
    runs: RunRepository,
) -> None:
    run = await runs.create_first_round(2026, 5)

    assert run.round is ElectionRound.FIRST
    assert run.candidates == (12, 27, 31, 44, 99)


async def test_unknown_runs_and_elections_are_not_set_up(runs: RunRepository) -> None:
    with pytest.raises(ElectionNotSetUpError):
        await runs.get(999)
    with pytest.raises(ElectionNotSetUpError):
        await runs.create_first_round(2030, 1)


async def test_activation_points_at_the_run_and_supersedes_an_unfinished_one(
    runs: RunRepository,
) -> None:
    assert await runs.active() is None
    first = await runs.activate((await runs.create_first_round(2026, 1)).id)
    second = await runs.activate((await runs.create_first_round(2026, 2)).id)

    assert first.status is RunStatus.COUNTING
    assert (await runs.active()) == second
    superseded = await runs.get(first.id)
    assert superseded.status is RunStatus.SUPERSEDED
    assert superseded.finished_at is not None


async def test_finished_runs_keep_their_status(
    runs: RunRepository, first_run: Run
) -> None:
    await runs.finish(first_run.id, RunStatus.COMPLETE)
    await runs.finish(first_run.id, RunStatus.SUPERSEDED)
    child = await runs.create(
        2026, ElectionRound.FIRST, 7, first_run.candidates, parent_id=first_run.id
    )
    await runs.activate(child.id)

    assert (await runs.get(first_run.id)).status is RunStatus.COMPLETE
    assert child.parent_id == first_run.id
