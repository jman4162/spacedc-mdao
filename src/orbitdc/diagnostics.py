"""Binding-constraint diagnosis and feasibility-threshold solving.

The package's most useful output is not a single cost number but a statement of
what limits the design and which assumptions decide it. These helpers read an
`Evaluation` and locate the binding factor, and solve for the parameter values
at which space would match Earth.
"""

from __future__ import annotations

from collections.abc import Callable

from orbitdc.evaluation import Evaluation
from orbitdc.waterfall import FACTOR_LABELS

# Search ranges and direction for each driver. `better` is the direction that
# helps space (lowers its LCOC).
DRIVER_RANGES: dict[str, tuple[float, float, str]] = {
    "launch_cost_per_kg_usd": (50.0, 20000.0, "lower"),
    "solar_specific_power_w_per_kg": (10.0, 400.0, "higher"),
    "radiator_areal_mass_kg_per_m2": (1.0, 50.0, "lower"),
    "annual_failure_rate": (0.0, 0.5, "lower"),
    "utilization": (0.1, 1.0, "higher"),
}

DRIVER_LABELS = {
    "launch_cost_per_kg_usd": "launch cost ($/kg)",
    "solar_specific_power_w_per_kg": "solar specific power (W/kg)",
    "radiator_areal_mass_kg_per_m2": "radiator areal mass (kg/m^2)",
    "annual_failure_rate": "annual accelerator failure rate",
    "utilization": "utilization",
}


def binding_constraints(ev: Evaluation) -> list[str]:
    """Human-readable notes on what limits this design."""
    notes: list[str] = []
    factors = ev.waterfall.factors
    limiting = sorted((v, k) for k, v in factors.items() if v < 0.999)
    for value, name in limiting:
        notes.append(
            f"{FACTOR_LABELS[name]}: factor {value:.2f} (caps compute to {value * 100:.0f}% here)"
        )

    ratio = ev.details.get("radiator_packaging_ratio")
    if ratio is not None and ratio > 1.0:
        notes.append(f"radiator area exceeds packaging budget by {(ratio - 1.0) * 100:.0f}%")

    solar_ratio = ev.details.get("solar_packaging_ratio")
    if solar_ratio is not None and solar_ratio > 1.0:
        notes.append(f"solar array exceeds deployable budget by {(solar_ratio - 1.0) * 100:.0f}%")

    if ev.thermal_bottleneck is not None:
        m2_kw = ev.details.get("radiator_m2_per_kw")
        kg_kw = ev.details.get("thermal_kg_per_kw")
        t_rad = ev.details.get("radiator_t_rad_k")
        notes.append(
            f"thermal bottleneck: {ev.thermal_bottleneck} "
            f"(T_rad {t_rad:.0f} K, {m2_kw:.2f} m^2/kW, {kg_kw:.1f} kg/kW thermal)"
        )
    for w in ev.thermal_warnings:
        notes.append(f"thermal caveat: {w}")

    ttc_margin = ev.details.get("rf_ttc_margin_db")
    if ttc_margin is not None and ttc_margin < 3.0:
        notes.append(f"RF TT&C link margin is thin ({ttc_margin:.1f} dB)")

    optical_avail = ev.details.get("optical_downlink_availability")
    if optical_avail is not None and optical_avail < 1.0:
        notes.append(f"optical downlink weather-limited to {optical_avail * 100:.0f}% availability")

    crosslink_factor = ev.details.get("crosslink_factor")
    if crosslink_factor is not None and crosslink_factor < 0.999:
        cap = ev.details.get("crosslink_capacity_gbps", 0.0)
        notes.append(
            f"crosslink-limited: {cap:,.0f} Gbps caps compute to {crosslink_factor * 100:.0f}%"
        )

    launches = ev.details.get("n_launches")
    if launches is not None and launches > 1.0:
        notes.append(f"requires ~{launches:.0f} launches at the chosen vehicle capacity")

    if ev.kg_per_kw is not None:
        notes.append(
            f"mass intensity {ev.kg_per_kw:.1f} kg/kW IT; {ev.specific_power_w_per_kg:.1f} W/kg"
        )

    if not notes:
        notes.append("no single factor dominates; design is broadly balanced")
    return notes


def _bisect(f: Callable[[float], float], lo: float, hi: float, iters: int = 60) -> float | None:
    """Find x in [lo, hi] with f(x) = 0 by bisection, or None if no sign change."""
    f_lo, f_hi = f(lo), f(hi)
    if f_lo == 0.0:
        return lo
    if f_hi == 0.0:
        return hi
    if (f_lo > 0.0) == (f_hi > 0.0):
        return None
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        if (f_mid > 0.0) == (f_lo > 0.0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def beats_earth_thresholds(
    space_lcoc_of: Callable[[str, float], float],
    earth_lcoc: float,
    drivers: tuple[str, ...] = tuple(DRIVER_RANGES),
) -> dict[str, float | None]:
    """For each driver, the value at which space LCOC equals Earth LCOC.

    `space_lcoc_of(driver, value)` re-evaluates space LCOC with that one driver
    overridden. Returns the crossover value per driver (None if none in range).
    """
    out: dict[str, float | None] = {}
    for driver in drivers:
        lo, hi, _ = DRIVER_RANGES[driver]

        def objective(value: float, d: str = driver) -> float:
            return space_lcoc_of(d, value) - earth_lcoc

        out[driver] = _bisect(objective, lo, hi)
    return out


def format_thresholds(thresholds: dict[str, float | None]) -> list[str]:
    lines: list[str] = []
    for driver, value in thresholds.items():
        label = DRIVER_LABELS.get(driver, driver)
        _, _, better = DRIVER_RANGES[driver]
        if value is None:
            lines.append(f"{label}: no crossover with Earth within the searched range")
        else:
            relation = "below" if better == "lower" else "above"
            lines.append(
                f"space matches Earth at {label} = {value:.4g} (space wins {relation} this)"
            )
    return lines
