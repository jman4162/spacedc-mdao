"""Dark "mission control" styling applied to every plotly figure.

The figure builders in ``orbitdc.viz.plotly_figures`` set their own titles and
trace colors; this just swaps in a dark template with transparent backgrounds so
they sit on the Streamlit dark theme.
"""

from __future__ import annotations

from typing import Any

ACCENT = "#5b8ff9"
GOOD = "#3fb950"
WARN = "#d29922"
BAD = "#f85149"
FONT = "ui-monospace, SFMono-Regular, Menlo, monospace"


def style(fig: Any) -> Any:
    """Apply the dark template + transparent canvas, returning the same figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT, "color": "#e6edf3", "size": 13},
        title_font={"family": FONT, "size": 16},
        margin={"l": 50, "r": 24, "t": 56, "b": 44},
    )
    return fig
