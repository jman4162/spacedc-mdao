"""Radiation environment and its effect on failure rate (EQUATIONS section 10).

A coarse, orbit-dependent TID/SEU model that makes the accelerator failure rate
depend on altitude, inclination, and hardware tolerance instead of being a flat
scalar. Deliberately low fidelity and low confidence (see data/radiation_env.yaml);
its job is to expose the radiation lever and feed sensitivity studies, not to
predict device behavior. Commercial parts (H100) are radiation-soft; this is a
real feasibility constraint for space.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.core.catalog_loader import load_yaml


@dataclass(frozen=True)
class RadiationResult:
    tid_krad_per_year: float
    tid_dose_krad: float
    seu_relative: float
    failure_rate_per_year: float  # radiation-induced contribution


def _interp(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            frac = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + frac * (ys[i] - ys[i - 1])
    return ys[-1]


def radiation_environment(altitude_km: float, inclination_deg: float) -> tuple[float, float]:
    """Return (TID krad/yr, relative SEU flux) for an orbit.

    Inclination scales the SEU flux up modestly (polar / SAA exposure).
    """
    env = load_yaml("radiation_env.yaml")["leo"]
    tid = _interp(altitude_km, env["altitude_km"], env["tid_krad_per_year"])
    seu_rel = _interp(altitude_km, env["altitude_km"], env["seu_relative"])
    inclination_factor = 1.0 + 0.5 * min(1.0, abs(inclination_deg) / 90.0)
    return tid, seu_rel * inclination_factor


def radiation_failure_contribution(
    *,
    altitude_km: float,
    inclination_deg: float,
    mission_years: float,
    tid_tolerance_krad: float,
    seu_susceptibility: float,
    ecc_mitigation: float,
) -> RadiationResult:
    """Radiation-induced annual failure-rate contribution for an accelerator.

    TID term: fraction of the part's dose tolerance consumed per year (wear).
    SEU term: soft-error rate scaled by flux, device susceptibility, and ECC.
    """
    tid_krad_per_year, seu_relative = radiation_environment(altitude_km, inclination_deg)
    tid_dose = tid_krad_per_year * mission_years
    tid_term = (tid_dose / tid_tolerance_krad) / mission_years if tid_tolerance_krad > 0 else 1.0

    seu_base = load_yaml("radiation_env.yaml")["leo"]["seu_base_rate_per_year"]
    seu_term = seu_base * seu_relative * seu_susceptibility * (1.0 - ecc_mitigation)

    return RadiationResult(
        tid_krad_per_year=tid_krad_per_year,
        tid_dose_krad=tid_dose,
        seu_relative=seu_relative,
        failure_rate_per_year=tid_term + seu_term,
    )
