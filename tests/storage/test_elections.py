from datetime import UTC, datetime

import psycopg
import pytest
from psycopg import AsyncConnection

from dema.domain.election import ElectionNotSetUpError, ElectionRound
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.elections import ElectionRepository

pytestmark = pytest.mark.integration


async def test_loads_candidates_and_polls_close(
    async_connection: AsyncConnection,
) -> None:
    record = await ElectionRepository(async_connection).load(2026, ElectionRound.FIRST)

    reference = DEMA_2026_FIRST_ROUND.election
    assert record.election.round is ElectionRound.FIRST
    assert set(record.election.candidates) == set(reference.candidates)
    assert record.polls_close == datetime(2026, 10, 4, 20, tzinfo=UTC)
    assert record.keys.ballots == "dema:2026:1:ballots"


async def test_reports_rounds_that_were_not_set_up(
    async_connection: AsyncConnection,
) -> None:
    repository = ElectionRepository(async_connection)

    with pytest.raises(ElectionNotSetUpError, match="run 'dema election setup' first"):
        await repository.load(2026, ElectionRound.SECOND)


async def test_lists_the_rounds_of_a_year(
    async_connection: AsyncConnection, seeded: psycopg.Connection
) -> None:
    repository = ElectionRepository(async_connection)

    assert await repository.rounds(2026) == [ElectionRound.FIRST]
    assert await repository.rounds(2030) == []
