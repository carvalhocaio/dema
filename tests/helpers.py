from redis.asyncio import Redis

from dema.domain.ballot import Ballot
from dema.sections.catalog import SectionCatalog
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.streaming.keys import ElectionKeys
from dema.tallying.memory import InMemoryTallyStore
from dema.tallying.tally import Tally

SIGNING_KEY = b"clancy-is-watching-from-the-trench"


def expected_tally(catalog: SectionCatalog, ballots: list[Ballot]) -> Tally:
    store = InMemoryTallyStore(
        DEMA_2026_FIRST_ROUND.election,
        total_sections=len(catalog),
        total_electorate=catalog.total_electorate,
    )
    for ballot in ballots:
        store.add(ballot)
    return store.snapshot()


async def rejected_entries(redis: Redis, keys: ElectionKeys) -> list[dict]:
    entries = await redis.xrange(keys.rejected) or []
    return [fields for _, fields in entries if fields]
