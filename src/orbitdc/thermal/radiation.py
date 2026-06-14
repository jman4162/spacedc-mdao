"""Level 0/1 radiator radiation physics (THEMRAL_RADIATOR_DEEPDIVE §2, §5).

Net heat rejection is emitted long-wave radiation minus absorbed solar, albedo,
and Earth IR. Treating deep space as a free cold sink without subtracting the
absorbed environment is the classic mistake; this module does not make it.
"""

from __future__ import annotations

from orbitdc.core.constants import STEFAN_BOLTZMANN
from orbitdc.thermal.surfaces import Coating, RadiatorSurface, ThermalEnvironment


def emitted_flux_w_m2(
    t_rad_k: float, eps: float, sides: int, t_sink_k: float = 3.0, view_factor: float = 1.0
) -> float:
    """Gross emitted flux per unit panel area: F_v * N_sides * eps * sigma * (T_rad^4 - T_sink^4).

    `view_factor` (1.0 = full hemisphere to space) is the Level-4 geometric
    derate for self-view, articulation, and solar-array blocking.
    """
    return view_factor * sides * eps * STEFAN_BOLTZMANN * (t_rad_k**4 - t_sink_k**4)


def net_flux_w_m2(
    t_rad_k: float,
    surface: RadiatorSurface,
    env: ThermalEnvironment,
    *,
    eol: bool = True,
    view_factor: float = 1.0,
) -> float:
    """Net rejected flux per unit panel area (W/m^2). Can be <= 0 (cannot reject)."""
    alpha = surface.coating.alpha(eol)
    eps = surface.coating.eps(eol)
    emitted = emitted_flux_w_m2(t_rad_k, eps, surface.sides, env.deep_space_sink_k, view_factor)
    absorbed = env.absorbed_w_m2(alpha, eps)
    return emitted - absorbed


def required_area_m2(
    q_waste_w: float,
    t_rad_k: float,
    surface: RadiatorSurface,
    env: ThermalEnvironment,
    *,
    eol: bool = True,
) -> float:
    """Panel area needed to reject q_waste at t_rad. Infinity if net flux <= 0."""
    net = net_flux_w_m2(t_rad_k, surface, env, eol=eol)
    if net <= 0.0:
        return float("inf")
    return q_waste_w / net


def ideal_blackbody_flux_w_m2(t_rad_k: float, eps: float = 0.9, sides: int = 1) -> float:
    """Idealized emission with no environmental absorption (optimistic bound).

    Reproduces the deep-dive's sanity table (e.g. ~413 W/m^2 one-sided at 300 K,
    eps=0.9).
    """
    return emitted_flux_w_m2(t_rad_k, eps, sides, t_sink_k=0.0)


def coating_at_eol_alpha_over_eps(coating: Coating) -> float:
    """alpha/eps at EOL; lower is better for net rejection."""
    return coating.alpha_solar_eol / coating.eps_ir_eol
