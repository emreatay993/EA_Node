from __future__ import annotations

from typing import Any


def event_targets_active_run(
    event: dict[str, Any],
    *,
    active_run_id: str,
    run_scoped_event_types: set[str] | frozenset[str],
) -> bool:
    event_type = str(event.get("type", ""))
    if event_type not in run_scoped_event_types:
        return True
    event_run_id = str(event.get("run_id", ""))
    return bool(active_run_id and event_run_id and event_run_id == active_run_id)


def run_action_state(active_run_id: str, engine_state: str) -> tuple[bool, str]:
    has_active_run = bool(active_run_id)
    can_pause = has_active_run and engine_state in {"running", "paused"}
    pause_label = "Resume" if engine_state == "paused" else "Pause"
    return can_pause, pause_label
