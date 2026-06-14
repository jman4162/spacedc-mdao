"""Sensitivity analysis: one-at-a-time tornado swings and global Sobol indices.

The tornado re-evaluates space LCOC at a low/high value per driver with the
others nominal. Sobol (via SALib) attributes output variance to each driver and
its interactions across the whole space.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from orbitdc.compare import evaluate_space
from orbitdc.core.schema import Scenario
from orbitdc.optimize.design import DESIGN_VARS, objective_value, overrides_from_vector

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


@dataclass(frozen=True)
class SobolResult:
    design_vars: list[str]
    objective: str
    s1: dict[str, float]  # first-order indices
    st: dict[str, float]  # total-order indices


def sobol_indices(
    space_scenario: Scenario,
    objective: str = "lcoc",
    design_vars: list[str] | None = None,
    *,
    n: int = 64,
    seed: int = 0,
) -> SobolResult:
    """Global Sobol sensitivity of an objective to the design drivers (SALib)."""
    from SALib.analyze import sobol as sobol_analyze
    from SALib.sample import sobol as sobol_sample

    dv = design_vars or list(DESIGN_VARS)
    problem = {
        "num_vars": len(dv),
        "names": dv,
        "bounds": [[DESIGN_VARS[name][1], DESIGN_VARS[name][2]] for name in dv],
    }
    samples = sobol_sample.sample(problem, n, calc_second_order=False, seed=seed)
    y = np.empty(samples.shape[0], dtype=float)
    for i, row in enumerate(samples):
        ev = evaluate_space(space_scenario, overrides_from_vector(dv, list(row)))
        y[i] = objective_value(ev, objective)

    indices = sobol_analyze.analyze(problem, y, calc_second_order=False, print_to_console=False)
    return SobolResult(
        design_vars=dv,
        objective=objective,
        s1={name: float(v) for name, v in zip(dv, indices["S1"], strict=True)},
        st={name: float(v) for name, v in zip(dv, indices["ST"], strict=True)},
    )
