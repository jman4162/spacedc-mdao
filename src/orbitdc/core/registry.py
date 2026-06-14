"""Catalog loading.

Catalogs live as YAML under ``orbitdc/data``. Each physically or economically
important number is written as a provenance mapping
(``{value, units, source, date, confidence, kind, ...}``); structural fields
(names, precision labels) are plain scalars. The registry resolves each entry
into a typed, frozen dataclass for the deterministic model path, and also keeps
the underlying `Assumption` objects so the provenance is never lost.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from functools import cache
from typing import Any, cast

from orbitdc.core.assumptions import Assumption
from orbitdc.core.catalog_loader import load_yaml as _load_yaml
from orbitdc.core.catalog_loader import resolve as _resolve


@dataclass(frozen=True)
class Accelerator:
    key: str
    name: str
    tdp_w: float
    peak_tflops_dense: float
    precision: str
    sparsity_supported: bool
    memory_gb: float
    mem_bw_tb_s: float
    mass_kg: float
    unit_cost_usd: float
    tid_tolerance_krad: float
    seu_susceptibility: float
    ecc_mitigation: float


@dataclass(frozen=True)
class SolarArray:
    key: str
    name: str
    specific_power_w_per_kg: float
    cell_efficiency: float
    packing_efficiency: float
    pointing_efficiency: float
    annual_degradation: float
    cost_per_w_usd: float


@dataclass(frozen=True)
class Battery:
    key: str
    name: str
    specific_energy_wh_per_kg: float
    depth_of_discharge: float
    round_trip_efficiency: float
    cost_per_wh_usd: float


@dataclass(frozen=True)
class Radiator:
    key: str
    name: str
    areal_mass_kg_per_m2: float
    emissivity: float
    t_radiator_k: float
    t_sink_k: float
    view_factor: float
    cost_per_m2_usd: float


@dataclass(frozen=True)
class LaunchVehicle:
    key: str
    name: str
    cost_per_kg_usd: float
    capacity_kg: float


_TYPES: dict[str, tuple[str, type]] = {
    "accelerators": ("accelerators.yaml", Accelerator),
    "solar_arrays": ("solar_arrays.yaml", SolarArray),
    "batteries": ("batteries.yaml", Battery),
    "radiators": ("radiators.yaml", Radiator),
    "launch": ("launch.yaml", LaunchVehicle),
}


@cache
def _catalog(category: str) -> dict[str, Any]:
    filename, cls = _TYPES[category]
    raw_entries = _load_yaml(filename)
    field_names = {f.name for f in fields(cls)}
    out: dict[str, Any] = {}
    for key, entry in raw_entries.items():
        kwargs: dict[str, Any] = {"key": key}
        for fname in field_names:
            if fname == "key":
                continue
            if fname not in entry:
                raise KeyError(f"{category}[{key}] missing field {fname!r}")
            kwargs[fname] = _resolve(entry[fname])
        out[key] = cls(**kwargs)
    return out


def list_catalogs() -> list[str]:
    """Names of the bundled data catalogs (YAML files under orbitdc/data)."""
    from importlib.resources import files

    return sorted(
        p.name.removesuffix(".yaml")
        for p in files("orbitdc.data").iterdir()
        if p.name.endswith(".yaml")
    )


def get_accelerator(key: str) -> Accelerator:
    return cast(Accelerator, _lookup("accelerators", key))


def get_solar_array(key: str) -> SolarArray:
    return cast(SolarArray, _lookup("solar_arrays", key))


def get_battery(key: str) -> Battery:
    return cast(Battery, _lookup("batteries", key))


def get_radiator(key: str) -> Radiator:
    return cast(Radiator, _lookup("radiators", key))


def get_launch(key: str) -> LaunchVehicle:
    return cast(LaunchVehicle, _lookup("launch", key))


def _lookup(category: str, key: str) -> Any:
    catalog = _catalog(category)
    if key not in catalog:
        raise KeyError(f"unknown {category} entry {key!r}; available: {sorted(catalog)}")
    return catalog[key]


def provenance(category: str) -> dict[str, dict[str, Assumption]]:
    """Return the `Assumption` for every provenance-tagged field, by entry then field."""
    filename, _ = _TYPES[category]
    raw_entries = _load_yaml(filename)
    out: dict[str, dict[str, Assumption]] = {}
    for key, entry in raw_entries.items():
        per_field: dict[str, Assumption] = {}
        for fname, raw in entry.items():
            if isinstance(raw, dict) and "value" in raw:
                per_field[fname] = Assumption(**raw)
        if per_field:
            out[key] = per_field
    return out
