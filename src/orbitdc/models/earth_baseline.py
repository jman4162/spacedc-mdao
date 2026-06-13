"""Terrestrial baseline (EQUATIONS.md §12).

A best-in-class hyperscale facility: high availability, good PUE, sustained
fraction, and utilization. Delivered compute degrades only by the sustained,
availability, and utilization factors; cooling and power are folded into PUE.
Do not benchmark space against a straw-man Earth facility.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarthResult:
    it_power_w: float
    facility_power_w: float
    pue: float
    delivered_tflops: float
    delivered_fraction: float


def earth_delivered(
    *,
    peak_tflops: float,
    it_power_w: float,
    pue: float,
    sustained_fraction: float,
    availability: float,
    utilization: float,
) -> EarthResult:
    delivered_fraction = sustained_fraction * availability * utilization
    return EarthResult(
        it_power_w=it_power_w,
        facility_power_w=it_power_w * pue,
        pue=pue,
        delivered_tflops=peak_tflops * delivered_fraction,
        delivered_fraction=delivered_fraction,
    )
