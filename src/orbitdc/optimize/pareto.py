"""Multi-objective Pareto fronts via pymoo NSGA-II.

OpenMDAO is the model/structure backbone; pymoo provides the multi-objective
search directly on the `evaluate_space` evaluator (robust for the non-smooth,
mixed objectives here). Each candidate is one full scenario evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.mixed import (
    MixedVariableDuplicateElimination,
    MixedVariableMating,
    MixedVariableSampling,
)
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.variable import Integer, Real
from pymoo.optimize import minimize as pymoo_minimize

from orbitdc.compare import evaluate_space
from orbitdc.core.schema import Scenario
from orbitdc.optimize.design import (
    DESIGN_VARS,
    DISCRETE_VARS,
    bounds,
    minimized,
    overrides_from_mixed,
    overrides_from_vector,
)


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


@dataclass(frozen=True)
class MixedParetoResult:
    design_vars: list[str]
    objectives: list[str]
    points: list[dict[str, float]]  # design variables per non-dominated point
    f: np.ndarray  # objective values (minimized form), shape (n_points, n_objs)

    @property
    def n_points(self) -> int:
        return len(self.points)


class _MixedProblem(ElementwiseProblem):  # type: ignore[misc]
    def __init__(self, scenario: Scenario, design_vars: list[str], objectives: list[str]) -> None:
        self._scenario = scenario
        self._objectives = objectives
        variables: dict[str, object] = {}
        for name in design_vars:
            if name in DISCRETE_VARS:
                _, lo_i, hi_i = DISCRETE_VARS[name]
                variables[name] = Integer(bounds=(lo_i, hi_i))
            else:
                _, lo_f, hi_f = DESIGN_VARS[name]
                variables[name] = Real(bounds=(lo_f, hi_f))
        super().__init__(vars=variables, n_obj=len(objectives))

    def _evaluate(
        self, x: dict[str, float], out: dict[str, object], *a: object, **k: object
    ) -> None:
        ev = evaluate_space(self._scenario, overrides_from_mixed(x))
        out["F"] = [minimized(ev, name) for name in self._objectives]


def pareto_nsga2_mixed(
    scenario: Scenario,
    objectives: list[str],
    design_vars: list[str] | None = None,
    *,
    pop_size: int = 24,
    n_gen: int = 15,
    seed: int = 1,
) -> MixedParetoResult:
    """Mixed continuous/integer NSGA-II over architecture and continuous drivers."""
    dv = design_vars or [
        "n_satellites",
        "accelerators_per_satellite",
        "altitude_km",
        "downlink_gbps",
    ]
    problem = _MixedProblem(scenario, dv, objectives)
    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=MixedVariableSampling(),
        mating=MixedVariableMating(eliminate_duplicates=MixedVariableDuplicateElimination()),
        eliminate_duplicates=MixedVariableDuplicateElimination(),
    )
    result = pymoo_minimize(problem, algorithm, ("n_gen", n_gen), seed=seed, verbose=False)
    raw = result.X if isinstance(result.X, list | np.ndarray) else [result.X]
    points = [{k: float(v) for k, v in row.items()} for row in raw]
    return MixedParetoResult(
        design_vars=dv, objectives=objectives, points=points, f=np.atleast_2d(result.F)
    )
