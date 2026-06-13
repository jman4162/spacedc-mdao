"""Tests for the provenance-tagged Assumption type and catalog loading."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from orbitdc.core.assumptions import Assumption
from orbitdc.core.registry import get_launch, provenance


def _a(**kw: object) -> Assumption:
    base: dict[str, object] = {
        "value": 10.0,
        "units": "x",
        "source": "test",
        "date": "2026-06-13",
    }
    base.update(kw)
    return Assumption(**base)  # type: ignore[arg-type]


def test_point_sample_is_nominal() -> None:
    rng = np.random.default_rng(0)
    a = _a(value=42.0)
    assert a.sample(rng) == 42.0


def test_triangular_sample_in_range() -> None:
    rng = np.random.default_rng(0)
    a = _a(distribution="triangular", low=1.0, high=3.0, value=2.0)
    for _ in range(100):
        s = a.sample(rng)
        assert 1.0 <= s <= 3.0


def test_invalid_kind_rejected() -> None:
    with pytest.raises(ValidationError):
        _a(kind="marketing")


def test_triangular_requires_bounds() -> None:
    with pytest.raises(ValidationError):
        _a(distribution="triangular")


def test_launch_cost_carries_distribution() -> None:
    # The catalog value resolves to a float for the model path...
    launch = get_launch("current_reusable")
    assert launch.cost_per_kg_usd == 3000.0
    # ...and the provenance keeps the distribution for sampling.
    prov = provenance("launch")["current_reusable"]["cost_per_kg_usd"]
    assert prov.distribution == "triangular"
    assert prov.kind == "estimated"
