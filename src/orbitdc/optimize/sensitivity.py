"""Tornado sensitivity: one-at-a-time swings of the key drivers.

For each driver, re-evaluate space LCOC at a low and a high value with the
others held at nominal, and rank by the resulting swing. This shows which
uncertain assumptions move the answer most.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.compare import evaluate_space
from orbitdc.core.schema import Scenario

# Plausible low/high test values per driver (not the wider solver search range).
TORNADO_RANGES: dict[str, tuple[float, float]] = {
    "launch_cost_per_kg_usd": (1500.0, 6000.0),
    "solar_specific_power_w_per_kg": (50.0, 200.0),
    "radiator_areal_mass_kg_per_m2": (3.0, 10.0),
    "annual_failure_rate": (0.02, 0.12),
    "utilization": (0.50, 0.95),
}


@dataclass(frozen=True)
class TornadoEntry:
    driver: str
    low_value: float
    high_value: float
    lcoc_low: float
    lcoc_high: float

    @property
    def swing(self) -> float:
        return abs(self.lcoc_high - self.lcoc_low)


def tornado(
    space_scenario: Scenario,
    drivers: dict[str, tuple[float, float]] | None = None,
) -> list[TornadoEntry]:
    """Return tornado entries sorted by descending LCOC swing."""
    ranges = drivers or TORNADO_RANGES
    entries: list[TornadoEntry] = []
    for driver, (lo, hi) in ranges.items():
        lcoc_lo = evaluate_space(space_scenario, {driver: lo}).lcoc_per_pflop_day
        lcoc_hi = evaluate_space(space_scenario, {driver: hi}).lcoc_per_pflop_day
        entries.append(TornadoEntry(driver, lo, hi, lcoc_lo, lcoc_hi))
    entries.sort(key=lambda e: e.swing, reverse=True)
    return entries
