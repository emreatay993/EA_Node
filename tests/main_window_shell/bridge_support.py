from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import pytest
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtQuick import QQuickItem

from ea_node_editor.telemetry.frame_rate import FrameRateSampler
from ea_node_editor.ui.shell.state import ShellRunState
from ea_node_editor.ui.shell.runtime_clipboard import build_graph_fragment_payload, serialize_graph_fragment_payload
from ea_node_editor.ui_qml.graph_canvas_bridge import GraphCanvasBridge
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.shell_inspector_bridge import ShellInspectorBridge
from ea_node_editor.ui_qml.shell_library_bridge import ShellLibraryBridge
from ea_node_editor.ui_qml.shell_workspace_bridge import ShellWorkspaceBridge
from ea_node_editor.ui_qml.viewer_host_service import ViewerHostService
from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge
from tests.main_window_shell.base import MainWindowShellTestBase, SharedMainWindowShellTestBase

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PASSIVE_IMAGE_DIRECT_ENV = "EA_NODE_EDITOR_PASSIVE_IMAGE_NODES_DIRECT"
_PASSIVE_PDF_DIRECT_ENV = "EA_NODE_EDITOR_PASSIVE_PDF_NODES_DIRECT"
_GRAPH_CANVAS_HOST_DIRECT_ENV = "EA_NODE_EDITOR_GRAPH_CANVAS_HOST_DIRECT"

pytestmark = pytest.mark.xdist_group("p03_bridge_contracts")


def _named_child_items(root: QObject, object_name: str) -> list[QQuickItem]:
    matches: list[QQuickItem] = []

    def _visit(item: QObject) -> None:
        if not isinstance(item, QQuickItem):
            return
        if item.objectName() == object_name:
            matches.append(item)
        for child in item.childItems():
            _visit(child)

    _visit(root)
    return matches


class _ShellLibraryHostStub(QObject):
    node_library_changed = pyqtSignal()
    library_pane_reset_requested = pyqtSignal(name="libraryPaneResetRequested")
    graph_search_changed = pyqtSignal()
    connection_quick_insert_changed = pyqtSignal()
    graph_hint_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.grouped_node_library_items = [
            {
                "kind": "item",
                "type_id": "core.logger",
                "display_name": "Logger",
            }
        ]
        self.graph_search_open = True
        self.graph_search_query = "graph search"
        self.graph_search_enabled_scopes = ["title", "type", "content", "port"]
        self.graph_search_results = [{"node_id": "node-1"}]
        self.graph_search_highlight_index = 2
        self.connection_quick_insert_open = True
        self.connection_quick_insert_overlay_x = 125.5
        self.connection_quick_insert_overlay_y = 240.25
        self.connection_quick_insert_source_summary = "Logger.exec_in [any]"
        self.connection_quick_insert_is_canvas_mode = True
        self.connection_quick_insert_query = "quick insert"
        self.connection_quick_insert_results = [{"type_id": "core.start"}]
        self.connection_quick_insert_highlight_index = 1
        self.graph_hint_visible = True
        self.graph_hint_message = "Hint message"
        self._return_values = {
            "request_rename_custom_workflow_from_library": True,
            "request_set_custom_workflow_scope": True,
            "request_delete_custom_workflow_from_library": True,
            "request_graph_search_accept": True,
            "request_graph_search_jump": True,
            "request_connection_quick_insert_accept": True,
            "request_connection_quick_insert_choose": True,
        }

    def _record(self, name: str, *args):
        self.calls.append((name, args))
        return self._return_values.get(name)

    def set_library_query(self, query: str) -> None:
        self._record("set_library_query", query)

    def request_add_node_from_library(self, type_id: str) -> None:
        self._record("request_add_node_from_library", type_id)

    def request_rename_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(self._record("request_rename_custom_workflow_from_library", workflow_id, workflow_scope))

    def request_set_custom_workflow_scope(self, workflow_id: str, workflow_scope: str) -> bool:
        return bool(self._record("request_set_custom_workflow_scope", workflow_id, workflow_scope))

    def request_delete_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(self._record("request_delete_custom_workflow_from_library", workflow_id, workflow_scope))

    def set_graph_search_query(self, query: str) -> None:
        self._record("set_graph_search_query", query)

    def set_graph_search_scope_enabled(self, scope_id: str, enabled: bool) -> None:
        self._record("set_graph_search_scope_enabled", scope_id, enabled)

    def request_graph_search_move(self, delta: int) -> None:
        self._record("request_graph_search_move", delta)

    def request_graph_search_accept(self) -> bool:
        return bool(self._record("request_graph_search_accept"))

    def request_close_graph_search(self) -> None:
        self._record("request_close_graph_search")

    def request_graph_search_highlight(self, index: int) -> None:
        self._record("request_graph_search_highlight", index)

    def request_graph_search_jump(self, index: int) -> bool:
        return bool(self._record("request_graph_search_jump", index))

    def set_connection_quick_insert_query(self, query: str) -> None:
        self._record("set_connection_quick_insert_query", query)

    def request_connection_quick_insert_move(self, delta: int) -> None:
        self._record("request_connection_quick_insert_move", delta)

    def request_connection_quick_insert_accept(self) -> bool:
        return bool(self._record("request_connection_quick_insert_accept"))

    def request_close_connection_quick_insert(self) -> None:
        self._record("request_close_connection_quick_insert")

    def request_connection_quick_insert_highlight(self, index: int) -> None:
        self._record("request_connection_quick_insert_highlight", index)

    def request_connection_quick_insert_choose(self, index: int) -> bool:
        return bool(self._record("request_connection_quick_insert_choose", index))


class _ShellInspectorHostStub(QObject):
    selected_node_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.selected_node_title = "Inspector Node"
        self.selected_node_subtitle = "Inspector subtitle"
        self.selected_node_summary = "Inspector Node\nType: passive.fixture"
        self.selected_node_header_items = [{"label": "Type", "value": "passive.fixture"}]
        self.has_selected_node = True
        self.selected_node_collapsible = True
        self.selected_node_collapsed = False
        self.selected_node_is_subnode_pin = False
        self.selected_node_is_subnode_shell = True
        self.selected_node_property_items = [
            {
                "key": "message",
                "label": "Message",
                "value": "hello",
                "editor_mode": "text",
            }
        ]
        self.selected_node_port_items = [
            {
                "key": "exec_in",
                "label": "Exec In",
                "direction": "in",
                "exposed": True,
            }
        ]
        self.pin_data_type_options = ["any", "text"]
        self._return_values = {
            "browse_selected_node_property_path": "C:/temp/selected.txt",
            "set_selected_port_label": True,
            "request_ungroup_selected_nodes": True,
            "request_add_selected_subnode_pin": "port-1",
            "request_remove_selected_port": True,
        }

    def _record(self, name: str, *args):
        self.calls.append((name, args))
        return self._return_values.get(name)

    def request_add_selected_subnode_pin(self, direction: str) -> str:
        return str(self._record("request_add_selected_subnode_pin", direction) or "")

    def set_selected_port_label(self, key: str, label: str) -> bool:
        return bool(self._record("set_selected_port_label", key, label))

    def request_remove_selected_port(self, key: str) -> bool:
        return bool(self._record("request_remove_selected_port", key))

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self._record("set_selected_node_collapsed", collapsed)

    def request_ungroup_selected_nodes(self) -> bool:
        return bool(self._record("request_ungroup_selected_nodes"))

    def set_selected_node_property(self, key: str, value: object) -> None:
        self._record("set_selected_node_property", key, value)

    def browse_selected_node_property_path(self, key: str, current_path: str) -> str:
        return str(self._record("browse_selected_node_property_path", key, current_path) or "")

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self._record("set_selected_port_exposed", key, exposed)


class _ShellWorkspaceHostStub(QObject):
    project_meta_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    graphics_preferences_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.project_display_name = "COREX Node Editor - packet.sfe"
        self.graphics_tab_strip_density = "relaxed"
        self.active_workspace_id = "ws-2"
        self.active_scope_breadcrumb_items = [
            {"label": "Root", "node_id": ""},
            {"label": "Scope", "node_id": "scope-node"},
        ]
        self.active_view_items = [
            {"view_id": "view-1", "label": "Main", "active": True},
            {"view_id": "view-2", "label": "Inspect", "active": False},
        ]
        self._return_values = {
            "request_open_scope_breadcrumb": True,
            "request_move_view_tab": True,
            "request_rename_view": True,
            "request_close_view": True,
            "request_move_workspace_tab": True,
            "request_rename_workspace_by_id": True,
            "request_close_workspace_by_id": True,
        }

    def _record(self, name: str, *args):
        self.calls.append((name, args))
        return self._return_values.get(name)

    def request_run_workflow(self) -> None:
        self._record("request_run_workflow")

    def request_toggle_run_pause(self) -> None:
        self._record("request_toggle_run_pause")

    def request_stop_workflow(self) -> None:
        self._record("request_stop_workflow")

    def show_workflow_settings_dialog(self, checked: bool = False) -> None:
        self._record("show_workflow_settings_dialog", checked)

    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        self._record("set_script_editor_panel_visible", checked)

    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        return bool(self._record("request_open_scope_breadcrumb", node_id))

    def request_switch_view(self, view_id: str) -> None:
        self._record("request_switch_view", view_id)

    def request_move_view_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._record("request_move_view_tab", from_index, to_index))

    def request_rename_view(self, view_id: str) -> bool:
        return bool(self._record("request_rename_view", view_id))

    def request_close_view(self, view_id: str) -> bool:
        return bool(self._record("request_close_view", view_id))

    def request_create_view(self) -> None:
        self._record("request_create_view")

    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._record("request_move_workspace_tab", from_index, to_index))

    def request_rename_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._record("request_rename_workspace_by_id", workspace_id))

    def request_close_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._record("request_close_workspace_by_id", workspace_id))

    def request_create_workspace(self) -> None:
        self._record("request_create_workspace")


