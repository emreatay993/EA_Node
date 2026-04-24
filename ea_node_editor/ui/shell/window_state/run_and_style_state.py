from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Iterable, Literal

from PyQt6.QtCore import Qt, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

_UNSET = object()


@pyqtSlot(bool)
def set_snap_to_grid_enabled(self: "ShellWindow", enabled: bool) -> None:
    self.graph_canvas_presenter.set_snap_to_grid_enabled(enabled)


@pyqtSlot(bool)
def set_graphics_minimap_expanded(self: "ShellWindow", expanded: bool) -> None:
    self.graph_canvas_presenter.set_graphics_minimap_expanded(expanded)


@pyqtSlot(bool)
def set_graphics_show_port_labels(self: "ShellWindow", show_port_labels: bool) -> None:
    self.app_preferences_controller.set_graphics_show_port_labels(show_port_labels, host=self)


@pyqtSlot(bool)
def set_graphics_show_tooltips(self: "ShellWindow", show_tooltips: bool) -> None:
    self.app_preferences_controller.set_graphics_show_tooltips(show_tooltips, host=self)


def _sync_graphics_show_port_labels_action(self: "ShellWindow", show_port_labels: bool) -> None:
    self.shell_host_presenter.sync_graphics_show_port_labels_action(show_port_labels)


def _sync_graphics_show_tooltips_action(self: "ShellWindow", show_tooltips: bool) -> None:
    self.shell_host_presenter.sync_graphics_show_tooltips_action(show_tooltips)


def _refresh_active_workspace_scene_payload(self: "ShellWindow") -> None:
    self.shell_host_presenter.refresh_active_workspace_scene_payload()


@pyqtSlot(str)
def set_graphics_performance_mode(self: "ShellWindow", mode: str) -> None:
    self.app_preferences_controller.set_graphics_performance_mode(mode, host=self)


@pyqtSlot(str)
def set_graphics_floating_toolbar_style(self: "ShellWindow", style: str) -> None:
    self.app_preferences_controller.set_graphics_floating_toolbar_style(style, host=self)


@pyqtSlot(str)
def set_graphics_floating_toolbar_size(self: "ShellWindow", size: str) -> None:
    self.app_preferences_controller.set_graphics_floating_toolbar_size(size, host=self)


@pyqtSlot("QVariantMap")
def set_graphics_expand_collision_avoidance(self: "ShellWindow", settings: dict[str, Any]) -> None:
    self.app_preferences_controller.set_graphics_expand_collision_avoidance(settings, host=self)


def _normalize_node_execution_workspace_id(self: "ShellWindow", workspace_id: str) -> str:
    return self.run_controller.normalize_node_execution_workspace_id(workspace_id)


def _normalize_execution_edge_workspace_id(self: "ShellWindow", workspace_id: str) -> str:
    return self.run_controller.normalize_execution_edge_workspace_id(workspace_id)


def _commit_node_execution_state_change(self: "ShellWindow") -> None:
    self.run_controller.commit_node_execution_state_change()


def _coerce_nonnegative_timing_ms(value: object) -> float:
    from ea_node_editor.ui.shell.controllers.run_controller import RunController

    return RunController._coerce_nonnegative_timing_ms(value)


def _current_epoch_ms() -> float:
    from ea_node_editor.ui.shell.controllers.run_controller import RunController

    return RunController._current_epoch_ms()


def _clear_execution_edge_progress_state_fields(self: "ShellWindow") -> bool:
    return self.run_controller._clear_execution_edge_progress_state_fields()


def _build_execution_edge_progress_index(
    self: "ShellWindow",
    *,
    workspace_id: str,
    runtime_snapshot: Any,
) -> tuple[str, dict[str, dict[str, tuple[str, ...]]]]:
    return self.run_controller.build_execution_edge_progress_index(
        workspace_id=workspace_id,
        runtime_snapshot=runtime_snapshot,
    )


def mark_node_execution_running(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    *,
    started_at_epoch_ms: float = 0.0,
) -> None:
    self.run_controller.mark_node_execution_running(
        workspace_id,
        node_id,
        started_at_epoch_ms=started_at_epoch_ms,
    )


def mark_node_execution_completed(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    *,
    elapsed_ms: float = 0.0,
) -> None:
    self.run_controller.mark_node_execution_completed(
        workspace_id,
        node_id,
        elapsed_ms=elapsed_ms,
    )


def invalidate_cached_node_elapsed_for_history_action(
    self: "ShellWindow",
    workspace_id: str,
    action_type: str,
    *,
    before_snapshot: object | None = None,
    after_snapshot: object | None = None,
) -> bool:
    return bool(
        self.run_controller.invalidate_cached_node_elapsed_for_history_action(
            workspace_id,
            action_type,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
    )


def clear_execution_edge_progress_state(self: "ShellWindow") -> None:
    self.run_controller.clear_execution_edge_progress_state()


def seed_execution_edge_progress_state(
    self: "ShellWindow",
    *,
    run_id: str,
    workspace_id: str,
    runtime_snapshot: Any,
) -> None:
    self.run_controller.seed_execution_edge_progress_state(
        run_id=run_id,
        workspace_id=workspace_id,
        runtime_snapshot=runtime_snapshot,
    )


def execution_edge_ids_for_source_port_kind(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    source_port_kind: str,
) -> tuple[str, ...]:
    return self.run_controller.execution_edge_ids_for_source_port_kind(
        workspace_id,
        node_id,
        source_port_kind,
    )


def mark_execution_edges_progressed(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    source_port_kinds: Iterable[str] | None = None,
) -> None:
    self.run_controller.mark_execution_edges_progressed(workspace_id, node_id, source_port_kinds)


def clear_node_execution_visualization_state(self: "ShellWindow") -> None:
    self.run_controller.clear_node_execution_visualization_state()


def set_run_failure_focus(
    self: "ShellWindow",
    workspace_id: str,
    node_id: str,
    *,
    node_title: str = "",
) -> None:
    self.run_controller.set_run_failure_focus(
        workspace_id,
        node_id,
        node_title=node_title,
    )


def clear_run_failure_focus(self: "ShellWindow") -> None:
    self.run_controller.clear_run_failure_focus()


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
    return self.shell_host_presenter.apply_graphics_preferences(graphics)


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
    return bool(self.graph_canvas_presenter.request_toggle_snap_to_grid())


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
_PRIVATE_EXPORT_NAMES = {
    "_coerce_nonnegative_timing_ms",
    "_current_epoch_ms",
    "_exported_names",
    "_should_bind",
}


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
