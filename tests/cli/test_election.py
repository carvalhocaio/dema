from pathlib import Path

import polars as pl
import psycopg
import pytest
import redis

from dema.cli import main
from dema.sections.catalog import SectionCatalog
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE

pytestmark = pytest.mark.integration


def runs(connection: psycopg.Connection) -> list[tuple]:
    return connection.execute(
        "SELECT id, round, seed, status, candidates, parent_id FROM runs ORDER BY id"
    ).fetchall()


def test_setup_seeds_sections_and_opens_an_active_run(
    migrated: psycopg.Connection,
    cli_env: None,
    redis_url: str,
    catalog_path: Path,
    small_catalog: SectionCatalog,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["election", "setup", str(catalog_path), "--seed", "40"])

    output = capsys.readouterr().out
    assert "election 2026/1 ready (run #1)" in output
    assert f"sections:   {len(small_catalog):>13,}" in output
    [(sections,)] = migrated.execute("SELECT count(*) FROM sections").fetchall()
    assert sections == len(small_catalog)
    assert runs(migrated) == [(1, 1, 40, "counting", [12, 27, 31, 44, 99], None)]
    client = redis.Redis.from_url(redis_url)
    assert client.get("dema:active_run") == b"1"
    meta = client.hgetall("dema:2026:1:1:meta")
    assert int(meta[b"total_electorate"]) == small_catalog.total_electorate


def keep_first_round_ballot(connection: psycopg.Connection) -> None:
    connection.execute(
        "INSERT INTO ballots (run_id, year, round, section, blank_votes, "
        "null_votes, issued_at, payload, signature) "
        "SELECT 1, 2026, 1, key, 0, 0, now(), '', repeat('0', 64) "
        "FROM sections LIMIT 1"
    )
    connection.commit()


def count_ballots(connection: psycopg.Connection, run_id: int) -> int:
    [(count,)] = connection.execute(
        "SELECT count(*) FROM ballots WHERE run_id = %s", (run_id,)
    ).fetchall()
    return count


def test_a_new_setup_supersedes_the_previous_run_and_keeps_its_ballots(
    migrated: psycopg.Connection,
    cli_env: None,
    catalog_path: Path,
) -> None:
    main(["election", "setup", str(catalog_path)])
    keep_first_round_ballot(migrated)

    main(["election", "setup", str(catalog_path)])

    assert [(run[0], run[3]) for run in runs(migrated)] == [
        (1, "superseded"),
        (2, "counting"),
    ]
    assert count_ballots(migrated, 1) == 1


def test_setup_opens_the_runoff_as_a_child_of_the_first_round(
    migrated: psycopg.Connection,
    cli_env: None,
    redis_url: str,
    catalog_path: Path,
    runoff_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["election", "setup", str(catalog_path)])
    keep_first_round_ballot(migrated)
    capsys.readouterr()

    main(
        [
            "election",
            "setup",
            str(catalog_path),
            "--round",
            "2",
            "--ballots",
            str(runoff_path),
        ]
    )

    assert "election 2026/2 ready (run #2)" in capsys.readouterr().out
    assert runs(migrated)[1] == (2, 2, 0, "counting", [27, 99], 1)
    assert count_ballots(migrated, 1) == 1
    [(polls_close,)] = migrated.execute(
        "SELECT polls_close FROM elections WHERE round = 2"
    ).fetchall()
    assert polls_close == SECOND_ROUND_POLLS_CLOSE
    assert redis.Redis.from_url(redis_url).exists("dema:2026:2:2:meta")


def test_runoff_setup_needs_an_active_first_round(
    migrated: psycopg.Connection,
    cli_env: None,
    catalog_path: Path,
    runoff_path: Path,
) -> None:
    second_round = ["--round", "2", "--ballots", str(runoff_path)]

    with pytest.raises(SystemExit) as without_runs:
        main(["election", "setup", str(catalog_path), *second_round])
    main(["election", "setup", str(catalog_path)])
    main(["election", "setup", str(catalog_path), *second_round])
    with pytest.raises(SystemExit) as after_runoff:
        main(["election", "setup", str(catalog_path), *second_round])

    expected = "dema: the second round needs an active first-round run"
    assert str(without_runs.value) == str(after_runoff.value) == expected


def rename_candidate(source: Path, target: Path, old: int, new: int) -> Path:
    frame = pl.read_parquet(source).rename({f"votes_{old}": f"votes_{new}"})
    frame.write_parquet(target)
    return target


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (
            ["--round", "1", "--ballots", "{runoff}"],
            "--ballots only applies to the second round",
        ),
        (["--round", "2"], "the second round needs --ballots"),
        (["--round", "2", "--ballots", "{first}"], "must name exactly two candidates"),
        (["--round", "2", "--ballots", "{stranger}"], "candidate 55 did not run"),
    ],
)
def test_setup_rejects_inconsistent_rounds(
    migrated: psycopg.Connection,
    cli_env: None,
    tmp_path: Path,
    catalog_path: Path,
    ballots_path: Path,
    runoff_path: Path,
    arguments: list[str],
    message: str,
) -> None:
    main(["election", "setup", str(catalog_path)])
    paths = {
        "{runoff}": str(runoff_path),
        "{first}": str(ballots_path),
        "{stranger}": str(
            rename_candidate(runoff_path, tmp_path / "stranger.parquet", 99, 55)
        ),
    }

    with pytest.raises(SystemExit, match=message):
        main(
            ["election", "setup", str(catalog_path)]
            + [paths.get(argument, argument) for argument in arguments]
        )
