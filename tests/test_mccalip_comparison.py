"""Capacity-capex / $-per-watt metric and the McCalip-optimistic reconciliation.

Makes the comparison with Andrew McCalip's calculator (cited by the Economist,
Mar 2026) reproducible: an apples-to-apples capex-per-watt figure, and a scenario
that closes most of the gap with optimistic sliders while LCOC stays above parity
because of the delivered-compute waterfall.
"""

from __future__ import annotations

import orbitdc as odc

EARTH = "examples/scenarios/earth_hyperscale_baseline.yaml"
DEFAULT = "examples/scenarios/orbital_1mw_inference.yaml"
MCCALIP = "examples/scenarios/orbital_mccalip_optimistic.yaml"


def test_capex_per_w_present_and_positive() -> None:
    space = odc.evaluate_space(odc.load_scenario(DEFAULT))
    earth = odc.evaluate_earth(odc.load_scenario(EARTH))
    assert space.capex_usd > 0.0
    assert space.details["capex_per_w_ex_gpu"] > 0.0
    assert earth.details["capex_per_w_ex_gpu"] > 0.0
    # Earth capacity-capex per watt is far below space (the McCalip terrestrial
    # figure ~$12/W-$16/W; space defaults are conservative).
    assert earth.details["capex_per_w_ex_gpu"] < space.details["capex_per_w_ex_gpu"]


def test_capex_excludes_gpu() -> None:
    space = odc.evaluate_space(odc.load_scenario(DEFAULT))
    ex_gpu = space.capex_usd - space.cost_breakdown_usd["accelerators"]
    assert space.details["capex_per_w_ex_gpu"] == ex_gpu / space.it_power_w


def test_bus_cost_is_configurable() -> None:
    space = odc.load_scenario(DEFAULT)
    high = odc.evaluate_space(space).capex_usd
    low = odc.evaluate_space(space, {"bus_cost_per_sat_usd": 100_000.0}).capex_usd
    assert low < high


def test_mccalip_optimistic_closes_most_of_the_gap() -> None:
    base = odc.evaluate_space(odc.load_scenario(DEFAULT))
    opt = odc.evaluate_space(odc.load_scenario(MCCALIP))
    # Optimistic sliders cut capex/W and LCOC well below the conservative default.
    assert opt.details["capex_per_w_ex_gpu"] < 0.6 * base.details["capex_per_w_ex_gpu"]
    assert opt.lcoc_per_pflop_day < 0.5 * base.lcoc_per_pflop_day
    # Crosslink-only operation un-binds the network (no ground-downlink penalty).
    assert opt.waterfall.factors["network"] > 0.95


def test_optimistic_still_loses_to_earth() -> None:
    # Even optimistic, the delivered-compute waterfall keeps space above parity.
    opt = odc.evaluate_space(odc.load_scenario(MCCALIP)).lcoc_per_pflop_day
    earth = odc.evaluate_earth(odc.load_scenario(EARTH)).lcoc_per_pflop_day
    assert opt > earth