class _WorkspaceTabsBridgeStub(QObject):
    tabs_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.tabs = [
            {"workspace_id": "ws-1", "label": "Workspace 1"},
            {"workspace_id": "ws-2", "label": "Workspace 2"},
        ]

    def activate_workspace(self, workspace_id: str) -> None:
        self.calls.append(("activate_workspace", (workspace_id,)))


class _ConsoleBridgeStub(QObject):
    output_changed = pyqtSignal()
    errors_changed = pyqtSignal()
    warnings_changed = pyqtSignal()
    counts_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.output_text = "stdout line"
        self.errors_text = "error line"
        self.warnings_text = "warning line"
        self.error_count_value = 3
        self.warning_count_value = 2

    def clear_all(self) -> None:
        self.calls.append(("clear_all", ()))


class _ScopeSceneBridgeStub(QObject):
    scope_changed = pyqtSignal()


class _ActiveWorkspaceManagerStub:
    def __init__(self, workspace_id: str) -> None:
        self._workspace_id = str(workspace_id)

    def active_workspace_id(self) -> str:
        return self._workspace_id


class _GraphCanvasShellHostStub(QObject):
    graphics_preferences_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()
    run_failure_changed = pyqtSignal()
    node_execution_state_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.graphics_minimap_expanded = True
        self.graphics_show_grid = True
        self.graphics_grid_style = "lines"
        self.graphics_show_minimap = True
        self.graphics_show_port_labels = True
        self.graphics_node_shadow = True
        self.graphics_shadow_strength = 70
        self.graphics_shadow_softness = 50
        self.graphics_shadow_offset = 4
        self.graphics_performance_mode = "full_fidelity"
        self.snap_to_grid_enabled = True
        self.snap_grid_size = 24.0
        self.run_state = ShellRunState()
        self.workspace_manager = _ActiveWorkspaceManagerStub("ws-1")
        self._return_values = {
            "request_open_subnode_scope": True,
            "browse_node_property_path": "C:/temp/from-canvas-bridge.txt",
            "request_drop_node_from_library": True,
            "request_connect_ports": True,
            "request_open_connection_quick_insert": True,
            "request_delete_selected_graph_items": True,
            "request_navigate_scope_parent": True,
            "request_navigate_scope_root": True,
            "request_edit_flow_edge_style": True,
            "request_edit_flow_edge_label": True,
            "request_reset_flow_edge_style": True,
            "request_copy_flow_edge_style": True,
            "request_paste_flow_edge_style": True,
            "request_remove_edge": True,
            "request_publish_custom_workflow_from_node": True,
            "request_edit_passive_node_style": True,
            "request_reset_passive_node_style": True,
            "request_copy_passive_node_style": True,
            "request_paste_passive_node_style": True,
            "request_rename_node": True,
            "request_ungroup_node": True,
            "request_remove_node": True,
        }

    def _record(self, name: str, *args):
        self.calls.append((name, args))
        return self._return_values.get(name)

    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self.graphics_minimap_expanded = bool(expanded)
        self._record("set_graphics_minimap_expanded", bool(expanded))

    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None:
        self.graphics_show_port_labels = bool(show_port_labels)
        self._record("set_graphics_show_port_labels", bool(show_port_labels))

    def set_graphics_performance_mode(self, mode: str) -> None:
        self.graphics_performance_mode = str(mode)
        self._record("set_graphics_performance_mode", str(mode))

    def request_open_subnode_scope(self, node_id: str) -> bool:
        return bool(self._record("request_open_subnode_scope", node_id))

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return str(self._record("browse_node_property_path", node_id, key, current_path) or "")

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> bool:
        return bool(
            self._record(
                "request_drop_node_from_library",
                type_id,
                scene_x,
                scene_y,
                target_mode,
                target_node_id,
                target_port_key,
                target_edge_id,
            )
        )

    def request_connect_ports(
        self,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        return bool(
            self._record(
                "request_connect_ports",
                source_node_id,
                source_port_key,
                target_node_id,
                target_port_key,
            )
        )

    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        cursor_scene_x: float,
        cursor_scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> bool:
        return bool(
            self._record(
                "request_open_connection_quick_insert",
                node_id,
                port_key,
                cursor_scene_x,
                cursor_scene_y,
                overlay_x,
                overlay_y,
            )
        )

    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        self._record(
            "request_open_canvas_quick_insert",
            scene_x,
            scene_y,
            overlay_x,
            overlay_y,
        )

    def request_delete_selected_graph_items(self, edge_ids: list[object]) -> bool:
        return bool(self._record("request_delete_selected_graph_items", edge_ids))

    def request_navigate_scope_parent(self) -> bool:
        return bool(self._record("request_navigate_scope_parent"))

    def request_navigate_scope_root(self) -> bool:
        return bool(self._record("request_navigate_scope_root"))

    def set_graph_cursor_shape(self, cursor_shape: int) -> None:
        self._record("set_graph_cursor_shape", cursor_shape)

    def clear_graph_cursor_shape(self) -> None:
        self._record("clear_graph_cursor_shape")

    def describe_pdf_preview(self, source: str, page_number: object) -> dict[str, object]:
        self._record("describe_pdf_preview", source, page_number)
        return {
            "source": source,
            "page_number": int(page_number),
            "valid": True,
        }

    def request_edit_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._record("request_edit_flow_edge_style", edge_id))

    def request_edit_flow_edge_label(self, edge_id: str) -> bool:
        return bool(self._record("request_edit_flow_edge_label", edge_id))

    def request_reset_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._record("request_reset_flow_edge_style", edge_id))

    def request_copy_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._record("request_copy_flow_edge_style", edge_id))

    def request_paste_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._record("request_paste_flow_edge_style", edge_id))

    def request_remove_edge(self, edge_id: str) -> bool:
        return bool(self._record("request_remove_edge", edge_id))

    def request_publish_custom_workflow_from_node(self, node_id: str) -> bool:
        return bool(self._record("request_publish_custom_workflow_from_node", node_id))

    def request_edit_passive_node_style(self, node_id: str) -> bool:
        return bool(self._record("request_edit_passive_node_style", node_id))

    def request_reset_passive_node_style(self, node_id: str) -> bool:
        return bool(self._record("request_reset_passive_node_style", node_id))

    def request_copy_passive_node_style(self, node_id: str) -> bool:
        return bool(self._record("request_copy_passive_node_style", node_id))

    def request_paste_passive_node_style(self, node_id: str) -> bool:
        return bool(self._record("request_paste_passive_node_style", node_id))

    def request_rename_node(self, node_id: str) -> bool:
        return bool(self._record("request_rename_node", node_id))

    def request_ungroup_node(self, node_id: str) -> bool:
        return bool(self._record("request_ungroup_node", node_id))

    def request_remove_node(self, node_id: str) -> bool:
        return bool(self._record("request_remove_node", node_id))


class _GraphCanvasParentStub(QObject):
    def __init__(self, shell_window: QObject) -> None:
        super().__init__()
        self.shell_window = shell_window


class _GraphCanvasSceneBridgeStub(QObject):
    workspace_changed = pyqtSignal(str)
    nodes_changed = pyqtSignal()
    edges_changed = pyqtSignal()
    selection_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.workspace_id = "ws-1"
        self.nodes_model = [{"node_id": "node-1", "selected": True}]
        self.backdrop_nodes_model = [{"node_id": "backdrop-1", "selected": False}]
        self.minimap_nodes_model = [{"node_id": "node-1", "x": 10.0, "y": 15.0}]
        self.workspace_scene_bounds_payload = {"x": 0.0, "y": 0.0, "width": 640.0, "height": 360.0}
        self.edges_model = [{"edge_id": "edge-1"}]
        self.selected_node_lookup = {"node-1": True}
        self._return_values = {
            "are_port_kinds_compatible": True,
            "are_data_types_compatible": True,
            "move_nodes_by_delta": True,
            "consume_pending_surface_action": True,
            "set_node_properties": True,
        }

    def _record(self, name: str, *args):
        self.calls.append((name, args))
        return self._return_values.get(name)

    def select_node(self, node_id: str, additive: bool = False) -> None:
        self._record("select_node", node_id, additive)

    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        self._record("set_node_property", node_id, key, value)

    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
        self._record("set_node_port_label", node_id, port_key, label)

    def clear_selection(self) -> None:
        self._record("clear_selection")

    def select_nodes_in_rect(self, x1: float, y1: float, x2: float, y2: float, additive: bool = False) -> None:
        self._record("select_nodes_in_rect", x1, y1, x2, y2, additive)

    def set_pending_surface_action(self, node_id: str) -> None:
        self._record("set_pending_surface_action", node_id)

    def consume_pending_surface_action(self, node_id: str) -> bool:
        return bool(self._record("consume_pending_surface_action", node_id))

    def set_node_properties(self, node_id: str, values: dict[str, object]) -> bool:
        return bool(self._record("set_node_properties", node_id, values))

    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return bool(self._record("are_port_kinds_compatible", source_kind, target_kind))

    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return bool(self._record("are_data_types_compatible", source_type, target_type))

    def move_nodes_by_delta(self, node_ids: list[object], delta_x: float, delta_y: float) -> bool:
        return bool(self._record("move_nodes_by_delta", node_ids, delta_x, delta_y))

    def move_node(self, node_id: str, x: float, y: float) -> None:
        self._record("move_node", node_id, x, y)

    def resize_node(self, node_id: str, width: float, height: float) -> None:
        self._record("resize_node", node_id, width, height)

    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        self._record("set_node_geometry", node_id, x, y, width, height)


class _GraphCanvasViewBridgeStub(QObject):
    view_state_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.center_x = 18.5
        self.center_y = -42.0
        self.zoom_value = 1.75
        self.visible_scene_rect_payload = {"x": -120.0, "y": -80.0, "width": 240.0, "height": 160.0}

    def _record(self, name: str, *args) -> None:
        self.calls.append((name, args))

    def adjust_zoom(self, factor: float) -> None:
        self._record("adjust_zoom", factor)

    def pan_by(self, delta_x: float, delta_y: float) -> None:
        self._record("pan_by", delta_x, delta_y)

    def set_viewport_size(self, width: float, height: float) -> None:
        self._record("set_viewport_size", width, height)

    def center_on_scene_point(self, x: float, y: float) -> None:
        self._record("center_on_scene_point", x, y)


