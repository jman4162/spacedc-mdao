"""Golden tests for the thermal radiator co-design module (sub-phase 2A).

Each check is hand-derivable or anchored to a cited reference
(THEMRAL_RADIATOR_DEEPDIVE).
"""

from __future__ import annotations

import math

from orbitdc.thermal import diagnosis, thermal_codesign
from orbitdc.thermal.catalog import (
    get_chip_stack,
    get_coating,
    get_coolant,
    get_radiator_surface,
)
from orbitdc.thermal.coolant import size_coolant
from orbitdc.thermal.network import junction_temperature_k, max_radiator_temp_k
from orbitdc.thermal.presets import get_environment
from orbitdc.thermal.radiation import net_flux_w_m2, required_area_m2
from orbitdc.thermal.surfaces import RadiatorSurface, ThermalEnvironment
from orbitdc.thermal.validation import ISS_PVR, ideal_area_for_mw


def test_ideal_table_matches_deep_dive() -> None:
    # One-sided eps=0.9, no absorption: the deep-dive sanity table.
    assert math.isclose(ideal_area_for_mw(300.0), 2419.0, rel_tol=2e-3)
    assert math.isclose(ideal_area_for_mw(350.0), 1306.0, rel_tol=2e-3)
    assert math.isclose(ideal_area_for_mw(600.0), 151.0, rel_tol=5e-3)


def test_net_flux_subtracts_absorbed_environment() -> None:
    surface = get_radiator_surface("deployable_osr")  # OSR, two-sided
    deep_space = ThermalEnvironment(sun_incidence_cos=0.0, view_factor_earth=0.0)
    sunny = ThermalEnvironment(sun_incidence_cos=0.5, view_factor_earth=0.2)
    # Absorbing environment must reduce net rejection.
    assert net_flux_w_m2(320.0, surface, sunny) < net_flux_w_m2(320.0, surface, deep_space)


def test_eol_area_exceeds_bol() -> None:
    surface = get_radiator_surface("deployable_osr")
    env = get_environment("conservative_leo")
    bol = required_area_m2(1.0e6, 320.0, surface, env, eol=False)
    eol = required_area_m2(1.0e6, 320.0, surface, env, eol=True)
    assert eol >= bol  # coatings degrade: alpha up, eps down


def test_coating_eol_worse_than_bol() -> None:
    osr = get_coating("osr")
    assert osr.alpha(eol=True) >= osr.alpha(eol=False)
    assert osr.eps(eol=True) <= osr.eps(eol=False)


def test_junction_stack_sets_radiator_ceiling() -> None:
    stack = get_chip_stack("h100_direct_liquid", chip_power_w=700.0)
    # T_rad_max = Tj_max - Q*R_total; junction at that T_rad equals Tj_max.
    t_rad_max = max_radiator_temp_k(stack)
    assert math.isclose(junction_temperature_k(t_rad_max, stack), stack.tj_max_k, rel_tol=1e-9)
    assert t_rad_max < stack.tj_max_k


def test_coolant_pump_power_is_fraction_of_q() -> None:
    loop = get_coolant("ammonia_single_phase")
    res = size_coolant(1.0e6, loop)
    assert math.isclose(res.pump_power_w, loop.pump_power_fraction * 1.0e6, rel_tol=1e-12)


def test_codesign_one_mw_chip_limited() -> None:
    stack = get_chip_stack("h100_direct_liquid", chip_power_w=700.0)
    coolant = get_coolant("ammonia_single_phase")
    surface = get_radiator_surface("deployable_osr")
    env = get_environment("conservative_leo")
    res = thermal_codesign(
        q_waste_w=1.0e6,
        chip_stack=stack,
        coolant=coolant,
        surface=surface,
        env=env,
        area_available_m2=5000.0,
    )
    assert res.feasible
    assert res.bottleneck == diagnosis.CHIP_LIMITED  # junction sets T_rad
    assert res.t_rad_k < surface.max_temp_k
    # Thermal mass is a real burden: order tonnes per MW.
    assert 5.0 < res.kg_per_kw < 40.0


def test_two_sided_sun_warning_fires() -> None:
    surface = RadiatorSurface(coating=get_coating("osr"), sides=2)
    env = ThermalEnvironment(sun_incidence_cos=0.5)
    stack = get_chip_stack("h100_direct_liquid", chip_power_w=700.0)
    coolant = get_coolant("ammonia_single_phase")
    res = thermal_codesign(
        q_waste_w=1.0e6,
        chip_stack=stack,
        coolant=coolant,
        surface=surface,
        env=env,
        area_available_m2=5000.0,
    )
    assert any("two-sided" in w for w in res.warnings)


def test_iss_pvr_anchor_sane() -> None:
    # 14 kW over 42.4 m^2 ~ 330 W/m^2; areal ~17.5 kg/m^2.
    assert ISS_PVR.net_w_m2 is not None and 300.0 < ISS_PVR.net_w_m2 < 360.0
    assert ISS_PVR.areal_density_kg_m2 is not None and 15.0 < ISS_PVR.areal_density_kg_m2 < 20.0
