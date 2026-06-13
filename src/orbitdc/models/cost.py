"""Cost model (EQUATIONS.md §11).

Lifecycle cost on a present-value basis, plus levelized cost of compute (LCOC).
Capex lands at t=0; opex and replacement are annual streams; delivered compute
is its own discounted stream. Levelizing matters because space economics depend
on mission life, degradation, failure rate, and utilization, not just capex.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.core.constants import HOURS_PER_YEAR


@dataclass(frozen=True)
class CostResult:
    capex_usd: float
    annual_opex_usd: float
    lifecycle_pv_usd: float
    lcoc_per_pflop_day: float
    cost_per_accelerator_hour: float
    breakdown_usd: dict[str, float]


def _periods(mission_years: float) -> int:
    return max(1, round(mission_years))


def _pflop_days_per_year(delivered_tflops: float) -> float:
    return delivered_tflops / 1000.0 * 365.25


def _levelize(
    capex: float,
    annual_cost: float,
    annual_delivered: float,
    annual_accel_hours: float,
    mission_years: float,
    rate: float,
) -> tuple[float, float, float]:
    """Return (lifecycle_pv, lcoc_per_pflop_day, cost_per_accel_hour)."""
    pv_cost = capex
    pv_delivered = 0.0
    pv_accel_hours = 0.0
    for t in range(1, _periods(mission_years) + 1):
        discount = (1.0 + rate) ** t
        pv_cost += annual_cost / discount
        pv_delivered += annual_delivered / discount
        pv_accel_hours += annual_accel_hours / discount
    lcoc = pv_cost / pv_delivered if pv_delivered > 0.0 else float("inf")
    per_hour = pv_cost / pv_accel_hours if pv_accel_hours > 0.0 else float("inf")
    return pv_cost, lcoc, per_hour


def space_cost(
    *,
    n_accelerators: int,
    accel_unit_cost_usd: float,
    accel_mass_kg: float,
    payload_factor: float,
    array_cost_usd: float,
    battery_cost_usd: float,
    radiator_cost_usd: float,
    n_satellites: int,
    bus_cost_per_sat_usd: float,
    comms_cost_per_sat_usd: float,
    launch_mass_kg: float,
    launch_cost_per_kg_usd: float,
    expected_failures: float,
    ground_segment_usd: float,
    annual_ops_usd: float,
    mission_years: float,
    discount_rate: float,
    delivered_tflops: float,
    delivered_fraction: float,
) -> CostResult:
    accel_cost = n_accelerators * accel_unit_cost_usd
    bus_cost = n_satellites * bus_cost_per_sat_usd
    comms_cost = n_satellites * comms_cost_per_sat_usd
    launch_cost = launch_mass_kg * launch_cost_per_kg_usd

    breakdown = {
        "accelerators": accel_cost,
        "solar": array_cost_usd,
        "battery": battery_cost_usd,
        "radiator": radiator_cost_usd,
        "bus_integration": bus_cost,
        "comms": comms_cost,
        "launch": launch_cost,
        "ground_segment": ground_segment_usd,
    }
    capex = sum(breakdown.values())

    # Replacement: resupply failed accelerators (hardware + their launch mass).
    replacement_per_year = (
        expected_failures
        * (accel_unit_cost_usd + accel_mass_kg * payload_factor * launch_cost_per_kg_usd)
        / mission_years
    )
    annual_opex = annual_ops_usd + replacement_per_year
    breakdown["replacement_total"] = replacement_per_year * mission_years
    breakdown["ops_total"] = annual_ops_usd * mission_years

    annual_delivered = _pflop_days_per_year(delivered_tflops)
    annual_accel_hours = n_accelerators * HOURS_PER_YEAR * delivered_fraction
    lifecycle_pv, lcoc, per_hour = _levelize(
        capex, annual_opex, annual_delivered, annual_accel_hours, mission_years, discount_rate
    )
    return CostResult(
        capex_usd=capex,
        annual_opex_usd=annual_opex,
        lifecycle_pv_usd=lifecycle_pv,
        lcoc_per_pflop_day=lcoc,
        cost_per_accelerator_hour=per_hour,
        breakdown_usd=breakdown,
    )


def earth_cost(
    *,
    n_accelerators: int,
    accel_unit_cost_usd: float,
    it_power_w: float,
    pue: float,
    facility_capex_per_mw_usd: float,
    energy_price_per_kwh: float,
    utilization: float,
    annual_maintenance_frac: float,
    mission_years: float,
    discount_rate: float,
    delivered_tflops: float,
    delivered_fraction: float,
) -> CostResult:
    accel_cost = n_accelerators * accel_unit_cost_usd
    facility_capex = facility_capex_per_mw_usd * (it_power_w / 1e6)
    breakdown = {"accelerators": accel_cost, "facility": facility_capex}
    capex = sum(breakdown.values())

    facility_power_w = it_power_w * pue
    annual_energy_kwh = facility_power_w / 1000.0 * HOURS_PER_YEAR * utilization
    annual_energy_cost = annual_energy_kwh * energy_price_per_kwh
    annual_maintenance = annual_maintenance_frac * capex
    annual_opex = annual_energy_cost + annual_maintenance
    breakdown["energy_total"] = annual_energy_cost * mission_years
    breakdown["maintenance_total"] = annual_maintenance * mission_years

    annual_delivered = _pflop_days_per_year(delivered_tflops)
    annual_accel_hours = n_accelerators * HOURS_PER_YEAR * delivered_fraction
    lifecycle_pv, lcoc, per_hour = _levelize(
        capex, annual_opex, annual_delivered, annual_accel_hours, mission_years, discount_rate
    )
    return CostResult(
        capex_usd=capex,
        annual_opex_usd=annual_opex,
        lifecycle_pv_usd=lifecycle_pv,
        lcoc_per_pflop_day=lcoc,
        cost_per_accelerator_hour=per_hour,
        breakdown_usd=breakdown,
    )
