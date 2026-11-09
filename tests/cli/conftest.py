from collections.abc import Iterator
from pathlib import Path

import pytest
import redis

from dema.config import get_settings
from dema.sections.catalog import SectionCatalog
from dema.simulation.ballots import SimulatedBallots
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.simulation.runoff import RunoffGenerator
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


@pytest.fixture
def runoff_path(tmp_path: Path, ballots_path: Path) -> Path:
    first_round = SimulatedBallots.from_parquet(ballots_path)
    runoff = RunoffGenerator(DEMA_2026_FIRST_ROUND, seed=7).generate(
        first_round, DEMA_2026_FIRST_ROUND.election
    )
    path = tmp_path / "runoff.parquet"
    runoff.ballots.to_parquet(path)
    return path
