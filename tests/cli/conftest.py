from collections.abc import Iterator
from pathlib import Path

import pytest
import redis

from dema.config import get_settings
from dema.sections.catalog import SectionCatalog
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from tests.helpers import SIGNING_KEY


@pytest.fixture
def cli_env(
    monkeypatch: pytest.MonkeyPatch, database_dsn: str, redis_url: str
) -> Iterator[None]:
    monkeypatch.setenv("DEMA_DATABASE_URL", database_dsn)
    monkeypatch.setenv("DEMA_REDIS_URL", redis_url)
    monkeypatch.setenv("DEMA_SIGNING_KEY", SIGNING_KEY.decode())
    redis.Redis.from_url(redis_url).flushdb()
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    redis.Redis.from_url(redis_url).flushdb()


@pytest.fixture
def catalog_path(tmp_path: Path, small_catalog: SectionCatalog) -> Path:
    path = tmp_path / "sections.parquet"
    small_catalog.to_parquet(path)
    return path


@pytest.fixture
def ballots_path(tmp_path: Path, small_catalog: SectionCatalog) -> Path:
    path = tmp_path / "ballots.parquet"
    BallotGenerator(DEMA_2026_FIRST_ROUND, seed=7).generate(small_catalog).to_parquet(
        path
    )
    return path
