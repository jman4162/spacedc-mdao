"""Formation flying: relative dynamics, formation-keeping Δv, collision margin.

The formation-keeping budget couples to the same separation that 4A's optical
crosslink uses: a tighter formation buys more crosslink bandwidth but costs more
to hold safely. Two effects:

1. **Drift cancellation.** Differential drag (and J2) across the formation is a
   small fraction of the nominal drag acceleration; nulling the accumulated
   relative velocity costs Δv ≈ a_diff · t. This is set by the disturbance, not
   the separation.

2. **Collision avoidance.** With separation s and navigation uncertainty sigma,
   the margin is s/sigma "sigmas". When that drops below a safe threshold,
   conjunction maneuvers (CAMs) are needed; their rate rises as the formation
   tightens. This is the separation-dependent term: closer = riskier = more Δv.

Relative motion uses the Clohessy-Wiltshire mean motion n = sqrt(mu/a^3); in the
unperturbed two-body CW model bounded relative orbits are closed (zero secular
Δv), so all formation-keeping cost here is perturbation- or collision-driven.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from orbitdc.core.constants import MU_EARTH, R_EARTH

# Collision-avoidance model defaults (low confidence; expose as drivers).
SAFE_MARGIN_SIGMAS = 10.0  # below this many sigmas of clearance, CAMs are needed
CAM_DELTAV_MS = 0.05  # per conjunction-avoidance maneuver (small radial nudge)
MAX_CAMS_PER_YEAR = 200.0  # cap so a degenerate close formation stays finite


@dataclass(frozen=True)
class FormationResult:
    mean_motion_rad_s: float
    relative_orbit_period_s: float
    drift_deltav_per_year_ms: float
    collision_margin_sigmas: float
    collision_avoidance_deltav_per_year_ms: float
    formation_deltav_per_year_ms: float


def mean_motion(radius_m: float) -> float:
    """Clohessy-Wiltshire mean motion n = sqrt(mu / a^3)."""
    return math.sqrt(MU_EARTH / radius_m**3)


def formation_keeping(
    *,
    altitude_km: float,
    drag_deltav_per_year_ms: float,
    differential_drag_frac: float,
    separation_m: float,
    position_uncertainty_m: float,
    safe_margin_sigmas: float = SAFE_MARGIN_SIGMAS,
    cam_deltav_ms: float = CAM_DELTAV_MS,
) -> FormationResult:
    """Formation-keeping Δv per year and the collision-avoidance margin.

    drag_deltav_per_year_ms is the nominal station-keeping drag Δv (reused so the
    differential term stays consistent with the orbit model).
    """
    radius_m = R_EARTH + altitude_km * 1000.0
    n = mean_motion(radius_m)
    period = 2.0 * math.pi / n

    # 1. Drift cancellation: a fraction of the nominal drag Δv is differential.
    drift_deltav = differential_drag_frac * drag_deltav_per_year_ms

    # 2. Collision avoidance: clearance in sigmas; CAMs scale up as it tightens.
    margin = separation_m / position_uncertainty_m
    if margin >= safe_margin_sigmas:
        cams_per_year = 0.0
    else:
        cams_per_year = min(MAX_CAMS_PER_YEAR, (safe_margin_sigmas / margin) - 1.0)
    cam_deltav = cams_per_year * cam_deltav_ms

    return FormationResult(
        mean_motion_rad_s=n,
        relative_orbit_period_s=period,
        drift_deltav_per_year_ms=drift_deltav,
        collision_margin_sigmas=margin,
        collision_avoidance_deltav_per_year_ms=cam_deltav,
        formation_deltav_per_year_ms=drift_deltav + cam_deltav,
    )


__all__ = ["FormationResult", "formation_keeping", "mean_motion"]