def _build_explicit_graph_canvas_bridge(
    *,
    parent: QObject | None = None,
    shell_window: QObject | None = None,
    canvas_source: object | None = None,
    host_source: object | None = None,
    scene_bridge: QObject | None = None,
    view_bridge: QObject | None = None,
) -> GraphCanvasBridge:
    state_bridge = GraphCanvasStateBridge(
        parent,
        shell_window=shell_window,
        canvas_source=canvas_source,
        scene_bridge=scene_bridge,
        view_bridge=view_bridge,
    )
    command_bridge = GraphCanvasCommandBridge(
        parent,
        shell_window=shell_window,
        canvas_source=canvas_source,
        host_source=host_source,
        scene_bridge=scene_bridge,
        view_bridge=view_bridge,
    )
    return GraphCanvasBridge(
        parent,
        shell_window=shell_window,
        scene_bridge=scene_bridge,
        view_bridge=view_bridge,
        state_bridge=state_bridge,
        command_bridge=command_bridge,
    )


class ShellLibraryBridgeTests(unittest.TestCase):
    def test_bridge_forwards_shell_library_search_state_and_actions(self) -> None:
        host = _ShellLibraryHostStub()
        bridge = ShellLibraryBridge(shell_window=host, library_source=host)

        self.assertIs(bridge.shell_window, host)
        self.assertIs(bridge.library_source, host)
        self.assertEqual(bridge.grouped_node_library_items, host.grouped_node_library_items)
        self.assertTrue(bridge.graph_search_open)
        self.assertEqual(bridge.graph_search_query, "graph search")
        self.assertEqual(bridge.graph_search_enabled_scopes, host.graph_search_enabled_scopes)
        self.assertEqual(bridge.graph_search_results, host.graph_search_results)
        self.assertEqual(bridge.graph_search_highlight_index, 2)
        self.assertTrue(bridge.connection_quick_insert_open)
        self.assertEqual(bridge.connection_quick_insert_overlay_x, 125.5)
        self.assertEqual(bridge.connection_quick_insert_overlay_y, 240.25)
        self.assertEqual(bridge.connection_quick_insert_source_summary, "Logger.exec_in [any]")
        self.assertTrue(bridge.connection_quick_insert_is_canvas_mode)
        self.assertEqual(bridge.connection_quick_insert_query, "quick insert")
        self.assertEqual(bridge.connection_quick_insert_results, host.connection_quick_insert_results)
        self.assertEqual(bridge.connection_quick_insert_highlight_index, 1)
        self.assertTrue(bridge.graph_hint_visible)
        self.assertEqual(bridge.graph_hint_message, "Hint message")

        bridge.set_library_query("logger")
        bridge.request_add_node_from_library("core.logger")
        self.assertTrue(bridge.request_rename_custom_workflow_from_library("wf-rename", "global"))
        self.assertTrue(bridge.request_set_custom_workflow_scope("wf-scope", "local"))
        self.assertTrue(bridge.request_delete_custom_workflow_from_library("wf-delete", "global"))
        bridge.set_graph_search_query("duplicate")
        bridge.set_graph_search_scope_enabled("content", False)
        bridge.request_graph_search_move(-1)
        self.assertTrue(bridge.request_graph_search_accept())
        bridge.request_close_graph_search()
        bridge.request_graph_search_highlight(3)
        self.assertTrue(bridge.request_graph_search_jump(4))
        bridge.set_connection_quick_insert_query("start")
        bridge.request_connection_quick_insert_move(1)
        self.assertTrue(bridge.request_connection_quick_insert_accept())
        bridge.request_close_connection_quick_insert()
        bridge.request_connection_quick_insert_highlight(5)
        self.assertTrue(bridge.request_connection_quick_insert_choose(6))

        self.assertEqual(
            host.calls,
            [
                ("set_library_query", ("logger",)),
                ("request_add_node_from_library", ("core.logger",)),
                ("request_rename_custom_workflow_from_library", ("wf-rename", "global")),
                ("request_set_custom_workflow_scope", ("wf-scope", "local")),
                ("request_delete_custom_workflow_from_library", ("wf-delete", "global")),
                ("set_graph_search_query", ("duplicate",)),
                ("set_graph_search_scope_enabled", ("content", False)),
                ("request_graph_search_move", (-1,)),
                ("request_graph_search_accept", ()),
                ("request_close_graph_search", ()),
                ("request_graph_search_highlight", (3,)),
                ("request_graph_search_jump", (4,)),
                ("set_connection_quick_insert_query", ("start",)),
                ("request_connection_quick_insert_move", (1,)),
                ("request_connection_quick_insert_accept", ()),
                ("request_close_connection_quick_insert", ()),
                ("request_connection_quick_insert_highlight", (5,)),
                ("request_connection_quick_insert_choose", (6,)),
            ],
        )

    def test_bridge_uses_explicit_library_source_contract_when_injected(self) -> None:
        host = _ShellLibraryHostStub()
        presenter = _ShellLibraryHostStub()
        presenter.grouped_node_library_items = [{"kind": "item", "type_id": "core.start", "display_name": "Start"}]
        presenter.graph_search_query = "presenter search"
        presenter.connection_quick_insert_query = "presenter quick insert"
        host.shell_library_presenter = presenter

        bridge = ShellLibraryBridge(shell_window=host, library_source=presenter)

        self.assertIs(bridge.library_source, presenter)
        self.assertEqual(bridge.grouped_node_library_items, presenter.grouped_node_library_items)
        self.assertEqual(bridge.graph_search_query, "presenter search")
        self.assertEqual(bridge.connection_quick_insert_query, "presenter quick insert")

        bridge.set_library_query("from presenter")
        self.assertEqual(presenter.calls, [("set_library_query", ("from presenter",))])
        self.assertEqual(host.calls, [])

    def test_bridge_wraps_shell_window_and_routes_through_host_library_presenter_when_present(self) -> None:
        host = _ShellLibraryHostStub()
        presenter = _ShellLibraryHostStub()
        presenter.graph_search_query = "presenter search"
        host.shell_library_presenter = presenter

        bridge = ShellLibraryBridge(shell_window=host)

        self.assertIsNot(bridge.library_source, presenter)
        self.assertEqual(bridge.graph_search_query, presenter.graph_search_query)
        bridge.set_library_query("host contract")
        self.assertEqual(presenter.calls, [("set_library_query", ("host contract",))])
        self.assertEqual(host.calls, [])

    def test_bridge_re_emits_shell_signals(self) -> None:
        host = _ShellLibraryHostStub()
        bridge = ShellLibraryBridge(shell_window=host, library_source=host)
        seen = {
            "node_library_changed": 0,
            "library_pane_reset_requested": 0,
            "graph_search_changed": 0,
            "connection_quick_insert_changed": 0,
            "graph_hint_changed": 0,
        }

        bridge.node_library_changed.connect(
            lambda: seen.__setitem__("node_library_changed", seen["node_library_changed"] + 1)
        )
        bridge.library_pane_reset_requested.connect(
            lambda: seen.__setitem__("library_pane_reset_requested", seen["library_pane_reset_requested"] + 1)
        )
        bridge.graph_search_changed.connect(
            lambda: seen.__setitem__("graph_search_changed", seen["graph_search_changed"] + 1)
        )
        bridge.connection_quick_insert_changed.connect(
            lambda: seen.__setitem__(
                "connection_quick_insert_changed",
                seen["connection_quick_insert_changed"] + 1,
            )
        )
        bridge.graph_hint_changed.connect(
            lambda: seen.__setitem__("graph_hint_changed", seen["graph_hint_changed"] + 1)
        )

        host.node_library_changed.emit()
        host.library_pane_reset_requested.emit()
        host.graph_search_changed.emit()
        host.connection_quick_insert_changed.emit()
        host.graph_hint_changed.emit()

        self.assertEqual(
            seen,
            {
                "node_library_changed": 1,
                "library_pane_reset_requested": 1,
                "graph_search_changed": 1,
                "connection_quick_insert_changed": 1,
                "graph_hint_changed": 1,
            },
        )


