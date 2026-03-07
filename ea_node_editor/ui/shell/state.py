from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class ShellState:
    project_path: str = ""
    library_query: str = ""
    library_category: str = ""
    library_data_type: str = ""
    library_direction: str = ""
    active_run_id: str = ""
    active_run_workspace_id: str = ""
    engine_state_value: Literal["ready", "running", "paused", "error"] = "ready"
    last_manual_save_ts: float = 0.0
    last_autosave_fingerprint: str = ""
    autosave_recovery_deferred: bool = False
