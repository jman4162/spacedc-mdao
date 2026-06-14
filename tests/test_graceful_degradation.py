"""Phase 4C-5: time-stepped fleet health and launch-quantized resupply."""

from __future__ import annotations

import itertools

import orbitdc as odc
from orbitdc.models.reliability import fleet_health_curve

SPACE = "examples/scenarios/orbital_1mw_inference.yaml"


def test_no_resupply_declines_monotonically() -> None:
    curve = fleet_health_curve(
        n_accelerators=1000,
        annual_failure_rate=0.10,
        mission_years=5.0,
        spare_fraction=0.0,
        reset_recovery_availability=1.0,
    )
    fracs = curve.surviving_fraction
    assert fracs[0] > fracs[-1]
    assert all(b <= a + 1e-9 for a, b in itertools.pairwise(fracs))
    assert curve.n_resupply_launches == 0


def test_resupply_raises_mean_and_counts_launches() -> None:
    common = dict(
        n_accelerators=1000,
        annual_failure_rate=0.10,
        mission_years=5.0,
        spare_fraction=0.0,
        reset_recovery_availability=1.0,
    )
    none = fleet_health_curve(**common)
    yearly = fleet_health_curve(resupply_interval_years=1.0, **common)
    assert yearly.mean_online_fraction > none.mean_online_fraction
    assert yearly.n_resupply_launches == 4  # resupply at t=1,2,3,4 (t=5 is mission end)
    assert yearly.replaced_units_total > 0.0


def test_off_by_default() -> None:
    base = odc.evaluate_space(odc.load_scenario(SPACE))
    assert base.availability_curve is None
    assert base.details["fleet_resupply_launches"] == 0.0


def test_curve_surfaced_when_enabled() -> None:
    base = odc.load_scenario(SPACE)
    d = base.model_dump()
    d["space"]["graceful_degradation"] = True
    g = odc.evaluate_space(odc.load_scenario_dict(d))
    assert g.availability_curve is not None
    times = [t for t, _ in g.availability_curve]
    caps = [c for _, c in g.availability_curve]
    assert times == sorted(times)
    assert caps[-1] < caps[0]  # declines without resupply