class ShellInspectorBridgeTests(unittest.TestCase):
    def test_bridge_forwards_shell_inspector_state_and_actions(self) -> None:
        host = _ShellInspectorHostStub()
        bridge = ShellInspectorBridge(shell_window=host, inspector_source=host)

        self.assertIs(bridge.shell_window, host)
        self.assertIs(bridge.inspector_source, host)
        self.assertEqual(bridge.selected_node_title, "Inspector Node")
        self.assertEqual(bridge.selected_node_subtitle, "Inspector subtitle")
        self.assertEqual(bridge.selected_node_summary, "Inspector Node\nType: passive.fixture")
        self.assertEqual(bridge.selected_node_header_items, host.selected_node_header_items)
        self.assertTrue(bridge.has_selected_node)
        self.assertTrue(bridge.selected_node_collapsible)
        self.assertFalse(bridge.selected_node_collapsed)
        self.assertFalse(bridge.selected_node_is_subnode_pin)
        self.assertTrue(bridge.selected_node_is_subnode_shell)
        self.assertEqual(bridge.selected_node_property_items, host.selected_node_property_items)
        self.assertEqual(bridge.selected_node_port_items, host.selected_node_port_items)
        self.assertEqual(bridge.pin_data_type_options, host.pin_data_type_options)

        self.assertEqual(bridge.request_add_selected_subnode_pin("out"), "port-1")
        self.assertTrue(bridge.set_selected_port_label("exec_in", "Renamed Input"))
        self.assertTrue(bridge.request_remove_selected_port("exec_in"))
        bridge.set_selected_node_collapsed(True)
        self.assertTrue(bridge.request_ungroup_selected_nodes())
        bridge.set_selected_node_property("message", "updated from bridge")
        self.assertEqual(
            bridge.browse_selected_node_property_path("source_path", "C:/temp"),
            "C:/temp/selected.txt",
        )
        bridge.set_selected_port_exposed("exec_in", False)

        self.assertEqual(
            host.calls,
            [
                ("request_add_selected_subnode_pin", ("out",)),
                ("set_selected_port_label", ("exec_in", "Renamed Input")),
                ("request_remove_selected_port", ("exec_in",)),
                ("set_selected_node_collapsed", (True,)),
                ("request_ungroup_selected_nodes", ()),
                ("set_selected_node_property", ("message", "updated from bridge")),
                ("browse_selected_node_property_path", ("source_path", "C:/temp")),
                ("set_selected_port_exposed", ("exec_in", False)),
            ],
        )

    def test_bridge_uses_explicit_inspector_source_contract_when_injected(self) -> None:
        host = _ShellInspectorHostStub()
        presenter = _ShellInspectorHostStub()
        presenter.selected_node_title = "Presenter Node"
        presenter.selected_node_property_items = [
            {"key": "message", "label": "Message", "value": "from presenter", "editor_mode": "text"}
        ]
        host.shell_inspector_presenter = presenter

        bridge = ShellInspectorBridge(shell_window=host, inspector_source=presenter)

        self.assertIs(bridge.inspector_source, presenter)
        self.assertEqual(bridge.selected_node_title, "Presenter Node")
        self.assertEqual(bridge.selected_node_property_items, presenter.selected_node_property_items)

        bridge.set_selected_node_property("message", "updated")
        self.assertEqual(presenter.calls, [("set_selected_node_property", ("message", "updated"))])
        self.assertEqual(host.calls, [])

    def test_bridge_wraps_shell_window_and_routes_through_host_inspector_presenter_when_present(self) -> None:
        host = _ShellInspectorHostStub()
        presenter = _ShellInspectorHostStub()
        presenter.selected_node_title = "Presenter Node"
        host.shell_inspector_presenter = presenter

        bridge = ShellInspectorBridge(shell_window=host)

        self.assertIsNot(bridge.inspector_source, presenter)
        self.assertEqual(bridge.selected_node_title, presenter.selected_node_title)
        bridge.set_selected_node_property("message", "host update")
        self.assertEqual(presenter.calls, [("set_selected_node_property", ("message", "host update"))])
        self.assertEqual(host.calls, [])

    def test_bridge_re_emits_shell_state_signals(self) -> None:
        host = _ShellInspectorHostStub()
        bridge = ShellInspectorBridge(shell_window=host, inspector_source=host)
        seen = {
            "selected_node_changed": 0,
            "workspace_state_changed": 0,
            "inspector_state_changed": 0,
        }

        bridge.selected_node_changed.connect(
            lambda: seen.__setitem__("selected_node_changed", seen["selected_node_changed"] + 1)
        )
        bridge.workspace_state_changed.connect(
            lambda: seen.__setitem__("workspace_state_changed", seen["workspace_state_changed"] + 1)
        )
        bridge.inspector_state_changed.connect(
            lambda: seen.__setitem__("inspector_state_changed", seen["inspector_state_changed"] + 1)
        )

        host.selected_node_changed.emit()
        host.workspace_state_changed.emit()

        self.assertEqual(
            seen,
            {
                "selected_node_changed": 1,
                "workspace_state_changed": 1,
                "inspector_state_changed": 2,
            },
        )


