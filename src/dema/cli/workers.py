import argparse
import asyncio
import logging
import multiprocessing
import signal
import socket

from dema.cli.common import Subparsers
from dema.config import get_settings
from dema.domain.election import ElectionNotSetUpError
from dema.runtime.active import ActiveRuns
from dema.wiring import build_signer, open_database, open_redis
from dema.workers.lanes import ActiveLanes
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
    try:
        asyncio.run(_work_async(consumer))
    except ElectionNotSetUpError as error:
        raise SystemExit(f"dema: {error}") from error


async def _work_async(consumer: str) -> None:
    settings = get_settings()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)
    async with open_redis(settings) as redis, open_database(settings) as connection:
        active = ActiveRuns(redis, connection)
        await active.current()
        worker = TallyWorker(
            lanes=ActiveLanes(active, redis, connection),
            signer=build_signer(settings),
            consumer=consumer,
            batch_size=settings.batch_size,
        )
        await worker.run(stop)
