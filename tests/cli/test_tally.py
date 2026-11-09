import asyncio
from pathlib import Path

import psycopg
import pytest

from dema.cli import main, tally
from dema.config import get_settings
from dema.domain.ballot import Ballot
from dema.integrity.signer import BallotSigner
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.ballots import PostgresBallotRepository
from dema.streaming.keys import ElectionKeys
from dema.tallying.redis_store import RedisTallyStore
from dema.tallying.tally import Tally
from dema.wiring import open_database, open_redis
from tests.helpers import SIGNING_KEY, expected_tally

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election
KEYS = ElectionKeys.for_election(ELECTION)
WATCH_INTERVAL = 0.25


async def add_to_redis(ballots: list[Ballot]) -> None:
    async with open_redis(get_settings()) as redis:
        await RedisTallyStore(redis, KEYS, ELECTION).add_many(ballots)


async def snapshot() -> Tally:
    async with open_redis(get_settings()) as redis:
        return await RedisTallyStore(redis, KEYS, ELECTION).snapshot()


async def save_to_postgres(ballots: list[Ballot]) -> None:
    signer = BallotSigner(SIGNING_KEY)
    verified = [signer.verify(signer.sign(ballot)) for ballot in ballots]
    async with open_database(get_settings()) as connection:
        await PostgresBallotRepository(connection, ELECTION).save_many(verified)


def test_watch_prints_changes_until_counting_ends(
    migrated: psycopg.Connection,
    cli_env: None,
    catalog_path: Path,
    small_ballots: list[Ballot],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["election", "setup", str(catalog_path)])
    capsys.readouterr()
    naps: list[float] = []
    real_sleep = asyncio.sleep

    async def count_everything_on_second_nap(seconds: float) -> None:
        if seconds != WATCH_INTERVAL:
            await real_sleep(seconds)
            return
        naps.append(seconds)
        if len(naps) == 2:
            await add_to_redis(small_ballots)

    monkeypatch.setattr(tally.asyncio, "sleep", count_everything_on_second_nap)

    main(["tally", "watch", "--interval", str(WATCH_INTERVAL)])

    lines = capsys.readouterr().out.splitlines()
    assert naps == [WATCH_INTERVAL, WATCH_INTERVAL]
    assert len(lines) == 2
    assert lines[0].lstrip().startswith("0.0%")
    assert lines[1].lstrip().startswith("100.0%")
    assert lines[1].endswith("[runoff]")


def test_rebuild_restores_redis_from_postgres(
    migrated: psycopg.Connection,
    cli_env: None,
    catalog_path: Path,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["election", "setup", str(catalog_path)])
    asyncio.run(save_to_postgres(small_ballots[:40]))
    migrated.execute("DELETE FROM minute_votes; DELETE FROM minute_totals")
    migrated.commit()
    capsys.readouterr()

    main(["tally", "rebuild"])

    assert capsys.readouterr().out == "restored 40 counted sections\n"
    [(rolled_up,)] = migrated.execute(
        "SELECT sum(sections) FROM minute_totals"
    ).fetchall()
    assert rolled_up == 40
    assert asyncio.run(snapshot()) == expected_tally(small_catalog, small_ballots[:40])
