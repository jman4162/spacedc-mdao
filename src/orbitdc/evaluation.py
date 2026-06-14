"""The common result shape for an evaluated design (space or earth)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

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
    thermal_bottleneck: str | None = None
    thermal_warnings: tuple[str, ...] = ()
    # (time_years, online_fraction) samples when graceful degradation is enabled.
    availability_curve: tuple[tuple[float, float], ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Plain nested dict (JSON-serializable) of the full evaluation."""
        return asdict(self)

    def to_json(self, indent: int | None = 2) -> str:
        """JSON string of the full evaluation."""
        return json.dumps(self.to_dict(), indent=indent)
