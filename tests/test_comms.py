"""Tests for RF TT&C margin and optical-downlink availability (Phase 3A)."""

from __future__ import annotations

from pathlib import Path

import orbitdc as odc

SPACE = Path(__file__).parents[1] / "examples" / "scenarios" / "orbital_1mw_inference.yaml"


def test_ttc_margin_is_reported() -> None:
    ev = odc.evaluate_space(odc.load_scenario(SPACE))
    assert "rf_ttc_margin_db" in ev.details
    # An S-band TT&C link should close with comfortable margin.
    assert ev.details["rf_ttc_margin_db"] > 3.0


def test_optical_availability_reduces_network_factor() -> None:
    scen = odc.load_scenario(SPACE)
    # The demo downlink is optical -> weather-limited availability < 1.
    ev = odc.evaluate_space(scen)
    assert ev.details["optical_downlink_availability"] < 1.0
    # The network factor includes the availability multiplier.
    data = scen.model_dump()
    data["space"]["architecture"]["downlink_type"] = "rf"
    rf_scen = odc.load_scenario_dict(data)
    ev_rf = odc.evaluate_space(rf_scen)
    assert ev_rf.details["optical_downlink_availability"] == 1.0
    assert ev_rf.waterfall.factors["network"] >= ev.waterfall.factors["network"]
