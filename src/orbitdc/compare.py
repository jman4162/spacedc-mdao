"""Evaluate scenarios and compare orbital vs terrestrial designs.

`compare(space, earth)` runs both through the discipline models and the
delivered-compute waterfall, then reports the binding constraints and the
parameter thresholds at which space would match Earth.
"""

from __future__ import annotations

import math
from dataclasses import replace

from orbitdc import diagnostics
from orbitdc.core.registry import (
    get_accelerator,
    get_battery,
    get_launch,
    get_solar_array,
)
from orbitdc.core.schema import Scenario
from orbitdc.evaluation import Evaluation
from orbitdc.models import (
    cost,
    earth_baseline,
    mass,
    network,
    orbit,
    power,
    reliability,
)
from orbitdc.thermal import thermal_codesign
from orbitdc.thermal.catalog import get_chip_stack, get_coolant, get_radiator_surface
from orbitdc.thermal.presets import get_environment
from orbitdc.waterfall import build_waterfall

# Soft cost/mass factors not yet promoted to catalogs (estimates; Phase 1).
PAYLOAD_FACTOR = 2.0  # board/chassis mass multiple over bare accelerators
COMMS_MASS_PER_SAT_KG = 30.0
AVIONICS_PROP_PER_SAT_KG = 60.0
STRUCTURE_FRAC = 0.20
MARGIN_FRAC = 0.20
BUS_COST_PER_SAT_USD = 2.0e6
COMMS_COST_PER_SAT_USD = 0.5e6
GROUND_SEGMENT_USD = 20.0e6
ANNUAL_OPS_USD = 5.0e6
EARTH_MAINTENANCE_FRAC = 0.05
RADIATOR_COST_PER_M2_USD = 5000.0  # space-qualified radiator panel


