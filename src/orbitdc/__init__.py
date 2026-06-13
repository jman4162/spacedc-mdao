"""orbitdc: MDAO of orbital compute infrastructure with terrestrial baselines.

The package optimizes delivered useful compute, not nominal capacity. See
`SPEC.md` and `EQUATIONS.md`. Public entry points:

    import orbitdc as odc
    space = odc.load_scenario("...space.yaml")
    earth = odc.load_scenario("...earth.yaml")
    result = odc.compare(space, earth)
    print(result.summary())
    print(result.explain_binding_constraints())
"""

from __future__ import annotations

from orbitdc.compare import (
    ComparisonResult,
    compare,
    evaluate,
    evaluate_earth,
    evaluate_space,
)
from orbitdc.core.scenario import load_scenario, load_scenario_dict
from orbitdc.evaluation import Evaluation

__version__ = "0.1.0"

__all__ = [
    "ComparisonResult",
    "Evaluation",
    "compare",
    "evaluate",
    "evaluate_earth",
    "evaluate_space",
    "load_scenario",
    "load_scenario_dict",
]
