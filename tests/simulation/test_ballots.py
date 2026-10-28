from itertools import islice
from pathlib import Path

from dema.simulation.ballots import SimulatedBallots, votes_column


def test_converts_rows_into_domain_ballots(ballots: SimulatedBallots) -> None:
    first = next(ballots.in_release_order())
    row = ballots.frame.row(0, named=True)

    assert str(first.section) == (
        f"{row['state']}-{row['municipality_code']:05d}"
        f"-{row['zone']:04d}-{row['number']:04d}"
    )
    assert first.nominal_votes == {
        n: row[votes_column(n)] for n in ballots.candidate_numbers
    }
    assert first.issued_at == row["issued_at"]


def test_yields_ballots_in_release_order(ballots: SimulatedBallots) -> None:
    issued = [ballot.issued_at for ballot in islice(ballots.in_release_order(), 500)]

    assert issued == sorted(issued)


def test_round_trips_through_parquet(ballots: SimulatedBallots, tmp_path: Path) -> None:
    path = tmp_path / "ballots.parquet"

    ballots.to_parquet(path)
    restored = SimulatedBallots.from_parquet(path)

    assert restored.frame.equals(ballots.frame)
    assert restored.candidate_numbers == ballots.candidate_numbers
