from __future__ import annotations

import inspect
import time
from typing import TYPE_CHECKING, Any, Iterable, Literal

from PyQt6.QtCore import Qt, pyqtSlot
from ea_node_editor.execution.runtime_snapshot import coerce_runtime_snapshot
from ea_node_editor.ui.shell.runtime_history import history_action_invalidates_persistent_node_elapsed

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

_UNSET = object()
_EXECUTION_EDGE_PORT_KINDS = frozenset({"exec", "completed", "failed"})


@pyqtSlot(bool)
def set_snap_to_grid_enabled(self: "ShellWindow", enabled: bool) -> None:
    self.graph_canvas_presenter.set_snap_to_grid_enabled(enabled)


@pyqtSlot(bool)
def set_graphics_minimap_expanded(self: "ShellWindow", expanded: bool) -> None:
    self.graph_canvas_presenter.set_graphics_minimap_expanded(expanded)


@pyqtSlot(bool)
def set_graphics_show_port_labels(self: "ShellWindow", show_port_labels: bool) -> None:
    self.app_preferences_controller.update_graphics_settings(
        {
            "canvas": {
                "show_port_labels": show_port_labels,
            }
        },
        host=self,
    )


def _sync_graphics_show_port_labels_action(self: "ShellWindow", show_port_labels: bool) -> None:
    action = getattr(self, "action_show_port_labels", None)
    if action is None or action.isChecked() == show_port_labels:
        return
    blocked = action.blockSignals(True)
    action.setChecked(show_port_labels)
    action.blockSignals(blocked)


def _refresh_active_workspace_scene_payload(self: "ShellWindow") -> None:
    workspace_manager = getattr(self, "workspace_manager", None)
    scene = getattr(self, "scene", None)
    if workspace_manager is None or scene is None:
        return
    workspace_id = str(workspace_manager.active_workspace_id() or "").strip()
    if not workspace_id:
        return
    scene.refresh_workspace_from_model(workspace_id)


@pyqtSlot(str)
def set_graphics_performance_mode(self: "ShellWindow", mode: str) -> None:
    self.app_preferences_controller.update_graphics_settings(
        {
            "performance": {
                "mode": mode,
            }
        },
        host=self,
    )


def _normalize_node_execution_workspace_id(self: "ShellWindow", workspace_id: str) -> str:
    normalized_workspace_id = str(workspace_id or "").strip()
    if normalized_workspace_id:
        return normalized_workspace_id
    state = self.run_state
    for candidate in (
        state.active_run_workspace_id,
        state.node_execution_workspace_id,
    ):
        normalized_candidate = str(candidate or "").strip()
        if normalized_candidate:
            return normalized_candidate
    return ""


def _normalize_execution_edge_workspace_id(self: "ShellWindow", workspace_id: str) -> str:
    normalized_workspace_id = str(workspace_id or "").strip()
    if normalized_workspace_id:
        return normalized_workspace_id
    state = self.run_state
    for candidate in (
        state.active_run_workspace_id,
        state.execution_edge_workspace_id,
        state.node_execution_workspace_id,
    ):
        normalized_candidate = str(candidate or "").strip()
        if normalized_candidate:
            return normalized_candidate
    return ""


def _commit_node_execution_state_change(self: "ShellWindow") -> None:
    self.run_state.node_execution_revision += 1
    self.node_execution_state_changed.emit()


def _coerce_nonnegative_timing_ms(value: object) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return 0.0
    return normalized if normalized >= 0.0 else 0.0


def _current_epoch_ms() -> float:
    return time.time() * 1000.0


def _clear_execution_edge_progress_state_fields(self: "ShellWindow") -> bool:
    state = self.run_state
    if not (
        state.execution_edge_run_id
        or state.execution_edge_workspace_id
        or state.execution_edge_ids_by_source_node_id
        or state.progressed_execution_edge_ids
    ):
        return False
    state.execution_edge_run_id = ""
    state.execution_edge_workspace_id = ""
    state.execution_edge_ids_by_source_node_id.clear()
    state.progressed_execution_edge_ids.clear()
    return True


