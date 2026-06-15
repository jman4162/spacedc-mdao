# Model architecture

The package is a `src/`-layout Python package (`orbitdc`) organized around one
spine: a scenario is loaded, run through the discipline models, collapsed into
the delivered-compute waterfall, and compared against an Earth baseline with
binding-constraint diagnosis.

## The governing waterfall

Installed peak capacity is degraded by independent factors, each produced by a
discipline model:

```
C_delivered = C_peak · f_software · f_power · f_thermal · f_network · f_availability · f_utilization
```

A factor below 1 means that discipline is throwing away compute. The binding
constraint is the factor that fails first; the package reports it rather than
hiding it inside a single headline number.

## Package layout

| Module | Responsibility |
| --- | --- |
| `core/` | `Assumption` provenance, the pydantic `Scenario` schema, scenario/catalog loaders, the unit registry |
| `data/` | provenance-tagged YAML catalogs (accelerators, launch, solar, batteries, radiators, coatings, coolants, chip stacks, cost/mass structure, radiation, comms, workloads) |
| `models/` | discipline models: compute, power, thermal entry, orbit (+ Skyfield), radiation, RF, lasercom, comms link, network, mass, cost, reliability, environmental, formation, Earth baseline |
| `thermal/` | the radiator co-design ladder: surfaces, radiation balance, transport network, coolant loop, co-design solve, bottleneck diagnosis, transient orbit, view factors (L4), degradation (L5) |
| `optimize/` | shared design-variable/objective spec, DOE, Pareto, sensitivity (tornado + Sobol), uncertainty, robustness |
| `mdao/` | OpenMDAO problem wrapping the evaluator |
| `viz/` | matplotlib + plotly figures, the Panel dashboard, the provenance table |
| top level | `compare`, `evaluate_space`/`evaluate_earth`, the waterfall, diagnostics, reporting, calibration, the CLI |

## Thermal radiator co-design

Thermal is the most detailed discipline because it is usually where optimistic
space-data-center arguments get sloppy. The chain couples chip power → junction
temperature → coolant loop → radiator temperature → required area → mass, with
net radiator flux (emission minus absorbed solar/albedo/Earth-IR at end-of-life
coatings) and a bottleneck classifier (chip-, HBM-, coolant-, transport-,
radiator-, or orientation-limited). The radiator temperature is bounded by the
tighter of the junction and HBM limits; closure is checked at end of life.

## Provenance

Every default number is an `Assumption` with a value, units, source, date,
confidence, and kind. `viz.provenance.collect_provenance()` walks the catalogs
and surfaces them; the [Assumptions & provenance](provenance.md) page is
generated from it. This is what makes the analysis reproducible rather than
arbitrary: every assumption is visible and challengeable.

## Limitations

The package is first-order by design. Two limits shape how to read the network
result:

- **Communication intensity (bits/FLOP) dominates and is low confidence.** It
  spans orders of magnitude by workload, so it is derived per workload (text
  inference ~1e-8 from token size / model FLOPs; rich-output ~2e-6) and exposed
  as the top sensitivity driver, not a single hidden scalar.
- **Downlink is a scalar service rate.** `downlink_gbps` times an optical
  availability factor is a bound, not an end-to-end time-averaged rate derived
  from terminal count, contact windows, ground-station diversity, weather,
  buffering, and ground-network egress. The 0.75 default availability is a
  single-site weather estimate that site diversity raises. See
  `background_information/EQUATIONS.md` section 9.
