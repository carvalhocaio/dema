from pathlib import Path

import pytest

from dema.cli import main
from dema.config import get_settings


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


def test_tallies_simulated_ballots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    catalog = tmp_path / "sections.parquet"
    ballots = tmp_path / "ballots.parquet"
    main(["sections", "synth", "2000", str(catalog)])
    main(["ballots", "simulate", str(catalog), str(ballots)])
    capsys.readouterr()

    main(["ballots", "tally", str(ballots), "--steps", "4"])
    lines = capsys.readouterr().out.splitlines()

    assert any(line.lstrip().startswith(">> runoff at") for line in lines)
    assert len([line for line in lines if ">>" not in line]) == 4


def test_reports_missing_signing_key_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DEMA_SIGNING_KEY", raising=False)
    get_settings.cache_clear()
    catalog, ballots = tmp_path / "sections.parquet", tmp_path / "ballots.parquet"
    main(["sections", "synth", "100", str(catalog)])
    main(["ballots", "simulate", str(catalog), str(ballots)])

    with pytest.raises(SystemExit, match="DEMA_SIGNING_KEY"):
        main(["ballots", "publish", str(ballots)])
    get_settings.cache_clear()