class GraphCanvasBridgeTests(unittest.TestCase):
    def test_graphics_state_bridge_exposes_read_heavy_canvas_state_and_re_emits_signals(self) -> None:
        host = _GraphCanvasShellHostStub()
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = GraphCanvasStateBridge(
            host,
            shell_window=host,
            canvas_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )
        seen = {
            "graphics_preferences_changed": 0,
            "snap_to_grid_changed": 0,
            "scene_nodes_changed": 0,
            "scene_edges_changed": 0,
            "scene_selection_changed": 0,
            "view_state_changed": 0,
        }

        bridge.graphics_preferences_changed.connect(
            lambda: seen.__setitem__("graphics_preferences_changed", seen["graphics_preferences_changed"] + 1)
        )
        bridge.snap_to_grid_changed.connect(
            lambda: seen.__setitem__("snap_to_grid_changed", seen["snap_to_grid_changed"] + 1)
        )
        bridge.scene_nodes_changed.connect(
            lambda: seen.__setitem__("scene_nodes_changed", seen["scene_nodes_changed"] + 1)
        )
        bridge.scene_edges_changed.connect(
            lambda: seen.__setitem__("scene_edges_changed", seen["scene_edges_changed"] + 1)
        )
        bridge.scene_selection_changed.connect(
            lambda: seen.__setitem__("scene_selection_changed", seen["scene_selection_changed"] + 1)
        )
        bridge.view_state_changed.connect(
            lambda: seen.__setitem__("view_state_changed", seen["view_state_changed"] + 1)
        )

        self.assertIs(bridge.parent(), host)
        self.assertIs(bridge.shell_window, host)
        self.assertIs(bridge.canvas_source, host)
        self.assertIs(bridge.scene_bridge, scene)
        self.assertIs(bridge.view_bridge, view)
        self.assertTrue(bridge.graphics_minimap_expanded)
        self.assertTrue(bridge.graphics_show_grid)
        self.assertEqual(bridge.graphics_grid_style, "lines")
        self.assertTrue(bridge.graphics_show_minimap)
        self.assertTrue(bridge.graphics_show_port_labels)
        self.assertTrue(bridge.graphics_node_shadow)
        self.assertEqual(bridge.graphics_shadow_strength, 70)
        self.assertEqual(bridge.graphics_shadow_softness, 50)
        self.assertEqual(bridge.graphics_shadow_offset, 4)
        self.assertEqual(bridge.graphics_performance_mode, "full_fidelity")
        self.assertTrue(bridge.snap_to_grid_enabled)
        self.assertEqual(bridge.snap_grid_size, 24.0)
        self.assertEqual(bridge.center_x, 18.5)
        self.assertEqual(bridge.center_y, -42.0)
        self.assertEqual(bridge.zoom_value, 1.75)
        self.assertEqual(bridge.visible_scene_rect_payload, view.visible_scene_rect_payload)
        self.assertEqual(bridge.nodes_model, scene.nodes_model)
        self.assertEqual(bridge.minimap_nodes_model, scene.minimap_nodes_model)
        self.assertEqual(bridge.workspace_scene_bounds_payload, scene.workspace_scene_bounds_payload)
        self.assertEqual(bridge.edges_model, scene.edges_model)
        self.assertEqual(bridge.selected_node_lookup, scene.selected_node_lookup)

        host.graphics_preferences_changed.emit()
        host.snap_to_grid_changed.emit()
        scene.nodes_changed.emit()
        scene.edges_changed.emit()
        scene.selection_changed.emit()
        view.view_state_changed.emit()

        self.assertEqual(
            seen,
            {
                "graphics_preferences_changed": 1,
                "snap_to_grid_changed": 1,
                "scene_nodes_changed": 1,
                "scene_edges_changed": 1,
                "scene_selection_changed": 1,
                "view_state_changed": 1,
            },
        )

    def test_state_bridge_does_not_discover_graph_canvas_presenter_from_shell_window(self) -> None:
        host = _GraphCanvasShellHostStub()
        presenter = _GraphCanvasShellHostStub()
        presenter.graphics_show_grid = False
        presenter.graphics_grid_style = "points"
        presenter.graphics_performance_mode = "max_performance"
        host.graph_canvas_presenter = presenter

        bridge = GraphCanvasStateBridge(shell_window=host)

        self.assertIs(bridge.canvas_source, host)
        self.assertTrue(bridge.graphics_show_grid)
        self.assertEqual(bridge.graphics_grid_style, "lines")
        self.assertEqual(bridge.graphics_performance_mode, "full_fidelity")

    def test_state_bridge_exposes_scene_compatibility_queries_for_bridge_first_qml(self) -> None:
        scene = _GraphCanvasSceneBridgeStub()
        bridge = GraphCanvasStateBridge(scene_bridge=scene)

        self.assertTrue(bridge.are_port_kinds_compatible("exec", "exec"))
        self.assertTrue(bridge.are_data_types_compatible("text", "text"))
        self.assertEqual(
            scene.calls,
            [
                ("are_port_kinds_compatible", ("exec", "exec")),
                ("are_data_types_compatible", ("text", "text")),
            ],
        )

    def test_graphics_state_node_execution_bridge_filters_lookup_to_scene_workspace_and_re_emits(self) -> None:
        host = _GraphCanvasShellHostStub()
        scene = _GraphCanvasSceneBridgeStub()
        bridge = GraphCanvasStateBridge(
            host,
            shell_window=host,
            canvas_source=host,
            scene_bridge=scene,
            view_bridge=_GraphCanvasViewBridgeStub(),
        )
        seen = {"node_execution_state_changed": 0}
        bridge.node_execution_state_changed.connect(
            lambda: seen.__setitem__(
                "node_execution_state_changed",
                seen["node_execution_state_changed"] + 1,
            )
        )

        host.run_state.node_execution_workspace_id = "ws-1"
        host.run_state.running_node_ids.add("node_running")
        host.run_state.completed_node_ids.add("node_completed")
        host.run_state.node_execution_revision = 8
        host.node_execution_state_changed.emit()

        self.assertEqual(bridge.running_node_lookup, {"node_running": True})
        self.assertEqual(bridge.completed_node_lookup, {"node_completed": True})
        self.assertEqual(bridge.node_execution_revision, 8)

        scene.workspace_id = "ws-2"
        scene.workspace_changed.emit("ws-2")

        self.assertEqual(bridge.running_node_lookup, {})
        self.assertEqual(bridge.completed_node_lookup, {})
        self.assertEqual(bridge.node_execution_revision, 8)
        self.assertEqual(seen["node_execution_state_changed"], 2)

    def test_command_bridge_routes_canvas_commands_to_explicit_canvas_host_scene_and_view_sources(self) -> None:
        host = _GraphCanvasShellHostStub()
        presenter = _GraphCanvasShellHostStub()
        host_source = _GraphCanvasShellHostStub()
        host.graph_canvas_presenter = presenter
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = GraphCanvasCommandBridge(
            host,
            shell_window=host,
            canvas_source=presenter,
            host_source=host_source,
            scene_bridge=scene,
            view_bridge=view,
        )

        self.assertIs(bridge.parent(), host)
        self.assertIs(bridge.shell_window, host)
        self.assertIs(bridge.canvas_source, presenter)
        self.assertIs(bridge.host_source, host_source)
        self.assertIs(bridge.scene_bridge, scene)
        self.assertIs(bridge.view_bridge, view)

        bridge.set_graphics_minimap_expanded(False)
        bridge.adjust_zoom(1.15)
        bridge.pan_by(-12.0, 8.0)
        bridge.set_viewport_size(1280.0, 720.0)
        bridge.center_on_scene_point(96.0, 144.0)
        self.assertTrue(bridge.request_open_subnode_scope("subnode-1"))
        self.assertEqual(
            bridge.browse_node_property_path("node-1", "source_path", "C:/temp/current.txt"),
            "C:/temp/from-canvas-bridge.txt",
        )
        self.assertTrue(
            bridge.request_drop_node_from_library(
                "core.logger",
                120.0,
                240.0,
                "port",
                "node-1",
                "exec_in",
                "edge-1",
            )
        )
        self.assertTrue(bridge.request_connect_ports("node-1", "exec_out", "node-2", "exec_in"))
        self.assertTrue(
            bridge.request_open_connection_quick_insert(
                "node-1",
                "exec_out",
                20.0,
                30.0,
                400.0,
                300.0,
            )
        )
        bridge.request_open_canvas_quick_insert(15.0, 25.0, 115.0, 215.0)
        self.assertTrue(bridge.request_publish_custom_workflow_from_node("node-1"))
        self.assertTrue(bridge.request_delete_selected_graph_items(["edge-1"]))
        self.assertTrue(bridge.request_navigate_scope_parent())
        self.assertTrue(bridge.request_navigate_scope_root())
        bridge.select_node("node-1", True)
        bridge.clear_selection()
        bridge.select_nodes_in_rect(1.0, 2.0, 3.0, 4.0, True)
        bridge.set_node_property("node-1", "message", "hello")
        bridge.set_pending_surface_action("node-1")
        self.assertTrue(bridge.consume_pending_surface_action("node-1"))
        self.assertTrue(bridge.set_node_properties("node-1", {"message": "bridge"}))
        self.assertTrue(bridge.are_port_kinds_compatible("exec", "exec"))
        self.assertTrue(bridge.are_data_types_compatible("text", "text"))
        self.assertTrue(bridge.move_nodes_by_delta(["node-1", "node-2"], 10.0, -5.0))
        bridge.move_node("node-1", 160.0, 220.0)
        bridge.resize_node("node-1", 320.0, 180.0)
        bridge.set_node_geometry("node-1", 150.0, 210.0, 340.0, 190.0)
        bridge.set_graph_cursor_shape(13)
        bridge.clear_graph_cursor_shape()
        self.assertEqual(
            bridge.describe_pdf_preview("C:/temp/preview.pdf", 2),
            {
                "source": "C:/temp/preview.pdf",
                "page_number": 2,
                "valid": True,
            },
        )
        self.assertTrue(bridge.request_edit_flow_edge_style("edge-1"))
        self.assertTrue(bridge.request_edit_flow_edge_label("edge-1"))
        self.assertTrue(bridge.request_reset_flow_edge_style("edge-1"))
        self.assertTrue(bridge.request_copy_flow_edge_style("edge-1"))
        self.assertTrue(bridge.request_paste_flow_edge_style("edge-1"))
        self.assertTrue(bridge.request_remove_edge("edge-1"))
        self.assertTrue(bridge.request_edit_passive_node_style("node-1"))
        self.assertTrue(bridge.request_reset_passive_node_style("node-1"))
        self.assertTrue(bridge.request_copy_passive_node_style("node-1"))
        self.assertTrue(bridge.request_paste_passive_node_style("node-1"))
        self.assertTrue(bridge.request_rename_node("node-1"))
        self.assertTrue(bridge.request_ungroup_node("node-1"))
        self.assertTrue(bridge.request_remove_node("node-1"))

        self.assertEqual(
            presenter.calls,
            [
                ("set_graphics_minimap_expanded", (False,)),
                ("request_open_subnode_scope", ("subnode-1",)),
                ("browse_node_property_path", ("node-1", "source_path", "C:/temp/current.txt")),
                (
                    "request_drop_node_from_library",
                    ("core.logger", 120.0, 240.0, "port", "node-1", "exec_in", "edge-1"),
                ),
                ("request_connect_ports", ("node-1", "exec_out", "node-2", "exec_in")),
                (
                    "request_open_connection_quick_insert",
                    ("node-1", "exec_out", 20.0, 30.0, 400.0, 300.0),
                ),
                ("request_open_canvas_quick_insert", (15.0, 25.0, 115.0, 215.0)),
                ("request_publish_custom_workflow_from_node", ("node-1",)),
            ],
        )
        self.assertEqual(
            host_source.calls,
            [
                ("request_delete_selected_graph_items", (["edge-1"],)),
                ("request_navigate_scope_parent", ()),
                ("request_navigate_scope_root", ()),
                ("set_graph_cursor_shape", (13,)),
                ("clear_graph_cursor_shape", ()),
                ("describe_pdf_preview", ("C:/temp/preview.pdf", 2)),
                ("request_edit_flow_edge_style", ("edge-1",)),
                ("request_edit_flow_edge_label", ("edge-1",)),
                ("request_reset_flow_edge_style", ("edge-1",)),
                ("request_copy_flow_edge_style", ("edge-1",)),
                ("request_paste_flow_edge_style", ("edge-1",)),
                ("request_remove_edge", ("edge-1",)),
                ("request_edit_passive_node_style", ("node-1",)),
                ("request_reset_passive_node_style", ("node-1",)),
                ("request_copy_passive_node_style", ("node-1",)),
                ("request_paste_passive_node_style", ("node-1",)),
                ("request_rename_node", ("node-1",)),
                ("request_ungroup_node", ("node-1",)),
                ("request_remove_node", ("node-1",)),
            ],
        )
        self.assertEqual(
            scene.calls,
            [
                ("select_node", ("node-1", True)),
                ("clear_selection", ()),
                ("select_nodes_in_rect", (1.0, 2.0, 3.0, 4.0, True)),
                ("set_node_property", ("node-1", "message", "hello")),
                ("set_pending_surface_action", ("node-1",)),
                ("consume_pending_surface_action", ("node-1",)),
                ("set_node_properties", ("node-1", {"message": "bridge"})),
                ("are_port_kinds_compatible", ("exec", "exec")),
                ("are_data_types_compatible", ("text", "text")),
                ("move_nodes_by_delta", (["node-1", "node-2"], 10.0, -5.0)),
                ("move_node", ("node-1", 160.0, 220.0)),
                ("resize_node", ("node-1", 320.0, 180.0)),
                ("set_node_geometry", ("node-1", 150.0, 210.0, 340.0, 190.0)),
            ],
        )
        self.assertEqual(
            view.calls,
            [
                ("adjust_zoom", (1.15,)),
                ("pan_by", (-12.0, 8.0)),
                ("set_viewport_size", (1280.0, 720.0)),
                ("center_on_scene_point", (96.0, 144.0)),
            ],
        )

    def test_command_bridge_does_not_discover_graph_canvas_presenter_from_shell_window(self) -> None:
        host = _GraphCanvasShellHostStub()
        presenter = _GraphCanvasShellHostStub()
        host.graph_canvas_presenter = presenter

        bridge = GraphCanvasCommandBridge(shell_window=host)

        self.assertIs(bridge.canvas_source, host)
        self.assertIs(bridge.host_source, host)
        bridge.set_graphics_minimap_expanded(False)
        self.assertTrue(bridge.request_open_subnode_scope("subnode-1"))
        self.assertEqual(
            host.calls,
            [
                ("set_graphics_minimap_expanded", (False,)),
                ("request_open_subnode_scope", ("subnode-1",)),
            ],
        )
        self.assertEqual(presenter.calls, [])

    def test_graphics_bridge_uses_explicit_shell_host_and_forwards_canvas_calls(self) -> None:
        host = _GraphCanvasShellHostStub()
        host_source = _GraphCanvasShellHostStub()
        parent = _GraphCanvasParentStub(host)
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        state_bridge = GraphCanvasStateBridge(
            parent,
            shell_window=host,
            canvas_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )
        command_bridge = GraphCanvasCommandBridge(
            parent,
            shell_window=host,
            canvas_source=host,
            host_source=host_source,
            scene_bridge=scene,
            view_bridge=view,
        )
        bridge = GraphCanvasBridge(
            parent,
            shell_window=host,
            scene_bridge=scene,
            view_bridge=view,
            state_bridge=state_bridge,
            command_bridge=command_bridge,
        )

        self.assertIs(bridge.parent(), parent)
        self.assertIs(bridge.shell_window, host)
        self.assertIsNot(bridge.shell_window, bridge.parent())
        self.assertIs(bridge.scene_bridge, scene)
        self.assertIs(bridge.view_bridge, view)
        self.assertIs(bridge.state_bridge, state_bridge)
        self.assertIs(bridge.command_bridge, command_bridge)
        self.assertTrue(bridge.graphics_minimap_expanded)
        self.assertTrue(bridge.graphics_show_grid)
        self.assertTrue(bridge.graphics_show_minimap)
        self.assertTrue(bridge.graphics_show_port_labels)
        self.assertTrue(bridge.graphics_node_shadow)
        self.assertEqual(bridge.graphics_shadow_strength, 70)
        self.assertEqual(bridge.graphics_shadow_softness, 50)
        self.assertEqual(bridge.graphics_shadow_offset, 4)
        self.assertEqual(bridge.graphics_performance_mode, "full_fidelity")
        self.assertTrue(bridge.snap_to_grid_enabled)
        self.assertEqual(bridge.snap_grid_size, 24.0)
        self.assertEqual(bridge.center_x, 18.5)
        self.assertEqual(bridge.center_y, -42.0)
        self.assertEqual(bridge.zoom_value, 1.75)
        self.assertEqual(bridge.nodes_model, scene.nodes_model)
        self.assertEqual(bridge.edges_model, scene.edges_model)
        self.assertEqual(bridge.selected_node_lookup, scene.selected_node_lookup)

        bridge.set_graphics_minimap_expanded(False)
        bridge.set_graphics_show_port_labels(False)
        self.assertFalse(bridge.graphics_show_port_labels)
        bridge.set_graphics_performance_mode("max_performance")
        bridge.adjust_zoom(1.15)
        bridge.pan_by(-12.0, 8.0)
        bridge.set_viewport_size(1280.0, 720.0)
        self.assertTrue(bridge.request_open_subnode_scope("subnode-1"))
        self.assertEqual(
            bridge.browse_node_property_path("node-1", "source_path", "C:/temp/current.txt"),
            "C:/temp/from-canvas-bridge.txt",
        )
        self.assertTrue(
            bridge.request_drop_node_from_library(
                "core.logger",
                120.0,
                240.0,
                "port",
                "node-1",
                "exec_in",
                "edge-1",
            )
        )
        self.assertTrue(bridge.request_connect_ports("node-1", "exec_out", "node-2", "exec_in"))
        self.assertTrue(
            bridge.request_open_connection_quick_insert(
                "node-1",
                "exec_out",
                20.0,
                30.0,
                400.0,
                300.0,
            )
        )
        bridge.select_node("node-1", True)
        bridge.set_node_property("node-1", "message", "hello")
        self.assertTrue(bridge.are_port_kinds_compatible("exec", "exec"))
        self.assertTrue(bridge.are_data_types_compatible("text", "text"))
        self.assertTrue(bridge.move_nodes_by_delta(["node-1", "node-2"], 10.0, -5.0))
        bridge.move_node("node-1", 160.0, 220.0)
        bridge.resize_node("node-1", 320.0, 180.0)
        bridge.set_node_geometry("node-1", 150.0, 210.0, 340.0, 190.0)

        self.assertEqual(
            host.calls,
            [
                ("set_graphics_minimap_expanded", (False,)),
                ("set_graphics_show_port_labels", (False,)),
                ("set_graphics_performance_mode", ("max_performance",)),
                ("request_open_subnode_scope", ("subnode-1",)),
                ("browse_node_property_path", ("node-1", "source_path", "C:/temp/current.txt")),
                (
                    "request_drop_node_from_library",
                    ("core.logger", 120.0, 240.0, "port", "node-1", "exec_in", "edge-1"),
                ),
                ("request_connect_ports", ("node-1", "exec_out", "node-2", "exec_in")),
                (
                    "request_open_connection_quick_insert",
                    ("node-1", "exec_out", 20.0, 30.0, 400.0, 300.0),
                ),
            ],
        )
        self.assertEqual(host_source.calls, [])
        self.assertEqual(
            scene.calls,
            [
                ("select_node", ("node-1", True)),
                ("set_node_property", ("node-1", "message", "hello")),
                ("are_port_kinds_compatible", ("exec", "exec")),
                ("are_data_types_compatible", ("text", "text")),
                ("move_nodes_by_delta", (["node-1", "node-2"], 10.0, -5.0)),
                ("move_node", ("node-1", 160.0, 220.0)),
                ("resize_node", ("node-1", 320.0, 180.0)),
                ("set_node_geometry", ("node-1", 150.0, 210.0, 340.0, 190.0)),
            ],
        )
        self.assertEqual(
            view.calls,
            [
                ("adjust_zoom", (1.15,)),
                ("pan_by", (-12.0, 8.0)),
                ("set_viewport_size", (1280.0, 720.0)),
            ],
        )

    def test_graphics_bridge_uses_explicit_graph_canvas_source_contract_when_injected(self) -> None:
        host = _GraphCanvasShellHostStub()
        presenter = _GraphCanvasShellHostStub()
        host_source = _GraphCanvasShellHostStub()
        presenter.graphics_show_grid = False
        presenter.graphics_grid_style = "points"
        presenter.graphics_show_minimap = False
        presenter.graphics_show_port_labels = False
        presenter.graphics_performance_mode = "max_performance"
        presenter.snap_to_grid_enabled = False
        host.graph_canvas_presenter = presenter
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()

        bridge = GraphCanvasBridge(
            shell_window=host,
            scene_bridge=scene,
            view_bridge=view,
            state_bridge=GraphCanvasStateBridge(
                shell_window=host,
                canvas_source=presenter,
                scene_bridge=scene,
                view_bridge=view,
            ),
            command_bridge=GraphCanvasCommandBridge(
                shell_window=host,
                canvas_source=presenter,
                host_source=host_source,
                scene_bridge=scene,
                view_bridge=view,
            ),
        )

        self.assertFalse(bridge.graphics_show_grid)
        self.assertEqual(bridge.graphics_grid_style, "points")
        self.assertFalse(bridge.graphics_show_minimap)
        self.assertFalse(bridge.graphics_show_port_labels)
        self.assertEqual(bridge.graphics_performance_mode, "max_performance")
        self.assertFalse(bridge.snap_to_grid_enabled)

        bridge.set_graphics_minimap_expanded(False)
        bridge.set_graphics_show_port_labels(True)
        bridge.set_graphics_performance_mode("full_fidelity")
        self.assertEqual(
            presenter.calls,
            [
                ("set_graphics_minimap_expanded", (False,)),
                ("set_graphics_show_port_labels", (True,)),
                ("set_graphics_performance_mode", ("full_fidelity",)),
            ],
        )
        self.assertEqual(host.calls, [])
        self.assertEqual(host_source.calls, [])

    def test_bridge_re_emits_shell_scene_and_view_signals(self) -> None:
        host = _GraphCanvasShellHostStub()
        host_source = _GraphCanvasShellHostStub()
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = _build_explicit_graph_canvas_bridge(
            parent=host,
            shell_window=host,
            canvas_source=host,
            host_source=host_source,
            scene_bridge=scene,
            view_bridge=view,
        )
        seen = {
            "graphics_preferences_changed": 0,
            "snap_to_grid_changed": 0,
            "scene_nodes_changed": 0,
            "scene_edges_changed": 0,
            "view_state_changed": 0,
        }

        bridge.graphics_preferences_changed.connect(
            lambda: seen.__setitem__("graphics_preferences_changed", seen["graphics_preferences_changed"] + 1)
        )
        bridge.snap_to_grid_changed.connect(
            lambda: seen.__setitem__("snap_to_grid_changed", seen["snap_to_grid_changed"] + 1)
        )
        bridge.scene_nodes_changed.connect(
            lambda: seen.__setitem__("scene_nodes_changed", seen["scene_nodes_changed"] + 1)
        )
        bridge.scene_edges_changed.connect(
            lambda: seen.__setitem__("scene_edges_changed", seen["scene_edges_changed"] + 1)
        )
        bridge.view_state_changed.connect(
            lambda: seen.__setitem__("view_state_changed", seen["view_state_changed"] + 1)
        )

        host.graphics_preferences_changed.emit()
        host.snap_to_grid_changed.emit()
        scene.nodes_changed.emit()
        scene.edges_changed.emit()
        view.view_state_changed.emit()

        self.assertEqual(
            seen,
            {
                "graphics_preferences_changed": 1,
                "snap_to_grid_changed": 1,
                "scene_nodes_changed": 1,
                "scene_edges_changed": 1,
                "view_state_changed": 1,
            },
        )

    def test_bridge_forwards_selected_node_lookup(self) -> None:
        host = _GraphCanvasShellHostStub()
        host_source = _GraphCanvasShellHostStub()
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = _build_explicit_graph_canvas_bridge(
            parent=host,
            shell_window=host,
            canvas_source=host,
            host_source=host_source,
            scene_bridge=scene,
            view_bridge=view,
        )

        self.assertEqual(bridge.selected_node_lookup, {"node-1": True})

        scene.selected_node_lookup = {"node-1": True, "node-2": True}
        self.assertEqual(
            bridge.selected_node_lookup,
            {"node-1": True, "node-2": True},
        )

    def test_bridge_exposes_unified_canvas_contract_extensions(self) -> None:
        host = _GraphCanvasShellHostStub()
        host_source = _GraphCanvasShellHostStub()
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = _build_explicit_graph_canvas_bridge(
            shell_window=host,
            canvas_source=host,
            host_source=host_source,
            scene_bridge=scene,
            view_bridge=view,
        )

        self.assertEqual(bridge.visible_scene_rect_payload, view.visible_scene_rect_payload)
        self.assertEqual(bridge.minimap_nodes_model, scene.minimap_nodes_model)
        self.assertEqual(bridge.workspace_scene_bounds_payload, scene.workspace_scene_bounds_payload)

        bridge.center_on_scene_point(96.0, 144.0)
        bridge.request_open_canvas_quick_insert(15.0, 25.0, 115.0, 215.0)
        self.assertTrue(bridge.request_delete_selected_graph_items(["edge-1"]))
        self.assertTrue(bridge.request_navigate_scope_parent())
        self.assertTrue(bridge.request_navigate_scope_root())
        bridge.clear_selection()
        bridge.select_nodes_in_rect(1.0, 2.0, 3.0, 4.0, True)
        bridge.set_pending_surface_action("node-1")
        self.assertTrue(bridge.consume_pending_surface_action("node-1"))
        self.assertTrue(bridge.set_node_properties("node-1", {"message": "bridge"}))
        bridge.set_graph_cursor_shape(13)
        bridge.clear_graph_cursor_shape()
        self.assertEqual(
            bridge.describe_pdf_preview("C:/temp/preview.pdf", 2),
            {
                "source": "C:/temp/preview.pdf",
                "page_number": 2,
                "valid": True,
            },
        )
        self.assertTrue(bridge.request_edit_flow_edge_style("edge-1"))
        self.assertTrue(bridge.request_edit_flow_edge_label("edge-1"))
        self.assertTrue(bridge.request_reset_flow_edge_style("edge-1"))
        self.assertTrue(bridge.request_copy_flow_edge_style("edge-1"))
        self.assertTrue(bridge.request_paste_flow_edge_style("edge-1"))
        self.assertTrue(bridge.request_remove_edge("edge-1"))
        self.assertTrue(bridge.request_publish_custom_workflow_from_node("node-1"))
        self.assertTrue(bridge.request_edit_passive_node_style("node-1"))
        self.assertTrue(bridge.request_reset_passive_node_style("node-1"))
        self.assertTrue(bridge.request_copy_passive_node_style("node-1"))
        self.assertTrue(bridge.request_paste_passive_node_style("node-1"))
        self.assertTrue(bridge.request_rename_node("node-1"))
        self.assertTrue(bridge.request_ungroup_node("node-1"))
        self.assertTrue(bridge.request_remove_node("node-1"))

        self.assertEqual(
            host.calls,
            [
                ("request_open_canvas_quick_insert", (15.0, 25.0, 115.0, 215.0)),
                ("request_publish_custom_workflow_from_node", ("node-1",)),
            ],
        )
        self.assertEqual(
            host_source.calls,
            [
                ("request_delete_selected_graph_items", (["edge-1"],)),
                ("request_navigate_scope_parent", ()),
                ("request_navigate_scope_root", ()),
                ("set_graph_cursor_shape", (13,)),
                ("clear_graph_cursor_shape", ()),
                ("describe_pdf_preview", ("C:/temp/preview.pdf", 2)),
                ("request_edit_flow_edge_style", ("edge-1",)),
                ("request_edit_flow_edge_label", ("edge-1",)),
                ("request_reset_flow_edge_style", ("edge-1",)),
                ("request_copy_flow_edge_style", ("edge-1",)),
                ("request_paste_flow_edge_style", ("edge-1",)),
                ("request_remove_edge", ("edge-1",)),
                ("request_edit_passive_node_style", ("node-1",)),
                ("request_reset_passive_node_style", ("node-1",)),
                ("request_copy_passive_node_style", ("node-1",)),
                ("request_paste_passive_node_style", ("node-1",)),
                ("request_rename_node", ("node-1",)),
                ("request_ungroup_node", ("node-1",)),
                ("request_remove_node", ("node-1",)),
            ],
        )
        self.assertEqual(
            scene.calls,
            [
                ("clear_selection", ()),
                ("select_nodes_in_rect", (1.0, 2.0, 3.0, 4.0, True)),
                ("set_pending_surface_action", ("node-1",)),
                ("consume_pending_surface_action", ("node-1",)),
                ("set_node_properties", ("node-1", {"message": "bridge"})),
            ],
        )
        self.assertEqual(
            view.calls,
            [
                ("center_on_scene_point", (96.0, 144.0)),
            ],
        )

    def test_graphics_bridge_exposes_comment_backdrop_payload_model_from_scene_bridge(self) -> None:
        scene = _GraphCanvasSceneBridgeStub()
        bridge = GraphCanvasBridge(scene_bridge=scene, view_bridge=_GraphCanvasViewBridgeStub())

        self.assertEqual(bridge.backdrop_nodes_model, scene.backdrop_nodes_model)

        scene.backdrop_nodes_model = [
            {"node_id": "backdrop-1", "selected": False},
            {"node_id": "backdrop-2", "selected": True},
        ]
        self.assertEqual(bridge.backdrop_nodes_model, scene.backdrop_nodes_model)

    def test_graphics_bridge_keeps_safe_defaults_without_shell_host(self) -> None:
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = GraphCanvasBridge(scene_bridge=scene, view_bridge=view)

        self.assertIsNone(bridge.shell_window)
        self.assertTrue(bridge.graphics_minimap_expanded)
        self.assertTrue(bridge.graphics_show_grid)
        self.assertEqual(bridge.graphics_grid_style, "lines")
        self.assertTrue(bridge.graphics_show_minimap)
        self.assertTrue(bridge.graphics_node_shadow)
        self.assertEqual(bridge.graphics_shadow_strength, 70)
        self.assertEqual(bridge.graphics_shadow_softness, 50)
        self.assertEqual(bridge.graphics_shadow_offset, 4)
        self.assertEqual(bridge.graphics_performance_mode, "full_fidelity")
        self.assertFalse(bridge.snap_to_grid_enabled)
        self.assertEqual(bridge.snap_grid_size, 20.0)
        self.assertFalse(bridge.request_open_subnode_scope("subnode-1"))


