"""OpenMDAO problem layer (optional; requires the ``mdao`` extra).

Import lazily — ``import orbitdc.mdao`` pulls in OpenMDAO. The base package and
``orbitdc.compare`` do not depend on this module.
"""

from orbitdc.mdao.problem import OrbitDCComponent, build_problem, optimize_single

__all__ = ["OrbitDCComponent", "build_problem", "optimize_single"]
