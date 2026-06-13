"""Load and validate scenarios from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from orbitdc.core.schema import Scenario


def load_scenario(path: str | Path) -> Scenario:
    """Read a YAML scenario file and validate it into a `Scenario`."""
    text = Path(path).read_text()
    data = cast(dict[str, Any], yaml.safe_load(text))
    return Scenario.model_validate(data)


def load_scenario_dict(data: dict[str, Any]) -> Scenario:
    """Validate an already-parsed scenario mapping."""
    return Scenario.model_validate(data)
