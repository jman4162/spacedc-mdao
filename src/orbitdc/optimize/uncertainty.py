"""Monte Carlo over uncertain drivers.

Sample the key drivers from their distributions, evaluate the space design for
each draw, and report the distribution of LCOC and the probability that space
beats a given Earth baseline. Driver distributions are `Assumption` objects, so
provenance and uncertainty travel together.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from orbitdc.compare import evaluate_space
from orbitdc.core.assumptions import Assumption
from orbitdc.core.registry import get_launch
from orbitdc.core.schema import Scenario


@dataclass(frozen=True)
class MonteCarloResult:
    n: int
    p_space_wins: float
    lcoc_samples: np.ndarray
    lcoc_p10: float
    lcoc_p50: float
    lcoc_p90: float


def default_drivers(space_scenario: Scenario) -> dict[str, Assumption]:
    """A standard set of uncertain drivers with distributions for sweeps."""
    assert space_scenario.space is not None
    launch = get_launch(space_scenario.space.launch)
    today = "2026-06-13"
    return {
        "launch_cost_per_kg_usd": Assumption(
            value=launch.cost_per_kg_usd,
            units="USD/kg",
            source="launch catalog",
            date=today,
            kind="estimated",
            distribution="triangular",
            low=launch.cost_per_kg_usd * 0.5,
            high=launch.cost_per_kg_usd * 2.0,
        ),
        "solar_specific_power_w_per_kg": Assumption(
            value=100.0,
            units="W/kg",
            source="NASA SoA range",
            date=today,
            kind="estimated",
            distribution="triangular",
            low=50.0,
            high=200.0,
        ),
        "radiator_areal_mass_kg_per_m2": Assumption(
            value=5.0,
            units="kg/m^2",
            source="estimate",
            date=today,
            kind="estimated",
            distribution="triangular",
            low=3.0,
            high=10.0,
        ),
        "annual_failure_rate": Assumption(
            value=0.05,
            units="1/yr",
            source="estimate",
            date=today,
            kind="estimated",
            distribution="triangular",
            low=0.02,
            high=0.12,
        ),
        "utilization": Assumption(
            value=space_scenario.utilization,
            units="fraction",
            source="scenario",
            date=today,
            kind="estimated",
            distribution="triangular",
            low=0.5,
            high=0.95,
        ),
    }


def monte_carlo(
    space_scenario: Scenario,
    earth_lcoc: float,
    drivers: dict[str, Assumption] | None = None,
    n: int = 1000,
    seed: int = 0,
) -> MonteCarloResult:
    """Run `n` draws and return the LCOC distribution and win probability."""
    rng = np.random.default_rng(seed)
    driver_map = drivers if drivers is not None else default_drivers(space_scenario)

    samples = np.empty(n, dtype=float)
    wins = 0
    for i in range(n):
        overrides = {name: a.sample(rng) for name, a in driver_map.items()}
        lcoc = evaluate_space(space_scenario, overrides).lcoc_per_pflop_day
        samples[i] = lcoc
        if lcoc < earth_lcoc:
            wins += 1

    return MonteCarloResult(
        n=n,
        p_space_wins=wins / n,
        lcoc_samples=samples,
        lcoc_p10=float(np.percentile(samples, 10)),
        lcoc_p50=float(np.percentile(samples, 50)),
        lcoc_p90=float(np.percentile(samples, 90)),
    )
