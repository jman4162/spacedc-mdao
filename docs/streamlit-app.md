# Interactive app

The repo ships a Streamlit app that puts the model behind sliders. It is the
zero-install way to probe the feasibility boundary: pick an orbital design and an
Earth baseline, then drag the uncertain assumptions and watch the verdict,
waterfalls, thermal stack, and architecture recompute live.

## Live demo

Deployed on Streamlit Community Cloud — link in the
[README](https://github.com/jman4162/spacedc-mdao#live-demo). No install needed.

## Run it locally

```bash
uv run --extra app streamlit run streamlit_app.py
```

The `app` extra is deliberately slim — `streamlit`, `plotly`, `networkx` on top
of the base package. It does not pull `panel`/`kaleido` (the `viz` extra) or the
heavy solver stack (`mdao`), so it deploys inside the free tier's memory budget.

## What each tab shows

- **Overview** — the LCOC verdict (orbital as a multiple of the Earth baseline),
  the delivered-compute and cost waterfalls, the binding constraints, and the
  single-driver thresholds at which orbital would match Earth.
- **Sensitivity & uncertainty** — a tornado of one-at-a-time LCOC swings and a
  Monte Carlo fan over the uncertain drivers, run around the selected scenario's
  baseline.
- **Thermal & architecture** — the radiator area-vs-temperature curve, the
  net-flux waterfall, the chip-to-radiator temperature ladder, the orbit-transient
  series, the power Sankey, the mass treemap, and the constellation graph.
- **Learn** — the delivered-compute principle, the two workload regimes (text
  inference vs rich multimodal output), and the full assumption-provenance table.

## How the sliders work

Each slider defaults to the value the selected scenario actually evaluates at, so
an untouched app reproduces `compare()` exactly. Moving a slider adds an entry to
the `overrides` dict threaded through `evaluate_space`, so the headline,
waterfalls, thermal, and architecture views are override-aware. The app is a thin
layer over the public API: model glue in `app/data.py`, rendering in `app/tabs.py`,
and the existing figure builders in `orbitdc.viz.plotly_figures`.

## Deploy your own

Point [Streamlit Community Cloud](https://share.streamlit.io/) at a fork of the
repo with `streamlit_app.py` as the entry point. It installs from
`requirements.txt` (the package via `.` plus the three app libraries).
