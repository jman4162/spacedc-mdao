"""Compute model (EQUATIONS.md §2).

Peak throughput uses DENSE tensor performance. Sustained throughput is peak
times a workload-dependent fraction; this is the f_software factor in the
delivered-compute waterfall. Catalog FLOPS are upper bounds, not sustained
application performance.
"""

from __future__ import annotations

from orbitdc.core.registry import Accelerator


def peak_tflops(n_accelerators: int, accel: Accelerator) -> float:
    """Aggregate dense peak throughput, TFLOP/s."""
    return n_accelerators * accel.peak_tflops_dense


def it_power_w(n_accelerators: int, accel: Accelerator, overhead_frac: float) -> float:
    """IT power draw: accelerator TDP plus CPU/memory/network/storage overhead."""
    return n_accelerators * accel.tdp_w * (1.0 + overhead_frac)


def sustained_tflops(peak: float, f_sustained: float) -> float:
    """Sustained throughput = peak * sustained fraction."""
    return peak * f_sustained


def joules_per_token(it_power_w_value: float, tokens_per_second: float) -> float:
    """Energy per token, J/token (EQUATIONS.md §2: E_token = P_IT / R_token)."""
    if tokens_per_second <= 0.0:
        raise ValueError("tokens_per_second must be positive")
    return it_power_w_value / tokens_per_second
