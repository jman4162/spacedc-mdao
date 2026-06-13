"""Golden-value regression tests for the discipline models.

Each check is hand-derivable from the equation it tests (EQUATIONS.md).
"""

from __future__ import annotations

import math

from orbitdc.core.constants import SPEED_OF_LIGHT, STEFAN_BOLTZMANN
from orbitdc.core.registry import get_accelerator, get_radiator
from orbitdc.models import compute, lasercom, orbit, reliability, rf, thermal


def test_h100_is_dense_not_sparse() -> None:
    accel = get_accelerator("h100_sxm")
    # 989 dense FP16 TFLOPS; 1979 would be the 2:4 sparsity number.
    assert accel.peak_tflops_dense == 989.0
    assert accel.sparsity_supported is True
    assert compute.peak_tflops(2, accel) == 1978.0


def test_orbit_period_650km() -> None:
    state = orbit.orbit_state(650.0)
    # A 650 km circular orbit has a ~97.7 min period.
    assert 97.0 < state.period_s / 60.0 < 98.5


def test_eclipse_fraction_matches_closed_form() -> None:
    state = orbit.orbit_state(650.0)
    r = state.radius_m
    re = 6_378_137.0
    expected = math.asin(re / r) / math.pi
    assert math.isclose(state.eclipse_fraction, expected, rel_tol=1e-9)
    assert math.isclose(state.sunlit_fraction, 1.0 - expected, rel_tol=1e-9)


def test_eclipse_zero_at_high_beta() -> None:
    # Large beta angle: the orbit never enters the cylindrical shadow.
    assert orbit.eclipse_fraction(7_028_137.0, beta_deg=80.0) == 0.0


def test_radiator_area_matches_stefan_boltzmann() -> None:
    rad = get_radiator("aluminum_panel")
    q = 1.0e5
    flux = (
        rad.emissivity
        * STEFAN_BOLTZMANN
        * rad.view_factor
        * (rad.t_radiator_k**4 - rad.t_sink_k**4)
    )
    expected_area = q / flux
    assert math.isclose(thermal.radiator_area_required(q, rad), expected_area, rel_tol=1e-12)
    # Sanity: order ~350 m^2 for these defaults.
    assert 300.0 < expected_area < 400.0


def test_fspl_matches_formula() -> None:
    range_m, freq_hz = 2.0e6, 26.0e9
    wavelength = SPEED_OF_LIGHT / freq_hz
    expected = 20.0 * math.log10(4.0 * math.pi * range_m / wavelength)
    assert math.isclose(rf.fspl_db(range_m, freq_hz), expected, rel_tol=1e-12)
    assert 186.0 < expected < 187.5


def test_optical_divergence_airy() -> None:
    theta = lasercom.beam_divergence_rad(1.55e-6, 0.1)
    assert math.isclose(theta, 1.22 * 1.55e-6 / 0.1, rel_tol=1e-12)


def test_reliability_mean_surviving() -> None:
    res = reliability.size_reliability(
        n_accelerators=1000,
        annual_failure_rate=0.05,
        mission_years=5.0,
        spare_fraction=0.0,
        reset_recovery_availability=1.0,
    )
    expected = (1.0 - math.exp(-0.25)) / 0.25
    assert math.isclose(res.mean_surviving_fraction, expected, rel_tol=1e-9)
    assert math.isclose(res.expected_failures, 1000 * (1.0 - math.exp(-0.25)), rel_tol=1e-9)
