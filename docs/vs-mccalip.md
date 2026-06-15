# Compared to the McCalip calculator and the Economist

The Economist (["Data centres in space: less crazy than you think"](https://www.economist.com/science-and-technology/2026/03/02/data-centres-in-space-less-crazy-than-you-think), 2 Mar 2026) cites Andrew McCalip's web calculator showing a 1 GW orbital data center at near-parity with Earth ($11–16.7bn vs $15.9bn) under optimistic assumptions, while this package reports space at ~19× Earth for the bundled text-inference design. The two are not in conflict. The difference is mostly the metric and the slider positions, not the physics. This page decomposes it with numbers from the model (`orbital_1mw_inference.yaml`, `orbital_mccalip_optimistic.yaml`, `earth_hyperscale_baseline.yaml`); regenerate them with `orbitdc compare`.

## Two different metrics

McCalip compares **total capex per nominal capacity** (GPUs excluded, capacity assumed ~98% usable = the daylight fraction). This package's headline is **LCOC = lifecycle cost / delivered PFLOP-days**, after the full degradation waterfall (the bundled space design delivers ~29% of nominal, Earth ~47%). The denominator difference alone moves the ratio by ~2×.

To compare like with like, the package exposes `capex_per_w_ex_gpu` (capex per watt of IT power, accelerators excluded) in the `compare` summary and `Evaluation.details`. McCalip's $16.7bn for 1 GW is $16.7/W on this basis.

## The capex-per-watt decomposition

| | Earth | Space, default | Space, McCalip-optimistic |
| --- | ---: | ---: | ---: |
| capex $/W IT (ex-GPU) | ~$12 | ~$524 | ~$212 |
| — launch | $0 | ~$236 | ~$11 |
| — satellite (solar+radiator+bus+comms) | n/a | ~$288 | ~$200 |
| facility | ~$12 | n/a | n/a |
| network factor | 1.00 | 0.75 | 1.00 |
| delivered fraction | 47% | 29% | 38% |
| LCOC $/PFLOP-day | ~$66 | ~$1,237 | ~$428 |
| LCOC vs Earth | 1× | 19× | 6× |

Three things stand out:

1. **Our Earth number matches McCalip's.** $12/W ex-GPU is ~$12bn for 1 GW, in line with his $15.9bn terrestrial estimate. The disagreement is entirely on the space side.
2. **We agree that Starship closes the launch gap.** Moving to the speculative $200/kg launch case drops launch from ~$236/W to ~$11/W — a ~20× reduction, consistent with the article.
3. **The unreproduced assumption is satellite cost.** Even with optimistic sliders, the satellite stays ~$200/W ex-GPU, against Starcloud's claimed "less than $5/W." That ~40× gap is dominated by the costed power system (the solar catalog is $50–60/W, and the array is oversized for eclipse recharge and degradation), plus comms and integration. The package does not reproduce a $5/W satellite from its component costs; whether Starcloud can is the open question.

## Why the optimistic case is still 6×, not parity

McCalip's calculator stops at capex per capacity. This package then divides by **delivered** compute, applying the waterfall McCalip omits: sustained-vs-peak software (0.55), reliability-adjusted availability (~0.82), and — for ground-dependent workloads — the optical-downlink weather availability (0.75). The McCalip-optimistic scenario removes the downlink penalty (crosslink-only operation, network factor 1.0) and still delivers only ~38% of nominal, so its LCOC is ~6× Earth even though its capex/W is down ~2.5× from the default.

## What this means

At equal inputs the two models agree: at McCalip's own pessimistic defaults ($500/kg, 37 W/kg, $22/W) his calculator gives $51bn, ~3× worse than Earth, which `tests/test_references.py::test_mccalip_orbital_is_several_times_costlier` reproduces from physics. The near-parity headline needs three things at once: a speculative launch price, a satellite cost roughly an order of magnitude below what the component catalog costs here, and a capex-per-capacity metric that does not charge for the delivered-compute waterfall. Each is defensible to argue; the package's job is to make all three visible rather than fold them into a single number.

Run it yourself:

```bash
orbitdc compare examples/scenarios/orbital_mccalip_optimistic.yaml examples/scenarios/earth_hyperscale_baseline.yaml
```
