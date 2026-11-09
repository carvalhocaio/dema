from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

import numpy as np

from dema.domain.state import Region
from dema.simulation.scenario import Scenario

NATIONAL_CONCENTRATION = 16.0
REGIONAL_CONCENTRATION = 150.0
TURNOUT_SPREAD = 0.04
MIN_TURNOUT = 0.05
MIN_SHARE = 1e-4
SAMPLER_STREAM = 1

REGIONS = tuple(Region)


@dataclass(frozen=True, slots=True)
class ScenarioDraw:
    scenario: Scenario
    national: Mapping[int, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "national", MappingProxyType(dict(self.national)))


class ScenarioSampler:
    def __init__(
        self,
        reference: Scenario,
        national_concentration: float = NATIONAL_CONCENTRATION,
        regional_concentration: float = REGIONAL_CONCENTRATION,
        turnout_spread: float = TURNOUT_SPREAD,
    ) -> None:
        if national_concentration <= 0 or regional_concentration <= 0:
            raise ValueError("concentrations must be positive")
        if not 0 <= turnout_spread < 1:
            raise ValueError(f"turnout spread must be within [0, 1): {turnout_spread}")
        self._reference = reference
        self._numbers = [c.number for c in reference.election.candidates]
        self._national_concentration = national_concentration
        self._regional_concentration = regional_concentration
        self._turnout_spread = turnout_spread

    def sample(self, seed: int) -> Scenario:
        return self.draw(seed).scenario

    def draw(self, seed: int) -> ScenarioDraw:
        rng = np.random.default_rng((seed, SAMPLER_STREAM))
        reference = self._reference_shares()
        average = reference.mean(axis=0)
        national = _floored(rng.dirichlet(average * self._national_concentration))
        centers = _normalized(national * reference / average)
        regional = np.vstack(
            [
                _floored(rng.dirichlet(center * self._regional_concentration))
                for center in centers
            ]
        )
        turnout = self._draw_turnout(rng)
        profiles = {
            region: replace(
                self._reference.profiles[region],
                preferences=dict(zip(self._numbers, regional[i].tolist(), strict=True)),
                turnout=turnout[i],
            )
            for i, region in enumerate(REGIONS)
        }
        return ScenarioDraw(
            scenario=replace(self._reference, profiles=profiles),
            national=dict(zip(self._numbers, national.tolist(), strict=True)),
        )

    def _reference_shares(self) -> np.ndarray:
        weights = np.array(
            [
                [self._reference.profiles[region].preferences[n] for n in self._numbers]
                for region in REGIONS
            ]
        )
        return _normalized(weights)

    def _draw_turnout(self, rng: np.random.Generator) -> list[float]:
        base = np.array([self._reference.profiles[r].turnout for r in REGIONS])
        spread = self._turnout_spread
        drawn = base + rng.uniform(-spread, spread, size=len(REGIONS))
        return np.clip(drawn, MIN_TURNOUT, 1.0).tolist()


def _normalized(weights: np.ndarray) -> np.ndarray:
    return weights / weights.sum(axis=-1, keepdims=True)


def _floored(shares: np.ndarray) -> np.ndarray:
    return _normalized(np.maximum(shares, MIN_SHARE))
