"""Free-space optical link budget (EQUATIONS.md §8), Tier 0.

Diffraction-limited divergence, geometric coupling, pointing loss, photons per
bit, and a margin. None of the surveyed dependencies cover free-space optical,
so this is implemented from scratch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from orbitdc.core.constants import PLANCK, SPEED_OF_LIGHT


@dataclass(frozen=True)
class OpticalLinkResult:
    divergence_rad: float
    geometric_efficiency: float
    pointing_efficiency: float
    rx_power_w: float
    photons_per_bit: float
    margin_db: float


def beam_divergence_rad(wavelength_m: float, tx_aperture_m: float) -> float:
    """Diffraction-limited divergence: theta ~ 1.22 lambda / D."""
    return 1.22 * wavelength_m / tx_aperture_m


def pointing_efficiency(pointing_error_rad: float, beam_divergence_rad_value: float) -> float:
    """Gaussian-beam pointing loss: exp(-2 (theta_err / theta_beam)^2)."""
    return math.exp(-2.0 * (pointing_error_rad / beam_divergence_rad_value) ** 2)


def optical_link(
    *,
    tx_power_w: float,
    wavelength_m: float,
    tx_aperture_m: float,
    rx_aperture_m: float,
    range_m: float,
    pointing_error_rad: float,
    eta_tx: float = 0.8,
    eta_rx: float = 0.8,
    eta_atm: float = 1.0,
    data_rate_bps: float = 1e10,
    receiver_sensitivity_photons_per_bit: float = 100.0,
) -> OpticalLinkResult:
    """Tier-0 received power and margin for a free-space optical link."""
    theta = beam_divergence_rad(wavelength_m, tx_aperture_m)
    eta_geo = min(1.0, (rx_aperture_m / (2.0 * range_m * theta)) ** 2)
    eta_point = pointing_efficiency(pointing_error_rad, theta)

    rx_power_w = tx_power_w * eta_tx * eta_rx * eta_geo * eta_point * eta_atm
    photon_energy_j = PLANCK * SPEED_OF_LIGHT / wavelength_m
    photons_per_bit = (rx_power_w / data_rate_bps) / photon_energy_j

    margin_db = 10.0 * math.log10(photons_per_bit / receiver_sensitivity_photons_per_bit)
    return OpticalLinkResult(
        divergence_rad=theta,
        geometric_efficiency=eta_geo,
        pointing_efficiency=eta_point,
        rx_power_w=rx_power_w,
        photons_per_bit=photons_per_bit,
        margin_db=margin_db,
    )
