from datetime import datetime

import polars as pl

from dema.domain.state import Region, State
from dema.sections.catalog import SectionCatalog
from dema.simulation.ballots import SimulatedBallots, votes_column
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND, KEONS, NICO

NORTHEAST = [state.value for state in State if state.region is Region.NORTHEAST]
SOUTH = [state.value for state in State if state.region is Region.SOUTH]


def keons_share(ballots: SimulatedBallots, states: list[str]) -> float:
    totals = (
        ballots.frame.filter(pl.col("state").is_in(states))
        .select(votes_column(KEONS.number), votes_column(NICO.number))
        .sum()
        .row(0)
    )
    return totals[0] / sum(totals)


def test_generates_one_ballot_per_section(
    catalog: SectionCatalog, ballots: SimulatedBallots
) -> None:
    assert len(ballots) == len(catalog)
    assert ballots.candidate_numbers == (27, 99, 31, 44, 12)


def test_is_deterministic_per_seed(catalog: SectionCatalog) -> None:
    first = BallotGenerator(DEMA_2026_FIRST_ROUND, seed=7).generate(catalog)
    second = BallotGenerator(DEMA_2026_FIRST_ROUND, seed=7).generate(catalog)

    assert first.frame.equals(second.frame)


def test_turnout_stays_near_scenario(ballots: SimulatedBallots) -> None:
    ballot_columns = [votes_column(n) for n in ballots.candidate_numbers]
    turnout = ballots.frame.select(
        pl.sum_horizontal(*ballot_columns, "blank_votes", "null_votes").sum()
        / pl.col("eligible_voters").sum()
    ).item()

    assert 0.75 < turnout < 0.83


def test_applies_regional_bias(ballots: SimulatedBallots) -> None:
    assert keons_share(ballots, NORTHEAST) > 0.65
    assert keons_share(ballots, SOUTH) < 0.45


def test_south_reports_before_northeast(ballots: SimulatedBallots) -> None:
    def median_release(states: list[str]) -> datetime:
        return (
            ballots.frame.filter(pl.col("state").is_in(states))
            .select(pl.col("issued_at").median())
            .item()
        )

    assert median_release(SOUTH) < median_release(NORTHEAST)


def test_ballots_are_sorted_by_release(ballots: SimulatedBallots) -> None:
    assert ballots.frame["issued_at"].is_sorted()
    first_release = ballots.frame.select(pl.col("issued_at").min()).item()

    assert first_release > DEMA_2026_FIRST_ROUND.polls_close
