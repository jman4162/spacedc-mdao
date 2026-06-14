"""Command-line interface: ``orbitdc compare <space.yaml> <earth.yaml>``."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from orbitdc.compare import compare
from orbitdc.core.scenario import load_scenario
from orbitdc.optimize.sensitivity import tornado
from orbitdc.optimize.uncertainty import monte_carlo


def _compare(args: argparse.Namespace) -> int:
    space = load_scenario(args.space)
    earth = load_scenario(args.earth)
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

    space = load_scenario(args.space)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitdc", description=__doc__)
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = args.func
    result: int = func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
