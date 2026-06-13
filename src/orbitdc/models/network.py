"""Network model (EQUATIONS.md §9).

Required off-board bandwidth scales with delivered compute and the workload's
communication intensity. If the available link (downlink for Earth-dependent
output) can't carry it, compute is throttled (f_network < 1). For exaflop-scale
clusters, even a small bits-per-FLOP intensity implies large bandwidth, so
Earth-dependent workloads are easily network-limited.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkResult:
    required_gbps: float
    available_gbps: float
    f_network: float


def required_bandwidth_gbps(compute_tflops: float, comm_intensity_bits_per_flop: float) -> float:
    """B_req = C * I_comm. C[TFLOP/s]*1e12*bits_per_flop bits/s, expressed in Gbit/s."""
    bits_per_s = compute_tflops * 1e12 * comm_intensity_bits_per_flop
    return bits_per_s / 1e9


def size_network(
    compute_tflops: float,
    comm_intensity_bits_per_flop: float,
    available_gbps: float,
) -> NetworkResult:
    required = required_bandwidth_gbps(compute_tflops, comm_intensity_bits_per_flop)
    f_network = 1.0 if required <= 0.0 else min(1.0, available_gbps / required)
    return NetworkResult(required_gbps=required, available_gbps=available_gbps, f_network=f_network)
