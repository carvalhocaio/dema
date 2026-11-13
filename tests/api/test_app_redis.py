from urllib.parse import urlsplit

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import AsyncConnection
from pydantic import PostgresDsn, RedisDsn, SecretStr
from redis.asyncio import Redis

from dema.api.app import create_app
from dema.api.schemas import ResultsView
from dema.config import Settings
from dema.domain.ballot import Ballot
from dema.domain.election import Election, ElectionRound
from dema.domain.run import Run
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE
from dema.storage.ballots import PostgresBallotRepository
from dema.storage.runs import RunRepository
from dema.storage.seed import seed_election
from dema.streaming.keys import CONTROL_STREAM, ElectionKeys
from dema.tallying.outcome import decide
from dema.tallying.redis_store import RedisTallyStore
from tests.conftest import TEST_DATABASE
from tests.helpers import SIGNING_KEY, expected_tally
from tests.storage.test_ballots import verify_all

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election
RUNOFF = Election(year=2026, round=ElectionRound.SECOND, candidates=(KEONS, NICO))


def settings_for(
    admin_url: str,
    redis_url: str,
    allow_runs: bool = False,
    signing_key: bytes | None = None,
) -> Settings:
    database = urlsplit(admin_url)._replace(path=f"/{TEST_DATABASE}").geturl()
    return Settings(
        redis_url=RedisDsn(redis_url),
        database_url=PostgresDsn(database),
        allow_runs=allow_runs,
        signing_key=None if signing_key is None else SecretStr(signing_key.decode()),
    )


async def test_serves_the_live_round_from_redis_and_its_timeline_from_postgres(
    async_connection: AsyncConnection,
    first_run: Run,
    admin_url: str,
    redis_client: Redis,
    redis_url: str,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    counted = small_ballots[:100]
    keys = ElectionKeys.for_run(first_run)
    store = RedisTallyStore(redis_client, keys, ELECTION)
    await store.reset(len(small_catalog), small_catalog.total_electorate)
    await store.add_many(counted)
    repository = PostgresBallotRepository(async_connection, ELECTION, first_run.id)
    await repository.save_many(verify_all(counted))

    with TestClient(create_app(settings_for(admin_url, redis_url))) as client:
        rounds = client.get("/rounds").json()
        results = client.get("/rounds/1/results").json()
        timeline = client.get("/rounds/1/timeline").json()

    tally = expected_tally(small_catalog, counted)
    assert rounds == [{"round": 1, "status": "live"}]
    assert ResultsView.model_validate(results) == ResultsView.build(
        ELECTION, tally, decide(ELECTION, tally), first_run
    )
    assert timeline["points"][-1]["progress"] == tally.progress


async def test_serves_the_finished_first_round_while_the_runoff_is_live(
    seeded: psycopg.Connection,
    async_connection: AsyncConnection,
    first_run: Run,
    admin_url: str,
    redis_url: str,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    repository = PostgresBallotRepository(async_connection, ELECTION, first_run.id)
    await repository.save_many(verify_all(small_ballots))
    seed_election(seeded, RUNOFF, SECOND_ROUND_POLLS_CLOSE)
    runs = RunRepository(async_connection)
    runoff = await runs.create(
        2026, ElectionRound.SECOND, 7, [KEONS.number, NICO.number], first_run.id
    )
    await runs.activate(runoff.id)

    with TestClient(create_app(settings_for(admin_url, redis_url))) as client:
        rounds = client.get("/rounds").json()
        results = client.get("/rounds/1/results").json()
        states = client.get("/rounds/1/states").json()

    tally = expected_tally(small_catalog, small_ballots)
    assert rounds == [
        {"round": 1, "status": "final"},
        {"round": 2, "status": "live"},
    ]
    counted = sum(state["counted_sections"] for state in states["states"])
    assert counted == len(small_ballots)
    assert ResultsView.model_validate(results) == ResultsView.build(
        ELECTION, tally, decide(ELECTION, tally), first_run
    )


async def test_requests_a_new_count_through_the_control_stream(
    async_connection: AsyncConnection,
    first_run: Run,
    admin_url: str,
    redis_client: Redis,
    redis_url: str,
) -> None:
    settings = settings_for(admin_url, redis_url, allow_runs=True)

    with TestClient(create_app(settings)) as client:
        created = client.post("/runs", json={"seed": 123, "speed": 300}).json()
        current = client.get("/runs/current").json()

    assert created["round"] == 1
    assert created["seed"] == 123
    assert created["status"] == "preparing"
    assert current["run"]["id"] == first_run.id
    [(_, fields)] = await redis_client.xrange(CONTROL_STREAM) or []
    assert fields == {b"run": str(created["id"]).encode(), b"speed": b"300.0"}


async def test_audits_a_counted_section_with_the_api_signing_key(
    async_connection: AsyncConnection,
    first_run: Run,
    admin_url: str,
    redis_url: str,
    small_ballots: list[Ballot],
) -> None:
    ballot = small_ballots[0]
    repository = PostgresBallotRepository(async_connection, ELECTION, first_run.id)
    await repository.save_many(verify_all([ballot]))
    path = f"/rounds/1/sections/{ballot.section}"

    signed = settings_for(admin_url, redis_url, signing_key=SIGNING_KEY)
    with TestClient(create_app(signed)) as client:
        verified = client.get(path).json()
    with TestClient(create_app(settings_for(admin_url, redis_url))) as client:
        unchecked = client.get(path).json()

    assert verified["section"] == str(ballot.section)
    assert verified["verified"] is True
    assert unchecked["verified"] is None
