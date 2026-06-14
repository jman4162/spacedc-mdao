"""Tests for the Phase 2D fidelity upgrades.

Environmental accounting, station-keeping delta-v, beta-angle eclipse, the
opensatcom RF seam, and the additional Earth baselines.
"""

from __future__ import annotations

import math
from pathlib import Path

import orbitdc as odc
from orbitdc.models import environmental, orbit, rf

SCEN = Path(__file__).parents[1] / "examples" / "scenarios"
EARTH_BASELINES = [
    "earth_hyperscale_baseline.yaml",
    "earth_leased_colo.yaml",
    "earth_renewable_storage.yaml",
    "earth_gas_backed.yaml",
    "earth_constrained_grid.yaml",
]


def test_atmospheric_density_decreases_with_altitude() -> None:
    assert orbit.atmospheric_density(400.0) > orbit.atmospheric_density(700.0)


def test_drag_deltav_and_propellant_positive() -> None:
    dv = orbit.drag_deltav_per_year_ms(650.0, drag_area_m2=1000.0, mass_kg=50000.0)
    assert dv > 0.0
    prop = orbit.station_keeping_propellant_kg(dv * 5.0, dry_mass_kg=50000.0, isp_s=220.0)
    assert prop > 0.0
    # Rocket equation: more delta-v needs more propellant.
    assert orbit.station_keeping_propellant_kg(
        20.0, 1000.0, 220.0
    ) > orbit.station_keeping_propellant_kg(10.0, 1000.0, 220.0)


def test_beta_angle_reduces_eclipse() -> None:
    low = orbit.orbit_state(650.0, beta_deg=0.0).eclipse_fraction
    high = orbit.orbit_state(650.0, beta_deg=70.0).eclipse_fraction
    assert high < low


def test_environmental_scales_with_grid_carbon() -> None:
    common = dict(
        delivered_tflops=1000.0,
        mission_years=5.0,
        facility_power_w=1.0e6,
        utilization=0.85,
        wue_l_per_kwh=1.8,
        hardware_mass_kg=10000.0,
        embodied_ef_kg_per_kg=60.0,
    )
    dirty = environmental.environmental(grid_carbon_intensity_kg_per_kwh=0.5, **common)
    clean = environmental.environmental(grid_carbon_intensity_kg_per_kwh=0.05, **common)
    assert dirty.co2e_total_kg > clean.co2e_total_kg
    assert dirty.water_l_total > 0.0


def test_space_has_no_operational_carbon_or_water() -> None:
    space = odc.load_scenario(SCEN / "orbital_1mw_inference.yaml")
    ev = odc.evaluate_space(space)
    assert ev.details["water_l_per_pflop_day"] == 0.0  # solar, no cooling water
    assert ev.details["propellant_mass_kg"] > 0.0
    assert ev.details["co2e_per_pflop_day"] > 0.0  # embodied + launch


def test_rf_backend_falls_back_to_inline() -> None:
    # Without opensatcom installed, fspl uses the inline form regardless of backend.
    inline = rf.fspl_db(2.0e6, 26.0e9, backend="inline")
    auto = rf.fspl_db(2.0e6, 26.0e9, backend="auto")
    assert math.isclose(inline, auto, rel_tol=1e-9)
    assert rf.preferred_backend() in ("inline", "opensatcom")


def test_all_earth_baselines_run() -> None:
    space = odc.load_scenario(SCEN / "orbital_1mw_inference.yaml")
    for baseline in EARTH_BASELINES:
        result = odc.compare(space, odc.load_scenario(SCEN / baseline))
        assert result.earth.lcoc_per_pflop_day > 0.0
        assert "kgCO2e/PFLOP-day" in result.summary()
