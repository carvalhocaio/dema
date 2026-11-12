from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from dema.domain.election import ElectionRound


class RunStatus(StrEnum):
    PREPARING = "preparing"
    COUNTING = "counting"
    COMPLETE = "complete"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class Run:
    id: int
    year: int
    round: ElectionRound
    seed: int
    status: RunStatus
    candidates: tuple[int, ...]
    parent_id: int | None
    started_at: datetime
    finished_at: datetime | None
