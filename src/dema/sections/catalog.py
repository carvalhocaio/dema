from collections.abc import Iterator
from pathlib import Path

import polars as pl

from dema.domain.section import Section, SectionKey
from dema.domain.state import State

KEY_COLUMNS = ("state", "municipality_code", "zone", "number")
SCHEMA = pl.Schema(
    {
        "state": pl.Enum([state.value for state in State]),
        "municipality_code": pl.Int32(),
        "zone": pl.Int16(),
        "number": pl.Int16(),
        "eligible_voters": pl.Int32(),
    }
)


class SectionCatalog:
    def __init__(self, frame: pl.DataFrame) -> None:
        self._frame = _validate(frame)

    @classmethod
    def from_parquet(cls, path: Path) -> "SectionCatalog":
        return cls(pl.read_parquet(path))

    def to_parquet(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._frame.write_parquet(path)

    @property
    def frame(self) -> pl.DataFrame:
        return self._frame

    @property
    def total_electorate(self) -> int:
        return int(self._frame["eligible_voters"].sum())

    def __len__(self) -> int:
        return self._frame.height

    def electorate_by_state(self) -> dict[State, int]:
        totals = self._frame.group_by("state").agg(pl.col("eligible_voters").sum())
        return {State(state): int(total) for state, total in totals.iter_rows()}

    def sections(self) -> Iterator[Section]:
        for state, municipality, zone, number, voters in self._frame.iter_rows():
            key = SectionKey(State(state), municipality, zone, number)
            yield Section(key=key, eligible_voters=voters)


def _validate(frame: pl.DataFrame) -> pl.DataFrame:
    missing = set(SCHEMA.names()) - set(frame.columns)
    if missing:
        raise ValueError(f"section catalog missing columns: {sorted(missing)}")
    typed = frame.select(SCHEMA.names()).cast(SCHEMA)
    if typed.is_empty():
        raise ValueError("section catalog must not be empty")
    if typed.select(pl.struct(KEY_COLUMNS).is_duplicated().any()).item():
        raise ValueError("section catalog has duplicated section keys")
    if typed.select((pl.col("eligible_voters") <= 0).any()).item():
        raise ValueError("every section must have eligible voters")
    return typed.sort(KEY_COLUMNS)
