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
    # bits moved off-accelerator per FLOP of delivered compute; drives the network limit.
    comm_intensity_bits_per_flop: float = Field(default=1e-3, ge=0.0)


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
    # Aggregate available link capacity for the constellation (Gbit/s).
    crosslink_gbps: float = Field(default=1.0e4, ge=0.0)
    downlink_gbps: float = Field(default=100.0, ge=0.0)
    # Radiator area that physically fits per satellite (packaging budget, m^2).
    radiator_area_m2_per_sat: float = Field(default=40.0, gt=0.0)


class SpaceParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    orbit: Orbit
    architecture: Architecture
    # Non-accelerator IT draw (CPU/memory/network/storage) as a fraction of accelerator TDP.
    it_power_overhead_frac: float = Field(default=0.25, ge=0.0)
    # Spacecraft housekeeping (avionics/comms/pumps/heaters) as a fraction of IT power.
    non_it_power_frac: float = Field(default=0.10, ge=0.0)
    # Catalog keys.
    solar_array: str = "rigid_triple_junction"
    battery: str = "li_ion_generic"
    launch: str = "current_reusable"
    # Thermal radiator co-design (Phase 2A).
    radiator_panel: str = "deployable_osr"
    coolant: str = "ammonia_single_phase"
    chip_stack: str = "h100_direct_liquid"
    thermal_environment: str = "conservative_leo"
    thermal_eol: bool = True
    # Reliability.
    annual_failure_rate: float = Field(default=0.05, ge=0.0)
    spare_fraction: float = Field(default=0.0, ge=0.0)
    reset_recovery_availability: float = Field(default=0.99, gt=0.0, le=1.0)


class EarthParams(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    n_accelerators: int = Field(gt=0)
    pue: float = Field(default=1.10, ge=1.0)
    energy_price_per_kwh: float = Field(default=0.06, ge=0.0)
    facility_capex_per_mw_usd: float = Field(default=12.0e6, ge=0.0)
    availability: float = Field(default=0.995, gt=0.0, le=1.0)
    it_power_overhead_frac: float = Field(default=0.25, ge=0.0)


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
