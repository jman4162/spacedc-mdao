"""Pure model glue for the Streamlit app.

Wraps the orbitdc public API so the rendering layer (``app.tabs``) never reaches
into model internals. Deliberately free of streamlit and plotly imports: this
module is type-checked under mypy --strict and runs with only the base deps, so
the smoke test in ``tests/test_streamlit_app.py`` can exercise it headless.

The app's interactivity is override-driven: sliders build an ``overrides`` dict
that is threaded through ``evaluate_space`` (and the threshold solve), so the
headline verdict, waterfalls, thermal, and architecture views all recompute
live. Tornado and Monte Carlo run around the selected scenario baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from orbitdc import diagnostics, evaluate_earth, evaluate_space, load_scenario
from orbitdc.compare import GENERIC_COMM_INTENSITY
from orbitdc.core import catalog_loader
from orbitdc.core.registry import get_solar_array
from orbitdc.core.schema import Scenario
from orbitdc.evaluation import Evaluation
from orbitdc.optimize.sensitivity import TornadoEntry, tornado
from orbitdc.optimize.uncertainty import MonteCarloResult, monte_carlo
from orbitdc.thermal.catalog import get_radiator_surface
from orbitdc.thermal.surfaces import ChipThermalStack, RadiatorSurface, ThermalEnvironment
from orbitdc.thermal.transient import TransientResult

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "examples" / "scenarios"


# --- scenario discovery -----------------------------------------------------


@dataclass(frozen=True)
class ScenarioOption:
    """A loadable scenario file surfaced in the picker."""

    name: str
    path: str
    kind: str


def list_scenarios(kind: str) -> list[ScenarioOption]:
    """Discover valid scenarios of a given kind under ``examples/scenarios``.

    Files that fail to load (e.g. the untracked ``* 2.yaml`` editor duplicates)
    are skipped rather than crashing the app.
    """
    options: list[ScenarioOption] = []
    for path in sorted(SCENARIO_DIR.glob("*.yaml")):
        try:
            scenario = load_scenario(path)
        except Exception:
            continue
        if scenario.kind == kind:
            options.append(ScenarioOption(name=scenario.name, path=str(path), kind=kind))
    return options


@lru_cache(maxsize=64)
def load(path: str) -> Scenario:
    """Cached scenario load (paths are stable for a session)."""
    return load_scenario(path)


# --- driver sliders ---------------------------------------------------------


@dataclass(frozen=True)
class DriverSpec:
    """One uncertain driver exposed as a sidebar slider.

    ``lo``/``hi`` bound the slider; the actual range is widened at render time to
    always contain the scenario baseline. ``log`` selects a log-scale slider for
    drivers (comm intensity) that span orders of magnitude.
    """

    key: str
    label: str
    help: str
    lo: float
    hi: float
    log: bool = False
    fmt: str = "%.2f"


# Ranges echo optimize/sensitivity.TORNADO_RANGES (the plausible engineering
# band), widened where a scenario baseline can sit outside it (e.g. speculative
# launch below $1500/kg).
DRIVERS: tuple[DriverSpec, ...] = (
    DriverSpec(
        "launch_cost_per_kg_usd",
        "Launch cost ($/kg)",
        "Falcon/heavy-lift today is ~$1,500/kg; Starship-class targets are far lower.",
        lo=100.0,
        hi=6000.0,
        fmt="$%.0f",
    ),
    DriverSpec(
        "solar_specific_power_w_per_kg",
        "Solar specific power (W/kg)",
        "Rigid triple-junction ~60 W/kg; flexible ROSA-class arrays ~150-200 W/kg.",
        lo=50.0,
        hi=250.0,
        fmt="%.0f",
    ),
    DriverSpec(
        "radiator_areal_mass_kg_per_m2",
        "Radiator areal mass (kg/m²)",
        "Lower is lighter heat rejection. Deployable panels ~7 kg/m²; composite ~4 kg/m².",
        lo=3.0,
        hi=12.0,
        fmt="%.1f",
    ),
    DriverSpec(
        "utilization",
        "Utilization",
        "Fraction of installed compute kept usefully busy over the mission.",
        lo=0.40,
        hi=0.98,
        fmt="%.2f",
    ),
    DriverSpec(
        "annual_failure_rate",
        "Annual failure rate (1/yr)",
        "Per-accelerator annual loss rate; drives sparing and replacement mass.",
        lo=0.0,
        hi=0.20,
        fmt="%.3f",
    ),
    DriverSpec(
        "comm_intensity_bits_per_flop",
        "Comm intensity (bits/FLOP)",
        "Bits moved off-satellite per delivered FLOP. Text inference ~1e-8; "
        "rich multimodal output ~2e-6 (downlink-bound).",
        lo=1.0e-9,
        hi=1.0e-5,
        log=True,
        fmt="%.2e",
    ),
)


def resolve_comm_intensity(space: Scenario) -> float:
    """Baseline bits/FLOP the scenario evaluates at (explicit > catalog > generic)."""
    wl = space.workload
    if wl.comm_intensity_bits_per_flop is not None:
        return wl.comm_intensity_bits_per_flop
    if wl.workload_type:
        try:
            return float(
                catalog_loader.entry("workloads.yaml", wl.workload_type)[
                    "comm_intensity_bits_per_flop"
                ]
            )
        except KeyError:
            pass
    return GENERIC_COMM_INTENSITY


def baselines(space: Scenario) -> dict[str, float]:
    """The scenario's baseline value for each slider driver.

    Sliders default to these, so the unmoved app reproduces ``compare()`` exactly.
    """
    assert space.space is not None
    sp = space.space
    ev = evaluate_space(space)
    return {
        "launch_cost_per_kg_usd": float(ev.details["launch_cost_per_kg_usd"]),
        "solar_specific_power_w_per_kg": get_solar_array(sp.solar_array).specific_power_w_per_kg,
        "radiator_areal_mass_kg_per_m2": get_radiator_surface(
            sp.radiator_panel
        ).areal_density_kg_m2,
        "utilization": space.utilization,
        "annual_failure_rate": sp.annual_failure_rate,
        "comm_intensity_bits_per_flop": resolve_comm_intensity(space),
    }


# --- override-aware runs -----------------------------------------------------


def run_space(space: Scenario, overrides: dict[str, float]) -> Evaluation:
    """Evaluate the orbital design with the slider overrides applied."""
    return evaluate_space(space, overrides or None)


def run_earth(earth: Scenario) -> Evaluation:
    """Evaluate the terrestrial baseline (no overrides)."""
    return evaluate_earth(earth)


def lcoc_ratio(space_ev: Evaluation, earth_ev: Evaluation) -> float:
    """Space LCOC as a multiple of Earth LCOC (inf if Earth is free)."""
    e = earth_ev.lcoc_per_pflop_day
    return space_ev.lcoc_per_pflop_day / e if e > 0.0 else float("inf")


def binding_constraints(space_ev: Evaluation) -> list[str]:
    """Human-readable notes on what limits this (override-aware) design."""
    return diagnostics.binding_constraints(space_ev)


def thresholds(space: Scenario, earth_lcoc: float, overrides: dict[str, float]) -> list[str]:
    """Single-driver values at which space LCOC matches Earth, around the current overrides."""

    def space_lcoc_of(driver: str, value: float) -> float:
        merged = {**overrides, driver: value}
        return evaluate_space(space, merged).lcoc_per_pflop_day

    crossings = diagnostics.beats_earth_thresholds(space_lcoc_of, earth_lcoc)
    return diagnostics.format_thresholds(crossings)


# --- sensitivity / uncertainty (around the scenario baseline) ---------------


def tornado_entries(space: Scenario) -> list[TornadoEntry]:
    """One-at-a-time LCOC swings per driver, sorted by descending swing."""
    return tornado(space)


def baseline_lcoc(space: Scenario) -> float:
    """Space LCOC at the scenario baseline (the tornado pivot)."""
    return evaluate_space(space).lcoc_per_pflop_day


def monte_carlo_result(
    space: Scenario, earth_lcoc: float, n: int, seed: int = 0
) -> MonteCarloResult:
    """Monte Carlo over the default driver distributions vs the Earth baseline."""
    return monte_carlo(space, earth_lcoc, n=n, seed=seed)


# --- thermal figure inputs (mirrors viz/dashboard.py) -----------------------


@dataclass(frozen=True)
class ThermalInputs:
    """Scalars + catalog objects the thermal plotly builders need."""

    q_waste_w: float
    t_rad_k: float
    surface: RadiatorSurface
    env: ThermalEnvironment
    stack: ChipThermalStack
    bottleneck: str | None
    transient: TransientResult


def thermal_inputs(space: Scenario, space_ev: Evaluation) -> ThermalInputs:
    """Assemble the thermal-tab inputs exactly as the Panel dashboard does."""
    from orbitdc.compare import scenario_transient
    from orbitdc.core.registry import get_accelerator
    from orbitdc.thermal.catalog import get_chip_stack
    from orbitdc.thermal.presets import get_environment

    assert space.space is not None
    sp = space.space
    surface = get_radiator_surface(sp.radiator_panel)
    env = get_environment(sp.thermal_environment)
    stack = get_chip_stack(sp.chip_stack, get_accelerator(space.accelerator).tdp_w)
    return ThermalInputs(
        q_waste_w=space_ev.details.get("bus_load_w", space_ev.it_power_w),
        t_rad_k=space_ev.details.get("radiator_t_rad_k", 330.0),
        surface=surface,
        env=env,
        stack=stack,
        bottleneck=space_ev.thermal_bottleneck,
        transient=scenario_transient(space),
    )
