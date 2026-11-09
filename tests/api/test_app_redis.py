import pytest
from fastapi.testclient import TestClient
from pydantic import PostgresDsn, RedisDsn
from redis.asyncio import Redis

from dema.api.app import create_app
from dema.api.schemas import ResultsView
from dema.config import Settings
from dema.domain.ballot import Ballot
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.streaming.keys import ElectionKeys
from dema.tallying.outcome import decide
from dema.tallying.redis_store import RedisTallyStore
from tests.helpers import expected_tally

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election


async def test_serves_live_tally_of_the_election_stored_in_postgres(
    redis_client: Redis,
    redis_url: str,
    database_dsn: str,
    async_connection: object,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    store = RedisTallyStore(redis_client, ElectionKeys.for_election(ELECTION), ELECTION)
    await store.reset(len(small_catalog), small_catalog.total_electorate)
    await store.add_many(small_ballots[:100])
    settings = Settings(
        redis_url=RedisDsn(redis_url), database_url=PostgresDsn(database_dsn)
    )

    with TestClient(create_app(settings)) as client:
        body = client.get("/results").json()

    tally = expected_tally(small_catalog, small_ballots[:100])
    expected = ResultsView.build(ELECTION, tally, decide(ELECTION, tally))
    assert ResultsView.model_validate(body) == expected
