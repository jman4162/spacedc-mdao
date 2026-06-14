"""Phase 4C-4: Skyfield orbit fidelity wiring and graceful fallback.

The pure helpers and the fallback path are hermetic. The real SGP4 computation
needs the `orbit` extra plus a one-time Skyfield data download, so it is skipped
when Skyfield (or its data) is unavailable."""

from __future__ import annotations

import pytest

import orbitdc as odc
from orbitdc.models.orbit_skyfield import AccessWindows, access_availability

SPACE = "examples/scenarios/orbital_1mw_inference.yaml"
ISS_TLE1 = "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9000"
ISS_TLE2 = "2 25544  51.6400 208.0000 0006703 130.0000 325.0000 15.50000000 10000"


def test_access_availability_fraction() -> None:
    w = AccessWindows(n_passes=4, total_access_hours=2.4, pass_starts_utc=[])
    assert access_availability(w, days=2) == pytest.approx(2.4 / 48.0)
    # Capped at 1.0 and 0 for a zero span.
    assert access_availability(w, days=0) == 0.0


def test_closed_form_access_is_unity() -> None:
    base = odc.evaluate_space(odc.load_scenario(SPACE))
    assert base.details["ground_station_access_fraction"] == 1.0


def test_skyfield_without_tle_falls_back() -> None:
    base = odc.load_scenario(SPACE)
    d = base.model_dump()
    d["space"]["orbit_fidelity"] = "skyfield"  # no TLE/stations -> fallback
    sk = odc.load_scenario_dict(d)
    b = odc.evaluate_space(base)
    g = odc.evaluate_space(sk)
    assert g.details["ground_station_access_fraction"] == 1.0
    assert g.lcoc_per_pflop_day == pytest.approx(b.lcoc_per_pflop_day)


def test_skyfield_access_lowers_optical_availability() -> None:
    pytest.importorskip("skyfield")
    from orbitdc.models import orbit_skyfield

    try:
        frac = orbit_skyfield.network_access_fraction(
            ISS_TLE1,
            ISS_TLE2,
            [(47.6, -122.3), (35.7, 139.7)],
            start_utc=(2024, 1, 1),
            days=2,
        )
    except Exception as exc:  # data download / SGP4 unavailable offline
        pytest.skip(f"Skyfield data unavailable: {exc}")

    # A LEO satellite is over any few stations only a small fraction of the time.
    assert 0.0 < frac < 0.5

    base = odc.load_scenario(SPACE)
    d = base.model_dump()
    d["space"].update(
        orbit_fidelity="skyfield",
        tle_line1=ISS_TLE1,
        tle_line2=ISS_TLE2,
        ground_stations=[[47.6, -122.3], [35.7, 139.7]],
        access_start_utc=[2024, 1, 1],
        access_days=2,
    )
    sk = odc.load_scenario_dict(d)
    b = odc.evaluate_space(base)
    g = odc.evaluate_space(sk)
    assert g.details["ground_station_access_fraction"] == pytest.approx(frac, rel=1e-3)
    # Tiny access starves the optical downlink -> much higher LCOC.
    assert g.lcoc_per_pflop_day > b.lcoc_per_pflop_day
