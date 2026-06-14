"""Tests for report export (Phase 3C)."""

from __future__ import annotations

from pathlib import Path

import pytest

import orbitdc as odc

SCEN = Path(__file__).parents[1] / "examples" / "scenarios"


def _result() -> odc.ComparisonResult:
    return odc.compare(
        odc.load_scenario(SCEN / "orbital_1mw_inference.yaml"),
        odc.load_scenario(SCEN / "earth_hyperscale_baseline.yaml"),
    )


def test_markdown_report(tmp_path: Path) -> None:
    out = odc.export_report(_result(), tmp_path / "report.md", fmt="md")
    text = out.read_text()
    assert "# Report:" in text
    assert "Verdict" in text
    assert "## Assumptions" in text  # provenance table included


def test_html_report(tmp_path: Path) -> None:
    pytest.importorskip("plotly")
    out = odc.export_report(_result(), tmp_path / "report.html", fmt="html")
    text = out.read_text()
    assert text.startswith("<html>")
    assert "plotly" in text.lower()  # embedded figures
    assert "commit" in text  # provenance footer
