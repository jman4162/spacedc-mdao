"""Assumption-provenance panel (SPEC viz #12).

Walks every data catalog and surfaces each provenance-tagged number with its
source, date, confidence, and kind — making bad assumptions visible.
"""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING, Any, cast

import yaml

if TYPE_CHECKING:
    from plotly.graph_objects import Figure

_CATALOGS = [
    "accelerators.yaml",
    "solar_arrays.yaml",
    "batteries.yaml",
    "radiators.yaml",
    "launch.yaml",
    "coatings.yaml",
    "coolants.yaml",
    "chip_stacks.yaml",
    "radiator_panels.yaml",
]


def collect_provenance() -> list[dict[str, Any]]:
    """Flat list of every provenance-tagged catalog value."""
    rows: list[dict[str, Any]] = []
    for filename in _CATALOGS:
        data = cast(dict[str, Any], yaml.safe_load((files("orbitdc.data") / filename).read_text()))
        catalog = filename.removesuffix(".yaml")
        for entry, fields in (data or {}).items():
            for field, raw in fields.items():
                if isinstance(raw, dict) and "value" in raw:
                    rows.append(
                        {
                            "catalog": catalog,
                            "entry": entry,
                            "field": field,
                            "value": raw["value"],
                            "units": raw.get("units", ""),
                            "source": raw.get("source", ""),
                            "date": raw.get("date", ""),
                            "confidence": raw.get("confidence", ""),
                            "kind": raw.get("kind", ""),
                        }
                    )
    return rows


def provenance_table() -> Figure:
    """A plotly Table of all provenance-tagged assumptions."""
    import plotly.graph_objects as go

    rows = collect_provenance()
    columns = ["catalog", "entry", "field", "value", "units", "confidence", "kind", "source"]
    fig = go.Figure(
        go.Table(
            header={"values": columns, "align": "left"},
            cells={"values": [[r[c] for r in rows] for c in columns], "align": "left"},
        )
    )
    fig.update_layout(title="Assumption provenance")
    return fig
