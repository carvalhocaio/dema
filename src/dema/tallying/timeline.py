from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from dema.domain.election import Election
from dema.tallying.outcome import Outcome, Verdict, decide
from dema.tallying.tally import Tally


@dataclass(frozen=True, slots=True)
class MinuteCount:
    minute: datetime
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
class TimelinePoint:
    at: datetime
    tally: Tally
    outcome: Outcome


@dataclass(frozen=True, slots=True)
class Timeline:
    points: tuple[TimelinePoint, ...]

    @property
    def decided_at(self) -> datetime | None:
        return next(
            (p.at for p in self.points if p.outcome.verdict is not Verdict.UNDECIDED),
            None,
        )


def build_timeline(
    election: Election,
    minutes: Sequence[MinuteCount],
    total_sections: int,
    total_electorate: int,
) -> Timeline:
    votes: Counter[int] = Counter(dict.fromkeys(election.candidate_numbers, 0))
    sections = electorate = blank = null = 0
    points: list[TimelinePoint] = []
    for count in sorted(minutes, key=lambda count: count.minute):
        votes.update(count.nominal_votes)
        sections += count.sections
        electorate += count.electorate
        blank += count.blank_votes
        null += count.null_votes
        tally = Tally(
            nominal_votes=votes,
            blank_votes=blank,
            null_votes=null,
            counted_sections=sections,
            counted_electorate=electorate,
            total_sections=total_sections,
            total_electorate=total_electorate,
        )
        points.append(TimelinePoint(count.minute, tally, decide(election, tally)))
    return Timeline(tuple(points))