def _build_execution_edge_progress_index(
    self: "ShellWindow",
    *,
    workspace_id: str,
    runtime_snapshot: Any,
) -> tuple[str, dict[str, dict[str, tuple[str, ...]]]]:
    snapshot = coerce_runtime_snapshot(runtime_snapshot)
    normalized_workspace_id = str(workspace_id or "").strip()
    if snapshot is None:
        return normalized_workspace_id, {}
    if not normalized_workspace_id:
        normalized_workspace_id = str(snapshot.active_workspace_id or "").strip()
    if not normalized_workspace_id:
        return "", {}
    try:
        workspace = snapshot.workspace(normalized_workspace_id)
    except KeyError:
        return normalized_workspace_id, {}

    registry = getattr(self, "registry", None)
    if registry is None:
        return normalized_workspace_id, {}

    nodes_by_id = workspace.nodes_by_id
    port_kinds_by_node_id: dict[str, dict[str, str]] = {}
    indexed_edge_ids: dict[str, dict[str, list[str]]] = {}

    for edge in workspace.edges:
        edge_id = str(edge.edge_id or "").strip()
        source_node_id = str(edge.source_node_id or "").strip()
        source_port_key = str(edge.source_port_key or "").strip()
        if not edge_id or not source_node_id or not source_port_key:
            continue
        port_kinds = port_kinds_by_node_id.get(source_node_id)
        if port_kinds is None:
            port_kinds = {}
            source_node = nodes_by_id.get(source_node_id)
            if source_node is not None:
                try:
                    spec = registry.get_spec(source_node.type_id)
                except Exception:  # noqa: BLE001
                    spec = None
                if spec is not None:
                    port_kinds = {
                        str(port.key): str(port.kind or "").strip().lower()
                        for port in getattr(spec, "ports", ())
                    }
            port_kinds_by_node_id[source_node_id] = port_kinds
        port_kind = port_kinds.get(source_port_key, "")
        if port_kind not in _EXECUTION_EDGE_PORT_KINDS:
            continue
        indexed_edge_ids.setdefault(source_node_id, {}).setdefault(port_kind, []).append(edge_id)

    return normalized_workspace_id, {
        source_node_id: {
            port_kind: tuple(edge_ids)
            for port_kind, edge_ids in port_kind_map.items()
        }
        for source_node_id, port_kind_map in indexed_edge_ids.items()
    }


def mark_node_execution_running(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    *,
    started_at_epoch_ms: float = 0.0,
) -> None:
    normalized_node_id = str(node_id or "").strip()
    if not normalized_node_id:
        return
    normalized_workspace_id = self._normalize_node_execution_workspace_id(workspace_id)
    if not normalized_workspace_id:
        return
    resolved_started_at_epoch_ms = _coerce_nonnegative_timing_ms(started_at_epoch_ms)
    if resolved_started_at_epoch_ms <= 0.0:
        resolved_started_at_epoch_ms = _current_epoch_ms()
    state = self.run_state
    changed = False
    if state.node_execution_workspace_id != normalized_workspace_id:
        state.node_execution_workspace_id = normalized_workspace_id
        state.running_node_ids.clear()
        state.completed_node_ids.clear()
        state.running_node_started_at_epoch_ms_by_node_id.clear()
        changed = True
    if normalized_node_id in state.completed_node_ids:
        state.completed_node_ids.discard(normalized_node_id)
        changed = True
    if normalized_node_id not in state.running_node_ids:
        state.running_node_ids.add(normalized_node_id)
        changed = True
    if (
        state.running_node_started_at_epoch_ms_by_node_id.get(normalized_node_id)
        != resolved_started_at_epoch_ms
    ):
        state.running_node_started_at_epoch_ms_by_node_id[normalized_node_id] = resolved_started_at_epoch_ms
        changed = True
    if changed:
        self._commit_node_execution_state_change()


