# User tiers

The package is built to be useful at three depths. Each tier reuses the same
evaluator and provenance-tagged catalogs, so results are comparable across them.

## Tier 1 — compare and diagnose

Run a scenario against an Earth baseline and read the binding constraints. No
optional extras are required.

```bash
uv run orbitdc compare space.yaml earth.yaml --tornado --monte-carlo 500
```

You get the delivered-compute waterfall, the levelized cost of compute (LCOC),
the binding constraint (what fails first), the feasibility thresholds (what would
have to change for space to match Earth), and a tornado / Monte-Carlo view of
which assumptions move the answer. Start in
`examples/notebooks/00_quick_start.ipynb` and `01_compare.ipynb`.

## Tier 2 — optimize and explore sensitivity

With the `mdao` extra, search the design space rather than evaluating one point.

```bash
uv run orbitdc optimize space.yaml --objective lcoc
uv run orbitdc optimize space.yaml --pareto lcoc,kg_per_kw
uv run orbitdc sobol space.yaml --objective lcoc
uv run orbitdc doe space.yaml --metrics lcoc,kg_per_kw
uv run orbitdc robust space.yaml earth_*.yaml
```

Single-objective optimization (gradient-free), NSGA-II Pareto fronts including
mixed-integer architecture (satellites, accelerators/sat, altitude), a
Latin-hypercube DOE, and SALib Sobol indices. See `03_pareto_exploration.ipynb`
and `04_monte_carlo_uncertainty.ipynb`.

## Tier 3 — extend, deepen, and visualize

- **Custom catalogs.** Add an accelerator, launch vehicle, coating, or coolant
  as a provenance-tagged YAML entry; it flows through every model and the
  provenance table.
- **Higher fidelity (Phase 4C, opt-in).** Formation-keeping Δv and a collision
  margin, parametric radiator view factors (Level 4), mission-integrated
  degradation (Level 5), Skyfield ground-station access (`orbit` extra), and a
  time-stepped graceful-degradation availability curve.
- **Dashboard.** With the `viz` extra, an interactive Panel app:

  ```bash
  uv run panel serve examples/dashboard_app.py --show
  ```

The [model architecture](architecture.md) page shows how these couple.
