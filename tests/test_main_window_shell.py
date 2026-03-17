from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtQuick import QQuickItem

from ea_node_editor.telemetry.frame_rate import FrameRateSampler
from ea_node_editor.ui.shell.runtime_clipboard import build_graph_fragment_payload, serialize_graph_fragment_payload
from ea_node_editor.ui_qml.graph_canvas_bridge import GraphCanvasBridge
from ea_node_editor.ui_qml.shell_inspector_bridge import ShellInspectorBridge
from ea_node_editor.ui_qml.shell_library_bridge import ShellLibraryBridge
from ea_node_editor.ui_qml.shell_workspace_bridge import ShellWorkspaceBridge
from tests.main_window_shell.base import MainWindowShellTestBase
from tests.main_window_shell.shell_basics_and_search import *  # noqa: F401,F403
from tests.main_window_shell.drop_connect_and_workflow_io import *  # noqa: F401,F403
from tests.main_window_shell.edit_clipboard_history import *  # noqa: F401,F403
from tests.main_window_shell.passive_style_context_menus import *  # noqa: F401,F403
from tests.main_window_shell.passive_property_editors import *  # noqa: F401,F403
from tests.main_window_shell.passive_image_nodes import *  # noqa: F401,F403
from tests.main_window_shell.passive_pdf_nodes import *  # noqa: F401,F403
from tests.main_window_shell.view_library_inspector import *  # noqa: F401,F403

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_TEST_RUNNER = (
    "import sys, unittest; "
    "target = sys.argv[1]; "
    "suite = unittest.defaultTestLoader.loadTestsFromName(target); "
    "result = unittest.TextTestRunner(verbosity=2).run(suite); "
    "sys.exit(0 if result.wasSuccessful() else 1)"
)


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
        self.project_display_name = "EA Node Editor - packet.sfe"
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


class _GraphCanvasShellHostStub(QObject):
    graphics_preferences_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.graphics_minimap_expanded = True
        self.graphics_show_grid = True
        self.graphics_show_minimap = True
        self.graphics_node_shadow = True
        self.graphics_shadow_strength = 70
        self.graphics_shadow_softness = 50
        self.graphics_shadow_offset = 4
        self.snap_to_grid_enabled = True
        self.snap_grid_size = 24.0
        self._return_values = {
            "request_open_subnode_scope": True,
            "browse_node_property_path": "C:/temp/from-canvas-bridge.txt",
            "request_drop_node_from_library": True,
            "request_connect_ports": True,
            "request_open_connection_quick_insert": True,
        }

    def _record(self, name: str, *args):
        self.calls.append((name, args))
        return self._return_values.get(name)

    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self.graphics_minimap_expanded = bool(expanded)
        self._record("set_graphics_minimap_expanded", bool(expanded))

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


class _GraphCanvasParentStub(QObject):
    def __init__(self, shell_window: QObject) -> None:
        super().__init__()
        self.shell_window = shell_window


class _GraphCanvasSceneBridgeStub(QObject):
    nodes_changed = pyqtSignal()
    edges_changed = pyqtSignal()
    selection_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.nodes_model = [{"node_id": "node-1", "selected": True}]
        self.edges_model = [{"edge_id": "edge-1"}]
        self.selected_node_lookup = {"node-1": True}
        self._return_values = {
            "are_port_kinds_compatible": True,
            "are_data_types_compatible": True,
            "move_nodes_by_delta": True,
        }

    def _record(self, name: str, *args):
        self.calls.append((name, args))
        return self._return_values.get(name)

    def select_node(self, node_id: str, additive: bool = False) -> None:
        self._record("select_node", node_id, additive)

    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        self._record("set_node_property", node_id, key, value)

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


class _GraphCanvasViewBridgeStub(QObject):
    view_state_changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.center_x = 18.5
        self.center_y = -42.0
        self.zoom_value = 1.75

    def _record(self, name: str, *args) -> None:
        self.calls.append((name, args))

    def adjust_zoom(self, factor: float) -> None:
        self._record("adjust_zoom", factor)

    def pan_by(self, delta_x: float, delta_y: float) -> None:
        self._record("pan_by", delta_x, delta_y)

    def set_viewport_size(self, width: float, height: float) -> None:
        self._record("set_viewport_size", width, height)


