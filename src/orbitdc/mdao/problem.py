"""OpenMDAO problem wrapping the scenario evaluator.

`OrbitDCComponent` is an ``ExplicitComponent`` whose inputs are the design
variables and whose outputs are the optimization metrics; ``compute`` calls
``evaluate_space``. The pure models stay the single source of truth, and
``run_model`` matches ``evaluate_space`` exactly. Derivatives are
finite-difference (the models are non-smooth), so single-objective runs use a
gradient-free driver (COBYLA). Multi-objective Pareto is handled by
``orbitdc.optimize.pareto`` (pymoo).
"""

from __future__ import annotations

from typing import Any

import openmdao.api as om

from orbitdc.compare import evaluate_space
from orbitdc.core.schema import Scenario
from orbitdc.optimize.design import DESIGN_VARS, metric_value, objective_sense


class OrbitDCComponent(om.ExplicitComponent):  # type: ignore[misc]
    """Wrap a full orbital-scenario evaluation as one OpenMDAO component."""

    def initialize(self) -> None:
        self.options.declare("scenario")
        self.options.declare("design_vars", types=list)
        self.options.declare("outputs", types=list)

    def setup(self) -> None:
        for name in self.options["design_vars"]:
            lo, hi = DESIGN_VARS[name][1], DESIGN_VARS[name][2]
            self.add_input(name, val=0.5 * (lo + hi))
        for name in self.options["outputs"]:
            self.add_output(name, val=0.0)
        self.declare_partials("*", "*", method="fd", form="central")

    def compute(self, inputs: Any, outputs: Any) -> None:
        scenario = self.options["scenario"]
        overrides = {
            DESIGN_VARS[name][0]: float(inputs[name][0]) for name in self.options["design_vars"]
        }
        ev = evaluate_space(scenario, overrides)
        for name in self.options["outputs"]:
            outputs[name] = metric_value(ev, name)


def build_problem(
    scenario: Scenario,
    design_vars: list[str],
    outputs: list[str],
) -> om.Problem:
    """Assemble an OpenMDAO problem around the evaluation component."""
    prob = om.Problem()
    prob.model.add_subsystem(
        "dc",
        OrbitDCComponent(scenario=scenario, design_vars=design_vars, outputs=outputs),
        promotes=["*"],
    )
    return prob


def optimize_single(
    scenario: Scenario,
    objective: str,
    design_vars: list[str],
    constraints: list[tuple[str, float | None, float | None]] | None = None,
    *,
    optimizer: str = "COBYLA",
    maxiter: int = 60,
) -> dict[str, float]:
    """Single-objective constrained optimization via OpenMDAO + ScipyOptimizeDriver.

    `constraints` is a list of (metric_name, lower, upper). Returns the optimal
    design variables plus the objective and constraint values.
    """
    cons = constraints or []
    outputs = [objective] + [c[0] for c in cons]
    prob = build_problem(scenario, design_vars, outputs)

    for name in design_vars:
        prob.model.add_design_var(name, lower=DESIGN_VARS[name][1], upper=DESIGN_VARS[name][2])
    scaler = -1.0 if objective_sense(objective) == "max" else 1.0
    prob.model.add_objective(objective, scaler=scaler)
    for cname, lower, upper in cons:
        prob.model.add_constraint(cname, lower=lower, upper=upper)

    prob.driver = om.ScipyOptimizeDriver(optimizer=optimizer, maxiter=maxiter, disp=False)
    prob.setup()
    prob.run_driver()

    result = {name: float(prob.get_val(name)[0]) for name in design_vars}
    for name in outputs:
        result[name] = float(prob.get_val(name)[0])
    return result
