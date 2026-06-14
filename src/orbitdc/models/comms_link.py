"""Inter-satellite optical crosslink capacity from a link budget (Phase 4A).

Derives the achievable crosslink bandwidth from formation geometry and terminal
parameters (separation, aperture, power, wavelength, DWDM channels) instead of
treating it as a magic number. Built on the Tier-0 free-space optical model in
`models/lasercom.py`, which it makes a live part of the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass

from orbitdc.core.constants import PLANCK, SPEED_OF_LIGHT
from orbitdc.models.lasercom import optical_link


@dataclass(frozen=True)
class CrosslinkResult:
    capacity_gbps: float
    rate_per_channel_gbps: float
    rx_power_w: float
    geometric_efficiency: float


def crosslink_capacity(
    *,
    separation_m: float,
    tx_power_w: float,
    tx_aperture_m: float,
    rx_aperture_m: float,
    wavelength_m: float,
    pointing_error_rad: float,
    dwdm_channels: int,
    rx_sensitivity_photons_per_bit: float,
    modem_rate_gbps_per_channel: float = 200.0,
    eta_tx: float = 0.8,
    eta_rx: float = 0.8,
) -> CrosslinkResult:
    """Achievable optical crosslink capacity (Gbit/s) between two satellites.

    The per-channel rate is the lesser of the modem limit (coherent optics, a few
    hundred Gbit/s) and the photon-limited rate set by received power; DWDM
    multiplies it across channels. Capacity falls as ~1/separation^2 once the link
    becomes photon-limited at longer range.
    """
    link = optical_link(
        tx_power_w=tx_power_w,
        wavelength_m=wavelength_m,
        tx_aperture_m=tx_aperture_m,
        rx_aperture_m=rx_aperture_m,
        range_m=separation_m,
        pointing_error_rad=pointing_error_rad,
        eta_tx=eta_tx,
        eta_rx=eta_rx,
    )
    photon_energy_j = PLANCK * SPEED_OF_LIGHT / wavelength_m
    photon_limited_bps = link.rx_power_w / (rx_sensitivity_photons_per_bit * photon_energy_j)
    rate_per_channel_bps = min(modem_rate_gbps_per_channel * 1e9, photon_limited_bps)
    total_gbps = rate_per_channel_bps * dwdm_channels / 1e9
    return CrosslinkResult(
        capacity_gbps=total_gbps,
        rate_per_channel_gbps=rate_per_channel_bps / 1e9,
        rx_power_w=link.rx_power_w,
        geometric_efficiency=link.geometric_efficiency,
    )
