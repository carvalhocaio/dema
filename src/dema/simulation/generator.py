from collections.abc import Callable

import numpy as np
import polars as pl

from dema.domain.state import Region, State
from dema.sections.catalog import KEY_COLUMNS, SectionCatalog
from dema.simulation.ballots import SimulatedBallots, votes_column
from dema.simulation.scenario import RegionalProfile, Scenario

REGIONS = tuple(Region)
REGION_INDEX = {state.value: REGIONS.index(state.region) for state in State}


class BallotGenerator:
    def __init__(self, scenario: Scenario, seed: int = 2026) -> None:
        self._scenario = scenario
        self._numbers = [candidate.number for candidate in scenario.election.candidates]
        self._seed = seed

    def generate(self, catalog: SectionCatalog) -> SimulatedBallots:
        rng = np.random.default_rng(self._seed)
        frame = catalog.frame
        region = (
            frame["state"]
            .cast(pl.String)
            .replace_strict(REGION_INDEX, return_dtype=pl.UInt8)
            .to_numpy()
        )
        counts = rng.multinomial(
            self._draw_turnout(rng, region, frame["eligible_voters"].to_numpy()),
            self._draw_vote_probabilities(rng, region),
        ).astype(np.int32)
        votes = {votes_column(n): counts[:, i] for i, n in enumerate(self._numbers)}
        delay_ms = self._draw_release_delay_ms(rng, region)
        return SimulatedBallots(
            frame.select(*KEY_COLUMNS, "eligible_voters").with_columns(
                **votes,
                blank_votes=counts[:, -2],
                null_votes=counts[:, -1],
                issued_at=pl.lit(self._scenario.polls_close)
                + pl.duration(milliseconds=pl.lit(pl.Series(delay_ms))),
            )
        )

    def _draw_turnout(
        self, rng: np.random.Generator, region: np.ndarray, eligible: np.ndarray
    ) -> np.ndarray:
        mean = self._per_region(lambda profile: profile.turnout)[region]
        concentration = self._scenario.turnout_cohesion
        rate = rng.beta(mean * concentration, (1 - mean) * concentration)
        return rng.binomial(eligible, rate)

    def _draw_vote_probabilities(
        self, rng: np.random.Generator, region: np.ndarray
    ) -> np.ndarray:
        scenario = self._scenario
        weights = np.array(
            [
                [scenario.profiles[r].preferences[n] for n in self._numbers]
                for r in REGIONS
            ]
        )
        alpha = weights / weights.sum(axis=1, keepdims=True) * scenario.cohesion
        shares = rng.gamma(alpha[region])
        shares /= shares.sum(axis=1, keepdims=True)
        size = len(region)
        return np.column_stack(
            (
                shares * scenario.valid_rate,
                np.full(size, scenario.blank_rate),
                np.full(size, scenario.null_rate),
            )
        )

    def _draw_release_delay_ms(
        self, rng: np.random.Generator, region: np.ndarray
    ) -> np.ndarray:
        mean = self._per_region(
            lambda profile: profile.release_delay.total_seconds() * 1000
        )[region]
        shape = self._scenario.release_shape
        return np.rint(rng.gamma(shape, mean / shape)).astype(np.int64)

    def _per_region(self, attribute: Callable[[RegionalProfile], float]) -> np.ndarray:
        return np.array([attribute(self._scenario.profiles[r]) for r in REGIONS])
