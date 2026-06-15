"""Streamlit tab renderers for the orbitdc showcase.

Thin presentation over ``app.data`` and the existing plotly builders in
``orbitdc.viz.plotly_figures``. No model math lives here.
"""

from __future__ import annotations

import streamlit as st

from app import data
from app.theme import style
from orbitdc.core.schema import Scenario
from orbitdc.evaluation import Evaluation
from orbitdc.optimize.sensitivity import TornadoEntry
from orbitdc.optimize.uncertainty import MonteCarloResult
from orbitdc.viz import plotly_figures as pf
from orbitdc.viz.provenance import collect_provenance


def _chart(fig: object) -> None:
    st.plotly_chart(style(fig), width="stretch")


# --- Overview / verdict -----------------------------------------------------


def render_overview(
    space_ev: Evaluation,
    earth_ev: Evaluation,
    ratio: float,
    binding: list[str],
    threshold_lines: list[str],
) -> None:
    if ratio < 1.0:
        st.success(f"Orbital LCOC is **{ratio:.2f}×** the Earth baseline — space wins here.")
    else:
        st.warning(
            f"Orbital LCOC is **{ratio:.1f}×** the Earth baseline. "
            "The waterfall below shows what limits it."
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orbital LCOC", f"${space_ev.lcoc_per_pflop_day:,.0f}", help="$/PFLOP-day")
    c2.metric("Earth LCOC", f"${earth_ev.lcoc_per_pflop_day:,.0f}", help="$/PFLOP-day")
    c3.metric(
        "Space vs Earth",
        f"{ratio:.1f}×",
        delta=f"{(ratio - 1.0) * 100:+.0f}% vs parity",
        delta_color="inverse",
    )
    c4.metric("Delivered fraction", f"{space_ev.delivered_fraction:.0%}", help="of installed peak")

    st.caption(
        "LCOC is the levelized cost of compute. The orbital number is "
        "Earth-independent; every Earth baseline it must beat is just a different "
        "horizontal line."
    )

    left, right = st.columns(2)
    with left:
        _chart(pf.delivered_waterfall(space_ev))
    with right:
        _chart(pf.cost_waterfall(space_ev))

    st.subheader("Binding constraints")
    st.caption("What actually limits this design — read these before the cost number.")
    for note in binding:
        st.markdown(f"- {note}")

    with st.expander("What would have to be true to match Earth"):
        st.caption("Single-driver crossover points, holding the current slider values fixed.")
        for line in threshold_lines:
            st.markdown(f"- {line}")


# --- Sensitivity & uncertainty ----------------------------------------------


def render_sensitivity(
    entries: list[TornadoEntry],
    baseline_lcoc: float,
    mc: MonteCarloResult,
    earth_lcoc: float,
) -> None:
    st.subheader("Which assumptions decide it")
    st.caption(
        "One-at-a-time swings and a Monte Carlo over the uncertain drivers, run "
        "around the selected scenario's baseline (independent of the sliders)."
    )
    _chart(pf.tornado(entries, baseline_lcoc))

    st.subheader("Uncertainty")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("P(space beats Earth)", f"{mc.p_space_wins:.0%}")
    m2.metric("LCOC p10", f"${mc.lcoc_p10:,.0f}")
    m3.metric("LCOC p50", f"${mc.lcoc_p50:,.0f}")
    m4.metric("LCOC p90", f"${mc.lcoc_p90:,.0f}")
    _chart(pf.monte_carlo_fan(mc, earth_lcoc))


# --- Thermal & architecture -------------------------------------------------


def render_thermal_architecture(space: Scenario, space_ev: Evaluation) -> None:
    ti = data.thermal_inputs(space, space_ev)

    st.subheader("Heat rejection")
    if ti.bottleneck:
        st.info(f"Thermal bottleneck: **{ti.bottleneck}** (radiator runs at ~{ti.t_rad_k:.0f} K).")
    left, right = st.columns(2)
    with left:
        _chart(pf.thermal_area_vs_temp(ti.q_waste_w, ti.surface, ti.env))
        _chart(pf.chip_temperature_ladder(ti.t_rad_k, ti.stack))
    with right:
        _chart(pf.net_flux_waterfall(ti.t_rad_k, ti.surface, ti.env))
        _chart(pf.orbit_timeline(ti.transient))

    st.subheader("Power and mass")
    left, right = st.columns(2)
    with left:
        _chart(pf.power_sankey(space_ev))
    with right:
        _chart(pf.mass_treemap(space_ev))

    assert space.space is not None
    arch = space.space.architecture
    n_sat = arch.satellites
    shown = min(n_sat, 48)
    st.subheader(f"Constellation ({n_sat} satellites, {arch.crosslink} crosslink)")
    if shown < n_sat:
        st.caption(f"Showing {shown} of {n_sat} satellites for legibility.")
    _chart(pf.constellation_graph(shown, crosslink=arch.crosslink))


# --- Learn & provenance -----------------------------------------------------

_LEARN_MD = """
### The one number that matters: delivered compute, not nameplate watts

This model exists to take installed capacity and degrade it through real physics
and economics. The central artifact is the **delivered-compute waterfall**:

```
installed peak → power-available → thermally-allowable → network-limited
→ reliability-adjusted → utilization-adjusted → delivered compute
```

Each step is a factor below 1. Power closure does **not** imply thermal closure:
you can have enough solar watts and still be unable to reject the heat. The cost
chain rides the same waterfall — useful compute drives power, heat, radiator
area, mass, launch cost, and lifetime delivered compute.

### Two workload regimes set the whole answer

The decisive orbital assumption is **communication intensity** — bits moved
off-satellite per delivered FLOP:

- **Text inference (~1e-8 bits/FLOP):** network un-binds; the orbital design runs
  roughly **~19×** a best-in-class Earth baseline, limited by launch and the
  satellite bus, not the downlink.
- **Rich multimodal output (~2e-6 bits/FLOP):** the optical downlink binds and
  the gap widens to **~82×**.

Training is hopelessly comms-bound and is not a near-term orbital workload.

### How to read this app

Move the sidebar sliders to ask *what would have to be true*. The headline,
waterfalls, thermal, and architecture views recompute live. The sensitivity tab
shows which assumption is doing the work; the table below is every default
number with its source and confidence — nothing here is a hidden magic constant.

Built on the orbitdc package. Full method: the
[white paper](https://github.com/jman4162/spacedc-mdao/blob/main/docs/whitepaper.md)
and [docs site](https://jman4162.github.io/spacedc-mdao/).
"""


def render_learn() -> None:
    st.markdown(_LEARN_MD)
    st.subheader("Assumption provenance")
    st.caption("Every default value, with source, date, confidence, and kind.")

    rows = collect_provenance()
    kinds = sorted({str(r.get("kind", "")) for r in rows})
    confidences = sorted({str(r.get("confidence", "")) for r in rows})
    f1, f2 = st.columns(2)
    pick_kind = f1.multiselect("Kind", kinds, default=kinds)
    pick_conf = f2.multiselect("Confidence", confidences, default=confidences)

    filtered = [
        r
        for r in rows
        if str(r.get("kind", "")) in pick_kind and str(r.get("confidence", "")) in pick_conf
    ]
    st.dataframe(filtered, width="stretch", hide_index=True)
    st.caption(f"{len(filtered)} of {len(rows)} catalog values shown.")
