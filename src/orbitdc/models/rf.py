"""RF link budget (EQUATIONS.md §7), Tier 0.

Inline Friis / free-space-path-loss link budget with enough terms for a
pass/fail margin. When the optional `opensatcom` backend is installed it can
provide a richer Tier-1 budget (ITU-R rain/gas, polarization, cascaded RF
chain); this module exposes the seam but does the Tier-0 math itself so the
base install stays dependency-free and deterministic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from orbitdc.core.constants import BOLTZMANN, SPEED_OF_LIGHT

try:  # optional Tier-1 backend
    import opensatcom  # noqa: F401

    HAS_OPENSATCOM = True
except ImportError:
    HAS_OPENSATCOM = False


@dataclass(frozen=True)
class LinkResult:
    fspl_db: float
    rx_power_dbw: float
    cn0_dbhz: float
    ebn0_db: float
    margin_db: float


def preferred_backend() -> str:
    """'opensatcom' if the Tier-1 backend is installed, else 'inline'."""
    return "opensatcom" if HAS_OPENSATCOM else "inline"


def fspl_db(range_m: float, freq_hz: float, backend: str = "auto") -> float:
    """Free-space path loss, dB: 20 log10(4 pi R / lambda).

    With ``backend='auto'`` (or ``'opensatcom'``) and opensatcom installed, the
    Tier-1 backend is used; otherwise the inline Tier-0 form. The seam is
    best-effort: any backend mismatch falls back to inline.
    """
    if backend in ("auto", "opensatcom") and HAS_OPENSATCOM:
        try:
            from opensatcom.propagation import FreeSpacePropagation

            return float(FreeSpacePropagation().total_path_loss_db(freq_hz, range_m))
        except Exception:
            pass
    wavelength_m = SPEED_OF_LIGHT / freq_hz
    return 20.0 * math.log10(4.0 * math.pi * range_m / wavelength_m)


def aperture_gain_dbi(diameter_m: float, freq_hz: float, efficiency: float = 0.6) -> float:
    """Aperture-antenna gain, dBi: 10 log10(eta (pi D / lambda)^2)."""
    wavelength_m = SPEED_OF_LIGHT / freq_hz
    gain = efficiency * (math.pi * diameter_m / wavelength_m) ** 2
    return 10.0 * math.log10(gain)


def link_margin(
    *,
    tx_power_dbw: float,
    tx_gain_dbi: float,
    rx_gain_dbi: float,
    range_m: float,
    freq_hz: float,
    system_noise_temp_k: float,
    data_rate_bps: float,
    required_ebn0_db: float,
    other_losses_db: float = 0.0,
) -> LinkResult:
    """Compute received power, C/N0, Eb/N0, and margin against a required Eb/N0."""
    loss = fspl_db(range_m, freq_hz) + other_losses_db
    rx_power_dbw = tx_power_dbw + tx_gain_dbi + rx_gain_dbi - loss
    n0_dbw_hz = 10.0 * math.log10(BOLTZMANN * system_noise_temp_k)
    cn0_dbhz = rx_power_dbw - n0_dbw_hz
    ebn0_db = cn0_dbhz - 10.0 * math.log10(data_rate_bps)
    return LinkResult(
        fspl_db=loss,
        rx_power_dbw=rx_power_dbw,
        cn0_dbhz=cn0_dbhz,
        ebn0_db=ebn0_db,
        margin_db=ebn0_db - required_ebn0_db,
    )
