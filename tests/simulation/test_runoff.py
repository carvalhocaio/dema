import numpy as np
import polars as pl
import pytest

from dema.domain.election import Election, ElectionRound
from dema.sections.catalog import KEY_COLUMNS, SectionCatalog
from dema.simulation.ballots import SimulatedBallots, votes_column
from dema.simulation.generator import BallotGenerator
from dema.simulation.presets import DEMA_2026_FIRST_ROUND
from dema.simulation.runoff import (
    SECOND_ROUND_POLLS_CLOSE,
    NoRunoffError,
    Runoff,
    RunoffGenerator,
    first_round_outcome,
)
from dema.simulation.sampler import ScenarioSampler
from dema.tallying.outcome import Verdict

REFERENCE = DEMA_2026_FIRST_ROUND
FIRST_ROUND = REFERENCE.election
LANDSLIDE_SEED = 3


@pytest.fixture(scope="module")
def first_round(small_catalog: SectionCatalog) -> SimulatedBallots:
    return BallotGenerator(REFERENCE, seed=7).generate(small_catalog)


def make_runoff(first_round: SimulatedBallots, seed: int = 11) -> Runoff:
    return RunoffGenerator(REFERENCE, seed=seed).generate(first_round, FIRST_ROUND)


def turnout(frame: pl.DataFrame, election: Election) -> np.ndarray:
    columns = [votes_column(n) for n in election.candidate_numbers]
    return (
        frame.select(pl.sum_horizontal(*columns, "blank_votes", "null_votes"))
        .to_series()
        .to_numpy()
    )


def test_finalists_are_the_first_round_top_two(first_round: SimulatedBallots) -> None:
    runoff = make_runoff(first_round)

    expected = first_round_outcome(first_round, FIRST_ROUND).finalists
    assert runoff.first_round.verdict is Verdict.RUNOFF
    assert runoff.election.candidates == expected
    assert runoff.election.round is ElectionRound.SECOND
    assert runoff.ballots.candidate_numbers == tuple(c.number for c in expected)


def test_keeps_sections_and_never_exceeds_their_electorate(
    first_round: SimulatedBallots,
) -> None:
    runoff = make_runoff(first_round)
    before = first_round.frame.sort(KEY_COLUMNS)
    after = runoff.ballots.frame.sort(KEY_COLUMNS)

    assert after.select(*KEY_COLUMNS, "eligible_voters").equals(
        before.select(*KEY_COLUMNS, "eligible_voters")
    )
    assert (
        turnout(after, runoff.election) <= after["eligible_voters"].to_numpy()
    ).all()
    assert (turnout(after, runoff.election) > 0).all()


def test_finalists_keep_most_of_their_voters(first_round: SimulatedBallots) -> None:
    transfers = make_runoff(first_round).transfers

    assert transfers.sum(axis=1) == pytest.approx(np.ones(len(transfers)))
    assert transfers[0, 0] > 0.8
    assert transfers[1, 1] > 0.8
    assert len(transfers) == len(FIRST_ROUND.candidates) + 3


def test_releases_ballots_after_the_second_round_closes(
    first_round: SimulatedBallots,
) -> None:
    frame = make_runoff(first_round).ballots.frame

    assert frame.select((pl.col("issued_at") > SECOND_ROUND_POLLS_CLOSE).all()).item()


def test_same_seed_derives_the_same_runoff(first_round: SimulatedBallots) -> None:
    first = make_runoff(first_round, seed=5).ballots.frame
    again = make_runoff(first_round, seed=5).ballots.frame
    other = make_runoff(first_round, seed=6).ballots.frame

    assert first.equals(again)
    assert not first.equals(other)


def test_refuses_when_the_first_round_elected_someone(
    small_catalog: SectionCatalog,
) -> None:
    landslide = ScenarioSampler(REFERENCE).sample(LANDSLIDE_SEED)
    ballots = BallotGenerator(landslide, seed=LANDSLIDE_SEED).generate(small_catalog)

    with pytest.raises(NoRunoffError, match=r"^Keons was elected in the first round"):
        make_runoff(ballots)
