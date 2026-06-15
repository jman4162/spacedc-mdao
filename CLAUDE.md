# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status: Phases 1–3 complete; Phase 4A landed

The Phase 1 thin end-to-end slice is built and passing (ruff + mypy --strict + pytest). The package is `orbitdc` (importable) / `spacedc-mdao` (distribution), under `src/orbitdc/`. Implemented: `core/` (Assumption, schema, scenario loader, units, registry), provenance-tagged `data/` catalogs, the discipline models in `models/`, the delivered-compute waterfall + diagnostics + `compare()` spine, Monte Carlo and tornado in `optimize/`, matplotlib `viz/`, a CLI, and example scenarios + notebooks.

**Phase 2A — thermal radiator co-design (`src/orbitdc/thermal/`)** replaced the Tier-0 radiator with a radiator-in-the-loop module: net radiator flux (emission minus absorbed solar/albedo/Earth-IR, EOL coatings), the chip-to-radiator resistance stack that bounds the radiator temperature, a coolant loop whose pump power feeds back as a bus load, a mass build-up, and a bottleneck classifier (chip/coolant/transport/radiator/orientation-limited). It carries catalogs (`coatings`, `coolants`, `chip_stacks`, `radiator_panels`) and validation anchors (ISS PVR/EATCS, Starcloud, NASA high-temp). `compare()` now surfaces T_rad, junction temp, m²/kW, kg/kW, and the bottleneck. See `examples/notebooks/02_radiator_feasibility.ipynb`. No new dependencies. Authoritative source: `background_information/THEMRAL_RADIATOR_DEEPDIVE.md`.

**Phase 2B — MDAO + optimization (`src/orbitdc/mdao/`, `src/orbitdc/optimize/`, optional `[mdao]` extra)**: `OrbitDCComponent` wraps `evaluate_space` as an OpenMDAO `ExplicitComponent` (FD partials; `run_model` matches `evaluate_space` exactly); `optimize_single` does constrained gradient-free single-objective optimization (ScipyOptimizeDriver/COBYLA). Multi-objective Pareto is pymoo NSGA-II (`optimize/pareto.py`) called directly on the evaluator. `optimize/doe.py` is a scipy-QMC Latin-hypercube sweep; `optimize/sensitivity.py` adds SALib Sobol indices. Shared design-variable/objective spec in `optimize/design.py`. CLI: `orbitdc optimize <scenario> [--objective lcoc | --pareto lcoc,kg_per_kw]`. Note: the OpenMDAO Pareto driver class is `pymooDriver` (lowercase) with a thin API, so we use pymoo directly. `import orbitdc.mdao` requires the extra; the base package never imports it.

**Phase 2C — interactive dashboard (`src/orbitdc/viz/`, optional `[viz]` extra)**: plotly figure builders in `viz/plotly_figures.py` (delivered/cost/mass/power-sankey, tornado, pareto scatter/parcoords, constellation graph, and the thermal panels: area-vs-temperature, net-W/m² waterfall, chip-to-radiator ladder); `viz/provenance.py` enumerates every provenance-tagged catalog value into a table; `viz/dashboard.py` assembles a tabbed Panel app. Run: `uv run panel serve examples/dashboard_app.py --show`. The matplotlib `viz/plots.py` stays in the base install; plotly/panel/networkx are import-on-use.

**Phase 2D — fidelity upgrades**: `models/environmental.py` (EQUATIONS §13 — operational/embodied/launch CO₂e and water, normalized per delivered PFLOP-day; wired into `compare()` and the summary, where space shows zero operational water and higher embodied/launch carbon per unit delivered while Earth carries grid carbon + water); station-keeping in `models/orbit.py` (coarse atmospheric density, drag Δv, rocket-equation propellant → launch mass) plus beta-angle eclipse via `sp.beta_deg`; the opensatcom Tier-1 RF backend wired behind a best-effort seam in `models/rf.py` (`fspl_db(..., backend=...)`, falls back to inline); optional Skyfield ground-access in `models/orbit_skyfield.py` (`[orbit]` extra; needs ephemeris, so local/plugin only, not in CI); and four more Earth baselines (`examples/scenarios/earth_*.yaml`: leased colo, renewable+storage, gas-backed, constrained-grid).

