from dema.domain.election import ElectionNotSetUpError, ElectionRound
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.storage.elections import ElectionRecord
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
            raise ElectionNotSetUpError
        return self.tally


class FakeElections:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.loads: list[tuple[int, ElectionRound]] = []

    async def load(self, year: int, round_: ElectionRound) -> ElectionRecord:
        self.loads.append((year, round_))
        if not self.ready:
            raise ElectionNotSetUpError
        return ElectionRecord(
            election=DEMA_2026_FIRST_ROUND.election,
            polls_close=DEMA_2026_FIRST_ROUND.polls_close,
        )
