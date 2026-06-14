"""Reproduce published space-DC references and test the calibration harness (Phase 4A).

References:
- Google Project Suncatcher: ~9.6-12.8 Tbps per aperture (24 DWDM channels);
  launch competitive below ~$200/kg by the mid-2030s; 100-200 m formations.
  (research.google blog; Converge Digest; DCD)
- Andrew McCalip's calculator: orbital compute is ~3x more expensive per usable
  watt than ground ("the economics are savage"). (andrewmccalip.com/space-datacenters)
"""

from __future__ import annotations

from pathlib import Path

import orbitdc as odc
from orbitdc.calibrate import fit_parameter
from orbitdc.compare import _launch_cost_for_case
from orbitdc.models.comms_link import crosslink_capacity

SCEN = Path(__file__).parents[1] / "examples" / "scenarios"


def test_suncatcher_crosslink_per_aperture() -> None:
    # Single aperture, 24 DWDM channels, close formation -> ~9.6-12.8 Tbps.
    cap = crosslink_capacity(
        separation_m=200.0,
        tx_power_w=5.0,
        tx_aperture_m=0.10,
        rx_aperture_m=0.10,
        wavelength_m=1.55e-6,
        pointing_error_rad=1e-6,
        dwdm_channels=24,
        rx_sensitivity_photons_per_bit=100.0,
        modem_rate_gbps_per_channel=533.0,
    ).capacity_gbps
    assert 9000.0 <= cap <= 13000.0  # Gbps, matches Suncatcher's per-aperture figure


def test_suncatcher_launch_target() -> None:
    # Suncatcher: competitive if launch falls below ~$200/kg.
    cost = _launch_cost_for_case("current_reusable", "speculative", 3000.0)
    assert cost <= 200.0


def test_mccalip_orbital_is_several_times_costlier() -> None:
    # McCalip's qualitative result: orbital is multiples more expensive than ground.
    result = odc.compare(
        odc.load_scenario(SCEN / "orbital_1mw_inference.yaml"),
        odc.load_scenario(SCEN / "earth_hyperscale_baseline.yaml"),
    )
    assert result.space.lcoc_per_pflop_day > 2.0 * result.earth.lcoc_per_pflop_day


def test_calibration_recovers_known_parameter() -> None:
    # Synthetic data y = 7.5 * x; recover the slope.
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [7.5 * x for x in xs]
    fitted = fit_parameter(
        xs,
        ys,
        model=lambda x, p: p * x,
        initial=1.0,
        name="slope",
        units="1",
        source="synthetic",
        date="2026-06-14",
    )
    assert abs(fitted.value - 7.5) < 1e-6
    assert fitted.kind == "empirical"
    assert fitted.confidence == "high"  # near-perfect fit
