from pathlib import Path

import pytest

from dema.domain.election import ElectionRound
from dema.sections.tse import TseSectionSource

HEADER = (
    '"NR_TURNO";"SG_UF";"CD_MUNICIPIO";"NM_MUNICIPIO";'
    '"NR_ZONA";"NR_SECAO";"QT_ELEITOR_SECAO"'
)
ROWS = (
    '"1";"MT";"90670";"CUIABÁ";"39";"7";"280"',
    '"1";"MT";"90670";"CUIABÁ";"39";"8";"0"',
    '"1";"SP";"71072";"SÃO PAULO";"1";"10";"350"',
    '"1";"SP";"71072";"SÃO PAULO";"1";"10";"350"',
    '"2";"SP";"71072";"SÃO PAULO";"1";"11";"410"',
)


def write_csv(path: Path, header: str = HEADER, rows: tuple[str, ...] = ROWS) -> Path:
    path.write_bytes("\n".join((header, *rows)).encode("latin-1"))
    return path


def test_loads_latin1_file_selecting_round(tmp_path: Path) -> None:
    catalog = TseSectionSource(write_csv(tmp_path / "tse.csv")).load()

    assert [str(section.key) for section in catalog.sections()] == [
        "MT-90670-0039-0007",
        "SP-71072-0001-0010",
    ]
    assert catalog.total_electorate == 630


def test_loads_second_round(tmp_path: Path) -> None:
    source = TseSectionSource(write_csv(tmp_path / "tse.csv"), ElectionRound.SECOND)

    assert source.load().total_electorate == 410


def test_works_without_round_column(tmp_path: Path) -> None:
    header = HEADER.removeprefix('"NR_TURNO";')
    rows = tuple(row.split(";", 1)[1] for row in ROWS)

    catalog = TseSectionSource(write_csv(tmp_path / "tse.csv", header, rows)).load()

    assert len(catalog) == 3


def test_reports_missing_columns(tmp_path: Path) -> None:
    header = HEADER.replace("QT_ELEITOR_SECAO", "QT_ELEITOR")

    with pytest.raises(ValueError, match="QT_ELEITOR_SECAO"):
        TseSectionSource(write_csv(tmp_path / "tse.csv", header)).load()
