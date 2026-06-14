"""Skyfield-backed orbit propagation (optional; requires the ``orbit`` extra).

Phase 1/2 use closed-form orbit math by default (poliastro is archived). This
module adds ground-station access windows from a TLE via Skyfield (SGP4). It
needs Skyfield's timescale/ephemeris data (a one-time download), so it is a
local/plugin capability, not part of the hermetic core or CI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccessWindows:
    n_passes: int
    total_access_hours: float
    pass_starts_utc: list[str]


def ground_station_access(
    tle_line1: str,
    tle_line2: str,
    lat_deg: float,
    lon_deg: float,
    *,
    start_utc: tuple[int, int, int],
    days: int = 1,
    min_elevation_deg: float = 5.0,
) -> AccessWindows:
    """Rise/set passes of a satellite over a ground station (Skyfield SGP4)."""
    from skyfield.api import EarthSatellite, load, wgs84

    ts = load.timescale()
    sat = EarthSatellite(tle_line1, tle_line2, "sat", ts)
    observer = wgs84.latlon(lat_deg, lon_deg)
    y, m, d = start_utc
    t0 = ts.utc(y, m, d)
    t1 = ts.utc(y, m, d + days)

    times, events = sat.find_events(observer, t0, t1, altitude_degrees=min_elevation_deg)

    starts: list[str] = []
    total_hours = 0.0
    rise_time = None
    for t, event in zip(times, events, strict=True):
        if event == 0:  # rise
            rise_time = t
            starts.append(t.utc_iso())
        elif event == 2 and rise_time is not None:  # set
            total_hours += (t - rise_time) * 24.0
            rise_time = None
    return AccessWindows(
        n_passes=len(starts), total_access_hours=total_hours, pass_starts_utc=starts
    )


def access_availability(windows: AccessWindows, days: int) -> float:
    """Fraction of the window the satellite is in view of the station (0..1)."""
    span_hours = days * 24.0
    if span_hours <= 0.0:
        return 0.0
    return min(1.0, windows.total_access_hours / span_hours)


def network_access_fraction(
    tle_line1: str,
    tle_line2: str,
    ground_stations: list[tuple[float, float]],
    *,
    start_utc: tuple[int, int, int],
    days: int = 3,
    min_elevation_deg: float = 10.0,
) -> float:
    """Union access fraction across a ground-station network (0..1).

    Treats stations as independent (1 - prod(1 - a_i)); a rough upper bound on
    the true union when passes overlap. Use it to refine optical-downlink
    availability under the Skyfield orbit fidelity.
    """
    if not ground_stations:
        return 0.0
    miss = 1.0
    for lat, lon in ground_stations:
        w = ground_station_access(
            tle_line1,
            tle_line2,
            lat,
            lon,
            start_utc=start_utc,
            days=days,
            min_elevation_deg=min_elevation_deg,
        )
        miss *= 1.0 - access_availability(w, days)
    return 1.0 - miss
