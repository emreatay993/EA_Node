from __future__ import annotations

import unittest

import pytest

from ea_node_editor.ui.shell.controllers.graph_action_controller import GraphActionController
from ea_node_editor.ui.shell.graph_action_contracts import GraphActionId
from ea_node_editor.ui.shell.presenters.workspace_presenter import ShellWorkspacePresenter
from ea_node_editor.ui_qml.graph_action_bridge import GraphActionBridge
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from tests.main_window_shell import bridge_support as _bridge_support

pytestmark = pytest.mark.xdist_group("p03_bridge_contracts")


class _GraphActionSource:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.nodes_model = [
            {
                "node_id": "locked-node",
                "addon_id": "addon.from-node",
                "locked_state": {"focus_addon_id": "addon.from-lock"},
            }
        ]

    def _record(self, name: str, *args: object) -> bool:
        self.calls.append((name, args))
        return True

    def copy_selected_nodes_to_clipboard(self) -> bool:
        return self._record("copy_selected_nodes_to_clipboard")

    def align_selection_left(self) -> bool:
        return self._record("align_selection_left")

    def request_delete_selected_graph_items(self, edge_ids: list[object]) -> bool:
        return self._record("request_delete_selected_graph_items", edge_ids)

    def request_open_subnode_scope(self, node_id: str) -> bool:
        return self._record("request_open_subnode_scope", node_id)

    def request_publish_custom_workflow_from_node(self, node_id: str) -> bool:
        return self._record("request_publish_custom_workflow_from_node", node_id)

    def open_comment_peek(self, node_id: str) -> bool:
        return self._record("open_comment_peek", node_id)

    def close_comment_peek(self) -> bool:
        return self._record("close_comment_peek")

    def requestOpen(self, focus_addon_id: str) -> None:  # noqa: N802
        self.calls.append(("requestOpen", (focus_addon_id,)))

    def request_edit_flow_edge_style(self, edge_id: str) -> bool:
        return self._record("request_edit_flow_edge_style", edge_id)

    def request_remove_edge(self, edge_id: str) -> bool:
        return self._record("request_remove_edge", edge_id)


