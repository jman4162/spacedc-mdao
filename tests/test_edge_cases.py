"""Edge-case and infeasible-design tests (Phase 3A)."""

from __future__ import annotations

from pathlib import Path

import pytest

import orbitdc as odc

SPACE = Path(__file__).parents[1] / "examples" / "scenarios" / "orbital_1mw_inference.yaml"
EARTH = Path(__file__).parents[1] / "examples" / "scenarios" / "earth_hyperscale_baseline.yaml"


def test_negative_override_rejected() -> None:
    space = odc.load_scenario(SPACE)
    with pytest.raises(ValueError, match="finite and non-negative"):
        odc.evaluate_space(space, {"launch_cost_per_kg_usd": -100.0})


def test_nonfinite_override_rejected() -> None:
    space = odc.load_scenario(SPACE)
    with pytest.raises(ValueError):
        odc.evaluate_space(space, {"utilization": float("inf")})


def test_tiny_radiator_throttles_thermal() -> None:
    data = odc.load_scenario(SPACE).model_dump()
    data["space"]["architecture"]["radiator_area_m2_per_sat"] = 1.0  # absurdly small
    ev = odc.evaluate_space(odc.load_scenario_dict(data))
    assert ev.waterfall.factors["thermal"] < 1.0
    assert ev.details["radiator_packaging_ratio"] > 1.0


def test_tiny_solar_budget_throttles_power() -> None:
    data = odc.load_scenario(SPACE).model_dump()
    data["space"]["architecture"]["solar_area_m2_per_sat"] = 1.0  # absurdly small
    ev = odc.evaluate_space(odc.load_scenario_dict(data))
    assert ev.waterfall.factors["power"] < 1.0
    assert ev.details["solar_packaging_ratio"] > 1.0


def test_extreme_low_utilization_runs() -> None:
    ev = odc.evaluate_space(odc.load_scenario(SPACE), {"utilization": 0.05})
    assert ev.delivered_tflops >= 0.0
    assert ev.waterfall.factors["utilization"] == pytest.approx(0.05)


def test_zero_grid_carbon_earth() -> None:
    data = odc.load_scenario(EARTH).model_dump()
    data["earth"]["grid_carbon_intensity_kg_per_kwh"] = 0.0
    ev = odc.evaluate_earth(odc.load_scenario_dict(data))
    # With zero grid carbon, only embodied carbon remains; still positive.
    assert ev.details["co2e_per_pflop_day"] > 0.0
