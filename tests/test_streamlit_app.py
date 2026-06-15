"""Smoke tests for the Streamlit app's model glue (app/data.py).

These guard the API contract the app depends on without starting a Streamlit
server. They import only ``app.data``, which is streamlit/plotly-free, so they
run under the base + dev install.
"""

from __future__ import annotations

import pytest
from app import data

from orbitdc.evaluation import Evaluation

SPACE = str(data.SCENARIO_DIR / "orbital_1mw_inference.yaml")
EARTH = str(data.SCENARIO_DIR / "earth_hyperscale_baseline.yaml")


def test_scenario_discovery_splits_by_kind() -> None:
    space_opts = data.list_scenarios("space")
    earth_opts = data.list_scenarios("earth")
    assert space_opts and earth_opts
    assert all(o.kind == "space" for o in space_opts)
    assert all(o.kind == "earth" for o in earth_opts)
    # The default scenarios are present.
    assert any("orbital_1mw_inference" in o.path for o in space_opts)
    assert any("earth_hyperscale_baseline" in o.path for o in earth_opts)


def test_runs_return_evaluations() -> None:
    space_ev = data.run_space(data.load(SPACE), {})
    earth_ev = data.run_earth(data.load(EARTH))
    assert isinstance(space_ev, Evaluation)
    assert isinstance(earth_ev, Evaluation)
    assert space_ev.lcoc_per_pflop_day > 0.0
    assert earth_ev.lcoc_per_pflop_day > 0.0


def test_baseline_run_matches_no_override() -> None:
    # The unmoved app (sliders at baseline) must reproduce evaluate_space().
    from orbitdc import evaluate_space

    space = data.load(SPACE)
    assert data.run_space(space, {}).lcoc_per_pflop_day == pytest.approx(
        evaluate_space(space).lcoc_per_pflop_day
    )


def test_override_changes_lcoc() -> None:
    space = data.load(SPACE)
    base = data.run_space(space, {}).lcoc_per_pflop_day
    # A 4x launch-cost hike must raise orbital LCOC.
    bumped = data.run_space(space, {"launch_cost_per_kg_usd": 8000.0}).lcoc_per_pflop_day
    assert bumped > base


def test_baselines_cover_every_driver() -> None:
    base = data.baselines(data.load(SPACE))
    for spec in data.DRIVERS:
        assert spec.key in base
        assert base[spec.key] >= 0.0


def test_binding_and_thresholds_are_strings() -> None:
    space = data.load(SPACE)
    space_ev = data.run_space(space, {})
    earth_lcoc = data.run_earth(data.load(EARTH)).lcoc_per_pflop_day
    notes = data.binding_constraints(space_ev)
    lines = data.thresholds(space, earth_lcoc, {})
    assert notes and all(isinstance(n, str) for n in notes)
    assert lines and all(isinstance(line, str) for line in lines)
