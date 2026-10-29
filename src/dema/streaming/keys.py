from dataclasses import dataclass

from dema.domain.election import Election

CONSUMER_GROUP = "tallying"


@dataclass(frozen=True, slots=True)
class ElectionKeys:
    prefix: str

    @classmethod
    def for_election(cls, election: Election) -> "ElectionKeys":
        return cls(f"dema:{election.year}:{election.round}")

    @property
    def ballots(self) -> str:
        return f"{self.prefix}:ballots"

    @property
    def rejected(self) -> str:
        return f"{self.prefix}:rejected"

    @property
    def counted(self) -> str:
        return f"{self.prefix}:counted"

    @property
    def tally(self) -> str:
        return f"{self.prefix}:tally"

    @property
    def meta(self) -> str:
        return f"{self.prefix}:meta"