def mark_node_execution_completed(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    *,
    elapsed_ms: float = 0.0,
) -> None:
    normalized_node_id = str(node_id or "").strip()
    if not normalized_node_id:
        return
    normalized_workspace_id = self._normalize_node_execution_workspace_id(workspace_id)
    if not normalized_workspace_id:
        return
    state = self.run_state
    changed = False
    if state.node_execution_workspace_id != normalized_workspace_id:
        state.node_execution_workspace_id = normalized_workspace_id
        state.running_node_ids.clear()
        state.completed_node_ids.clear()
        state.running_node_started_at_epoch_ms_by_node_id.clear()
        changed = True
    started_at_lookup = state.running_node_started_at_epoch_ms_by_node_id
    had_started_at = normalized_node_id in started_at_lookup
    started_at_epoch_ms = started_at_lookup.pop(normalized_node_id, 0.0)
    if had_started_at:
        changed = True
    if normalized_node_id in state.running_node_ids:
        state.running_node_ids.discard(normalized_node_id)
        changed = True
    if normalized_node_id not in state.completed_node_ids:
        state.completed_node_ids.add(normalized_node_id)
        changed = True
    worker_elapsed_ms = _coerce_nonnegative_timing_ms(elapsed_ms)
    should_cache_elapsed = False
    resolved_elapsed_ms = 0.0
    if worker_elapsed_ms > 0.0:
        resolved_elapsed_ms = worker_elapsed_ms
        should_cache_elapsed = True
    elif started_at_epoch_ms > 0.0:
        resolved_elapsed_ms = max(0.0, _current_epoch_ms() - started_at_epoch_ms)
        should_cache_elapsed = True
    if should_cache_elapsed:
        workspace_cache = state.cached_node_elapsed_ms_by_workspace_id.setdefault(
            normalized_workspace_id,
            {},
        )
        if workspace_cache.get(normalized_node_id) != resolved_elapsed_ms:
            workspace_cache[normalized_node_id] = resolved_elapsed_ms
            changed = True
    if changed:
        self._commit_node_execution_state_change()


def invalidate_cached_node_elapsed_for_history_action(
    self: "ShellWindow",
    workspace_id: str,
    action_type: str,
    *,
    before_snapshot: object | None = None,
    after_snapshot: object | None = None,
) -> bool:
    normalized_workspace_id = str(workspace_id or "").strip()
    if not normalized_workspace_id:
        return False
    if not history_action_invalidates_persistent_node_elapsed(
        action_type,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    ):
        return False
    state = self.run_state
    changed = False
    if (
        state.node_execution_workspace_id == normalized_workspace_id
        and state.running_node_started_at_epoch_ms_by_node_id
    ):
        state.running_node_started_at_epoch_ms_by_node_id.clear()
        changed = True
    if normalized_workspace_id in state.cached_node_elapsed_ms_by_workspace_id:
        state.cached_node_elapsed_ms_by_workspace_id.pop(normalized_workspace_id, None)
        changed = True
    if changed:
        self._commit_node_execution_state_change()
    return changed


def clear_execution_edge_progress_state(self: "ShellWindow") -> None:
    if self._clear_execution_edge_progress_state_fields():
        self._commit_node_execution_state_change()


def seed_execution_edge_progress_state(
    self: "ShellWindow",
    *,
    run_id: str,
    workspace_id: str,
    runtime_snapshot: Any,
) -> None:
    normalized_run_id = str(run_id or "").strip()
    normalized_workspace_id, edge_index = self._build_execution_edge_progress_index(
        workspace_id=workspace_id,
        runtime_snapshot=runtime_snapshot,
    )
    state = self.run_state
    changed = self._clear_execution_edge_progress_state_fields()
    if state.execution_edge_run_id != normalized_run_id:
        state.execution_edge_run_id = normalized_run_id
        changed = True
    if state.execution_edge_workspace_id != normalized_workspace_id:
        state.execution_edge_workspace_id = normalized_workspace_id
        changed = True
    if state.execution_edge_ids_by_source_node_id != edge_index:
        state.execution_edge_ids_by_source_node_id = edge_index
        changed = True
    if changed:
        self._commit_node_execution_state_change()


def execution_edge_ids_for_source_port_kind(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    source_port_kind: str,
) -> tuple[str, ...]:
    normalized_node_id = str(node_id or "").strip()
    normalized_port_kind = str(source_port_kind or "").strip().lower()
    if not normalized_node_id or normalized_port_kind not in _EXECUTION_EDGE_PORT_KINDS:
        return tuple()
    normalized_workspace_id = self._normalize_execution_edge_workspace_id(workspace_id)
    state = self.run_state
    if not normalized_workspace_id or state.execution_edge_workspace_id != normalized_workspace_id:
        return tuple()
    node_edge_ids = state.execution_edge_ids_by_source_node_id.get(normalized_node_id, {})
    return tuple(node_edge_ids.get(normalized_port_kind, ()))


