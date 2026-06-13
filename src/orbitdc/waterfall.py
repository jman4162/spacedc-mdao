"""The delivered-compute waterfall (EQUATIONS.md §1).

Installed peak compute is multiplied down by each limiting factor. The factors
are multiplicative, so their product (delivered compute) is order-independent;
the presentation order follows the canonical waterfall.
"""

from __future__ import annotations

from dataclasses import dataclass

# Canonical presentation order of the degradation factors.
FACTOR_ORDER = ("software", "power", "thermal", "network", "availability", "utilization")

FACTOR_LABELS = {
    "software": "sustained (vs peak)",
    "power": "power-available",
    "thermal": "thermally allowable",
    "network": "network-limited",
    "availability": "reliability-adjusted",
    "utilization": "utilization-adjusted",
}


@dataclass(frozen=True)
class Waterfall:
    peak_tflops: float
    factors: dict[str, float]
    stages_tflops: dict[str, float]  # cumulative compute after applying each factor
    delivered_tflops: float
    delivered_fraction: float


def build_waterfall(peak_tflops: float, factors: dict[str, float]) -> Waterfall:
    """Apply the factors in canonical order, recording the cumulative compute."""
    running = peak_tflops
    stages: dict[str, float] = {}
    for name in FACTOR_ORDER:
        running *= factors.get(name, 1.0)
        stages[name] = running
    fraction = running / peak_tflops if peak_tflops > 0.0 else 0.0
    return Waterfall(
        peak_tflops=peak_tflops,
        factors={k: factors.get(k, 1.0) for k in FACTOR_ORDER},
        stages_tflops=stages,
        delivered_tflops=running,
        delivered_fraction=fraction,
    )
