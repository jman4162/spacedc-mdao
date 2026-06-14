"""Shared optimization spec: design variables and objectives.

Both the OpenMDAO problem (single-objective + DOE) and the pymoo Pareto search
operate on the same continuous design variables (the `evaluate_space` override
drivers) and the same objective extractors, so results are comparable.
"""

from __future__ import annotations

from collections.abc import Callable

from orbitdc.evaluation import Evaluation

# name -> (evaluate_space override key, lower bound, upper bound)
DESIGN_VARS: dict[str, tuple[str, float, float]] = {
    "utilization": ("utilization", 0.30, 0.98),
    "radiator_areal_mass": ("radiator_areal_mass_kg_per_m2", 2.0, 12.0),
    "solar_specific_power": ("solar_specific_power_w_per_kg", 30.0, 200.0),
    "launch_cost_per_kg": ("launch_cost_per_kg_usd", 200.0, 6000.0),
    "downlink_gbps": ("downlink_gbps", 50.0, 5000.0),
    "annual_failure_rate": ("annual_failure_rate", 0.01, 0.20),
    "radiator_cost_per_m2": ("radiator_cost_per_m2_usd", 2000.0, 12000.0),
    "altitude_km": ("altitude_km", 400.0, 1200.0),
    "radiator_t_rad_setpoint": ("radiator_t_rad_setpoint_k", 300.0, 345.0),
}

# Integer architecture variables for mixed-integer optimization.
DISCRETE_VARS: dict[str, tuple[str, int, int]] = {
    "n_satellites": ("n_satellites", 8, 128),
    "accelerators_per_satellite": ("accelerators_per_satellite", 4, 32),
}

# name -> (extractor, sense) where sense is "min" or "max"
_OBJECTIVES: dict[str, tuple[Callable[[Evaluation], float], str]] = {
    "lcoc": (lambda e: e.lcoc_per_pflop_day, "min"),
    "kg_per_kw": (lambda e: e.kg_per_kw if e.kg_per_kw is not None else float("inf"), "min"),
    "thermal_kg_per_kw": (lambda e: e.details.get("thermal_kg_per_kw", float("inf")), "min"),
    "availability": (lambda e: e.waterfall.factors.get("availability", 0.0), "max"),
    "delivered": (lambda e: e.delivered_tflops, "max"),
}


def objective_value(ev: Evaluation, name: str) -> float:
    """Raw objective value (in its natural direction)."""
    return _OBJECTIVES[name][0](ev)


def metric_value(ev: Evaluation, name: str) -> float:
    """Any optimization metric: an objective, or a `details` key (for constraints)."""
    if name in _OBJECTIVES:
        return _OBJECTIVES[name][0](ev)
    if name in ev.details:
        return ev.details[name]
    raise KeyError(f"unknown metric {name!r}")


def objective_sense(name: str) -> str:
    return _OBJECTIVES[name][1]


def minimized(ev: Evaluation, name: str) -> float:
    """Objective rewritten as a quantity to MINIMIZE (negate maximization)."""
    value = objective_value(ev, name)
    return -value if objective_sense(name) == "max" else value


def overrides_from_vector(names: list[str], x: list[float]) -> dict[str, float]:
    """Map a design-variable vector to an evaluate_space overrides dict."""
    return {DESIGN_VARS[n][0]: v for n, v in zip(names, x, strict=True)}


def overrides_from_mixed(x: dict[str, float]) -> dict[str, float]:
    """Map a mixed continuous/discrete variable dict to evaluate_space overrides."""
    out: dict[str, float] = {}
    for name, value in x.items():
        if name in DESIGN_VARS:
            out[DESIGN_VARS[name][0]] = float(value)
        elif name in DISCRETE_VARS:
            out[DISCRETE_VARS[name][0]] = float(value)
    return out


def bounds(names: list[str]) -> tuple[list[float], list[float]]:
    lows = [DESIGN_VARS[n][1] for n in names]
    highs = [DESIGN_VARS[n][2] for n in names]
    return lows, highs
