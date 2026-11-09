from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from psycopg import AsyncConnection
from pydantic import PostgresDsn, RedisDsn
from redis.asyncio import Redis

from dema.api.app import create_app
from dema.api.schemas import ResultsView
from dema.config import Settings
from dema.domain.ballot import Ballot
from dema.domain.election import ElectionRound
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.storage.ballots import PostgresBallotRepository
from dema.streaming.keys import ElectionKeys
from dema.tallying.outcome import decide
from dema.tallying.redis_store import RedisTallyStore
from tests.conftest import TEST_DATABASE
from tests.helpers import expected_tally
from tests.storage.test_ballots import verify_all

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election


async def test_serves_the_live_round_from_redis_and_its_timeline_from_postgres(
    async_connection: AsyncConnection,
    admin_url: str,
    redis_client: Redis,
    redis_url: str,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    counted = small_ballots[:100]
    store = RedisTallyStore(redis_client, ElectionKeys.for_election(ELECTION), ELECTION)
    await store.reset(len(small_catalog), small_catalog.total_electorate)
    await store.add_many(counted)
    await PostgresBallotRepository(async_connection, ELECTION).save_many(
        verify_all(counted)
    )
    database = urlsplit(admin_url)._replace(path=f"/{TEST_DATABASE}").geturl()
    settings = Settings(
        redis_url=RedisDsn(redis_url), database_url=PostgresDsn(database)
    )

    with TestClient(create_app(settings=settings)) as client:
        rounds = client.get("/rounds").json()
        results = client.get("/rounds/1/results").json()
        timeline = client.get("/rounds/1/timeline").json()

    tally = expected_tally(small_catalog, counted)
    assert rounds == [{"round": 1, "status": "live"}]
    assert ResultsView.model_validate(results) == ResultsView.build(
        ELECTION, tally, decide(ELECTION, tally)
    )
    assert timeline["points"][-1]["progress"] == tally.progress


async def test_serves_finished_rounds_from_postgres(
    async_connection: AsyncConnection,
    admin_url: str,
    redis_url: str,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    await PostgresBallotRepository(async_connection, ELECTION).save_many(
        verify_all(small_ballots)
    )
    database = urlsplit(admin_url)._replace(path=f"/{TEST_DATABASE}").geturl()
    settings = Settings(
        redis_url=RedisDsn(redis_url),
        database_url=PostgresDsn(database),
        round=ElectionRound.SECOND,
    )

    with TestClient(create_app(settings=settings)) as client:
        rounds = client.get("/rounds").json()
        results = client.get("/rounds/1/results").json()

    tally = expected_tally(small_catalog, small_ballots)
    assert rounds == [{"round": 1, "status": "final"}]
    assert ResultsView.model_validate(results) == ResultsView.build(
        ELECTION, tally, decide(ELECTION, tally)
    )