class MainWindowGraphCanvasBridgeTests(SharedMainWindowShellTestBase):
    def test_qml_context_registers_only_state_command_and_view_canvas_bridges(self) -> None:
        context = self.window.quick_widget.rootContext()
        graph_canvas_state_bridge = context.contextProperty("graphCanvasStateBridge")
        graph_canvas_command_bridge = context.contextProperty("graphCanvasCommandBridge")
        graph_canvas_view_bridge = context.contextProperty("graphCanvasViewBridge")

        self.assertIsInstance(graph_canvas_state_bridge, GraphCanvasStateBridge)
        self.assertIs(graph_canvas_state_bridge.parent(), self.window)
        self.assertIs(graph_canvas_state_bridge.shell_window, self.window)
        self.assertIs(graph_canvas_state_bridge.canvas_source, self.window.graph_canvas_presenter)
        self.assertIs(graph_canvas_state_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_state_bridge.view_bridge, self.window.view)

        self.assertIsInstance(graph_canvas_command_bridge, GraphCanvasCommandBridge)
        self.assertIs(graph_canvas_command_bridge.parent(), self.window)
        self.assertIs(graph_canvas_command_bridge.shell_window, self.window)
        self.assertIs(graph_canvas_command_bridge.canvas_source, self.window.graph_canvas_presenter)
        self.assertIs(graph_canvas_command_bridge.host_source, self.window.graph_canvas_host_presenter)
        self.assertIs(graph_canvas_command_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_command_bridge.view_bridge, self.window.view)
        self.assertIs(graph_canvas_view_bridge, self.window.view)
        self.assertIs(graph_canvas_view_bridge.parent(), self.window)

        viewer_session_bridge = context.contextProperty("viewerSessionBridge")
        self.assertIsInstance(viewer_session_bridge, ViewerSessionBridge)
        self.assertIs(viewer_session_bridge.parent(), self.window)
        self.assertEqual(
            viewer_session_bridge.active_workspace_id,
            self.window.workspace_manager.active_workspace_id(),
        )

        viewer_host_service = context.contextProperty("viewerHostService")
        self.assertIsInstance(viewer_host_service, ViewerHostService)
        self.assertIs(viewer_host_service.parent(), self.window)
        self.assertIs(viewer_host_service.overlay_manager, self.window.embedded_viewer_overlay_manager)

        self.assertIsNone(context.contextProperty("graphCanvasBridge"))

    def test_shell_window_keeps_split_canvas_bridge_aliases_in_sync_with_context_bundle(self) -> None:
        bridges = self.window._shell_context_bridges
        context_bindings = dict(self.window._shell_qml_context_property_bindings)

        self.assertIs(self.window.graph_canvas_state_bridge, bridges.graph_canvas_state_bridge)
        self.assertIs(self.window.graph_canvas_command_bridge, bridges.graph_canvas_command_bridge)
        self.assertIs(
            self.window.viewer_session_bridge,
            context_bindings["viewerSessionBridge"],
        )
        self.assertIs(
            self.window.viewer_host_service,
            context_bindings["viewerHostService"],
        )
        self.assertIs(context_bindings["graphCanvasViewBridge"], self.window.view)

    def test_shell_window_and_split_graph_canvas_bridges_share_persisted_port_label_preference_path(self) -> None:
        graph_canvas_state_bridge = self.window.graph_canvas_state_bridge
        graph_canvas_command_bridge = self.window.graph_canvas_command_bridge

        self.assertTrue(self.window.graphics_show_port_labels)
        self.assertTrue(graph_canvas_state_bridge.graphics_show_port_labels)

        self.window.set_graphics_show_port_labels(False)
        self.app.processEvents()

        self.assertFalse(self.window.graphics_show_port_labels)
        self.assertFalse(graph_canvas_state_bridge.graphics_show_port_labels)
        persisted = json.loads(self._app_preferences_path.read_text(encoding="utf-8"))
        self.assertFalse(persisted["graphics"]["canvas"]["show_port_labels"])

        graph_canvas_command_bridge.set_graphics_show_port_labels(True)
        self.app.processEvents()

        self.assertTrue(self.window.graphics_show_port_labels)
        self.assertTrue(graph_canvas_state_bridge.graphics_show_port_labels)
        persisted = json.loads(self._app_preferences_path.read_text(encoding="utf-8"))
        self.assertTrue(persisted["graphics"]["canvas"]["show_port_labels"])

    def test_main_window_node_execution_bridge_shell_helpers_drive_bridge_lookup_contract(self) -> None:
        bridge = self.window.graph_canvas_state_bridge
        workspace_id = self.window.scene.workspace_id

        self.assertTrue(workspace_id)
        self.assertEqual(bridge.running_node_lookup, {})
        self.assertEqual(bridge.completed_node_lookup, {})

        self.window.mark_node_execution_running(workspace_id, "node_exec")
        self.app.processEvents()

        first_revision = bridge.node_execution_revision
        self.assertEqual(bridge.running_node_lookup, {"node_exec": True})
        self.assertEqual(bridge.completed_node_lookup, {})

        self.window.mark_node_execution_completed(workspace_id, "node_exec")
        self.app.processEvents()

        self.assertGreater(bridge.node_execution_revision, first_revision)
        self.assertEqual(bridge.running_node_lookup, {})
        self.assertEqual(bridge.completed_node_lookup, {"node_exec": True})

        self.window.clear_node_execution_visualization_state()
        self.app.processEvents()

        self.assertEqual(bridge.running_node_lookup, {})
        self.assertEqual(bridge.completed_node_lookup, {})


