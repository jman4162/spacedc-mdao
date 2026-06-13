"""Thermal model (EQUATIONS.md §4).

Nearly all electrical power becomes heat that must leave by radiation. The
installed radiator area is the packaging budget; if the heat to reject exceeds
what that area can radiate, compute is throttled (f_thermal < 1). This is the
classic space constraint, and the one optimistic analyses tend to skip.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.core.constants import STEFAN_BOLTZMANN
from orbitdc.core.registry import Radiator


@dataclass(frozen=True)
class ThermalResult:
    q_waste_w: float
    area_required_m2: float
    area_available_m2: float
    q_rejectable_w: float
    f_thermal: float
    packaging_ratio: float  # required / available; > 1 means it does not fit
    radiator_mass_kg: float
    radiator_cost_usd: float


def _rejectable_flux_w_per_m2(rad: Radiator) -> float:
    return (
        rad.emissivity
        * STEFAN_BOLTZMANN
        * rad.view_factor
        * (rad.t_radiator_k**4 - rad.t_sink_k**4)
    )


def radiator_area_required(q_waste_w: float, rad: Radiator) -> float:
    """A_rad = Q / (eps sigma F (T_rad^4 - T_sink^4))."""
    return q_waste_w / _rejectable_flux_w_per_m2(rad)


def size_thermal(q_waste_w: float, area_available_m2: float, rad: Radiator) -> ThermalResult:
    """Compute heat rejection against the installed radiator area."""
    flux = _rejectable_flux_w_per_m2(rad)
    area_required = q_waste_w / flux
    q_rejectable = flux * area_available_m2
    f_thermal = min(1.0, q_rejectable / q_waste_w) if q_waste_w > 0.0 else 1.0
    return ThermalResult(
        q_waste_w=q_waste_w,
        area_required_m2=area_required,
        area_available_m2=area_available_m2,
        q_rejectable_w=q_rejectable,
        f_thermal=f_thermal,
        packaging_ratio=area_required / area_available_m2,
        radiator_mass_kg=area_available_m2 * rad.areal_mass_kg_per_m2,
        radiator_cost_usd=area_available_m2 * rad.cost_per_m2_usd,
    )


def junction_temperature(t_radiator_k: float, q_chip_w: float, r_total_k_per_w: float) -> float:
    """T_junction = T_rad + Q_chip * sum(R) (EQUATIONS.md §4 resistance chain)."""
    return t_radiator_k + q_chip_w * r_total_k_per_w
