import pytest
from redis.asyncio import Redis

from dema.domain.ballot import Ballot
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.streaming.keys import ElectionKeys
from dema.tallying.redis_store import ElectionNotSetUpError, RedisTallyStore
from dema.tallying.validation import UnknownCandidateError
from tests.factories import make_ballot
from tests.helpers import expected_tally

pytestmark = pytest.mark.integration

ELECTION = DEMA_2026_FIRST_ROUND.election
KEYS = ElectionKeys.for_election(ELECTION)


@pytest.fixture
async def store(redis_client: Redis, small_catalog: SectionCatalog) -> RedisTallyStore:
    store = RedisTallyStore(redis_client, KEYS, ELECTION)
    await store.reset(len(small_catalog), small_catalog.total_electorate)
    return store


async def test_requires_setup_before_snapshot(redis_client: Redis) -> None:
    with pytest.raises(ElectionNotSetUpError):
        await RedisTallyStore(redis_client, KEYS, ELECTION).snapshot()


async def test_starts_empty_after_reset(
    store: RedisTallyStore, small_catalog: SectionCatalog
) -> None:
    assert await store.snapshot() == expected_tally(small_catalog, [])


async def test_matches_in_memory_tally(
    store: RedisTallyStore, small_catalog: SectionCatalog, small_ballots: list[Ballot]
) -> None:
    assert await store.add_many(small_ballots) == len(small_ballots)

    assert await store.snapshot() == expected_tally(small_catalog, small_ballots)


async def test_counts_each_section_once(
    store: RedisTallyStore, small_catalog: SectionCatalog, small_ballots: list[Ballot]
) -> None:
    await store.add_many(small_ballots[:20])

    assert await store.add_many(small_ballots[:40]) == 20
    assert await store.snapshot() == expected_tally(small_catalog, small_ballots[:40])


async def test_rejects_unknown_candidates(store: RedisTallyStore) -> None:
    with pytest.raises(UnknownCandidateError):
        await store.add_many([make_ballot(nominal_votes={13: 10})])


async def test_restores_snapshot_and_counted_sections(
    store: RedisTallyStore, small_catalog: SectionCatalog, small_ballots: list[Ballot]
) -> None:
    half = small_ballots[: len(small_ballots) // 2]
    tally = expected_tally(small_catalog, half)

    await store.restore(tally, [str(ballot.section) for ballot in half])

    assert await store.snapshot() == tally
    assert await store.add_many(half) == 0
