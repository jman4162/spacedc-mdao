# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status: Phase 1 done; Phase 2A (thermal) + 2B (MDAO) + 2C (dashboard) landed

The Phase 1 thin end-to-end slice is built and passing (ruff + mypy --strict + pytest). The package is `orbitdc` (importable) / `spacedc-mdao` (distribution), under `src/orbitdc/`. Implemented: `core/` (Assumption, schema, scenario loader, units, registry), provenance-tagged `data/` catalogs, the discipline models in `models/`, the delivered-compute waterfall + diagnostics + `compare()` spine, Monte Carlo and tornado in `optimize/`, matplotlib `viz/`, a CLI, and example scenarios + notebooks.

**Phase 2A — thermal radiator co-design (`src/orbitdc/thermal/`)** replaced the Tier-0 radiator with a radiator-in-the-loop module: net radiator flux (emission minus absorbed solar/albedo/Earth-IR, EOL coatings), the chip-to-radiator resistance stack that bounds the radiator temperature, a coolant loop whose pump power feeds back as a bus load, a mass build-up, and a bottleneck classifier (chip/coolant/transport/radiator/orientation-limited). It carries catalogs (`coatings`, `coolants`, `chip_stacks`, `radiator_panels`) and validation anchors (ISS PVR/EATCS, Starcloud, NASA high-temp). `compare()` now surfaces T_rad, junction temp, m²/kW, kg/kW, and the bottleneck. See `examples/notebooks/02_radiator_feasibility.ipynb`. No new dependencies. Authoritative source: `background_information/THEMRAL_RADIATOR_DEEPDIVE.md`.

**Phase 2B — MDAO + optimization (`src/orbitdc/mdao/`, `src/orbitdc/optimize/`, optional `[mdao]` extra)**: `OrbitDCComponent` wraps `evaluate_space` as an OpenMDAO `ExplicitComponent` (FD partials; `run_model` matches `evaluate_space` exactly); `optimize_single` does constrained gradient-free single-objective optimization (ScipyOptimizeDriver/COBYLA). Multi-objective Pareto is pymoo NSGA-II (`optimize/pareto.py`) called directly on the evaluator. `optimize/doe.py` is a scipy-QMC Latin-hypercube sweep; `optimize/sensitivity.py` adds SALib Sobol indices. Shared design-variable/objective spec in `optimize/design.py`. CLI: `orbitdc optimize <scenario> [--objective lcoc | --pareto lcoc,kg_per_kw]`. Note: the OpenMDAO Pareto driver class is `pymooDriver` (lowercase) with a thin API, so we use pymoo directly. `import orbitdc.mdao` requires the extra; the base package never imports it.

**Phase 2C — interactive dashboard (`src/orbitdc/viz/`, optional `[viz]` extra)**: plotly figure builders in `viz/plotly_figures.py` (delivered/cost/mass/power-sankey, tornado, pareto scatter/parcoords, constellation graph, and the thermal panels: area-vs-temperature, net-W/m² waterfall, chip-to-radiator ladder); `viz/provenance.py` enumerates every provenance-tagged catalog value into a table; `viz/dashboard.py` assembles a tabbed Panel app. Run: `uv run panel serve examples/dashboard_app.py --show`. The matplotlib `viz/plots.py` stays in the base install; plotly/panel/networkx are import-on-use.

Still deferred: 2D Skyfield orbit / opensatcom RF / environmental / multiple Earth baselines.

Key reference docs:

- `SPEC.md` — the design contract: package concept, model families, full target layout, and MVP scope.
- `background_information/EQUATIONS.md` — the equation map behind every model, in GitHub-rendered `$$` LaTeX. The v0.1 minimum equation set per discipline is §15; what to avoid early is §16. Each `models/` module cites its section. (Reference docs live in `background_information/`; the arXiv PDF and `AI_WRITING_SLOP_Guide.md` are gitignored and stay local.)
- `2511.19468v1.pdf` — reference orbital-data-center feasibility paper (arXiv:2511.19468). Excluded from git (see `.gitignore`); cite by ID.
- The approved Phase 1 plan: `~/.claude/plans/please-make-an-implementation-rustling-puddle.md`.

Note the layout differs slightly from the SPEC's aspirational tree: Phase 1 keeps power/thermal sizing inside the discipline models, sizes power/thermal to load (so the feasibility pressure surfaces as mass, cost, radiator-packaging ratio, and network throttling rather than an `f_power` < 1), and defers the `mdao/` and `formation/environmental` modules.

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

## Tech stack

Phase 1 (current) is deliberately dependency-light. The fuller stack below is the eventual target, phased in as fidelity grows. See the approved plan at `~/.claude/plans/please-make-an-implementation-rustling-puddle.md` for the Phase 1 scope and rationale.

