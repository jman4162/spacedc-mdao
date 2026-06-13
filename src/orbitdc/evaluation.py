"""The common result shape for an evaluated design (space or earth)."""

from __future__ import annotations

from dataclasses import dataclass, field

from orbitdc.waterfall import Waterfall


@dataclass(frozen=True)
class Evaluation:
    label: str
    kind: str  # "space" or "earth"
    n_accelerators: int
    peak_tflops: float
    delivered_tflops: float
    delivered_fraction: float
    waterfall: Waterfall
    lcoc_per_pflop_day: float
    cost_per_accelerator_hour: float
    lifecycle_pv_usd: float
    cost_breakdown_usd: dict[str, float]
    it_power_w: float
    # Space-only fields (None for earth).
    dry_mass_kg: float | None = None
    specific_power_w_per_kg: float | None = None
    kg_per_kw: float | None = None
    mass_breakdown_kg: dict[str, float] | None = None
    details: dict[str, float] = field(default_factory=dict)
