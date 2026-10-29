from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable

import psycopg

MIGRATIONS = files("dema.storage") / "migrations"
LOCK_ID = 20261004


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    statements: str


def discover(directory: Traversable = MIGRATIONS) -> list[Migration]:
    scripts = sorted(
        (entry for entry in directory.iterdir() if entry.name.endswith(".sql")),
        key=lambda entry: entry.name,
    )
    return [
        Migration(
            version=script.name.removesuffix(".sql"), statements=script.read_text()
        )
        for script in scripts
    ]


class Migrator:
    def __init__(
        self, connection: psycopg.Connection, migrations: list[Migration] | None = None
    ) -> None:
        self._connection = connection
        self._migrations = discover() if migrations is None else migrations

    def migrate(self) -> list[str]:
        with self._connection.transaction():
            self._connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version text PRIMARY KEY, "
                "applied_at timestamptz NOT NULL DEFAULT now())"
            )
            applied = self._applied_versions()
            pending = [m for m in self._migrations if m.version not in applied]
            for migration in pending:
                self._apply(migration)
        return [migration.version for migration in pending]

    def _applied_versions(self) -> set[str]:
        rows = self._connection.execute("SELECT version FROM schema_migrations")
        return {version for (version,) in rows}

    def _apply(self, migration: Migration) -> None:
        self._connection.execute(migration.statements.encode())
        self._connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (%s)", (migration.version,)
        )
