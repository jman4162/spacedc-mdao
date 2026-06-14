"""CLI integration tests (Phase 3C)."""

from __future__ import annotations

from pathlib import Path

import pytest

from orbitdc.cli import main

SCEN = Path(__file__).parents[1] / "examples" / "scenarios"
SPACE = str(SCEN / "orbital_1mw_inference.yaml")
EARTH = str(SCEN / "earth_hyperscale_baseline.yaml")


def test_version_exits() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_compare_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["compare", SPACE, EARTH]) == 0
    assert "Verdict" in capsys.readouterr().out


def test_provenance_runs(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["provenance"]) == 0
    assert "provenance-tagged values" in capsys.readouterr().out


def test_missing_file_friendly_error() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["compare", "does_not_exist.yaml", EARTH])
    assert "not found" in str(exc.value)