Phase 1 (in use now):
- `pydantic` v2 for validated input schemas and the `Assumption` provenance type.
- `pint` for units **at the I/O boundary only**; model math runs on plain SI floats (documented in names/docstrings) to stay fast and mypy-clean.
- `numpy` / `scipy` for analysis; `pyyaml` for scenarios; `matplotlib` for the Phase 1 static plots (waterfall, cost waterfall, tornado).
- `pytest` with **golden-value regression tests** — every physics/cost model ships with a hand-checkable fixture. This is a hard requirement, not optional.
- Optional `[rf]` extra: **`opensatcom`** (John's MIT satcom library) as the Tier-1 RF link-budget backend; `rf.py` falls back to inline Friis/FSPL when it is not installed.

Deferred to later phases (do not pull in for Phase 1):
- **OpenMDAO** — the eventual MDAO backbone (Tier 2 coupled solves). Keep model functions pure/side-effect-free so they wrap cleanly as `ExplicitComponent`s later. Do *not* hand-roll an optimizer framework when this lands.
- `gpkit` (convex/GP trade studies, only where physics is cleanly monomial/posynomial); the interactive viz stack (`plotly` / `altair` / `pyvista` / `networkx` / `panel`); `SALib` for Sobol sensitivity; `pandas` / `polars`.
- Orbital-mechanics library: **`poliastro` is archived/unmaintained (since Oct 2023) — do not adopt it.** Phase 1 uses closed-form orbit math (period, circular velocity, cylindrical-shadow eclipse fraction). If a library is later needed, prefer the maintained fork **`hapsira`** or `astropy` + `sgp4`.

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

The project uses `uv` for environment and dependency management.

```bash
uv sync --extra dev --extra mdao   # create venv + install package with extras (add --extra rf as needed)
uv run ruff check .                # lint
uv run ruff format --check .       # formatting check (drop --check to apply)
uv run mypy src                    # type-check (strict)
uv run pytest                      # run the test suite
uv run pytest tests/test_orbit.py -k eclipse   # run a single test
uv run python -m orbitdc compare examples/scenarios/orbital_1mw_inference.yaml examples/scenarios/earth_hyperscale_baseline.yaml
uv run orbitdc optimize examples/scenarios/orbital_1mw_inference.yaml --pareto lcoc,kg_per_kw   # needs [mdao]
```

**Code-quality gate:** all code must pass `ruff check`, `ruff format`, and `mypy --strict` (configured over `src/`) before commit. CI (`.github/workflows/ci.yml`) enforces ruff + mypy + pytest; do not commit changes that break them.

## Writing style — avoid AI slop

These rules apply to everything we publish: README, docs, docstrings, code comments, commit/PR messages, `SPEC.md`/`EQUATIONS.md` prose, and any papers. They are distilled from Wikipedia's "Signs of AI writing" (<https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>). The goal is plain, specific, falsifiable technical writing.

Do not write:
- **Significance inflation / puffery:** "stands as a testament", "plays a pivotal/vital/crucial role", "marks a turning point", "evolving landscape", "rich tapestry", "groundbreaking", "renowned", "seamless", "robust" (as filler), "boasts" (meaning "has").
- **Trailing "-ing" significance clauses:** "…, highlighting its importance", "…, reflecting broader trends", "…, underscoring the need for…", "…, showcasing…". Delete them or state the concrete consequence.
- **Vague attribution / weasel sourcing:** "experts argue", "studies show", "it is widely regarded", "industry reports suggest". Cite a specific source (with a number or link) or drop the claim.
- **Boilerplate "Challenges / Future Outlook / Despite its … faces several challenges" sections.** State concrete limitations with numbers instead.
- **Negative-parallelism filler:** "not just X, but Y", "it's not merely X — it's Y". Compulsive rule-of-three triads. Elegant variation (call the same thing by the same name every time; don't swap synonyms for variety).
- **The AI-vocab cluster:** *additionally* (as a sentence-opener), *crucial, delve, leverage, underscore, intricate, testament, tapestry, foster, meticulous, comprehensive, pivotal, vibrant, garner, bolster*.

Formatting:
- Sentence-case headings, not Title Case. Use boldface sparingly. Straight quotes, no decorative em-dash runs, no emoji. Standard Markdown only.
- Plain "X is Y" copula sentences are good — don't contort to avoid "is"/"are".

Default to concrete, specific statements with numbers and a source. When a number is uncertain, say so and tag it (the `Assumption` provenance type — source, date, confidence, kind — is the structural antidote to slop; see below). When you don't know, say so plainly rather than generating confident filler.
