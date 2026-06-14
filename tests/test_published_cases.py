"""Reproduce published radiator cases from the model (Phase 3A).

These derive the headline numbers from the net-flux balance under documented
assumptions, rather than asserting a stored constant. They validate that the
thermal model can recover the primary space-DC reference (Starcloud) and is
order-of-magnitude consistent with flown hardware (ISS PVR).
"""

from __future__ import annotations

from orbitdc.thermal import validation as v
from orbitdc.thermal.catalog import get_coating
from orbitdc.thermal.radiation import net_flux_w_m2
from orbitdc.thermal.surfaces import RadiatorSurface, ThermalEnvironment


def test_starcloud_633_reproduced_from_model() -> None:
    # Starcloud/Lumen white paper: ~633 W/m^2 net at 20 C, two-sided, low
    # absorptivity, one side sun-exposed. Recover it from the net-flux balance.
    surface = RadiatorSurface(coating=get_coating("osr"), sides=2, max_temp_k=400.0)
    env = ThermalEnvironment(sun_incidence_cos=1.0, view_factor_earth=0.05)
    net = net_flux_w_m2(293.15, surface, env, eol=False)  # 20 C, beginning of life
    assert 600.0 <= net <= 680.0  # reproduces the published ~633 W/m^2 claim
    assert v.STARCLOUD.net_w_m2 == 633.0  # the stored anchor agrees


def test_starcloud_is_optimistic_vs_conservative() -> None:
    # The same panel under EOL coatings + a sun/Earth-facing orientation rejects
    # much less, which is why the 633 figure is an optimistic bound.
    surface = RadiatorSurface(coating=get_coating("osr"), sides=2, max_temp_k=400.0)
    optimistic = net_flux_w_m2(
        293.15,
        surface,
        ThermalEnvironment(sun_incidence_cos=1.0, view_factor_earth=0.05),
        eol=False,
    )
    conservative = net_flux_w_m2(
        293.15, surface, ThermalEnvironment(sun_incidence_cos=1.0, view_factor_earth=0.30), eol=True
    )
    assert conservative < optimistic


def test_iss_pvr_order_of_magnitude() -> None:
    # ISS PVR rejects 14 kW over ~42.4 m^2 ~ 330 W/m^2. The model at an ISS-like
    # radiator temperature and two-sided panel lands in the same hundreds-of-W/m^2
    # band. It runs higher than the as-flown 330 because the model omits ISS
    # view-factor and plumbing inefficiencies.
    surface = RadiatorSurface(coating=get_coating("white_z93"), sides=2, max_temp_k=320.0)
    env = ThermalEnvironment(sun_incidence_cos=0.3, view_factor_earth=0.20)
    net = net_flux_w_m2(275.0, surface, env, eol=False)
    assert 250.0 <= net <= 600.0
    assert v.ISS_PVR.net_w_m2 is not None and 300.0 <= v.ISS_PVR.net_w_m2 <= 360.0
