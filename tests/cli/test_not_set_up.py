from pathlib import Path

import psycopg
import pytest

from dema.cli import main

pytestmark = pytest.mark.integration

MESSAGE = "dema: run 'dema election setup' first"


@pytest.mark.parametrize(
    "command",
    [
        ["tally", "watch"],
        ["tally", "rebuild"],
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
