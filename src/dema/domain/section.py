from dataclasses import dataclass

from dema.domain.state import State


@dataclass(frozen=True, slots=True, order=True)
class SectionKey:
    state: State
    municipality_code: int
    zone: int
    number: int

    def __str__(self) -> str:
        return (
            f"{self.state}-{self.municipality_code:05d}"
            f"-{self.zone:04d}-{self.number:04d}"
        )

    @classmethod
    def parse(cls, raw: str) -> "SectionKey":
        state, municipality, zone, number = raw.split("-")
        return cls(State(state), int(municipality), int(zone), int(number))


@dataclass(frozen=True, slots=True)
class Section:
    key: SectionKey
    eligible_voters: int

    def __post_init__(self) -> None:
        if self.eligible_voters <= 0:
            raise ValueError(f"section {self.key} must have eligible voters")
