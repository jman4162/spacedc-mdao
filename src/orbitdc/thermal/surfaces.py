"""Thermal data classes and the orbital heat-load environment.

These frozen dataclasses drive the thermal fidelity ladder (see
``background_information/THEMRAL_RADIATOR_DEEPDIVE.md``): a radiator surface and
its coating, the orbital environment that loads it, the chip-to-radiator
resistance stack, and the coolant loop. Math runs on SI floats.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Coating:
    """Radiator surface optical properties, beginning- and end-of-life.

    Low solar absorptance ``alpha`` and high IR emissivity ``eps`` are the goal.
    Atomic oxygen and UV raise alpha and lower eps over a mission, so closure
    must be checked at EOL.
    """

    name: str
    alpha_solar_bol: float
    eps_ir_bol: float
    alpha_solar_eol: float
    eps_ir_eol: float

    def alpha(self, eol: bool) -> float:
        return self.alpha_solar_eol if eol else self.alpha_solar_bol

    def eps(self, eol: bool) -> float:
        return self.eps_ir_eol if eol else self.eps_ir_bol


@dataclass(frozen=True)
class ThermalEnvironment:
    """Orbital radiative environment loading a radiator panel.

    Geometry is captured by the incidence and view-factor terms so a
    well-oriented (edge-to-sun, space-facing) radiator absorbs little, while a
    nadir/sun-facing one absorbs a lot.
    """

    solar_w_m2: float = 1361.0  # NASA SORCE mean
    albedo: float = 0.30  # NASA satellite average
    earth_ir_w_m2: float = 238.0  # NASA CERES OLR
    sun_incidence_cos: float = 0.0  # cos of solar angle on the panel; 0 = edge-on
    view_factor_earth: float = 0.0  # fraction of hemisphere subtended by Earth
    deep_space_sink_k: float = 3.0

    def absorbed_w_m2(self, alpha: float, eps: float) -> float:
        """Absorbed environmental flux per unit panel area (W/m^2).

        alpha weights short-wave (solar, albedo); eps weights long-wave (Earth
        IR), by Kirchhoff's law.
        """
        solar = alpha * self.solar_w_m2 * self.sun_incidence_cos
        albedo = alpha * self.albedo * self.solar_w_m2 * self.view_factor_earth
        earth_ir = eps * self.earth_ir_w_m2 * self.view_factor_earth
        return solar + albedo + earth_ir


@dataclass(frozen=True)
class RadiatorSurface:
    """A radiator panel: geometry, coating, areal mass, and temperature limit."""

    coating: Coating
    sides: int = 2  # 1 = one-sided, 2 = two-sided radiation
    areal_density_kg_m2: float = 7.0  # deployable system-level default
    max_temp_k: float = 350.0  # material/coolant ceiling for the panel
    view_factor_space: float = 0.95


@dataclass(frozen=True)
class ChipThermalStack:
    """Per-accelerator chip-to-radiator thermal resistance stack (K/W)."""

    chip_power_w: float
    r_junction_to_case: float
    r_tim: float
    r_coldplate: float
    r_transport: float
    r_radiator: float
    tj_max_k: float = 393.0  # H100 throttle ~120 C
    tj_design_k: float = 363.0  # design target ~90 C
    hbm_limit_k: float | None = None

    @property
    def r_total(self) -> float:
        return (
            self.r_junction_to_case
            + self.r_tim
            + self.r_coldplate
            + self.r_transport
            + self.r_radiator
        )


@dataclass(frozen=True)
class CoolantLoop:
    """Heat-transport loop from cold plates to the radiator."""

    fluid: str = "ammonia"
    mode: str = "single_phase"  # or "two_phase"
    cp_j_kg_k: float = 4700.0
    h_fg_j_kg: float = 1.37e6  # latent heat (two-phase)
    delta_t_k: float = 5.0
    pump_power_fraction: float = 0.02  # fraction of Q (single ~2%, two-phase ~11%)
    freeze_temp_k: float = 195.0
    fluid_mass_per_kw: float = 1.5  # kg per kW transported (fluid + lines)
    hardware_mass_per_kw: float = 2.0  # pumps, valves, accumulators, sensors
