from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from dema.config import get_settings

TEST_DATABASE = "dema_test"


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
