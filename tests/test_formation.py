"""Phase 4C-1: formation-flying relative dynamics and collision margin."""

from __future__ import annotations

import orbitdc as odc
from orbitdc.core.constants import R_EARTH
from orbitdc.models.formation import formation_keeping, mean_motion

SPACE = "examples/scenarios/orbital_1mw_inference.yaml"


def test_mean_motion_matches_period() -> None:
    import math

    r = R_EARTH + 650e3
    n = mean_motion(r)
    # n = 2 pi / T; a 650 km LEO orbit is ~98 min.
    period_min = (2 * math.pi / n) / 60.0
    assert 95.0 < period_min < 100.0


def test_collision_margin_scales_with_separation() -> None:
    common = dict(
        altitude_km=650.0,
        drag_deltav_per_year_ms=2.3,
        differential_drag_frac=0.05,
        position_uncertainty_m=50.0,
    )
    tight = formation_keeping(separation_m=300.0, **common)
    wide = formation_keeping(separation_m=5000.0, **common)
    assert tight.collision_margin_sigmas < wide.collision_margin_sigmas
    # A tighter formation needs collision-avoidance maneuvers; a loose one does not.
    assert tight.collision_avoidance_deltav_per_year_ms > 0.0
    assert wide.collision_avoidance_deltav_per_year_ms == 0.0
    assert tight.formation_deltav_per_year_ms > wide.formation_deltav_per_year_ms


def test_drift_deltav_is_a_fraction_of_drag() -> None:
    fk = formation_keeping(
        altitude_km=650.0,
        drag_deltav_per_year_ms=10.0,
        differential_drag_frac=0.05,
        separation_m=2000.0,
        position_uncertainty_m=50.0,
    )
    assert fk.drift_deltav_per_year_ms == 0.05 * 10.0


def test_formation_surfaced_in_compare() -> None:
    space = odc.load_scenario(SPACE)
    tight = odc.evaluate_space(space, {"formation_separation_m": 300.0})
    wide = odc.evaluate_space(space, {"formation_separation_m": 5000.0})
    assert tight.details["collision_margin_sigmas"] < wide.details["collision_margin_sigmas"]
    assert tight.details["station_keeping_deltav_ms"] >= wide.details["station_keeping_deltav_ms"]


def test_single_satellite_has_no_formation() -> None:
    space = odc.load_scenario(SPACE)
    one = odc.evaluate_space(space, {"n_satellites": 1})
    assert one.details["formation_deltav_per_year_ms"] == 0.0
    assert one.details["collision_margin_sigmas"] == float("inf")
