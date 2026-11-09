from pathlib import Path

import pytest

from dema.cli import main
from dema.sections.catalog import SectionCatalog
from tests.sections.test_tse import write_csv


def test_imports_tse_csv_for_the_requested_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "sections.parquet"

    main(["sections", "import", str(write_csv(tmp_path / "tse.csv")), str(output)])

    assert len(SectionCatalog.from_parquet(output)) > 0
    assert "sections:" in capsys.readouterr().out
