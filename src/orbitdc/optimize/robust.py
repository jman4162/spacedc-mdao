"""Multi-scenario comparison and robust optimization (Phase 4B).

A space design's LCOC is independent of the Earth baseline, so "robustness across
Earth baselines" reduces to beating the *toughest* (cheapest) baseline. These
helpers make that explicit: a batch matrix of verdicts across baselines, and an
optimizer that minimizes space LCOC and reports how many baselines it then beats.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.compare import evaluate_earth, evaluate_space
from orbitdc.core.schema import Scenario


@dataclass(frozen=True)
class BatchRow:
    earth_label: str
    earth_lcoc: float
    space_lcoc: float
    ratio: float
    space_wins: bool


@dataclass(frozen=True)
class BatchResult:
    space_label: str
    space_lcoc: float
    rows: list[BatchRow]

    @property
    def n_wins(self) -> int:
        return sum(1 for r in self.rows if r.space_wins)


def batch_compare(space: Scenario, earths: list[Scenario]) -> BatchResult:
    """Compare one space design against several Earth baselines."""
    space_ev = evaluate_space(space)
    space_lcoc = space_ev.lcoc_per_pflop_day
    rows: list[BatchRow] = []
    for earth in earths:
        e = evaluate_earth(earth)
        ratio = space_lcoc / e.lcoc_per_pflop_day if e.lcoc_per_pflop_day > 0 else float("inf")
        rows.append(
            BatchRow(
                earth_label=earth.name,
                earth_lcoc=e.lcoc_per_pflop_day,
                space_lcoc=space_lcoc,
                ratio=ratio,
                space_wins=space_lcoc < e.lcoc_per_pflop_day,
            )
        )
    return BatchResult(space_label=space.name, space_lcoc=space_lcoc, rows=rows)


@dataclass(frozen=True)
class RobustResult:
    design: dict[str, float]
    space_lcoc: float
    n_baselines_beaten: int
    n_baselines: int


def robust_optimize(
    space: Scenario,
    earths: list[Scenario],
    design_vars: list[str],
    *,
    maxiter: int = 60,
) -> RobustResult:
    """Minimize space LCOC, then report how many Earth baselines it beats.

    Beating the toughest (cheapest) baseline implies beating them all, so this is
    the robust objective across the ensemble.
    """
    from orbitdc.mdao import optimize_single

    cons: list[tuple[str, float | None, float | None]] = [("radiator_packaging_ratio", None, 1.0)]
    result = optimize_single(space, "lcoc", design_vars, constraints=cons, maxiter=maxiter)
    space_lcoc = result["lcoc"]
    earth_lcocs = [evaluate_earth(e).lcoc_per_pflop_day for e in earths]
    beaten = sum(1 for el in earth_lcocs if space_lcoc < el)
    design = {k: v for k, v in result.items() if k in design_vars}
    return RobustResult(
        design=design,
        space_lcoc=space_lcoc,
        n_baselines_beaten=beaten,
        n_baselines=len(earths),
    )


def format_batch(result: BatchResult) -> str:
    lines = [f"{result.space_label}: space LCOC = {result.space_lcoc:,.0f} $/PFLOP-day", ""]
    lines.append(f"{'Earth baseline':<40}{'earth LCOC':>14}{'ratio':>10}  verdict")
    for r in result.rows:
        verdict = "SPACE wins" if r.space_wins else "earth wins"
        lines.append(f"{r.earth_label:<40}{r.earth_lcoc:>14,.0f}{r.ratio:>9.1f}x  {verdict}")
    lines.append("")
    lines.append(f"Space beats {result.n_wins}/{len(result.rows)} baselines.")
    return "\n".join(lines)


__all__ = [
    "BatchResult",
    "BatchRow",
    "RobustResult",
    "batch_compare",
    "format_batch",
    "robust_optimize",
]
