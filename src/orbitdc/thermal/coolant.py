"""Level 3 coolant loop (THEMRAL_RADIATOR_DEEPDIVE §5).

Heat transport from cold plates to the radiator costs pump power and mass.
Single-phase loops move heat with sensible heat (Q = m_dot cp dT); two-phase
loops add latent heat and move more per unit flow but cost more parasitic
power. Pump power is a real bus load that feeds back into solar and mass.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.thermal.surfaces import CoolantLoop


@dataclass(frozen=True)
class CoolantResult:
    mass_flow_kg_s: float
    pump_power_w: float
    fluid_mass_kg: float
    hardware_mass_kg: float
    total_mass_kg: float


def mass_flow_kg_s(q_w: float, loop: CoolantLoop) -> float:
    """Required coolant mass flow to carry q_w."""
    if loop.mode == "two_phase":
        per_kg = loop.h_fg_j_kg + loop.cp_j_kg_k * loop.delta_t_k
    else:
        per_kg = loop.cp_j_kg_k * loop.delta_t_k
    return q_w / per_kg


def size_coolant(q_w: float, loop: CoolantLoop) -> CoolantResult:
    """Pump power and mass to transport q_w to the radiator."""
    q_kw = q_w / 1000.0
    fluid_mass = q_kw * loop.fluid_mass_per_kw
    hardware_mass = q_kw * loop.hardware_mass_per_kw
    return CoolantResult(
        mass_flow_kg_s=mass_flow_kg_s(q_w, loop),
        pump_power_w=loop.pump_power_fraction * q_w,
        fluid_mass_kg=fluid_mass,
        hardware_mass_kg=hardware_mass,
        total_mass_kg=fluid_mass + hardware_mass,
    )
