"""Tier-4 empirical calibration (SPEC §"Recommended model tiers").

Fit a model parameter to measured / flight / benchmark data by least squares and
return it as a provenance-tagged `Assumption` (kind="empirical") whose confidence
reflects the fit residual. This is the entry point for grounding the package's
defaults in real data rather than estimates.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
from scipy.optimize import least_squares

from orbitdc.core.assumptions import Assumption


def fit_parameter(
    x_data: Sequence[float],
    y_data: Sequence[float],
    model: Callable[[float, float], float],
    *,
    initial: float,
    name: str,
    units: str,
    source: str,
    date: str,
) -> Assumption:
    """Fit a single parameter `p` so that `model(x, p) ~ y` over the data.

    Returns an `Assumption` with the fitted value; confidence is high/medium/low
    by the normalized RMS residual.
    """
    xs = np.asarray(x_data, dtype=float)
    ys = np.asarray(y_data, dtype=float)

    def residuals(p: np.ndarray) -> np.ndarray:
        return np.array([model(float(x), float(p[0])) - y for x, y in zip(xs, ys, strict=True)])

    result = least_squares(residuals, x0=[initial])
    value = float(result.x[0])

    rms = float(np.sqrt(np.mean(residuals(result.x) ** 2)))
    scale = float(np.mean(np.abs(ys))) or 1.0
    rel = rms / scale
    confidence = "high" if rel < 0.02 else "medium" if rel < 0.10 else "low"

    return Assumption(
        value=value,
        units=units,
        source=f"{source} (least-squares fit, rel. RMS {rel:.1%})",
        date=date,
        confidence=confidence,
        kind="empirical",
    )
