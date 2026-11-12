import psycopg
import pytest

from dema.cli import main

pytestmark = pytest.mark.integration


def test_migrate_applies_pending_then_reports_up_to_date(
    connection: psycopg.Connection, cli_env: None, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["db", "migrate"])
    first = capsys.readouterr().out
    main(["db", "migrate"])

    assert first.splitlines() == [
        "applied 0001_initial_schema",
        "applied 0002_minute_rollup",
        "applied 0003_state_rollup",
        "applied 0004_runs",
    ]
    assert capsys.readouterr().out == "database is up to date\n"
