"""Closed-form orbital mechanics (EQUATIONS.md §6).

Phase 1 needs only circular-orbit period, velocity, and a sunlit/eclipse
fraction from a cylindrical-shadow model. No orbit-propagation library is
used (poliastro is archived; prefer hapsira/astropy if one is ever needed).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from orbitdc.core.constants import G0, MU_EARTH, R_EARTH, SECONDS_PER_YEAR

# Rough mean-solar-activity atmospheric density (kg/m^3) by altitude (km).
# Density varies by 1-2 orders of magnitude with solar activity; low confidence.
_RHO_TABLE: dict[float, float] = {
    300.0: 2.0e-11,
    400.0: 3.0e-12,
    500.0: 5.0e-13,
    600.0: 1.2e-13,
    700.0: 4.0e-14,
    800.0: 1.5e-14,
}


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


def atmospheric_density(altitude_km: float) -> float:
    """Coarse log-linear interpolation of mean atmospheric density (kg/m^3)."""
    alts = sorted(_RHO_TABLE)
    if altitude_km <= alts[0]:
        return _RHO_TABLE[alts[0]]
    if altitude_km >= alts[-1]:
        return _RHO_TABLE[alts[-1]]
    lo = max(a for a in alts if a <= altitude_km)
    hi = min(a for a in alts if a >= altitude_km)
    if lo == hi:
        return _RHO_TABLE[lo]
    frac = (altitude_km - lo) / (hi - lo)
    log_rho = math.log(_RHO_TABLE[lo]) + frac * (
        math.log(_RHO_TABLE[hi]) - math.log(_RHO_TABLE[lo])
    )
    return math.exp(log_rho)


def drag_deltav_per_year_ms(
    altitude_km: float, drag_area_m2: float, mass_kg: float, cd: float = 2.2
) -> float:
    """Annual delta-v to offset atmospheric drag: a_D = 0.5 rho v^2 Cd A / m."""
    radius_m = R_EARTH + altitude_km * 1000.0
    v = circular_velocity(radius_m)
    rho = atmospheric_density(altitude_km)
    accel = 0.5 * rho * v * v * cd * drag_area_m2 / mass_kg
    return accel * SECONDS_PER_YEAR


def station_keeping_propellant_kg(
    total_deltav_ms: float, dry_mass_kg: float, isp_s: float
) -> float:
    """Propellant from the rocket equation: m_prop = m_dry (exp(dv/(Isp g0)) - 1)."""
    return dry_mass_kg * (math.exp(total_deltav_ms / (isp_s * G0)) - 1.0)


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
