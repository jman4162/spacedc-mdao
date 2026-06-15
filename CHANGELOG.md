# Changelog

All notable changes to `spacedc-mdao`. The package optimizes delivered useful
compute and reports the feasibility boundary; it is skeptical by default.

## Unreleased

### McCalip / Economist reconciliation
- Added a capacity-capex metric for an apples-to-apples comparison with the
  McCalip calculator (cited by the Economist, Mar 2026): `Evaluation.capex_usd`
  and `details["capex_per_w_ex_gpu"]` ($/W of IT power, accelerators excluded),
  shown in the `compare` summary. Our Earth figure (~$12/W) matches McCalip's
  terrestrial estimate.
- Made satellite bus cost scenario-configurable (`SpaceParams.bus_cost_per_sat_usd`
  + `evaluate_space` override; was a fixed catalog constant).
- Added `examples/scenarios/orbital_mccalip_optimistic.yaml` (speculative launch,
  150 W/kg solar, composite radiator, low bus cost, crosslink-only). It cuts
  capex/W ~2.5x and LCOC to ~6x Earth — launch closes (Starship), but the
  satellite stays ~$200/W vs Starcloud's claimed $5/W, and the waterfall keeps
  LCOC above parity.
- New docs page `vs-mccalip.md` decomposing the gap line by line, and a README
  pointer. `tests/test_mccalip_comparison.py`.

### Downlink-claim accuracy correction
- Recalibrated `llm_inference` communication intensity to a text-derived ~1e-8
  bits/FLOP (32 bits/token / (2*N_params)); the prior 2e-6 was ~1,000-20,000x too
  high for compact text output and silently set the "downlink-limited" headline.
  Added a `multimodal_inference` workload (~2e-6) for the rich-output regime where
  downlink bandwidth genuinely binds, plus `examples/scenarios/orbital_multimodal_inference.yaml`.
  The text-inference demo is now ~19x Earth (optical-weather/capex-limited), not
  82x; the multimodal demo is ~82x (downlink-bandwidth-limited).
- Fixed a latent bug: a scenario's workload `type` now populates `workload_type`
  (so the catalog comm intensity is actually used), and `comm_intensity_bits_per_flop`
  defaults to `None` ("use catalog") so a `model_dump` round-trip no longer bakes
  in a default that masks the catalog.
- Surfaced the decisive assumptions as sensitivity drivers: `comm_intensity_bits_per_flop`,
  `downlink_gbps`, and `optical_downlink_availability` (now an `evaluate_space`
  override) are in the tornado and Sobol drivers; comm intensity dominates.
- README, EQUATIONS section 9, and a docs limitations note: two workload regimes,
  the bits/FLOP derivation, TBIRD (2023) 200 Gbps context, 0.75 as a single-site
  weather/contact estimate, and the scalar-downlink limitation.

## 0.4.0 — Phase 4

Credibility & validation, breadth, deepened physics (all opt-in), a docs site,
and the first PyPI release. Reserve 1.0.0 for an API-stability commitment.

### 4E — PyPI release
- Version 0.4.0; clean-venv install from the built wheel imports `orbitdc`, ships
  `py.typed` + the data catalogs, and runs the CLI. `twine check` passes.
- `release.yml`: publish-on-tag via PyPI Trusted Publishing (OIDC, no token).

### 4A — credibility & validation
- HBM thermal limit wired into the radiator-temperature ceiling and bottleneck
  diagnosis (`hbm-limited`); the demo H100 is HBM-limited.
- Crosslink bandwidth derived from formation geometry + an optical link budget
  (`models/comms_link.py`); `crosslink_gbps` is now an explicit override.
- Reproduce Google Suncatcher and McCalip references from the model
  (`tests/test_references.py`); `calibrate.fit_parameter` Tier-4 harness.
- `logging` + `orbitdc --verbose`.

### 4B — breadth of trade studies
- Real accelerators with cited specs: AMD MI300X and Google TPU v5e (now five
  catalog entries); added catalog variety (current heavy-lift launch,
  high-energy battery, flexible/ROSA solar, composite-deployable radiator).
