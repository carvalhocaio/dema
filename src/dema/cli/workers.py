import argparse
import asyncio
import logging
import multiprocessing
import signal
import socket

from dema.cli.common import Subparsers
from dema.config import get_settings
from dema.storage.ballots import PostgresBallotRepository
from dema.streaming.stream import BallotStream
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import (
    ACTIVE_KEYS,
    ACTIVE_SCENARIO,
    build_signer,
    open_database,
    open_redis,
)
from dema.workers.tally_worker import TallyWorker


def register(commands: Subparsers) -> None:
    workers = commands.add_parser("workers", help="run tallying workers")
    actions = workers.add_subparsers(required=True)
    run = actions.add_parser("run", help="consume ballots until interrupted")
    run.add_argument("--processes", type=int, default=1)
    run.set_defaults(handler=_run)


def _run(args: argparse.Namespace) -> None:
    names = [f"{socket.gethostname()}-{index}" for index in range(args.processes)]
    if len(names) == 1:
        _work(names[0])
        return
    context = multiprocessing.get_context("spawn")
    processes = [context.Process(target=_work, args=(name,)) for name in names]
    for process in processes:
        process.start()
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        for process in processes:
            process.join()


def _work(consumer: str) -> None:
    logging.basicConfig(
        level=logging.INFO, format=f"%(asctime)s {consumer} %(levelname)s %(message)s"
    )
    asyncio.run(_work_async(consumer))


async def _work_async(consumer: str) -> None:
    settings = get_settings()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)
    election = ACTIVE_SCENARIO.election
    async with open_redis(settings) as redis, open_database(settings) as connection:
        worker = TallyWorker(
            stream=BallotStream(redis, ACTIVE_KEYS),
            signer=build_signer(settings),
            repository=PostgresBallotRepository(connection, election),
            store=RedisTallyStore(redis, ACTIVE_KEYS, election),
            consumer=consumer,
            batch_size=settings.batch_size,
        )
        logging.info("consuming %s", ACTIVE_KEYS.ballots)
        await worker.run(stop)
