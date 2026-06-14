"""Tests for the MDAO + optimization layer (sub-phase 2B).

Skipped unless the ``mdao`` extra (openmdao / pymoo / SALib) is installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("openmdao")
pytest.importorskip("pymoo")
pytest.importorskip("SALib")

import orbitdc as odc
from orbitdc.compare import evaluate_space
from orbitdc.mdao import build_problem, optimize_single
from orbitdc.optimize.doe import latin_hypercube_doe
from orbitdc.optimize.pareto import pareto_nsga2
from orbitdc.optimize.sensitivity import sobol_indices

SPACE = Path(__file__).parents[1] / "examples" / "scenarios" / "orbital_1mw_inference.yaml"


def _space() -> odc.Scenario:  # type: ignore[name-defined]
    return odc.load_scenario(SPACE)


def test_run_model_matches_evaluate_space() -> None:
    space = _space()
    prob = build_problem(space, ["utilization"], ["lcoc"])
    prob.setup()
    prob.set_val("utilization", 0.85)
    prob.run_model()
    direct = evaluate_space(space, {"utilization": 0.85}).lcoc_per_pflop_day
    assert abs(float(prob.get_val("lcoc")[0]) - direct) < 1e-6


def test_optimize_single_improves_and_respects_constraint() -> None:
    space = _space()
    baseline = evaluate_space(space).lcoc_per_pflop_day
    res = optimize_single(
        space,
        "lcoc",
        ["utilization", "downlink_gbps", "launch_cost_per_kg"],
        constraints=[("radiator_packaging_ratio", None, 1.0)],
        maxiter=40,
    )
    assert res["lcoc"] <= baseline  # optimizer should not worsen LCOC
    assert res["radiator_packaging_ratio"] <= 1.0 + 1e-6


def test_pareto_returns_nondominated_set() -> None:
    pf = pareto_nsga2(_space(), ["lcoc", "kg_per_kw"], pop_size=12, n_gen=6, seed=1)
    assert pf.n_points >= 1
    assert pf.f.shape[1] == 2


def test_doe_shape() -> None:
    doe = latin_hypercube_doe(_space(), ["lcoc", "kg_per_kw"], n=10, seed=0)
    assert doe.values.shape == (10, 2)
    assert doe.samples.shape[1] == len(doe.design_vars)


def test_sobol_total_ge_first_order() -> None:
    sob = sobol_indices(_space(), "lcoc", n=16, seed=0)
    # Total-order index should dominate; downlink is the known top driver.
    assert sob.st["downlink_gbps"] >= 0.5
