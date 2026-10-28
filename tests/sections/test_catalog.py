from pathlib import Path

import polars as pl
import pytest

from dema.domain.state import State
from dema.sections.catalog import SectionCatalog


def make_frame(**overrides: list) -> pl.DataFrame:
    columns = {
        "state": ["SP", "MT", "MT"],
        "municipality_code": [71072, 90670, 90670],
        "zone": [1, 39, 1],
        "number": [10, 7, 7],
        "eligible_voters": [350, 280, 300],
    }
    return pl.DataFrame(columns | overrides)


def test_computes_totals() -> None:
    catalog = SectionCatalog(make_frame())

    assert len(catalog) == 3
    assert catalog.total_electorate == 930
    assert catalog.electorate_by_state() == {State.SP: 350, State.MT: 580}


def test_sorts_by_section_key() -> None:
    catalog = SectionCatalog(make_frame())

    assert [str(section.key) for section in catalog.sections()] == [
        "MT-90670-0001-0007",
        "MT-90670-0039-0007",
        "SP-71072-0001-0010",
    ]


def test_ignores_extra_columns() -> None:
    frame = make_frame().with_columns(pl.lit("CUIABÁ").alias("municipality_name"))

    assert "municipality_name" not in SectionCatalog(frame).frame.columns


def test_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="eligible_voters"):
        SectionCatalog(make_frame().drop("eligible_voters"))


def test_rejects_duplicated_keys() -> None:
    with pytest.raises(ValueError, match="duplicated"):
        SectionCatalog(make_frame(zone=[1, 39, 39]))


def test_rejects_sections_without_voters() -> None:
    with pytest.raises(ValueError, match="eligible voters"):
        SectionCatalog(make_frame(eligible_voters=[350, 0, 300]))


def test_rejects_unknown_states() -> None:
    with pytest.raises(pl.exceptions.InvalidOperationError):
        SectionCatalog(make_frame(state=["SP", "MT", "XX"]))


def test_rejects_empty_frame() -> None:
    with pytest.raises(ValueError, match="empty"):
        SectionCatalog(make_frame().clear())


def test_round_trips_through_parquet(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "sections.parquet"
    catalog = SectionCatalog(make_frame())

    catalog.to_parquet(path)

    assert SectionCatalog.from_parquet(path).frame.equals(catalog.frame)