class ShellLibraryBridgeTests(unittest.TestCase):
    def test_bridge_forwards_shell_library_search_state_and_actions(self) -> None:
        host = _ShellLibraryHostStub()
        bridge = ShellLibraryBridge(shell_window=host)

        self.assertIs(bridge.shell_window, host)
        self.assertEqual(bridge.grouped_node_library_items, host.grouped_node_library_items)
        self.assertTrue(bridge.graph_search_open)
        self.assertEqual(bridge.graph_search_query, "graph search")
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

    def test_bridge_re_emits_shell_signals(self) -> None:
        host = _ShellLibraryHostStub()
        bridge = ShellLibraryBridge(shell_window=host)
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
        bridge = ShellInspectorBridge(shell_window=host)

        self.assertIs(bridge.shell_window, host)
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

    def test_bridge_re_emits_shell_state_signals(self) -> None:
        host = _ShellInspectorHostStub()
        bridge = ShellInspectorBridge(shell_window=host)
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
    def test_bridge_uses_explicit_shell_host_and_forwards_canvas_calls(self) -> None:
        host = _GraphCanvasShellHostStub()
        parent = _GraphCanvasParentStub(host)
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = GraphCanvasBridge(parent, shell_window=host, scene_bridge=scene, view_bridge=view)

        self.assertIs(bridge.parent(), parent)
        self.assertIs(bridge.shell_window, host)
        self.assertIsNot(bridge.shell_window, bridge.parent())
        self.assertIs(bridge.scene_bridge, scene)
        self.assertIs(bridge.view_bridge, view)
        self.assertTrue(bridge.graphics_minimap_expanded)
        self.assertTrue(bridge.graphics_show_grid)
        self.assertTrue(bridge.graphics_show_minimap)
        self.assertTrue(bridge.graphics_node_shadow)
        self.assertEqual(bridge.graphics_shadow_strength, 70)
        self.assertEqual(bridge.graphics_shadow_softness, 50)
        self.assertEqual(bridge.graphics_shadow_offset, 4)
        self.assertTrue(bridge.snap_to_grid_enabled)
        self.assertEqual(bridge.snap_grid_size, 24.0)
        self.assertEqual(bridge.center_x, 18.5)
        self.assertEqual(bridge.center_y, -42.0)
        self.assertEqual(bridge.zoom_value, 1.75)
        self.assertEqual(bridge.nodes_model, scene.nodes_model)
        self.assertEqual(bridge.edges_model, scene.edges_model)
        self.assertEqual(bridge.selected_node_lookup, scene.selected_node_lookup)

        bridge.set_graphics_minimap_expanded(False)
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

        self.assertEqual(
            host.calls,
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
            ],
        )
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

    def test_bridge_re_emits_shell_scene_and_view_signals(self) -> None:
        host = _GraphCanvasShellHostStub()
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = GraphCanvasBridge(host, shell_window=host, scene_bridge=scene, view_bridge=view)
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
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = GraphCanvasBridge(host, shell_window=host, scene_bridge=scene, view_bridge=view)

        self.assertEqual(bridge.selected_node_lookup, {"node-1": True})

        scene.selected_node_lookup = {"node-1": True, "node-2": True}
        self.assertEqual(
            bridge.selected_node_lookup,
            {"node-1": True, "node-2": True},
        )

    def test_bridge_keeps_safe_defaults_without_shell_host(self) -> None:
        scene = _GraphCanvasSceneBridgeStub()
        view = _GraphCanvasViewBridgeStub()
        bridge = GraphCanvasBridge(scene_bridge=scene, view_bridge=view)

        self.assertIsNone(bridge.shell_window)
        self.assertTrue(bridge.graphics_minimap_expanded)
        self.assertTrue(bridge.graphics_show_grid)
        self.assertTrue(bridge.graphics_show_minimap)
        self.assertTrue(bridge.graphics_node_shadow)
        self.assertEqual(bridge.graphics_shadow_strength, 70)
        self.assertEqual(bridge.graphics_shadow_softness, 50)
        self.assertEqual(bridge.graphics_shadow_offset, 4)
        self.assertFalse(bridge.snap_to_grid_enabled)
        self.assertEqual(bridge.snap_grid_size, 20.0)
        self.assertFalse(bridge.request_open_subnode_scope("subnode-1"))


