"""Export a shareable comparison report (Phase 3C).

`export_report` writes a self-contained HTML (figures + narrative) or Markdown
(text) file with the git commit, timestamp, and scenario, so a result can be
archived or shared. HTML needs the ``viz`` extra; Markdown does not.
"""

from __future__ import annotations

import datetime
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from orbitdc.compare import ComparisonResult


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _provenance_lines() -> str:
    from orbitdc.viz.provenance import collect_provenance

    rows = collect_provenance()
    out = ["| catalog | entry | field | value | confidence | kind |", "|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["catalog"], x["entry"], x["field"])):
        out.append(
            f"| {r['catalog']} | {r['entry']} | {r['field']} | {r['value']:g} "
            f"| {r['confidence']} | {r['kind']} |"
        )
    return "\n".join(out)


def export_report(result: ComparisonResult, path: str | Path, fmt: str = "html") -> Path:
    """Write a comparison report to `path`. fmt is 'html' or 'md'."""
    out_path = Path(path)
    stamp = datetime.datetime.now(tz=datetime.UTC).isoformat(timespec="seconds")
    footer = f"generated {stamp} | commit {_git_commit()}"
    scenario_yaml = yaml.safe_dump(result._space_scenario.model_dump(), sort_keys=False)

    if fmt == "md":
        body = (
            f"# Report: {result.space.label}\n\n```\n{result.summary()}\n```\n\n"
            f"```\n{result.explain_binding_constraints()}\n```\n\n"
            f"## Scenario\n```yaml\n{scenario_yaml}```\n\n"
            f"## Assumptions\n{_provenance_lines()}\n\n_{footer}_\n"
        )
        out_path.write_text(body)
        return out_path

    import plotly.io as pio

    from orbitdc.viz import plotly_figures as pf

    figs = [
        pf.delivered_waterfall(result.space),
        pf.cost_waterfall(result.space),
        pf.mass_treemap(result.space),
    ]
    fig_html = "\n".join(
        pio.to_html(f, full_html=False, include_plotlyjs=("cdn" if i == 0 else False))
        for i, f in enumerate(figs)
    )
    html = (
        f"<html><head><meta charset='utf-8'><title>{result.space.label}</title></head><body>"
        f"<h1>{result.space.label}</h1>"
        f"<pre>{result.summary()}</pre>"
        f"<pre>{result.explain_binding_constraints()}</pre>"
        f"{fig_html}"
        f"<h2>Scenario</h2><pre>{scenario_yaml}</pre>"
        f"<hr><small>{footer}</small></body></html>"
    )
    out_path.write_text(html)
    return out_path