def evaluate_space(scenario: Scenario, overrides: dict[str, float] | None = None) -> Evaluation:
    """Evaluate an orbital scenario, optionally overriding named scalar drivers."""
    if scenario.kind != "space" or scenario.space is None:
        raise ValueError("evaluate_space requires a space scenario")
    o = overrides or {}
    sp = scenario.space
    arch = sp.architecture

    accel = get_accelerator(scenario.accelerator)
    array = get_solar_array(sp.solar_array)
    battery = get_battery(sp.battery)
    launch = get_launch(sp.launch)
    coolant = get_coolant(sp.coolant)
    surface = get_radiator_surface(sp.radiator_panel)
    chip_stack = get_chip_stack(sp.chip_stack, accel.tdp_w)
    thermal_env = get_environment(sp.thermal_environment)

    # Apply overrides (used by sensitivity / threshold solving).
    if "solar_specific_power_w_per_kg" in o:
        array = replace(array, specific_power_w_per_kg=o["solar_specific_power_w_per_kg"])
    if "radiator_areal_mass_kg_per_m2" in o:
        surface = replace(surface, areal_density_kg_m2=o["radiator_areal_mass_kg_per_m2"])
    launch_cost_per_kg = o.get("launch_cost_per_kg_usd", launch.cost_per_kg_usd)
    annual_failure_rate = o.get("annual_failure_rate", sp.annual_failure_rate)
    utilization = o.get("utilization", scenario.utilization)
    comm_intensity = o.get(
        "comm_intensity_bits_per_flop", scenario.workload.comm_intensity_bits_per_flop
    )
    downlink_gbps = o.get("downlink_gbps", arch.downlink_gbps)

    n_accel = scenario.n_accelerators
    n_sat = arch.satellites

    peak = n_accel * accel.peak_tflops_dense
    it_power_w = n_accel * accel.tdp_w * (1.0 + sp.it_power_overhead_frac)

    orbit_state = orbit.orbit_state(sp.orbit.altitude_km)

    # Thermal pump power is a bus load: q_waste includes pump dissipation, so the
    # array carries IT + housekeeping + pump. Solve the small fixed point directly.
    pump_frac = coolant.pump_power_fraction
    base_load_w = it_power_w * (1.0 + sp.non_it_power_frac)
    q_waste_w = base_load_w / (1.0 - pump_frac)
    non_it_effective = q_waste_w / it_power_w - 1.0

    pw = power.size_power(
        it_power_w=it_power_w,
        non_it_frac=non_it_effective,
        sunlit_fraction=orbit_state.sunlit_fraction,
        eclipse_duration_s=orbit_state.eclipse_duration_s,
        mission_years=scenario.mission_life_years,
        array=array,
        battery=battery,
    )

    area_available = arch.radiator_area_m2_per_sat * n_sat
    th = thermal_codesign(
        q_waste_w=q_waste_w,
        chip_stack=chip_stack,
        coolant=coolant,
        surface=surface,
        env=thermal_env,
        area_available_m2=area_available,
        eol=sp.thermal_eol,
    )

    rel = reliability.size_reliability(
        n_accelerators=n_accel,
        annual_failure_rate=annual_failure_rate,
        mission_years=scenario.mission_life_years,
        spare_fraction=sp.spare_fraction,
        reset_recovery_availability=sp.reset_recovery_availability,
    )

    # Compute available before the network limit, then size the network on it.
    pre_network = (
        peak
        * scenario.sustained_fraction
        * 1.0  # f_power (sized to load)
        * th.f_thermal
        * rel.f_availability
        * utilization
    )
    net = network.size_network(pre_network, comm_intensity, downlink_gbps)

    factors = {
        "software": scenario.sustained_fraction,
        "power": 1.0,
        "thermal": th.f_thermal,
        "network": net.f_network,
        "availability": rel.f_availability,
        "utilization": utilization,
    }
    wf = build_waterfall(peak, factors)
    delivered = wf.delivered_tflops

    ms = mass.mass_buildup(
        n_accelerators=n_accel,
        accel_mass_kg=accel.mass_kg,
        payload_factor=PAYLOAD_FACTOR,
        array_mass_kg=pw.array_mass_kg,
        battery_mass_kg=pw.battery_mass_kg,
        radiator_mass_kg=th.panel_mass_kg + th.coolant_mass_kg,
        n_satellites=n_sat,
        comms_mass_per_sat_kg=COMMS_MASS_PER_SAT_KG,
        avionics_propulsion_per_sat_kg=AVIONICS_PROP_PER_SAT_KG,
        structure_frac=STRUCTURE_FRAC,
        margin_frac=MARGIN_FRAC,
    )

    cr = cost.space_cost(
        n_accelerators=n_accel,
        accel_unit_cost_usd=accel.unit_cost_usd,
        accel_mass_kg=accel.mass_kg,
        payload_factor=PAYLOAD_FACTOR,
        array_cost_usd=pw.array_cost_usd,
        battery_cost_usd=pw.battery_cost_usd,
        radiator_cost_usd=th.area_installed_m2 * RADIATOR_COST_PER_M2_USD,
        n_satellites=n_sat,
        bus_cost_per_sat_usd=BUS_COST_PER_SAT_USD,
        comms_cost_per_sat_usd=COMMS_COST_PER_SAT_USD,
        launch_mass_kg=ms.dry_mass_kg,
        launch_cost_per_kg_usd=launch_cost_per_kg,
        expected_failures=rel.expected_failures,
        ground_segment_usd=GROUND_SEGMENT_USD,
        annual_ops_usd=ANNUAL_OPS_USD,
        mission_years=scenario.mission_life_years,
        discount_rate=scenario.discount_rate,
        delivered_tflops=delivered,
        delivered_fraction=wf.delivered_fraction,
    )

    details: dict[str, float] = {
        "radiator_packaging_ratio": th.packaging_ratio,
        "radiator_area_required_m2": th.area_required_m2,
        "radiator_area_available_m2": th.area_available_m2,
        "radiator_t_rad_k": th.t_rad_k,
        "chip_junction_k": th.t_junction_k,
        "radiator_net_flux_w_m2": th.net_flux_w_m2,
        "radiator_m2_per_kw": th.m2_per_kw,
        "thermal_kg_per_kw": th.kg_per_kw,
        "thermal_pump_power_kw": th.pump_power_w / 1000.0,
        "thermal_feasible": float(th.feasible),
        "network_required_gbps": net.required_gbps,
        "network_available_gbps": net.available_gbps,
        "n_launches": math.ceil(ms.dry_mass_kg / launch.capacity_kg),
        "sunlit_fraction": orbit_state.sunlit_fraction,
        "orbital_period_min": orbit_state.period_s / 60.0,
        "expected_failures": rel.expected_failures,
    }

    return Evaluation(
        label=scenario.name,
        kind="space",
        n_accelerators=n_accel,
        peak_tflops=peak,
        delivered_tflops=delivered,
        delivered_fraction=wf.delivered_fraction,
        waterfall=wf,
        lcoc_per_pflop_day=cr.lcoc_per_pflop_day,
        cost_per_accelerator_hour=cr.cost_per_accelerator_hour,
        lifecycle_pv_usd=cr.lifecycle_pv_usd,
        cost_breakdown_usd=cr.breakdown_usd,
        it_power_w=it_power_w,
        dry_mass_kg=ms.dry_mass_kg,
        specific_power_w_per_kg=it_power_w / ms.dry_mass_kg,
        kg_per_kw=ms.dry_mass_kg / (it_power_w / 1000.0),
        mass_breakdown_kg=ms.breakdown_kg,
        details=details,
        thermal_bottleneck=th.bottleneck,
        thermal_warnings=th.warnings,
    )


