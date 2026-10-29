from dataclasses import dataclass
from datetime import date

PRESIDENTIAL_NUMBER_RANGE = range(10, 100)


@dataclass(frozen=True, slots=True)
class Candidate:
    number: int
    name: str
    party: str
    birth_date: date

    def __post_init__(self) -> None:
        if self.number not in PRESIDENTIAL_NUMBER_RANGE:
            raise ValueError(f"presidential number must have two digits: {self.number}")
        if not self.name.strip():
            raise ValueError("candidate name must not be blank")
