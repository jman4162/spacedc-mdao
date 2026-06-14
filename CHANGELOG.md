# Changelog

All notable changes to `spacedc-mdao`. The package optimizes delivered useful
compute and reports the feasibility boundary; it is skeptical by default.

## Unreleased — Phase 4 (in progress)

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
