from dataclasses import replace
from datetime import UTC, datetime

import pytest
from psycopg import AsyncConnection

from dema.domain.election import ElectionNotSetUpError, ElectionRound
from dema.domain.run import Run
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.storage.elections import ElectionRepository

pytestmark = pytest.mark.integration


async def test_loads_the_candidates_and_polls_close_of_a_run(
    async_connection: AsyncConnection, first_run: Run
) -> None:
    record = await ElectionRepository(async_connection).load(first_run)

    reference = DEMA_2026_FIRST_ROUND.election
    assert record.run == first_run
    assert record.election.round is ElectionRound.FIRST
    assert set(record.election.candidates) == set(reference.candidates)
    assert record.polls_close == datetime(2026, 10, 4, 20, tzinfo=UTC)
    assert record.keys.ballots == f"dema:2026:1:{first_run.id}:ballots"


async def test_keeps_only_the_candidates_of_the_run(
    async_connection: AsyncConnection, first_run: Run
) -> None:
    run = replace(first_run, candidates=(KEONS.number, NICO.number))

    record = await ElectionRepository(async_connection).load(run)

    assert record.election.candidate_numbers == {KEONS.number, NICO.number}


async def test_reports_rounds_that_were_not_set_up(
    async_connection: AsyncConnection, first_run: Run
) -> None:
    run = replace(first_run, round=ElectionRound.SECOND)

    with pytest.raises(ElectionNotSetUpError, match="run 'dema election setup' first"):
        await ElectionRepository(async_connection).load(run)
