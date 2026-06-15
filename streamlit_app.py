"""Streamlit Cloud showcase app for orbitdc.

Run locally:  uv run --extra app streamlit run streamlit_app.py
Deploy:       point Streamlit Community Cloud at this repo + streamlit_app.py.

The app is a thin presentation layer over the orbitdc public API. Model glue
lives in app/data.py; figure rendering in app/tabs.py. This file owns the page
shell, the sidebar controls, and the (cached) model runs.
"""

from __future__ import annotations

import math

import streamlit as st
from app import data, tabs

st.set_page_config(
    page_title="Orbital data centers, by the numbers",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- cached model runs ------------------------------------------------------
# Keyed on hashable scalars (paths, override items) so sliders only recompute
# what they change. Tornado/Monte Carlo key on the scenario, not the overrides.


@st.cache_data(show_spinner=False)
def _space_eval(space_path: str, overrides_items: tuple[tuple[str, float], ...]):
    return data.run_space(data.load(space_path), dict(overrides_items))


@st.cache_data(show_spinner=False)
def _earth_eval(earth_path: str):
    return data.run_earth(data.load(earth_path))


@st.cache_data(show_spinner=False)
def _baselines(space_path: str) -> dict[str, float]:
    return data.baselines(data.load(space_path))


@st.cache_data(show_spinner=False)
def _thresholds(
    space_path: str, earth_lcoc: float, overrides_items: tuple[tuple[str, float], ...]
) -> list[str]:
    return data.thresholds(data.load(space_path), earth_lcoc, dict(overrides_items))


@st.cache_data(show_spinner=False)
def _tornado(space_path: str):
    space = data.load(space_path)
    return data.tornado_entries(space), data.baseline_lcoc(space)


@st.cache_data(show_spinner=False)
def _monte_carlo(space_path: str, earth_lcoc: float, n: int):
    return data.monte_carlo_result(data.load(space_path), earth_lcoc, n=n)


@st.cache_data(show_spinner=False)
def _scenarios(kind: str) -> list[data.ScenarioOption]:
    return data.list_scenarios(kind)


# --- sidebar controls -------------------------------------------------------


def _pick(label: str, kind: str, default_stem: str) -> str:
    options = _scenarios(kind)
    if not options:
        st.sidebar.error(f"No {kind} scenarios found under examples/scenarios.")
        st.stop()
    # Display the human-readable names directly; map the choice back to its path.
    names = [opt.name for opt in options]
    default_index = next((i for i, opt in enumerate(options) if default_stem in opt.path), 0)
    choice = st.sidebar.selectbox(label, names, index=default_index)
    return options[names.index(choice)].path


def _slider(spec: data.DriverSpec, baseline: float) -> float:
    """Render one driver slider defaulting to its scenario baseline."""
    key = f"drv_{spec.key}"
    if spec.log:
        lo_e, hi_e = math.log10(spec.lo), math.log10(spec.hi)
        base_e = math.log10(baseline) if baseline > 0 else lo_e
        lo_e, hi_e = min(lo_e, base_e), max(hi_e, base_e)
        exp = st.sidebar.slider(
            spec.label,
            min_value=float(lo_e),
            max_value=float(hi_e),
            value=float(base_e),
            step=0.1,
            help=spec.help,
            key=key,
        )
        return float(10.0**exp)
    lo, hi = min(spec.lo, baseline), max(spec.hi, baseline)
    return float(
        st.sidebar.slider(
            spec.label,
            min_value=float(lo),
            max_value=float(hi),
            value=float(baseline),
            help=spec.help,
            format=spec.fmt,
            key=key,
        )
    )


def _build_overrides(space_path: str) -> dict[str, float]:
    base = _baselines(space_path)
    st.sidebar.subheader("What would have to be true")
    st.sidebar.caption("Drag a slider to override an assumption and re-run live.")
    overrides: dict[str, float] = {}
    for spec in data.DRIVERS:
        b = base[spec.key]
        value = _slider(spec, b)
        # Only override when the user actually moved off the baseline, so the
        # untouched app reproduces compare() exactly.
        if b == 0.0 or abs(value / b - 1.0) > 1e-6:
            overrides[spec.key] = value
    if st.sidebar.button("Reset to scenario defaults", width="stretch"):
        for spec in data.DRIVERS:
            st.session_state.pop(f"drv_{spec.key}", None)
        st.rerun()
    return overrides


# --- page -------------------------------------------------------------------

st.title("🛰️ Orbital data centers, by the numbers")
st.caption(
    "An interactive physics-and-economics model of orbital compute versus the "
    "best terrestrial baselines. Move the sliders to see which assumptions decide "
    "whether the orbital case closes."
)
st.info(
    "Open the sidebar on the left (the **»** arrow at the top-left if it is "
    "collapsed) to choose scenarios and drag the assumption sliders.",
    icon="👈",
)

st.sidebar.header("Scenario")
space_path = _pick("Orbital design", "space", "orbital_1mw_inference")
earth_path = _pick("Earth baseline", "earth", "earth_hyperscale_baseline")
overrides = _build_overrides(space_path)

n_draws = st.sidebar.select_slider(
    "Monte Carlo draws", options=[100, 200, 300, 400, 500], value=300
)

overrides_items = tuple(sorted(overrides.items()))
space_ev = _space_eval(space_path, overrides_items)
earth_ev = _earth_eval(earth_path)
ratio = data.lcoc_ratio(space_ev, earth_ev)

st.sidebar.divider()
st.sidebar.metric("Orbital / Earth LCOC", f"{ratio:.1f}×")
if overrides:
    st.sidebar.caption(f"{len(overrides)} assumption(s) overridden.")

tab_overview, tab_sensitivity, tab_physics, tab_learn = st.tabs(
    ["Overview", "Sensitivity & uncertainty", "Thermal & architecture", "Learn"]
)

with tab_overview:
    binding = data.binding_constraints(space_ev)
    threshold_lines = _thresholds(space_path, earth_ev.lcoc_per_pflop_day, overrides_items)
    tabs.render_overview(space_ev, earth_ev, ratio, binding, threshold_lines)

with tab_sensitivity:
    entries, baseline_lcoc = _tornado(space_path)
    mc = _monte_carlo(space_path, earth_ev.lcoc_per_pflop_day, n_draws)
    tabs.render_sensitivity(entries, baseline_lcoc, mc, earth_ev.lcoc_per_pflop_day)

with tab_physics:
    tabs.render_thermal_architecture(data.load(space_path), space_ev)

with tab_learn:
    tabs.render_learn()
