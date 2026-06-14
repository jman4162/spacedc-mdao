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


@dataclass(frozen=True)
class FleetHealthCurve:
    times_years: tuple[float, ...]
    surviving_fraction: tuple[float, ...]  # capacity online at each sample
    mean_online_fraction: float
    f_availability: float
    n_resupply_launches: int
    replaced_units_total: float


def fleet_health_curve(
    *,
    n_accelerators: int,
    annual_failure_rate: float,
    mission_years: float,
    spare_fraction: float,
    reset_recovery_availability: float,
    resupply_interval_years: float | None = None,
    n_steps: int = 48,
) -> FleetHealthCurve:
    """Time-stepped fleet capacity, optionally restored at launch-quantized resupplies.

    Without resupply the surviving fraction decays as exp(-lam t) (a graceful
    decline). With a resupply interval, failed units are replenished at each
    launch window, producing a sawtooth that the mission-mean availability
    integrates over. Spares add a flat buffer; reset-recovery scales the result.
    """
    lam = annual_failure_rate
    dt = mission_years / n_steps
    times: list[float] = []
    capacity: list[float] = []

    surviving = 1.0
    replaced_total = 0.0
    n_launches = 0
    next_resupply = resupply_interval_years if resupply_interval_years else float("inf")

    for i in range(1, n_steps + 1):
        t = i * dt
        surviving *= math.exp(-lam * dt)
        if t >= next_resupply and t < mission_years:
            replaced_total += (1.0 - surviving) * n_accelerators
            surviving = 1.0
            n_launches += 1
            next_resupply += resupply_interval_years  # type: ignore[operator]
        online = min(1.0, surviving + spare_fraction)
        times.append(t)
        capacity.append(online)

    mean_online = sum(capacity) / len(capacity)
    return FleetHealthCurve(
        times_years=tuple(times),
        surviving_fraction=tuple(capacity),
        mean_online_fraction=mean_online,
        f_availability=reset_recovery_availability * mean_online,
        n_resupply_launches=n_launches,
        replaced_units_total=replaced_total,
    )