class ShellWorkspaceBridgeTests(unittest.TestCase):
    def test_bridge_forwards_workspace_run_title_and_console_concerns(self) -> None:
        host = _ShellWorkspaceHostStub()
        tabs_bridge = _WorkspaceTabsBridgeStub()
        console_bridge = _ConsoleBridgeStub()
        scene_bridge = _ScopeSceneBridgeStub()
        bridge = ShellWorkspaceBridge(
            shell_window=host,
            scene_bridge=scene_bridge,
            console_bridge=console_bridge,
            workspace_tabs_bridge=tabs_bridge,
        )

        self.assertIs(bridge.shell_window, host)
        self.assertIs(bridge.scene_bridge, scene_bridge)
        self.assertIs(bridge.console_bridge, console_bridge)
        self.assertIs(bridge.workspace_tabs_bridge, tabs_bridge)
        self.assertEqual(bridge.project_display_name, "EA Node Editor - packet.sfe")
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

    def test_bridge_re_emits_workspace_and_console_signals(self) -> None:
        host = _ShellWorkspaceHostStub()
        tabs_bridge = _WorkspaceTabsBridgeStub()
        console_bridge = _ConsoleBridgeStub()
        scene_bridge = _ScopeSceneBridgeStub()
        bridge = ShellWorkspaceBridge(
            shell_window=host,
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


class ShellLibraryBridgeQmlBoundaryTests(unittest.TestCase):
    def test_owned_qml_components_route_migrated_concerns_through_shell_library_bridge(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml": (
                (
                    "mainWindowRef.set_library_query",
                    "mainWindowRef.grouped_node_library_items",
                    "mainWindowRef.request_add_node_from_library",
                    "target: root.mainWindowRef",
                ),
                ("shellLibraryBridgeRef",),
            ),
            "ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml": (
                (
                    "mainWindowRef.request_rename_custom_workflow_from_library",
                    "mainWindowRef.request_set_custom_workflow_scope",
                    "mainWindowRef.request_delete_custom_workflow_from_library",
                ),
                ("shellLibraryBridgeRef",),
            ),
            "ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml": (
                (
                    "mainWindowRef.graph_search_",
                    "mainWindowRef.set_graph_search_query",
                    "mainWindowRef.request_graph_search_",
                    "target: root.mainWindowRef",
                ),
                ("shellLibraryBridgeRef",),
            ),
            "ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml": (
                (
                    "mainWindowRef.connection_quick_insert_",
                    "mainWindowRef.set_connection_quick_insert_query",
                    "mainWindowRef.request_close_connection_quick_insert",
                    "mainWindowRef.request_connection_quick_insert_",
                    "target: root.mainWindowRef",
                ),
                ("shellLibraryBridgeRef",),
            ),
            "ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml": (
                ("mainWindowRef.graph_hint_",),
                ("shellLibraryBridgeRef",),
            ),
        }

        for relative_path, (absent_snippets, present_snippets) in expectations.items():
            qml_path = _REPO_ROOT / relative_path
            qml_text = qml_path.read_text(encoding="utf-8")

            for snippet in absent_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="absent"):
                    self.assertNotIn(snippet, qml_text)

            for snippet in present_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="present"):
                    self.assertIn(snippet, qml_text)


