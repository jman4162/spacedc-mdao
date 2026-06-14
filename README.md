# spacedc-mdao

A Python package for multidisciplinary design analysis and optimization (MDAO) of orbital compute infrastructure, with terrestrial data-center baselines for comparison.

The package optimizes **delivered useful compute**, not nominal watts or nominal GPUs. It takes installed capacity and degrades it through power, thermal, network, reliability, and utilization limits, then reports where a design fails and which assumptions decide the outcome. Its job is to make the feasibility boundary visible, not to argue that space wins.

See `SPEC.md` for the design contract and `background_information/EQUATIONS.md` for the governing equations.

## Status

Phase 1 (thin end-to-end slice). Implemented: scenario loading, the discipline models in the v0.1 minimum set (`background_information/EQUATIONS.md` §15), the delivered-compute waterfall, an Earth-vs-space comparison with binding-constraint diagnosis, Monte Carlo and tornado sensitivity, and static plots. OpenMDAO coupling, interactive dashboards, and high-fidelity plugins are deferred to later phases.

## Install

```bash
uv sync --extra rf --extra dev   # all extras
# or, minimal:
uv sync
```

The `rf` extra pulls in [`opensatcom`](https://github.com/jman4162/opensatcom) as the Tier-1 RF link-budget backend. Without it, `rf.py` uses an inline Friis/FSPL link budget.

## Use

```python
import orbitdc as odc

space = odc.load_scenario("examples/scenarios/orbital_1mw_inference.yaml")
earth = odc.load_scenario("examples/scenarios/earth_hyperscale_baseline.yaml")

result = odc.compare(space, earth)
print(result.summary())
print(result.explain_binding_constraints())
```

Or from the command line:

```bash
orbitdc compare examples/scenarios/orbital_1mw_inference.yaml examples/scenarios/earth_hyperscale_baseline.yaml
```

## Development

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy src
uv run pytest
```

All code must pass ruff, `ruff format`, and `mypy --strict` before commit. CI enforces this.

## License

MIT.
