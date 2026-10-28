from pathlib import Path

import pytest

from dema.cli import main


def test_synthesizes_and_summarizes_catalog(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "sections.parquet"

    main(["sections", "synth", "1000", str(output)])
    synth_output = capsys.readouterr().out
    main(["sections", "summary", str(output)])

    assert output.exists()
    assert "sections:           1,000" in synth_output
    assert capsys.readouterr().out == synth_output
