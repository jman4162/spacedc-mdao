"""Environment presets — the deep-dive's net-W/m^2 scenario table (§6.A).

Each preset is a `ThermalEnvironment` capturing radiator orientation and orbit
loading, from idealized (deep-space view, no sun/Earth) to conservative LEO
(sun exposure, Earth IR/albedo, partial self-view).
"""

from __future__ import annotations

from orbitdc.thermal.surfaces import ThermalEnvironment

PRESETS: dict[str, ThermalEnvironment] = {
    # Two-sided, deep-space view, no Sun/Earth absorption. Optimistic bound.
    "idealized": ThermalEnvironment(sun_incidence_cos=0.0, view_factor_earth=0.0),
    # Articulated, edge-to-sun, low Earth view.
    "good_engineering": ThermalEnvironment(sun_incidence_cos=0.10, view_factor_earth=0.05),
    # Starcloud-like: one side mildly sun-exposed, low Earth view.
    "starcloud_optimistic": ThermalEnvironment(sun_incidence_cos=0.15, view_factor_earth=0.05),
    # Conservative LEO: real sun exposure, Earth IR/albedo, self-view penalty.
    "conservative_leo": ThermalEnvironment(sun_incidence_cos=0.50, view_factor_earth=0.20),
}


def get_environment(name: str) -> ThermalEnvironment:
    if name not in PRESETS:
        raise KeyError(f"unknown environment preset {name!r}; available: {sorted(PRESETS)}")
    return PRESETS[name]
