import argparse
import asyncio
import logging
import signal
from datetime import datetime

from dema.cli.common import Subparsers
from dema.config import get_settings
from dema.director.control import ControlStream
from dema.director.counter import RunCounter, SeedElection
from dema.director.service import Director
from dema.domain.election import Election
from dema.storage.seed import seed_election_at
from dema.wiring import build_signer, open_database, open_redis


def register(commands: Subparsers) -> None:
    director = commands.add_parser("director", help="run counts on demand")
    actions = director.add_subparsers(required=True)
    run = actions.add_parser("run", help="serve new-count requests until interrupted")
    run.set_defaults(handler=_run)


def seeder(database_url: str) -> SeedElection:
    async def seed(election: Election, polls_close: datetime) -> None:
        await asyncio.to_thread(seed_election_at, database_url, election, polls_close)

    return seed


def _run(_: argparse.Namespace) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s director %(levelname)s %(message)s"
    )
    asyncio.run(_run_async())


async def _run_async() -> None:
    settings = get_settings()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)

    async with open_database(settings) as connection, open_redis(settings) as redis:
        counter = RunCounter(
            redis,
            connection,
            build_signer(settings),
            seeder(str(settings.database_url)),
            settings.speed_factor,
            settings.batch_size,
        )
        await Director(ControlStream(redis), counter).run(stop)