class SharedUiSupportBoundaryTests(unittest.TestCase):
    def test_packet_owned_shared_helpers_route_through_neutral_ui_support_module(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/graph_scene_payload_builder.py": (
                (
                    "from ea_node_editor.ui.shell.window_library_inspector import build_inline_property_items",
                ),
                (
                    "from ea_node_editor.ui.support.node_presentation import build_inline_property_items",
                ),
            ),
            "ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py": (
                (
                    "from ea_node_editor.ui.shell.window_library_inspector import build_user_facing_node_instance_number",
                ),
                (
                    "from ea_node_editor.ui.support.node_presentation import build_user_facing_node_instance_number",
                ),
            ),
            "ea_node_editor/ui/shell/window_library_inspector.py": (
                (),
                (
                    "from ea_node_editor.ui.support.node_presentation import (",
                    "build_inline_property_items",
                    "build_user_facing_node_instance_number",
                ),
            ),
        }

        for relative_path, (absent_snippets, present_snippets) in expectations.items():
            module_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
            for snippet in absent_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="absent"):
                    self.assertNotIn(snippet, module_text)
            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="present"):
                    self.assertIn(snippet, module_text)


class ShellWorkspaceBridgeTests(unittest.TestCase):
    def test_bridge_forwards_workspace_run_title_and_console_concerns(self) -> None:
        host = _ShellWorkspaceHostStub()
        tabs_bridge = _WorkspaceTabsBridgeStub()
        console_bridge = _ConsoleBridgeStub()
        scene_bridge = _ScopeSceneBridgeStub()
        bridge = ShellWorkspaceBridge(
            shell_window=host,
            workspace_source=host,
            scene_bridge=scene_bridge,
            console_bridge=console_bridge,
            workspace_tabs_bridge=tabs_bridge,
        )

        self.assertIs(bridge.shell_window, host)
        self.assertIs(bridge.workspace_source, host)
        self.assertIs(bridge.scene_bridge, scene_bridge)
        self.assertIs(bridge.console_bridge, console_bridge)
        self.assertIs(bridge.workspace_tabs_bridge, tabs_bridge)
        self.assertEqual(bridge.project_display_name, "COREX Node Editor - packet.sfe")
        self.assertEqual(bridge.graphics_tab_strip_density, "relaxed")
        self.assertEqual(bridge.active_workspace_id, "ws-2")
        self.assertEqual(
            bridge.active_scope_breadcrumb_items,
            host.active_scope_breadcrumb_items,
        )
        self.assertEqual(bridge.active_view_items, host.active_view_items)
        self.assertEqual(bridge.workspace_tabs, tabs_bridge.tabs)
        self.assertEqual(bridge.output_text, "stdout line")
        self.assertEqual(bridge.errors_text, "error line")
        self.assertEqual(bridge.warnings_text, "warning line")
        self.assertEqual(bridge.error_count_value, 3)
        self.assertEqual(bridge.warning_count_value, 2)

        bridge.request_run_workflow()
        bridge.request_toggle_run_pause()
        bridge.request_stop_workflow()
        bridge.show_workflow_settings_dialog()
        bridge.show_workflow_settings_dialog(True)
        bridge.set_script_editor_panel_visible()
        bridge.set_script_editor_panel_visible(False)
        self.assertTrue(bridge.request_open_scope_breadcrumb("scope-node"))
        bridge.request_switch_view("view-2")
        self.assertTrue(bridge.request_move_view_tab(0, 1))
        self.assertTrue(bridge.request_rename_view("view-2"))
        self.assertTrue(bridge.request_close_view("view-1"))
        bridge.request_create_view()
        bridge.activate_workspace("ws-1")
        self.assertTrue(bridge.request_move_workspace_tab(1, 0))
        self.assertTrue(bridge.request_rename_workspace_by_id("ws-1"))
        self.assertTrue(bridge.request_close_workspace_by_id("ws-1"))
        bridge.request_create_workspace()
        bridge.clear_all()

        self.assertEqual(
            host.calls,
            [
                ("request_run_workflow", ()),
                ("request_toggle_run_pause", ()),
                ("request_stop_workflow", ()),
                ("show_workflow_settings_dialog", (False,)),
                ("show_workflow_settings_dialog", (True,)),
                ("set_script_editor_panel_visible", (None,)),
                ("set_script_editor_panel_visible", (False,)),
                ("request_open_scope_breadcrumb", ("scope-node",)),
                ("request_switch_view", ("view-2",)),
                ("request_move_view_tab", (0, 1)),
                ("request_rename_view", ("view-2",)),
                ("request_close_view", ("view-1",)),
                ("request_create_view", ()),
                ("request_move_workspace_tab", (1, 0)),
                ("request_rename_workspace_by_id", ("ws-1",)),
                ("request_close_workspace_by_id", ("ws-1",)),
                ("request_create_workspace", ()),
            ],
        )
        self.assertEqual(
            tabs_bridge.calls,
            [("activate_workspace", ("ws-1",))],
        )
        self.assertEqual(console_bridge.calls, [("clear_all", ())])

    def test_bridge_uses_explicit_workspace_source_contract_when_injected(self) -> None:
        host = _ShellWorkspaceHostStub()
        presenter = _ShellWorkspaceHostStub()
        presenter.project_display_name = "Presenter Packet"
        presenter.active_view_items = [{"view_id": "view-presenter", "label": "Presenter", "active": True}]
        host.shell_workspace_presenter = presenter
        tabs_bridge = _WorkspaceTabsBridgeStub()
        console_bridge = _ConsoleBridgeStub()
        scene_bridge = _ScopeSceneBridgeStub()

        bridge = ShellWorkspaceBridge(
            shell_window=host,
            workspace_source=presenter,
            scene_bridge=scene_bridge,
            console_bridge=console_bridge,
            workspace_tabs_bridge=tabs_bridge,
        )

        self.assertIs(bridge.workspace_source, presenter)
        self.assertEqual(bridge.project_display_name, "Presenter Packet")
        self.assertEqual(bridge.active_view_items, presenter.active_view_items)

        bridge.request_run_workflow()
        self.assertEqual(presenter.calls, [("request_run_workflow", ())])
        self.assertEqual(host.calls, [])

    def test_bridge_wraps_shell_window_and_routes_through_host_workspace_presenter_when_present(self) -> None:
        host = _ShellWorkspaceHostStub()
        presenter = _ShellWorkspaceHostStub()
        presenter.project_display_name = "Presenter Packet"
        host.shell_workspace_presenter = presenter
        tabs_bridge = _WorkspaceTabsBridgeStub()
        console_bridge = _ConsoleBridgeStub()
        scene_bridge = _ScopeSceneBridgeStub()

        bridge = ShellWorkspaceBridge(
            shell_window=host,
            scene_bridge=scene_bridge,
            console_bridge=console_bridge,
            workspace_tabs_bridge=tabs_bridge,
        )

        self.assertIsNot(bridge.workspace_source, presenter)
        self.assertEqual(bridge.project_display_name, presenter.project_display_name)
        bridge.request_run_workflow()
        self.assertEqual(presenter.calls, [("request_run_workflow", ())])
        self.assertEqual(host.calls, [])

    def test_bridge_re_emits_workspace_and_console_signals(self) -> None:
        host = _ShellWorkspaceHostStub()
        tabs_bridge = _WorkspaceTabsBridgeStub()
        console_bridge = _ConsoleBridgeStub()
        scene_bridge = _ScopeSceneBridgeStub()
        bridge = ShellWorkspaceBridge(
            shell_window=host,
            workspace_source=host,
            scene_bridge=scene_bridge,
            console_bridge=console_bridge,
            workspace_tabs_bridge=tabs_bridge,
        )
        seen = {
            "project_meta_changed": 0,
            "workspace_state_changed": 0,
            "graphics_preferences_changed": 0,
            "workspace_tabs_changed": 0,
            "console_output_changed": 0,
            "console_errors_changed": 0,
            "console_warnings_changed": 0,
            "console_counts_changed": 0,
        }

        bridge.project_meta_changed.connect(
            lambda: seen.__setitem__("project_meta_changed", seen["project_meta_changed"] + 1)
        )
        bridge.workspace_state_changed.connect(
            lambda: seen.__setitem__("workspace_state_changed", seen["workspace_state_changed"] + 1)
        )
        bridge.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "graphics_preferences_changed",
                seen["graphics_preferences_changed"] + 1,
            )
        )
        bridge.workspace_tabs_changed.connect(
            lambda: seen.__setitem__("workspace_tabs_changed", seen["workspace_tabs_changed"] + 1)
        )
        bridge.console_output_changed.connect(
            lambda: seen.__setitem__("console_output_changed", seen["console_output_changed"] + 1)
        )
        bridge.console_errors_changed.connect(
            lambda: seen.__setitem__("console_errors_changed", seen["console_errors_changed"] + 1)
        )
        bridge.console_warnings_changed.connect(
            lambda: seen.__setitem__("console_warnings_changed", seen["console_warnings_changed"] + 1)
        )
        bridge.console_counts_changed.connect(
            lambda: seen.__setitem__("console_counts_changed", seen["console_counts_changed"] + 1)
        )

        host.project_meta_changed.emit()
        host.workspace_state_changed.emit()
        host.graphics_preferences_changed.emit()
        scene_bridge.scope_changed.emit()
        tabs_bridge.tabs_changed.emit()
        console_bridge.output_changed.emit()
        console_bridge.errors_changed.emit()
        console_bridge.warnings_changed.emit()
        console_bridge.counts_changed.emit()

        self.assertEqual(
            seen,
            {
                "project_meta_changed": 1,
                "workspace_state_changed": 2,
                "graphics_preferences_changed": 1,
                "workspace_tabs_changed": 1,
                "console_output_changed": 1,
                "console_errors_changed": 1,
                "console_warnings_changed": 1,
                "console_counts_changed": 1,
            },
        )


ShellLibraryBridgeTests.__test__ = False
ShellInspectorBridgeTests.__test__ = False
GraphCanvasBridgeTests.__test__ = False
MainWindowGraphCanvasBridgeTests.__test__ = False
SharedUiSupportBoundaryTests.__test__ = False
ShellWorkspaceBridgeTests.__test__ = False


__all__ = [
    "ShellLibraryBridgeTests",
    "ShellInspectorBridgeTests",
    "GraphCanvasBridgeTests",
    "MainWindowGraphCanvasBridgeTests",
    "SharedUiSupportBoundaryTests",
    "ShellWorkspaceBridgeTests",
]
