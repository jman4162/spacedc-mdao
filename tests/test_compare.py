"""End-to-end checks on the comparison spine."""

from __future__ import annotations

from pathlib import Path

import orbitdc as odc
from orbitdc.compare import evaluate_space
from orbitdc.optimize import monte_carlo, tornado

SCENARIOS = Path(__file__).parents[1] / "examples" / "scenarios"
SPACE = SCENARIOS / "orbital_1mw_inference.yaml"
EARTH = SCENARIOS / "earth_hyperscale_baseline.yaml"


def test_waterfall_degrades_compute() -> None:
    space = odc.load_scenario(SPACE)
    ev = evaluate_space(space)
    assert ev.delivered_tflops > 0.0
    assert ev.delivered_tflops < ev.peak_tflops
    assert 0.0 < ev.delivered_fraction < 1.0
    # The waterfall product equals delivered compute.
    product = ev.peak_tflops
    for f in ev.waterfall.factors.values():
        product *= f
    assert abs(product - ev.delivered_tflops) < 1e-6


def test_compare_runs_and_is_deterministic() -> None:
    space = odc.load_scenario(SPACE)
    earth = odc.load_scenario(EARTH)
    r1 = odc.compare(space, earth)
    r2 = odc.compare(space, earth)
    assert r1.space.lcoc_per_pflop_day == r2.space.lcoc_per_pflop_day
    assert r1.earth.lcoc_per_pflop_day == r2.earth.lcoc_per_pflop_day
    assert "Verdict" in r1.summary()
    assert r1.space.lcoc_per_pflop_day > 0.0
    assert r1.earth.lcoc_per_pflop_day > 0.0


def test_binding_constraints_nonempty() -> None:
    space = odc.load_scenario(SPACE)
    earth = odc.load_scenario(EARTH)
    text = odc.compare(space, earth).explain_binding_constraints()
    assert "binding constraints" in text.lower()
    # The demo space design is thermally and network limited.
    assert "network-limited" in text or "thermally allowable" in text


def test_thresholds_present() -> None:
    space = odc.load_scenario(SPACE)
    earth = odc.load_scenario(EARTH)
    thresholds = odc.compare(space, earth).thresholds()
    assert set(thresholds) >= {"launch_cost_per_kg_usd", "utilization"}


def test_tornado_sorted_by_swing() -> None:
    space = odc.load_scenario(SPACE)
    entries = tornado(space)
    assert len(entries) == 9
    swings = [e.swing for e in entries]
    assert swings == sorted(swings, reverse=True)


def test_monte_carlo_deterministic_and_bounded() -> None:
    space = odc.load_scenario(SPACE)
    earth = odc.load_scenario(EARTH)
    earth_lcoc = odc.compare(space, earth).earth.lcoc_per_pflop_day
    a = monte_carlo(space, earth_lcoc, n=64, seed=0)
    b = monte_carlo(space, earth_lcoc, n=64, seed=0)
    assert 0.0 <= a.p_space_wins <= 1.0
    assert a.p_space_wins == b.p_space_wins
    assert a.lcoc_p10 <= a.lcoc_p50 <= a.lcoc_p90
