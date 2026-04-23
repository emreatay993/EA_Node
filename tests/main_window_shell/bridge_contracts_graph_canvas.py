from __future__ import annotations

import pytest

from ea_node_editor.ui.shell.controllers.graph_action_controller import GraphActionController
from ea_node_editor.ui.shell.graph_action_contracts import GraphActionId
from ea_node_editor.ui.shell.presenters.workspace_presenter import ShellWorkspacePresenter
from ea_node_editor.ui_qml.graph_action_bridge import GraphActionBridge
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from tests.main_window_shell import bridge_support as _bridge_support
from tests.main_window_shell.bridge_support import (
    GraphCanvasBridgeTests as _GraphCanvasBridgeTests,
)

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


class GraphCanvasBridgeTests(_GraphCanvasBridgeTests):
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

    def test_graph_typography_bridge_state_and_legacy_bridges_share_graph_label_pixel_size_property(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        view = _bridge_support._GraphCanvasViewBridgeStub()
        bridge = _bridge_support._build_explicit_graph_canvas_bridge(
            parent=host,
            shell_window=host,
            canvas_source=host,
            host_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )
        state_bridge = bridge.state_bridge
        seen = {
            "graphics_preferences_changed": 0,
            "legacy_graphics_preferences_changed": 0,
        }
        state_bridge.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "graphics_preferences_changed",
                seen["graphics_preferences_changed"] + 1,
            )
        )
        bridge.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "legacy_graphics_preferences_changed",
                seen["legacy_graphics_preferences_changed"] + 1,
            )
        )

        self.assertEqual(state_bridge.graphics_graph_label_pixel_size, 10)
        self.assertEqual(bridge.graphics_graph_label_pixel_size, 10)

        host.graphics_graph_label_pixel_size = 15
        host.graphics_preferences_changed.emit()

        self.assertEqual(state_bridge.graphics_graph_label_pixel_size, 15)
        self.assertEqual(bridge.graphics_graph_label_pixel_size, 15)
        self.assertEqual(
            seen,
            {
                "graphics_preferences_changed": 1,
                "legacy_graphics_preferences_changed": 1,
            },
        )

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

    def test_graph_node_icon_size_bridge_state_and_legacy_bridges_share_effective_size_property(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        host.graphics_graph_label_pixel_size = 16
        host.graphics_graph_node_icon_pixel_size_override = None
        host.graphics_node_title_icon_pixel_size = 16
        presenter = _bridge_support._GraphCanvasShellHostStub()
        presenter.graphics_graph_label_pixel_size = 16
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        view = _bridge_support._GraphCanvasViewBridgeStub()
        bridge = _bridge_support._build_explicit_graph_canvas_bridge(
            parent=host,
            shell_window=host,
            canvas_source=presenter,
            host_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )
        state_bridge = bridge.state_bridge

        self.assertIsNone(state_bridge.graphics_graph_node_icon_pixel_size_override)
        self.assertIsNone(bridge.graphics_graph_node_icon_pixel_size_override)
        self.assertEqual(state_bridge.graphics_node_title_icon_pixel_size, 16)
        self.assertEqual(bridge.graphics_node_title_icon_pixel_size, 16)

        host.graphics_graph_node_icon_pixel_size_override = 13
        host.graphics_node_title_icon_pixel_size = 13
        host.graphics_preferences_changed.emit()

        self.assertEqual(state_bridge.graphics_graph_node_icon_pixel_size_override, 13)
        self.assertEqual(bridge.graphics_graph_node_icon_pixel_size_override, 13)
        self.assertEqual(state_bridge.graphics_node_title_icon_pixel_size, 13)
        self.assertEqual(bridge.graphics_node_title_icon_pixel_size, 13)

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

        self.assertTrue(bridge.can_open_comment_peek("comment-1"))
        self.assertFalse(bridge.can_open_comment_peek("logger-1"))
        self.assertTrue(bridge.request_open_comment_peek("comment-1"))
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
