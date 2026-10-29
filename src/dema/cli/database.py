import argparse

import psycopg

from dema.cli.common import Subparsers
from dema.config import get_settings
from dema.storage.migrator import Migrator


def register(commands: Subparsers) -> None:
    database = commands.add_parser("db", help="manage the database")
    actions = database.add_subparsers(required=True)
    migrate = actions.add_parser("migrate", help="apply pending migrations")
    migrate.set_defaults(handler=_migrate)


def _migrate(_: argparse.Namespace) -> None:
    with psycopg.connect(str(get_settings().database_url)) as connection:
        applied = Migrator(connection).migrate()
    for version in applied:
        print(f"applied {version}")
    if not applied:
        print("database is up to date")
