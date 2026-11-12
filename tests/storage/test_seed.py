import psycopg
import pytest
from psycopg import AsyncConnection

from dema.sections.catalog import SectionCatalog
from dema.sections.synthetic import SyntheticSectionSource
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.seed import (
    load_catalog,
    replace_sections,
    seed_election,
    seed_election_at,
)

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election


def scalar(connection: psycopg.Connection, query: str) -> object:
    row = connection.execute(query.encode()).fetchone()
    return row[0] if row else None


def test_seeds_election_idempotently(migrated: psycopg.Connection) -> None:
    seed_election(migrated, ELECTION, DEMA_2026_FIRST_ROUND.polls_close)
    seed_election(migrated, ELECTION, DEMA_2026_FIRST_ROUND.polls_close)

    assert scalar(migrated, "SELECT count(*) FROM elections") == 1
    assert scalar(migrated, "SELECT count(*) FROM candidates") == 5


def test_loads_sections_from_catalog(
    seeded: psycopg.Connection, small_catalog: SectionCatalog
) -> None:
    assert scalar(seeded, "SELECT count(*) FROM sections") == len(small_catalog)
    assert (
        scalar(seeded, "SELECT sum(eligible_voters) FROM sections")
        == small_catalog.total_electorate
    )


def test_replacing_sections_drops_stale_ones(seeded: psycopg.Connection) -> None:
    smaller = SyntheticSectionSource(50, seed=7).load()

    replace_sections(seeded, smaller)

    assert scalar(seeded, "SELECT count(*) FROM sections") == 50
    assert (
        scalar(seeded, "SELECT sum(eligible_voters) FROM sections")
        == smaller.total_electorate
    )


async def test_loads_the_catalog_back_from_postgres(
    async_connection: AsyncConnection, small_catalog: SectionCatalog
) -> None:
    catalog = await load_catalog(async_connection)

    assert catalog.frame.equals(small_catalog.frame)


def test_seeds_an_election_from_a_database_url(
    migrated: psycopg.Connection, database_url: str
) -> None:
    seed_election_at(database_url, ELECTION, DEMA_2026_FIRST_ROUND.polls_close)

    assert scalar(migrated, "SELECT count(*) FROM candidates") == len(
        ELECTION.candidates
    )
