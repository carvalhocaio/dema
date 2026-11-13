import psycopg
import pytest

from dema.demo.setup import demo_environment, prepare_database


def test_enables_runs_and_keeps_an_existing_signing_key() -> None:
    env, generated = demo_environment({"PATH": "/bin"}, has_key=True)

    assert env == {"PATH": "/bin", "DEMA_ALLOW_RUNS": "true"}
    assert generated is False


def test_generates_an_ephemeral_key_when_missing() -> None:
    env, generated = demo_environment({}, False, lambda: "k" * 64)

    assert env["DEMA_SIGNING_KEY"] == "k" * 64
    assert generated is True


def test_default_key_is_random_and_long_enough() -> None:
    first, _ = demo_environment({}, has_key=False)
    second, _ = demo_environment({}, has_key=False)

    assert len(first["DEMA_SIGNING_KEY"]) == 64
    assert first["DEMA_SIGNING_KEY"] != second["DEMA_SIGNING_KEY"]


@pytest.mark.integration
def test_prepares_an_empty_database_once(
    connection: psycopg.Connection, database_url: str
) -> None:
    assert prepare_database(database_url, 2026, 50) == 50
    assert prepare_database(database_url, 2026, 999) == 50

    [(candidates,)] = connection.execute(
        "SELECT count(*) FROM candidates WHERE round = 1"
    ).fetchall()
    assert candidates == 5
