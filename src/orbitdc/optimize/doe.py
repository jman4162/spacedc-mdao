"""Design of experiments: Latin-hypercube sweep over the design variables.

Uses scipy's QMC sampler (dependency-light); returns evaluated metrics in
memory for surrogate fitting, plotting, or screening.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import qmc

from orbitdc.compare import evaluate_space
from orbitdc.core.schema import Scenario
from orbitdc.optimize.design import DESIGN_VARS, metric_value, overrides_from_vector


@dataclass(frozen=True)
class DOEResult:
    design_vars: list[str]
    metrics: list[str]
    samples: np.ndarray  # (n, n_vars) design points
    values: np.ndarray  # (n, n_metrics) evaluated metrics


def latin_hypercube_doe(
    scenario: Scenario,
    metrics: list[str],
    design_vars: list[str] | None = None,
    *,
    n: int = 32,
    seed: int = 0,
) -> DOEResult:
    """Evaluate `metrics` over a Latin-hypercube sample of the design space."""
    dv = design_vars or list(DESIGN_VARS)
    lows = np.array([DESIGN_VARS[name][1] for name in dv])
    highs = np.array([DESIGN_VARS[name][2] for name in dv])

    sampler = qmc.LatinHypercube(d=len(dv), seed=seed)
    unit = sampler.random(n)
    samples = qmc.scale(unit, lows, highs)

    values = np.empty((n, len(metrics)), dtype=float)
    for i, row in enumerate(samples):
        ev = evaluate_space(scenario, overrides_from_vector(dv, list(row)))
        values[i] = [metric_value(ev, m) for m in metrics]

    return DOEResult(design_vars=dv, metrics=metrics, samples=samples, values=values)
