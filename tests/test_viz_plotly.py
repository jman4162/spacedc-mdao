"""Headless tests for the interactive viz layer (sub-phase 2C).

Skipped unless the ``viz`` extra (plotly / panel / networkx) is installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("plotly")
pytest.importorskip("networkx")

import orbitdc as odc
from orbitdc.thermal.catalog import get_chip_stack, get_radiator_surface
from orbitdc.thermal.presets import get_environment
from orbitdc.viz import plotly_figures as pf
from orbitdc.viz.provenance import collect_provenance, provenance_table

SCEN = Path(__file__).parents[1] / "examples" / "scenarios"


def _result() -> odc.ComparisonResult:
    return odc.compare(
        odc.load_scenario(SCEN / "orbital_1mw_inference.yaml"),
        odc.load_scenario(SCEN / "earth_hyperscale_baseline.yaml"),
    )


def test_overview_figures_build() -> None:
    from plotly.graph_objects import Figure

    ev = _result().space
    for fig in (
        pf.delivered_waterfall(ev),
        pf.cost_breakdown(ev),
        pf.mass_treemap(ev),
        pf.power_sankey(ev),
        pf.constellation_graph(64),
    ):
        assert isinstance(fig, Figure)


def test_thermal_figures_build() -> None:
    from plotly.graph_objects import Figure

    surface = get_radiator_surface("deployable_osr")
    env = get_environment("conservative_leo")
    stack = get_chip_stack("h100_direct_liquid", 700.0)
    assert isinstance(pf.thermal_area_vs_temp(1.0e6, surface, env), Figure)
    assert isinstance(pf.net_flux_waterfall(330.0, surface, env), Figure)
    assert isinstance(pf.chip_temperature_ladder(330.0, stack), Figure)


def test_provenance_panel() -> None:
    from plotly.graph_objects import Figure

    rows = collect_provenance()
    assert len(rows) > 10
    assert {"source", "confidence", "kind"} <= set(rows[0])
    assert isinstance(provenance_table(), Figure)


def test_dashboard_builds() -> None:
    pytest.importorskip("panel")
    from orbitdc.viz.dashboard import build_dashboard

    dash = build_dashboard(
        odc.load_scenario(SCEN / "orbital_1mw_inference.yaml"),
        odc.load_scenario(SCEN / "earth_hyperscale_baseline.yaml"),
    )
    assert len(dash) == 3  # three tabs
