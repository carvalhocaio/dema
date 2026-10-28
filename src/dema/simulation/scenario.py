from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import MappingProxyType

from dema.domain.election import Election
from dema.domain.state import Region


@dataclass(frozen=True, slots=True)
class RegionalProfile:
    preferences: Mapping[int, float]
    turnout: float
    release_delay: timedelta

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "preferences", MappingProxyType(dict(self.preferences))
        )
        if any(weight <= 0 for weight in self.preferences.values()):
            raise ValueError("candidate preferences must be positive")
        if not 0 < self.turnout <= 1:
            raise ValueError(f"turnout must be within (0, 1]: {self.turnout}")
        if self.release_delay <= timedelta(0):
            raise ValueError("release delay must be positive")


@dataclass(frozen=True, slots=True)
class Scenario:
    election: Election
    profiles: Mapping[Region, RegionalProfile]
    polls_close: datetime
    blank_rate: float = 0.016
    null_rate: float = 0.028
    cohesion: float = 80.0
    turnout_cohesion: float = 150.0
    release_shape: float = 4.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "profiles", MappingProxyType(dict(self.profiles)))
        if set(self.profiles) != set(Region):
            raise ValueError("scenario requires a profile for every region")
        numbers = self.election.candidate_numbers
        if any(set(p.preferences) != numbers for p in self.profiles.values()):
            raise ValueError("preferences must cover exactly the election candidates")
        if self.blank_rate < 0 or self.null_rate < 0:
            raise ValueError("blank and null rates must not be negative")
        if self.blank_rate + self.null_rate >= 1:
            raise ValueError("blank and null rates leave no room for valid votes")
        if self.polls_close.tzinfo is None:
            raise ValueError("polls closing time must be timezone-aware")

    @property
    def valid_rate(self) -> float:
        return 1 - self.blank_rate - self.null_rate
