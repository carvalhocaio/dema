from collections.abc import Mapping
from dataclasses import dataclass

import polars as pl

from dema.simulation.ballots import SimulatedBallots, votes_column


@dataclass(frozen=True, slots=True)
class Checkpoint:
    progress: float
    shares: Mapping[int, float]

    @property
    def leader(self) -> int:
        return max(self.shares, key=self.shares.__getitem__)


def counting_timeline(ballots: SimulatedBallots, steps: int = 10) -> list[Checkpoint]:
    if steps <= 0:
        raise ValueError("timeline requires a positive number of steps")
    columns = [votes_column(n) for n in ballots.candidate_numbers]
    cumulative = ballots.frame.select(pl.col(columns).cum_sum())
    total = len(ballots)
    rows = [max(round(total * step / steps), 1) - 1 for step in range(1, steps + 1)]
    return [
        _checkpoint(cumulative.row(row), ballots, (row + 1) / total) for row in rows
    ]


def _checkpoint(
    cumulative: tuple[int, ...], ballots: SimulatedBallots, progress: float
) -> Checkpoint:
    valid = sum(cumulative)
    shares = {
        number: votes / valid
        for number, votes in zip(ballots.candidate_numbers, cumulative, strict=True)
    }
    return Checkpoint(progress=progress, shares=shares)
