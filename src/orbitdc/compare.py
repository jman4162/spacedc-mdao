"""Evaluate scenarios and compare orbital vs terrestrial designs.

`compare(space, earth)` runs both through the discipline models and the
delivered-compute waterfall, then reports the binding constraints and the
parameter thresholds at which space would match Earth.
"""

from __future__ import annotations

import logging
import math
from dataclasses import replace
from typing import TYPE_CHECKING

from orbitdc import diagnostics

if TYPE_CHECKING:
    from orbitdc.optimize.uncertainty import MonteCarloResult
from orbitdc.core import catalog_loader
from orbitdc.core.registry import (
    get_accelerator,
    get_battery,
    get_launch,
    get_solar_array,
    provenance,
)
from orbitdc.core.schema import Scenario
from orbitdc.evaluation import Evaluation
from orbitdc.models import (
    comms_link,
    cost,
    earth_baseline,
    environmental,
    mass,
    network,
    orbit,
    power,
    radiation,
    reliability,
    rf,
)
from orbitdc.thermal import thermal_codesign
from orbitdc.thermal.catalog import get_chip_stack, get_coolant, get_radiator_surface
from orbitdc.thermal.presets import get_environment
from orbitdc.thermal.transient import TransientResult, transient_orbit
from orbitdc.waterfall import build_waterfall

# Soft cost/mass factors, loaded from provenance-tagged catalogs (Phase 3A).
_MASS = catalog_loader.entry("mass_structure.yaml", "default")
_COST = catalog_loader.entry("cost_structure.yaml", "default")
PAYLOAD_FACTOR = _MASS["payload_factor"]
COMMS_MASS_PER_SAT_KG = _MASS["comms_mass_per_sat_kg"]
AVIONICS_PROP_PER_SAT_KG = _MASS["avionics_propulsion_per_sat_kg"]
STRUCTURE_FRAC = _MASS["structure_frac"]
MARGIN_FRAC = _MASS["margin_frac"]
BUS_COST_PER_SAT_USD = _COST["bus_cost_per_sat_usd"]
COMMS_COST_PER_SAT_USD = _COST["comms_cost_per_sat_usd"]
GROUND_SEGMENT_USD = _COST["ground_segment_usd"]
ANNUAL_OPS_USD = _COST["annual_ops_usd"]
EARTH_MAINTENANCE_FRAC = _COST["earth_maintenance_frac"]
RADIATOR_COST_PER_M2_USD = _COST["radiator_cost_per_m2_usd"]
ALUMINUM_CP_J_PER_KG_K = 900.0  # radiator thermal capacitance (specific heat)

logger = logging.getLogger("orbitdc")


def _launch_cost_for_case(launch_key: str, case: str, nominal: float) -> float:
    """Resolve launch $/kg for a scenario case from the catalog distribution."""
    if case == "speculative":
        return get_launch("aggressive_future").cost_per_kg_usd
    prov = provenance("launch").get(launch_key, {}).get("cost_per_kg_usd")
    if prov is not None:
        if case == "pessimistic" and prov.high is not None:
            return prov.high
        if case == "aggressive" and prov.low is not None:
            return prov.low
    return nominal


