"""Thermal Level 4: a parametric effective view factor to deep space.

Levels 0-3 assume a radiator sees a full cold-space hemisphere. A real panel
does not: it partly sees its own structure and the opposite face, it is
articulated off the ideal edge-to-sun attitude, and the solar array subtends
part of its sky. This module reduces the view factor parametrically — NOT by
ray tracing or Monte-Carlo integration, which stay Tier-3 plugins (see
``THEMRAL_RADIATOR_DEEPDIVE.md`` §4). Defaults are low confidence; expose them
as drivers rather than headline numbers.

The three losses combine multiplicatively on the nominal panel view factor:

    F_eff = F_nominal * cos(articulation) * (1 - self_view) * (1 - array_block)

Articulation enters as a cosine because a panel tilted by theta from its ideal
attitude projects less of its radiating area toward cold space.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ViewFactorResult:
    effective: float
    articulation_loss: float
    self_view_loss: float
    array_blocking_loss: float


def effective_view_factor(
    *,
    nominal: float = 0.95,
    articulation_deg: float = 0.0,
    self_view_frac: float = 0.05,
    array_blocking_frac: float = 0.10,
) -> ViewFactorResult:
    """Effective radiator view factor to deep space (0..nominal).

    nominal: panel's geometric view factor with no obstructions (catalog value).
    articulation_deg: panel attitude off the ideal cold-space pointing.
    self_view_frac: hemisphere fraction lost to own structure / opposite face.
    array_blocking_frac: hemisphere fraction subtended by the solar array.
    """
    cos_art = max(0.0, math.cos(math.radians(articulation_deg)))
    self_factor = max(0.0, 1.0 - self_view_frac)
    array_factor = max(0.0, 1.0 - array_blocking_frac)
    effective = nominal * cos_art * self_factor * array_factor
    return ViewFactorResult(
        effective=effective,
        articulation_loss=nominal * (1.0 - cos_art),
        self_view_loss=nominal * cos_art * self_view_frac,
        array_blocking_loss=nominal * cos_art * self_factor * array_blocking_frac,
    )


__all__ = ["ViewFactorResult", "effective_view_factor"]
