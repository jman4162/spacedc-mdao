"""Phase 4C-2: parametric Level-4 view factors."""

from __future__ import annotations

import math

import orbitdc as odc
from orbitdc.thermal.view_factors import effective_view_factor

SPACE = "examples/scenarios/orbital_1mw_inference.yaml"


def test_no_obstruction_returns_nominal() -> None:
    vf = effective_view_factor(
        nominal=0.95, articulation_deg=0.0, self_view_frac=0.0, array_blocking_frac=0.0
    )
    assert vf.effective == 0.95


def test_losses_combine_multiplicatively() -> None:
    vf = effective_view_factor(
        nominal=0.95, articulation_deg=0.0, self_view_frac=0.05, array_blocking_frac=0.10
    )
    assert vf.effective == 0.95 * 0.95 * 0.90


def test_articulation_is_cosine() -> None:
    vf = effective_view_factor(
        nominal=1.0, articulation_deg=60.0, self_view_frac=0.0, array_blocking_frac=0.0
    )
    assert vf.effective == math.cos(math.radians(60.0))


def test_view_factor_off_by_default() -> None:
    base = odc.evaluate_space(odc.load_scenario(SPACE))
    assert base.details["thermal_view_factor"] == 1.0


def test_level4_lowers_emission_and_raises_mass() -> None:
    base = odc.load_scenario(SPACE)
    d = base.model_dump()
    d["space"]["thermal_view_factors"] = True
    level4 = odc.load_scenario_dict(d)
    b = odc.evaluate_space(base)
    f = odc.evaluate_space(level4)
    assert f.details["thermal_view_factor"] < 1.0
    # Less emission per m^2 -> more area/mass -> higher LCOC.
    assert f.details["thermal_kg_per_kw"] > b.details["thermal_kg_per_kw"]
    assert f.lcoc_per_pflop_day > b.lcoc_per_pflop_day
