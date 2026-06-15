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

Against a hyperscale Earth baseline (PUE 1.10) at **$66**/PFLOP-day, the result
depends entirely on what the workload ships to Earth, which sets the
communication intensity (bits moved per FLOP):

- **Text inference** (compact token output, derived ~1e-8 bits/FLOP): the network
  un-binds. Space is **$1,237**/PFLOP-day, **~19x** Earth, delivering 29% of
  installed compute. The binding limit is the **0.75 optical-downlink weather
  availability** (single-site, mitigable by site diversity) plus launch and
  radiator capex, not downlink bandwidth.
- **Rich-output inference** (embeddings, multimodal, artifact return, ~2e-6
  bits/FLOP): the downlink bandwidth binds. Space is **$5,389**, **~82x** Earth,
  delivering 6.6%.

Communication intensity is the single most decisive assumption (see the tornado
below). Stacking every other improvement on the text-inference design, each at
its aggressive-to-speculative bound:

| Lever (current -> target) | Cumulative LCOC | x Earth |
| --- | ---: | ---: |
| baseline (text inference) | $1,237 | 19x |
| optical availability 0.75 -> 0.95 (site diversity) | $977 | 15x |
| launch cost $1,500 -> $200/kg | $604 | 9x |
| production learning (unit cost) | $404 | 6x |
| solar 100 -> 200 W/kg | $400 | 6x |
| radiator 7 -> 2 kg/m^2 | $396 | 6x |
| utilization 0.85 -> 0.98 | $344 | 5x |
| failure rate 0.05 -> 0.01 /yr | $311 | **5x** |

Even with every lever maxed, text inference lands at **~5x Earth** and wins **0%**
of 500 Monte-Carlo draws. The residual is the launch, radiator, and bus mass Earth
never carries. These numbers are produced by the model, not typed in; regenerate
with `python scripts/generate_readme_assets.py`.

### On the downlink claim

The 200 Gbps optical downlink in the scenario is a demonstrated LEO burst rate
(NASA/MIT Lincoln Laboratory TBIRD, 2023). The model treats `downlink_gbps` as a
scalar service rate times an availability factor, not an end-to-end time-averaged
rate derived from terminal count, contact windows, ground-station diversity,
weather, buffering, and ground-network egress. The 0.75 optical availability is a
single-site weather/contact estimate, not a universal cap. RF can add a
cloud-robust fallback and continuity, but it is not a drop-in replacement for a
bulk optical pipe (its own spectrum, antenna, power, and ground tradeoffs). See
the limitations note below.

## What the model shows

| | |
| --- | --- |
| ![Tornado](https://raw.githubusercontent.com/jman4162/spacedc-mdao/main/docs/assets/img/tornado.png) | Communication intensity dominates LCOC sensitivity by far — the dominant uncertainty, now an explicit driver. |
| ![Delivered waterfall](https://raw.githubusercontent.com/jman4162/spacedc-mdao/main/docs/assets/img/delivered_waterfall.png) | Installed peak compute degraded to delivered for the text-inference design. |
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

## Limitations

First-order by design; the results are only as good as the assumptions, which is
why every default is provenance-tagged and exposed as a sensitivity driver. Two
to keep in mind:

- **Workload I/O dominates.** Communication intensity (bits/FLOP) is the most
  decisive input and is low confidence. The catalog separates text inference
  (~1e-8, derived from token size / model FLOPs) from rich-output inference
  (~2e-6); pick the one that matches what you actually ship to Earth.
- **Downlink is a scalar service rate, not an end-to-end model.** `downlink_gbps`
  times an availability factor is not the same as a time-averaged operational
  rate from terminal count, contact windows, ground-station diversity, weather,
  buffering, and ground-network egress. Treat the network result as a bound, and
  the 0.75 optical availability as a single-site weather estimate.

## Compared to the McCalip calculator

The Economist (Mar 2026) cites Andrew McCalip's calculator showing a 1 GW orbital
data center at near-parity with Earth under optimistic assumptions. That is not in
conflict with this package's ~19x: McCalip compares capex per nominal capacity
(GPUs excluded), while the headline here is cost per *delivered* compute after the
waterfall. The package exposes `capex_per_w_ex_gpu` for an apples-to-apples
comparison — its Earth figure (~$12/W, ~$12bn/GW) matches McCalip's terrestrial
estimate, it agrees that Starship closes the launch gap, and it shows the
remaining difference is a satellite cost (~$200/W here vs Starcloud's claimed
$5/W) plus the delivered-compute metric. See
[vs the McCalip calculator](https://jman4162.github.io/spacedc-mdao/vs-mccalip/).

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
