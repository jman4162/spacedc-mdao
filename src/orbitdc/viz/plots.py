"""Static matplotlib plots for Phase 1.

Three plots: the delivered-compute waterfall, the cost breakdown, and the
tornado. Each returns a Matplotlib Figure; callers decide whether to show or
save. Imports are local so importing orbitdc stays light.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from orbitdc.evaluation import Evaluation
from orbitdc.waterfall import FACTOR_LABELS, FACTOR_ORDER

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from orbitdc.optimize.sensitivity import TornadoEntry


def plot_delivered_waterfall(ev: Evaluation) -> Figure:
    """Bar chart of compute from installed peak down through each limiting factor."""
    import matplotlib.pyplot as plt

    wf = ev.waterfall
    labels = ["installed peak"] + [FACTOR_LABELS[f] for f in FACTOR_ORDER]
    values = [wf.peak_tflops] + [wf.stages_tflops[f] for f in FACTOR_ORDER]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(range(len(values)), values, color="#4c72b0")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("TFLOP/s")
    ax.set_title(f"Delivered-compute waterfall: {ev.label}")
    fig.tight_layout()
    return fig


def plot_cost_waterfall(ev: Evaluation) -> Figure:
    """Bar chart of the lifecycle cost breakdown."""
    import matplotlib.pyplot as plt

    items = [(k, v) for k, v in ev.cost_breakdown_usd.items() if not k.endswith("_total") or v > 0]
    items.sort(key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    values = [v / 1e6 for _, v in items]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(range(len(values)), values, color="#dd8452")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("USD (millions)")
    ax.set_title(f"Cost breakdown: {ev.label}")
    fig.tight_layout()
    return fig


def plot_tornado(entries: list[TornadoEntry], baseline_lcoc: float) -> Figure:
    """Horizontal tornado of LCOC swings around a baseline."""
    import matplotlib.pyplot as plt

    labels = [e.driver for e in entries]
    lows = [e.lcoc_low for e in entries]
    highs = [e.lcoc_high for e in entries]
    y = range(len(entries))

    fig, ax = plt.subplots(figsize=(9, 5))
    for i, (lo, hi) in enumerate(zip(lows, highs, strict=True)):
        left, right = min(lo, hi), max(lo, hi)
        ax.barh(i, right - left, left=left, color="#55a868")
    ax.axvline(baseline_lcoc, color="black", linestyle="--", label="baseline")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.set_xlabel("LCOC $/PFLOP-day")
    ax.set_title("Tornado: LCOC sensitivity")
    ax.legend()
    fig.tight_layout()
    return fig