def mark_execution_edges_progressed(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    source_port_kinds: Iterable[str] | None = None,
) -> None:
    normalized_node_id = str(node_id or "").strip()
    if not normalized_node_id:
        return
    normalized_workspace_id = self._normalize_execution_edge_workspace_id(workspace_id)
    state = self.run_state
    if not normalized_workspace_id or state.execution_edge_workspace_id != normalized_workspace_id:
        return
    node_edge_ids = state.execution_edge_ids_by_source_node_id.get(normalized_node_id)
    if not node_edge_ids:
        return
    if source_port_kinds is None:
        requested_port_kinds = tuple(node_edge_ids)
    else:
        requested_port_kinds = tuple(
            normalized_kind
            for normalized_kind in (
                str(source_port_kind or "").strip().lower()
                for source_port_kind in source_port_kinds
            )
            if normalized_kind in _EXECUTION_EDGE_PORT_KINDS
        )
    changed = False
    for port_kind in requested_port_kinds:
        for edge_id in node_edge_ids.get(port_kind, ()):
            if edge_id in state.progressed_execution_edge_ids:
                continue
            state.progressed_execution_edge_ids.add(edge_id)
            changed = True
    if changed:
        self._commit_node_execution_state_change()


def clear_node_execution_visualization_state(self: "ShellWindow") -> None:
    state = self.run_state
    changed = False
    if (
        state.node_execution_workspace_id
        or state.running_node_ids
        or state.completed_node_ids
        or state.running_node_started_at_epoch_ms_by_node_id
    ):
        state.node_execution_workspace_id = ""
        state.running_node_ids.clear()
        state.completed_node_ids.clear()
        state.running_node_started_at_epoch_ms_by_node_id.clear()
        changed = True
    if self._clear_execution_edge_progress_state_fields():
        changed = True
    if changed:
        self._commit_node_execution_state_change()


def set_run_failure_focus(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    *,
    node_title: str = "",
) -> None:
    normalized_workspace_id = str(workspace_id or "").strip()
    normalized_node_id = str(node_id or "").strip()
    normalized_node_title = str(node_title or "").strip()
    state = self.run_state
    if (
        state.failed_workspace_id == normalized_workspace_id
        and state.failed_node_id == normalized_node_id
        and state.failed_node_title == normalized_node_title
    ):
        state.failure_focus_revision += 1
        self.run_failure_changed.emit()
        return
    state.failed_workspace_id = normalized_workspace_id
    state.failed_node_id = normalized_node_id
    state.failed_node_title = normalized_node_title
    state.failure_focus_revision += 1
    self.run_failure_changed.emit()


def clear_run_failure_focus(self: "ShellWindow") -> None:
    state = self.run_state
    if not (state.failed_workspace_id or state.failed_node_id or state.failed_node_title):
        return
    state.failed_workspace_id = ""
    state.failed_node_id = ""
    state.failed_node_title = ""
    self.run_failure_changed.emit()


def _apply_graph_cursor(self: "ShellWindow", cursor_shape: Qt.CursorShape) -> None:
    self.shell_host_presenter.apply_graph_cursor(cursor_shape)


@pyqtSlot(int)
def set_graph_cursor_shape(self: "ShellWindow", cursor_shape: int) -> None:
    self.shell_host_presenter.set_graph_cursor_shape(cursor_shape)


@pyqtSlot()
def clear_graph_cursor_shape(self: "ShellWindow") -> None:
    self.shell_host_presenter.clear_graph_cursor_shape()


def _apply_theme(self: "ShellWindow", theme_id: Any) -> str:
    return self.shell_host_presenter.apply_theme(theme_id)


def preview_graph_theme_settings(self: "ShellWindow", graph_theme_settings: Any) -> str:
    return self.shell_host_presenter.preview_graph_theme_settings(graph_theme_settings)


def apply_graphics_preferences(self: "ShellWindow", graphics: Any) -> dict[str, Any]:
    previous_show_port_labels = bool(
        getattr(getattr(self, "workspace_ui_state", None), "show_port_labels", True)
    )
    resolved = self.shell_workspace_presenter.apply_graphics_preferences(graphics)
    canvas = resolved.get("canvas", {}) if isinstance(resolved, dict) else {}
    current_show_port_labels = bool(canvas.get("show_port_labels", previous_show_port_labels))
    self._sync_graphics_show_port_labels_action(current_show_port_labels)
    if previous_show_port_labels != current_show_port_labels:
        self._refresh_active_workspace_scene_payload()
    return resolved


