"""Multi-objective Pareto fronts via pymoo NSGA-II.

OpenMDAO is the model/structure backbone; pymoo provides the multi-objective
search directly on the `evaluate_space` evaluator (robust for the non-smooth,
mixed objectives here). Each candidate is one full scenario evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize as pymoo_minimize

from orbitdc.compare import evaluate_space
from orbitdc.core.schema import Scenario
from orbitdc.optimize.design import bounds, minimized, overrides_from_vector


@dataclass(frozen=True)
class ParetoResult:
    design_vars: list[str]
    objectives: list[str]
    x: np.ndarray  # design points, shape (n_points, n_vars)
    f: np.ndarray  # objective values in MINIMIZED form, shape (n_points, n_objs)

    @property
    def n_points(self) -> int:
        return int(self.x.shape[0])


class _ScenarioProblem(ElementwiseProblem):  # type: ignore[misc]
    def __init__(self, scenario: Scenario, design_vars: list[str], objectives: list[str]) -> None:
        self._scenario = scenario
        self._design_vars = design_vars
        self._objectives = objectives
        lows, highs = bounds(design_vars)
        super().__init__(
            n_var=len(design_vars),
            n_obj=len(objectives),
            xl=np.array(lows),
            xu=np.array(highs),
        )

    def _evaluate(
        self, x: np.ndarray, out: dict[str, object], *args: object, **kwargs: object
    ) -> None:
        overrides = overrides_from_vector(self._design_vars, list(x))
        ev = evaluate_space(self._scenario, overrides)
        out["F"] = [minimized(ev, name) for name in self._objectives]


def pareto_nsga2(
    scenario: Scenario,
    objectives: list[str],
    design_vars: list[str] | None = None,
    *,
    pop_size: int = 24,
    n_gen: int = 15,
    seed: int = 1,
) -> ParetoResult:
    """Run NSGA-II and return the non-dominated set (objectives in minimized form)."""
    dv = design_vars or [
        "utilization",
        "radiator_areal_mass",
        "launch_cost_per_kg",
        "downlink_gbps",
    ]
    problem = _ScenarioProblem(scenario, dv, objectives)
    result = pymoo_minimize(
        problem, NSGA2(pop_size=pop_size), ("n_gen", n_gen), seed=seed, verbose=False
    )
    x = np.atleast_2d(result.X)
    f = np.atleast_2d(result.F)
    return ParetoResult(design_vars=dv, objectives=objectives, x=x, f=f)
