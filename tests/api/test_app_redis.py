import pytest
from fastapi.testclient import TestClient
from pydantic import RedisDsn
from redis.asyncio import Redis

from dema.api.app import create_app
from dema.api.schemas import ResultsView
from dema.config import Settings
from dema.domain.ballot import Ballot
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.tallying.outcome import decide
from dema.tallying.redis_store import RedisTallyStore
from dema.wiring import ACTIVE_KEYS
from tests.helpers import expected_tally

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election


async def test_serves_live_tally_from_redis(
    redis_client: Redis,
    redis_url: str,
    small_catalog: SectionCatalog,
    small_ballots: list[Ballot],
) -> None:
    store = RedisTallyStore(redis_client, ACTIVE_KEYS, ELECTION)
    await store.reset(len(small_catalog), small_catalog.total_electorate)
    await store.add_many(small_ballots[:100])
    settings = Settings(redis_url=RedisDsn(redis_url))

    with TestClient(create_app(settings=settings)) as client:
        body = client.get("/results").json()

    tally = expected_tally(small_catalog, small_ballots[:100])
    expected = ResultsView.build(ELECTION, tally, decide(ELECTION, tally))
    assert ResultsView.model_validate(body) == expected
