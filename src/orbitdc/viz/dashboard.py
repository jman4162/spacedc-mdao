"""Panel exploration dashboard (Phase 2C; requires the ``viz`` extra).

Assembles the plotly figures into a tabbed app: overview, thermal, and
assumption provenance. Run inline in Jupyter, or ``panel serve`` a script that
calls ``build_dashboard(...).servable()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from orbitdc.compare import compare
from orbitdc.core.schema import Scenario
from orbitdc.thermal.catalog import get_chip_stack, get_radiator_surface
from orbitdc.thermal.presets import get_environment
from orbitdc.viz import plotly_figures as pf
from orbitdc.viz.provenance import provenance_table

if TYPE_CHECKING:
    import panel as pn


def build_dashboard(space: Scenario, earth: Scenario) -> pn.Tabs:
    """Build the tabbed exploration dashboard for a space/earth comparison."""
    import panel as pn

    pn.extension("plotly")
    result = compare(space, earth)
    ev = result.space

    overview = pn.Column(
        pn.pane.Markdown(f"### {result.summary().splitlines()[0]}"),
        pn.pane.Plotly(pf.delivered_waterfall(ev)),
        pn.pane.Plotly(pf.cost_breakdown(ev)),
        pn.pane.Plotly(pf.mass_treemap(ev)),
        pn.pane.Plotly(pf.power_sankey(ev)),
    )

    assert space.space is not None
    sp = space.space
    surface = get_radiator_surface(sp.radiator_panel)
    env = get_environment(sp.thermal_environment)
    from orbitdc.core.registry import get_accelerator

    stack = get_chip_stack(sp.chip_stack, get_accelerator(space.accelerator).tdp_w)
    q_waste = ev.details.get("bus_load_w", ev.it_power_w)
    t_rad = ev.details.get("radiator_t_rad_k", 330.0)
    thermal = pn.Column(
        pn.pane.Markdown(f"### Thermal: {ev.thermal_bottleneck}"),
        pn.pane.Plotly(pf.thermal_area_vs_temp(q_waste, surface, env)),
        pn.pane.Plotly(pf.net_flux_waterfall(t_rad, surface, env)),
        pn.pane.Plotly(pf.chip_temperature_ladder(t_rad, stack)),
    )

    provenance = pn.Column(pn.pane.Plotly(provenance_table()))

    return pn.Tabs(("Overview", overview), ("Thermal", thermal), ("Provenance", provenance))