Phase 2 is complete. Extras: `[mdao]`, `[viz]`, `[orbit]`, `[rf]`. The base install stays numpy/scipy/pydantic/pint/pyyaml/matplotlib.

**Phase 3A — credibility & provenance.** Soft cost/mass/embodied factors moved out of `compare.py`/`environmental.py` into provenance-tagged catalogs (`data/cost_structure.yaml`, `mass_structure.yaml`, `embodied_factors.yaml`); the duplicated YAML loaders are unified in `core/catalog_loader.py` (note: write YAML numbers as plain decimals — `2000000.0`, not `2.0e6`, which PyYAML parses as a string). `tests/test_published_cases.py` recovers Starcloud's ~633 W/m² and the ISS PVR band from the model, not stored constants. `models/radiation.py` + `data/radiation_env.yaml` add an orbit-dependent TID/SEU failure-rate contribution (accelerators carry `tid_tolerance_krad`/`seu_susceptibility`/`ecc_mitigation`), added to the base `annual_failure_rate`. RF TT&C margin and optical-downlink weather availability (`data/comms.yaml`, `Architecture.downlink_type`) now bind in `compare()` — optical availability multiplies `f_network`. A `launch_case` selector (current/pessimistic/aggressive/speculative) pulls from the `launch.yaml` distribution. `evaluate_space` validates overrides (finite, non-negative) and applies a solar-array packaging budget (`Architecture.solar_area_m2_per_sat`) so `f_power` can drop below 1. **Phase 3B — real MDAO + transient thermal + missing viz.** `evaluate_space` accepts architecture overrides (`n_satellites`, `accelerators_per_satellite`, `altitude_km`, `radiator_t_rad_setpoint_k`); `optimize/design.py` adds `DISCRETE_VARS`; `optimize/pareto.py` `pareto_nsga2_mixed` runs pymoo mixed Integer/Real NSGA-II over the architecture. `thermal/transient.py` integrates panel temperature over the sunlit/eclipse cycle (behind `SpaceParams.thermal_fidelity="transient"`, which orbit-averages and relaxes the worst-case `f_thermal`); steady is the default. `data/workloads.yaml` + `Workload.workload_type` supply comm intensity (llm_inference/training/earth_observation/edge — the space-native vs Earth-dependent split; training is hopelessly comms-bound); `SpaceParams.duty_cycle_fraction` sizes power+thermal for a bursty average. New plotly figures: `cost_waterfall` (true waterfall), `monte_carlo_fan`, `orbit_timeline` (from `compare.scenario_transient`), `link_budget_heatmap`; `ComparisonResult.monte_carlo()` convenience; dashboard gained an Uncertainty tab (4 tabs).

**Phase 3C — UX, reporting, hygiene.** CLI gained `provenance`, `doe`, `sobol`, and `--version`, plus friendly scenario-load errors (`cli._load`). `Evaluation.to_dict()`/`to_json()`; `list_catalogs()` and `export_report` exported from the package root. `reporting.py` writes a shareable HTML (plotly figures + narrative) or Markdown report with git commit + timestamp + scenario. Added `py.typed`, `LICENSE`, `CHANGELOG.md`; version bumped to **0.3.0**; CI gained an editable-install loop guard (the flakiness was uv skipping the editable rebuild when the version was unchanged — `--reinstall-package spacedc-mdao` forces it). Notebook ladder: `00_quick_start`, `03_pareto_exploration`, `04_monte_carlo_uncertainty` (+ existing 01/02).

Phase 3 is complete. The package is a credible, provenance-driven, optimizable exploration environment. Extras: `[mdao]`, `[viz]`, `[orbit]`, `[rf]`.

