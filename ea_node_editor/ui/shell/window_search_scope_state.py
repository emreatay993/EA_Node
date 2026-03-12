from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

ScopeCameraKey = tuple[str, str, tuple[str, ...]]
ScopeCameraState = tuple[float, float, float]


def set_graph_search_state(
    window: ShellWindow,
    *,
    open_: bool | None = None,
    query: str | None = None,
    results: list[dict[str, Any]] | None = None,
    highlight_index: int | None = None,
) -> None:
    changed = False
    if open_ is not None:
        normalized_open = bool(open_)
        if normalized_open != window._graph_search_open:
            window._graph_search_open = normalized_open
            changed = True
    if query is not None:
        normalized_query = str(query)
        if normalized_query != window._graph_search_query:
            window._graph_search_query = normalized_query
            changed = True
    if results is not None:
        normalized_results = list(results)
        if normalized_results != window._graph_search_results:
            window._graph_search_results = normalized_results
            changed = True
    if highlight_index is not None:
        normalized_index = int(highlight_index)
        if normalized_index != window._graph_search_highlight_index:
            window._graph_search_highlight_index = normalized_index
            changed = True
    if changed:
        window.graph_search_changed.emit()


def refresh_graph_search_results(window: ShellWindow, query: str) -> None:
    normalized_query = str(query).strip()
    if not normalized_query:
        set_graph_search_state(window, query="", results=[], highlight_index=-1)
        return
    ranked = window._search_graph_nodes(normalized_query, limit=window._GRAPH_SEARCH_LIMIT)
    highlight = 0 if ranked else -1
    set_graph_search_state(window, query=normalized_query, results=ranked, highlight_index=highlight)


def request_graph_search_move(window: ShellWindow, delta: int) -> None:
    if not window._graph_search_open or not window._graph_search_results:
        return
    step = 1 if int(delta) > 0 else -1 if int(delta) < 0 else 0
    if step == 0:
        return
    count = len(window._graph_search_results)
    current = window._graph_search_highlight_index
    if current < 0 or current >= count:
        next_index = 0 if step > 0 else count - 1
    else:
        next_index = max(0, min(count - 1, current + step))
    set_graph_search_state(window, highlight_index=next_index)


def request_graph_search_highlight(window: ShellWindow, index: int) -> None:
    if not window._graph_search_open:
        return
    normalized = int(index)
    if normalized < 0 or normalized >= len(window._graph_search_results):
        return
    set_graph_search_state(window, highlight_index=normalized)


def request_graph_search_accept(window: ShellWindow) -> bool:
    if not window._graph_search_open:
        return False
    if not window._graph_search_query.strip():
        return False
    if not window._graph_search_results:
        return False
    index = window._graph_search_highlight_index
    if index < 0 or index >= len(window._graph_search_results):
        index = 0
    result = window._graph_search_results[index]
    jumped = window._jump_to_graph_node(result["workspace_id"], result["node_id"])
    if jumped:
        window.request_close_graph_search()
    return bool(jumped)


def request_graph_search_jump(window: ShellWindow, index: int) -> bool:
    normalized = int(index)
    if normalized < 0 or normalized >= len(window._graph_search_results):
        return False
    set_graph_search_state(window, highlight_index=normalized)
    return bool(request_graph_search_accept(window))


def active_scope_camera_key(
    window: ShellWindow,
    scope_path: tuple[str, ...] | None = None,
) -> ScopeCameraKey | None:
    workspace_id = window.workspace_manager.active_workspace_id()
    workspace = window.model.project.workspaces.get(workspace_id)
    if workspace is None:
        return None
    workspace.ensure_default_view()
    view_id = workspace.active_view_id
    if not view_id:
        return None
    if scope_path is None:
        scope_path = tuple(str(value) for value in window.scene.active_scope_path)
    return workspace_id, view_id, tuple(scope_path)


def remember_scope_camera(window: ShellWindow, scope_path: tuple[str, ...] | None = None) -> None:
    key = active_scope_camera_key(window, scope_path)
    if key is None:
        return
    center = window.view.mapToScene(window.view.viewport().rect().center())
    window._runtime_scope_camera[key] = (float(window.view.zoom), float(center.x()), float(center.y()))


def restore_scope_camera(window: ShellWindow, scope_path: tuple[str, ...] | None = None) -> bool:
    key = active_scope_camera_key(window, scope_path)
    if key is None:
        return False
    state = window._runtime_scope_camera.get(key)
    if state is None:
        return False
    zoom, pan_x, pan_y = state
    window.view.set_zoom(max(0.1, min(3.0, float(zoom))))
    window.view.centerOn(float(pan_x), float(pan_y))
    return True


def navigate_scope(window: ShellWindow, navigate_fn: Callable[[], bool]) -> bool:
    remember_scope_camera(window)
    changed = bool(navigate_fn())
    if not changed:
        return False
    if not restore_scope_camera(window):
        window._frame_all()
    window.workspace_state_changed.emit()
    return True


def _persist_graphics_updates(window: ShellWindow, updates: dict[str, Any]) -> None:
    window.app_preferences_controller.update_graphics_settings(updates)


def set_snap_to_grid_enabled(window: ShellWindow, enabled: bool, *, persist: bool = True) -> None:
    normalized = bool(enabled)
    if window._snap_to_grid_enabled == normalized:
        if window.action_snap_to_grid.isChecked() != normalized:
            blocked = window.action_snap_to_grid.blockSignals(True)
            window.action_snap_to_grid.setChecked(normalized)
            window.action_snap_to_grid.blockSignals(blocked)
        return
    window._snap_to_grid_enabled = normalized
    if window.action_snap_to_grid.isChecked() != normalized:
        blocked = window.action_snap_to_grid.blockSignals(True)
        window.action_snap_to_grid.setChecked(normalized)
        window.action_snap_to_grid.blockSignals(blocked)
    window.snap_to_grid_changed.emit()
    if persist:
        _persist_graphics_updates(
            window,
            {
                "interaction": {
                    "snap_to_grid": normalized,
                },
            },
        )


def set_graphics_minimap_expanded(window: ShellWindow, expanded: bool, *, persist: bool = True) -> None:
    normalized = bool(expanded)
    if window._graphics_minimap_expanded == normalized:
        return
    window._graphics_minimap_expanded = normalized
    window.graphics_preferences_changed.emit()
    if persist:
        _persist_graphics_updates(
            window,
            {
                "canvas": {
                    "minimap_expanded": normalized,
                },
            },
        )


def show_graph_hint(window: ShellWindow, message: str, timeout_ms: int = 3600) -> None:
    normalized = str(message).strip()
    if not normalized:
        clear_graph_hint(window)
        return
    window._graph_hint_message = normalized
    window.graph_hint_changed.emit()
    timeout_value = max(250, int(timeout_ms))
    window.graph_hint_timer.start(timeout_value)


def clear_graph_hint(window: ShellWindow) -> None:
    if window.graph_hint_timer.isActive():
        window.graph_hint_timer.stop()
    if not window._graph_hint_message:
        return
    window._graph_hint_message = ""
    window.graph_hint_changed.emit()
