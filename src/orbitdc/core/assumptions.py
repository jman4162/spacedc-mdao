"""The provenance-tagged value type.

Every default number in the package is an `Assumption`: it carries where the
number came from, when, how confident we are, and what kind of evidence backs
it. This is a first-class requirement, not a nicety -- it is the structural
antidote to confidently-wrong inputs, and it feeds the Monte Carlo and the
(future) provenance view. An `Assumption` can also sample from a distribution
for uncertainty sweeps.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

Confidence = str  # one of: "low", "medium", "high"
Kind = str  # one of: "empirical", "vendor", "estimated", "speculative"
Distribution = str  # one of: "point", "uniform", "triangular", "normal", "lognormal"

_CONFIDENCE = {"low", "medium", "high"}
_KIND = {"empirical", "vendor", "estimated", "speculative"}
_DISTRIBUTION = {"point", "uniform", "triangular", "normal", "lognormal"}


class Assumption(BaseModel):
    """A single numeric assumption with provenance and optional uncertainty.

    `value` is the nominal (point) estimate in `units`. For uncertainty sweeps,
    set `distribution` and supply `low`/`high` (and `std` for normal kinds).
    """

    model_config = ConfigDict(frozen=True)

    value: float
    units: str
    source: str
    date: str  # ISO date, e.g. "2026-06-13"
    confidence: Confidence = "medium"
    kind: Kind = "estimated"
    distribution: Distribution = "point"
    low: float | None = None
    high: float | None = None
    std: float | None = Field(default=None, description="std dev for normal/lognormal")

    @model_validator(mode="after")
    def _check(self) -> Assumption:
        if self.confidence not in _CONFIDENCE:
            raise ValueError(f"confidence must be one of {_CONFIDENCE}, got {self.confidence!r}")
        if self.kind not in _KIND:
            raise ValueError(f"kind must be one of {_KIND}, got {self.kind!r}")
        if self.distribution not in _DISTRIBUTION:
            raise ValueError(f"distribution must be one of {_DISTRIBUTION}")
        if self.distribution in {"uniform", "triangular"} and (
            self.low is None or self.high is None
        ):
            raise ValueError(f"{self.distribution} distribution requires low and high")
        if self.distribution in {"normal", "lognormal"} and self.std is None:
            raise ValueError(f"{self.distribution} distribution requires std")
        return self

    def sample(self, rng: np.random.Generator) -> float:
        """Draw one sample. A 'point' assumption always returns its nominal value."""
        if self.distribution == "point":
            return self.value
        if self.distribution == "uniform":
            assert self.low is not None and self.high is not None
            return float(rng.uniform(self.low, self.high))
        if self.distribution == "triangular":
            assert self.low is not None and self.high is not None
            return float(rng.triangular(self.low, self.value, self.high))
        if self.distribution == "normal":
            assert self.std is not None
            return float(rng.normal(self.value, self.std))
        # lognormal: interpret value as the median, std as sigma of underlying normal
        assert self.std is not None
        return float(rng.lognormal(np.log(self.value), self.std))
