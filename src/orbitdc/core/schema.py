"""Validated scenario schema (the I/O boundary).

A `Scenario` is the user-facing description of a design to evaluate. Physical
and cost constants live in the catalogs (`data/`); a scenario references those
by key and adds architecture and a few high-level knobs. Two kinds are
supported, discriminated by `kind`: an orbital design (`space`) and a
terrestrial baseline (`earth`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Workload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str = "generic"
    # Named workload preset (data/workloads.yaml); supplies comm intensity if set.
    # Defaults from `type` so a scenario's `type: llm_inference` pulls the catalog.
    workload_type: str | None = None
    # bits moved off-accelerator per FLOP of delivered compute; drives the network
    # limit. None means "resolve from workload_type catalog" (survives model_dump
    # round-trips, unlike a magic default that reloads as an explicit value).
    comm_intensity_bits_per_flop: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="before")
    @classmethod
    def _workload_type_from_type(cls, data: object) -> object:
        if isinstance(data, dict):
            t = data.get("type")
            if data.get("workload_type") is None and t not in (None, "generic"):
                return {**data, "workload_type": t}
        return data


class Orbit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str = "leo"
    altitude_km: float = Field(gt=0.0)
    inclination_deg: float | None = None


class Architecture(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    satellites: int = Field(gt=0)
    accelerators_per_satellite: int = Field(gt=0)
    crosslink: str = "optical"
    downlink_type: str = "optical"  # "optical" (weather-limited) or "rf"
    # Inter-satellite separation; drives the derived crosslink capacity and Δv.
    formation_separation_m: float = Field(default=1000.0, gt=0.0)
    # Aggregate crosslink capacity (Gbit/s); derived from geometry unless set here.
    crosslink_gbps: float = Field(default=1.0e4, ge=0.0)
    downlink_gbps: float = Field(default=100.0, ge=0.0)
    # Radiator area that physically fits per satellite (packaging budget, m^2).
    radiator_area_m2_per_sat: float = Field(default=40.0, gt=0.0)
    # Solar-array area that physically fits per satellite (deployable budget, m^2).
    solar_area_m2_per_sat: float = Field(default=200.0, gt=0.0)


class SpaceParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    orbit: Orbit
    architecture: Architecture
    # Non-accelerator IT draw (CPU/memory/network/storage) as a fraction of accelerator TDP.
    it_power_overhead_frac: float = Field(default=0.25, ge=0.0)
    # Average/peak load ratio; <1 sizes power+thermal for a bursty workload's average.
    duty_cycle_fraction: float = Field(default=1.0, gt=0.0, le=1.0)
    # Spacecraft housekeeping (avionics/comms/pumps/heaters) as a fraction of IT power.
    non_it_power_frac: float = Field(default=0.10, ge=0.0)
    # Catalog keys.
    solar_array: str = "rigid_triple_junction"
    battery: str = "li_ion_generic"
    launch: str = "current_reusable"
    # Launch-cost case: pulls a point from the launch catalog distribution.
    launch_case: Literal["current", "pessimistic", "aggressive", "speculative"] = "current"
    # Thermal radiator co-design (Phase 2A).
    radiator_panel: str = "deployable_osr"
    coolant: str = "ammonia_single_phase"
    chip_stack: str = "h100_direct_liquid"
    thermal_environment: str = "conservative_leo"
    thermal_eol: bool = True
    # "steady" (worst-case) or "transient" (orbit-averaged, duty-cycle aware).
    thermal_fidelity: Literal["steady", "transient"] = "steady"
    # Reliability.
    annual_failure_rate: float = Field(default=0.05, ge=0.0)
    spare_fraction: float = Field(default=0.0, ge=0.0)
    reset_recovery_availability: float = Field(default=0.99, gt=0.0, le=1.0)
    # Graceful degradation (Phase 4C): time-stepped fleet health with optional
    # launch-quantized resupply. Off by default (scalar mean availability).
    graceful_degradation: bool = False
    resupply_interval_years: float | None = Field(default=None, gt=0.0)
    # Orbit geometry and station-keeping (Phase 2D).
    beta_deg: float = 0.0
    drag_area_m2_per_sat: float = Field(default=20.0, ge=0.0)
    thruster_isp_s: float = Field(default=220.0, gt=0.0)
    # Formation flying (Phase 4C). Differential drag drives drift cancellation;
    # navigation uncertainty vs separation sets the collision-avoidance margin.
    formation_position_uncertainty_m: float = Field(default=50.0, gt=0.0)
    differential_drag_frac: float = Field(default=0.05, ge=0.0)
    # Thermal Level 4 (Phase 4C): parametric view-factor derate. Off by default
    # (full-hemisphere assumption); when on, reduces effective emission.
    thermal_view_factors: bool = False
    radiator_articulation_deg: float = Field(default=0.0, ge=0.0)
    radiator_self_view_frac: float = Field(default=0.05, ge=0.0, lt=1.0)
    radiator_array_blocking_frac: float = Field(default=0.10, ge=0.0, lt=1.0)
    # Thermal Level 5 (Phase 4C): mission-integrated degradation. Off by default
    # (single EOL snapshot); when on, derates f_thermal for coating drift, MMOD
    # area loss, and a possible coolant-loop-out.
    thermal_degradation: bool = False
    mmod_area_loss_per_year: float = Field(default=0.005, ge=0.0)
    coolant_loop_out_prob_per_year: float = Field(default=0.02, ge=0.0)
    n_coolant_loops: int = Field(default=2, ge=1)
    # Orbit fidelity (Phase 4C): closed-form by default; "skyfield" derives the
    # ground-station access fraction from a TLE (needs the `orbit` extra + data;
    # falls back to closed-form on any failure). Access refines optical downlink.
    orbit_fidelity: Literal["closed_form", "skyfield"] = "closed_form"
    tle_line1: str | None = None
    tle_line2: str | None = None
    ground_stations: tuple[tuple[float, float], ...] = ()
    access_start_utc: tuple[int, int, int] | None = None
    access_days: int = Field(default=3, ge=1)
    access_min_elevation_deg: float = Field(default=10.0, ge=0.0)


class EarthParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    n_accelerators: int = Field(gt=0)
    pue: float = Field(default=1.10, ge=1.0)
    energy_price_per_kwh: float = Field(default=0.06, ge=0.0)
    facility_capex_per_mw_usd: float = Field(default=12.0e6, ge=0.0)
    availability: float = Field(default=0.995, gt=0.0, le=1.0)
    it_power_overhead_frac: float = Field(default=0.25, ge=0.0)
    # Environmental (Phase 2D).
    grid_carbon_intensity_kg_per_kwh: float = Field(default=0.40, ge=0.0)
    wue_l_per_kwh: float = Field(default=1.8, ge=0.0)


class Scenario(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: Literal["space", "earth"]
    mission_life_years: float = Field(gt=0.0)
    accelerator: str = "h100_sxm"
    workload: Workload = Workload()
    utilization: float = Field(default=0.85, gt=0.0, le=1.0)
    sustained_fraction: float = Field(default=0.55, gt=0.0, le=1.0)
    discount_rate: float = Field(default=0.08, ge=0.0)

    space: SpaceParams | None = None
    earth: EarthParams | None = None

    @model_validator(mode="after")
    def _check_kind(self) -> Scenario:
        if self.kind == "space" and self.space is None:
            raise ValueError("space scenario requires a `space:` block")
        if self.kind == "earth" and self.earth is None:
            raise ValueError("earth scenario requires an `earth:` block")
        return self

    @property
    def n_accelerators(self) -> int:
        if self.kind == "space":
            assert self.space is not None
            return (
                self.space.architecture.satellites
                * self.space.architecture.accelerators_per_satellite
            )
        assert self.earth is not None
        return self.earth.n_accelerators
