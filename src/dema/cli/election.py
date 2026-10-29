import argparse
import asyncio
from pathlib import Path

import psycopg

from dema.cli.common import Subparsers
from dema.config import get_settings
from dema.sections.catalog import SectionCatalog
from dema.storage.seed import clear_ballots, replace_sections, seed_election
from dema.streaming.stream import BallotStream
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import ACTIVE_KEYS, ACTIVE_SCENARIO, open_redis


def register(commands: Subparsers) -> None:
    election = commands.add_parser("election", help="prepare an election run")
    actions = election.add_subparsers(required=True)
    setup = actions.add_parser("setup", help="seed sections and reset the tally")
    setup.add_argument("catalog", type=Path)
    setup.set_defaults(handler=_setup)


def _setup(args: argparse.Namespace) -> None:
    catalog = SectionCatalog.from_parquet(args.catalog)
    with psycopg.connect(str(get_settings().database_url)) as connection:
        seed_election(connection, ACTIVE_SCENARIO)
        clear_ballots(connection, ACTIVE_SCENARIO)
        replace_sections(connection, catalog)
    asyncio.run(_reset_redis(catalog))
    election = ACTIVE_SCENARIO.election
    print(f"election {election.year}/{election.round} ready")
    print(f"sections:   {len(catalog):>13,}")
    print(f"electorate: {catalog.total_electorate:>13,}")


async def _reset_redis(catalog: SectionCatalog) -> None:
    async with open_redis(get_settings()) as redis:
        await BallotStream(redis, ACTIVE_KEYS).clear()
        store = RedisTallyStore(redis, ACTIVE_KEYS, ACTIVE_SCENARIO.election)
        await store.reset(len(catalog), catalog.total_electorate)
