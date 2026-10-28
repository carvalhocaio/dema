from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from dema.domain.section import SectionKey


@dataclass(frozen=True, slots=True)
class Ballot:
    section: SectionKey
    eligible_voters: int
    nominal_votes: Mapping[int, int]
    blank_votes: int
    null_votes: int
    issued_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "nominal_votes", MappingProxyType(dict(self.nominal_votes))
        )
        counts = (*self.nominal_votes.values(), self.blank_votes, self.null_votes)
        if any(count < 0 for count in counts):
            raise ValueError(f"ballot {self.section} has negative counts")
        if self.turnout > self.eligible_voters:
            raise ValueError(f"ballot {self.section} turnout exceeds electorate")

    @property
    def valid_votes(self) -> int:
        return sum(self.nominal_votes.values())

    @property
    def turnout(self) -> int:
        return self.valid_votes + self.blank_votes + self.null_votes

    @property
    def abstentions(self) -> int:
        return self.eligible_voters - self.turnout
