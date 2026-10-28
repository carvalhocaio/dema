from dataclasses import dataclass
from enum import IntEnum

from dema.domain.candidate import Candidate


class ElectionRound(IntEnum):
    FIRST = 1
    SECOND = 2


@dataclass(frozen=True, slots=True)
class Election:
    year: int
    round: ElectionRound
    candidates: tuple[Candidate, ...]

    def __post_init__(self) -> None:
        numbers = [candidate.number for candidate in self.candidates]
        if len(numbers) != len(set(numbers)):
            raise ValueError("candidate numbers must be unique")
        if self.round is ElectionRound.SECOND and len(self.candidates) != 2:
            raise ValueError("second round requires exactly two candidates")
        if len(self.candidates) < 2:
            raise ValueError("an election requires at least two candidates")

    @property
    def candidate_numbers(self) -> frozenset[int]:
        return frozenset(candidate.number for candidate in self.candidates)

    def candidate(self, number: int) -> Candidate:
        for candidate in self.candidates:
            if candidate.number == number:
                return candidate
        raise KeyError(number)
