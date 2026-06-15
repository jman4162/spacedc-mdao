"""Regenerate the README/docs visual assets from the bundled scenarios.

Run under the viz extra:

    uv run --extra viz python scripts/generate_readme_assets.py

Every number comes from the model (no hand-typed constants), so the README stays
honest as the catalogs change. Outputs go to docs/assets/img/:

- viability_ladder.gif  hero animation: LCOC vs Earth as each lever is applied
- delivered_waterfall.png  installed peak degraded to delivered compute
- tornado.png           which assumptions move LCOC
- monte_carlo.png       LCOC distribution + P(space wins)
- power_sankey.png      solar -> IT/housekeeping/pump -> radiated heat
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import plotly.io as pio
from matplotlib.animation import FuncAnimation

import orbitdc as odc
from orbitdc.core.schema import Scenario
from orbitdc.optimize.sensitivity import tornado
from orbitdc.viz import plotly_figures as pf
from orbitdc.viz.plots import plot_delivered_waterfall

SPACE = "examples/scenarios/orbital_1mw_inference.yaml"
EARTH = "examples/scenarios/earth_hyperscale_baseline.yaml"
OUT = Path("docs/assets/img")

# Cumulative levers for the text-inference demo (network already un-bound at the
# 0.75 optical-weather ceiling), each set to its aggressive/speculative bound in
# impact order. The labels carry the current -> target move.
LEVERS: list[tuple[str, dict[str, float]]] = [
    ("baseline (text inference)", {}),
    (
        "+ optical availability 0.75 -> 0.95 (site diversity)",
        {"optical_downlink_availability": 0.95},
    ),
    ("+ launch $1,500 -> $200/kg", {"launch_cost_per_kg_usd": 200.0}),
    ("+ production learning (0.8)", {"learning_rate": 0.8}),
    ("+ solar 100 -> 200 W/kg", {"solar_specific_power_w_per_kg": 200.0}),
    ("+ radiator 7 -> 2 kg/m^2", {"radiator_areal_mass_kg_per_m2": 2.0}),
    ("+ utilization 0.85 -> 0.98", {"utilization": 0.98}),
    ("+ failure 0.05 -> 0.01 /yr", {"annual_failure_rate": 0.01}),
]


def _ladder(space: Scenario, earth_lcoc: float) -> tuple[list[str], list[float]]:
    """Cumulative (label, x-Earth) pairs as each lever is stacked."""
    cum: dict[str, float] = {}
    labels: list[str] = []
    ratios: list[float] = []
    for label, ov in LEVERS:
        cum.update(ov)
        lcoc = odc.evaluate_space(space, dict(cum)).lcoc_per_pflop_day
        labels.append(label)
        ratios.append(lcoc / earth_lcoc)
    return labels, ratios


def viability_ladder_gif(space: Scenario, earth_lcoc: float, path: Path) -> None:
    labels, ratios = _ladder(space, earth_lcoc)
    n = len(ratios)
    fig, ax = plt.subplots(figsize=(9, 5))

    def draw(frame: int) -> None:
        ax.clear()
        shown = frame + 1
        colors = ["#c44e52" if shown <= 1 else "#4c72b0"] * shown
        colors[-1] = "#dd8452"
        ax.barh(range(shown), ratios[:shown], color=colors)
        ax.axvline(1.0, color="black", linestyle="--", linewidth=1.5)
        ax.text(1.05, -0.6, "Earth parity (1x)", color="black", fontsize=9)
        ax.set_xscale("log")
        ax.set_xlim(0.7, 40)
        ax.set_ylim(-1, n)
        ax.set_yticks(range(shown))
        ax.set_yticklabels(labels[:shown], fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("space LCOC, multiples of Earth (log scale)")
        cur = ratios[shown - 1]
        ax.set_title(f"Path to viability (1 MW text inference): {cur:.0f}x Earth")
        for i in range(shown):
            ax.text(ratios[i] * 1.05, i, f"{ratios[i]:.0f}x", va="center", fontsize=8)
        if shown == n:
            ax.text(
                0.98,
                0.04,
                f"frontier {ratios[-1]:.0f}x Earth: every lever maxed, still does not close",
                transform=ax.transAxes,
                ha="right",
                fontsize=9,
                color="#c44e52",
            )
        fig.tight_layout()

    # Hold the final frame a few extra beats so the verdict reads.
    frames = list(range(n)) + [n - 1] * 6
    anim = FuncAnimation(fig, draw, frames=frames, interval=900)
    anim.save(path, writer="pillow", dpi=110)
    plt.close(fig)


def _write_png(fig: object, path: Path, *, plotly: bool = True) -> None:
    if plotly:
        pio.write_image(fig, path, width=900, height=520, scale=2)
    else:
        fig.savefig(path, dpi=130, bbox_inches="tight")  # type: ignore[attr-defined]
        plt.close(fig)  # type: ignore[arg-type]


def main() -> None:
    plt.switch_backend("Agg")
    OUT.mkdir(parents=True, exist_ok=True)
    space = odc.load_scenario(SPACE)
    earth = odc.load_scenario(EARTH)
    result = odc.compare(space, earth)
    earth_lcoc = result.earth.lcoc_per_pflop_day

    print(f"space LCOC={result.space.lcoc_per_pflop_day:,.0f}  earth LCOC={earth_lcoc:,.0f}")

    viability_ladder_gif(space, earth_lcoc, OUT / "viability_ladder.gif")
    print("wrote viability_ladder.gif")

    _write_png(
        plot_delivered_waterfall(result.space), OUT / "delivered_waterfall.png", plotly=False
    )
    _write_png(pf.tornado(tornado(space), result.space.lcoc_per_pflop_day), OUT / "tornado.png")
    mc = result.monte_carlo(n=500, seed=0)
    _write_png(pf.monte_carlo_fan(mc, earth_lcoc), OUT / "monte_carlo.png")
    _write_png(pf.power_sankey(result.space), OUT / "power_sankey.png")
    print(f"wrote 4 PNGs; P(space wins)={mc.p_space_wins:.0%}")


if __name__ == "__main__":
    main()
