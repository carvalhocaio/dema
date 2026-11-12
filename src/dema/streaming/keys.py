from dataclasses import dataclass

from dema.domain.run import Run

CONSUMER_GROUP = "tallying"
ACTIVE_RUN_KEY = "dema:active_run"
CONTROL_STREAM = "dema:control"
DIRECTOR_GROUP = "director"


@dataclass(frozen=True, slots=True)
class ElectionKeys:
    prefix: str

    @classmethod
    def for_run(cls, run: Run) -> "ElectionKeys":
        return cls(f"dema:{run.year}:{run.round}:{run.id}")

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