@pyqtSlot()
def request_run_workflow(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_run_workflow()


@pyqtSlot()
def request_toggle_run_pause(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_toggle_run_pause()


@pyqtSlot()
def request_stop_workflow(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_stop_workflow()


@pyqtSlot(result=bool)
def request_toggle_snap_to_grid(self: "ShellWindow") -> bool:
    self.set_snap_to_grid_enabled(not self.search_scope_state.snap_to_grid_enabled)
    return bool(self.search_scope_state.snap_to_grid_enabled)


@pyqtSlot(str, result=bool)
def request_edit_passive_node_style(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.shell_host_presenter.request_edit_passive_node_style(node_id))


@pyqtSlot(str, result=bool)
def request_reset_passive_node_style(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.shell_host_presenter.request_reset_passive_node_style(node_id))


@pyqtSlot(str, result=bool)
def request_copy_passive_node_style(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.shell_host_presenter.request_copy_passive_node_style(node_id))


@pyqtSlot(str, result=bool)
def request_paste_passive_node_style(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.shell_host_presenter.request_paste_passive_node_style(node_id))


@pyqtSlot(str, result=bool)
def request_edit_flow_edge_style(self: "ShellWindow", edge_id: str) -> bool:
    return bool(self.shell_host_presenter.request_edit_flow_edge_style(edge_id))


@pyqtSlot(str, result=bool)
def request_edit_flow_edge_label(self: "ShellWindow", edge_id: str) -> bool:
    return bool(self.shell_host_presenter.request_edit_flow_edge_label(edge_id))


@pyqtSlot(str, result=bool)
def request_reset_flow_edge_style(self: "ShellWindow", edge_id: str) -> bool:
    return bool(self.shell_host_presenter.request_reset_flow_edge_style(edge_id))


@pyqtSlot(str, result=bool)
def request_copy_flow_edge_style(self: "ShellWindow", edge_id: str) -> bool:
    return bool(self.shell_host_presenter.request_copy_flow_edge_style(edge_id))


@pyqtSlot(str, result=bool)
def request_paste_flow_edge_style(self: "ShellWindow", edge_id: str) -> bool:
    return bool(self.shell_host_presenter.request_paste_flow_edge_style(edge_id))


def _project_passive_style_presets(self: "ShellWindow") -> dict[str, list[dict[str, Any]]]:
    return self.shell_host_presenter._project_passive_style_presets()


def _set_project_passive_style_presets(
    self: "ShellWindow",
    *,
    node_presets: Any = _UNSET,
    edge_presets: Any = _UNSET,
) -> None:
    self.shell_host_presenter._set_project_passive_style_presets(
        node_presets=node_presets,
        edge_presets=edge_presets,
    )


def edit_passive_node_style(self: "ShellWindow", node_id: str) -> dict[str, Any] | None:
    return self.shell_host_presenter.edit_passive_node_style(node_id)


def edit_flow_edge_style(self: "ShellWindow", edge_id: str) -> dict[str, Any] | None:
    return self.shell_host_presenter.edit_flow_edge_style(edge_id)


def _write_style_clipboard(self: "ShellWindow", *, kind: str, style: dict[str, Any]) -> None:
    self.shell_host_presenter._write_style_clipboard(kind=kind, style=style)


def _read_style_clipboard(self: "ShellWindow", *, kind: str) -> dict[str, Any] | None:
    return self.shell_host_presenter._read_style_clipboard(kind=kind)


def _normalize_style_clipboard_payload(
    self: "ShellWindow",
    payload: Any,
    *,
    kind: str,
) -> dict[str, Any] | None:
    return self.shell_host_presenter._normalize_style_clipboard_payload(payload, kind=kind)


def _focus_failed_node(self: "ShellWindow", workspace_id, node_id, error):
    return self.workspace_library_controller.focus_failed_node(workspace_id, node_id, error)


def _run_workflow(self: "ShellWindow"):
    return self.run_controller.run_workflow()


def _toggle_pause_resume(self: "ShellWindow"):
    return self.run_controller.toggle_pause_resume()


def _pause_workflow(self: "ShellWindow"):
    return self.run_controller.pause_workflow()


def _resume_workflow(self: "ShellWindow"):
    return self.run_controller.resume_workflow()


def _stop_workflow(self: "ShellWindow"):
    return self.run_controller.stop_workflow()


def _handle_execution_event(self: "ShellWindow", event):
    return self.run_controller.handle_execution_event(event)


def _clear_active_run(self: "ShellWindow"):
    return self.run_controller.clear_active_run()


def _set_run_ui_state(
    self: "ShellWindow",
    state,
    details,
    running,
    queued,
    done,
    failed,
    *,
    clear_run=False,
):
    return self.run_controller.set_run_ui_state(
        state,
        details,
        running,
        queued,
        done,
        failed,
        clear_run=clear_run,
    )


def _update_run_actions(self: "ShellWindow"):
    return self.run_controller.update_run_actions()


@pyqtSlot()
@pyqtSlot(bool)
def show_workflow_settings_dialog(self: "ShellWindow", _checked: bool = False) -> None:
    self.shell_workspace_presenter.show_workflow_settings_dialog(_checked)


@pyqtSlot()
@pyqtSlot(bool)
def show_graphics_settings_dialog(self: "ShellWindow", _checked: bool = False) -> None:
    self.shell_host_presenter.show_graphics_settings_dialog(_checked)


def edit_graph_theme_settings(
    self: "ShellWindow",
    graph_theme_settings: Any,
    *,
    enable_live_apply: bool = False,
) -> dict[str, Any] | None:
    return self.shell_host_presenter.edit_graph_theme_settings(
        graph_theme_settings,
        enable_live_apply=enable_live_apply,
    )


@pyqtSlot()
@pyqtSlot(bool)
def show_graph_theme_editor_dialog(self: "ShellWindow", _checked: bool = False) -> None:
    self.shell_host_presenter.show_graph_theme_editor_dialog(_checked)


@pyqtSlot()
@pyqtSlot(bool)
def set_script_editor_panel_visible(self: "ShellWindow", checked: bool | None = None) -> None:
    self.shell_workspace_presenter.set_script_editor_panel_visible(checked)


@pyqtSlot()
def _record_render_frame(self: "ShellWindow") -> None:
    self._frame_rate_sampler.record_frame()


def _update_metrics(self: "ShellWindow") -> None:
    self.shell_host_presenter.update_metrics()


def update_engine_status(
    self: "ShellWindow",
    state: Literal["ready", "running", "paused", "error"],
    details: str = "",
) -> None:
    self.shell_host_presenter.update_engine_status(state, details)


def update_job_counters(self: "ShellWindow", running: int, queued: int, done: int, failed: int) -> None:
    self.shell_host_presenter.update_job_counters(running, queued, done, failed)


def update_system_metrics(
    self: "ShellWindow",
    cpu_percent: float,
    ram_used_gb: float,
    ram_total_gb: float,
    fps: float | None = None,
) -> None:
    self.shell_host_presenter.update_system_metrics(
        cpu_percent,
        ram_used_gb,
        ram_total_gb,
        fps=0.0 if fps is None else fps,
    )


def update_notification_counters(self: "ShellWindow", warnings: int, errors: int) -> None:
    self.shell_host_presenter.update_notification_counters(warnings, errors)


_PROPERTY_EXPORTS = set()
_FORCE_BIND_NAMES = {'_set_project_passive_style_presets', '_set_run_ui_state'}
_PRIVATE_EXPORT_NAMES = {"_exported_names", "_should_bind"}


def _exported_names() -> list[str]:
    names = set(_PROPERTY_EXPORTS)
    for name, value in globals().items():
        if name in _PRIVATE_EXPORT_NAMES:
            continue
        if not inspect.isfunction(value) or getattr(value, "__module__", None) != __name__:
            continue
        if name.startswith("_get_"):
            continue
        if name.startswith("_set_") and name not in _FORCE_BIND_NAMES:
            continue
        names.add(name)
    return sorted(names)


def _should_bind(name: str, value: object) -> bool:
    if name in _FORCE_BIND_NAMES:
        return True
    if name.startswith("_qt_") or name.startswith("_get_") or name.startswith("_set_"):
        return False
    return inspect.isfunction(value) or isinstance(value, property)


__all__ = _exported_names()
WINDOW_STATE_FACADE_BINDINGS = {
    name: globals()[name]
    for name in __all__
    if _should_bind(name, globals()[name])
}
