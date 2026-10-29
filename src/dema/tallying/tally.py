from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Tally:
    nominal_votes: Mapping[int, int]
    blank_votes: int
    null_votes: int
    counted_sections: int
    counted_electorate: int
    total_sections: int
    total_electorate: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "nominal_votes", MappingProxyType(dict(self.nominal_votes))
        )
        if not 0 <= self.counted_sections <= self.total_sections:
            raise ValueError("counted sections must be within the total")
        if not 0 <= self.counted_electorate <= self.total_electorate:
            raise ValueError("counted electorate must be within the total")

    @property
    def valid_votes(self) -> int:
        return sum(self.nominal_votes.values())

    @property
    def turnout(self) -> int:
        return self.valid_votes + self.blank_votes + self.null_votes

    @property
    def abstentions(self) -> int:
        return self.counted_electorate - self.turnout

    @property
    def remaining_electorate(self) -> int:
        return self.total_electorate - self.counted_electorate

    @property
    def progress(self) -> float:
        return self.counted_sections / self.total_sections if self.total_sections else 0

    @property
    def is_complete(self) -> bool:
        return self.counted_sections == self.total_sections

    def share(self, number: int) -> float:
        valid = self.valid_votes
        return self.nominal_votes[number] / valid if valid else 0.0
