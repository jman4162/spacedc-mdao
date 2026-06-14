# Changelog

All notable changes to `spacedc-mdao`. The package optimizes delivered useful
compute and reports the feasibility boundary; it is skeptical by default.

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
