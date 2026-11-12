from pathlib import Path

import psycopg
import pytest
import redis

from dema.cli import main
from dema.sections.catalog import SectionCatalog

pytestmark = pytest.mark.integration


def test_publish_streams_every_ballot(
    migrated: psycopg.Connection,
    cli_env: None,
    redis_url: str,
    catalog_path: Path,
    ballots_path: Path,
    small_catalog: SectionCatalog,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["election", "setup", str(catalog_path)])
    capsys.readouterr()

    main(["ballots", "publish", str(ballots_path), "--speed", "1e9"])

    assert capsys.readouterr().out == f"published {len(small_catalog):,} ballots\n"
    stream = redis.Redis.from_url(redis_url).xlen("dema:2026:1:1:ballots")
    assert stream == len(small_catalog)