def evaluate_earth(scenario: Scenario) -> Evaluation:
    """Evaluate a terrestrial baseline scenario."""
    if scenario.kind != "earth" or scenario.earth is None:
        raise ValueError("evaluate_earth requires an earth scenario")
    ep = scenario.earth
    accel = get_accelerator(scenario.accelerator)

    n_accel = ep.n_accelerators
    peak = n_accel * accel.peak_tflops_dense
    it_power_w = n_accel * accel.tdp_w * (1.0 + ep.it_power_overhead_frac)

    eb = earth_baseline.earth_delivered(
        peak_tflops=peak,
        it_power_w=it_power_w,
        pue=ep.pue,
        sustained_fraction=scenario.sustained_fraction,
        availability=ep.availability,
        utilization=scenario.utilization,
    )

    factors = {
        "software": scenario.sustained_fraction,
        "power": 1.0,
        "thermal": 1.0,
        "network": 1.0,
        "availability": ep.availability,
        "utilization": scenario.utilization,
    }
    wf = build_waterfall(peak, factors)

    cr = cost.earth_cost(
        n_accelerators=n_accel,
        accel_unit_cost_usd=accel.unit_cost_usd,
        it_power_w=it_power_w,
        pue=ep.pue,
        facility_capex_per_mw_usd=ep.facility_capex_per_mw_usd,
        energy_price_per_kwh=ep.energy_price_per_kwh,
        utilization=scenario.utilization,
        annual_maintenance_frac=EARTH_MAINTENANCE_FRAC,
        mission_years=scenario.mission_life_years,
        discount_rate=scenario.discount_rate,
        delivered_tflops=eb.delivered_tflops,
        delivered_fraction=eb.delivered_fraction,
    )

    return Evaluation(
        label=scenario.name,
        kind="earth",
        n_accelerators=n_accel,
        peak_tflops=peak,
        delivered_tflops=eb.delivered_tflops,
        delivered_fraction=eb.delivered_fraction,
        waterfall=wf,
        lcoc_per_pflop_day=cr.lcoc_per_pflop_day,
        cost_per_accelerator_hour=cr.cost_per_accelerator_hour,
        lifecycle_pv_usd=cr.lifecycle_pv_usd,
        cost_breakdown_usd=cr.breakdown_usd,
        it_power_w=it_power_w,
        details={"pue": eb.pue, "facility_power_w": eb.facility_power_w},
    )


def evaluate(scenario: Scenario, overrides: dict[str, float] | None = None) -> Evaluation:
    """Dispatch on scenario kind."""
    if scenario.kind == "space":
        return evaluate_space(scenario, overrides)
    return evaluate_earth(scenario)


class ComparisonResult:
    """The outcome of comparing a space design against an Earth baseline."""

    def __init__(self, space: Scenario, earth: Scenario) -> None:
        self._space_scenario = space
        self._earth_scenario = earth
        self.space = evaluate_space(space)
        self.earth = evaluate_earth(earth)

    @property
    def space_beats_earth(self) -> bool:
        return self.space.lcoc_per_pflop_day < self.earth.lcoc_per_pflop_day

    def thresholds(self) -> dict[str, float | None]:
        """Solve for the driver values at which space LCOC equals Earth LCOC."""

        def space_lcoc_of(driver: str, value: float) -> float:
            return evaluate_space(self._space_scenario, {driver: value}).lcoc_per_pflop_day

        return diagnostics.beats_earth_thresholds(space_lcoc_of, self.earth.lcoc_per_pflop_day)

    def explain_binding_constraints(self) -> str:
        lines = ["Space design binding constraints:"]
        lines += [f"  - {n}" for n in diagnostics.binding_constraints(self.space)]
        lines.append("")
        lines.append("Space matches Earth (LCOC) at these single-parameter thresholds:")
        lines += [f"  - {s}" for s in diagnostics.format_thresholds(self.thresholds())]
        return "\n".join(lines)

    def summary(self) -> str:
        s, e = self.space, self.earth
        verdict = "SPACE wins" if self.space_beats_earth else "EARTH wins"
        ratio = (
            s.lcoc_per_pflop_day / e.lcoc_per_pflop_day
            if e.lcoc_per_pflop_day > 0
            else float("inf")
        )
        rows = [
            f"Comparison: {s.label}  vs  {e.label}",
            "",
            f"{'metric':<32}{'space':>18}{'earth':>18}",
            f"{'accelerators':<32}{s.n_accelerators:>18,}{e.n_accelerators:>18,}",
            f"{'peak TFLOP/s':<32}{s.peak_tflops:>18,.0f}{e.peak_tflops:>18,.0f}",
            f"{'delivered TFLOP/s':<32}{s.delivered_tflops:>18,.0f}{e.delivered_tflops:>18,.0f}",
            f"{'delivered fraction':<32}{s.delivered_fraction:>18.2%}{e.delivered_fraction:>18.2%}",
            f"{'LCOC $/PFLOP-day':<32}{s.lcoc_per_pflop_day:>18,.0f}{e.lcoc_per_pflop_day:>18,.0f}",
            f"{'$/accelerator-hour':<32}{s.cost_per_accelerator_hour:>18,.3f}{e.cost_per_accelerator_hour:>18,.3f}",
            "",
            f"Verdict: {verdict} on LCOC (space/earth = {ratio:.2f}x)",
        ]
        return "\n".join(rows)


def compare(space: Scenario, earth: Scenario) -> ComparisonResult:
    """Compare an orbital design against a terrestrial baseline."""
    return ComparisonResult(space, earth)
