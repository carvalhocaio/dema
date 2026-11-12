import argparse
import asyncio
from contextlib import suppress

from dema.cli.common import Subparsers, format_progress
from dema.config import get_settings
from dema.runtime.active import ActiveRuns
from dema.storage.ballots import PostgresBallotRepository
from dema.tallying.outcome import decide
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import open_database, open_redis


def register(commands: Subparsers) -> None:
    tally = commands.add_parser("tally", help="inspect the live tally")
    actions = tally.add_subparsers(required=True)

    watch = actions.add_parser("watch", help="print progress until counting ends")
    watch.add_argument("--interval", type=float, default=1.0)
    watch.set_defaults(handler=_watch)

    rebuild = actions.add_parser("rebuild", help="rebuild Redis from Postgres")
    rebuild.set_defaults(handler=_rebuild)


def _watch(args: argparse.Namespace) -> None:
    with suppress(KeyboardInterrupt):
        asyncio.run(_watch_async(args.interval))


async def _watch_async(interval: float) -> None:
    settings = get_settings()
    async with open_database(settings) as connection, open_redis(settings) as redis:
        record = await ActiveRuns(redis, connection).current()
        election = record.election
        store = RedisTallyStore(redis, record.keys, election)
        last_counted = -1
        while True:
            tally = await store.snapshot()
            if tally.counted_sections != last_counted:
                last_counted = tally.counted_sections
                print(format_progress(tally, decide(election, tally)), flush=True)
            if tally.is_complete:
                return
            await asyncio.sleep(interval)


def _rebuild(_: argparse.Namespace) -> None:
    counted = asyncio.run(_rebuild_async())
    print(f"restored {counted:,} counted sections")


async def _rebuild_async() -> int:
    settings = get_settings()
    async with open_database(settings) as connection, open_redis(settings) as redis:
        record = await ActiveRuns(redis, connection).current()
        repository = PostgresBallotRepository(
            connection, record.election, record.run.id
        )
        await repository.rebuild_rollup()
        tally = await repository.tally()
        store = RedisTallyStore(redis, record.keys, record.election)
        await store.restore(tally, await repository.counted_sections())
    return tally.counted_sections
