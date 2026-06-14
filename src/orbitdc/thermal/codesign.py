"""Radiator-in-the-loop thermal co-design (THEMRAL_RADIATOR_DEEPDIVE §11).

Couples chip power -> junction temperature -> coolant loop -> radiator
temperature -> radiator area -> radiator mass. The radiator runs as hot as the
chip stack allows (to minimize area), sized for end-of-life rejection.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.thermal import diagnosis, network, radiation
from orbitdc.thermal.coolant import size_coolant
from orbitdc.thermal.surfaces import (
    ChipThermalStack,
    CoolantLoop,
    RadiatorSurface,
    ThermalEnvironment,
)

# Mass build-up fractions on (panels + coolant) for structure, deployment, margin.
STRUCTURE_FRAC = 0.15
DEPLOYMENT_FRAC = 0.10
MARGIN_FRAC = 0.20


@dataclass(frozen=True)
class ThermalCodesignResult:
    feasible: bool
    t_rad_k: float
    t_junction_k: float
    junction_capped: bool  # chip stack (not panel material) set T_rad
    net_flux_w_m2: float
    absorbed_fraction: float
    area_required_m2: float
    area_available_m2: float
    area_installed_m2: float
    f_thermal: float
    packaging_ratio: float
    pump_power_w: float
    panel_mass_kg: float
    coolant_mass_kg: float
    thermal_mass_kg: float
    m2_per_kw: float
    kg_per_kw: float
    bottleneck: str
    warnings: tuple[str, ...]
    hbm_margin_k: float | None = None
    hbm_limited: bool = False


def thermal_codesign(
    *,
    q_waste_w: float,
    chip_stack: ChipThermalStack,
    coolant: CoolantLoop,
    surface: RadiatorSurface,
    env: ThermalEnvironment,
    area_available_m2: float,
    eol: bool = True,
    t_rad_override: float | None = None,
    view_factor: float = 1.0,
) -> ThermalCodesignResult:
    """Solve the coupled chip->radiator thermal design and size area + mass.

    `t_rad_override` (if given) caps the radiator temperature below the junction
    ceiling — running cooler costs area but eases the chip thermal margin.
    """
    # 1. Radiator temperature: as hot as the junction allows, capped by material.
    t_rad_ceiling = network.max_radiator_temp_k(chip_stack)
    t_rad = min(t_rad_ceiling, surface.max_temp_k)
    if t_rad_override is not None:
        t_rad = min(t_rad, t_rad_override)
    junction_capped = t_rad_ceiling < surface.max_temp_k
    t_junction = network.junction_temperature_k(t_rad, chip_stack)

    # 2. Net rejection at that temperature (EOL coatings).
    net = radiation.net_flux_w_m2(t_rad, surface, env, eol=eol, view_factor=view_factor)
    emitted = radiation.emitted_flux_w_m2(
        t_rad, surface.coating.eps(eol), surface.sides, env.deep_space_sink_k, view_factor
    )
    absorbed = max(0.0, emitted - net)
    absorbed_fraction = absorbed / emitted if emitted > 0.0 else 1.0

    q_kw = q_waste_w / 1000.0
    coolant_res = size_coolant(q_waste_w, coolant)

    if net <= 0.0 or t_rad <= env.deep_space_sink_k:
        # Cannot reject at this temperature/orientation: chip- or radiator-limited.
        return ThermalCodesignResult(
            feasible=False,
            t_rad_k=t_rad,
            t_junction_k=t_junction,
            junction_capped=junction_capped,
            net_flux_w_m2=net,
            absorbed_fraction=absorbed_fraction,
            area_required_m2=float("inf"),
            area_available_m2=area_available_m2,
            area_installed_m2=area_available_m2,
            f_thermal=0.0,
            packaging_ratio=float("inf"),
            pump_power_w=coolant_res.pump_power_w,
            panel_mass_kg=area_available_m2 * surface.areal_density_kg_m2,
            coolant_mass_kg=coolant_res.total_mass_kg,
            thermal_mass_kg=float("inf"),
            m2_per_kw=float("inf"),
            kg_per_kw=float("inf"),
            bottleneck=diagnosis.CHIP_LIMITED if junction_capped else diagnosis.RADIATOR_LIMITED,
            warnings=tuple(
                diagnosis.gotcha_warnings(
                    eol_used=eol, sun_incidence_cos=env.sun_incidence_cos, sides=surface.sides
                )
            ),
        )

    # 3. Area: required vs the installed packaging budget.
    area_required = q_waste_w / net
    area_installed = min(area_required, area_available_m2)
    q_rejectable = net * area_available_m2
    f_thermal = min(1.0, q_rejectable / q_waste_w)
    packaging_ratio = area_required / area_available_m2

    # 4. Mass build-up.
    panel_mass = area_installed * surface.areal_density_kg_m2
    base = panel_mass + coolant_res.total_mass_kg
    thermal_mass = base * (1.0 + STRUCTURE_FRAC + DEPLOYMENT_FRAC + MARGIN_FRAC)

    # HBM is the temperature-sensitive subsystem; when its limit is below the
    # junction limit it sets the (cooler) radiator temperature, so the design is
    # HBM-limited and the margin is measured to the HBM limit.
    hbm_margin = network.hbm_margin_k(t_rad, chip_stack)
    hbm_limited = (
        chip_stack.hbm_limit_k is not None and chip_stack.hbm_limit_k < chip_stack.tj_max_k
    )

    bottleneck = diagnosis.classify_bottleneck(
        junction_capped=junction_capped,
        packaging_ratio=packaging_ratio,
        absorbed_fraction=absorbed_fraction,
        pump_power_fraction=coolant.pump_power_fraction,
        hbm_limited=hbm_limited,
    )

    return ThermalCodesignResult(
        feasible=True,
        t_rad_k=t_rad,
        t_junction_k=t_junction,
        junction_capped=junction_capped,
        net_flux_w_m2=net,
        absorbed_fraction=absorbed_fraction,
        area_required_m2=area_required,
        area_available_m2=area_available_m2,
        area_installed_m2=area_installed,
        f_thermal=f_thermal,
        packaging_ratio=packaging_ratio,
        pump_power_w=coolant_res.pump_power_w,
        panel_mass_kg=panel_mass,
        coolant_mass_kg=coolant_res.total_mass_kg,
        thermal_mass_kg=thermal_mass,
        m2_per_kw=area_required / q_kw,
        kg_per_kw=thermal_mass / q_kw,
        bottleneck=bottleneck,
        warnings=tuple(
            diagnosis.gotcha_warnings(
                eol_used=eol, sun_incidence_cos=env.sun_incidence_cos, sides=surface.sides
            )
        ),
        hbm_margin_k=hbm_margin,
        hbm_limited=hbm_limited,
    )
