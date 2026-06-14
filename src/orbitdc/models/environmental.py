"""Environmental accounting (EQUATIONS.md §13).

Operational, embodied, and launch carbon plus water, normalized per unit of
delivered compute. Space is not automatically "green": it trades operational
grid carbon and water for embodied and launch carbon. These figures are
lower-confidence than the physics and should be read as order-of-magnitude.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.core.constants import HOURS_PER_YEAR

# Default emission factors (lower confidence; order-of-magnitude).
SPACECRAFT_EMBODIED_KG_PER_KG = 80.0  # kgCO2e per kg of spacecraft hardware
SERVER_EMBODIED_KG_PER_KG = 60.0  # kgCO2e per kg of terrestrial hardware
PROPELLANT_EF_KG_PER_KG = 3.0  # kgCO2e per kg propellant burned (+ manufacturing)


@dataclass(frozen=True)
class EnvironmentalResult:
    co2e_total_kg: float
    co2e_per_pflop_day: float
    water_l_total: float
    water_l_per_pflop_day: float
    breakdown_kg: dict[str, float]


def _delivered_pflop_days(delivered_tflops: float, mission_years: float) -> float:
    return delivered_tflops / 1000.0 * 365.25 * mission_years


def environmental(
    *,
    delivered_tflops: float,
    mission_years: float,
    facility_power_w: float,
    utilization: float,
    grid_carbon_intensity_kg_per_kwh: float,
    wue_l_per_kwh: float,
    hardware_mass_kg: float,
    embodied_ef_kg_per_kg: float,
    propellant_mass_kg: float = 0.0,
) -> EnvironmentalResult:
    """Lifecycle CO2e and water, normalized per delivered PFLOP-day."""
    lifetime_energy_kwh = facility_power_w / 1000.0 * HOURS_PER_YEAR * mission_years * utilization

    operational = lifetime_energy_kwh * grid_carbon_intensity_kg_per_kwh
    embodied = hardware_mass_kg * embodied_ef_kg_per_kg
    launch = propellant_mass_kg * PROPELLANT_EF_KG_PER_KG
    breakdown = {"operational": operational, "embodied": embodied, "launch": launch}
    total = operational + embodied + launch

    water = lifetime_energy_kwh * wue_l_per_kwh
    delivered = _delivered_pflop_days(delivered_tflops, mission_years)
    per = (total / delivered) if delivered > 0.0 else float("inf")
    water_per = (water / delivered) if delivered > 0.0 else float("inf")

    return EnvironmentalResult(
        co2e_total_kg=total,
        co2e_per_pflop_day=per,
        water_l_total=water,
        water_l_per_pflop_day=water_per,
        breakdown_kg=breakdown,
    )
