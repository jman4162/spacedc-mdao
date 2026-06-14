"""Phase 4B: cost learning curves, TRL premium, and multi-scenario robustness."""

from __future__ import annotations

import glob
import math

import pytest

import orbitdc as odc
from orbitdc.models.cost import learning_multiplier, trl_multiplier
from orbitdc.optimize.robust import batch_compare


def test_learning_multiplier_doubling() -> None:
    # An 85% curve halves nothing but drops to 0.85 per production doubling.
    assert learning_multiplier(1, 0.85) == pytest.approx(1.0)
    assert learning_multiplier(2, 0.85) == pytest.approx(0.85)
    assert learning_multiplier(4, 0.85) == pytest.approx(0.85**2)
    assert learning_multiplier(8, 0.85) == pytest.approx(0.85**3)


def test_learning_multiplier_disabled() -> None:
    assert learning_multiplier(1000, 1.0) == 1.0
    assert learning_multiplier(0, 0.85) == 1.0


def test_learning_multiplier_matches_wright_exponent() -> None:
    b = math.log2(0.8)
    assert learning_multiplier(50, 0.8) == pytest.approx(50.0**b)


def test_trl_multiplier() -> None:
    assert trl_multiplier(9.0) == 1.0
    assert trl_multiplier(5.0) == pytest.approx(1.0 + 4 * 0.15)
    # never below 1.0
    assert trl_multiplier(11.0) == 1.0


def test_learning_lowers_lcoc() -> None:
    space = odc.load_scenario("examples/scenarios/orbital_1mw_inference.yaml")
    flat = odc.evaluate_space(space).lcoc_per_pflop_day
    learned = odc.evaluate_space(space, {"learning_rate": 0.85}).lcoc_per_pflop_day
    assert learned < flat


def test_learning_rate_is_a_design_var() -> None:
    from orbitdc.optimize.design import DESIGN_VARS

    assert "learning_rate" in DESIGN_VARS


def test_batch_compare_matrix() -> None:
    space = odc.load_scenario("examples/scenarios/orbital_1mw_inference.yaml")
    earths = [odc.load_scenario(p) for p in sorted(glob.glob("examples/scenarios/earth_*.yaml"))]
    res = batch_compare(space, earths)
    assert len(res.rows) == len(earths) == 5
    # Space LCOC is identical across all baselines (Earth-independent).
    assert all(r.space_lcoc == res.space_lcoc for r in res.rows)
    # Each row's verdict is consistent with its ratio.
    for r in res.rows:
        assert r.space_wins == (r.ratio < 1.0)
    assert 0 <= res.n_wins <= len(earths)
