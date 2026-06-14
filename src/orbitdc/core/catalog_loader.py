"""Shared YAML catalog loading with provenance resolution.

Catalogs store each important number as a provenance mapping
(``{value, units, source, date, confidence, kind, ...}``); structural fields are
plain scalars. `resolve` returns the usable value; `load_yaml` and `entry`
read a catalog file from the ``orbitdc.data`` package. Used by both
``core.registry`` and ``thermal.catalog`` (previously duplicated).
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from typing import Any, cast

import yaml


def resolve(raw: Any) -> Any:
    """Return the usable value: the `value` of a provenance mapping, or the scalar."""
    if isinstance(raw, dict) and "value" in raw:
        return raw["value"]
    return raw


@cache
def load_yaml(filename: str) -> dict[str, Any]:
    """Load and cache a catalog YAML from the ``orbitdc.data`` package."""
    text = (files("orbitdc.data") / filename).read_text()
    return cast(dict[str, Any], yaml.safe_load(text) or {})


def entry(filename: str, key: str) -> dict[str, Any]:
    """Return one catalog entry with every field resolved to its value."""
    catalog = load_yaml(filename)
    if key not in catalog:
        raise KeyError(f"unknown entry {key!r} in {filename}; available: {sorted(catalog)}")
    return {k: resolve(v) for k, v in catalog[key].items()}
