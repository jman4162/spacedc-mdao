"""Units at the I/O boundary only.

Model math runs on plain SI floats (documented in argument names). `pint` is
used here to parse and convert user-facing quantities into SI before they reach
the models. Keeping pint out of the numeric core keeps the math fast and
mypy-clean.
"""

from __future__ import annotations

from typing import Any

from pint import UnitRegistry

ureg: UnitRegistry[Any] = UnitRegistry()


def to_si(value: float, unit: str) -> float:
    """Convert ``value`` given in ``unit`` to its base SI magnitude.

    Example: ``to_si(650, "km") == 650_000.0``.
    """
    quantity = value * ureg(unit)
    return float(quantity.to_base_units().magnitude)
