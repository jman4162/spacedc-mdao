"""Tests for the radiation model (Phase 3A)."""

from __future__ import annotations

import math
from pathlib import Path

import orbitdc as odc
from orbitdc.models import radiation

SPACE = Path(__file__).parents[1] / "examples" / "scenarios" / "orbital_1mw_inference.yaml"


def test_radiation_rises_with_altitude_and_inclination() -> None:
    tid_low, seu_low = radiation.radiation_environment(400.0, 0.0)
    tid_high, seu_high = radiation.radiation_environment(1500.0, 98.0)
    assert tid_high > tid_low
    assert seu_high > seu_low


def test_tid_dose_is_rate_times_years() -> None:
    res = radiation.radiation_failure_contribution(
        altitude_km=650.0,
        inclination_deg=0.0,
        mission_years=5.0,
        tid_tolerance_krad=20.0,
        seu_susceptibility=1.0,
        ecc_mitigation=0.8,
    )
    assert math.isclose(res.tid_dose_krad, res.tid_krad_per_year * 5.0, rel_tol=1e-9)
    assert res.failure_rate_per_year > 0.0


def test_ecc_mitigation_reduces_seu_failures() -> None:
    common = dict(
        altitude_km=650.0,
        inclination_deg=0.0,
        mission_years=5.0,
        tid_tolerance_krad=20.0,
        seu_susceptibility=1.0,
    )
    protected = radiation.radiation_failure_contribution(ecc_mitigation=0.9, **common)
    unprotected = radiation.radiation_failure_contribution(ecc_mitigation=0.0, **common)
    assert unprotected.failure_rate_per_year > protected.failure_rate_per_year


def test_radiation_wired_into_evaluation() -> None:
    ev = odc.evaluate_space(odc.load_scenario(SPACE))
    assert ev.details["total_failure_rate"] > ev.details["radiation_failure_rate"]
    assert ev.details["tid_dose_krad"] > 0.0
