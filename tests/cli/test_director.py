import asyncio
import os
import signal

import psycopg
import pytest

from dema.cli import director, main
from dema.config import get_settings
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.streaming.keys import CONTROL_STREAM
from dema.wiring import open_redis


def test_run_starts_the_async_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_run_async() -> None:
        calls.append("ran")

    monkeypatch.setattr(director, "_run_async", fake_run_async)

    main(["director", "run"])

    assert calls == ["ran"]


async def interrupt_once_listening() -> None:
    async with open_redis(get_settings()) as redis:
        while not await redis.exists(CONTROL_STREAM):
            await asyncio.sleep(0.05)
    os.kill(os.getpid(), signal.SIGINT)


@pytest.mark.integration
async def test_run_async_listens_until_interrupted(
    migrated: psycopg.Connection, cli_env: None
) -> None:
    watcher = asyncio.create_task(interrupt_once_listening())

    await asyncio.wait_for(director._run_async(), timeout=30)
    await watcher

    async with open_redis(get_settings()) as redis:
        groups = await redis.xinfo_groups(CONTROL_STREAM)
    assert [group["name"] for group in groups] == [b"director"]


@pytest.mark.integration
async def test_seeder_writes_the_election_to_the_database(
    migrated: psycopg.Connection, database_url: str
) -> None:
    await director.seeder(database_url)(
        DEMA_2026_FIRST_ROUND.election, DEMA_2026_FIRST_ROUND.polls_close
    )

    [(count,)] = migrated.execute("SELECT count(*) FROM candidates").fetchall()
    assert count == len(DEMA_2026_FIRST_ROUND.election.candidates)
