"""Power model (EQUATIONS.md §3).

The solar array and battery are sized to carry the continuous load through
sunlit and eclipse phases, so power "closes" by construction. The feasibility
pressure from power therefore shows up downstream as array/battery mass and
cost (and ultimately launch mass), not as a throttle on compute.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.core.constants import SOLAR_CONSTANT
from orbitdc.core.registry import Battery, SolarArray


@dataclass(frozen=True)
class PowerResult:
    load_w: float  # continuous IT + housekeeping load
    array_eol_sunlit_w: float  # required array output at end of life, sunlit
    array_bol_w: float  # required array output at beginning of life
    array_area_m2: float
    array_mass_kg: float
    array_cost_usd: float
    battery_energy_wh: float
    battery_mass_kg: float
    battery_cost_usd: float


def size_power(
    it_power_w: float,
    non_it_frac: float,
    sunlit_fraction: float,
    eclipse_duration_s: float,
    mission_years: float,
    array: SolarArray,
    battery: Battery,
) -> PowerResult:
    """Size the solar array and battery to carry the load over a full orbit."""
    load_w = it_power_w * (1.0 + non_it_frac)

    f_sun = sunlit_fraction
    if not 0.0 < f_sun <= 1.0:
        raise ValueError("sunlit_fraction must be in (0, 1]")
    eclipse_share = (1.0 - f_sun) / f_sun  # t_eclipse / t_sunlit

    # Energy balance: array must power the load in sunlight and recharge the
    # battery for eclipse (with round-trip loss).
    array_eol_w = load_w * (1.0 + eclipse_share / battery.round_trip_efficiency)

    # Beginning-of-life output, before annual degradation.
    array_bol_w = array_eol_w / (1.0 - array.annual_degradation) ** mission_years

    area_m2 = array_bol_w / (
        SOLAR_CONSTANT
        * array.cell_efficiency
        * array.packing_efficiency
        * array.pointing_efficiency
    )
    array_mass_kg = array_bol_w / array.specific_power_w_per_kg
    array_cost_usd = array_bol_w * array.cost_per_w_usd

    # Battery: carry the load through the longest eclipse, limited by DOD.
    eclipse_hours = eclipse_duration_s / 3600.0
    battery_energy_wh = load_w * eclipse_hours / battery.depth_of_discharge
    battery_mass_kg = battery_energy_wh / battery.specific_energy_wh_per_kg
    battery_cost_usd = battery_energy_wh * battery.cost_per_wh_usd

    return PowerResult(
        load_w=load_w,
        array_eol_sunlit_w=array_eol_w,
        array_bol_w=array_bol_w,
        array_area_m2=area_m2,
        array_mass_kg=array_mass_kg,
        array_cost_usd=array_cost_usd,
        battery_energy_wh=battery_energy_wh,
        battery_mass_kg=battery_mass_kg,
        battery_cost_usd=battery_cost_usd,
    )