class ShellInspectorBridgeQmlBoundaryTests(unittest.TestCase):
    def test_inspector_pane_routes_owned_concerns_through_shell_inspector_bridge(self) -> None:
        qml_path = _REPO_ROOT / "ea_node_editor/ui_qml/components/shell/InspectorPane.qml"
        qml_text = qml_path.read_text(encoding="utf-8")

        absent_snippets = (
            "mainWindowRef.has_selected_node",
            "mainWindowRef.selected_node_is_subnode_pin",
            "mainWindowRef.selected_node_is_subnode_shell",
            "mainWindowRef.selected_node_port_items",
            "mainWindowRef.selected_node_title",
            "mainWindowRef.selected_node_subtitle",
            "mainWindowRef.selected_node_collapsible",
            "mainWindowRef.selected_node_collapsed",
            "mainWindowRef.selected_node_header_items",
            "mainWindowRef.selected_node_property_items",
            "mainWindowRef.pin_data_type_options",
            "mainWindowRef.request_add_selected_subnode_pin",
            "mainWindowRef.set_selected_port_label",
            "mainWindowRef.request_remove_selected_port",
            "mainWindowRef.set_selected_node_collapsed",
            "mainWindowRef.request_ungroup_selected_nodes",
            "mainWindowRef.set_selected_node_property",
            "mainWindowRef.browse_selected_node_property_path",
            "mainWindowRef.set_selected_port_exposed",
            "target: root.mainWindowRef",
        )
        present_snippets = (
            "property var mainWindowRef",
            "readonly property var inspectorBridgeRef: shellInspectorBridge",
            "root.inspectorBridgeRef.has_selected_node",
            "root.inspectorBridgeRef.selected_node_is_subnode_pin",
            "root.inspectorBridgeRef.selected_node_is_subnode_shell",
            "root.inspectorBridgeRef.selected_node_port_items",
            "root.inspectorBridgeRef.selected_node_title",
            "root.inspectorBridgeRef.selected_node_subtitle",
            "root.inspectorBridgeRef.selected_node_collapsible",
            "root.inspectorBridgeRef.selected_node_collapsed",
            "root.inspectorBridgeRef.selected_node_header_items",
            "root.inspectorBridgeRef.selected_node_property_items",
            "root.inspectorBridgeRef.pin_data_type_options",
            "root.inspectorBridgeRef.request_add_selected_subnode_pin",
            "root.inspectorBridgeRef.set_selected_port_label",
            "root.inspectorBridgeRef.request_remove_selected_port",
            "root.inspectorBridgeRef.set_selected_node_collapsed",
            "root.inspectorBridgeRef.request_ungroup_selected_nodes",
            "root.inspectorBridgeRef.set_selected_node_property",
            "root.inspectorBridgeRef.browse_selected_node_property_path",
            "root.inspectorBridgeRef.set_selected_port_exposed",
            "target: root.inspectorBridgeRef",
        )

        for snippet in absent_snippets:
            with self.subTest(snippet=snippet, expectation="absent"):
                self.assertNotIn(snippet, qml_text)

        for snippet in present_snippets:
            with self.subTest(snippet=snippet, expectation="present"):
                self.assertIn(snippet, qml_text)


