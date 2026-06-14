"""Tests for the workload library and duty cycle (Phase 3B)."""

from __future__ import annotations

from pathlib import Path

import orbitdc as odc

SPACE = Path(__file__).parents[1] / "examples" / "scenarios" / "orbital_1mw_inference.yaml"


def _with(**space_overrides: object) -> odc.Scenario:  # type: ignore[name-defined]
    data = odc.load_scenario(SPACE).model_dump()
    data["space"] = {**data["space"], **space_overrides}
    return odc.load_scenario_dict(data)


def _with_workload(workload_type: str) -> odc.Scenario:  # type: ignore[name-defined]
    data = odc.load_scenario(SPACE).model_dump()
    data["workload"] = {"type": "x", "workload_type": workload_type}
    return odc.load_scenario_dict(data)


def test_training_is_comms_bound_vs_earth_obs() -> None:
    training = odc.evaluate_space(_with_workload("llm_training"))
    earth_obs = odc.evaluate_space(_with_workload("earth_observation"))
    # Earth-dependent training moves far more data than a space-native workload.
    assert training.details["network_required_gbps"] > earth_obs.details["network_required_gbps"]
    assert earth_obs.waterfall.factors["network"] > training.waterfall.factors["network"]


def test_explicit_comm_intensity_overrides_workload_type() -> None:
    data = odc.load_scenario(SPACE).model_dump()
    data["workload"] = {"workload_type": "llm_training", "comm_intensity_bits_per_flop": 1e-9}
    ev = odc.evaluate_space(odc.load_scenario_dict(data))
    # The explicit value wins over the workload preset.
    assert ev.details["network_required_gbps"] < 10.0


def test_duty_cycle_reduces_sizing_load() -> None:
    full = odc.evaluate_space(_with(duty_cycle_fraction=1.0))
    half = odc.evaluate_space(_with(duty_cycle_fraction=0.5))
    assert half.details["bus_load_w"] < full.details["bus_load_w"]