**Phase 4A — credibility & validation.** The HBM limit is wired in: `thermal/network.max_radiator_temp_k` now uses the tighter of the junction and HBM limits, so the demo H100 is **HBM-limited** (radiator runs cooler at ~312 K, thermal mass up to ~18 kg/kW); `thermal/diagnosis` has an `hbm-limited` label. Crosslink bandwidth is **derived** from formation geometry via `models/comms_link.crosslink_capacity` (modem-capped, photon-limited at long range — reproduces Suncatcher's ~12.8 Tbps per aperture); `Architecture.formation_separation_m` drives it, the scalar `crosslink_gbps` is now an explicit override, and crosslink folds into the network factor. `tests/test_references.py` reproduces Suncatcher (crosslink, <$200/kg launch) and McCalip (orbital several× costlier) from the model. `calibrate.fit_parameter` (scipy least-squares → provenance-tagged `Assumption`) is the Tier-4 entry point. `logging` + `orbitdc --verbose` trace intermediate values.

**Phase 4B — breadth of trade studies.** `data/accelerators.yaml` now has five entries with cited specs, adding **AMD MI300X** (1300 dense FP16 TFLOPS, 750 W, 192 GB HBM3) and **Google TPU v5e** (197 bf16 TFLOPS, 16 GB); catalog variety added across launch (`current_heavy_lift` ~$1500/kg), batteries (`li_ion_high_energy` 250 Wh/kg), solar (`flexible_rosa` 150 W/kg), and radiators (`composite_deployable` 4 kg/m²). `models/cost.py` gained a Wright's-law learning curve (`learning_multiplier(quantity, rate)`, `unit_cost ∝ n^log2(rate)`) applied to accelerator and bus costs, plus a TRL premium (`trl_multiplier`); `data/cost_structure.yaml` carries `learning_rate` (default 1.0 = off) and `bus_trl` (default 9). `learning_rate` is an `evaluate_space` override and a tornado/Sobol driver. `optimize/robust.py`: `batch_compare(space, earths)` returns a verdict matrix (space LCOC is Earth-independent, so robustness reduces to beating the cheapest baseline), `robust_optimize` minimizes space LCOC and counts baselines beaten; CLI `orbitdc robust <space> <earth...>`.

**Phase 4C — deepen physics (all opt-in; defaults unchanged).** Five parametric-fidelity additions, each behind a flag so the default evaluation is identical. (1) **Formation dynamics** (`models/formation.py`): Clohessy-Wiltshire mean motion, differential-drag drift cancellation, and a collision-avoidance margin (separation / nav uncertainty) that triggers conjunction maneuvers; folds into station-keeping Δv, and `formation_separation_m` is now an override (so the 4A crosslink and 4C keeping/risk share one knob — tighter = more bandwidth, lower margin). (2) **Thermal Level 4** (`thermal/view_factors.py`): an effective view factor from articulation/self-view/solar-array blocking that derates emission, behind `SpaceParams.thermal_view_factors`. (3) **Thermal Level 5** (`thermal/degradation.py`): a mission-integrated coating trajectory + MMOD area loss + single-loop-out derate on `f_thermal`, behind `thermal_degradation`. (4) **Skyfield orbit** (`models/orbit_skyfield.py` wired into `evaluate_space`): ground-station access fraction (SGP4) refines optical-downlink availability behind `orbit_fidelity="skyfield"` + the `[orbit]` extra, with a logged graceful fallback to closed-form on any failure (a few-station optical architecture shows ~4% access → LCOC explodes, the honest result). (5) **Graceful degradation** (`reliability.fleet_health_curve`): a time-stepped fleet-capacity sawtooth with launch-quantized resupply, exposed as `Evaluation.availability_curve`, behind `graceful_degradation` (+ `resupply_interval_years`).

**Phase 4D — documentation site.** MkDocs Material under `docs/` (`mkdocs.yml`, new `[docs]` extra: mkdocs, mkdocs-material, mkdocstrings[python]). Pages: home, quick start, the three user tiers, model architecture, the governing equations (embedded from `background_information/EQUATIONS.md` via a pymdownx snippet), an mkdocstrings API reference, and an assumptions/provenance page **generated at build time** by the `docs/gen_provenance.py` MkDocs hook (writes `docs/provenance.md`, gitignored, from `collect_provenance()`). Build: `uv run --no-sync python -m mkdocs build --strict` (invoke via `python -m mkdocs`, not the bare `mkdocs` shim, or it resolves the global pyenv install). CI has a `docs` job (strict build) + a `deploy-docs` job (GitHub Pages on `main`); README links the site.

**Phase 4E — PyPI release.** Version bumped to **0.4.0** (pyproject + `__init__`). The wheel ships `py.typed` + the 15 data catalogs (`uv build` → `twine check` passes; a clean-venv install imports `orbitdc`, runs the CLI). `.github/workflows/release.yml` publishes on a `v*` tag via **PyPI Trusted Publishing** (OIDC, no stored token). **One-time admin the maintainer must do before the first tag:** (1) configure a Trusted Publisher on PyPI (owner `jman4162`, repo `spacedc-mdao`, workflow `release.yml`, environment `pypi`) — can be a "pending" publisher so the first publish creates the project; (2) create a GitHub Environment named `pypi`. Then bump the version, tag `vX.Y.Z`, and push the tag. **Phase 4 is complete.**

**Post-4E — downlink accuracy correction.** An external audit was right that the "82x, downlink-limited" headline hinged on `llm_inference` comm intensity = 2e-6 bits/FLOP, ~1,000-20,000x above a text derivation (32 bits/token / (2*N_params)). Recalibrated `llm_inference` to ~1e-8 (text; network un-binds to the 0.75 optical-weather ceiling, demo now ~19x) and added a `multimodal_inference` preset (~2e-6, downlink-bandwidth-bound, ~82x) + `examples/scenarios/orbital_multimodal_inference.yaml`. Fixed a latent bug where a scenario's workload `type` did not populate `workload_type` (so the catalog comm intensity was dead and the inline scalar did the work); `type` now seeds `workload_type` via a validator, and `comm_intensity_bits_per_flop` defaults to `None` ("use catalog") so `model_dump` round-trips don't bake in a masking default. `comm_intensity_bits_per_flop`, `downlink_gbps`, and `optical_downlink_availability` (new `evaluate_space` override) are now tornado/Sobol drivers — comm intensity dominates. README/EQUATIONS §9/docs carry the two regimes, the bits/FLOP derivation, the TBIRD 200 Gbps context, and the scalar-downlink limitation.

**Post-4E — McCalip/Economist reconciliation.** The Economist (Mar 2026) cites McCalip's calculator showing a 1 GW orbital DC at near-parity under optimistic sliders, vs our ~19x. The gap is methodology + slider positions, not physics. Added a capacity-capex metric (`Evaluation.capex_usd`, `details["capex_per_w_ex_gpu"]` = $/W of IT power ex-GPU, shown in the `compare` summary) — our Earth figure ~$12/W matches McCalip's terrestrial $15.9bn/GW. Made bus cost scenario-configurable (`SpaceParams.bus_cost_per_sat_usd` + override; was a fixed constant). `examples/scenarios/orbital_mccalip_optimistic.yaml` (speculative launch, flexible_rosa 150 W/kg, composite_deployable radiator, low bus cost, crosslink-only `downlink_type: rf`) cuts capex/W ~2.5x and LCOC to ~6x: launch closes via Starship ($236->$11/W), but the satellite stays ~$200/W vs Starcloud's claimed $5/W (our solar is $50-60/W catalog), and the delivered-compute waterfall keeps LCOC above parity. Docs: `docs/vs-mccalip.md` decomposes the gap; `tests/test_mccalip_comparison.py`.

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

The package's job is **not** to prove space data centers are viable. It is to make the feasibility boundary visible — to report **binding constraints and sensitivity**, so a user can see *which* uncertain assumptions (launch $/kg, satellite $/W, solar W/kg, radiator kg/kW, utilization, communication intensity, failure rate, mission life) are doing the work. Prefer diagnostics like "space does not close because radiator area exceeds packaging by 38%" over a single headline cost number.

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

Terrestrial baseline (PUE/WUE/energy price/capex/utilization) + orbital scalar model (launch $/kg, satellite $/W, W/kg, life, failure rate, utilization) + solar/radiator/battery sizing + simple RF and optical link budgets + accelerator catalog (H100, AMD MI300X, Google TPU v5e, TPU-like, generic ASIC) + Monte Carlo & tornado sensitivity + Pareto dashboard + assumption provenance.

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
uv run orbitdc robust examples/scenarios/orbital_1mw_inference.yaml examples/scenarios/earth_*.yaml   # space vs every Earth baseline
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
