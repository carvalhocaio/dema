import psycopg
import pytest

from dema.sections.catalog import SectionCatalog
from dema.sections.synthetic import SyntheticSectionSource
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.seed import clear_ballots, replace_sections, seed_election

pytestmark = pytest.mark.integration


def scalar(connection: psycopg.Connection, query: str) -> object:
    row = connection.execute(query.encode()).fetchone()
    return row[0] if row else None


def test_seeds_election_idempotently(migrated: psycopg.Connection) -> None:
    seed_election(migrated, DEMA_2026_FIRST_ROUND)
    seed_election(migrated, DEMA_2026_FIRST_ROUND)

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


def test_clears_election_ballots(seeded: psycopg.Connection) -> None:
    section = scalar(seeded, "SELECT key FROM sections LIMIT 1")
    seeded.execute(
        "INSERT INTO ballots (year, round, section, blank_votes, null_votes, "
        "issued_at, payload, signature) VALUES (2026, 1, %s, 0, 0, now(), '', '')",
        (section,),
    )

    clear_ballots(seeded, DEMA_2026_FIRST_ROUND)

    assert scalar(seeded, "SELECT count(*) FROM ballots") == 0
