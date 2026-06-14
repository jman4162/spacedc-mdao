"""Load provenance-tagged thermal catalogs (coatings, coolants, chip stacks,
radiator panels) into the thermal dataclasses. Same YAML-with-provenance
convention as ``orbitdc.core.registry``.
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from typing import Any, cast

import yaml

from orbitdc.thermal.surfaces import ChipThermalStack, Coating, CoolantLoop, RadiatorSurface


def _resolve(raw: Any) -> Any:
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]
    return raw


@cache
def _load(filename: str) -> dict[str, Any]:
    text = (files("orbitdc.data") / filename).read_text()
    return cast(dict[str, Any], yaml.safe_load(text) or {})


def _entry(filename: str, key: str) -> dict[str, Any]:
    catalog = _load(filename)
    if key not in catalog:
        raise KeyError(f"unknown entry {key!r} in {filename}; available: {sorted(catalog)}")
    return {k: _resolve(v) for k, v in catalog[key].items()}


def get_coating(key: str) -> Coating:
    e = _entry("coatings.yaml", key)
    return Coating(
        name=e.get("name", key),
        alpha_solar_bol=e["alpha_solar_bol"],
        eps_ir_bol=e["eps_ir_bol"],
        alpha_solar_eol=e["alpha_solar_eol"],
        eps_ir_eol=e["eps_ir_eol"],
    )


def get_coolant(key: str) -> CoolantLoop:
    e = _entry("coolants.yaml", key)
    return CoolantLoop(
        fluid=e.get("fluid", key),
        mode=e.get("mode", "single_phase"),
        cp_j_kg_k=e["cp_j_kg_k"],
        h_fg_j_kg=e.get("h_fg_j_kg", 0.0),
        delta_t_k=e.get("delta_t_k", 5.0),
        pump_power_fraction=e["pump_power_fraction"],
        freeze_temp_k=e.get("freeze_temp_k", 195.0),
        fluid_mass_per_kw=e.get("fluid_mass_per_kw", 1.5),
        hardware_mass_per_kw=e.get("hardware_mass_per_kw", 2.0),
    )


def get_chip_stack(key: str, chip_power_w: float) -> ChipThermalStack:
    e = _entry("chip_stacks.yaml", key)
    return ChipThermalStack(
        chip_power_w=chip_power_w,
        r_junction_to_case=e["r_junction_to_case"],
        r_tim=e["r_tim"],
        r_coldplate=e["r_coldplate"],
        r_transport=e["r_transport"],
        r_radiator=e["r_radiator"],
        tj_max_k=e.get("tj_max_k", 393.0),
        tj_design_k=e.get("tj_design_k", 363.0),
        hbm_limit_k=e.get("hbm_limit_k"),
    )


def get_radiator_surface(key: str, env_sun_facing: bool = False) -> RadiatorSurface:
    e = _entry("radiator_panels.yaml", key)
    return RadiatorSurface(
        coating=get_coating(e["coating"]),
        sides=e.get("sides", 2),
        areal_density_kg_m2=e["areal_density_kg_m2"],
        max_temp_k=e.get("max_temp_k", 350.0),
        view_factor_space=e.get("view_factor_space", 0.95),
    )
