"""Tests for derived crosslink capacity (Phase 4A)."""

from __future__ import annotations

from pathlib import Path

import orbitdc as odc
from orbitdc.models.comms_link import crosslink_capacity

SPACE = Path(__file__).parents[1] / "examples" / "scenarios" / "orbital_1mw_inference.yaml"


def _cap(separation_m: float, aperture_m: float) -> float:
    return crosslink_capacity(
        separation_m=separation_m,
        tx_power_w=5.0,
        tx_aperture_m=aperture_m,
        rx_aperture_m=aperture_m,
        wavelength_m=1.55e-6,
        pointing_error_rad=1e-6,
        dwdm_channels=16,
        rx_sensitivity_photons_per_bit=100.0,
    ).capacity_gbps


def test_crosslink_is_modem_limited_close_in() -> None:
    # Close formation with a good aperture is modem-limited: 16 channels x 200 Gbps.
    assert _cap(1000.0, 0.08) == 200.0 * 16.0


def test_crosslink_falls_at_long_range() -> None:
    # Far + small aperture becomes photon-limited and drops below the modem cap.
    assert _cap(200000.0, 0.02) < _cap(1000.0, 0.08)


def test_crosslink_derived_not_magic_number() -> None:
    data = odc.load_scenario(SPACE).model_dump()
    # Remove the explicit crosslink_gbps so it derives from formation geometry.
    data["space"]["architecture"].pop("crosslink_gbps", None)
    ev = odc.evaluate_space(odc.load_scenario_dict(data))
    cap = ev.details["crosslink_capacity_gbps"]
    assert cap != 1.0e4  # not the schema default magic number
    assert cap > 0.0


def test_explicit_crosslink_gbps_overrides_derivation() -> None:
    data = odc.load_scenario(SPACE).model_dump()
    data["space"]["architecture"]["crosslink_gbps"] = 123.0
    ev = odc.evaluate_space(odc.load_scenario_dict(data))
    assert ev.details["crosslink_capacity_gbps"] == 123.0
