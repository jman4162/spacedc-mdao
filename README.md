# spacedc-mdao

A Python package for multidisciplinary design analysis and optimization (MDAO) of orbital compute infrastructure, with terrestrial data-center baselines for comparison.

The package optimizes **delivered useful compute**, not nominal watts or nominal GPUs. It takes installed capacity and degrades it through power, thermal, network, reliability, and utilization limits, then reports where a design fails and which assumptions decide the outcome. Its job is to make the feasibility boundary visible, not to argue that space wins.

See `SPEC.md` for the design contract and `background_information/EQUATIONS.md` for the governing equations.

## Status

Phases 1 and 2 are complete. Implemented:

- **Core (Phase 1):** scenario loading, the discipline models in the v0.1 minimum set (`background_information/EQUATIONS.md` §15), the delivered-compute waterfall, an Earth-vs-space comparison with binding-constraint diagnosis and feasibility thresholds, Monte Carlo and tornado sensitivity, matplotlib plots, and a CLI.
- **Thermal radiator co-design (2A):** a `thermal/` module coupling chip power → junction temperature → coolant loop → radiator temperature → area → mass, with net radiator flux (emission minus absorbed solar/albedo/Earth-IR at end-of-life coatings), a bottleneck classifier, and validation anchors (ISS PVR/EATCS, Starcloud, NASA high-temp). The radiator temperature is bounded by the chip stack; closure is checked at end of life.
- **MDAO + optimization (2B):** OpenMDAO components wrap the evaluator (FD partials), `optimize_single` for constrained single-objective optimization, pymoo NSGA-II Pareto fronts, a scipy Latin-hypercube DOE, and SALib Sobol indices.
- **Interactive dashboard (2C):** plotly figures (delivered/cost/mass/power-sankey, tornado, Pareto, constellation graph, thermal panels) and a Panel app, plus an assumption-provenance table.
- **Fidelity (2D):** environmental CO₂e/water accounting, station-keeping Δv and propellant, beta-angle eclipse, an optional Skyfield ground-access seam, and five Earth baselines.
- **Credibility (3A):** all soft factors moved to provenance-tagged catalogs; Starcloud/ISS recovered from the model; orbit-dependent radiation (TID/SEU); RF margin and optical weather availability bind; launch-cost cases; input validation.
- **Real MDAO (3B):** mixed-integer architecture optimization (satellites, accelerators/sat, altitude); transient orbit thermal; a workload library (space-native vs Earth-dependent); uncertainty fan / orbit-timeline / link-budget-heatmap figures.
- **UX (3C):** CLI `provenance`/`doe`/`sobol`/`--version`, HTML/Markdown report export, `Evaluation.to_dict()`, and a beginner→advanced notebook ladder.

The package is skeptical by default. For the bundled 1 MW inference scenario, Earth wins on levelized cost: the orbital design is downlink-limited, its radiators are a multi-tonne burden (chip-limited temperature), and station-keeping plus replacement add up.

## Install

`spacedc-mdao` uses `uv`. The base install is light; capabilities live behind extras.

```bash
uv sync                                          # base (numpy/scipy/pydantic/pint/matplotlib)
uv sync --extra dev --extra mdao --extra viz     # development + optimization + dashboard
```

| Extra    | Pulls in                          | Enables                                            |
| -------- | --------------------------------- | -------------------------------------------------- |
| `mdao`   | openmdao, pymoo, SALib            | optimization, Pareto fronts, DOE, Sobol            |
| `viz`    | plotly, panel, networkx           | interactive figures + dashboard                    |
| `orbit`  | skyfield                          | ground-station access windows (needs ephemeris)    |
| `rf`     | [opensatcom](https://github.com/jman4162/opensatcom) | Tier-1 RF link-budget backend (else inline Friis/FSPL) |

## Use

```python
import orbitdc as odc

space = odc.load_scenario("examples/scenarios/orbital_1mw_inference.yaml")
earth = odc.load_scenario("examples/scenarios/earth_hyperscale_baseline.yaml")

result = odc.compare(space, earth)
print(result.summary())
print(result.explain_binding_constraints())
```

From the command line:

```bash
orbitdc compare  examples/scenarios/orbital_1mw_inference.yaml examples/scenarios/earth_hyperscale_baseline.yaml
orbitdc optimize examples/scenarios/orbital_1mw_inference.yaml --pareto lcoc,kg_per_kw      # needs [mdao]
```

Notebooks: `examples/notebooks/01_compare.ipynb` (Earth-vs-space) and `examples/notebooks/02_radiator_feasibility.ipynb` (how big and heavy the radiators must be). Dashboard: `uv run panel serve examples/dashboard_app.py --show` (needs `[viz]`).

## Development

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run pytest
```

All code must pass ruff, `ruff format`, and `mypy --strict` before commit. CI enforces this. Every default number in the catalogs carries provenance (source, date, confidence, kind); see `background_information/THEMRAL_RADIATOR_DEEPDIVE.md` for the thermal modeling background.

## License

MIT.
