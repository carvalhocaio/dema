from pathlib import Path

import psycopg
import pytest
import redis

from dema.cli import main
from dema.sections.catalog import SectionCatalog

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
