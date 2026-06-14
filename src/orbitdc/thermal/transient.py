"""Orbit-transient thermal model (THEMRAL_RADIATOR_DEEPDIVE Level 1).

Integrates the radiator panel temperature across the sunlit/eclipse cycle with a
lumped capacitance. During the hot sunlit phase the panel absorbs solar/albedo
and rejects less, so compute throttles; during eclipse it rejects more (and can
approach the coolant freeze point). Returns a time series for the orbit-timeline
view and a duty-cycle-averaged throttle that refines the steady-state f_thermal.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from orbitdc.core.constants import STEFAN_BOLTZMANN
from orbitdc.thermal.surfaces import RadiatorSurface, ThermalEnvironment


@dataclass(frozen=True)
class TransientResult:
    time_s: np.ndarray
    t_rad_k: np.ndarray
    throttle: np.ndarray
    sunlit_mask: np.ndarray
    avg_throttle: float
    t_max_k: float
    t_min_k: float
    freeze_margin_k: float
    survival_heater_w: float


def transient_orbit(
    *,
    q_waste_w: float,
    area_m2: float,
    surface: RadiatorSurface,
    env: ThermalEnvironment,
    period_s: float,
    sunlit_fraction: float,
    t_rad_target_k: float,
    thermal_capacitance_j_per_k: float,
    freeze_temp_k: float = 195.0,
    n_steps: int = 200,
    eol: bool = True,
) -> TransientResult:
    """Integrate panel temperature over one orbit (explicit Euler)."""
    eps = surface.coating.eps(eol)
    alpha = surface.coating.alpha(eol)
    emit_coef = eps * STEFAN_BOLTZMANN * surface.sides * area_m2  # emitted = emit_coef * T^4

    # Absorbed environmental power (W) in each phase.
    abs_sunlit = (
        alpha * env.solar_w_m2 * env.sun_incidence_cos
        + alpha * env.albedo * env.solar_w_m2 * env.view_factor_earth
        + eps * env.earth_ir_w_m2 * env.view_factor_earth
    ) * area_m2
    abs_eclipse = eps * env.earth_ir_w_m2 * env.view_factor_earth * area_m2

    dt = period_s / n_steps
    sunlit_time = sunlit_fraction * period_s
    reject_at_target = emit_coef * t_rad_target_k**4

    times = np.empty(n_steps)
    temps = np.empty(n_steps)
    throttles = np.empty(n_steps)
    sunlit = np.empty(n_steps, dtype=bool)

    t = t_rad_target_k
    for i in range(n_steps):
        clock = i * dt
        is_sun = clock < sunlit_time
        q_abs = abs_sunlit if is_sun else abs_eclipse
        # Throttle waste heat so the panel can hold its target temperature.
        capacity = max(0.0, reject_at_target - q_abs)
        throttle = min(1.0, capacity / q_waste_w) if q_waste_w > 0 else 1.0
        q_in = q_waste_w * throttle + q_abs
        t += (q_in - emit_coef * t**4) / thermal_capacitance_j_per_k * dt
        times[i], temps[i], throttles[i], sunlit[i] = clock, t, throttle, is_sun

    t_min = float(temps.min())
    freeze_margin = t_min - freeze_temp_k
    survival_heater = 0.0 if freeze_margin >= 0 else emit_coef * freeze_temp_k**4 * 0.1
    return TransientResult(
        time_s=times,
        t_rad_k=temps,
        throttle=throttles,
        sunlit_mask=sunlit,
        avg_throttle=float(throttles.mean()),
        t_max_k=float(temps.max()),
        t_min_k=t_min,
        freeze_margin_k=freeze_margin,
        survival_heater_w=survival_heater,
    )
