from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import polars as pl

from dema.domain.candidate import Candidate
from dema.domain.election import Election, ElectionRound
from dema.sections.catalog import KEY_COLUMNS
from dema.simulation.ballots import SimulatedBallots, votes_column
from dema.simulation.generator import draw_release_delay_ms, region_codes
from dema.simulation.scenario import Scenario
from dema.tallying.outcome import Outcome, Verdict, decide
from dema.tallying.tally import Tally

SECOND_ROUND_POLLS_CLOSE = datetime(2026, 10, 25, 20, 0, tzinfo=UTC)
RUNOFF_STREAM = 2

DESTINATIONS = ("first", "second", "blank", "null", "abstention")


@dataclass(frozen=True, slots=True)
class TransferPrior:
    mean: tuple[float, float, float, float, float]
    concentration: float

    def draw(self, rng: np.random.Generator) -> np.ndarray:
        alpha = np.asarray(self.mean) / sum(self.mean) * self.concentration
        return rng.dirichlet(alpha)


FIRST_FINALIST = TransferPrior((0.92, 0.02, 0.01, 0.01, 0.04), 200.0)
SECOND_FINALIST = TransferPrior((0.02, 0.92, 0.01, 0.01, 0.04), 200.0)
ELIMINATED = TransferPrior((0.37, 0.37, 0.06, 0.06, 0.14), 6.0)
BLANK = TransferPrior((0.12, 0.12, 0.46, 0.10, 0.20), 30.0)
NULL = TransferPrior((0.12, 0.12, 0.10, 0.46, 0.20), 30.0)
ABSTENTION = TransferPrior((0.05, 0.05, 0.01, 0.01, 0.88), 100.0)


class NoRunoffError(RuntimeError):
    def __init__(self, winner: Candidate) -> None:
        super().__init__(
            f"{winner.name} was elected in the first round; there is no runoff"
        )


@dataclass(frozen=True, slots=True)
class Runoff:
    election: Election
    first_round: Outcome
    transfers: np.ndarray
    ballots: SimulatedBallots


def first_round_outcome(ballots: SimulatedBallots, election: Election) -> Outcome:
    frame = ballots.frame
    electorate = int(frame["eligible_voters"].sum())
    tally = Tally(
        nominal_votes={
            n: int(frame[votes_column(n)].sum()) for n in election.candidate_numbers
        },
        blank_votes=int(frame["blank_votes"].sum()),
        null_votes=int(frame["null_votes"].sum()),
        counted_sections=len(ballots),
        counted_electorate=electorate,
        total_sections=len(ballots),
        total_electorate=electorate,
    )
    return decide(election, tally)


class RunoffGenerator:
    def __init__(self, scenario: Scenario, seed: int) -> None:
        self._scenario = scenario
        self._seed = seed

    def generate(self, first_round: SimulatedBallots, election: Election) -> Runoff:
        outcome = first_round_outcome(first_round, election)
        if outcome.verdict is Verdict.ELECTED:
            raise NoRunoffError(outcome.leader.candidate)
        first, second = outcome.finalists
        rng = np.random.default_rng((self._seed, RUNOFF_STREAM))
        origins = self._origins(first_round, election, first, second)
        transfers = np.vstack([prior.draw(rng) for prior, _ in origins])
        moved = np.sum(
            [
                rng.multinomial(voters, row)
                for row, (_, voters) in zip(transfers, origins, strict=True)
            ],
            axis=0,
        )
        frame = first_round.frame
        delay_ms = draw_release_delay_ms(rng, self._scenario, region_codes(frame))
        runoff = frame.select(*KEY_COLUMNS, "eligible_voters").with_columns(
            **{
                votes_column(first.number): moved[:, 0].astype(np.int32),
                votes_column(second.number): moved[:, 1].astype(np.int32),
            },
            blank_votes=moved[:, 2].astype(np.int32),
            null_votes=moved[:, 3].astype(np.int32),
            issued_at=pl.lit(SECOND_ROUND_POLLS_CLOSE)
            + pl.duration(milliseconds=pl.lit(pl.Series(delay_ms))),
        )
        return Runoff(
            election=Election(
                year=election.year,
                round=ElectionRound.SECOND,
                candidates=(first, second),
            ),
            first_round=outcome,
            transfers=transfers,
            ballots=SimulatedBallots(runoff),
        )

    def _origins(
        self,
        ballots: SimulatedBallots,
        election: Election,
        first: Candidate,
        second: Candidate,
    ) -> list[tuple[TransferPrior, np.ndarray]]:
        frame = ballots.frame

        def column(name: str) -> np.ndarray:
            return frame[name].to_numpy().astype(np.int64)

        eliminated = [c.number for c in election.candidates if c not in (first, second)]
        turnout = np.sum(
            [column(votes_column(n)) for n in election.candidate_numbers]
            + [column("blank_votes"), column("null_votes")],
            axis=0,
        )
        return [
            (FIRST_FINALIST, column(votes_column(first.number))),
            (SECOND_FINALIST, column(votes_column(second.number))),
            *((ELIMINATED, column(votes_column(n))) for n in eliminated),
            (BLANK, column("blank_votes")),
            (NULL, column("null_votes")),
            (ABSTENTION, column("eligible_voters") - turnout),
        ]
