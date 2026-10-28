from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

import numpy as np
import polars as pl

from dema.domain.state import State
from dema.sections.catalog import SectionCatalog

AVERAGE_VOTERS_PER_SECTION = 307
MIN_VOTERS_PER_SECTION = 30
MAX_VOTERS_PER_SECTION = 600
SECTIONS_PER_ZONE = 500

APPROXIMATE_ELECTORATE_THOUSANDS: Mapping[State, int] = MappingProxyType(
    {
        State.SP: 34_104,
        State.MG: 16_378,
        State.RJ: 12_857,
        State.BA: 11_321,
        State.PR: 8_600,
        State.RS: 8_590,
        State.PE: 7_226,
        State.CE: 6_820,
        State.PA: 6_080,
        State.SC: 5_490,
        State.MA: 5_040,
        State.GO: 4_920,
        State.PB: 3_080,
        State.ES: 2_920,
        State.AM: 2_650,
        State.PI: 2_570,
        State.RN: 2_550,
        State.MT: 2_470,
        State.AL: 2_320,
        State.DF: 2_200,
        State.MS: 1_960,
        State.SE: 1_700,
        State.RO: 1_240,
        State.TO: 1_080,
        State.ZZ: 919,
        State.AC: 614,
        State.AP: 577,
        State.RR: 401,
    }
)


@dataclass(frozen=True, slots=True)
class SyntheticSectionSource:
    sections: int
    seed: int = 2026
    mean_voters: int = AVERAGE_VOTERS_PER_SECTION
    spread: float = 0.25
    weights: Mapping[State, int] = field(
        default_factory=lambda: APPROXIMATE_ELECTORATE_THOUSANDS
    )

    def load(self) -> SectionCatalog:
        if self.sections <= 0:
            raise ValueError("synthetic source requires a positive section count")
        rng = np.random.default_rng(self.seed)
        states = list(self.weights)
        shares = np.array([self.weights[state] for state in states], dtype=float)
        per_state = rng.multinomial(self.sections, shares / shares.sum())
        position = np.concatenate([np.arange(count) for count in per_state])
        return SectionCatalog(
            pl.DataFrame(
                {
                    "state": np.repeat([state.value for state in states], per_state),
                    "municipality_code": np.repeat(
                        np.arange(len(states)) + 10_000, per_state
                    ),
                    "zone": position // SECTIONS_PER_ZONE + 1,
                    "number": position % SECTIONS_PER_ZONE + 1,
                    "eligible_voters": self._draw_voters(rng),
                }
            )
        )

    def _draw_voters(self, rng: np.random.Generator) -> np.ndarray:
        voters = rng.normal(
            self.mean_voters, self.mean_voters * self.spread, self.sections
        )
        return np.clip(
            np.rint(voters), MIN_VOTERS_PER_SECTION, MAX_VOTERS_PER_SECTION
        ).astype(np.int32)
