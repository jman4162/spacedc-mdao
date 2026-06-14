"""Panel dashboard entry point.

Run with:  uv run panel serve examples/dashboard_app.py --show
(requires the ``viz`` extra: uv sync --extra viz)
"""

from __future__ import annotations

from pathlib import Path

import orbitdc as odc
from orbitdc.viz.dashboard import build_dashboard

_SCEN = Path(__file__).parent / "scenarios"

build_dashboard(
    odc.load_scenario(_SCEN / "orbital_1mw_inference.yaml"),
    odc.load_scenario(_SCEN / "earth_hyperscale_baseline.yaml"),
).servable()
