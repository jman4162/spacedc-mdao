"""Thermal Level 5: mission-integrated degradation (coatings, MMOD, loop-out).

Levels 0-4 evaluate the radiator at a single end-of-life snapshot. Level 5
integrates three time-dependent losses over the mission and returns a derate on
the rejectable flux (``THEMRAL_RADIATOR_DEEPDIVE.md`` §5):

1. **Coating trajectory.** alpha rises and eps falls roughly linearly from BOL to
   EOL; the net flux is computed at each step rather than only at EOL.
2. **Micrometeoroid / debris.** Cumulative panel area loss accrues with time.
3. **Single-loop-out.** A coolant-loop failure removes 1/N of capacity for the
   rest of the mission; its probability rises with time.

The derate is the mission-averaged rejectable flux divided by the EOL-snapshot
flux the lower levels already use, so Level 5 < EOL whenever MMOD or loop-out
dominate the (favorable) BOL->EOL coating averaging. Defaults are low confidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.thermal.radiation import emitted_flux_w_m2
from orbitdc.thermal.surfaces import RadiatorSurface, ThermalEnvironment

# Low-confidence Level-5 defaults; expose as drivers, not headline numbers.
MMOD_AREA_LOSS_PER_YEAR = 0.005  # ~0.5%/yr effective panel area loss (LEO debris)
LOOP_OUT_PROB_PER_YEAR = 0.02  # annual probability a coolant loop is lost
N_COOLANT_LOOPS = 2


@dataclass(frozen=True)
class DegradationResult:
    derate: float  # mission-averaged rejectable flux / EOL-snapshot flux
    eol_net_flux_w_m2: float
    mission_avg_net_flux_w_m2: float
    mmod_area_retained: float  # at EOL
    loop_availability: float  # at EOL


def _net_flux(
    t_rad_k: float,
    alpha: float,
    eps: float,
    surface: RadiatorSurface,
    env: ThermalEnvironment,
    view_factor: float,
) -> float:
    emitted = emitted_flux_w_m2(t_rad_k, eps, surface.sides, env.deep_space_sink_k, view_factor)
    absorbed = env.absorbed_w_m2(alpha, eps)
    return emitted - absorbed


def mission_thermal_derate(
    *,
    mission_years: float,
    t_rad_k: float,
    surface: RadiatorSurface,
    env: ThermalEnvironment,
    view_factor: float = 1.0,
    mmod_area_loss_per_year: float = MMOD_AREA_LOSS_PER_YEAR,
    loop_out_prob_per_year: float = LOOP_OUT_PROB_PER_YEAR,
    n_loops: int = N_COOLANT_LOOPS,
    n_steps: int = 24,
) -> DegradationResult:
    """Mission-integrated rejectable-flux derate vs the EOL snapshot."""
    coating = surface.coating
    eol_net = _net_flux(t_rad_k, coating.alpha(True), coating.eps(True), surface, env, view_factor)

    acc = 0.0
    for i in range(n_steps):
        frac = (i + 0.5) / n_steps  # midpoint of each interval, in [0, 1]
        t_years = frac * mission_years
        # Coating trajectory: linear BOL -> EOL.
        alpha = coating.alpha_solar_bol + frac * (coating.alpha_solar_eol - coating.alpha_solar_bol)
        eps = coating.eps_ir_bol + frac * (coating.eps_ir_eol - coating.eps_ir_bol)
        net = _net_flux(t_rad_k, alpha, eps, surface, env, view_factor)
        area_retained = max(0.0, 1.0 - mmod_area_loss_per_year * t_years)
        # Expected capacity from a possible single-loop-out (small-probability).
        loop_factor = 1.0 - min(1.0, loop_out_prob_per_year * t_years) / n_loops
        acc += net * area_retained * loop_factor
    mission_avg = acc / n_steps

    derate = mission_avg / eol_net if eol_net > 0.0 else 0.0
    eol_years = mission_years
    return DegradationResult(
        derate=derate,
        eol_net_flux_w_m2=eol_net,
        mission_avg_net_flux_w_m2=mission_avg,
        mmod_area_retained=max(0.0, 1.0 - mmod_area_loss_per_year * eol_years),
        loop_availability=1.0 - min(1.0, loop_out_prob_per_year * eol_years) / n_loops,
    )


__all__ = ["DegradationResult", "mission_thermal_derate"]
