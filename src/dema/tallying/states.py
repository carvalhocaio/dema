from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from dema.domain.election import Election
from dema.domain.state import State
from dema.tallying.outcome import decide
from dema.tallying.tally import Tally


@dataclass(frozen=True, slots=True)
class StateCount:
    state: State
    sections: int
    electorate: int
    blank_votes: int
    null_votes: int
    nominal_votes: Mapping[int, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "nominal_votes", MappingProxyType(dict(self.nominal_votes))
        )


@dataclass(frozen=True, slots=True)
class StateTotals:
    state: State
    sections: int
    electorate: int


@dataclass(frozen=True, slots=True)
class StateTally:
    state: State
    tally: Tally
    leader: int | None


def build_state_tallies(
    election: Election,
    totals: Sequence[StateTotals],
    counts: Sequence[StateCount],
) -> tuple[StateTally, ...]:
    counted = {count.state: count for count in counts}
    result = []
    for total in sorted(totals, key=lambda total: total.state):
        count = counted.get(total.state)
        votes = dict.fromkeys(election.candidate_numbers, 0)
        if count:
            votes |= count.nominal_votes
        tally = Tally(
            nominal_votes=votes,
            blank_votes=count.blank_votes if count else 0,
            null_votes=count.null_votes if count else 0,
            counted_sections=count.sections if count else 0,
            counted_electorate=count.electorate if count else 0,
            total_sections=total.sections,
            total_electorate=total.electorate,
        )
        leader = decide(election, tally).leader
        result.append(
            StateTally(
                total.state, tally, leader.candidate.number if leader.votes else None
            )
        )
    return tuple(result)
