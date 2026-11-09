from pathlib import Path

import psycopg
import pytest

from dema.cli import main, workers

pytestmark = pytest.mark.integration

MESSAGE = "dema: run 'dema election setup' first"


@pytest.mark.parametrize(
    "command",
    [
        ["tally", "watch"],
        ["tally", "rebuild"],
        ["workers", "run"],
    ],
)
def test_commands_need_a_prepared_round(
    migrated: psycopg.Connection, cli_env: None, command: list[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(command)

    assert str(raised.value) == MESSAGE


def test_publish_needs_a_prepared_round(
    migrated: psycopg.Connection, cli_env: None, ballots_path: Path
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["ballots", "publish", str(ballots_path)])

    assert str(raised.value) == MESSAGE


def test_spawned_workers_exit_cleanly_without_a_prepared_round(
    migrated: psycopg.Connection, cli_env: None
) -> None:
    with pytest.raises(SystemExit) as raised:
        workers._work("worker-x")

    assert str(raised.value) == MESSAGE
