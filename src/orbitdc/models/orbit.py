"""Closed-form orbital mechanics (EQUATIONS.md §6).

Phase 1 needs only circular-orbit period, velocity, and a sunlit/eclipse
fraction from a cylindrical-shadow model. No orbit-propagation library is
used (poliastro is archived; prefer hapsira/astropy if one is ever needed).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from orbitdc.core.constants import MU_EARTH, R_EARTH


@dataclass(frozen=True)
class OrbitState:
    altitude_m: float
    radius_m: float
    velocity_m_s: float
    period_s: float
    sunlit_fraction: float
    eclipse_fraction: float
    eclipse_duration_s: float


def circular_velocity(radius_m: float) -> float:
    """v = sqrt(mu / r)."""
    return math.sqrt(MU_EARTH / radius_m)


def orbital_period(radius_m: float) -> float:
    """T = 2 pi sqrt(r^3 / mu)."""
    return 2.0 * math.pi * math.sqrt(radius_m**3 / MU_EARTH)


def eclipse_fraction(radius_m: float, beta_deg: float = 0.0) -> float:
    """Fraction of a circular orbit spent in Earth's cylindrical shadow.

    f_e = (1/pi) * arccos( sqrt(r^2 - Re^2) / (r * cos(beta)) ), and 0 when the
    beta angle is large enough that the orbit never enters the shadow.
    """
    beta = math.radians(beta_deg)
    cos_beta = math.cos(beta)
    if cos_beta <= 0.0:
        return 0.0
    arg = math.sqrt(radius_m**2 - R_EARTH**2) / (radius_m * cos_beta)
    if arg >= 1.0:
        return 0.0
    return math.acos(arg) / math.pi


def orbit_state(altitude_km: float, beta_deg: float = 0.0) -> OrbitState:
    """Full closed-form orbit state for a circular orbit at a given altitude."""
    radius_m = R_EARTH + altitude_km * 1000.0
    period = orbital_period(radius_m)
    f_eclipse = eclipse_fraction(radius_m, beta_deg)
    return OrbitState(
        altitude_m=altitude_km * 1000.0,
        radius_m=radius_m,
        velocity_m_s=circular_velocity(radius_m),
        period_s=period,
        sunlit_fraction=1.0 - f_eclipse,
        eclipse_fraction=f_eclipse,
        eclipse_duration_s=f_eclipse * period,
    )
