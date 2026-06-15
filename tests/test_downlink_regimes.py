"""Downlink accuracy: text vs rich-output inference regimes.

Locks in the comm-intensity correction: text inference un-binds the network
(limited by optical-weather availability), while rich-output binds the downlink
bandwidth. Comm intensity is the dominant LCOC driver.
"""

from __future__ import annotations

import orbitdc as odc
from orbitdc.core import catalog_loader
from orbitdc.optimize.sensitivity import tornado

TEXT = "examples/scenarios/orbital_1mw_inference.yaml"
MULTIMODAL = "examples/scenarios/orbital_multimodal_inference.yaml"


def test_text_value_below_multimodal() -> None:
    text = catalog_loader.entry("workloads.yaml", "llm_inference")["comm_intensity_bits_per_flop"]
    rich = catalog_loader.entry("workloads.yaml", "multimodal_inference")[
        "comm_intensity_bits_per_flop"
    ]
    assert text < rich
    # A first-principles text derivation (32 bits / 2*N_params) is <= 2e-9 at 8B;
    # the catalog default allows overhead but stays well below the rich-output value.
    assert text <= 1e-7


def test_text_inference_unbinds_network() -> None:
    ev = odc.evaluate_space(odc.load_scenario(TEXT))
    # Network is limited by optical-weather availability (~0.75), not bandwidth.
    assert ev.waterfall.factors["network"] > 0.6
    assert ev.details["optical_downlink_availability"] < 1.0


def test_multimodal_binds_downlink() -> None:
    ev = odc.evaluate_space(odc.load_scenario(MULTIMODAL))
    # Rich output saturates the downlink: network factor collapses.
    assert ev.waterfall.factors["network"] < 0.3


def test_text_cheaper_than_multimodal() -> None:
    text = odc.evaluate_space(odc.load_scenario(TEXT)).lcoc_per_pflop_day
    rich = odc.evaluate_space(odc.load_scenario(MULTIMODAL)).lcoc_per_pflop_day
    assert text < rich


def test_comm_intensity_is_dominant_driver() -> None:
    entries = tornado(odc.load_scenario(TEXT))
    top = max(entries, key=lambda e: e.swing)
    assert top.driver == "comm_intensity_bits_per_flop"


def test_dump_roundtrip_preserves_catalog_comm_intensity() -> None:
    # model_dump -> reload must not bake in a default that masks the catalog.
    base = odc.load_scenario(TEXT)
    rt = odc.load_scenario_dict(base.model_dump())
    assert odc.evaluate_space(rt).lcoc_per_pflop_day == odc.evaluate_space(base).lcoc_per_pflop_day
