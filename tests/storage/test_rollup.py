import asyncio

import psycopg
import pytest
from psycopg import AsyncConnection

from dema.domain.ballot import Ballot
from dema.domain.run import Run
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.ballots import PostgresBallotRepository
from dema.storage.migrator import Migrator, discover
from dema.storage.seed import replace_sections, seed_election
from dema.tallying.outcome import Verdict
from tests.storage.test_ballots import verify_all

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election

DIRECT_TOTALS = """
SELECT date_trunc('minute', b.issued_at, 'UTC'), count(*), sum(s.eligible_voters),
       sum(b.blank_votes), sum(b.null_votes)
FROM ballots AS b JOIN sections AS s ON s.key = b.section
GROUP BY 1 ORDER BY 1
"""
ROLLUP_TOTALS = """
SELECT minute, sections, electorate, blank_votes, null_votes
FROM minute_totals ORDER BY minute
"""
DIRECT_VOTES = """
SELECT date_trunc('minute', b.issued_at, 'UTC'), v.candidate, sum(v.votes)
FROM ballot_votes AS v JOIN ballots AS b USING (year, round, section)
GROUP BY 1, 2 ORDER BY 1, 2
"""
ROLLUP_VOTES = "SELECT minute, candidate, votes FROM minute_votes ORDER BY 1, 2"
DIRECT_STATE_TOTALS = """
SELECT s.state, count(*), sum(s.eligible_voters), sum(b.blank_votes), sum(b.null_votes)
FROM ballots AS b JOIN sections AS s ON s.key = b.section
GROUP BY 1 ORDER BY 1
"""
STATE_TOTALS = """
SELECT state, sections, electorate, blank_votes, null_votes
FROM state_totals ORDER BY state
"""
DIRECT_STATE_VOTES = """
SELECT s.state, v.candidate, sum(v.votes)
FROM ballot_votes AS v JOIN ballots AS b USING (year, round, section)
JOIN sections AS s ON s.key = b.section
GROUP BY 1, 2 ORDER BY 1, 2
"""
STATE_VOTES = "SELECT state, candidate, votes FROM state_votes ORDER BY 1, 2"


PAIRS = (
    (ROLLUP_TOTALS, DIRECT_TOTALS),
    (ROLLUP_VOTES, DIRECT_VOTES),
    (STATE_TOTALS, DIRECT_STATE_TOTALS),
    (STATE_VOTES, DIRECT_STATE_VOTES),
)


def normalized(rows: list[tuple]) -> list[tuple]:
    return [tuple(int(v) if isinstance(v, int) else v for v in row) for row in rows]


async def rows(connection: AsyncConnection, query: str) -> list[tuple]:
    cursor = await connection.execute(query.encode())
    return normalized(await cursor.fetchall())


async def assert_rollup_matches_ballots(connection: AsyncConnection) -> None:
    for rollup, direct in PAIRS:
        assert await rows(connection, rollup) == await rows(connection, direct)
    assert await rows(connection, ROLLUP_TOTALS)


def assert_rollup_matches_ballots_now(connection: psycopg.Connection) -> None:
    for rollup, direct in PAIRS:
        assert normalized(connection.execute(rollup.encode()).fetchall()) == (
            normalized(connection.execute(direct.encode()).fetchall())
        )
    assert connection.execute(ROLLUP_TOTALS.encode()).fetchall()


@pytest.fixture
def repository(
    async_connection: AsyncConnection, first_run: Run
) -> PostgresBallotRepository:
    return PostgresBallotRepository(async_connection, ELECTION, first_run.id)


async def test_rollup_follows_saved_ballots_including_duplicates(
    repository: PostgresBallotRepository,
    async_connection: AsyncConnection,
    small_ballots: list[Ballot],
) -> None:
    await repository.save_many(verify_all(small_ballots[:80]))
    await repository.save_many(verify_all(small_ballots[40:120]))
    assert await repository.save_many(verify_all(small_ballots[:10])) == 0

    await assert_rollup_matches_ballots(async_connection)


