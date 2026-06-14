# Quick start

`spacedc-mdao` uses [uv](https://docs.astral.sh/uv/). The base install is light;
capabilities live behind extras.

```bash
uv sync                                          # base (numpy/scipy/pydantic/pint/matplotlib)
uv sync --extra dev --extra mdao --extra viz     # development + optimization + dashboard
```

| Extra   | Pulls in                | Enables                                         |
| ------- | ----------------------- | ----------------------------------------------- |
| `mdao`  | openmdao, pymoo, SALib  | optimization, Pareto fronts, DOE, Sobol         |
| `viz`   | plotly, panel, networkx | interactive figures + dashboard                 |
| `orbit` | skyfield                | ground-station access windows (needs ephemeris) |
| `rf`    | opensatcom              | Tier-1 RF link-budget backend                   |
| `docs`  | mkdocs-material, mkdocstrings | this documentation site                    |

The distribution is `spacedc-mdao`; the import package is `orbitdc`.

## Compare a space design against an Earth baseline

```bash
uv run orbitdc compare \
  examples/scenarios/orbital_1mw_inference.yaml \
  examples/scenarios/earth_hyperscale_baseline.yaml --tornado
```

Or from Python:

```python
import orbitdc as odc

space = odc.load_scenario("examples/scenarios/orbital_1mw_inference.yaml")
earth = odc.load_scenario("examples/scenarios/earth_hyperscale_baseline.yaml")
result = odc.compare(space, earth)

print(result.summary())
print(result.explain_binding_constraints())
```

## Robustness across every Earth baseline

```bash
uv run orbitdc robust examples/scenarios/orbital_1mw_inference.yaml \
  examples/scenarios/earth_*.yaml
```

## Optimize (needs the `mdao` extra)

```bash
uv run orbitdc optimize examples/scenarios/orbital_1mw_inference.yaml \
  --pareto lcoc,kg_per_kw
```

See [User tiers](tiers.md) for the full progression from one-line compares to
custom catalogs and the interactive dashboard.
