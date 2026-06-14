"""Thermal radiator co-design module.

A radiator-in-the-loop fidelity ladder (THEMRAL_RADIATOR_DEEPDIVE):
environment heat loads -> net radiator flux -> chip-to-radiator resistance
stack -> coolant loop -> radiator area + mass -> bottleneck diagnosis. The
radiator temperature is bounded by the chip stack, and closure is checked at
end of life.
"""

from orbitdc.thermal.codesign import ThermalCodesignResult, thermal_codesign
from orbitdc.thermal.surfaces import (
    ChipThermalStack,
    Coating,
    CoolantLoop,
    RadiatorSurface,
    ThermalEnvironment,
)

__all__ = [
    "ChipThermalStack",
    "Coating",
    "CoolantLoop",
    "RadiatorSurface",
    "ThermalCodesignResult",
    "ThermalEnvironment",
    "thermal_codesign",
]
