import psycopg
import pytest

from dema.storage.migrator import Migration, Migrator, discover

pytestmark = pytest.mark.integration


def test_discovers_packaged_migrations_in_order() -> None:
    versions = [migration.version for migration in discover()]

    assert versions[0] == "0001_initial_schema"
    assert versions == sorted(versions)


def test_applies_pending_migrations_once(connection: psycopg.Connection) -> None:
    migrator = Migrator(connection)

    assert migrator.migrate() == ["0001_initial_schema"]
    assert migrator.migrate() == []


def test_applies_only_new_migrations(connection: psycopg.Connection) -> None:
    first = Migration("0001_first", "CREATE TABLE crops (id int)")
    second = Migration("0002_second", "ALTER TABLE crops ADD COLUMN bales int")
    Migrator(connection, [first]).migrate()

    assert Migrator(connection, [first, second]).migrate() == ["0002_second"]


def test_rolls_back_failed_migration(connection: psycopg.Connection) -> None:
    broken = [
        Migration("0001_ok", "CREATE TABLE crops (id int)"),
        Migration("0002_broken", "CREATE TABLE crops (id int)"),
    ]

    with pytest.raises(psycopg.errors.DuplicateTable):
        Migrator(connection, broken).migrate()

    exists = connection.execute("SELECT to_regclass('crops')").fetchone()
    assert exists == (None,)