class ShellWorkspaceBridgeQmlBoundaryTests(unittest.TestCase):
    def test_workspace_run_title_and_console_qml_routes_owned_concerns_through_shell_workspace_bridge(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml": (
                ("mainWindowRef.project_display_name",),
                (
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.project_display_name",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml": (
                (
                    "mainWindowRef.request_run_workflow",
                    "mainWindowRef.request_toggle_run_pause",
                    "mainWindowRef.request_stop_workflow",
                    "mainWindowRef.show_workflow_settings_dialog",
                    "mainWindowRef.set_script_editor_panel_visible",
                ),
                (
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.request_run_workflow",
                    "root.workspaceBridgeRef.request_toggle_run_pause",
                    "root.workspaceBridgeRef.request_stop_workflow",
                    "root.workspaceBridgeRef.show_workflow_settings_dialog",
                    "root.workspaceBridgeRef.set_script_editor_panel_visible",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml": (
                (
                    "mainWindowRef.graphics_tab_strip_density",
                    "mainWindowRef.active_scope_breadcrumb_items",
                    "mainWindowRef.active_view_items",
                    "mainWindowRef.active_workspace_id",
                    "mainWindowRef.request_open_scope_breadcrumb",
                    "mainWindowRef.request_switch_view",
                    "mainWindowRef.request_move_view_tab",
                    "mainWindowRef.request_rename_view",
                    "mainWindowRef.request_close_view",
                    "mainWindowRef.request_create_view",
                    "mainWindowRef.request_move_workspace_tab",
                    "mainWindowRef.request_rename_workspace_by_id",
                    "mainWindowRef.request_close_workspace_by_id",
                    "mainWindowRef.request_create_workspace",
                    "workspaceTabsBridgeRef.tabs",
                    "workspaceTabsBridgeRef.activate_workspace",
                    "consoleBridgeRef.error_count_value",
                    "consoleBridgeRef.warning_count_value",
                    "consoleBridgeRef.clear_all",
                    "consoleBridgeRef.output_text",
                    "consoleBridgeRef.errors_text",
                    "consoleBridgeRef.warnings_text",
                ),
                (
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.graphics_tab_strip_density",
                    "root.workspaceBridgeRef.active_scope_breadcrumb_items",
                    "root.workspaceBridgeRef.active_view_items",
                    "root.workspaceBridgeRef.active_workspace_id",
                    "root.workspaceBridgeRef.request_open_scope_breadcrumb",
                    "root.workspaceBridgeRef.request_switch_view",
                    "root.workspaceBridgeRef.request_move_view_tab",
                    "root.workspaceBridgeRef.request_rename_view",
                    "root.workspaceBridgeRef.request_close_view",
                    "root.workspaceBridgeRef.request_create_view",
                    "root.workspaceBridgeRef.request_move_workspace_tab",
                    "root.workspaceBridgeRef.request_rename_workspace_by_id",
                    "root.workspaceBridgeRef.request_close_workspace_by_id",
                    "root.workspaceBridgeRef.request_create_workspace",
                    "root.workspaceBridgeRef.workspace_tabs",
                    "root.workspaceBridgeRef.activate_workspace",
                    "root.workspaceBridgeRef.error_count_value",
                    "root.workspaceBridgeRef.warning_count_value",
                    "root.workspaceBridgeRef.clear_all",
                    "root.workspaceBridgeRef.output_text",
                    "root.workspaceBridgeRef.errors_text",
                    "root.workspaceBridgeRef.warnings_text",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml": (
                ("mainWindowRef.set_script_editor_panel_visible(false)",),
                (
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.set_script_editor_panel_visible(false)",
                ),
            ),
        }

        for relative_path, (absent_snippets, present_snippets) in expectations.items():
            qml_path = _REPO_ROOT / relative_path
            qml_text = qml_path.read_text(encoding="utf-8")

            for snippet in absent_snippets:
                with self.subTest(path=relative_path, snippet=snippet, expectation="absent"):
                    self.assertNotIn(snippet, qml_text)

        for snippet in present_snippets:
            with self.subTest(path=relative_path, snippet=snippet, expectation="present"):
                self.assertIn(snippet, qml_text)


class GraphCanvasQmlBoundaryTests(unittest.TestCase):
    def test_graph_canvas_routes_owned_concerns_through_bridge_first_refs(self) -> None:
        qml_path = _REPO_ROOT / "ea_node_editor/ui_qml/components/GraphCanvas.qml"
        qml_text = qml_path.read_text(encoding="utf-8")

        absent_snippets = (
            "mainWindowBridge.graphics_minimap_expanded",
            "mainWindowBridge.graphics_show_grid",
            "mainWindowBridge.graphics_show_minimap",
            "mainWindowBridge.graphics_node_shadow",
            "mainWindowBridge.graphics_shadow_strength",
            "mainWindowBridge.graphics_shadow_softness",
            "mainWindowBridge.graphics_shadow_offset",
            "mainWindowBridge.snap_to_grid_enabled",
            "mainWindowBridge.snap_grid_size",
            "mainWindowBridge.request_open_subnode_scope",
            "mainWindowBridge.browse_node_property_path",
            "mainWindowBridge.request_drop_node_from_library",
            "mainWindowBridge.request_connect_ports",
            "mainWindowBridge.request_open_connection_quick_insert",
            "sceneBridge.nodes_model",
            "sceneBridge.selected_node_lookup",
            "sceneBridge.select_node",
            "sceneBridge.set_node_property",
            "sceneBridge.are_port_kinds_compatible",
            "sceneBridge.are_data_types_compatible",
            "sceneBridge.move_nodes_by_delta",
            "sceneBridge.move_node",
            "sceneBridge.resize_node",
            "viewBridge.adjust_zoom",
            "viewBridge.pan_by",
            "viewBridge.set_viewport_size",
            "viewBridge.zoom_value",
            "viewBridge.center_x",
            "viewBridge.center_y",
        )
        present_snippets = (
            "readonly property var _canvasShellBridgeRef",
            "readonly property var _canvasSceneBridgeRef",
            "readonly property var _canvasViewBridgeRef",
            "root._canvasShellBridgeRef.graphics_show_grid",
            "root._canvasSceneBridgeRef.nodes_model",
            "bridge.selected_node_lookup",
            "var bridge = root._canvasShellBridgeRef",
            "var bridge = root._canvasSceneBridgeRef",
            "var view = root._canvasViewBridgeRef",
            "scale: root._canvasViewBridgeRef ? root._canvasViewBridgeRef.zoom_value : 1.0",
            "target: root._canvasSceneBridgeRef",
            "target: root._canvasViewBridgeRef",
        )

        for snippet in absent_snippets:
            with self.subTest(snippet=snippet, expectation="absent"):
                self.assertNotIn(snippet, qml_text)

        for snippet in present_snippets:
            with self.subTest(snippet=snippet, expectation="present"):
                self.assertIn(snippet, qml_text)


class FrameRateSamplerTests(unittest.TestCase):
    def test_snapshot_is_zero_without_enough_frames(self) -> None:
        sampler = FrameRateSampler(window_seconds=1.0)

        self.assertEqual(sampler.snapshot(timestamp=1.0).fps, 0.0)

        sampler.record_frame(timestamp=1.25)
        sample = sampler.snapshot(timestamp=1.25)
        self.assertEqual(sample.fps, 0.0)
        self.assertEqual(sample.sample_count, 1)

    def test_snapshot_reports_average_fps_within_recent_window(self) -> None:
        sampler = FrameRateSampler(window_seconds=1.0)
        for timestamp in (10.0, 10.2, 10.4, 10.6):
            sampler.record_frame(timestamp=timestamp)

        sample = sampler.snapshot(timestamp=10.6)

        self.assertAlmostEqual(sample.fps, 5.0, places=4)
        self.assertEqual(sample.sample_count, 4)

    def test_snapshot_drops_stale_frames_and_returns_idle_zero(self) -> None:
        sampler = FrameRateSampler(window_seconds=0.5)
        for timestamp in (20.0, 20.1, 20.2):
            sampler.record_frame(timestamp=timestamp)

        self.assertGreater(sampler.snapshot(timestamp=20.2).fps, 0.0)
        self.assertEqual(sampler.snapshot(timestamp=20.8).fps, 0.0)


class MainWindowShellTelemetryTests(MainWindowShellTestBase):
    def test_update_system_metrics_can_render_explicit_fps_value(self) -> None:
        self.window.update_system_metrics(37.0, 4.3, 16.0, fps=58.0)
        self.app.processEvents()

        self.assertEqual(self.window.status_metrics.text(), "FPS:58 CPU:37% RAM:4.3/16.0 GB")


class MainWindowShellContextBootstrapTests(MainWindowShellTestBase):
    def test_qml_context_preserves_legacy_context_properties_and_registers_facades(self) -> None:
        context = self.window.quick_widget.rootContext()

        expected_context_names = (
            "mainWindow",
            "sceneBridge",
            "viewBridge",
            "consoleBridge",
            "scriptEditorBridge",
            "scriptHighlighterBridge",
            "themeBridge",
            "graphThemeBridge",
            "workspaceTabsBridge",
            "uiIcons",
            "statusEngine",
            "statusJobs",
            "statusMetrics",
            "statusNotifications",
            "shellLibraryBridge",
            "shellWorkspaceBridge",
            "shellInspectorBridge",
            "graphCanvasBridge",
        )
        for name in expected_context_names:
            with self.subTest(name=name):
                self.assertIsNotNone(context.contextProperty(name))

        shell_library_bridge = context.contextProperty("shellLibraryBridge")
        self.assertIsInstance(shell_library_bridge, ShellLibraryBridge)
        self.assertIs(shell_library_bridge.shell_window, self.window)

        shell_workspace_bridge = context.contextProperty("shellWorkspaceBridge")
        self.assertIsInstance(shell_workspace_bridge, ShellWorkspaceBridge)
        self.assertIs(shell_workspace_bridge.shell_window, self.window)
        self.assertIs(shell_workspace_bridge.scene_bridge, self.window.scene)
        self.assertIs(shell_workspace_bridge.view_bridge, self.window.view)
        self.assertIs(shell_workspace_bridge.console_bridge, self.window.console_panel)
        self.assertIs(shell_workspace_bridge.workspace_tabs_bridge, self.window.workspace_tabs)

        shell_inspector_bridge = context.contextProperty("shellInspectorBridge")
        self.assertIsInstance(shell_inspector_bridge, ShellInspectorBridge)
        self.assertIs(shell_inspector_bridge.shell_window, self.window)
        self.assertIs(shell_inspector_bridge.scene_bridge, self.window.scene)

        graph_canvas_bridge = context.contextProperty("graphCanvasBridge")
        self.assertIsInstance(graph_canvas_bridge, GraphCanvasBridge)
        self.assertIs(graph_canvas_bridge.parent(), self.window)
        self.assertIs(graph_canvas_bridge.shell_window, self.window)
        self.assertIs(graph_canvas_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_bridge.view_bridge, self.window.view)


class MainWindowShellHostProtocolStateTests(MainWindowShellTestBase):
    def test_search_scope_state_tracks_graph_search_quick_insert_and_hints(self) -> None:
        self.window.action_graph_search.trigger()
        self.window.set_graph_search_query("core.start")
        self.app.processEvents()

        graph_search_state = self.window.search_scope_state.graph_search
        self.assertTrue(graph_search_state.open)
        self.assertEqual(graph_search_state.query, "core.start")
        self.assertEqual(graph_search_state.results, self.window.graph_search_results)

        self.window.request_open_canvas_quick_insert(40.0, 55.0, 120.0, 180.0)
        self.app.processEvents()

        quick_insert_state = self.window.search_scope_state.connection_quick_insert
        self.assertTrue(quick_insert_state.open)
        self.assertEqual(quick_insert_state.context["mode"], "canvas_insert")
        self.assertEqual(quick_insert_state.context["overlay_x"], 120.0)
        self.assertEqual(quick_insert_state.results, self.window.connection_quick_insert_results)

        self.window.show_graph_hint("Packet hint", 500)
        self.assertEqual(self.window.search_scope_state.graph_hint_message, "Packet hint")
        self.window.clear_graph_hint()
        self.assertEqual(self.window.search_scope_state.graph_hint_message, "")

    def test_scope_camera_cache_is_owned_by_search_scope_state(self) -> None:
        self.window.view.set_zoom(1.35)
        self.window.view.centerOn(140.0, -75.0)

        self.window._remember_scope_camera()

        key = self.window._active_scope_camera_key()
        self.assertIsNotNone(key)
        if key is None:
            self.fail("Expected active scope camera key")
        self.assertIn(key, self.window.search_scope_state.runtime_scope_camera)


class MainWindowShellGraphCanvasHostTests(MainWindowShellTestBase):
    def test_graph_canvas_host_binds_canvas_bridge_ref_to_registered_graph_canvas_bridge(self) -> None:
        graph_canvas = self._graph_canvas_item()
        context = self.window.quick_widget.rootContext()
        graph_canvas_bridge = context.contextProperty("graphCanvasBridge")

        self.assertIsInstance(graph_canvas_bridge, GraphCanvasBridge)
        self.assertIsInstance(graph_canvas.property("canvasBridgeRef"), GraphCanvasBridge)
        self.assertIs(graph_canvas.property("canvasBridgeRef"), graph_canvas_bridge)
        self.assertIsNot(graph_canvas.property("canvasBridgeRef"), self.window)
        self.assertIs(graph_canvas.property("sceneBridge"), self.window.scene)
        self.assertIs(graph_canvas.property("viewBridge"), self.window.view)
        self.assertTrue(bool(graph_canvas.property("showGrid")))
        self.assertEqual(
            bool(graph_canvas.property("showGrid")),
            graph_canvas.property("canvasBridgeRef").graphics_show_grid,
        )
        self.assertEqual(
            bool(graph_canvas.property("minimapVisible")),
            graph_canvas.property("canvasBridgeRef").graphics_show_minimap,
        )
        self.assertEqual(
            bool(graph_canvas.property("minimapExpanded")),
            graph_canvas.property("canvasBridgeRef").graphics_minimap_expanded,
        )

    def test_graph_canvas_keeps_graph_node_card_discoverability_after_host_refactor(self) -> None:
        graph_canvas = self._graph_canvas_item()
        self.window.scene.add_node_from_type("core.logger", 180.0, 120.0)
        self.app.processEvents()

        node_cards = _named_child_items(graph_canvas, "graphNodeCard")
        self.assertGreaterEqual(len(node_cards), 1)
        self.assertIsNotNone(node_cards[0].findChild(QObject, "graphNodeStandardSurface"))

    def test_plain_text_graph_fragment_payload_is_ignored_by_paste(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.scene.add_node_from_type("core.start", x=25.0, y=35.0)
        before_state = self._workspace_state()
        before_depth = self.window.runtime_history.undo_depth(workspace_id)
        clipboard = self.app.clipboard()

        valid_text_payload = serialize_graph_fragment_payload(
            build_graph_fragment_payload(
                nodes=[
                    {
                        "ref_id": "ref-start",
                        "type_id": "core.start",
                        "title": "Start",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {},
                        "visual_style": {},
                        "parent_node_id": None,
                    }
                ],
                edges=[],
            )
        )
        self.assertIsNotNone(valid_text_payload)
        clipboard.setText(str(valid_text_payload))

        pasted = self.window.request_paste_selected_nodes()
        self.assertFalse(pasted)
        self.assertEqual(self._workspace_state(), before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_depth)

    def test_graph_search_results_use_user_facing_instance_ids_for_duplicate_nodes(self) -> None:
        first_node_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        second_node_id = self.window.scene.add_node_from_type("core.start", x=260.0, y=40.0)
        self.window.scene.set_node_title(first_node_id, "Duplicate Search Alpha")
        self.window.scene.set_node_title(second_node_id, "Duplicate Search Beta")
        self.app.processEvents()

        self.window.action_graph_search.trigger()
        self.window.set_graph_search_query("duplicate search")
        self.app.processEvents()

        results_by_id = {
            item["node_id"]: item
            for item in self.window.graph_search_results
        }
        self.assertEqual(results_by_id[first_node_id]["instance_number"], 1)
        self.assertEqual(results_by_id[first_node_id]["instance_label"], "ID 1")
        self.assertEqual(results_by_id[second_node_id]["instance_number"], 2)
        self.assertEqual(results_by_id[second_node_id]["instance_label"], "ID 2")


class _SubprocessShellWindowTest(unittest.TestCase):
    __test__ = False

    def __init__(self, target: str) -> None:
        super().__init__(methodName="runTest")
        self._target = target

    def id(self) -> str:
        return self._target

    def __str__(self) -> str:
        return self._target

    def shortDescription(self) -> str:
        return self._target

    def runTest(self) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        result = subprocess.run(
            [sys.executable, "-c", _SHELL_TEST_RUNNER, self._target],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        output = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        self.fail(
            f"Subprocess shell test failed for {self._target} "
            f"(exit={result.returncode}).\n{output}"
        )


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(FrameRateSamplerTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellLibraryBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellInspectorBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellWorkspaceBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellLibraryBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellInspectorBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellWorkspaceBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(GraphCanvasQmlBoundaryTests))

    shell_classes: list[type[MainWindowShellTestBase]] = []
    for candidate in globals().values():
        if not isinstance(candidate, type):
            continue
        if not issubclass(candidate, MainWindowShellTestBase):
            continue
        if candidate is MainWindowShellTestBase:
            continue
        shell_classes.append(candidate)

    for case_type in sorted(shell_classes, key=lambda item: (item.__module__, item.__name__)):
        for test_name in loader.getTestCaseNames(case_type):
            target = f"{case_type.__module__}.{case_type.__qualname__}.{test_name}"
            suite.addTest(_SubprocessShellWindowTest(target))
    return suite


if __name__ == "__main__":
    import unittest

    unittest.main()
