from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from dema.domain.election import Election, ElectionNotSetUpError, ElectionRound
from dema.domain.state import State
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO
from dema.simulation.runoff import SECOND_ROUND_POLLS_CLOSE
from dema.storage.elections import ElectionRecord
from dema.tallying.states import (
    StateCount,
    StateTally,
    StateTotals,
    build_state_tallies,
)
from dema.tallying.tally import Tally
from dema.tallying.timeline import MinuteCount, Timeline, build_timeline

FIRST_ROUND = DEMA_2026_FIRST_ROUND.election
SECOND_ROUND = Election(year=2026, round=ElectionRound.SECOND, candidates=(KEONS, NICO))
ELECTIONS = {
    ElectionRound.FIRST: ElectionRecord(FIRST_ROUND, DEMA_2026_FIRST_ROUND.polls_close),
    ElectionRound.SECOND: ElectionRecord(SECOND_ROUND, SECOND_ROUND_POLLS_CLOSE),
}


def make_tally(
    counted_sections: int,
    keons: int = 600,
    nico: int = 400,
    election: Election = FIRST_ROUND,
) -> Tally:
    votes = dict.fromkeys(election.candidate_numbers, 0)
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


def make_timeline(election: Election) -> Timeline:
    start = datetime(2026, 10, 4, 20, 0, tzinfo=UTC)
    minutes = [
        MinuteCount(
            minute=start + timedelta(minutes=offset),
            sections=5,
            electorate=1_500,
            blank_votes=10,
            null_votes=15,
            nominal_votes={KEONS.number: keons, NICO.number: 1_000 - keons},
        )
        for offset, keons in ((0, 400), (3, 900))
    ]
    return build_timeline(election, minutes, 10, 3_000)


def make_states(election: Election) -> tuple[StateTally, ...]:
    totals = [StateTotals(State.SP, 10, 3_000), StateTotals(State.ZZ, 2, 100)]
    counts = [
        StateCount(State.SP, 4, 1_200, 10, 15, {KEONS.number: 500, NICO.number: 400})
    ]
    return build_state_tallies(election, totals, counts)


class FakeSource:
    def __init__(self, tally: Tally | None = None) -> None:
        self.tally = tally

    async def snapshot(self) -> Tally:
        if self.tally is None:
            raise ElectionNotSetUpError
        return self.tally


class FakeArchive:
    def __init__(
        self,
        rounds: tuple[ElectionRound, ...] = (ElectionRound.FIRST,),
        tallies: Mapping[ElectionRound, Tally] | None = None,
    ) -> None:
        self.ready = rounds
        self.tallies = dict(tallies or {})
        self.loads: list[tuple[int, ElectionRound]] = []

    async def rounds(self, year: int) -> list[ElectionRound]:
        return list(self.ready)

    async def load(self, year: int, round_: ElectionRound) -> ElectionRecord:
        self.loads.append((year, round_))
        if round_ not in self.ready:
            raise ElectionNotSetUpError
        return ELECTIONS[round_]

    async def tally(self, election: Election) -> Tally:
        return self.tallies[election.round]

    async def states(self, election: Election) -> tuple[StateTally, ...]:
        return make_states(election)

    async def timeline(self, election: Election) -> Timeline:
        return make_timeline(election)
