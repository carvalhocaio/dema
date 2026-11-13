import secrets
from collections.abc import Callable, Mapping
from dataclasses import replace

import psycopg

from dema.sections.synthetic import SyntheticSectionSource
from dema.services.counting import REFERENCE_SCENARIO
from dema.storage.migrator import Migrator
from dema.storage.seed import replace_sections, seed_election

SIGNING_KEY = "DEMA_SIGNING_KEY"
CATALOG_SEED = 2026


def demo_environment(
    environ: Mapping[str, str],
    has_key: bool,
    generate_key: Callable[[], str] = lambda: secrets.token_hex(32),
) -> tuple[dict[str, str], bool]:
    environment = dict(environ) | {"DEMA_ALLOW_RUNS": "true"}
    if has_key:
        return environment, False
    return environment | {SIGNING_KEY: generate_key()}, True


def prepare_database(database_url: str, year: int, sections: int) -> int:
    with psycopg.connect(database_url) as connection:
        Migrator(connection).migrate()
        [(existing,)] = connection.execute("SELECT count(*) FROM sections").fetchall()
        if existing == 0:
            catalog = SyntheticSectionSource(sections, seed=CATALOG_SEED).load()
            replace_sections(connection, catalog)
            existing = len(catalog)
        election = replace(REFERENCE_SCENARIO.election, year=year)
        seed_election(connection, election, REFERENCE_SCENARIO.polls_close)
    return existing
