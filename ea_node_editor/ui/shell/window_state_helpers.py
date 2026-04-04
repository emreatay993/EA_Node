from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Literal

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QFileDialog, QInputDialog

from ea_node_editor.graph.file_issue_state import (
    EXTERNAL_LINK_MODE,
    MANAGED_COPY_MODE,
    preferred_repair_mode_for_value,
    repair_modes_for_node_property,
)
from ea_node_editor.ui.pdf_preview_provider import (
    describe_pdf_preview as build_pdf_preview_description,
)
from ea_node_editor.ui.shell.window_actions import (
    build_window_menu_bar,
    create_window_actions,
    format_recent_project_menu_label as format_recent_project_menu_label_value,
    refresh_recent_projects_menu as refresh_recent_projects_menu_entries,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


_UNSET = object()


def _get_project_path(self: "ShellWindow") -> str:
    return self.project_session_state.project_path


def _set_project_path(self: "ShellWindow", value: str) -> None:
    self.project_session_state.project_path = str(value)


project_path = property(_get_project_path, _set_project_path)


def _get_recent_project_paths(self: "ShellWindow") -> list[str]:
    return list(self.project_session_state.recent_project_paths)


def _set_recent_project_paths(self: "ShellWindow", value: list[str]) -> None:
    self.project_session_state.recent_project_paths = [str(path) for path in value]


recent_project_paths = property(_get_recent_project_paths, _set_recent_project_paths)


def _get_library_query(self: "ShellWindow") -> str:
    return self.library_filter_state.library_query


def _set_library_query(self: "ShellWindow", value: str) -> None:
    self.library_filter_state.library_query = str(value)


_library_query = property(_get_library_query, _set_library_query)


def _get_library_category(self: "ShellWindow") -> str:
    return self.library_filter_state.library_category


def _set_library_category(self: "ShellWindow", value: str) -> None:
    self.library_filter_state.library_category = str(value)


_library_category = property(_get_library_category, _set_library_category)


def _get_library_data_type(self: "ShellWindow") -> str:
    return self.library_filter_state.library_data_type


def _set_library_data_type(self: "ShellWindow", value: str) -> None:
    self.library_filter_state.library_data_type = str(value)


_library_data_type = property(_get_library_data_type, _set_library_data_type)


def _get_library_direction(self: "ShellWindow") -> str:
    return self.library_filter_state.library_direction


def _set_library_direction(self: "ShellWindow", value: str) -> None:
    self.library_filter_state.library_direction = str(value)


_library_direction = property(_get_library_direction, _set_library_direction)


def _get_active_run_id(self: "ShellWindow") -> str:
    return self.run_state.active_run_id


def _set_active_run_id(self: "ShellWindow", value: str) -> None:
    self.run_state.active_run_id = str(value)


_active_run_id = property(_get_active_run_id, _set_active_run_id)


def _get_active_run_workspace_id(self: "ShellWindow") -> str:
    return self.run_state.active_run_workspace_id


def _set_active_run_workspace_id(self: "ShellWindow", value: str) -> None:
    self.run_state.active_run_workspace_id = str(value)


_active_run_workspace_id = property(_get_active_run_workspace_id, _set_active_run_workspace_id)


def _get_engine_state_value(self: "ShellWindow") -> Literal["ready", "running", "paused", "error"]:
    return self.run_state.engine_state_value


def _set_engine_state_value(
    self: "ShellWindow",
    value: Literal["ready", "running", "paused", "error"] | str,
) -> None:
    normalized = str(value)
    if normalized not in {"ready", "running", "paused", "error"}:
        normalized = "ready"
    self.run_state.engine_state_value = normalized  # type: ignore[assignment]


_engine_state_value = property(_get_engine_state_value, _set_engine_state_value)


def _get_last_manual_save_ts(self: "ShellWindow") -> float:
    return self.project_session_state.last_manual_save_ts


def _set_last_manual_save_ts(self: "ShellWindow", value: float) -> None:
    self.project_session_state.last_manual_save_ts = float(value)


_last_manual_save_ts = property(_get_last_manual_save_ts, _set_last_manual_save_ts)


def _get_last_autosave_fingerprint(self: "ShellWindow") -> str:
    return self.project_session_state.last_autosave_fingerprint


def _set_last_autosave_fingerprint(self: "ShellWindow", value: str) -> None:
    self.project_session_state.last_autosave_fingerprint = str(value)


_last_autosave_fingerprint = property(_get_last_autosave_fingerprint, _set_last_autosave_fingerprint)


def _get_autosave_recovery_deferred(self: "ShellWindow") -> bool:
    return self.project_session_state.autosave_recovery_deferred


def _set_autosave_recovery_deferred(self: "ShellWindow", value: bool) -> None:
    self.project_session_state.autosave_recovery_deferred = bool(value)


_autosave_recovery_deferred = property(_get_autosave_recovery_deferred, _set_autosave_recovery_deferred)


def _qt_project_display_name(self: "ShellWindow") -> str:
    return self.shell_workspace_presenter.project_display_name


def _registry_library_items(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_library_presenter._registry_library_items()


def _combined_library_items(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_library_presenter._combined_library_items()


def _library_item_matches_filters(
    self: "ShellWindow",
    item: dict[str, Any],
    *,
    query: str,
    category: str,
    data_type: str,
    direction: str,
) -> bool:
    return self.shell_library_presenter._library_item_matches_filters(
        item,
        query=query,
        category=category,
        data_type=data_type,
        direction=direction,
    )


def _qt_filtered_node_library_items(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_library_presenter.filtered_node_library_items


def _qt_grouped_node_library_items(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_library_presenter.grouped_node_library_items


def _qt_library_category_options(self: "ShellWindow") -> list[dict[str, str]]:
    return self.shell_library_presenter.library_category_options


def _qt_library_direction_options(self: "ShellWindow") -> list[dict[str, str]]:
    return self.shell_library_presenter.library_direction_options


def _qt_library_data_type_options(self: "ShellWindow") -> list[dict[str, str]]:
    return self.shell_library_presenter.library_data_type_options


def _qt_pin_data_type_options(self: "ShellWindow") -> list[str]:
    return self.shell_inspector_presenter.pin_data_type_options


def _qt_graph_search_open(self: "ShellWindow") -> bool:
    return self.shell_library_presenter.graph_search_open


def _qt_graph_search_query(self: "ShellWindow") -> str:
    return self.shell_library_presenter.graph_search_query


def _qt_graph_search_enabled_scopes(self: "ShellWindow") -> list[str]:
    return self.shell_library_presenter.graph_search_enabled_scopes


def _qt_graph_search_results(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_library_presenter.graph_search_results


def _qt_graph_search_highlight_index(self: "ShellWindow") -> int:
    return self.shell_library_presenter.graph_search_highlight_index


def _qt_connection_quick_insert_open(self: "ShellWindow") -> bool:
    return self.shell_library_presenter.connection_quick_insert_open


def _qt_connection_quick_insert_query(self: "ShellWindow") -> str:
    return self.shell_library_presenter.connection_quick_insert_query


def _qt_connection_quick_insert_results(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_library_presenter.connection_quick_insert_results


def _qt_connection_quick_insert_highlight_index(self: "ShellWindow") -> int:
    return self.shell_library_presenter.connection_quick_insert_highlight_index


def _qt_connection_quick_insert_overlay_x(self: "ShellWindow") -> float:
    return self.shell_library_presenter.connection_quick_insert_overlay_x


def _qt_connection_quick_insert_overlay_y(self: "ShellWindow") -> float:
    return self.shell_library_presenter.connection_quick_insert_overlay_y


def _qt_connection_quick_insert_source_summary(self: "ShellWindow") -> str:
    return self.shell_library_presenter.connection_quick_insert_source_summary


def _qt_connection_quick_insert_is_canvas_mode(self: "ShellWindow") -> bool:
    return self.shell_library_presenter.connection_quick_insert_is_canvas_mode


def _qt_graph_hint_message(self: "ShellWindow") -> str:
    return self.shell_library_presenter.graph_hint_message


def _qt_graph_hint_visible(self: "ShellWindow") -> bool:
    return self.shell_library_presenter.graph_hint_visible


def _qt_graphics_show_grid(self: "ShellWindow") -> bool:
    return self.graph_canvas_presenter.graphics_show_grid


def _qt_graphics_grid_style(self: "ShellWindow") -> str:
    return self.graph_canvas_presenter.graphics_grid_style


def _qt_graphics_edge_crossing_style(self: "ShellWindow") -> str:
    return self.shell_workspace_presenter.graphics_edge_crossing_style


def _qt_graphics_show_minimap(self: "ShellWindow") -> bool:
    return self.graph_canvas_presenter.graphics_show_minimap


def _qt_graphics_show_port_labels(self: "ShellWindow") -> bool:
    return self.graph_canvas_presenter.graphics_show_port_labels


def _qt_graphics_minimap_expanded(self: "ShellWindow") -> bool:
    return self.graph_canvas_presenter.graphics_minimap_expanded


def _qt_graphics_node_shadow(self: "ShellWindow") -> bool:
    return self.graph_canvas_presenter.graphics_node_shadow


def _qt_graphics_shadow_strength(self: "ShellWindow") -> int:
    return self.graph_canvas_presenter.graphics_shadow_strength


def _qt_graphics_shadow_softness(self: "ShellWindow") -> int:
    return self.graph_canvas_presenter.graphics_shadow_softness


def _qt_graphics_shadow_offset(self: "ShellWindow") -> int:
    return self.graph_canvas_presenter.graphics_shadow_offset


def _qt_graphics_performance_mode(self: "ShellWindow") -> str:
    return self.shell_workspace_presenter.graphics_performance_mode


def _qt_graphics_tab_strip_density(self: "ShellWindow") -> str:
    return self.shell_workspace_presenter.graphics_tab_strip_density


def _qt_active_theme_id(self: "ShellWindow") -> str:
    return self.shell_workspace_presenter.active_theme_id


def _qt_snap_to_grid_enabled(self: "ShellWindow") -> bool:
    return self.graph_canvas_presenter.snap_to_grid_enabled


def _qt_snap_grid_size(self: "ShellWindow") -> float:
    return self.graph_canvas_presenter.snap_grid_size


def _qt_active_workspace_id(self: "ShellWindow") -> str:
    return self.shell_workspace_presenter.active_workspace_id


def _qt_active_workspace_name(self: "ShellWindow") -> str:
    return self.shell_workspace_presenter.active_workspace_name


def _qt_active_view_name(self: "ShellWindow") -> str:
    return self.shell_workspace_presenter.active_view_name


def _qt_active_view_items(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_workspace_presenter.active_view_items


def _qt_active_scope_breadcrumb_items(self: "ShellWindow") -> list[dict[str, str]]:
    return self.shell_workspace_presenter.active_scope_breadcrumb_items


def _selected_node_header_data(self: "ShellWindow") -> dict[str, Any]:
    return self.shell_inspector_presenter._selected_node_header_data()


def _qt_selected_node_title(self: "ShellWindow") -> str:
    return self.shell_inspector_presenter.selected_node_title


def _qt_selected_node_subtitle(self: "ShellWindow") -> str:
    return self.shell_inspector_presenter.selected_node_subtitle


def _qt_selected_node_header_items(self: "ShellWindow") -> list[dict[str, str]]:
    return self.shell_inspector_presenter.selected_node_header_items


def _qt_selected_node_summary(self: "ShellWindow") -> str:
    return self.shell_inspector_presenter.selected_node_summary


def _qt_has_selected_node(self: "ShellWindow") -> bool:
    return self.shell_inspector_presenter.has_selected_node


def _qt_selected_node_collapsible(self: "ShellWindow") -> bool:
    return self.shell_inspector_presenter.selected_node_collapsible


def _qt_selected_node_collapsed(self: "ShellWindow") -> bool:
    return self.shell_inspector_presenter.selected_node_collapsed


def _qt_selected_node_is_subnode_pin(self: "ShellWindow") -> bool:
    return self.shell_inspector_presenter.selected_node_is_subnode_pin


def _qt_selected_node_is_subnode_shell(self: "ShellWindow") -> bool:
    return self.shell_inspector_presenter.selected_node_is_subnode_shell


def _qt_can_publish_custom_workflow_from_scope(self: "ShellWindow") -> bool:
    return self.shell_workspace_presenter.can_publish_custom_workflow_from_scope


def _qt_selected_node_property_items(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_inspector_presenter.selected_node_property_items


def _node_property_spec(self: "ShellWindow", node_id: str, key: str):
    return self.shell_inspector_presenter._node_property_spec(node_id, key)


def _selected_node_property_spec(self: "ShellWindow", key: str):
    return self.shell_inspector_presenter._selected_node_property_spec(key)


def _path_dialog_start_path(self: "ShellWindow", current_path: str) -> str:
    return self.shell_inspector_presenter._path_dialog_start_path(current_path)


def _qt_selected_node_port_items(self: "ShellWindow") -> list[dict[str, Any]]:
    return self.shell_inspector_presenter.selected_node_port_items


def _create_actions(self: "ShellWindow") -> None:
    create_window_actions(self)


def _build_menu_bar(self: "ShellWindow") -> None:
    build_window_menu_bar(self)


def _refresh_recent_projects_menu(self: "ShellWindow") -> None:
    refresh_recent_projects_menu_entries(self)


def _set_graph_search_state(
    self: "ShellWindow",
    *,
    open_: bool | None = None,
    query: str | None = None,
    enabled_scopes: list[str] | None = None,
    results: list[dict[str, Any]] | None = None,
    highlight_index: int | None = None,
) -> None:
    self.shell_library_presenter._set_graph_search_state(
        open_=open_,
        query=query,
        enabled_scopes=enabled_scopes,
        results=results,
        highlight_index=highlight_index,
    )


def _refresh_graph_search_results(self: "ShellWindow", query: str) -> None:
    self.shell_library_presenter._refresh_graph_search_results(query)


def _set_connection_quick_insert_state(
    self: "ShellWindow",
    *,
    open_: bool | None = None,
    query: str | None = None,
    results: list[dict[str, Any]] | None = None,
    highlight_index: int | None = None,
    context: dict[str, Any] | None | object = _UNSET,
) -> None:
    self.shell_library_presenter._set_connection_quick_insert_state(
        open_=open_,
        query=query,
        results=results,
        highlight_index=highlight_index,
        context=context,
    )


def _connection_quick_insert_context_for_port(
    self: "ShellWindow",
    node_id: str,
    port_key: str,
) -> dict[str, Any] | None:
    return self.shell_library_presenter._connection_quick_insert_context_for_port(node_id, port_key)


def _refresh_connection_quick_insert_results(self: "ShellWindow", query: str) -> None:
    self.shell_library_presenter._refresh_connection_quick_insert_results(query)


def _active_scope_camera_key(
    self: "ShellWindow",
    scope_path: tuple[str, ...] | None = None,
) -> tuple[str, str, tuple[str, ...]] | None:
    return self.search_scope_controller.active_scope_camera_key(scope_path)


def _remember_scope_camera(self: "ShellWindow", scope_path: tuple[str, ...] | None = None) -> None:
    self.search_scope_controller.remember_scope_camera(scope_path)


def _restore_scope_camera(self: "ShellWindow", scope_path: tuple[str, ...] | None = None) -> bool:
    return bool(self.search_scope_controller.restore_scope_camera(scope_path))


def _navigate_scope(self: "ShellWindow", navigate_fn: Callable[[], bool]) -> bool:
    return bool(self.search_scope_controller.navigate_scope(navigate_fn))


def _on_scene_scope_changed(self: "ShellWindow") -> None:
    self.request_close_connection_quick_insert()
    self.workspace_state_changed.emit()
    self.selected_node_changed.emit()


def _on_project_meta_changed(self: "ShellWindow") -> None:
    self.selected_node_changed.emit()
    self._refresh_active_workspace_scene_payload()


@pyqtSlot(str)
def set_library_query(self: "ShellWindow", query: str) -> None:
    self.shell_library_presenter.set_library_query(query)


@pyqtSlot(str)
def set_library_category(self: "ShellWindow", category: str) -> None:
    self.shell_library_presenter.set_library_category(category)


@pyqtSlot(str)
def set_library_data_type(self: "ShellWindow", data_type: str) -> None:
    self.shell_library_presenter.set_library_data_type(data_type)


@pyqtSlot(str)
def set_library_direction(self: "ShellWindow", direction: str) -> None:
    self.shell_library_presenter.set_library_direction(direction)


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


@pyqtSlot(str)
@pyqtSlot(str, int)
def show_graph_hint(self: "ShellWindow", message: str, timeout_ms: int = 3600) -> None:
    self.shell_library_presenter.show_graph_hint(message, timeout_ms)


@pyqtSlot()
def clear_graph_hint(self: "ShellWindow") -> None:
    self.shell_library_presenter.clear_graph_hint()


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


def _commit_node_execution_state_change(self: "ShellWindow") -> None:
    self.run_state.node_execution_revision += 1
    self.node_execution_state_changed.emit()


def mark_node_execution_running(self: "ShellWindow", workspace_id: str, node_id: str) -> None:
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
        changed = True
    if normalized_node_id in state.completed_node_ids:
        state.completed_node_ids.discard(normalized_node_id)
        changed = True
    if normalized_node_id not in state.running_node_ids:
        state.running_node_ids.add(normalized_node_id)
        changed = True
    if changed:
        self._commit_node_execution_state_change()


def mark_node_execution_completed(self: "ShellWindow", workspace_id: str, node_id: str) -> None:
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
        changed = True
    if normalized_node_id in state.running_node_ids:
        state.running_node_ids.discard(normalized_node_id)
        changed = True
    if normalized_node_id not in state.completed_node_ids:
        state.completed_node_ids.add(normalized_node_id)
        changed = True
    if changed:
        self._commit_node_execution_state_change()


def clear_node_execution_visualization_state(self: "ShellWindow") -> None:
    state = self.run_state
    if not (state.node_execution_workspace_id or state.running_node_ids or state.completed_node_ids):
        return
    state.node_execution_workspace_id = ""
    state.running_node_ids.clear()
    state.completed_node_ids.clear()
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
def request_open_graph_search(self: "ShellWindow") -> None:
    self.shell_library_presenter.request_open_graph_search()


@pyqtSlot()
def request_close_graph_search(self: "ShellWindow") -> None:
    self.shell_library_presenter.request_close_graph_search()


@pyqtSlot(str, str, float, float, float, float, result=bool)
def request_open_connection_quick_insert(
    self: "ShellWindow",
    node_id: str,
    port_key: str,
    scene_x: float,
    scene_y: float,
    overlay_x: float,
    overlay_y: float,
) -> bool:
    return bool(
        self.graph_canvas_presenter.request_open_connection_quick_insert(
            node_id,
            port_key,
            scene_x,
            scene_y,
            overlay_x,
            overlay_y,
        )
    )


@pyqtSlot(float, float, float, float)
def request_open_canvas_quick_insert(
    self: "ShellWindow",
    scene_x: float,
    scene_y: float,
    overlay_x: float,
    overlay_y: float,
) -> None:
    self.graph_canvas_presenter.request_open_canvas_quick_insert(
        scene_x,
        scene_y,
        overlay_x,
        overlay_y,
    )


@pyqtSlot()
def request_close_connection_quick_insert(self: "ShellWindow") -> None:
    self.shell_library_presenter.request_close_connection_quick_insert()


@pyqtSlot(str)
def set_connection_quick_insert_query(self: "ShellWindow", query: str) -> None:
    self.shell_library_presenter.set_connection_quick_insert_query(query)


@pyqtSlot(int)
def request_connection_quick_insert_move(self: "ShellWindow", delta: int) -> None:
    self.shell_library_presenter.request_connection_quick_insert_move(delta)


@pyqtSlot(int)
def request_connection_quick_insert_highlight(self: "ShellWindow", index: int) -> None:
    self.shell_library_presenter.request_connection_quick_insert_highlight(index)


@pyqtSlot(result=bool)
def request_connection_quick_insert_accept(self: "ShellWindow") -> bool:
    return bool(self.shell_library_presenter.request_connection_quick_insert_accept())


@pyqtSlot(int, result=bool)
def request_connection_quick_insert_choose(self: "ShellWindow", index: int) -> bool:
    return bool(self.shell_library_presenter.request_connection_quick_insert_choose(index))


@pyqtSlot(str)
def set_graph_search_query(self: "ShellWindow", query: str) -> None:
    self.shell_library_presenter.set_graph_search_query(query)


@pyqtSlot(str, bool)
def set_graph_search_scope_enabled(self: "ShellWindow", scope_id: str, enabled: bool) -> None:
    self.shell_library_presenter.set_graph_search_scope_enabled(scope_id, enabled)


@pyqtSlot(int)
def request_graph_search_move(self: "ShellWindow", delta: int) -> None:
    self.shell_library_presenter.request_graph_search_move(delta)


@pyqtSlot(int)
def request_graph_search_highlight(self: "ShellWindow", index: int) -> None:
    self.shell_library_presenter.request_graph_search_highlight(index)


@pyqtSlot(result=bool)
def request_graph_search_accept(self: "ShellWindow") -> bool:
    return bool(self.shell_library_presenter.request_graph_search_accept())


@pyqtSlot(int, result=bool)
def request_graph_search_jump(self: "ShellWindow", index: int) -> bool:
    return bool(self.shell_library_presenter.request_graph_search_jump(index))


@pyqtSlot(str)
def request_add_node_from_library(self: "ShellWindow", type_id: str) -> None:
    self.shell_library_presenter.request_add_node_from_library(type_id)


@pyqtSlot(result=bool)
def request_publish_custom_workflow_from_selected(self: "ShellWindow") -> bool:
    return bool(self.shell_library_presenter.request_publish_custom_workflow_from_selected())


@pyqtSlot(result=bool)
def request_publish_custom_workflow_from_scope(self: "ShellWindow") -> bool:
    return bool(self.shell_library_presenter.request_publish_custom_workflow_from_scope())


@pyqtSlot(str, result=bool)
def request_publish_custom_workflow_from_node(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.shell_library_presenter.request_publish_custom_workflow_from_node(node_id))


@pyqtSlot(str, result=bool)
@pyqtSlot(str, str, result=bool)
def request_delete_custom_workflow_from_library(
    self: "ShellWindow",
    workflow_id: str,
    workflow_scope: str = "",
) -> bool:
    return bool(
        self.shell_library_presenter.request_delete_custom_workflow_from_library(
            workflow_id,
            workflow_scope,
        )
    )


@pyqtSlot(str, result=bool)
@pyqtSlot(str, str, result=bool)
def request_rename_custom_workflow_from_library(
    self: "ShellWindow",
    workflow_id: str,
    workflow_scope: str = "",
) -> bool:
    return bool(
        self.shell_library_presenter.request_rename_custom_workflow_from_library(
            workflow_id,
            workflow_scope,
        )
    )


@pyqtSlot(str, str, result=bool)
def request_set_custom_workflow_scope(
    self: "ShellWindow",
    workflow_id: str,
    workflow_scope: str,
) -> bool:
    return bool(self.shell_library_presenter.request_set_custom_workflow_scope(workflow_id, workflow_scope))


@pyqtSlot(str, float, float, str, str, str, str, result=bool)
def request_drop_node_from_library(
    self: "ShellWindow",
    type_id: str,
    scene_x: float,
    scene_y: float,
    target_mode: str,
    target_node_id: str,
    target_port_key: str,
    target_edge_id: str,
) -> bool:
    return bool(
        self.graph_canvas_presenter.request_drop_node_from_library(
            type_id,
            scene_x,
            scene_y,
            target_mode,
            target_node_id,
            target_port_key,
            target_edge_id,
        )
    )


@pyqtSlot()
def request_run_workflow(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_run_workflow()


@pyqtSlot()
def request_toggle_run_pause(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_toggle_run_pause()


@pyqtSlot()
def request_stop_workflow(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_stop_workflow()


@pyqtSlot()
def request_create_workspace(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_create_workspace()


@pyqtSlot()
def request_create_view(self: "ShellWindow") -> None:
    self.shell_workspace_presenter.request_create_view()


@pyqtSlot(str)
def request_switch_view(self: "ShellWindow", view_id: str) -> None:
    self.shell_workspace_presenter.request_switch_view(view_id)


@pyqtSlot(str, result=bool)
def request_open_subnode_scope(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.graph_canvas_presenter.request_open_subnode_scope(node_id))


@pyqtSlot(str, result=bool)
def request_open_scope_breadcrumb(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_open_scope_breadcrumb(node_id))


@pyqtSlot(result=bool)
def request_navigate_scope_parent(self: "ShellWindow") -> bool:
    return bool(self._navigate_scope(self.scene.navigate_scope_parent))


@pyqtSlot(result=bool)
def request_navigate_scope_root(self: "ShellWindow") -> bool:
    return bool(self._navigate_scope(self.scene.navigate_scope_root))


@pyqtSlot()
def request_save_project(self: "ShellWindow") -> None:
    self._save_project()


@pyqtSlot()
def request_save_project_as(self: "ShellWindow") -> None:
    self._save_project_as()


@pyqtSlot()
def request_open_project(self: "ShellWindow") -> None:
    self._open_project()


@pyqtSlot()
def request_rename_workspace(self: "ShellWindow") -> None:
    self._rename_active_workspace()


@pyqtSlot(str, result=bool)
def request_rename_workspace_by_id(self: "ShellWindow", workspace_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_rename_workspace_by_id(workspace_id))


@pyqtSlot()
def request_duplicate_workspace(self: "ShellWindow") -> None:
    self._duplicate_active_workspace()


@pyqtSlot()
def request_close_workspace(self: "ShellWindow") -> None:
    self._close_active_workspace()


@pyqtSlot(str, result=bool)
def request_close_workspace_by_id(self: "ShellWindow", workspace_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_close_workspace_by_id(workspace_id))


@pyqtSlot(str, result=bool)
def request_close_view(self: "ShellWindow", view_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_close_view(view_id))


@pyqtSlot(str, result=bool)
def request_rename_view(self: "ShellWindow", view_id: str) -> bool:
    return bool(self.shell_workspace_presenter.request_rename_view(view_id))


@pyqtSlot(int, int, result=bool)
def request_move_workspace_tab(self: "ShellWindow", from_index: int, to_index: int) -> bool:
    return bool(self.shell_workspace_presenter.request_move_workspace_tab(from_index, to_index))


@pyqtSlot(int, int, result=bool)
def request_move_view_tab(self: "ShellWindow", from_index: int, to_index: int) -> bool:
    return bool(self.shell_workspace_presenter.request_move_view_tab(from_index, to_index))


@pyqtSlot(result=bool)
def request_align_selection_left(self: "ShellWindow") -> bool:
    return bool(self._align_selection_left())


@pyqtSlot(result=bool)
def request_align_selection_right(self: "ShellWindow") -> bool:
    return bool(self._align_selection_right())


@pyqtSlot(result=bool)
def request_align_selection_top(self: "ShellWindow") -> bool:
    return bool(self._align_selection_top())


@pyqtSlot(result=bool)
def request_align_selection_bottom(self: "ShellWindow") -> bool:
    return bool(self._align_selection_bottom())


@pyqtSlot(result=bool)
def request_distribute_selection_horizontally(self: "ShellWindow") -> bool:
    return bool(self._distribute_selection_horizontally())


@pyqtSlot(result=bool)
def request_distribute_selection_vertically(self: "ShellWindow") -> bool:
    return bool(self._distribute_selection_vertically())


@pyqtSlot(result=bool)
def request_toggle_snap_to_grid(self: "ShellWindow") -> bool:
    self.set_snap_to_grid_enabled(not self.search_scope_state.snap_to_grid_enabled)
    return bool(self.search_scope_state.snap_to_grid_enabled)


@pyqtSlot()
def request_connect_selected_nodes(self: "ShellWindow") -> None:
    self._connect_selected_nodes()


@pyqtSlot(result=bool)
def request_duplicate_selected_nodes(self: "ShellWindow") -> bool:
    return bool(self._duplicate_selected_nodes())


@pyqtSlot(result=bool)
def request_wrap_selected_nodes_in_comment_backdrop(self: "ShellWindow") -> bool:
    return bool(self._wrap_selected_nodes_in_comment_backdrop())


@pyqtSlot(result=bool)
def request_group_selected_nodes(self: "ShellWindow") -> bool:
    return bool(self._group_selected_nodes())


@pyqtSlot(result=bool)
def request_ungroup_selected_nodes(self: "ShellWindow") -> bool:
    return bool(self.shell_inspector_presenter.request_ungroup_selected_nodes())


@pyqtSlot(result=bool)
def request_copy_selected_nodes(self: "ShellWindow") -> bool:
    return bool(self._copy_selected_nodes_to_clipboard())


@pyqtSlot(result=bool)
def request_cut_selected_nodes(self: "ShellWindow") -> bool:
    return bool(self._cut_selected_nodes_to_clipboard())


@pyqtSlot(result=bool)
def request_paste_selected_nodes(self: "ShellWindow") -> bool:
    return bool(self._paste_nodes_from_clipboard())


@pyqtSlot(result=bool)
def request_undo(self: "ShellWindow") -> bool:
    return bool(self._undo())


@pyqtSlot(result=bool)
def request_redo(self: "ShellWindow") -> bool:
    return bool(self._redo())


@pyqtSlot(str, str, str, str, result=bool)
def request_connect_ports(
    self: "ShellWindow",
    node_a_id: str,
    port_a: str,
    node_b_id: str,
    port_b: str,
) -> bool:
    return bool(self.graph_canvas_presenter.request_connect_ports(node_a_id, port_a, node_b_id, port_b))


@pyqtSlot(str, result=bool)
def request_remove_edge(self: "ShellWindow", edge_id: str) -> bool:
    return bool(self.workspace_library_controller.request_remove_edge(edge_id).payload)


@pyqtSlot(str, result=bool)
def request_ungroup_node(self: "ShellWindow", node_id: str) -> bool:
    if not node_id:
        return False
    scene = self.scene
    if scene is None:
        return False
    scene.select_node(node_id)
    return self.request_ungroup_selected_nodes()


@pyqtSlot(str, result=bool)
def request_remove_node(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.workspace_library_controller.request_remove_node(node_id).payload)


@pyqtSlot(str, result=str)
def request_add_selected_subnode_pin(self: "ShellWindow", direction: str) -> str:
    return self.shell_inspector_presenter.request_add_selected_subnode_pin(direction)


@pyqtSlot(str, result=bool)
def request_rename_node(self: "ShellWindow", node_id: str) -> bool:
    return bool(self.workspace_library_controller.request_rename_node(node_id).payload)


@pyqtSlot(str, result=bool)
def request_rename_selected_port(self: "ShellWindow", key: str) -> bool:
    return bool(self.workspace_library_controller.request_rename_selected_port(key).payload)


@pyqtSlot(str, result=bool)
def request_remove_selected_port(self: "ShellWindow", key: str) -> bool:
    return bool(self.workspace_library_controller.request_remove_selected_port(key).payload)


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


@pyqtSlot("QVariantList", result=bool)
def request_delete_selected_graph_items(self: "ShellWindow", edge_ids: list[Any]) -> bool:
    return bool(self.workspace_library_controller.request_delete_selected_graph_items(edge_ids).payload)


@pyqtSlot(str, "QVariant")
def set_selected_node_property(self: "ShellWindow", key: str, value: Any) -> None:
    self.shell_inspector_presenter.set_selected_node_property(key, value)


@pyqtSlot(str, "QVariant", result="QVariantMap")
def describe_pdf_preview(self: "ShellWindow", source: str, page_number: Any) -> dict[str, Any]:
    return build_pdf_preview_description(source, page_number)


@pyqtSlot(str, str, result=str)
def browse_selected_node_property_path(self: "ShellWindow", key: str, current_path: str) -> str:
    return self.shell_inspector_presenter.browse_selected_node_property_path(key, current_path)


@pyqtSlot(str, str, str, result=str)
def browse_node_property_path(self: "ShellWindow", node_id: str, key: str, current_path: str) -> str:
    return self.graph_canvas_presenter.browse_node_property_path(node_id, key, current_path)


def _browse_property_path_dialog(self: "ShellWindow", property_label: str, current_path: str) -> str:
    return self.shell_host_presenter.browse_property_path_dialog(property_label, current_path)


def _repair_property_path_dialog(
    self: "ShellWindow",
    *,
    node_type_id: str,
    property_key: str,
    property_label: str,
    current_path: str,
) -> str:
    repair_modes = repair_modes_for_node_property(node_type_id, property_key)
    normalized_label = str(property_label or "").strip() or "File"
    normalized_current_path = str(current_path or "").strip()
    if not repair_modes:
        return self.shell_host_presenter.browse_property_path_dialog(normalized_label, normalized_current_path)

    selected_mode = repair_modes[0]
    if len(repair_modes) > 1:
        metadata = self.model.project.metadata
        default_mode = preferred_repair_mode_for_value(
            normalized_current_path,
            project_path=str(self.project_path or "").strip() or None,
            project_metadata=dict(metadata) if isinstance(metadata, dict) else None,
            fallback_mode=self.app_preferences_controller.source_import_mode(),
            allowed_modes=repair_modes,
        )
        options = ["Managed Copy", "External Link"]
        default_index = 0 if default_mode == MANAGED_COPY_MODE else 1
        selection, accepted = QInputDialog.getItem(
            self,
            "Repair file...",
            f"Store repaired {normalized_label.lower()} as:",
            options,
            default_index,
            False,
        )
        if not accepted:
            return ""
        selected_mode = MANAGED_COPY_MODE if str(selection or "").strip() == options[0] else EXTERNAL_LINK_MODE

    selected_path, _selected_filter = QFileDialog.getOpenFileName(
        self,
        f"Repair {normalized_label}",
        self.shell_host_presenter._path_dialog_start_path(normalized_current_path),
    )
    normalized_selected_path = str(selected_path or "").strip()
    if not normalized_selected_path:
        return ""
    if selected_mode == EXTERNAL_LINK_MODE:
        return normalized_selected_path

    managed_ref = self.shell_host_presenter._import_source_as_managed_copy(
        property_label=normalized_label,
        current_path=normalized_current_path,
        selected_path=normalized_selected_path,
    )
    return managed_ref or normalized_selected_path


@pyqtSlot(str, bool)
def set_selected_port_exposed(self: "ShellWindow", key: str, exposed: bool) -> None:
    self.shell_inspector_presenter.set_selected_port_exposed(key, exposed)


@pyqtSlot(str, str, result=bool)
def set_selected_port_label(self: "ShellWindow", key: str, label: str) -> bool:
    return bool(self.shell_inspector_presenter.set_selected_port_label(key, label))


@pyqtSlot(bool)
def set_selected_node_collapsed(self: "ShellWindow", collapsed: bool) -> None:
    self.shell_inspector_presenter.set_selected_node_collapsed(collapsed)


def _ensure_project_metadata_defaults(self: "ShellWindow"):
    return self.project_session_controller.ensure_project_metadata_defaults()


def _workflow_settings_payload(self: "ShellWindow"):
    return self.project_session_controller.workflow_settings_payload()


def _persist_script_editor_state(self: "ShellWindow"):
    return self.project_session_controller.persist_script_editor_state()


def _restore_script_editor_state(self: "ShellWindow"):
    return self.project_session_controller.restore_script_editor_state()


def _save_project(self: "ShellWindow"):
    return self.project_session_controller.save_project()


def _save_project_as(self: "ShellWindow"):
    return self.project_session_controller.save_project_as()


def _show_project_files(self: "ShellWindow"):
    return self.project_session_controller.show_project_files_dialog()


def _new_project(self: "ShellWindow"):
    self.project_session_controller.new_project()
    self.clear_run_failure_focus()
    self._reset_viewer_session_bridge(reason="project_close")
    return None


def _open_project(self: "ShellWindow"):
    before_project_path = self.project_path
    before_project_object_id = id(self.model.project)
    self.project_session_controller.open_project()
    if self.project_path != before_project_path or id(self.model.project) != before_project_object_id:
        self.clear_run_failure_focus()
        self._reset_viewer_session_bridge(reason="project_close")
    return None


def _open_project_path(self: "ShellWindow", path):
    opened = bool(self.project_session_controller.open_project_path(path))
    if opened:
        self.clear_run_failure_focus()
        self._reset_viewer_session_bridge(reason="project_close")
    return opened


def _clear_recent_projects(self: "ShellWindow"):
    return self.project_session_controller.clear_recent_projects()


def _restore_session(self: "ShellWindow"):
    return self.project_session_controller.restore_session()


def _discard_autosave_snapshot(self: "ShellWindow"):
    return self.project_session_controller.discard_autosave_snapshot()


def _recover_autosave_if_newer(self: "ShellWindow"):
    return self.project_session_controller.recover_autosave_if_newer()


def _process_deferred_autosave_recovery(self: "ShellWindow"):
    return self.project_session_controller.process_deferred_autosave_recovery()


def _autosave_tick(self: "ShellWindow"):
    return self.project_session_controller.autosave_tick()


def _persist_session(self: "ShellWindow", project_doc=None):
    return self.project_session_controller.persist_session(project_doc)


def _switch_workspace_by_offset(self: "ShellWindow", offset):
    return self.workspace_library_controller.switch_workspace_by_offset(offset)


def _refresh_workspace_tabs(self: "ShellWindow"):
    return self.workspace_library_controller.refresh_workspace_tabs()


def _switch_workspace(self: "ShellWindow", workspace_id):
    return self.workspace_library_controller.switch_workspace(workspace_id)


def _save_active_view_state(self: "ShellWindow"):
    return self.workspace_library_controller.save_active_view_state()


def _restore_active_view_state(self: "ShellWindow"):
    return self.workspace_library_controller.restore_active_view_state()


def _visible_scene_rect(self: "ShellWindow"):
    return self.workspace_library_controller.visible_scene_rect()


def _current_workspace_scene_bounds(self: "ShellWindow"):
    return self.workspace_library_controller.current_workspace_scene_bounds()


def _selection_bounds(self: "ShellWindow"):
    return self.workspace_library_controller.selection_bounds()


def _frame_all(self: "ShellWindow"):
    return self.workspace_library_controller.frame_all()


def _frame_selection(self: "ShellWindow"):
    return self.workspace_library_controller.frame_selection()


def _frame_node(self: "ShellWindow", node_id):
    return self.workspace_library_controller.frame_node(node_id)


def _center_on_node(self: "ShellWindow", node_id):
    return self.workspace_library_controller.center_on_node(node_id)


def _center_on_selection(self: "ShellWindow"):
    return self.workspace_library_controller.center_on_selection()


def _search_graph_nodes(self: "ShellWindow", query, limit=10, enabled_scopes=None):
    return self.workspace_library_controller.search_graph_nodes(
        query,
        limit,
        enabled_scopes=enabled_scopes,
    )


def _jump_to_graph_node(self: "ShellWindow", workspace_id, node_id):
    return self.workspace_library_controller.jump_to_graph_node(workspace_id, node_id)


def _create_view(self: "ShellWindow"):
    return self.workspace_library_controller.create_view()


def _switch_view(self: "ShellWindow", view_id):
    return self.workspace_library_controller.switch_view(view_id)


def _rename_view(self: "ShellWindow", view_id):
    return self.workspace_library_controller.rename_view(view_id)


def _create_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.create_workspace()


def _rename_active_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.rename_active_workspace()


def _duplicate_active_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.duplicate_active_workspace()


def _close_active_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.close_active_workspace()


def _on_workspace_tab_changed(self: "ShellWindow", index):
    return self.workspace_library_controller.on_workspace_tab_changed(index)


def _on_workspace_tab_close(self: "ShellWindow", index):
    return self.workspace_library_controller.on_workspace_tab_close(index)


def _add_node_from_library(self: "ShellWindow", type_id):
    return self.workspace_library_controller.add_node_from_library(type_id)


def _insert_library_node(self: "ShellWindow", type_id, x, y):
    return self.workspace_library_controller.insert_library_node(type_id, x, y)


def _active_workspace(self: "ShellWindow"):
    return self.workspace_library_controller.active_workspace()


def _prompt_connection_candidate(self: "ShellWindow", *, title, label, candidates):
    return self.workspace_library_controller.prompt_connection_candidate(
        title=title,
        label=label,
        candidates=candidates,
    )


def _auto_connect_dropped_node_to_port(
    self: "ShellWindow",
    new_node_id,
    target_node_id,
    target_port_key,
):
    return self.workspace_library_controller.auto_connect_dropped_node_to_port(
        new_node_id,
        target_node_id,
        target_port_key,
    )


def _auto_connect_dropped_node_to_edge(self: "ShellWindow", new_node_id, target_edge_id):
    return self.workspace_library_controller.auto_connect_dropped_node_to_edge(new_node_id, target_edge_id)


def _on_scene_node_selected(self: "ShellWindow", node_id):
    return self.workspace_library_controller.on_scene_node_selected(node_id)


def _on_node_property_changed(self: "ShellWindow", node_id, key, value):
    return self.workspace_library_controller.on_node_property_changed(node_id, key, value)


def _on_port_exposed_changed(self: "ShellWindow", node_id, key, exposed):
    return self.workspace_library_controller.on_port_exposed_changed(node_id, key, exposed)


def _on_node_collapse_changed(self: "ShellWindow", node_id, collapsed):
    return self.workspace_library_controller.on_node_collapse_changed(node_id, collapsed)


def _connect_selected_nodes(self: "ShellWindow"):
    return self.workspace_library_controller.connect_selected_nodes()


def _duplicate_selected_nodes(self: "ShellWindow"):
    return self.workspace_library_controller.duplicate_selected_nodes()


def _wrap_selected_nodes_in_comment_backdrop(self: "ShellWindow"):
    return self.workspace_graph_edit_controller.wrap_selected_nodes_in_comment_backdrop()


def _group_selected_nodes(self: "ShellWindow"):
    return self.workspace_library_controller.group_selected_nodes()


def _ungroup_selected_nodes(self: "ShellWindow"):
    return self.workspace_library_controller.ungroup_selected_nodes()


def _align_selection_left(self: "ShellWindow"):
    return self.workspace_library_controller.align_selection_left()


def _align_selection_right(self: "ShellWindow"):
    return self.workspace_library_controller.align_selection_right()


def _align_selection_top(self: "ShellWindow"):
    return self.workspace_library_controller.align_selection_top()


def _align_selection_bottom(self: "ShellWindow"):
    return self.workspace_library_controller.align_selection_bottom()


def _distribute_selection_horizontally(self: "ShellWindow"):
    return self.workspace_library_controller.distribute_selection_horizontally()


def _distribute_selection_vertically(self: "ShellWindow"):
    return self.workspace_library_controller.distribute_selection_vertically()


def _copy_selected_nodes_to_clipboard(self: "ShellWindow"):
    return self.workspace_library_controller.copy_selected_nodes_to_clipboard()


def _cut_selected_nodes_to_clipboard(self: "ShellWindow"):
    return self.workspace_library_controller.cut_selected_nodes_to_clipboard()


def _paste_nodes_from_clipboard(self: "ShellWindow"):
    return self.workspace_library_controller.paste_nodes_from_clipboard()


def _undo(self: "ShellWindow"):
    return self.workspace_library_controller.undo()


def _redo(self: "ShellWindow"):
    return self.workspace_library_controller.redo()


def _selected_node_context(self: "ShellWindow"):
    return self.workspace_library_controller.selected_node_context()


def _active_workspace_data(self: "ShellWindow"):
    return self.shell_host_presenter._active_workspace_data()


def _passive_node_context(self: "ShellWindow", node_id: str):
    return self.shell_host_presenter._passive_node_context(node_id)


def _flow_edge_context(self: "ShellWindow", edge_id: str):
    return self.shell_host_presenter._flow_edge_context(edge_id)


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


def _reveal_parent_chain(self: "ShellWindow", workspace_id, node_id):
    return self.workspace_library_controller.reveal_parent_chain(workspace_id, node_id)


def _import_custom_workflow(self: "ShellWindow"):
    return self.workspace_library_controller.import_custom_workflow()


def _export_custom_workflow(self: "ShellWindow"):
    controller = self.workspace_library_controller
    package_io_controller = getattr(controller, "workspace_package_io_controller", None)
    prompt_override = getattr(controller, "_prompt_custom_workflow_export_definition", None)
    if package_io_controller is not None and callable(prompt_override):
        package_io_controller._prompt_custom_workflow_export_definition = prompt_override
    return controller.export_custom_workflow()


def _import_node_package(self: "ShellWindow"):
    return self.workspace_library_controller.import_node_package()


def _export_node_package(self: "ShellWindow"):
    return self.workspace_library_controller.export_node_package()


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


def _prompt_recover_autosave(self: "ShellWindow", recovered_project=None):
    return self.project_session_controller.prompt_recover_autosave(recovered_project)


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


_EXCLUDED_BINDING_NAMES = {
    "Any",
    "Callable",
    "Literal",
    "TYPE_CHECKING",
    "ShellWindow",
    "Qt",
    "pyqtSlot",
    "QFileDialog",
    "QInputDialog",
    "EXTERNAL_LINK_MODE",
    "MANAGED_COPY_MODE",
    "preferred_repair_mode_for_value",
    "repair_modes_for_node_property",
    "build_pdf_preview_description",
    "build_window_menu_bar",
    "create_window_actions",
    "format_recent_project_menu_label_value",
    "refresh_recent_projects_menu_entries",
    "_UNSET",
    "_EXCLUDED_BINDING_NAMES",
    "_should_bind",
}


def _should_bind(name: str, value: object) -> bool:
    if name in _EXCLUDED_BINDING_NAMES:
        return False
    if name.startswith("_qt_") or name.startswith("_get_") or name.startswith("_set_"):
        return False
    return callable(value) or isinstance(value, property)


SHELL_WINDOW_FACADE_BINDINGS = {
    name: value
    for name, value in globals().items()
    if _should_bind(name, value)
}
for helper_name in (
    "_set_graph_search_state",
    "_set_connection_quick_insert_state",
    "_set_project_passive_style_presets",
    "_set_run_ui_state",
):
    SHELL_WINDOW_FACADE_BINDINGS[helper_name] = globals()[helper_name]
SHELL_WINDOW_FACADE_BINDINGS["_format_recent_project_menu_label"] = staticmethod(
    format_recent_project_menu_label_value
)


__all__ = [
    "SHELL_WINDOW_FACADE_BINDINGS",
    "project_path",
    "recent_project_paths",
    "_library_query",
    "_library_category",
    "_library_data_type",
    "_library_direction",
    "_active_run_id",
    "_active_run_workspace_id",
    "_engine_state_value",
    "_last_manual_save_ts",
    "_last_autosave_fingerprint",
    "_autosave_recovery_deferred",
    "_qt_project_display_name",
    "_qt_filtered_node_library_items",
    "_qt_grouped_node_library_items",
    "_qt_library_category_options",
    "_qt_library_direction_options",
    "_qt_library_data_type_options",
    "_qt_pin_data_type_options",
    "_qt_graph_search_open",
    "_qt_graph_search_query",
    "_qt_graph_search_enabled_scopes",
    "_qt_graph_search_results",
    "_qt_graph_search_highlight_index",
    "_qt_connection_quick_insert_open",
    "_qt_connection_quick_insert_query",
    "_qt_connection_quick_insert_results",
    "_qt_connection_quick_insert_highlight_index",
    "_qt_connection_quick_insert_overlay_x",
    "_qt_connection_quick_insert_overlay_y",
    "_qt_connection_quick_insert_source_summary",
    "_qt_connection_quick_insert_is_canvas_mode",
    "_qt_graph_hint_message",
    "_qt_graph_hint_visible",
    "_qt_graphics_show_grid",
    "_qt_graphics_grid_style",
    "_qt_graphics_edge_crossing_style",
    "_qt_graphics_show_minimap",
    "_qt_graphics_show_port_labels",
    "_qt_graphics_minimap_expanded",
    "_qt_graphics_node_shadow",
    "_qt_graphics_shadow_strength",
    "_qt_graphics_shadow_softness",
    "_qt_graphics_shadow_offset",
    "_qt_graphics_performance_mode",
    "_qt_graphics_tab_strip_density",
    "_qt_active_theme_id",
    "_qt_snap_to_grid_enabled",
    "_qt_snap_grid_size",
    "_qt_active_workspace_id",
    "_qt_active_workspace_name",
    "_qt_active_view_name",
    "_qt_active_view_items",
    "_qt_active_scope_breadcrumb_items",
    "_qt_selected_node_title",
    "_qt_selected_node_subtitle",
    "_qt_selected_node_header_items",
    "_qt_selected_node_summary",
    "_qt_has_selected_node",
    "_qt_selected_node_collapsible",
    "_qt_selected_node_collapsed",
    "_qt_selected_node_is_subnode_pin",
    "_qt_selected_node_is_subnode_shell",
    "_qt_can_publish_custom_workflow_from_scope",
    "_qt_selected_node_property_items",
    "_qt_selected_node_port_items",
]
