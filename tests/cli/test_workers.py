import asyncio
import os
import signal
import socket
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest

from dema.cli import main, workers
from dema.config import get_settings
from dema.domain.ballot import Ballot
from dema.integrity.signer import BallotSigner
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.streaming.keys import ElectionKeys
from dema.streaming.stream import BallotStream
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import open_redis
from tests.helpers import SIGNING_KEY, expected_tally

ELECTION = DEMA_2026_FIRST_ROUND.election
KEYS = ElectionKeys.for_election(ELECTION)


class FakeProcess:
    def __init__(
        self, log: list[str], interrupt: list[bool], target: Callable, args: tuple
    ) -> None:
        self._log = log
        self._interrupt = interrupt
        self.target = target
        self.name = args[0]

    def start(self) -> None:
        self._log.append(f"start {self.name}")

    def join(self) -> None:
        self._log.append(f"join {self.name}")
        if self._interrupt:
            self._interrupt.pop()
            raise KeyboardInterrupt


def fake_spawn(
    monkeypatch: pytest.MonkeyPatch, interrupt: bool
) -> tuple[list[str], list[str]]:
    log: list[str] = []
    methods: list[str] = []
    pending = [True] if interrupt else []

    def get_context(method: str) -> SimpleNamespace:
        methods.append(method)
        return SimpleNamespace(
            Process=lambda target, args: FakeProcess(log, pending, target, args)
        )

    monkeypatch.setattr(workers.multiprocessing, "get_context", get_context)
    return log, methods


def test_single_process_works_in_the_foreground(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    consumers: list[str] = []
    monkeypatch.setattr(workers, "_work", consumers.append)

    main(["workers", "run"])

    assert consumers == [f"{socket.gethostname()}-0"]


def test_spawns_and_joins_one_process_per_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log, methods = fake_spawn(monkeypatch, interrupt=False)

    main(["workers", "run", "--processes", "2"])

    host = socket.gethostname()
    assert methods == ["spawn"]
    assert log == [
        f"start {host}-0",
        f"start {host}-1",
        f"join {host}-0",
        f"join {host}-1",
    ]


def test_ctrl_c_waits_for_every_process_to_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log, _ = fake_spawn(monkeypatch, interrupt=True)

    main(["workers", "run", "--processes", "2"])

    host = socket.gethostname()
    assert log[2:] == [f"join {host}-0", f"join {host}-0", f"join {host}-1"]


def test_work_runs_the_async_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    consumers: list[str] = []

    async def fake_work_async(consumer: str) -> None:
        consumers.append(consumer)

    monkeypatch.setattr(workers, "_work_async", fake_work_async)

    workers._work("worker-x")

    assert consumers == ["worker-x"]


async def interrupt_when_counted(total: int) -> None:
    async with open_redis(get_settings()) as redis:
        store = RedisTallyStore(redis, KEYS, ELECTION)
        while (await store.snapshot()).counted_sections < total:
            await asyncio.sleep(0.05)
    os.kill(os.getpid(), signal.SIGINT)


@pytest.mark.integration
async def test_work_async_tallies_until_interrupted(
    migrated: psycopg.Connection,
    cli_env: None,
    catalog_path: Path,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    await asyncio.to_thread(main, ["election", "setup", str(catalog_path)])
    signer = BallotSigner(SIGNING_KEY)
    async with open_redis(get_settings()) as redis:
        stream = BallotStream(redis, KEYS)
        await stream.ensure_group()
        await stream.publish([signer.sign(ballot) for ballot in small_ballots])

    watcher = asyncio.create_task(interrupt_when_counted(len(small_ballots)))
    await asyncio.wait_for(workers._work_async("worker-test"), timeout=30)
    await watcher

    async with open_redis(get_settings()) as redis:
        tally = await RedisTallyStore(redis, KEYS, ELECTION).snapshot()
    assert tally == expected_tally(small_catalog, small_ballots)
