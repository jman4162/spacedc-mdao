"""Phase 4C-3: thermal Level-5 mission-integrated degradation."""

from __future__ import annotations

import orbitdc as odc
from orbitdc.thermal.catalog import get_radiator_surface
from orbitdc.thermal.degradation import mission_thermal_derate
from orbitdc.thermal.presets import get_environment

SPACE = "examples/scenarios/orbital_1mw_inference.yaml"


def _surface_env() -> tuple[object, object]:
    return get_radiator_surface("deployable_osr"), get_environment("good_engineering")


def test_mmod_lowers_derate() -> None:
    surface, env = _surface_env()
    common = dict(mission_years=5.0, t_rad_k=320.0, surface=surface, env=env)
    low = mission_thermal_derate(mmod_area_loss_per_year=0.0, **common)
    high = mission_thermal_derate(mmod_area_loss_per_year=0.02, **common)
    assert high.derate < low.derate
    assert high.mmod_area_retained < low.mmod_area_retained


def test_longer_mission_loses_more_area() -> None:
    surface, env = _surface_env()
    common = dict(t_rad_k=320.0, surface=surface, env=env, mmod_area_loss_per_year=0.01)
    short = mission_thermal_derate(mission_years=2.0, **common)
    long = mission_thermal_derate(mission_years=10.0, **common)
    assert long.mmod_area_retained < short.mmod_area_retained
    assert long.derate < short.derate


def test_loop_out_reduces_availability() -> None:
    surface, env = _surface_env()
    common = dict(mission_years=5.0, t_rad_k=320.0, surface=surface, env=env)
    safe = mission_thermal_derate(loop_out_prob_per_year=0.0, **common)
    risky = mission_thermal_derate(loop_out_prob_per_year=0.10, **common)
    assert risky.loop_availability < safe.loop_availability


def test_degradation_off_by_default() -> None:
    base = odc.evaluate_space(odc.load_scenario(SPACE))
    assert base.details["thermal_degradation_derate"] == 1.0


def test_level5_does_not_improve_f_thermal() -> None:
    base = odc.load_scenario(SPACE)
    d = base.model_dump()
    d["space"]["thermal_degradation"] = True
    d["space"]["mmod_area_loss_per_year"] = 0.02
    level5 = odc.load_scenario_dict(d)
    b = odc.evaluate_space(base)
    g = odc.evaluate_space(level5)
    assert g.details["thermal_degradation_derate"] < 1.0
    assert g.waterfall.factors["thermal"] <= b.waterfall.factors["thermal"]
