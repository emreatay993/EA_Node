from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias


ScopeCameraKey: TypeAlias = tuple[str, str, tuple[str, ...]]
ScopeCameraState: TypeAlias = tuple[float, float, float]


@dataclass(slots=True)
class ShellProjectSessionState:
    project_path: str = ""
    recent_project_paths: list[str] = field(default_factory=list)
    last_manual_save_ts: float = 0.0
    last_autosave_fingerprint: str = ""
    autosave_recovery_deferred: bool = False


@dataclass(slots=True)
class ShellLibraryFilterState:
    library_query: str = ""
    library_category: str = ""
    library_data_type: str = ""
    library_direction: str = ""


@dataclass(slots=True)
class ShellRunState:
    active_run_id: str = ""
    active_run_workspace_id: str = ""
    engine_state_value: Literal["ready", "running", "paused", "error"] = "ready"


@dataclass(slots=True)
class GraphSearchState:
    open: bool = False
    query: str = ""
    results: list[dict[str, Any]] = field(default_factory=list)
    highlight_index: int = -1


@dataclass(slots=True)
class ConnectionQuickInsertState:
    open: bool = False
    query: str = ""
    results: list[dict[str, Any]] = field(default_factory=list)
    highlight_index: int = -1
    context: dict[str, Any] | None = None


@dataclass(slots=True)
class ShellWindowSearchScopeState:
    graph_search: GraphSearchState = field(default_factory=GraphSearchState)
    connection_quick_insert: ConnectionQuickInsertState = field(default_factory=ConnectionQuickInsertState)
    graph_hint_message: str = ""
    graphics_minimap_expanded: bool = False
    snap_to_grid_enabled: bool = False
    runtime_scope_camera: dict[ScopeCameraKey, ScopeCameraState] = field(default_factory=dict)


@dataclass(slots=True)
class ShellState:
    project_session: ShellProjectSessionState = field(default_factory=ShellProjectSessionState)
    library_filters: ShellLibraryFilterState = field(default_factory=ShellLibraryFilterState)
    run: ShellRunState = field(default_factory=ShellRunState)
    search_scope: ShellWindowSearchScopeState = field(default_factory=ShellWindowSearchScopeState)