- Cost learning curves (Wright's law, `learning_multiplier`) and a TRL premium
  (`trl_multiplier`) in `models/cost.py`; `learning_rate`/`bus_trl` in
  `data/cost_structure.yaml`. `learning_rate` is a sensitivity/Sobol driver.
- Multi-scenario robustness (`optimize/robust.py`): `batch_compare` matrices one
  space design against every Earth baseline; `robust_optimize` minimizes space
  LCOC and reports baselines beaten. CLI `orbitdc robust <space> <earth...>`.

### 4C — deepen physics (all opt-in; defaults unchanged)
- Formation dynamics (`models/formation.py`): Clohessy-Wiltshire mean motion,
  differential-drag drift cancellation, and a collision-avoidance margin
  (separation / nav uncertainty) that drives conjunction maneuvers. Folds into
  station-keeping; `formation_separation_m` is an override.
- Thermal Level 4 (`thermal/view_factors.py`): parametric effective view factor
  from articulation, self-view, and solar-array blocking; behind
  `thermal_view_factors`.
- Thermal Level 5 (`thermal/degradation.py`): mission-integrated coating
  trajectory + MMOD area loss + single-loop-out derate on f_thermal; behind
  `thermal_degradation`.
- Skyfield orbit fidelity: ground-station access fraction (SGP4) refines optical
  downlink availability behind `orbit_fidelity="skyfield"` + the `orbit` extra,
  with a logged graceful fallback to closed-form.
- Graceful degradation (`reliability.fleet_health_curve`): a time-stepped fleet
  capacity curve with launch-quantized resupply (sawtooth), exposed as
  `Evaluation.availability_curve`; behind `graceful_degradation`.

### 4D — documentation site
- MkDocs Material site (`docs/`, `mkdocs.yml`, `[docs]` extra): quick start, user
  tiers, model architecture, embedded governing equations, an mkdocstrings API
  reference, and an assumptions/provenance page generated from the catalogs at
  build time. CI builds with `--strict` and deploys to GitHub Pages on `main`.
- `pyproject` metadata for release: classifiers, `[project.urls]`.

## 0.3.0 — Phase 3

### 3A — credibility & provenance
- Moved soft cost/mass/embodied factors into provenance-tagged catalogs
  (`cost_structure`, `mass_structure`, `embodied_factors`); unified the YAML
  loaders in `core/catalog_loader.py`.
- `tests/test_published_cases.py` recovers Starcloud ~633 W/m² and the ISS PVR
  band from the model, not stored constants.
- Orbit-dependent radiation (`models/radiation.py`, TID/SEU) feeds the failure rate.
- RF TT&C margin and optical-downlink weather availability now bind in `compare()`.
- `launch_case` selector pulls from the launch-cost distribution.
- Override validation and a solar-array packaging budget (`f_power` can drop below 1).

### 3B — real MDAO + transient thermal + visualization
- Mixed-integer architecture optimization (`pareto_nsga2_mixed`): n_satellites,
  accelerators/sat, altitude, radiator setpoint.
- Transient orbit thermal (`thermal/transient.py`), behind `thermal_fidelity`.
- Workload library (space-native vs Earth-dependent) and a duty cycle.
- New figures: cost waterfall, Monte Carlo fan, orbit timeline, link-budget heatmap;
  `ComparisonResult.monte_carlo()`; dashboard Uncertainty tab.

### 3C — UX, reporting, hygiene
- CLI `doe` / `sobol` / `provenance` / `--version`; friendly scenario-load errors.
- `evaluate` exported; `list_scenarios()` / `list_catalogs()`; `Evaluation.to_dict()`.
- HTML/Markdown report export (`reporting.export_report`).
- `py.typed`, `LICENSE`, this changelog; beginner→advanced notebook ladder.

## 0.2.0 — Phase 2
- Thermal radiator co-design module (`thermal/`).
- OpenMDAO + pymoo optimization, scipy DOE, SALib Sobol (`mdao/`, `optimize/`).
- Interactive plotly + Panel dashboard (`viz/`).
- Environmental CO₂e/water, station-keeping Δv, RF/orbit fidelity, five Earth baselines.

## 0.1.0 — Phase 1
- Discipline models, the delivered-compute waterfall, `compare()` with
  binding-constraint diagnosis and feasibility thresholds, Monte Carlo and
  tornado, matplotlib plots, a CLI, and provenance-tagged catalogs.
