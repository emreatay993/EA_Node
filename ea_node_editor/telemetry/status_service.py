from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ea_node_editor.telemetry.system_metrics import SystemMetrics, read_system_metrics

EngineState = Literal["ready", "running", "paused", "error"]


@dataclass(frozen=True, slots=True)
class StatusPresentation:
    icon: str
    text: str


@dataclass(frozen=True, slots=True)
class MetricsPresentation:
    text: str


class ShellStatusService:
    def collect_system_metrics(self) -> SystemMetrics:
        return read_system_metrics()

    def engine_status(self, state: EngineState, details: str = "") -> StatusPresentation:
        text = str(state).capitalize()
        if details:
            text = f"{text} ({details})"
        icon_map = {
            "ready": "R",
            "running": "Run",
            "paused": "P",
            "error": "!",
        }
        return StatusPresentation(icon=icon_map.get(state, "E"), text=text)

    def job_counters(self, *, running: int, queued: int, done: int, failed: int) -> StatusPresentation:
        return StatusPresentation(icon="J", text=f"R:{running} Q:{queued} D:{done} F:{failed}")

    def system_metrics(
        self,
        *,
        fps: float,
        cpu_percent: float,
        ram_used_gb: float,
        ram_total_gb: float,
    ) -> MetricsPresentation:
        return MetricsPresentation(
            text=f"FPS:{max(0.0, float(fps)):.0f} "
            f"CPU:{float(cpu_percent):.0f}% "
            f"RAM:{float(ram_used_gb):.1f}/{float(ram_total_gb):.1f} GB"
        )

    def notification_counters(self, *, warnings: int, errors: int) -> StatusPresentation:
        return StatusPresentation(icon="N", text=f"W:{warnings} E:{errors}")


__all__ = [
    "EngineState",
    "MetricsPresentation",
    "ShellStatusService",
    "StatusPresentation",
]
