import psycopg

from dema.sections.catalog import SectionCatalog
from dema.simulation.scenario import Scenario

SECTION_COLUMNS = ("state", "municipality_code", "zone", "number", "eligible_voters")


def seed_election(connection: psycopg.Connection, scenario: Scenario) -> None:
    election = scenario.election
    with connection.transaction():
        connection.execute(
            "INSERT INTO elections (year, round, polls_close) VALUES (%s, %s, %s) "
            "ON CONFLICT (year, round) "
            "DO UPDATE SET polls_close = EXCLUDED.polls_close",
            (election.year, election.round, scenario.polls_close),
        )
        with connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO candidates "
                "(year, round, number, name, party, birth_date) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (year, round, number) DO UPDATE SET "
                "name = EXCLUDED.name, party = EXCLUDED.party, "
                "birth_date = EXCLUDED.birth_date",
                [
                    (
                        election.year,
                        election.round,
                        candidate.number,
                        candidate.name,
                        candidate.party,
                        candidate.birth_date,
                    )
                    for candidate in election.candidates
                ],
            )


def replace_sections(connection: psycopg.Connection, catalog: SectionCatalog) -> None:
    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute(
            "CREATE TEMP TABLE staged_sections ("
            "state char(2), municipality_code integer, zone smallint, "
            "number smallint, eligible_voters integer) ON COMMIT DROP"
        )
        with cursor.copy("COPY staged_sections FROM STDIN") as copy:
            for row in catalog.frame.select(SECTION_COLUMNS).iter_rows():
                copy.write_row(row)
        cursor.execute(
            "INSERT INTO sections "
            "(state, municipality_code, zone, number, eligible_voters) "
            "SELECT * FROM staged_sections ON CONFLICT (key) "
            "DO UPDATE SET eligible_voters = EXCLUDED.eligible_voters"
        )
        cursor.execute(
            "DELETE FROM sections AS s WHERE NOT EXISTS ("
            "SELECT FROM staged_sections AS t "
            "WHERE (t.state, t.municipality_code, t.zone, t.number) "
            "= (s.state, s.municipality_code, s.zone, s.number))"
        )


def clear_ballots(connection: psycopg.Connection, scenario: Scenario) -> None:
    election = scenario.election
    with connection.transaction():
        connection.execute(
            "DELETE FROM ballots WHERE year = %s AND round = %s",
            (election.year, election.round),
        )
