from datetime import UTC, date, datetime

import psycopg
import pytest

from dema.storage.migrator import Migrator
from tests.factories import KEONS, NICO, make_section_key

pytestmark = pytest.mark.integration


@pytest.fixture
def schema(connection: psycopg.Connection) -> psycopg.Connection:
    Migrator(connection).migrate()
    connection.execute(
        "INSERT INTO elections VALUES (2026, 1, %s)",
        (datetime(2026, 10, 4, 20, tzinfo=UTC),),
    )
    connection.execute(
        "INSERT INTO candidates VALUES (2026, 1, %s, %s, 'Dema Order', %s)",
        (NICO.number, NICO.name, date(1961, 5, 24)),
    )
    connection.execute("INSERT INTO sections VALUES ('MT', 90670, 1, 1, 400)")
    connection.commit()
    return connection


def insert_ballot(connection: psycopg.Connection, section: str) -> None:
    connection.execute(
        "INSERT INTO ballots (year, round, section, blank_votes, null_votes, "
        "issued_at, payload, signature) VALUES (2026, 1, %s, 5, 10, now(), %s, %s)",
        (section, b"{}", "0" * 64),
    )


def test_section_key_matches_domain_format(schema: psycopg.Connection) -> None:
    key = schema.execute("SELECT key FROM sections").fetchone()

    assert key == (str(make_section_key()),)


def test_rejects_duplicated_ballot(schema: psycopg.Connection) -> None:
    insert_ballot(schema, str(make_section_key()))

    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_ballot(schema, str(make_section_key()))


def test_rejects_ballot_for_unknown_section(schema: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insert_ballot(schema, "SP-71072-0001-0010")


def test_rejects_votes_for_unknown_candidate(schema: psycopg.Connection) -> None:
    section = str(make_section_key())
    insert_ballot(schema, section)

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        schema.execute(
            "INSERT INTO ballot_votes VALUES (2026, 1, %s, %s, 120)",
            (section, KEONS.number),
        )


def test_deleting_ballot_cascades_to_votes(schema: psycopg.Connection) -> None:
    section = str(make_section_key())
    insert_ballot(schema, section)
    schema.execute(
        "INSERT INTO ballot_votes VALUES (2026, 1, %s, %s, 150)",
        (section, NICO.number),
    )

    schema.execute("DELETE FROM ballots")

    assert schema.execute("SELECT count(*) FROM ballot_votes").fetchone() == (0,)
