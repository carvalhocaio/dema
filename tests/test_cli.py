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


def test_simulates_ballots_from_catalog(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog = tmp_path / "sections.parquet"
    ballots = tmp_path / "ballots.parquet"
    main(["sections", "synth", "2000", str(catalog)])
    capsys.readouterr()

    main(["ballots", "simulate", str(catalog), str(ballots)])
    output = capsys.readouterr().out

    assert ballots.exists()
    assert "ballots: 2,000" in output
    assert "100.0%" in output
