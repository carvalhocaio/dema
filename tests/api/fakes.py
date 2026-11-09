from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.tallying.redis_store import ElectionNotSetUpError
from dema.tallying.tally import Tally


def make_tally(counted_sections: int, keons: int = 600, nico: int = 400) -> Tally:
    votes = dict.fromkeys(DEMA_2026_FIRST_ROUND.election.candidate_numbers, 0)
    votes |= {KEONS.number: keons, NICO.number: nico}
    return Tally(
        nominal_votes=votes,
        blank_votes=20,
        null_votes=30,
        counted_sections=counted_sections,
        counted_electorate=counted_sections * 300,
        total_sections=10,
        total_electorate=3_000,
    )


class FakeSource:
    def __init__(self, tally: Tally | None = None) -> None:
        self.tally = tally

    async def snapshot(self) -> Tally:
        if self.tally is None:
            raise ElectionNotSetUpError("not set up")
        return self.tally
