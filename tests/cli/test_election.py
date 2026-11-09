from pathlib import Path

import polars as pl
import psycopg
import pytest
import redis

from dema.cli import main
from dema.config import get_settings
from dema.sections.catalog import SectionCatalog
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE

pytestmark = pytest.mark.integration


def test_setup_seeds_sections_and_resets_the_tally(
    migrated: psycopg.Connection,
    cli_env: None,
    redis_url: str,
    catalog_path: Path,
    small_catalog: SectionCatalog,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["election", "setup", str(catalog_path)])

    output = capsys.readouterr().out
    assert "election 2026/1 ready" in output
    assert f"sections:   {len(small_catalog):>13,}" in output
    [(sections,)] = migrated.execute("SELECT count(*) FROM sections").fetchall()
    assert sections == len(small_catalog)
    meta = redis.Redis.from_url(redis_url).hgetall("dema:2026:1:meta")
    assert int(meta[b"total_electorate"]) == small_catalog.total_electorate


def count_ballots(connection: psycopg.Connection, round_: int) -> int:
    [(count,)] = connection.execute(
        "SELECT count(*) FROM ballots WHERE round = %s", (round_,)
    ).fetchall()
    return count


def keep_first_round_ballot(connection: psycopg.Connection) -> None:
    connection.execute(
        "INSERT INTO ballots (year, round, section, blank_votes, null_votes, "
        "issued_at, payload, signature) "
        "SELECT 2026, 1, key, 0, 0, now(), '', repeat('0', 64) "
        "FROM sections LIMIT 1"
    )
    connection.commit()


def test_setup_prepares_the_runoff_without_touching_the_first_round(
    migrated: psycopg.Connection,
    cli_env: None,
    redis_url: str,
    catalog_path: Path,
    runoff_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["election", "setup", str(catalog_path)])
    keep_first_round_ballot(migrated)
    monkeypatch.setenv("DEMA_ROUND", "2")
    get_settings.cache_clear()
    capsys.readouterr()

    main(["election", "setup", str(catalog_path), "--ballots", str(runoff_path)])

    output = capsys.readouterr().out
    assert "election 2026/2 ready" in output
    assert "candidates: Keons x Nico" in output
    assert count_ballots(migrated, 1) == 1
    [(polls_close,)] = migrated.execute(
        "SELECT polls_close FROM elections WHERE round = 2"
    ).fetchall()
    assert polls_close == SECOND_ROUND_POLLS_CLOSE
    assert redis.Redis.from_url(redis_url).exists("dema:2026:2:meta")


def test_runoff_setup_needs_the_first_round(
    migrated: psycopg.Connection,
    cli_env: None,
    catalog_path: Path,
    runoff_path: Path,
) -> None:
    with pytest.raises(SystemExit) as raised:
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

    assert str(raised.value) == "dema: run 'dema election setup' first"


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