def evaluate_space(scenario: Scenario, overrides: dict[str, float] | None = None) -> Evaluation:
    """Evaluate an orbital scenario, optionally overriding named scalar drivers."""
    if scenario.kind != "space" or scenario.space is None:
        raise ValueError("evaluate_space requires a space scenario")
    o = overrides or {}
    for key, val in o.items():
        if not math.isfinite(val) or val < 0.0:
            raise ValueError(f"override {key}={val!r} must be finite and non-negative")
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
    base_launch_cost = _launch_cost_for_case(sp.launch, sp.launch_case, launch.cost_per_kg_usd)
    launch_cost_per_kg = o.get("launch_cost_per_kg_usd", base_launch_cost)
    radiator_cost_per_m2 = o.get("radiator_cost_per_m2_usd", RADIATOR_COST_PER_M2_USD)
    annual_failure_rate = o.get("annual_failure_rate", sp.annual_failure_rate)
    utilization = o.get("utilization", scenario.utilization)
    wl = scenario.workload
    if wl.workload_type and "comm_intensity_bits_per_flop" not in wl.model_fields_set:
        base_comm = catalog_loader.entry("workloads.yaml", wl.workload_type)[
            "comm_intensity_bits_per_flop"
        ]
    else:
        base_comm = wl.comm_intensity_bits_per_flop
    comm_intensity = o.get("comm_intensity_bits_per_flop", base_comm)
    downlink_gbps = o.get("downlink_gbps", arch.downlink_gbps)
    # Architecture overrides (used by mixed-integer optimization).
    n_sat = int(o.get("n_satellites", arch.satellites))
    accel_per_sat = int(o.get("accelerators_per_satellite", arch.accelerators_per_satellite))
    altitude_km = o.get("altitude_km", sp.orbit.altitude_km)
    t_rad_setpoint = o.get("radiator_t_rad_setpoint_k")

    n_accel = n_sat * accel_per_sat
    peak = n_accel * accel.peak_tflops_dense
    it_power_w = n_accel * accel.tdp_w * (1.0 + sp.it_power_overhead_frac)

    orbit_state = orbit.orbit_state(altitude_km, sp.beta_deg)

    # Thermal pump power is a bus load: q_waste includes pump dissipation, so the
    # array carries IT + housekeeping + pump. Solve the small fixed point directly.
    pump_frac = coolant.pump_power_fraction
    # Duty cycle sizes power+thermal for the bursty workload's average load.
    base_load_w = it_power_w * sp.duty_cycle_fraction * (1.0 + sp.non_it_power_frac)
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

    # Power closure: if the sized array exceeds the deployable budget, the design
    # is power-limited and compute throttles.
    solar_area_available = arch.solar_area_m2_per_sat * n_sat
    solar_packaging_ratio = pw.array_area_m2 / solar_area_available
    f_power = min(1.0, 1.0 / solar_packaging_ratio)

    area_available = arch.radiator_area_m2_per_sat * n_sat
    th = thermal_codesign(
        q_waste_w=q_waste_w,
        chip_stack=chip_stack,
        coolant=coolant,
        surface=surface,
        env=thermal_env,
        area_available_m2=area_available,
        eol=sp.thermal_eol,
        t_rad_override=t_rad_setpoint,
    )

    # Radiation: orbit + hardware tolerance add to the (non-radiation) base rate.
    rad = radiation.radiation_failure_contribution(
        altitude_km=altitude_km,
        inclination_deg=sp.orbit.inclination_deg or 0.0,
        mission_years=scenario.mission_life_years,
        tid_tolerance_krad=accel.tid_tolerance_krad,
        seu_susceptibility=accel.seu_susceptibility,
        ecc_mitigation=accel.ecc_mitigation,
    )
    effective_failure_rate = annual_failure_rate + rad.failure_rate_per_year

    rel = reliability.size_reliability(
        n_accelerators=n_accel,
        annual_failure_rate=effective_failure_rate,
        mission_years=scenario.mission_life_years,
        spare_fraction=sp.spare_fraction,
        reset_recovery_availability=sp.reset_recovery_availability,
    )

    # Transient thermal (optional): orbit-averaging relaxes the worst-case limit
    # because eclipse phases reject more heat than the hot sunlit phase.
    f_thermal_used = th.f_thermal
    if sp.thermal_fidelity == "transient" and th.feasible:
        tr = transient_orbit(
            q_waste_w=q_waste_w,
            area_m2=th.area_installed_m2,
            surface=surface,
            env=thermal_env,
            period_s=orbit_state.period_s,
            sunlit_fraction=orbit_state.sunlit_fraction,
            t_rad_target_k=th.t_rad_k,
            thermal_capacitance_j_per_k=th.thermal_mass_kg * ALUMINUM_CP_J_PER_KG_K,
            freeze_temp_k=coolant.freeze_temp_k,
        )
        f_thermal_used = tr.avg_throttle

    # Compute available before the network limit, then size the network on it.
    pre_network = (
        peak
        * scenario.sustained_fraction
        * f_power
        * f_thermal_used
        * rel.f_availability
        * utilization
    )
    net = network.size_network(pre_network, comm_intensity, downlink_gbps)

    # Optical ground downlinks lose availability to weather; RF TT&C must close.
    comms = catalog_loader.entry("comms.yaml", "default")
    optical_availability = (
        comms["optical_downlink_availability"] if arch.downlink_type == "optical" else 1.0
    )

    # Crosslink capacity derived from formation geometry + the optical link budget
    # (unless the scenario set crosslink_gbps explicitly). Internal traffic that
    # exceeds it throttles compute too.
    if "crosslink_gbps" in arch.model_fields_set:
        crosslink_gbps = arch.crosslink_gbps
    else:
        crosslink_gbps = comms_link.crosslink_capacity(
            separation_m=arch.formation_separation_m,
            tx_power_w=comms["crosslink_tx_power_w"],
            tx_aperture_m=comms["crosslink_aperture_m"],
            rx_aperture_m=comms["crosslink_aperture_m"],
            wavelength_m=comms["crosslink_wavelength_m"],
            pointing_error_rad=comms["crosslink_pointing_error_rad"],
            dwdm_channels=int(comms["crosslink_dwdm_channels"]),
            rx_sensitivity_photons_per_bit=comms["crosslink_rx_sensitivity_photons_per_bit"],
        ).capacity_gbps
    crosslink_gbps = o.get("crosslink_gbps", crosslink_gbps)
    f_crosslink = 1.0 if net.required_gbps <= 0.0 else min(1.0, crosslink_gbps / net.required_gbps)
    slant_range_m = sp.orbit.altitude_km * 1000.0 * 2.0  # rough low-elevation slant range
    ttc_link = rf.link_margin(
        tx_power_dbw=comms["ttc_tx_power_dbw"],
        tx_gain_dbi=comms["ttc_sat_gain_dbi"],
        rx_gain_dbi=rf.aperture_gain_dbi(comms["ttc_ground_aperture_m"], comms["ttc_freq_hz"]),
        range_m=slant_range_m,
        freq_hz=comms["ttc_freq_hz"],
        system_noise_temp_k=comms["ttc_system_noise_temp_k"],
        data_rate_bps=comms["ttc_data_rate_bps"],
        required_ebn0_db=comms["ttc_required_ebn0_db"],
        other_losses_db=comms["ttc_other_losses_db"],
    )

    factors = {
        "software": scenario.sustained_fraction,
        "power": f_power,
        "thermal": f_thermal_used,
        "network": min(net.f_network, f_crosslink) * optical_availability,
        "availability": rel.f_availability,
        "utilization": utilization,
    }
    wf = build_waterfall(peak, factors)
    delivered = wf.delivered_tflops

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "%s: it_power=%.0f kW q_waste=%.0f kW T_rad=%.0f K factors=%s "
            "crosslink=%.0f Gbps failure=%.3f/yr delivered=%.0f TFLOP/s",
            scenario.name,
            it_power_w / 1000.0,
            q_waste_w / 1000.0,
            th.t_rad_k,
            {k: round(v, 3) for k, v in factors.items()},
            crosslink_gbps,
            effective_failure_rate,
            delivered,
        )

    ms = mass.mass_buildup(
        n_accelerators=n_accel,
        accel_mass_kg=accel.mass_kg,
        payload_factor=PAYLOAD_FACTOR,
        array_mass_kg=pw.array_mass_kg * f_power,
        battery_mass_kg=pw.battery_mass_kg * f_power,
        radiator_mass_kg=th.panel_mass_kg + th.coolant_mass_kg,
        n_satellites=n_sat,
        comms_mass_per_sat_kg=COMMS_MASS_PER_SAT_KG,
        avionics_propulsion_per_sat_kg=AVIONICS_PROP_PER_SAT_KG,
        structure_frac=STRUCTURE_FRAC,
        margin_frac=MARGIN_FRAC,
    )

    # Station-keeping: propellant to offset drag over the mission.
    drag_area = sp.drag_area_m2_per_sat * n_sat
    deltav_ms = (
        orbit.drag_deltav_per_year_ms(altitude_km, drag_area, ms.dry_mass_kg)
        * scenario.mission_life_years
    )
    propellant_kg = orbit.station_keeping_propellant_kg(
        deltav_ms, ms.dry_mass_kg, sp.thruster_isp_s
    )
    launch_mass_kg = ms.dry_mass_kg + propellant_kg

    # Environmental: space operates on solar (no grid carbon/water); embodied +
    # launch carbon dominate.
    env_result = environmental.environmental(
        delivered_tflops=delivered,
        mission_years=scenario.mission_life_years,
        facility_power_w=pw.load_w,
        utilization=utilization,
        grid_carbon_intensity_kg_per_kwh=0.0,
        wue_l_per_kwh=0.0,
        hardware_mass_kg=ms.dry_mass_kg,
        embodied_ef_kg_per_kg=environmental.SPACECRAFT_EMBODIED_KG_PER_KG,
        propellant_mass_kg=propellant_kg,
    )

    cr = cost.space_cost(
        n_accelerators=n_accel,
        accel_unit_cost_usd=accel.unit_cost_usd,
        accel_mass_kg=accel.mass_kg,
        payload_factor=PAYLOAD_FACTOR,
        array_cost_usd=pw.array_cost_usd * f_power,
        battery_cost_usd=pw.battery_cost_usd * f_power,
        radiator_cost_usd=th.area_installed_m2 * radiator_cost_per_m2,
        n_satellites=n_sat,
        bus_cost_per_sat_usd=BUS_COST_PER_SAT_USD,
        comms_cost_per_sat_usd=COMMS_COST_PER_SAT_USD,
        launch_mass_kg=launch_mass_kg,
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
        "solar_packaging_ratio": solar_packaging_ratio,
        "radiator_area_required_m2": th.area_required_m2,
        "radiator_area_available_m2": th.area_available_m2,
        "radiator_t_rad_k": th.t_rad_k,
        "chip_junction_k": th.t_junction_k,
        "hbm_margin_k": th.hbm_margin_k if th.hbm_margin_k is not None else float("nan"),
        "radiator_net_flux_w_m2": th.net_flux_w_m2,
        "radiator_m2_per_kw": th.m2_per_kw,
        "thermal_kg_per_kw": th.kg_per_kw,
        "thermal_pump_power_kw": th.pump_power_w / 1000.0,
        "bus_load_w": q_waste_w,
        "thermal_feasible": float(th.feasible),
        "network_required_gbps": net.required_gbps,
        "network_available_gbps": net.available_gbps,
        "rf_ttc_margin_db": ttc_link.margin_db,
        "optical_downlink_availability": optical_availability,
        "crosslink_capacity_gbps": crosslink_gbps,
        "crosslink_factor": f_crosslink,
        "n_launches": math.ceil(launch_mass_kg / launch.capacity_kg),
        "sunlit_fraction": orbit_state.sunlit_fraction,
        "eclipse_fraction": orbit_state.eclipse_fraction,
        "orbital_period_min": orbit_state.period_s / 60.0,
        "expected_failures": rel.expected_failures,
        "tid_dose_krad": rad.tid_dose_krad,
        "radiation_failure_rate": rad.failure_rate_per_year,
        "total_failure_rate": effective_failure_rate,
        "station_keeping_deltav_ms": deltav_ms,
        "launch_cost_per_kg_usd": launch_cost_per_kg,
        "propellant_mass_kg": propellant_kg,
        "co2e_per_pflop_day": env_result.co2e_per_pflop_day,
        "co2e_total_t": env_result.co2e_total_kg / 1000.0,
        "water_l_per_pflop_day": env_result.water_l_per_pflop_day,
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

    env_e = environmental.environmental(
        delivered_tflops=eb.delivered_tflops,
        mission_years=scenario.mission_life_years,
        facility_power_w=eb.facility_power_w,
        utilization=scenario.utilization,
        grid_carbon_intensity_kg_per_kwh=ep.grid_carbon_intensity_kg_per_kwh,
        wue_l_per_kwh=ep.wue_l_per_kwh,
        hardware_mass_kg=n_accel * accel.mass_kg * PAYLOAD_FACTOR,
        embodied_ef_kg_per_kg=environmental.SERVER_EMBODIED_KG_PER_KG,
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
        details={
            "pue": eb.pue,
            "facility_power_w": eb.facility_power_w,
            "co2e_per_pflop_day": env_e.co2e_per_pflop_day,
            "co2e_total_t": env_e.co2e_total_kg / 1000.0,
            "water_l_per_pflop_day": env_e.water_l_per_pflop_day,
        },
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

    def monte_carlo(self, n: int = 500, seed: int = 0) -> MonteCarloResult:
        """Monte Carlo over the default drivers vs this Earth baseline (for the fan chart)."""
        from orbitdc.optimize.uncertainty import monte_carlo as _mc

        return _mc(self._space_scenario, self.earth.lcoc_per_pflop_day, n=n, seed=seed)

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
            f"{'kgCO2e/PFLOP-day':<32}"
            f"{s.details.get('co2e_per_pflop_day', float('nan')):>18,.1f}"
            f"{e.details.get('co2e_per_pflop_day', float('nan')):>18,.1f}",
            f"{'L water/PFLOP-day':<32}"
            f"{s.details.get('water_l_per_pflop_day', float('nan')):>18,.1f}"
            f"{e.details.get('water_l_per_pflop_day', float('nan')):>18,.1f}",
            "",
            f"Verdict: {verdict} on LCOC (space/earth = {ratio:.2f}x)",
        ]
        return "\n".join(rows)


def scenario_transient(scenario: Scenario) -> TransientResult:
    """Build the orbit-transient thermal series for a space scenario (for viz)."""
    if scenario.kind != "space" or scenario.space is None:
        raise ValueError("scenario_transient requires a space scenario")
    sp = scenario.space
    ev = evaluate_space(scenario)
    surface = get_radiator_surface(sp.radiator_panel)
    thermal_env = get_environment(sp.thermal_environment)
    coolant = get_coolant(sp.coolant)
    o_state = orbit.orbit_state(sp.orbit.altitude_km, sp.beta_deg)
    q_waste = ev.details["bus_load_w"]
    area_installed = min(
        ev.details["radiator_area_required_m2"], ev.details["radiator_area_available_m2"]
    )
    thermal_mass = ev.details["thermal_kg_per_kw"] * q_waste / 1000.0
    return transient_orbit(
        q_waste_w=q_waste,
        area_m2=area_installed,
        surface=surface,
        env=thermal_env,
        period_s=o_state.period_s,
        sunlit_fraction=o_state.sunlit_fraction,
        t_rad_target_k=ev.details["radiator_t_rad_k"],
        thermal_capacitance_j_per_k=thermal_mass * ALUMINUM_CP_J_PER_KG_K,
        freeze_temp_k=coolant.freeze_temp_k,
    )


def compare(space: Scenario, earth: Scenario) -> ComparisonResult:
    """Compare an orbital design against a terrestrial baseline."""
    return ComparisonResult(space, earth)
