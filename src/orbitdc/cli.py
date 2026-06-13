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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = args.func
    result: int = func(args)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
