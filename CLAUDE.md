# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status: greenfield

There is **no code yet**. The repo currently contains only:

- `SPEC.md` — the authoritative design contract. Read it before doing any implementation work; it defines the package concept, model families, package layout, tech-stack choices, and MVP scope.
- `EQUATIONS.md` — the authoritative equation map: the coupled conservation laws and bottleneck equations behind every model (compute, power, thermal, mass, orbit, RF, optical, network, reliability, cost, Earth baseline, environmental, optimization). When implementing a `models/` module, this is the reference for the actual math, the v0.1 minimum equation set per discipline (§15), and what to explicitly avoid early (§16). Note: its LaTeX is lightly mangled (markdown ate some `\frac`/`=` lines) — read for intent, not copy-paste.
- `2511.19468v1.pdf` — a reference orbital-data-center feasibility paper cited by the spec (arXiv:2511.19468). Excluded from git (see `.gitignore`); cite by ID.

This is not yet a git repo and has no packaging, tests, or tooling. When scaffolding, follow `SPEC.md` rather than inventing a different structure.

## What this package is

`spacedc-mdao`: an open-source Python package for **multidisciplinary design analysis and optimization (MDAO) of orbital compute infrastructure**, with comparable terrestrial data-center baselines. (The spec also floats `orbitdc` as the importable package name; the example code uses `import orbitdc as odc`.)

### The one principle that governs every model

**Optimize delivered useful compute-years, not nominal watts or nominal GPUs.** Every model exists to take installed/nominal capacity and degrade it through real constraints. The central artifact is the **delivered-compute waterfall**:

```
installed compute
→ thermally allowable compute
→ power-available compute
→ network-limited compute
→ reliability-adjusted compute
→ utilization-adjusted delivered compute
```

Equivalently (per `EQUATIONS.md` §1), `C_delivered = C_peak · f_power · f_thermal · f_network · f_availability · f_utilization · f_software` — each factor is a model that multiplies installed capacity down. And the same chain drives cost: useful compute → power → heat → radiator area → mass → launch cost → lifetime delivered compute. Power closure does **not** imply thermal closure; never silently assume all IT power can be rejected.

The package's job is **not** to prove space data centers are viable. It is to make the feasibility boundary visible — to report **binding constraints and sensitivity**, so a user can see *which* uncertain assumptions (launch $/kg, satellite $/W, solar W/kg, radiator kg/kW, utilization, communication intensity, failure rate, mission life) are doing the work. Be skeptical by default. Prefer diagnostics like "space does not close because radiator area exceeds packaging by 38%" over a single headline cost number.

## Architectural shape (from SPEC.md)

Three user levels, layered on shared models:
- **Beginner:** YAML scenarios, built-in assumptions, calculator notebooks, Pareto plots, "why did this design fail?" diagnostics.
- **Power-user:** Python API with swappable models, Monte Carlo, sensitivity, custom optimizers.
- **Advanced MDAO:** derivative-aware OpenMDAO components, coupled solves, constrained optimization, surrogates, high-fidelity plugin hooks.

Planned source layout (target; create as needed):
```
core/    units, schema, scenario, registry, assumptions
data/    catalogs: accelerators, launch, solar_arrays, batteries, radiators,
         antennas, optical_terminals, earth_datacenters, cost_indices
models/  compute, power, thermal, orbit, formation, rf, lasercom,
         reliability, cost, earth_baseline, environmental
mdao/    openmdao_components, drivers, constraints, objectives
optimize/ doe, pareto, uncertainty, sensitivity, surrogate
viz/     dashboard, pareto, sankey, thermal, orbit3d, constellation_graph,
         link_budget, cost_waterfall
examples/ notebooks/, scenarios/
cli.py
```

Two cross-cutting conventions that must hold across all models:
1. **Model tiers (Tier 0–4).** Default fidelity is **Tier 1** (engineering trade studies). Tier 0 (scalar calculators) is "too easy to misuse"; Tier 3 (high-fidelity external plugins) is too slow for broad sweeps. Each physical model should offer tiered implementations behind a common interface, with plugins optional, never mandatory.
2. **Assumption provenance.** Every default number must carry source, date, confidence, and a flag for empirical / vendor-stated / estimated / speculative. This feeds the assumption-provenance viz and is a first-class requirement, not a nicety. Do **not** bake in single magic numbers for sensitive inputs (especially launch $/kg) — treat them as scenario distributions (pessimistic / current / aggressive / speculative).

## Intended tech stack (do not substitute without reason)

- **OpenMDAO** is the MDAO backbone — do *not* hand-roll an optimizer framework.
- `pydantic` for validated input schemas; `pint` or Astropy units for units.
- `numpy` / `scipy` / `pandas` / `polars` for analysis.
- `gpkit` (optional) for convex/geometric-programming trade studies.
- `poliastro` / `astropy` for orbital mechanics (advanced mode; beginner mode uses orbit presets).
- `plotly` / `altair` / `pyvista` / `networkx` / `panel` for visualization.
- `SALib` (or equivalent) for sensitivity analysis.
- `pytest` with **regression tests against known examples** — the spec calls these out specifically; new physics/cost models should ship with a regression fixture.

## MVP scope — build this first, in this spirit

Terrestrial baseline (PUE/WUE/energy price/capex/utilization) + orbital scalar model (launch $/kg, satellite $/W, W/kg, life, failure rate, utilization) + solar/radiator/battery sizing + simple RF and optical link budgets + accelerator catalog (H100-like, TPU-like, generic ASIC) + Monte Carlo & tornado sensitivity + Pareto dashboard + assumption provenance.

**Explicitly out of MVP:** formation-flying dynamics, detailed radiation transport, full thermal FEM. The MVP wins by making first-order physics and economics impossible to hand-wave — not by depth in any one discipline.

Terrestrial baselines must use best-in-class hyperscale numbers (e.g. PUE ~1.08–1.10), never a strawman PUE 1.5 facility.

## Target user-facing API (the shape to build toward)

```python
import orbitdc as odc
space = odc.scenarios.load("orbital_1mw_inference.yaml")
earth = odc.scenarios.load("earth_hyperscale_baseline.yaml")
result = odc.compare(space, earth)
result.summary()
result.plot_cost_waterfall()
result.plot_delivered_compute_waterfall()
result.explain_binding_constraints()
```

## Commands

None yet — no build/test/lint tooling is configured. When you add packaging (`pyproject.toml`) and a test suite, document the real `pytest` / lint / install commands here, replacing this section.