async def test_concurrent_workers_keep_the_rollup_exact(
    database_url: str,
    async_connection: AsyncConnection,
    first_run: Run,
    small_ballots: list[Ballot],
) -> None:
    async def worker(batches: list[list[Ballot]]) -> None:
        connection = await AsyncConnection.connect(database_url, autocommit=True)
        async with connection:
            repository = PostgresBallotRepository(connection, ELECTION, first_run.id)
            for batch in batches:
                await repository.save_many(verify_all(batch))

    batches = [small_ballots[i : i + 25] for i in range(0, len(small_ballots), 25)]
    await asyncio.gather(
        worker(batches), worker(batches[::-1]), worker(batches[1::2] + batches[::2])
    )

    await assert_rollup_matches_ballots(async_connection)


async def test_rebuild_restores_a_wiped_rollup(
    repository: PostgresBallotRepository,
    async_connection: AsyncConnection,
    small_ballots: list[Ballot],
) -> None:
    await repository.save_many(verify_all(small_ballots))
    await async_connection.execute("UPDATE minute_votes SET votes = 0")
    await async_connection.execute("DELETE FROM minute_totals WHERE sections > 1")
    await async_connection.execute("DELETE FROM state_votes")

    await repository.rebuild_rollup()

    await assert_rollup_matches_ballots(async_connection)


async def test_timeline_accumulates_minutes_into_the_final_tally(
    repository: PostgresBallotRepository, small_ballots: list[Ballot]
) -> None:
    await repository.save_many(verify_all(small_ballots))

    timeline = await repository.timeline()

    minutes = [point.at for point in timeline.points]
    assert minutes == sorted(minutes)
    assert len(minutes) > 1
    assert timeline.points[-1].tally == await repository.tally()
    assert timeline.points[-1].outcome.verdict is Verdict.RUNOFF
    assert timeline.decided_at is not None
    assert timeline.decided_at <= minutes[-1]


async def test_timeline_is_empty_before_any_ballot(
    repository: PostgresBallotRepository,
) -> None:
    timeline = await repository.timeline()

    assert timeline.points == ()
    assert timeline.decided_at is None


def test_migrations_backfill_ballots_saved_before_runs(
    connection: psycopg.Connection,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    initial, *_ = discover()
    Migrator(connection, [initial]).migrate()
    seed_election(connection, ELECTION, DEMA_2026_FIRST_ROUND.polls_close)
    replace_sections(connection, small_catalog)
    with connection.transaction(), connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO ballots (year, round, section, blank_votes, null_votes, "
            "issued_at, payload, signature) "
            "VALUES (2026, 1, %s, %s, %s, %s, '', repeat('0', 64))",
            [
                (str(b.section), b.blank_votes, b.null_votes, b.issued_at)
                for b in small_ballots
            ],
        )
        cursor.executemany(
            "INSERT INTO ballot_votes (year, round, section, candidate, votes) "
            "VALUES (2026, 1, %s, %s, %s)",
            [
                (str(b.section), number, votes)
                for b in small_ballots
                for number, votes in b.nominal_votes.items()
            ],
        )

    assert Migrator(connection).migrate() == [
        "0002_minute_rollup",
        "0003_state_rollup",
        "0004_runs",
    ]

    [(run_id, status, candidates)] = connection.execute(
        "SELECT id, status, candidates FROM runs"
    ).fetchall()
    assert status == "complete"
    assert candidates == sorted(ELECTION.candidate_numbers)
    assert connection.execute("SELECT run_id FROM active_run").fetchall() == [(run_id,)]
    assert connection.execute("SELECT DISTINCT run_id FROM ballots").fetchall() == [
        (run_id,)
    ]
    assert_rollup_matches_ballots_now(connection)


async def test_states_report_progress_and_leader_per_state(
    repository: PostgresBallotRepository,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    await repository.save_many(verify_all(small_ballots[:150]))

    states = await repository.states()

    by_state = {s.state: s for s in states}
    assert [s.state for s in states] == sorted(by_state)
    assert sum(s.tally.total_sections for s in states) == len(small_catalog)
    assert sum(s.tally.counted_sections for s in states) == 150
    assert any(s.leader is not None for s in states)
    assert all(s.leader is None for s in states if s.tally.counted_sections == 0)
