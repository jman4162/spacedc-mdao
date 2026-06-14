"""Interactive plotly figures (Phase 2C; requires the ``viz`` extra).

Each builder returns a ``plotly.graph_objects.Figure``. Imports are local so the
base package stays plotly-free. Several figures back the SPEC's exploration
environment and the deep-dive's thermal dashboard.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orbitdc.evaluation import Evaluation
from orbitdc.waterfall import FACTOR_LABELS, FACTOR_ORDER

if TYPE_CHECKING:
    from plotly.graph_objects import Figure

    from orbitdc.optimize.pareto import ParetoResult
    from orbitdc.optimize.sensitivity import TornadoEntry
    from orbitdc.optimize.uncertainty import MonteCarloResult
    from orbitdc.thermal.surfaces import ChipThermalStack, RadiatorSurface, ThermalEnvironment
    from orbitdc.thermal.transient import TransientResult


def delivered_waterfall(ev: Evaluation) -> Figure:
    """Installed peak compute degraded through each limiting factor."""
    import plotly.graph_objects as go

    wf = ev.waterfall
    labels = ["installed peak"] + [FACTOR_LABELS[f] for f in FACTOR_ORDER]
    values = [wf.peak_tflops] + [wf.stages_tflops[f] for f in FACTOR_ORDER]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color="#4c72b0"))
    fig.update_layout(title=f"Delivered-compute waterfall: {ev.label}", yaxis_title="TFLOP/s")
    return fig


def cost_breakdown(ev: Evaluation) -> Figure:
    """Lifecycle cost components (USD millions)."""
    import plotly.graph_objects as go

    items = sorted(ev.cost_breakdown_usd.items(), key=lambda kv: kv[1], reverse=True)
    fig = go.Figure(
        go.Bar(x=[k for k, _ in items], y=[v / 1e6 for _, v in items], marker_color="#dd8452")
    )
    fig.update_layout(title=f"Cost breakdown: {ev.label}", yaxis_title="USD (millions)")
    return fig


def mass_treemap(ev: Evaluation) -> Figure:
    """Dry-mass breakdown as a treemap."""
    import plotly.graph_objects as go

    breakdown = ev.mass_breakdown_kg or {}
    labels = list(breakdown)
    fig = go.Figure(
        go.Treemap(labels=labels, parents=[""] * len(labels), values=list(breakdown.values()))
    )
    fig.update_layout(title=f"Mass treemap: {ev.label}")
    return fig


def power_sankey(ev: Evaluation) -> Figure:
    """Solar -> bus -> IT / housekeeping / pump -> waste heat -> radiated."""
    import plotly.graph_objects as go

    bus = ev.details.get("bus_load_w", ev.it_power_w)
    it = ev.it_power_w
    pump = ev.details.get("thermal_pump_power_kw", 0.0) * 1000.0
    house = max(0.0, bus - it - pump)
    nodes = ["solar", "IT", "housekeeping", "pump", "waste heat", "radiated"]
    src = [0, 0, 0, 1, 2, 3, 4]
    dst = [1, 2, 3, 4, 4, 4, 5]
    val = [it, house, pump, it, house, pump, bus]
    fig = go.Figure(
        go.Sankey(
            node={"label": nodes},
            link={"source": src, "target": dst, "value": [v / 1000.0 for v in val]},
        )
    )
    fig.update_layout(title=f"Power flow (kW): {ev.label}")
    return fig


def tornado(entries: list[TornadoEntry], baseline_lcoc: float) -> Figure:
    """LCOC swings per driver around a baseline."""
    import plotly.graph_objects as go

    fig = go.Figure()
    for e in entries:
        lo, hi = min(e.lcoc_low, e.lcoc_high), max(e.lcoc_low, e.lcoc_high)
        fig.add_trace(go.Bar(y=[e.driver], x=[hi - lo], base=lo, orientation="h", name=e.driver))
    fig.add_vline(x=baseline_lcoc, line_dash="dash")
    fig.update_layout(
        title="Tornado: LCOC sensitivity", xaxis_title="LCOC $/PFLOP-day", showlegend=False
    )
    return fig


def pareto_scatter(pf: ParetoResult) -> Figure:
    """Scatter (2 objectives) or parallel coordinates (3+)."""
    import plotly.graph_objects as go

    if len(pf.objectives) == 2:
        fig = go.Figure(go.Scatter(x=pf.f[:, 0], y=pf.f[:, 1], mode="markers", marker={"size": 9}))
        fig.update_layout(
            title="Pareto front", xaxis_title=pf.objectives[0], yaxis_title=pf.objectives[1]
        )
        return fig
    dims = [{"label": o, "values": pf.f[:, i]} for i, o in enumerate(pf.objectives)]
    fig = go.Figure(go.Parcoords(dimensions=dims))
    fig.update_layout(title="Pareto front (parallel coordinates)")
    return fig


def thermal_area_vs_temp(
    q_waste_w: float,
    surface: RadiatorSurface,
    env: ThermalEnvironment,
    t_min: float = 290.0,
    t_max: float = 380.0,
) -> Figure:
    """Required radiator area as a function of radiator temperature (EOL)."""
    import plotly.graph_objects as go

    from orbitdc.thermal.radiation import required_area_m2

    temps = [t_min + i * (t_max - t_min) / 40.0 for i in range(41)]
    areas = [required_area_m2(q_waste_w, t, surface, env, eol=True) for t in temps]
    fig = go.Figure(go.Scatter(x=temps, y=areas, mode="lines"))
    fig.update_layout(
        title="Radiator area vs temperature (EOL)",
        xaxis_title="radiator temperature (K)",
        yaxis_title="area (m^2)",
    )
    return fig


def net_flux_waterfall(t_rad_k: float, surface: RadiatorSurface, env: ThermalEnvironment) -> Figure:
    """Emitted minus absorbed solar/albedo/Earth-IR = net W/m^2."""
    import plotly.graph_objects as go

    from orbitdc.thermal.radiation import emitted_flux_w_m2

    eps = surface.coating.eps(eol=True)
    alpha = surface.coating.alpha(eol=True)
    emitted = emitted_flux_w_m2(t_rad_k, eps, surface.sides, env.deep_space_sink_k)
    solar = alpha * env.solar_w_m2 * env.sun_incidence_cos
    albedo = alpha * env.albedo * env.solar_w_m2 * env.view_factor_earth
    earth_ir = eps * env.earth_ir_w_m2 * env.view_factor_earth
    fig = go.Figure(
        go.Waterfall(
            x=["emitted", "-solar", "-albedo", "-Earth IR", "net"],
            measure=["absolute", "relative", "relative", "relative", "total"],
            y=[emitted, -solar, -albedo, -earth_ir, 0.0],
        )
    )
    fig.update_layout(title=f"Net radiator flux at {t_rad_k:.0f} K", yaxis_title="W/m^2")
    return fig


def chip_temperature_ladder(t_rad_k: float, stack: ChipThermalStack) -> Figure:
    """Temperature rise from radiator up to the junction along the resistance stack."""
    import plotly.graph_objects as go

    q = stack.chip_power_w
    steps = [
        ("radiator", t_rad_k),
        ("transport", q * stack.r_transport),
        ("cold plate", q * stack.r_coldplate),
        ("TIM", q * stack.r_tim),
        ("junction-case", q * stack.r_junction_to_case),
    ]
    labels = []
    temps = []
    running = 0.0
    for name, delta in steps:
        running = delta if name == "radiator" else running + delta
        labels.append(name)
        temps.append(running)
    fig = go.Figure(go.Bar(x=labels, y=temps, marker_color="#c44e52"))
    fig.add_hline(y=stack.tj_max_k, line_dash="dash", annotation_text="Tj_max")
    fig.update_layout(title="Chip-to-radiator temperature ladder", yaxis_title="temperature (K)")
    return fig


def cost_waterfall(ev: Evaluation) -> Figure:
    """True cost waterfall: cumulative lifecycle cost flowing through components."""
    import plotly.graph_objects as go

    items = sorted(
        ((k, v) for k, v in ev.cost_breakdown_usd.items() if not k.endswith("_total")),
        key=lambda kv: kv[1],
        reverse=True,
    )
    labels = [k for k, _ in items] + ["lifecycle PV"]
    values = [v / 1e6 for _, v in items] + [0.0]
    measure = ["relative"] * len(items) + ["total"]
    fig = go.Figure(go.Waterfall(x=labels, y=values, measure=measure))
    fig.update_layout(title=f"Cost waterfall: {ev.label}", yaxis_title="USD (millions)")
    return fig


def monte_carlo_fan(mc: MonteCarloResult, earth_lcoc: float) -> Figure:
    """Uncertainty fan: LCOC distribution with the 'space wins' region shaded."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=mc.lcoc_samples, nbinsx=40, name="space LCOC"))
    for label, value in (("p10", mc.lcoc_p10), ("p50", mc.lcoc_p50), ("p90", mc.lcoc_p90)):
        fig.add_vline(x=value, line_dash="dot", annotation_text=label)
    fig.add_vline(x=earth_lcoc, line_color="red", annotation_text="Earth")
    fig.update_layout(
        title=f"LCOC uncertainty (P(space wins) = {mc.p_space_wins:.0%})",
        xaxis_title="LCOC $/PFLOP-day",
        yaxis_title="count",
    )
    return fig


