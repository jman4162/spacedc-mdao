"""Command-line interface: ``orbitdc compare <space.yaml> <earth.yaml>``."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from pydantic import ValidationError

from orbitdc import __version__
from orbitdc.compare import compare
from orbitdc.core.scenario import load_scenario
from orbitdc.core.schema import Scenario
from orbitdc.optimize.sensitivity import tornado
from orbitdc.optimize.uncertainty import monte_carlo


def _load(path: str) -> Scenario:
    """Load a scenario with a friendly error instead of a raw ValidationError."""
    try:
        return load_scenario(path)
    except FileNotFoundError:
        raise SystemExit(f"error: scenario file not found: {path}") from None
    except ValidationError as exc:
        n = len(exc.errors())
        lines = "\n".join(
            f"  - {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise SystemExit(f"error: invalid scenario {path} ({n} problem(s)):\n{lines}") from None


def _compare(args: argparse.Namespace) -> int:
    space = _load(args.space)
    earth = _load(args.earth)
    result = compare(space, earth)

    print(result.summary())
    print()
    print(result.explain_binding_constraints())

    if args.tornado:
        print()
        print("Tornado (LCOC swing, largest first):")
        for e in tornado(space):
            span = f"{e.lcoc_low:>13,.0f} -> {e.lcoc_high:<13,.0f}"
            print(f"  {e.driver:<30} {span} swing {e.swing:,.0f}")

    if args.monte_carlo:
        print()
        mc = monte_carlo(space, result.earth.lcoc_per_pflop_day, n=args.monte_carlo, seed=args.seed)
        print(
            f"Monte Carlo (n={mc.n}): P(space beats Earth) = {mc.p_space_wins:.1%}; "
            f"LCOC p10/p50/p90 = {mc.lcoc_p10:,.0f} / {mc.lcoc_p50:,.0f} / {mc.lcoc_p90:,.0f}"
        )
    return 0


def _optimize(args: argparse.Namespace) -> int:
    # Lazy imports: optimization needs the `mdao` extra.
    from orbitdc.mdao import optimize_single
    from orbitdc.optimize.pareto import pareto_nsga2

    space = _load(args.space)
    design_vars = [v.strip() for v in args.design_vars.split(",")] if args.design_vars else None

    if args.pareto:
        objectives = [o.strip() for o in args.pareto.split(",")]
        pf = pareto_nsga2(space, objectives, design_vars, pop_size=args.pop, n_gen=args.gen)
        print(f"Pareto front ({pf.n_points} points) over {objectives}:")
        for row_x, row_f in zip(pf.x, pf.f, strict=True):
            objs = ", ".join(f"{o}={v:,.2f}" for o, v in zip(objectives, row_f, strict=True))
            dvs = ", ".join(f"{n}={x:,.3g}" for n, x in zip(pf.design_vars, row_x, strict=True))
            print(f"  [{objs}]  @  {dvs}")
        return 0

    dv = design_vars or [
        "utilization",
        "downlink_gbps",
        "launch_cost_per_kg",
        "radiator_areal_mass",
    ]
    cons: list[tuple[str, float | None, float | None]] = [("radiator_packaging_ratio", None, 1.0)]
    res = optimize_single(space, args.objective, dv, constraints=cons, maxiter=args.maxiter)
    print(f"Optimized {args.objective} = {res[args.objective]:,.2f}")
    print("Design variables:")
    for name in dv:
        print(f"  {name:<24} {res[name]:,.4g}")
    return 0


def _robust(args: argparse.Namespace) -> int:
    from orbitdc.optimize.robust import batch_compare, format_batch

    space = _load(args.space)
    earths = [_load(p) for p in args.earths]
    print(format_batch(batch_compare(space, earths)))
    return 0


def _provenance(args: argparse.Namespace) -> int:
    from orbitdc.viz.provenance import collect_provenance

    rows = collect_provenance()
    print(f"{'catalog':<18}{'entry':<26}{'field':<28}{'value':>14}  conf  kind")
    for r in sorted(rows, key=lambda x: (x["catalog"], x["entry"], x["field"])):
        print(
            f"{r['catalog']:<18}{r['entry']:<26}{r['field']:<28}"
            f"{r['value']:>14,.4g}  {r['confidence']:<5} {r['kind']}"
        )
    print(f"\n{len(rows)} provenance-tagged values.")
    return 0


def _doe(args: argparse.Namespace) -> int:
    import numpy as np

    from orbitdc.optimize.doe import latin_hypercube_doe

    space = _load(args.space)
    metrics = [m.strip() for m in args.metrics.split(",")]
    doe = latin_hypercube_doe(space, metrics, n=args.n, seed=args.seed)
    print(f"DOE ({doe.values.shape[0]} samples) over {doe.design_vars}:")
    for j, m in enumerate(metrics):
        col = doe.values[:, j]
        med = float(np.median(col))
        print(f"  {m:<20} min={col.min():,.2f}  median={med:,.2f}  max={col.max():,.2f}")
    return 0


def _sobol(args: argparse.Namespace) -> int:
    from orbitdc.optimize.sensitivity import sobol_indices

    space = _load(args.space)
    sob = sobol_indices(space, args.objective, n=args.n, seed=args.seed)
    print(f"Sobol indices for {args.objective} (total-order, largest first):")
    for name in sorted(sob.st, key=lambda k: sob.st[k], reverse=True):
        print(f"  {name:<30} ST={sob.st[name]:.3f}  S1={sob.s1[name]:.3f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitdc", description=__doc__)
    parser.add_argument("--version", action="version", version=f"orbitdc {__version__}")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="log intermediate values (DEBUG)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cmp_p = sub.add_parser("compare", help="compare a space scenario against an earth baseline")
    cmp_p.add_argument("space", help="path to the space scenario YAML")
    cmp_p.add_argument("earth", help="path to the earth scenario YAML")
    cmp_p.add_argument("--tornado", action="store_true", help="also print a tornado sensitivity")
    cmp_p.add_argument(
        "--monte-carlo", type=int, default=0, metavar="N", help="run N Monte Carlo draws"
    )
    cmp_p.add_argument("--seed", type=int, default=0, help="Monte Carlo seed")
    cmp_p.set_defaults(func=_compare)

    opt_p = sub.add_parser("optimize", help="optimize a space scenario (needs the mdao extra)")
    opt_p.add_argument("space", help="path to the space scenario YAML")
    opt_p.add_argument("--objective", default="lcoc", help="objective to minimize/maximize")
    opt_p.add_argument(
        "--pareto", default="", help="comma-separated objectives for an NSGA-II front"
    )
    opt_p.add_argument("--design-vars", default="", help="comma-separated design variables")
    opt_p.add_argument("--maxiter", type=int, default=60, help="single-objective iterations")
    opt_p.add_argument("--pop", type=int, default=24, help="NSGA-II population size")
    opt_p.add_argument("--gen", type=int, default=15, help="NSGA-II generations")
    opt_p.set_defaults(func=_optimize)

    rob_p = sub.add_parser("robust", help="compare one space design against many earth baselines")
    rob_p.add_argument("space", help="path to the space scenario YAML")
    rob_p.add_argument("earths", nargs="+", help="paths to earth baseline scenario YAMLs")
    rob_p.set_defaults(func=_robust)

    prov_p = sub.add_parser("provenance", help="dump every provenance-tagged catalog value")
    prov_p.set_defaults(func=_provenance)

    doe_p = sub.add_parser("doe", help="Latin-hypercube design-of-experiments (needs mdao extra)")
    doe_p.add_argument("space", help="path to the space scenario YAML")
    doe_p.add_argument("--metrics", default="lcoc,kg_per_kw", help="comma-separated metrics")
    doe_p.add_argument("--n", type=int, default=32, help="number of samples")
    doe_p.add_argument("--seed", type=int, default=0)
    doe_p.set_defaults(func=_doe)

    sob_p = sub.add_parser("sobol", help="Sobol global sensitivity (needs mdao extra)")
    sob_p.add_argument("space", help="path to the space scenario YAML")
    sob_p.add_argument("--objective", default="lcoc", help="objective to analyze")
    sob_p.add_argument("--n", type=int, default=64, help="base sample size")
    sob_p.add_argument("--seed", type=int, default=0)
    sob_p.set_defaults(func=_sobol)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    import logging

    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "verbose", False):
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")
    func = args.func
    result: int = func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
