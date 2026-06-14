"""MkDocs hook: generate the assumptions/provenance page from the catalogs.

Runs at build time so the published table always matches the shipped catalogs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def on_pre_build(config: Any) -> None:
    from orbitdc.viz.provenance import collect_provenance

    rows = collect_provenance()
    rows.sort(key=lambda r: (r["catalog"], r["entry"], r["field"]))

    lines = [
        "# Assumptions & provenance",
        "",
        "Every default number in `spacedc-mdao` is a provenance-tagged "
        "`Assumption` (value, units, source, date, confidence, kind). This page "
        "is generated from the catalogs at build time. Low-confidence values are "
        "the ones to challenge first; the package keeps them as sensitivity "
        "drivers, not headline claims.",
        "",
        f"**{len(rows)} provenance-tagged values.**",
        "",
        "| Catalog | Entry | Field | Value | Confidence | Kind | Source |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for r in rows:
        source = str(r.get("source", "")).replace("|", "\\|")
        lines.append(
            f"| {r['catalog']} | {r['entry']} | {r['field']} | "
            f"{r['value']:,.4g} | {r['confidence']} | {r['kind']} | {source} |"
        )

    out = Path(__file__).parent / "provenance.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
