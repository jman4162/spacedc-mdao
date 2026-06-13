"""Reliability and availability (EQUATIONS.md §10).

Exponential survival with an annual failure rate, averaged over the mission to
get the mean online fraction, then adjusted by spares and reset-recovery
availability. In space MTTR is reset/degradation/spare-activation, not a
technician swap.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ReliabilityResult:
    annual_failure_rate: float
    mean_surviving_fraction: float
    expected_failures: float
    f_availability: float


def size_reliability(
    n_accelerators: int,
    annual_failure_rate: float,
    mission_years: float,
    spare_fraction: float,
    reset_recovery_availability: float,
) -> ReliabilityResult:
    lam = annual_failure_rate
    t = mission_years
    if lam <= 0.0:
        mean_surviving = 1.0
        expected_failures = 0.0
    else:
        # time-average of e^{-lam t} over [0, T]
        mean_surviving = (1.0 - math.exp(-lam * t)) / (lam * t)
        expected_failures = n_accelerators * (1.0 - math.exp(-lam * t))

    online_fraction = min(1.0, mean_surviving + spare_fraction)
    f_availability = reset_recovery_availability * online_fraction
    return ReliabilityResult(
        annual_failure_rate=lam,
        mean_surviving_fraction=mean_surviving,
        expected_failures=expected_failures,
        f_availability=f_availability,
    )
