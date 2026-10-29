from collections.abc import AsyncIterator, Iterator
from urllib.parse import urlsplit

import psycopg
import pytest
import redis
from psycopg import AsyncConnection, sql
from psycopg.conninfo import make_conninfo
from redis.asyncio import Redis

from dema.config import get_settings
from dema.domain.ballot import Ballot
from dema.sections.catalog import SectionCatalog
from dema.sections.synthetic import SyntheticSectionSource
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.migrator import Migrator
from dema.storage.seed import replace_sections, seed_election

TEST_DATABASE = "dema_test"
TEST_REDIS_DB = 15


@pytest.fixture(scope="session")
def admin_url() -> str:
    url = str(get_settings().database_url)
    try:
        psycopg.connect(url, connect_timeout=2).close()
    except psycopg.OperationalError:
        pytest.skip("Postgres is not reachable; run `make up`")
    return url


@pytest.fixture(scope="session")
def database_url(admin_url: str) -> Iterator[str]:
    statement = sql.SQL("DROP DATABASE IF EXISTS {database} WITH (FORCE)")
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(statement.format(database=sql.Identifier(TEST_DATABASE)))
        admin.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DATABASE))
        )
    yield make_conninfo(admin_url, dbname=TEST_DATABASE)
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(statement.format(database=sql.Identifier(TEST_DATABASE)))


@pytest.fixture
def connection(database_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(database_url) as connection:
        connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        connection.commit()
        yield connection


@pytest.fixture
def migrated(connection: psycopg.Connection) -> psycopg.Connection:
    Migrator(connection).migrate()
    return connection


@pytest.fixture(scope="session")
def small_catalog() -> SectionCatalog:
    return SyntheticSectionSource(300, seed=7).load()


@pytest.fixture(scope="session")
def small_ballots(small_catalog: SectionCatalog) -> list[Ballot]:
    generator = BallotGenerator(DEMA_2026_FIRST_ROUND, seed=7)
    return list(generator.generate(small_catalog).in_release_order())


@pytest.fixture
def seeded(
    migrated: psycopg.Connection, small_catalog: SectionCatalog
) -> psycopg.Connection:
    seed_election(migrated, DEMA_2026_FIRST_ROUND)
    replace_sections(migrated, small_catalog)
    return migrated


@pytest.fixture
async def async_connection(
    database_url: str, seeded: psycopg.Connection
) -> AsyncIterator[AsyncConnection]:
    connection = await AsyncConnection.connect(database_url, autocommit=True)
    async with connection:
        yield connection


@pytest.fixture(scope="session")
def redis_url() -> str:
    url = urlsplit(str(get_settings().redis_url))._replace(path=f"/{TEST_REDIS_DB}")
    try:
        redis.Redis.from_url(url.geturl(), socket_connect_timeout=2).ping()
    except redis.ConnectionError:
        pytest.skip("Redis is not reachable; run `make up`")
    return url.geturl()


@pytest.fixture
async def redis_client(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()
