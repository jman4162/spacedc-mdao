"""Mass build-up (EQUATIONS.md §5).

Mass is the coupling between physics and launch cost. We build it up from
subsystems plus structure and margin fractions, rather than assuming one global
W/kg, so the binding subsystem is visible.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MassResult:
    breakdown_kg: dict[str, float]
    dry_mass_kg: float


def mass_buildup(
    *,
    n_accelerators: int,
    accel_mass_kg: float,
    payload_factor: float,
    array_mass_kg: float,
    battery_mass_kg: float,
    radiator_mass_kg: float,
    n_satellites: int,
    comms_mass_per_sat_kg: float,
    avionics_propulsion_per_sat_kg: float,
    structure_frac: float,
    margin_frac: float,
) -> MassResult:
    """Sum subsystem masses, then add structure and margin as fractions."""
    compute = n_accelerators * accel_mass_kg * payload_factor
    comms = n_satellites * comms_mass_per_sat_kg
    avionics_propulsion = n_satellites * avionics_propulsion_per_sat_kg

    subsystems = (
        compute + array_mass_kg + battery_mass_kg + radiator_mass_kg + comms + avionics_propulsion
    )
    structure = structure_frac * subsystems
    margin = margin_frac * (subsystems + structure)

    breakdown = {
        "compute": compute,
        "solar": array_mass_kg,
        "battery": battery_mass_kg,
        "radiator": radiator_mass_kg,
        "comms": comms,
        "avionics_propulsion": avionics_propulsion,
        "structure": structure,
        "margin": margin,
    }
    return MassResult(breakdown_kg=breakdown, dry_mass_kg=sum(breakdown.values()))
