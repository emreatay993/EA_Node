from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Iterable, Literal

from PyQt6.QtCore import Qt, pyqtSlot

from ea_node_editor.developer_mode import developer_mode_capability_enabled

if TYPE_CHECKING:
    from ea_node_editor.runtime_contracts.settled_results import RootExecutionError
    from ea_node_editor.ui.shell.window import ShellWindow

logger = logging.getLogger(__name__)

_UNSET = object()


def _coerce_nonnegative_timing_ms(value: object) -> float:
    from ea_node_editor.ui.shell.controllers.run_controller import RunController

    return RunController._coerce_nonnegative_timing_ms(value)


def _current_epoch_ms() -> float:
    from ea_node_editor.ui.shell.controllers.run_controller import RunController

    return RunController._current_epoch_ms()


class ShellWindowRunAndStyleStateMixin:
    @pyqtSlot(bool)
    def set_snap_to_grid_enabled(self: "ShellWindow", enabled: bool) -> None:
        self.graph_canvas_presenter.set_snap_to_grid_enabled(enabled)

    @pyqtSlot(bool)
    def set_interact_with_locked_objects(self: "ShellWindow", enabled: bool) -> None:
        self.scene.set_interact_with_locked_objects(bool(enabled))

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self: "ShellWindow", expanded: bool) -> None:
        self.graph_canvas_presenter.set_graphics_minimap_expanded(expanded)

    @pyqtSlot(bool)
    def set_graphics_show_port_labels(self: "ShellWindow", show_port_labels: bool) -> None:
        self.app_preferences_controller.set_graphics_show_port_labels(show_port_labels, host=self)

    @pyqtSlot("QVariantMap")
    def set_graphics_tooltip_categories(self: "ShellWindow", categories: dict[str, Any]) -> None:
        self.app_preferences_controller.set_graphics_tooltip_categories(categories, host=self)

    @pyqtSlot(str, bool)
    def set_graphics_tooltip_category_enabled(self: "ShellWindow", category: str, enabled: bool) -> None:
        self.app_preferences_controller.set_graphics_tooltip_category_enabled(category, enabled, host=self)

    @pyqtSlot(str, result=bool)
    def tooltip_category_enabled(self: "ShellWindow", category: str) -> bool:
        return bool(self.shell_workspace_presenter.tooltip_category_enabled(category))

    def _sync_graphics_show_port_labels_action(self: "ShellWindow", show_port_labels: bool) -> None:
        self.shell_host_presenter.sync_graphics_show_port_labels_action(show_port_labels)

    def _sync_general_help_tooltips_action(self: "ShellWindow", enabled: bool) -> None:
        self.shell_host_presenter.sync_general_help_tooltips_action(enabled)

    def _refresh_active_workspace_scene_payload(self: "ShellWindow") -> None:
        self.shell_host_presenter.refresh_active_workspace_scene_payload()

    @pyqtSlot(str)
    def set_graphics_floating_toolbar_style(self: "ShellWindow", style: str) -> None:
        self.app_preferences_controller.set_graphics_floating_toolbar_style(style, host=self)

    @pyqtSlot(str)
    def set_graphics_floating_toolbar_size(self: "ShellWindow", size: str) -> None:
        self.app_preferences_controller.set_graphics_floating_toolbar_size(size, host=self)

    @pyqtSlot(str)
    def set_graphics_selection_toolbar_mode(self: "ShellWindow", mode: str) -> None:
        self.app_preferences_controller.set_graphics_selection_toolbar_mode(mode, host=self)

    @pyqtSlot(str)
    def set_graphics_selection_toolbar_minimal_menu_trigger(
        self: "ShellWindow",
        trigger: str,
    ) -> None:
        self.app_preferences_controller.set_graphics_selection_toolbar_minimal_menu_trigger(
            trigger,
            host=self,
        )

    @pyqtSlot("QVariantMap")
    def set_graphics_expand_collision_avoidance(self: "ShellWindow", settings: dict[str, Any]) -> None:
        self.app_preferences_controller.set_graphics_expand_collision_avoidance(settings, host=self)

    def _normalize_node_execution_workspace_id(self: "ShellWindow", workspace_id: str) -> str:
        return self.run_controller.normalize_node_execution_workspace_id(workspace_id)

    def _commit_node_execution_state_change(self: "ShellWindow") -> None:
        self.run_controller.commit_node_execution_state_change()

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

    def mark_node_execution_settled(
        self: "ShellWindow",
        workspace_id: str,
        node_id: str,
        *,
        status: str = "completed",
        errors: tuple[RootExecutionError, ...] = (),
        elapsed_ms: float = 0.0,
        warning: bool = False,
    ) -> None:
        self.run_controller.mark_node_execution_settled(
            workspace_id,
            node_id,
            status=status,
            errors=errors,
            elapsed_ms=elapsed_ms,
            warning=warning,
        )

    def invalidate_solution_for_history_action(
        self: "ShellWindow",
        workspace_id: str,
        action_type: str,
        *,
        before_snapshot: object | None = None,
        after_snapshot: object | None = None,
    ) -> bool:
        return bool(
            self.run_controller.invalidate_solution_for_history_action(
                workspace_id,
                action_type,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
            )
        )

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
    def request_propagate_passive_node_style(self: "ShellWindow", node_id: str) -> bool:
        return bool(self.shell_host_presenter.request_propagate_passive_node_style(node_id))

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

    def _focus_failed_node(self: "ShellWindow", workspace_id, node_id):
        return self.workspace_library_controller.focus_failed_node(workspace_id, node_id)

    @staticmethod
    def _first_status_node_id(node_ids: Iterable[Any]) -> str:
        for node_id in sorted(str(value or "").strip() for value in node_ids):
            if node_id:
                return node_id
        return ""

    @pyqtSlot(str, result=bool)
    def request_focus_status_execution_node(self: "ShellWindow", target: str = "auto") -> bool:
        normalized_target = str(target or "auto").strip().lower()
        run_state = self.run_state

        if normalized_target in {"auto", "failed", "failure", "error", "errored"}:
            failed_workspace_id = str(getattr(run_state, "failed_workspace_id", "") or "").strip()
            failed_node_id = str(getattr(run_state, "failed_node_id", "") or "").strip()
            if failed_workspace_id and failed_node_id:
                self.workspace_library_controller.focus_failed_node(failed_workspace_id, failed_node_id)
                return True
            if normalized_target != "auto":
                return False

        execution_workspace_id = str(getattr(run_state, "node_execution_workspace_id", "") or "").strip()
        if not execution_workspace_id:
            execution_workspace_id = str(getattr(run_state, "active_run_workspace_id", "") or "").strip()
        if not execution_workspace_id:
            execution_workspace_id = str(self.workspace_manager.active_workspace_id() or "").strip()

        node_ids_by_target = {
            "running": getattr(run_state, "running_node_ids", set()),
            "run": getattr(run_state, "running_node_ids", set()),
            "warning": getattr(run_state, "warning_node_ids", set()),
            "warn": getattr(run_state, "warning_node_ids", set()),
            "completed": getattr(run_state, "completed_node_ids", set()),
            "done": getattr(run_state, "completed_node_ids", set()),
        }
        candidate_sets = (
            [node_ids_by_target.get(normalized_target, set())]
            if normalized_target != "auto"
            else [
                getattr(run_state, "running_node_ids", set()),
                getattr(run_state, "warning_node_ids", set()),
                getattr(run_state, "completed_node_ids", set()),
            ]
        )
        for node_ids in candidate_sets:
            node_id = self._first_status_node_id(node_ids)
            if not node_id:
                continue
            if self.workspace_library_controller.jump_to_graph_node(execution_workspace_id, node_id):
                return True
        return False

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
        try:
            return self.run_controller.handle_execution_event(event)
        except Exception:
            event_type = event.get("type", "") if isinstance(event, dict) else type(event).__name__
            logger.exception("Error handling execution event (%s); keeping the app alive.", event_type)
            return None

    def _toggle_developer_mode(self: "ShellWindow") -> None:
        if not developer_mode_capability_enabled():
            return
        active = not self.run_state.developer_mode_active
        self.run_state.developer_mode_active = active
        self.show_graph_hint(f"Developer mode {'ON' if active else 'OFF'}", 2400)

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

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_selected_run_settings_dialog(self: "ShellWindow", _checked: bool = False) -> None:
        self.shell_host_presenter.show_selected_run_settings_dialog(_checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_keyboard_mouse_reference_dialog(self: "ShellWindow", _checked: bool = False) -> None:
        self.shell_host_presenter.show_keyboard_mouse_reference_dialog(_checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_third_party_notices_dialog(self: "ShellWindow", _checked: bool = False) -> None:
        self.shell_host_presenter.show_third_party_notices_dialog(_checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_plugin_authoring_dialog(self: "ShellWindow", _checked: bool = False) -> None:
        self.plugin_authoring_controller.show_dialog()

    @pyqtSlot()
    @pyqtSlot(bool)
    def reload_plugins(self: "ShellWindow", _checked: bool = False) -> None:
        self.plugin_authoring_controller.reload_plugins()

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
        disk_read_mb_s: float = 0.0,
        disk_write_mb_s: float = 0.0,
        show_fps: bool = True,
    ) -> None:
        self.shell_host_presenter.update_system_metrics(
            cpu_percent,
            ram_used_gb,
            ram_total_gb,
            fps=0.0 if fps is None else fps,
            disk_read_mb_s=disk_read_mb_s,
            disk_write_mb_s=disk_write_mb_s,
            show_fps=show_fps,
        )

    def update_notification_counters(self: "ShellWindow", warnings: int, errors: int) -> None:
        self.shell_host_presenter.update_notification_counters(warnings, errors)


__all__ = [
    "ShellWindowRunAndStyleStateMixin",
]
