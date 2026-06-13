"""Physical constants in SI units.

Values are CODATA / standard references. Kept in one place so models share
exact numbers and tests can import the same constants they check against.
"""

from __future__ import annotations

# Radiation and thermodynamics
STEFAN_BOLTZMANN = 5.670374419e-8  # W / (m^2 K^4)
BOLTZMANN = 1.380649e-23  # J / K
PLANCK = 6.62607015e-34  # J s
SPEED_OF_LIGHT = 299_792_458.0  # m / s

# Solar
SOLAR_CONSTANT = 1361.0  # W / m^2, mean irradiance at 1 AU

# Earth / orbital mechanics
MU_EARTH = 3.986004418e14  # m^3 / s^2, geocentric gravitational parameter
R_EARTH = 6_378_137.0  # m, equatorial radius (WGS-84)
G0 = 9.80665  # m / s^2, standard gravity (for the rocket equation)

# Time
HOURS_PER_YEAR = 8760.0
SECONDS_PER_YEAR = 365.25 * 24 * 3600.0
