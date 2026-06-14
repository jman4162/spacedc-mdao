"""Tests for the orbit-transient thermal model (Phase 3B)."""

from __future__ import annotations

from pathlib import Path

import orbitdc as odc
from orbitdc.thermal.catalog import get_radiator_surface
from orbitdc.thermal.presets import get_environment
from orbitdc.thermal.transient import transient_orbit

SPACE = Path(__file__).parents[1] / "examples" / "scenarios" / "orbital_1mw_inference.yaml"


def test_transient_timeseries_shape_and_bounds() -> None:
    tr = transient_orbit(
        q_waste_w=1.1e6,
        area_m2=768.0,
        surface=get_radiator_surface("deployable_osr"),
        env=get_environment("conservative_leo"),
        period_s=5860.0,
        sunlit_fraction=0.64,
        t_rad_target_k=337.0,
        thermal_capacitance_j_per_k=1.0e7,
        n_steps=120,
    )
    assert tr.time_s.shape == (120,)
    assert 0.0 <= tr.avg_throttle <= 1.0
    assert tr.t_min_k <= tr.t_max_k
    assert tr.sunlit_mask.sum() > 0  # part of the orbit is sunlit


def test_transient_relaxes_thermal_vs_steady() -> None:
    data = odc.load_scenario(SPACE).model_dump()
    data["space"]["architecture"]["radiator_area_m2_per_sat"] = 12.0  # thermally tight
    steady = dict(data)
    steady["space"] = {**data["space"], "thermal_fidelity": "steady"}
    transient = dict(data)
    transient["space"] = {**data["space"], "thermal_fidelity": "transient"}
    f_steady = odc.evaluate_space(odc.load_scenario_dict(steady)).waterfall.factors["thermal"]
    f_trans = odc.evaluate_space(odc.load_scenario_dict(transient)).waterfall.factors["thermal"]
    assert f_steady < 1.0  # design is thermally limited
    assert f_trans >= f_steady  # eclipse averaging cannot make it worse
