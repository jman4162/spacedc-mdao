"""Thermal bottleneck diagnosis (THEMRAL_RADIATOR_DEEPDIVE §6, §9, §10).

Classifies what limits a thermal design and guards against the documented
"gotchas" (BOL-only closure, free radiator temperature, two-sided credit when a
side is sun-facing).
"""

from __future__ import annotations

# Bottleneck labels.
CHIP_LIMITED = "chip-limited"
HBM_LIMITED = "hbm-limited"
COOLANT_LIMITED = "coolant-limited"
TRANSPORT_LIMITED = "transport-limited"
RADIATOR_LIMITED = "radiator-limited"
ORIENTATION_LIMITED = "orientation-limited"


def classify_bottleneck(
    *,
    junction_capped: bool,
    packaging_ratio: float,
    absorbed_fraction: float,
    pump_power_fraction: float,
    hbm_limited: bool = False,
) -> str:
    """Return the dominant thermal bottleneck.

    - junction_capped: the chip stack (not the panel material) set the radiator
      temperature, forcing a colder, larger radiator.
    - packaging_ratio: required area / available area (>1 means it does not fit).
    - absorbed_fraction: absorbed environment / gross emission (orientation).
    - pump_power_fraction: parasitic transport power / waste heat.
    - hbm_limited: the HBM temperature limit is exceeded (the sensitive subsystem).
    """
    if hbm_limited:
        return HBM_LIMITED
    if packaging_ratio > 1.0 and junction_capped:
        return CHIP_LIMITED
    if packaging_ratio > 1.0:
        return RADIATOR_LIMITED
    if absorbed_fraction > 0.5:
        return ORIENTATION_LIMITED
    if pump_power_fraction > 0.08:
        return TRANSPORT_LIMITED
    if junction_capped:
        return CHIP_LIMITED
    return COOLANT_LIMITED


def gotcha_warnings(*, eol_used: bool, sun_incidence_cos: float, sides: int) -> list[str]:
    """Flag the classic optimistic-modeling mistakes if present."""
    warnings: list[str] = []
    if not eol_used:
        warnings.append("closure computed at BOL, not EOL — coatings degrade over the mission")
    if sides == 2 and sun_incidence_cos > 0.0:
        warnings.append("two-sided rejection credited while a side is sun-exposed")
    return warnings
