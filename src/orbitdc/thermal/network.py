"""Level 2 chip-to-radiator thermal network (THEMRAL_RADIATOR_DEEPDIVE §5, §6).

The radiator temperature is not a free input: the junction must stay below its
limit through the resistance stack, which sets the maximum allowable radiator
temperature, which sets the minimum radiator area. A radiator can be 'big
enough' yet the die still overheats because heat cannot transport fast enough.
"""

from __future__ import annotations

from orbitdc.thermal.surfaces import ChipThermalStack


def junction_temperature_k(t_rad_k: float, stack: ChipThermalStack) -> float:
    """T_junction = T_rad + Q_chip * R_total."""
    return t_rad_k + stack.chip_power_w * stack.r_total


def max_radiator_temp_k(stack: ChipThermalStack, *, use_design_limit: bool = False) -> float:
    """Highest radiator temperature that keeps the junction within its limit.

    T_rad_max = Tj_limit - Q_chip * R_total. Lower => larger radiator area.
    """
    tj_limit = stack.tj_design_k if use_design_limit else stack.tj_max_k
    return tj_limit - stack.chip_power_w * stack.r_total


def hbm_margin_k(t_rad_k: float, stack: ChipThermalStack) -> float | None:
    """Margin to the HBM temperature limit, if one is defined (K). Negative = over."""
    if stack.hbm_limit_k is None:
        return None
    return stack.hbm_limit_k - junction_temperature_k(t_rad_k, stack)
