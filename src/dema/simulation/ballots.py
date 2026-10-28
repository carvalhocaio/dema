from collections.abc import Iterator
from pathlib import Path

import polars as pl

from dema.domain.ballot import Ballot
from dema.domain.section import SectionKey
from dema.domain.state import State

VOTES_PREFIX = "votes_"


def votes_column(number: int) -> str:
    return f"{VOTES_PREFIX}{number}"


class SimulatedBallots:
    def __init__(self, frame: pl.DataFrame) -> None:
        self._frame = frame.sort("issued_at")
        self._numbers = tuple(
            int(column.removeprefix(VOTES_PREFIX))
            for column in frame.columns
            if column.startswith(VOTES_PREFIX)
        )

    @classmethod
    def from_parquet(cls, path: Path) -> "SimulatedBallots":
        return cls(pl.read_parquet(path))

    def to_parquet(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._frame.write_parquet(path)

    @property
    def frame(self) -> pl.DataFrame:
        return self._frame

    @property
    def candidate_numbers(self) -> tuple[int, ...]:
        return self._numbers

    def __len__(self) -> int:
        return self._frame.height

    def in_release_order(self) -> Iterator[Ballot]:
        for row in self._frame.iter_rows(named=True):
            yield Ballot(
                section=SectionKey(
                    State(row["state"]),
                    row["municipality_code"],
                    row["zone"],
                    row["number"],
                ),
                eligible_voters=row["eligible_voters"],
                nominal_votes={n: row[votes_column(n)] for n in self._numbers},
                blank_votes=row["blank_votes"],
                null_votes=row["null_votes"],
                issued_at=row["issued_at"],
            )
