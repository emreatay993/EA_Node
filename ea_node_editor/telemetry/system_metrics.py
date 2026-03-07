from __future__ import annotations

import os
from dataclasses import dataclass

try:
    import psutil  # type: ignore
except Exception:  # noqa: BLE001
    psutil = None


@dataclass(slots=True, frozen=True)
class SystemMetrics:
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float


def _bytes_to_gb(size_bytes: float) -> float:
    return size_bytes / (1024 ** 3)


def read_system_metrics() -> SystemMetrics:
    if psutil is None:
        return SystemMetrics(cpu_percent=0.0, ram_used_gb=0.0, ram_total_gb=0.0)
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=None)
    return SystemMetrics(
        cpu_percent=float(cpu),
        ram_used_gb=round(_bytes_to_gb(mem.used), 2),
        ram_total_gb=round(_bytes_to_gb(mem.total), 2),
    )