class GraphCanvasBridgeTests(unittest.TestCase):
    __test__ = True

    def test_graph_action_controller_delegates_representative_action_families(self) -> None:
        workspace = _GraphActionSource()
        canvas_presenter = _GraphActionSource()
        host_presenter = _GraphActionSource()
        library_presenter = _GraphActionSource()
        scene = _GraphActionSource()
        addon_manager = _GraphActionSource()
        controller = GraphActionController(
            workspace_library_controller=workspace,
            graph_canvas_presenter=canvas_presenter,
            graph_canvas_host_presenter=host_presenter,
            shell_library_presenter=library_presenter,
            scene_bridge=scene,
            addon_manager_bridge=addon_manager,
        )

        self.assertFalse(hasattr(controller, "shell_window"))
        self.assertFalse(hasattr(controller, "_shell_window"))
        self.assertTrue(controller.trigger(GraphActionId.COPY_SELECTION.value))
        self.assertTrue(controller.trigger(GraphActionId.ALIGN_SELECTION_LEFT.value))
        self.assertTrue(controller.trigger(GraphActionId.DELETE_SELECTION.value, {"edge_ids": ["edge-1"]}))
        self.assertTrue(controller.trigger(GraphActionId.OPEN_SUBNODE_SCOPE.value, {"node_id": "node-1"}))
        self.assertTrue(
            controller.trigger(GraphActionId.PUBLISH_CUSTOM_WORKFLOW_FROM_NODE.value, {"node_id": "node-2"})
        )
        self.assertTrue(controller.trigger(GraphActionId.OPEN_COMMENT_PEEK.value, {"node_id": "comment-1"}))
        self.assertTrue(controller.trigger(GraphActionId.CLOSE_COMMENT_PEEK.value))
        self.assertTrue(controller.trigger(GraphActionId.OPEN_ADDON_MANAGER_FOR_NODE.value, {"node_id": "locked-node"}))
        self.assertTrue(controller.trigger(GraphActionId.REMOVE_EDGE.value, {"edge_id": "edge-1"}))

        self.assertEqual(
            workspace.calls,
            [
                ("copy_selected_nodes_to_clipboard", ()),
                ("align_selection_left", ()),
            ],
        )
        self.assertEqual(
            canvas_presenter.calls,
            [("request_open_subnode_scope", ("node-1",))],
        )
        self.assertEqual(
            host_presenter.calls,
            [
                ("request_delete_selected_graph_items", (["edge-1"],)),
                ("request_remove_edge", ("edge-1",)),
            ],
        )
        self.assertEqual(
            library_presenter.calls,
            [("request_publish_custom_workflow_from_node", ("node-2",))],
        )
        self.assertEqual(
            scene.calls,
            [
                ("open_comment_peek", ("comment-1",)),
                ("close_comment_peek", ()),
            ],
        )
        self.assertEqual(addon_manager.calls, [("requestOpen", ("addon.from-lock",))])

    def test_graph_action_bridge_exposes_contract_metadata_and_rejects_bad_payloads(self) -> None:
        host_presenter = _GraphActionSource()
        controller = GraphActionController(graph_canvas_host_presenter=host_presenter)
        bridge = GraphActionBridge(controller=controller)

        self.assertIn(GraphActionId.REMOVE_EDGE.value, bridge.actionIds)
        self.assertEqual(
            bridge.action_metadata("edit_flow_edge")["actionId"],
            GraphActionId.EDIT_FLOW_EDGE_STYLE.value,
        )
        self.assertEqual(
            bridge.action_metadata(GraphActionId.REMOVE_EDGE.value)["requiredPayloadKeys"],
            ["edge_id"],
        )
        self.assertTrue(bridge.trigger_graph_action("edit_flow_edge", {"edge_id": "edge-2"}))
        self.assertFalse(bridge.trigger_graph_action("edit_flow_edge", {"edge_id": ""}))
        self.assertFalse(bridge.trigger_graph_action("edit_flow_edge", {"edge_id": 123}))
        self.assertFalse(bridge.trigger_graph_action("not_a_graph_action", {}))
        self.assertEqual(
            host_presenter.calls,
            [("request_edit_flow_edge_style", ("edge-2",))],
        )

    def test_command_bridge_routes_canvas_commands_to_explicit_canvas_host_scene_and_view_sources(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        presenter = _bridge_support._GraphCanvasShellHostStub()
        host_source = _bridge_support._GraphCanvasShellHostStub()
        host.graph_canvas_presenter = presenter
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        view = _bridge_support._GraphCanvasViewBridgeStub()
        bridge = GraphCanvasCommandBridge(
            host,
            shell_window=host,
            canvas_source=presenter,
            host_source=host_source,
            scene_bridge=scene,
            view_bridge=view,
        )

        self.assertIs(bridge.parent(), host)
        self.assertIsNone(bridge.shell_window)
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
        self.assertEqual(
            bridge.pick_node_property_color("node-1", "accent_color", "#336699"),
            "#AA5500",
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

        self.assertEqual(
            presenter.calls,
            [
                ("set_graphics_minimap_expanded", (False,)),
                ("request_open_subnode_scope", ("subnode-1",)),
                ("browse_node_property_path", ("node-1", "source_path", "C:/temp/current.txt")),
                ("pick_node_property_color", ("node-1", "accent_color", "#336699")),
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

    def test_split_canvas_bridges_use_explicit_sources_without_legacy_wrapper(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        host_source = _bridge_support._GraphCanvasShellHostStub()
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        view = _bridge_support._GraphCanvasViewBridgeStub()
        state_bridge = GraphCanvasStateBridge(
            host,
            shell_window=host,
            canvas_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )
        command_bridge = GraphCanvasCommandBridge(
            host,
            shell_window=host,
            canvas_source=host,
            host_source=host_source,
            scene_bridge=scene,
            view_bridge=view,
        )

        self.assertIsNone(state_bridge.shell_window)
        self.assertIs(state_bridge.scene_bridge, scene)
        self.assertIs(state_bridge.view_bridge, view)
        self.assertIsNone(command_bridge.shell_window)
        self.assertIs(command_bridge.canvas_source, host)
        self.assertIs(command_bridge.host_source, host_source)
        self.assertIs(command_bridge.scene_bridge, scene)
        self.assertIs(command_bridge.view_bridge, view)
        self.assertTrue(state_bridge.graphics_minimap_expanded)
        self.assertTrue(state_bridge.graphics_show_grid)
        self.assertTrue(state_bridge.graphics_show_minimap)
        self.assertTrue(state_bridge.graphics_show_port_labels)
        self.assertTrue(state_bridge.graphics_node_shadow)
        self.assertEqual(state_bridge.graphics_shadow_strength, 70)
        self.assertEqual(state_bridge.graphics_shadow_softness, 50)
        self.assertEqual(state_bridge.graphics_shadow_offset, 4)
        self.assertEqual(state_bridge.graphics_performance_mode, "full_fidelity")
        self.assertTrue(state_bridge.snap_to_grid_enabled)
        self.assertEqual(state_bridge.snap_grid_size, 24.0)
        self.assertEqual(state_bridge.center_x, 18.5)
        self.assertEqual(state_bridge.center_y, -42.0)
        self.assertEqual(state_bridge.zoom_value, 1.75)
        self.assertEqual(state_bridge.nodes_model, scene.nodes_model)
        self.assertEqual(state_bridge.edges_model, scene.edges_model)
        self.assertEqual(state_bridge.selected_node_lookup, scene.selected_node_lookup)

        command_bridge.set_graphics_minimap_expanded(False)
        command_bridge.set_graphics_show_port_labels(False)
        self.assertFalse(state_bridge.graphics_show_port_labels)
        command_bridge.set_graphics_performance_mode("max_performance")
        command_bridge.adjust_zoom(1.15)
        command_bridge.pan_by(-12.0, 8.0)
        command_bridge.set_viewport_size(1280.0, 720.0)
        self.assertTrue(command_bridge.request_open_subnode_scope("subnode-1"))
        self.assertEqual(
            command_bridge.browse_node_property_path("node-1", "source_path", "C:/temp/current.txt"),
            "C:/temp/from-canvas-bridge.txt",
        )
        self.assertEqual(
            command_bridge.pick_node_property_color("node-1", "accent_color", "#336699"),
            "#AA5500",
        )
        self.assertTrue(
            command_bridge.request_drop_node_from_library(
                "core.logger",
                120.0,
                240.0,
                "port",
                "node-1",
                "exec_in",
                "edge-1",
            )
        )
        self.assertTrue(command_bridge.request_connect_ports("node-1", "exec_out", "node-2", "exec_in"))
        command_bridge.select_node("node-1", True)
        command_bridge.set_node_property("node-1", "message", "hello")
        self.assertTrue(command_bridge.are_port_kinds_compatible("exec", "exec"))
        self.assertTrue(command_bridge.are_data_types_compatible("text", "text"))
        self.assertTrue(command_bridge.move_nodes_by_delta(["node-1", "node-2"], 10.0, -5.0))
        command_bridge.move_node("node-1", 160.0, 220.0)
        command_bridge.resize_node("node-1", 320.0, 180.0)
        command_bridge.set_node_geometry("node-1", 150.0, 210.0, 340.0, 190.0)

        self.assertEqual(
            host.calls,
            [
                ("set_graphics_minimap_expanded", (False,)),
                ("set_graphics_show_port_labels", (False,)),
                ("set_graphics_performance_mode", ("max_performance",)),
                ("request_open_subnode_scope", ("subnode-1",)),
                ("browse_node_property_path", ("node-1", "source_path", "C:/temp/current.txt")),
                ("pick_node_property_color", ("node-1", "accent_color", "#336699")),
                (
                    "request_drop_node_from_library",
                    ("core.logger", 120.0, 240.0, "port", "node-1", "exec_in", "edge-1"),
                ),
                ("request_connect_ports", ("node-1", "exec_out", "node-2", "exec_in")),
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

    def test_split_canvas_bridges_expose_canvas_contract_extensions(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        host_source = _bridge_support._GraphCanvasShellHostStub()
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        view = _bridge_support._GraphCanvasViewBridgeStub()
        state_bridge = GraphCanvasStateBridge(
            shell_window=host,
            canvas_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )
        command_bridge = GraphCanvasCommandBridge(
            shell_window=host,
            canvas_source=host,
            host_source=host_source,
            scene_bridge=scene,
            view_bridge=view,
        )

        self.assertEqual(state_bridge.visible_scene_rect_payload, view.visible_scene_rect_payload)
        self.assertEqual(state_bridge.minimap_nodes_model, scene.minimap_nodes_model)
        self.assertEqual(state_bridge.workspace_scene_bounds_payload, scene.workspace_scene_bounds_payload)

        command_bridge.center_on_scene_point(96.0, 144.0)
        command_bridge.request_open_canvas_quick_insert(15.0, 25.0, 115.0, 215.0)
        self.assertTrue(command_bridge.request_delete_selected_graph_items(["edge-1"]))
        self.assertTrue(command_bridge.request_navigate_scope_parent())
        self.assertTrue(command_bridge.request_navigate_scope_root())
        command_bridge.clear_selection()
        command_bridge.select_nodes_in_rect(1.0, 2.0, 3.0, 4.0, True)
        command_bridge.set_pending_surface_action("node-1")
        self.assertTrue(command_bridge.consume_pending_surface_action("node-1"))
        self.assertTrue(command_bridge.set_node_properties("node-1", {"message": "bridge"}))
        command_bridge.set_graph_cursor_shape(13)
        command_bridge.clear_graph_cursor_shape()
        self.assertEqual(
            command_bridge.describe_pdf_preview("C:/temp/preview.pdf", 2),
            {
                "source": "C:/temp/preview.pdf",
                "page_number": 2,
                "valid": True,
            },
        )

        self.assertEqual(host.calls, [("request_open_canvas_quick_insert", (15.0, 25.0, 115.0, 215.0))])
        self.assertEqual(
            host_source.calls,
            [
                ("request_delete_selected_graph_items", (["edge-1"],)),
                ("request_navigate_scope_parent", ()),
                ("request_navigate_scope_root", ()),
                ("set_graph_cursor_shape", (13,)),
                ("clear_graph_cursor_shape", ()),
                ("describe_pdf_preview", ("C:/temp/preview.pdf", 2)),
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
        self.assertEqual(view.calls, [("center_on_scene_point", (96.0, 144.0))])

    def test_graph_typography_bridge_workspace_presenter_snapshots_graph_label_pixel_size(self) -> None:
        host = _bridge_support._ShellWorkspacePresenterHostStub()
        presenter = ShellWorkspacePresenter(host, ui_state=host.workspace_ui_state)
        seen = {"graphics_preferences_changed": 0}
        presenter.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "graphics_preferences_changed",
                seen["graphics_preferences_changed"] + 1,
            )
        )

        resolved = presenter.apply_graphics_preferences(
            {"typography": {"graph_label_pixel_size": 17}},
        )

        self.assertEqual(
            resolved["typography"]["graph_label_pixel_size"],
            17,
        )
        self.assertEqual(host.workspace_ui_state.graph_label_pixel_size, 17)
        self.assertEqual(presenter.graphics_graph_label_pixel_size, 17)
        self.assertEqual(seen["graphics_preferences_changed"], 1)

    def test_graph_typography_state_bridge_baseline_without_legacy_wrapper(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        view = _bridge_support._GraphCanvasViewBridgeStub()
        state_bridge = GraphCanvasStateBridge(
            host,
            shell_window=host,
            canvas_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )
        seen = {
            "graphics_preferences_changed": 0,
        }
        state_bridge.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "graphics_preferences_changed",
                seen["graphics_preferences_changed"] + 1,
            )
        )

        self.assertEqual(state_bridge.graphics_graph_label_pixel_size, 10)

        host.graphics_graph_label_pixel_size = 15
        host.graphics_preferences_changed.emit()

        self.assertEqual(state_bridge.graphics_graph_label_pixel_size, 15)
        self.assertEqual(seen, {"graphics_preferences_changed": 1})

    def test_graph_node_icon_size_bridge_workspace_presenter_projects_nullable_override_and_effective_size(self) -> None:
        host = _bridge_support._ShellWorkspacePresenterHostStub()
        presenter = ShellWorkspacePresenter(host, ui_state=host.workspace_ui_state)
        seen = {"graphics_preferences_changed": 0}
        presenter.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "graphics_preferences_changed",
                seen["graphics_preferences_changed"] + 1,
            )
        )

        resolved = presenter.apply_graphics_preferences(
            {
                "typography": {
                    "graph_label_pixel_size": 16,
                    "graph_node_icon_pixel_size_override": None,
                }
            },
        )

        self.assertEqual(resolved["typography"]["graph_label_pixel_size"], 16)
        self.assertIsNone(resolved["typography"]["graph_node_icon_pixel_size_override"])
        self.assertEqual(host.workspace_ui_state.node_title_icon_pixel_size, 16)
        self.assertEqual(presenter.graphics_node_title_icon_pixel_size, 16)
        self.assertEqual(seen["graphics_preferences_changed"], 1)

        resolved = presenter.apply_graphics_preferences(
            {
                "typography": {
                    "graph_label_pixel_size": 16,
                    "graph_node_icon_pixel_size_override": 3,
                }
            },
        )

        self.assertEqual(resolved["typography"]["graph_node_icon_pixel_size_override"], 8)
        self.assertEqual(host.workspace_ui_state.node_title_icon_pixel_size, 8)
        self.assertEqual(presenter.graphics_graph_node_icon_pixel_size_override, 8)
        self.assertEqual(presenter.graphics_node_title_icon_pixel_size, 8)
        self.assertEqual(seen["graphics_preferences_changed"], 2)

    def test_graph_node_icon_size_state_bridge_baseline_without_legacy_wrapper(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        host.graphics_graph_label_pixel_size = 16
        host.graphics_graph_node_icon_pixel_size_override = None
        host.graphics_node_title_icon_pixel_size = 16
        presenter = _bridge_support._GraphCanvasShellHostStub()
        presenter.graphics_graph_label_pixel_size = 16
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        view = _bridge_support._GraphCanvasViewBridgeStub()
        state_bridge = GraphCanvasStateBridge(
            host,
            shell_window=host,
            canvas_source=presenter,
            graphics_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )

        self.assertIsNone(state_bridge.graphics_graph_node_icon_pixel_size_override)
        self.assertEqual(state_bridge.graphics_node_title_icon_pixel_size, 16)

        host.graphics_graph_node_icon_pixel_size_override = 13
        host.graphics_node_title_icon_pixel_size = 13
        host.graphics_preferences_changed.emit()

        self.assertEqual(state_bridge.graphics_graph_node_icon_pixel_size_override, 13)
        self.assertEqual(state_bridge.graphics_node_title_icon_pixel_size, 13)

    def test_graph_canvas_command_bridge_routes_comment_peek_to_scene_bridge_layer(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        scene = _bridge_support._GraphCanvasSceneBridgeStub()

        def can_open_comment_peek(node_id: str) -> bool:
            scene.calls.append(("can_open_comment_peek", (node_id,)))
            return node_id == "comment-1"

        def open_comment_peek(node_id: str) -> bool:
            scene.calls.append(("open_comment_peek", (node_id,)))
            if node_id != "comment-1":
                return False
            scene.active_comment_peek_node_id = node_id
            return True

        def close_comment_peek() -> bool:
            scene.calls.append(("close_comment_peek", ()))
            if not getattr(scene, "active_comment_peek_node_id", ""):
                return False
            scene.active_comment_peek_node_id = ""
            return True

        scene.active_comment_peek_node_id = ""
        scene.can_open_comment_peek = can_open_comment_peek
        scene.open_comment_peek = open_comment_peek
        scene.close_comment_peek = close_comment_peek

        bridge = GraphCanvasCommandBridge(
            host,
            shell_window=host,
            canvas_source=host,
            host_source=host,
            scene_bridge=scene,
            view_bridge=_bridge_support._GraphCanvasViewBridgeStub(),
        )
        action_bridge = GraphActionBridge(
            controller=GraphActionController(scene_bridge=scene),
        )

        self.assertTrue(bridge.can_open_comment_peek("comment-1"))
        self.assertFalse(bridge.can_open_comment_peek("logger-1"))
        self.assertTrue(
            action_bridge.trigger_graph_action(
                GraphActionId.OPEN_COMMENT_PEEK.value,
                {"node_id": "comment-1"},
            )
        )
        self.assertEqual(bridge.active_comment_peek_node_id(), "comment-1")
        self.assertTrue(bridge.request_close_comment_peek())
        self.assertEqual(bridge.active_comment_peek_node_id(), "")
        self.assertEqual(
            scene.calls,
            [
                ("can_open_comment_peek", ("comment-1",)),
                ("can_open_comment_peek", ("logger-1",)),
                ("open_comment_peek", ("comment-1",)),
                ("close_comment_peek", ()),
            ],
        )
        self.assertNotIn(("request_open_subnode_scope", ("comment-1",)), host.calls)


__all__ = ["GraphCanvasBridgeTests"]
