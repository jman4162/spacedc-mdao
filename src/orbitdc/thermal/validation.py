"""Validation anchors (THEMRAL_RADIATOR_DEEPDIVE §4, §8).

Real and published reference points to sanity-check the radiator model. These
back regression tests and let users see how a design compares to flown
hardware and to optimistic published claims.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.core.constants import STEFAN_BOLTZMANN


@dataclass(frozen=True)
class ValidationAnchor:
    name: str
    note: str
    heat_kw: float | None = None
    mass_kg: float | None = None
    area_m2: float | None = None
    net_w_m2: float | None = None
    areal_density_kg_m2: float | None = None


# ISS Photovoltaic Radiator: 14 kW, 740.7 kg, 3.12 m x 13.6 m.
ISS_PVR = ValidationAnchor(
    name="ISS PVR",
    note="Flown deployable radiator (NASA ISS ATCS overview).",
    heat_kw=14.0,
    mass_kg=740.7,
    area_m2=3.12 * 13.6,
    net_w_m2=14_000.0 / (3.12 * 13.6),
    areal_density_kg_m2=740.7 / (3.12 * 13.6),
)

# ISS EATCS radiator ORU: eight-panel deployable, 23.3 m x 3.4 m, 1122.64 kg; 70 kW system.
ISS_EATCS = ValidationAnchor(
    name="ISS EATCS ORU",
    note="35 kW/loop, 70 kW total; ammonia pumped loops (NASA ISS ATCS overview).",
    heat_kw=35.0,
    mass_kg=1122.64,
    area_m2=23.3 * 3.4,
    areal_density_kg_m2=1122.64 / (23.3 * 3.4),
)

# Starcloud/Lumen white paper: claimed ~633 W/m^2 net at 20 C, two-sided, low absorptivity.
# Explicitly an optimistic company-white-paper case.
STARCLOUD = ValidationAnchor(
    name="Starcloud/Lumen white paper",
    note="Company white paper, optimistic: two-sided, 20 C, low absorptivity.",
    net_w_m2=633.0,
)

# NASA high-temperature foldable heat-pipe radiator: <3 kg/m^2 at 500-600 K.
# Not compatible with low-temperature GPU/HBM limits.
NASA_HIGH_TEMP = ValidationAnchor(
    name="NASA high-temp radiator concept",
    note="<3 kg/m^2 at 500-600 K; for nuclear-electric, not GPU-compatible.",
    areal_density_kg_m2=3.0,
)

ANCHORS = [ISS_PVR, ISS_EATCS, STARCLOUD, NASA_HIGH_TEMP]


def ideal_area_for_mw(t_rad_k: float, eps: float = 0.9, sides: int = 1) -> float:
    """Idealized (no absorption) radiator area to reject 1 MW. Matches the
    deep-dive sanity table, e.g. ~2420 m^2 one-sided at 300 K.
    """
    flux = sides * eps * STEFAN_BOLTZMANN * t_rad_k**4
    return 1.0e6 / flux
