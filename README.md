# spacedc-mdao

[![PyPI](https://img.shields.io/pypi/v/spacedc-mdao.svg)](https://pypi.org/project/spacedc-mdao/)
[![CI](https://github.com/jman4162/spacedc-mdao/actions/workflows/ci.yml/badge.svg)](https://github.com/jman4162/spacedc-mdao/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue)](https://jman4162.github.io/spacedc-mdao/)
[![Python](https://img.shields.io/pypi/pyversions/spacedc-mdao.svg)](https://pypi.org/project/spacedc-mdao/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A skeptical, provenance-driven feasibility engine for orbital data centers, with
terrestrial baselines for comparison. It optimizes **delivered useful compute**,
not nominal watts or nominal GPUs: it takes installed capacity, degrades it
through power, thermal, network, reliability, and utilization limits, then reports
which assumptions decide the outcome. The job is to make the feasibility boundary
visible, not to argue that space wins.

![Path to viability](https://raw.githubusercontent.com/jman4162/spacedc-mdao/main/docs/assets/img/viability_ladder.gif)

## What would have to be true

For the bundled 1 MW LLM-inference design against a hyperscale Earth baseline
(PUE 1.10), Earth costs **$66**/PFLOP-day and space costs **$5,389** — about
**82x** more. Only **6.6%** of installed compute is delivered; the binding
constraint is the network factor (0.17, downlink-limited). Stacking every
improvement, each at its aggressive-to-speculative bound, shows what each metric
buys:

| Lever (current -> target) | Cumulative LCOC | x Earth |
| --- | ---: | ---: |
| baseline | $5,389 | 82x |
| downlink throughput 200 Gbps -> unbounded | $1,237 | 19x |
| launch cost $1,500 -> $200/kg | $765 | 12x |
| production learning (unit cost) | $512 | 8x |
| solar 100 -> 200 W/kg | $506 | 8x |
| radiator 7 -> 2 kg/m^2 | $502 | 8x |
| utilization 0.85 -> 0.98 | $435 | 7x |
| failure rate 0.05 -> 0.01 /yr | $394 | **6x** |

Two ceilings no hardware fixes. The network factor is pinned at **0.75** by
optical-downlink weather availability, so more bandwidth cannot exceed it without
RF downlink, more ground stations, or a relay. And even with every lever maxed,
space lands at **~6x Earth** ($394 vs $66) and wins **0%** of 500 Monte-Carlo
draws — the residual is the launch, radiator, and bus mass Earth never carries.
The unlock is a space-native, near-zero-downlink workload, not a faster GPU.

These numbers are produced by the model, not typed in; regenerate them with
`python scripts/generate_readme_assets.py`.

## What the model shows

| | |
| --- | --- |
| ![Delivered waterfall](https://raw.githubusercontent.com/jman4162/spacedc-mdao/main/docs/assets/img/delivered_waterfall.png) | Installed peak compute degraded to delivered: the network-limited step is the cliff. |
| ![Tornado](https://raw.githubusercontent.com/jman4162/spacedc-mdao/main/docs/assets/img/tornado.png) | Which assumptions move levelized cost. Launch $/kg dominates the swept drivers. |
| ![Monte Carlo](https://raw.githubusercontent.com/jman4162/spacedc-mdao/main/docs/assets/img/monte_carlo.png) | LCOC distribution under input uncertainty; space beats Earth in 0% of draws. |

## Install

`spacedc-mdao` uses [uv](https://docs.astral.sh/uv/). The base install is light;
capabilities live behind extras.

```bash
pip install spacedc-mdao            # base
pip install "spacedc-mdao[mdao,viz]"  # optimization + figures
```

| Extra   | Pulls in                      | Enables                                  |
| ------- | ----------------------------- | ---------------------------------------- |
| `mdao`  | openmdao, pymoo, SALib        | optimization, Pareto fronts, DOE, Sobol  |
| `viz`   | plotly, panel, networkx, kaleido | interactive + exported figures        |
| `orbit` | skyfield                      | ground-station access (needs ephemeris)  |
| `rf`    | opensatcom                    | Tier-1 RF link-budget backend            |

The distribution is `spacedc-mdao`; the import package is `orbitdc`.

## Quick start

```python
import orbitdc as odc

space = odc.load_scenario("examples/scenarios/orbital_1mw_inference.yaml")
earth = odc.load_scenario("examples/scenarios/earth_hyperscale_baseline.yaml")

result = odc.compare(space, earth)
print(result.summary())
print(result.explain_binding_constraints())
```

```bash
orbitdc compare examples/scenarios/orbital_1mw_inference.yaml examples/scenarios/earth_hyperscale_baseline.yaml --tornado
orbitdc robust  examples/scenarios/orbital_1mw_inference.yaml examples/scenarios/earth_*.yaml
orbitdc optimize examples/scenarios/orbital_1mw_inference.yaml --pareto lcoc,kg_per_kw   # needs [mdao]
```

The [quick start](https://jman4162.github.io/spacedc-mdao/quickstart/) and
[user tiers](https://jman4162.github.io/spacedc-mdao/tiers/) pages go from a
one-line compare to custom catalogs and the dashboard.

## What's inside

Delivered compute is the product of the waterfall factors:

```
C_delivered = C_peak * f_software * f_power * f_thermal * f_network * f_availability * f_utilization
```

Each factor is a discipline model that multiplies installed capacity down: a
radiator co-design ladder (chip -> junction -> coolant -> radiator -> area ->
mass, closed at end of life), an optical/RF link budget, orbit and formation
dynamics, radiation-driven reliability, and a levelized-cost spine with a
Wright's-law learning curve. Every default number carries provenance (source,
date, confidence, kind). The [model architecture](https://jman4162.github.io/spacedc-mdao/architecture/)
and [governing equations](https://jman4162.github.io/spacedc-mdao/equations/)
pages have the details; v0.4.0 completes Phases 1-4 (see `CHANGELOG.md`).

## Documentation

Full docs: <https://jman4162.github.io/spacedc-mdao/> — quick start, user tiers,
model architecture, the governing equations, an API reference, and a generated
assumptions/provenance table. See `SPEC.md` for the design contract and
`background_information/EQUATIONS.md` for the equation map. The thermal modeling
background is in `background_information/THEMRAL_RADIATOR_DEEPDIVE.md`.

## Development

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run pytest
```

All code passes ruff, `ruff format`, and `mypy --strict` before commit; CI
enforces it. Regenerate the README figures with
`uv run --extra viz python scripts/generate_readme_assets.py`.

## License

MIT. See `LICENSE`.