def orbit_timeline(transient: TransientResult) -> Figure:
    """Radiator temperature, throttle, and sunlit/eclipse bands over one orbit."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    minutes = transient.time_s / 60.0
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=minutes, y=transient.t_rad_k, name="T_rad (K)"), secondary_y=False)
    fig.add_trace(go.Scatter(x=minutes, y=transient.throttle, name="throttle"), secondary_y=True)
    # Shade eclipse spans.
    eclipse = ~transient.sunlit_mask
    if eclipse.any():
        start = minutes[eclipse][0]
        end = minutes[eclipse][-1]
        fig.add_vrect(x0=start, x1=end, fillcolor="gray", opacity=0.15, line_width=0)
    fig.update_xaxes(title_text="time (min)")
    fig.update_yaxes(title_text="radiator temperature (K)", secondary_y=False)
    fig.update_yaxes(title_text="throttle fraction", secondary_y=True, range=[0, 1.05])
    fig.update_layout(title="Orbit timeline: radiator temperature and throttle")
    return fig


def link_budget_heatmap(
    *,
    tx_power_w: float = 5.0,
    wavelength_m: float = 1.55e-6,
    rx_aperture_m: float = 0.3,
    pointing_error_rad: float = 1.0e-6,
) -> Figure:
    """Optical link margin (dB) over transmit aperture x range."""
    import numpy as np
    import plotly.graph_objects as go

    from orbitdc.models.lasercom import optical_link

    apertures = np.linspace(0.05, 0.5, 24)
    ranges_km = np.linspace(200.0, 3000.0, 24)
    margin = np.empty((len(ranges_km), len(apertures)))
    for i, rng in enumerate(ranges_km):
        for j, ap in enumerate(apertures):
            res = optical_link(
                tx_power_w=tx_power_w,
                wavelength_m=wavelength_m,
                tx_aperture_m=float(ap),
                rx_aperture_m=rx_aperture_m,
                range_m=float(rng) * 1000.0,
                pointing_error_rad=pointing_error_rad,
            )
            margin[i, j] = res.margin_db
    fig = go.Figure(go.Heatmap(x=apertures, y=ranges_km, z=margin, colorbar={"title": "margin dB"}))
    fig.update_layout(
        title="Optical link margin",
        xaxis_title="transmit aperture (m)",
        yaxis_title="range (km)",
    )
    return fig


def constellation_graph(n_satellites: int, crosslink: str = "optical") -> Figure:
    """Satellites as a ring graph with crosslink edges (networkx layout)."""
    import networkx as nx
    import plotly.graph_objects as go

    n = min(n_satellites, 64)
    g = nx.cycle_graph(n)
    pos: dict[int, Any] = nx.circular_layout(g)
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for a, b in g.edges():
        edge_x += [pos[a][0], pos[b][0], None]
        edge_y += [pos[a][1], pos[b][1], None]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line={"color": "#999"}))
    fig.add_trace(
        go.Scatter(
            x=[pos[i][0] for i in g.nodes()],
            y=[pos[i][1] for i in g.nodes()],
            mode="markers",
            marker={"size": 8, "color": "#4c72b0"},
        )
    )
    fig.update_layout(
        title=f"Constellation: {n} satellites, {crosslink} crosslinks",
        showlegend=False,
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig
