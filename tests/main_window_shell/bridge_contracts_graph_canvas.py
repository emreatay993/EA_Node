from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import pytest
from PyQt6.QtCore import QObject, QPointF, pyqtSignal
from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import NodeLinkRecord
from ea_node_editor.nodes.builtins.passive_annotation import PASSIVE_ANNOTATION_TEXT_TYPE_ID
from ea_node_editor.nodes.builtins.media_panel import MEDIA_PANEL_TYPE_ID
from ea_node_editor.ui.shell.controllers.graph_action_controller import GraphActionController
from ea_node_editor.ui.shell.graph_action_contracts import GraphActionId
from ea_node_editor.ui.shell.presenters import workspace_presenter as workspace_presenter_module
from ea_node_editor.ui.shell.presenters.workspace_presenter import ShellWorkspacePresenter
from ea_node_editor.ui.shell.tooltip_policy import (
    TOOLTIP_CATEGORY_ADVANCED,
    TOOLTIP_CATEGORY_NAMES,
    TOOLTIP_CATEGORY_WARNING,
)
from ea_node_editor.ui_qml.graph_action_bridge import GraphActionBridge
from ea_node_editor.ui_qml.graph_canvas_bridge import GraphCanvasBridge
from ea_node_editor.ui_qml.graph_canvas_command import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_canvas_state import graphics_preferences_props as graphics_preferences_module
from ea_node_editor.ui_qml.graph_scene.command_bridge import GraphSceneCommandBridge
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

    def set_selection_same_type_width(self, node_ids: tuple[str, ...]) -> bool:
        return self._record("set_selection_same_type_width", node_ids)

    def set_selection_same_type_height(self, node_ids: tuple[str, ...]) -> bool:
        return self._record("set_selection_same_type_height", node_ids)

    def straighten_selection_connections(self) -> bool:
        return self._record("straighten_selection_connections")

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

    def request_propagate_passive_node_style(self, node_id: str) -> bool:
        return self._record("request_propagate_passive_node_style", node_id)

    def run_selected_nodes(self, node_ids=None) -> bool:
        return self._record("run_selected_nodes", tuple(node_ids or ()))

    def preview_selected_run(self, node_ids=None) -> bool:
        return self._record("preview_selected_run", tuple(node_ids or ()))

    def open_selected_run_settings(self) -> bool:
        return self._record("open_selected_run_settings")

    def confirm_selected_run_preview(self) -> bool:
        return self._record("confirm_selected_run_preview")

    def clear_selected_run_preview(self) -> bool:
        return self._record("clear_selected_run_preview")


class _WorkspaceLinkController:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def switch_workspace(self, workspace_id: str) -> None:
        self.calls.append(("switch_workspace", (workspace_id,)))

    def jump_to_graph_node(self, workspace_id: str, node_id: str) -> bool:
        self.calls.append(("jump_to_graph_node", (workspace_id, node_id)))
        return True


class _SceneBridgeForNodeLinkTests(QObject):
    pending_surface_action_changed = pyqtSignal()

    def __init__(self, model: GraphModel, workspace_id: str) -> None:
        super().__init__()
        self._model = model
        self._workspace_id = workspace_id


class _AuthoringBoundaryForNodeLinkTests:
    def __init__(self, model: GraphModel, workspace_id: str) -> None:
        self.model = model
        self.workspace_id = workspace_id
        self.focus_calls: list[str] = []
        self.property_calls: list[tuple[str, str, object]] = []

    def focus_node(self, node_id: str) -> QPointF:
        self.focus_calls.append(str(node_id))
        return QPointF(10.0, 20.0)

    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        self.property_calls.append((str(node_id), str(key), value))
        self.model.set_node_property(self.workspace_id, str(node_id), str(key), value)


class _BatchEdgeAuthoringBoundary:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.rewire_result = True
        self.display_mode_result = True

    def request_rewire_edges(
        self,
        edge_ids: list[object],
        endpoint: str,
        node_id: str,
        port_key: str,
        copy_requested: bool,
        append_requested: bool,
    ) -> bool:
        self.calls.append(
            (
                "request_rewire_edges",
                (
                    list(edge_ids),
                    endpoint,
                    node_id,
                    port_key,
                    copy_requested,
                    append_requested,
                ),
            )
        )
        return self.rewire_result

    def set_edges_display_mode(self, edge_ids: list[object], mode: str) -> bool:
        self.calls.append(("set_edges_display_mode", (list(edge_ids), mode)))
        return self.display_mode_result


class _CanvasRewireSource:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.result = True

    def request_rewire_edges(
        self,
        edge_ids: list[object],
        endpoint: str,
        node_id: str,
        port_key: str,
        copy_requested: bool,
        append_requested: bool,
    ) -> bool:
        self.calls.append(
            (
                "request_rewire_edges",
                (
                    list(edge_ids),
                    endpoint,
                    node_id,
                    port_key,
                    copy_requested,
                    append_requested,
                ),
            )
        )
        return self.result


class _RewireEndpointPolicy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.result: object = {
            "candidate_role": "target",
            "compatible_endpoint_ids": [{"node_id": "sink", "port_key": "payload"}],
        }

    def compatible_rewire_endpoint_snapshot(
        self,
        edge_ids: list[object],
        endpoint: str,
        copy_requested: bool,
        append_requested: bool,
    ) -> object:
        self.calls.append(
            (
                "compatible_rewire_endpoint_snapshot",
                (list(edge_ids), endpoint, copy_requested, append_requested),
            )
        )
        return self.result


class GraphCanvasBridgeTests(unittest.TestCase):
    __test__ = True

    def test_command_bridge_text_annotation_style_clipboard_is_internal(self) -> None:
        app = QApplication.instance() or QApplication([])
        app.setProperty("eaNodeEditorStyleClipboard:text-annotation-style", "")
        clipboard = app.clipboard()
        clipboard.setText("external clipboard text")
        bridge = GraphCanvasCommandBridge()

        self.assertFalse(bridge.has_text_annotation_style())
        self.assertEqual(bridge.paste_text_annotation_style(), {})
        self.assertTrue(
            bridge.copy_text_annotation_style(
                {
                    "text": "Do not copy content",
                    "format": "plain",
                    "font_family": "  Segoe UI  ",
                    "font_size": 999,
                    "text_color": "#aabbcc",
                    "horizontal_alignment": "right",
                    "line_height": 9,
                    "opacity": -2,
                }
            )
        )

        self.assertEqual(clipboard.text(), "external clipboard text")
        self.assertTrue(bridge.has_text_annotation_style())
        self.assertEqual(
            bridge.paste_text_annotation_style(),
            {
                "font_family": "Segoe UI",
                "font_size": 144,
                "text_color": "#AABBCC",
                "horizontal_alignment": "right",
                "line_height": 4.0,
                "opacity": 0,
            },
        )

    def test_command_bridge_opens_workspace_node_link_through_shell_navigation(self) -> None:
        controller = _WorkspaceLinkController()
        active_workspace = SimpleNamespace(
            nodes={
                "node-1": SimpleNamespace(
                    links=[
                        NodeLinkRecord(
                            link_id="link-workspace",
                            kind="workspace",
                            title="Target workspace",
                            target="ws-target",
                        )
                    ]
                )
            }
        )
        shell = SimpleNamespace(
            model=SimpleNamespace(
                project=SimpleNamespace(
                    workspaces={
                        "ws-active": active_workspace,
                        "ws-target": SimpleNamespace(nodes={}),
                    }
                )
            ),
            workspace_manager=SimpleNamespace(active_workspace_id=lambda: "ws-active"),
            workspace_library_controller=controller,
        )
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        scene._return_values["open_node_link"] = False
        command_bridge = GraphCanvasCommandBridge(shell_window=shell, scene_bridge=scene)

        self.assertTrue(command_bridge.open_node_link("node-1", "link-workspace"))
        self.assertEqual(controller.calls, [("switch_workspace", ("ws-target",))])
        self.assertNotIn(("open_node_link", ("node-1", "link-workspace")), scene.calls)

    def test_command_bridge_opens_cross_workspace_node_link_through_graph_jump(self) -> None:
        controller = _WorkspaceLinkController()
        active_workspace = SimpleNamespace(
            nodes={
                "node-source": SimpleNamespace(
                    links=[
                        NodeLinkRecord(
                            link_id="link-cross-node",
                            kind="node",
                            title="Target node",
                            target="node-target",
                            target_workspace_id="ws-target",
                            target_node_id="node-target",
                        )
                    ]
                )
            }
        )
        target_workspace = SimpleNamespace(nodes={"node-target": SimpleNamespace(links=[])})
        shell = SimpleNamespace(
            model=SimpleNamespace(
                project=SimpleNamespace(
                    workspaces={
                        "ws-active": active_workspace,
                        "ws-target": target_workspace,
                    }
                )
            ),
            workspace_manager=SimpleNamespace(active_workspace_id=lambda: "ws-active"),
            workspace_library_controller=controller,
        )
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        scene._workspace_id = "ws-active"
        scene._return_values["open_node_link"] = False
        command_bridge = GraphCanvasCommandBridge(shell_window=shell, scene_bridge=scene)

        self.assertTrue(command_bridge.open_node_link("node-source", "link-cross-node"))
        self.assertEqual(controller.calls, [("jump_to_graph_node", ("ws-target", "node-target"))])
        self.assertNotIn(("open_node_link", ("node-source", "link-cross-node")), scene.calls)

    def test_scene_command_bridge_rejects_cross_workspace_node_link(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        source = model.add_node(
            workspace.workspace_id,
            "core.logger",
            "Source",
            40.0,
            60.0,
        )
        workspace.nodes[source.node_id].links.append(
            NodeLinkRecord(
                link_id="link-cross-node",
                kind="node",
                title="Target",
                target="node-target",
                target_workspace_id="workspace-target",
                target_node_id="node-target",
            )
        )
        authoring = _AuthoringBoundaryForNodeLinkTests(model, workspace.workspace_id)
        bridge = GraphSceneCommandBridge(
            _SceneBridgeForNodeLinkTests(model, workspace.workspace_id),
            scope_selection=SimpleNamespace(),
            authoring_boundary=authoring,
            pending_surface_action=SimpleNamespace(node_id=""),
        )

        self.assertFalse(bridge.open_node_link(source.node_id, "link-cross-node"))
        self.assertEqual(authoring.focus_calls, [])

    def test_scene_command_bridge_opens_video_timestamp_node_link_and_updates_position(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            video_path = Path(temporary_directory) / "clip.mp4"
            video_path.write_bytes(b"video")
            model = GraphModel()
            workspace = model.active_workspace
            video = model.add_node(
                workspace.workspace_id,
                MEDIA_PANEL_TYPE_ID,
                "Media Panel",
                40.0,
                60.0,
                properties={"source": str(video_path), "position_ms": 0},
                exposed_ports={"source": False},
            )
            note = model.add_node(
                workspace.workspace_id,
                PASSIVE_ANNOTATION_TEXT_TYPE_ID,
                "Video note",
                240.0,
                60.0,
            )
            workspace.nodes[note.node_id].links.append(
                NodeLinkRecord(
                    link_id="link-video-time",
                    kind="node",
                    title="Video 0:07",
                    target=video.node_id,
                    subtitle="video_position_ms=7777",
                )
            )
            authoring = _AuthoringBoundaryForNodeLinkTests(model, workspace.workspace_id)
            bridge = GraphSceneCommandBridge(
                _SceneBridgeForNodeLinkTests(model, workspace.workspace_id),
                scope_selection=SimpleNamespace(),
                authoring_boundary=authoring,
                pending_surface_action=SimpleNamespace(node_id=""),
            )

            self.assertTrue(bridge.open_node_link(note.node_id, "link-video-time"))
            self.assertEqual(authoring.property_calls, [(video.node_id, "position_ms", 7777)])
            self.assertEqual(authoring.focus_calls, [video.node_id])
            self.assertEqual(workspace.nodes[video.node_id].properties["position_ms"], 7777)

    def test_scene_command_bridge_focuses_nonready_media_timestamp_target_without_seeking(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        media = model.add_node(
            workspace.workspace_id,
            MEDIA_PANEL_TYPE_ID,
            "Media Panel",
            40.0,
            60.0,
            properties={"source": "C:/dormant/clip.mp4", "position_ms": 0},
            exposed_ports={"source": True},
        )
        note = model.add_node(
            workspace.workspace_id,
            PASSIVE_ANNOTATION_TEXT_TYPE_ID,
            "Video note",
            240.0,
            60.0,
        )
        workspace.nodes[note.node_id].links.append(
            NodeLinkRecord(
                link_id="link-video-time",
                kind="node",
                title="Video 0:07",
                target=media.node_id,
                subtitle="video_position_ms=7777",
            )
        )
        authoring = _AuthoringBoundaryForNodeLinkTests(model, workspace.workspace_id)
        bridge = GraphSceneCommandBridge(
            _SceneBridgeForNodeLinkTests(model, workspace.workspace_id),
            scope_selection=SimpleNamespace(),
            authoring_boundary=authoring,
            pending_surface_action=SimpleNamespace(node_id=""),
        )

        self.assertTrue(bridge.open_node_link(note.node_id, "link-video-time"))
        self.assertEqual(authoring.property_calls, [])
        self.assertEqual(authoring.focus_calls, [media.node_id])
        self.assertEqual(workspace.nodes[media.node_id].properties["position_ms"], 0)

    def test_scene_command_bridge_forwards_batch_rewire_and_display_mode_results(self) -> None:
        scene = _SceneBridgeForNodeLinkTests(GraphModel(), "workspace-1")
        authoring = _BatchEdgeAuthoringBoundary()
        bridge = GraphSceneCommandBridge(
            scene,
            scope_selection=SimpleNamespace(),
            authoring_boundary=authoring,
            pending_surface_action=SimpleNamespace(node_id=""),
        )

        self.assertTrue(
            bridge.request_rewire_edges(
                ["edge-2", "edge-1"],
                "target",
                "sink-node",
                "payload",
                True,
                True,
            )
        )
        self.assertTrue(bridge.set_edges_display_mode(["edge-1", "edge-2"], "faint"))
        authoring.rewire_result = False
        authoring.display_mode_result = False
        self.assertFalse(
            bridge.request_rewire_edges(
                ["edge-1"], "source", "", "", False, False
            )
        )
        self.assertFalse(bridge.set_edges_display_mode(["edge-1"], "hidden"))
        self.assertEqual(
            authoring.calls,
            [
                (
                    "request_rewire_edges",
                    (
                        ["edge-2", "edge-1"],
                        "target",
                        "sink-node",
                        "payload",
                        True,
                        True,
                    ),
                ),
                ("set_edges_display_mode", (["edge-1", "edge-2"], "faint")),
                (
                    "request_rewire_edges",
                    (["edge-1"], "source", "", "", False, False),
                ),
                ("set_edges_display_mode", (["edge-1"], "hidden")),
            ],
        )

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
        self.assertTrue(
            controller.trigger(
                GraphActionId.SET_SELECTION_SAME_TYPE_WIDTH.value,
                {"node_ids": ["node-1", "node-2"]},
            )
        )
        self.assertTrue(
            controller.trigger(
                GraphActionId.SET_SELECTION_SAME_TYPE_HEIGHT.value,
                {"node_ids": ["node-3", "node-4"]},
            )
        )
        self.assertTrue(controller.trigger(GraphActionId.STRAIGHTEN_SELECTION_CONNECTIONS.value))
        self.assertTrue(controller.trigger(GraphActionId.DELETE_SELECTION.value, {"edge_ids": ["edge-1"]}))
        self.assertTrue(controller.trigger(GraphActionId.OPEN_SUBNODE_SCOPE.value, {"node_id": "node-1"}))
        self.assertTrue(
            controller.trigger(GraphActionId.PUBLISH_CUSTOM_WORKFLOW_FROM_NODE.value, {"node_id": "node-2"})
        )
        self.assertTrue(controller.trigger(GraphActionId.OPEN_COMMENT_PEEK.value, {"node_id": "comment-1"}))
        self.assertTrue(controller.trigger(GraphActionId.CLOSE_COMMENT_PEEK.value))
        self.assertTrue(controller.trigger(GraphActionId.OPEN_ADDON_MANAGER_FOR_NODE.value, {"node_id": "locked-node"}))
        self.assertTrue(controller.trigger(GraphActionId.REMOVE_EDGE.value, {"edge_id": "edge-1"}))
        self.assertTrue(
            controller.trigger(GraphActionId.PROPAGATE_PASSIVE_NODE_STYLE.value, {"node_id": "node-3"})
        )

        self.assertEqual(
            workspace.calls,
            [
                ("copy_selected_nodes_to_clipboard", ()),
                ("align_selection_left", ()),
                ("set_selection_same_type_width", (("node-1", "node-2"),)),
                ("set_selection_same_type_height", (("node-3", "node-4"),)),
                ("straighten_selection_connections", ()),
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
                ("request_propagate_passive_node_style", ("node-3",)),
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

    def test_graph_action_controller_routes_selected_run_actions(self) -> None:
        run_controller = _GraphActionSource()
        controller = GraphActionController(run_controller=run_controller)

        self.assertTrue(controller.trigger(GraphActionId.RUN_SELECTED.value, {"node_id": "node-1"}))
        self.assertTrue(controller.trigger(GraphActionId.PREVIEW_SELECTED_RUN.value, {"node_id": "node-3"}))
        self.assertTrue(controller.trigger(GraphActionId.OPEN_SELECTED_RUN_SETTINGS.value))
        self.assertTrue(controller.trigger(GraphActionId.CONFIRM_SELECTED_RUN_PREVIEW.value))
        self.assertTrue(controller.trigger(GraphActionId.CLEAR_SELECTED_RUN_PREVIEW.value))

        self.assertEqual(
            run_controller.calls,
            [
                ("run_selected_nodes", (("node-1",),)),
                ("preview_selected_run", (("node-3",),)),
                ("open_selected_run_settings", ()),
                ("confirm_selected_run_preview", ()),
                ("clear_selected_run_preview", ()),
            ],
        )

    def test_graph_action_controller_opens_node_path_via_platform_helpers(self) -> None:
        import ea_node_editor.ui.shell.controllers.graph_action_controller as controller_module

        class _PathPointerScene:
            nodes_model = [
                {
                    "node_id": "pp-1",
                    "type_id": "io.path_pointer",
                    "properties": {"path": "C:/tmp/file.txt", "mode": "file"},
                }
            ]

        class _HintPresenter:
            def __init__(self) -> None:
                self.hints: list[tuple[str, int]] = []

            def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
                self.hints.append((message, timeout_ms))

        presenter = _HintPresenter()
        controller = GraphActionController(scene_bridge=_PathPointerScene(), graph_canvas_presenter=presenter)

        default_calls: list[str] = []
        chooser_calls: list[str] = []
        with mock.patch.object(
            controller_module,
            "open_path_with_default_handler",
            lambda path: default_calls.append(path) or True,
        ), mock.patch.object(
            controller_module,
            "open_path_with_app_chooser",
            lambda path: chooser_calls.append(path) or True,
        ):
            self.assertTrue(controller.trigger(GraphActionId.OPEN_NODE_PATH.value, {"node_id": "pp-1"}))
            self.assertTrue(controller.trigger(GraphActionId.OPEN_NODE_PATH_WITH.value, {"node_id": "pp-1"}))

        self.assertEqual(default_calls, ["C:/tmp/file.txt"])
        self.assertEqual(chooser_calls, ["C:/tmp/file.txt"])
        self.assertEqual(presenter.hints, [])

    def test_graph_action_controller_open_node_path_hints_when_path_missing(self) -> None:
        import ea_node_editor.ui.shell.controllers.graph_action_controller as controller_module

        class _EmptyPathPointerScene:
            nodes_model = [
                {"node_id": "pp-1", "type_id": "io.path_pointer", "properties": {"path": ""}}
            ]

        class _HintPresenter:
            def __init__(self) -> None:
                self.hints: list[tuple[str, int]] = []

            def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
                self.hints.append((message, timeout_ms))

        presenter = _HintPresenter()
        controller = GraphActionController(scene_bridge=_EmptyPathPointerScene(), graph_canvas_presenter=presenter)

        opener_calls: list[str] = []
        with mock.patch.object(
            controller_module,
            "open_path_with_default_handler",
            lambda path: opener_calls.append(path) or True,
        ):
            self.assertFalse(controller.trigger(GraphActionId.OPEN_NODE_PATH.value, {"node_id": "pp-1"}))

        self.assertEqual(opener_calls, [])
        self.assertEqual(len(presenter.hints), 1)
        self.assertIn("No path", presenter.hints[0][0])

    def test_graph_action_bridge_exposes_contract_metadata_and_rejects_bad_payloads(self) -> None:
        host_presenter = _GraphActionSource()
        controller = GraphActionController(graph_canvas_host_presenter=host_presenter)
        bridge = GraphActionBridge(controller=controller)

        self.assertIn(GraphActionId.REMOVE_EDGE.value, bridge.actionIds)
        self.assertEqual(
            bridge.action_metadata(GraphActionId.EDIT_FLOW_EDGE_STYLE.value)["actionId"],
            GraphActionId.EDIT_FLOW_EDGE_STYLE.value,
        )
        self.assertEqual(bridge.action_metadata("edit_flow_edge"), {})
        self.assertEqual(
            bridge.action_metadata(GraphActionId.REMOVE_EDGE.value)["requiredPayloadKeys"],
            ["edge_id"],
        )
        self.assertTrue(bridge.trigger_graph_action("edit_flow_edge_style", {"edge_id": "edge-2"}))
        self.assertFalse(bridge.trigger_graph_action("edit_flow_edge_style", {"edge_id": ""}))
        self.assertFalse(bridge.trigger_graph_action("edit_flow_edge_style", {"edge_id": 123}))
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
            bridge.internalize_node_property_path("node-1", "source_path", "C:/temp/current.txt"),
            "temp://from-canvas-internalized",
        )
        self.assertEqual(
            bridge.pick_node_property_color("node-1", "accent_color", "#336699"),
            "#AA5500",
        )
        self.assertEqual(
            bridge.request_save_image_crop_replace(
                "image-1",
                {"x": 0.25, "y": 0.1, "width": 0.5, "height": 0.8},
            )["source_ref"],
            "project-staged://image_crop_1",
        )
        self.assertTrue(
            bridge.request_drop_node_from_library(
                "core.logger",
                120.0,
                240.0,
                "port",
                "node-1",
                "payload",
                "edge-1",
            )
        )
        self.assertTrue(bridge.request_connect_ports("node-1", "value", "node-2", "payload"))
        self.assertTrue(
            bridge.request_open_connection_quick_insert(
                "node-1",
                "value",
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
        self.assertEqual(
            bridge.upsert_node_link(
                "node-1",
                "",
                "url",
                "Docs",
                "https://example.com/docs",
                "Reference",
            ),
            "link-1",
        )
        self.assertTrue(bridge.remove_node_link("node-1", "link-1"))
        self.assertTrue(bridge.move_node_link("node-1", "link-1", -1))
        self.assertTrue(bridge.open_node_link("node-1", "link-1"))
        self.assertTrue(bridge.are_port_kinds_compatible("data", "data"))
        self.assertTrue(bridge.are_data_types_compatible("text", "text"))
        self.assertTrue(bridge.move_nodes_by_delta(["node-1", "node-2"], 10.0, -5.0))
        bridge.move_node("node-1", 160.0, 220.0)
        bridge.resize_node("node-1", 320.0, 180.0)
        bridge.set_node_geometry("node-1", 150.0, 210.0, 340.0, 190.0)
        self.assertEqual(bridge.normalize_edge_label("  Primary path  "), "Primary path")
        self.assertTrue(bridge.set_edge_label("edge-1", "Loop branch"))
        self.assertTrue(bridge.clear_edge_label("edge-1"))
        self.assertEqual(
            bridge.normalize_edge_visual_style({"stroke_color": "#E06C75", "stroke_pattern": "dashed"}),
            {"stroke_color": "#E06C75", "stroke_pattern": "dashed"},
        )
        self.assertTrue(bridge.set_edge_visual_style("edge-1", {"stroke_color": "#E06C75"}))
        self.assertTrue(bridge.clear_edge_visual_style("edge-1"))
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
            bridge.describe_mail_preview("C:/temp/message.eml"),
            {
                "source": "C:/temp/message.eml",
                "state": "ready",
                "preview_url": "file:///C:/temp/mail-preview.html",
            },
        )
        self.assertEqual(
            bridge.open_local_file_source("C:/temp/message.eml", True),
            {"success": True, "path": "C:/temp/message.eml", "error": {}},
        )

        self.assertEqual(
            presenter.calls,
            [
                ("set_graphics_minimap_expanded", (False,)),
                ("request_open_subnode_scope", ("subnode-1",)),
                ("browse_node_property_path", ("node-1", "source_path", "C:/temp/current.txt")),
                ("internalize_node_property_path", ("node-1", "source_path", "C:/temp/current.txt")),
                ("pick_node_property_color", ("node-1", "accent_color", "#336699")),
                (
                    "request_save_image_crop_replace",
                    ("image-1", {"x": 0.25, "y": 0.1, "width": 0.5, "height": 0.8}),
                ),
                (
                    "request_drop_node_from_library",
                    ("core.logger", 120.0, 240.0, "port", "node-1", "payload", "edge-1"),
                ),
                ("request_connect_ports", ("node-1", "value", "node-2", "payload", False)),
                (
                    "request_open_connection_quick_insert",
                    ("node-1", "value", 20.0, 30.0, 400.0, 300.0, False),
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
                ("describe_mail_preview", ("C:/temp/message.eml",)),
                ("open_local_file_source", ("C:/temp/message.eml", True)),
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
                (
                    "upsert_node_link",
                    ("node-1", "", "url", "Docs", "https://example.com/docs", "Reference"),
                ),
                ("remove_node_link", ("node-1", "link-1")),
                ("move_node_link", ("node-1", "link-1", -1)),
                ("open_node_link", ("node-1", "link-1")),
                ("are_port_kinds_compatible", ("data", "data")),
                ("are_data_types_compatible", ("text", "text")),
                ("move_nodes_by_delta", (["node-1", "node-2"], 10.0, -5.0)),
                ("move_node", ("node-1", 160.0, 220.0)),
                ("resize_node", ("node-1", 320.0, 180.0)),
                ("set_node_geometry", ("node-1", 150.0, 210.0, 340.0, 190.0)),
                ("normalize_edge_label", ("  Primary path  ",)),
                ("set_edge_label", ("edge-1", "Loop branch")),
                ("clear_edge_label", ("edge-1",)),
                (
                    "normalize_edge_visual_style",
                    ({"stroke_color": "#E06C75", "stroke_pattern": "dashed"},),
                ),
                ("set_edge_visual_style", ("edge-1", {"stroke_color": "#E06C75"})),
                ("clear_edge_visual_style", ("edge-1",)),
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

    def test_command_bridge_exposes_tabular_preview_slot_for_qml_inline_surfaces(self) -> None:
        host_source = _bridge_support._GraphCanvasShellHostStub()
        bridge = GraphCanvasCommandBridge(host_source=host_source)

        meta_object = bridge.metaObject()
        self.assertGreaterEqual(
            meta_object.indexOfMethod(b"describe_tabular_preview(QVariantMap,QVariantMap)"),
            0,
        )

        payload = bridge.describe_tabular_preview(
            {"path": "C:/temp/stations.csv"},
            {"row_limit": 50, "column_limit": 50},
        )

        self.assertEqual(payload["state"], "ready")
        self.assertEqual(payload["preview_kind"], "table")
        self.assertEqual(payload["source"]["path"], "C:/temp/stations.csv")
        self.assertEqual(
            host_source.calls,
            [
                (
                    "describe_tabular_preview",
                    (
                        {"path": "C:/temp/stations.csv"},
                        {"row_limit": 50, "column_limit": 50},
                    ),
                )
            ],
        )

    def test_canvas_command_bridge_forwards_batch_rewire_and_preserves_boolean_failure(self) -> None:
        source = _CanvasRewireSource()
        bridge = GraphCanvasCommandBridge(canvas_source=source)

        self.assertTrue(
            bridge.request_rewire_edges(
                ["edge-a", "edge-b"],
                "target",
                "sink-node",
                "payload",
                True,
                False,
            )
        )
        source.result = False
        self.assertFalse(
            bridge.request_rewire_edges(["edge-a"], "target", "", "", False, False)
        )
        self.assertEqual(
            source.calls,
            [
                (
                    "request_rewire_edges",
                    (
                        ["edge-a", "edge-b"],
                        "target",
                        "sink-node",
                        "payload",
                        True,
                        False,
                    ),
                ),
                (
                    "request_rewire_edges",
                    (["edge-a"], "target", "", "", False, False),
                ),
            ],
        )

    def test_graph_canvas_bridge_exposes_only_the_batch_rewire_surface(self) -> None:
        source = _CanvasRewireSource()
        bridge = GraphCanvasBridge(
            command_bridge=GraphCanvasCommandBridge(canvas_source=source),
        )

        self.assertTrue(
            bridge.request_rewire_edges(
                ["edge-a", "edge-b"],
                "target",
                "sink-node",
                "payload",
                False,
                True,
            )
        )
        meta = bridge.metaObject()
        self.assertGreaterEqual(
            meta.indexOfMethod(
                b"request_rewire_edges(QVariantList,QString,QString,QString,bool,bool)"
            ),
            0,
        )
        self.assertEqual(
            meta.indexOfMethod(
                b"request_move_edge_endpoint(QString,QString,QString,QString,bool)"
            ),
            -1,
        )
        self.assertEqual(
            source.calls,
            [
                (
                    "request_rewire_edges",
                    (
                        ["edge-a", "edge-b"],
                        "target",
                        "sink-node",
                        "payload",
                        False,
                        True,
                    ),
                )
            ],
        )

    def test_state_bridge_forwards_compatible_rewire_snapshot_and_rejects_non_map(self) -> None:
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        policy = _RewireEndpointPolicy()
        scene.policy_bridge = policy
        bridge = GraphCanvasStateBridge(scene_bridge=scene)

        self.assertEqual(
            bridge.compatible_rewire_endpoint_snapshot(
                ["edge-a", "edge-b"], "target", True, False
            ),
            policy.result,
        )
        policy.result = ["not", "a", "map"]
        self.assertEqual(
            bridge.compatible_rewire_endpoint_snapshot(["edge-a"], "source", False, True),
            {},
        )
        self.assertEqual(
            policy.calls,
            [
                (
                    "compatible_rewire_endpoint_snapshot",
                    (["edge-a", "edge-b"], "target", True, False),
                ),
                (
                    "compatible_rewire_endpoint_snapshot",
                    (["edge-a"], "source", False, True),
                ),
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
        self.assertEqual(state_bridge.graphics_canvas_background_variant, "theme")
        self.assertTrue(state_bridge.graphics_show_minimap)
        self.assertTrue(state_bridge.graphics_show_canvas_options_button)
        self.assertTrue(state_bridge.graphics_show_port_labels)
        self.assertTrue(state_bridge.graphics_notched_ports)
        self.assertEqual(state_bridge.graphics_node_elapsed_time_unit, "seconds")
        self.assertEqual(state_bridge.graphics_node_elapsed_time_visibility, "always")
        self.assertEqual(state_bridge.graphics_node_comment_editor_default, "canvas_popover")
        self.assertFalse(state_bridge.graphics_node_floating_toolbar_opens_on_hover)
        self.assertEqual(state_bridge.graphics_folder_explorer_column_widths, {})
        self.assertTrue(state_bridge.graphics_node_shadow)
        self.assertEqual(state_bridge.graphics_shadow_strength, 70)
        self.assertEqual(state_bridge.graphics_shadow_softness, 50)
        self.assertEqual(state_bridge.graphics_shadow_offset, 4)
        self.assertEqual(state_bridge.graphics_status_bar_layout, "option_1")
        self.assertTrue(state_bridge.graphics_show_fps_telemetry)
        self.assertEqual(state_bridge.graphics_selection_toolbar_mode, "minimal_ghost_menu")
        self.assertEqual(
            state_bridge.graphics_selection_toolbar_minimal_menu_trigger,
            "click_affordance",
        )
        self.assertTrue(state_bridge.snap_to_grid_enabled)
        self.assertEqual(state_bridge.snap_grid_size, 24.0)
        self.assertEqual(state_bridge.center_x, 18.5)
        self.assertEqual(state_bridge.center_y, -42.0)
        self.assertEqual(state_bridge.zoom_value, 1.75)
        self.assertEqual(state_bridge.nodes_model, scene.nodes_model)
        self.assertEqual(state_bridge.edges_model, scene.edges_model)
        self.assertEqual(state_bridge.selected_node_ids, scene.selected_node_ids)
        self.assertEqual(state_bridge.selected_node_lookup, scene.selected_node_lookup)

        host.graphics_notched_ports = False
        self.assertFalse(state_bridge.graphics_notched_ports)

        command_bridge.set_graphics_minimap_expanded(False)
        command_bridge.set_graphics_canvas_background_variant("white")
        command_bridge.set_graphics_show_port_labels(False)
        command_bridge.set_graphics_node_elapsed_time_unit("milliseconds")
        command_bridge.set_graphics_node_elapsed_time_visibility("during_run")
        command_bridge.set_graphics_node_comment_editor_default("inspector")
        self.assertFalse(state_bridge.graphics_show_port_labels)
        self.assertEqual(state_bridge.graphics_node_elapsed_time_unit, "milliseconds")
        self.assertEqual(state_bridge.graphics_node_elapsed_time_visibility, "during_run")
        self.assertEqual(state_bridge.graphics_node_comment_editor_default, "inspector")
        host.graphics_node_floating_toolbar_opens_on_hover = True
        self.assertTrue(state_bridge.graphics_node_floating_toolbar_opens_on_hover)
        self.assertEqual(state_bridge.graphics_canvas_background_variant, "white")
        command_bridge.set_folder_explorer_column_widths({"name": 240})
        self.assertEqual(state_bridge.graphics_folder_explorer_column_widths, {"name": 240})
        command_bridge.set_graphics_selection_toolbar_mode("side_rail")
        command_bridge.set_graphics_selection_toolbar_minimal_menu_trigger("right_click")
        self.assertEqual(state_bridge.graphics_selection_toolbar_mode, "side_rail")
        self.assertEqual(
            state_bridge.graphics_selection_toolbar_minimal_menu_trigger,
            "right_click",
        )
        command_bridge.adjust_zoom(1.15)
        command_bridge.pan_by(-12.0, 8.0)
        command_bridge.set_viewport_size(1280.0, 720.0)
        self.assertTrue(command_bridge.request_open_subnode_scope("subnode-1"))
        self.assertEqual(
            command_bridge.browse_node_property_path("node-1", "source_path", "C:/temp/current.txt"),
            "C:/temp/from-canvas-bridge.txt",
        )
        self.assertEqual(
            command_bridge.internalize_node_property_path("node-1", "source_path", "C:/temp/current.txt"),
            "temp://from-canvas-internalized",
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
                "payload",
                "edge-1",
            )
        )
        self.assertEqual(command_bridge.video_frame_capture_path("video-1", 4567), "C:/temp/corex-video-frame.png")
        self.assertEqual(
            command_bridge.request_save_image_crop_replace(
                "image-1",
                {"x": 0.25, "y": 0.1, "width": 0.5, "height": 0.8},
            )["source_ref"],
            "project-staged://image_crop_1",
        )
        self.assertEqual(
            command_bridge.request_create_video_frame_image_node(
                "video-1",
                "C:/temp/captured-frame.png",
                4567,
                320.0,
                180.0,
                512.0,
                384.0,
            )["created_node_id"],
            "image-node-1",
        )
        self.assertEqual(
            command_bridge.request_create_video_timestamp_annotation(
                "video-1",
                4567,
                340.0,
                220.0,
            )["link_id"],
            "link-video-1",
        )
        self.assertEqual(
            command_bridge.request_trim_video_clip_replace(
                "video-1",
                1000,
                4000,
                {"clip_enabled": True, "clip_start_ms": 1000, "clip_end_ms": 4000},
            )["request_id"],
            "trim-replace-1",
        )
        self.assertEqual(
            command_bridge.request_trim_video_clip_copy(
                "video-1",
                1000,
                4000,
                360.0,
                240.0,
                {"clip_enabled": True, "clip_start_ms": 1000, "clip_end_ms": 4000},
            )["created_node_id"],
            "video-copy-1",
        )
        self.assertTrue(command_bridge.request_connect_ports("node-1", "value", "node-2", "payload"))
        command_bridge.select_node("node-1", True)
        command_bridge.set_node_property("node-1", "message", "hello")
        self.assertEqual(
            command_bridge.upsert_node_link("node-1", "", "url", "Docs", "https://example.com/docs", ""),
            "link-1",
        )
        self.assertEqual(
            command_bridge.upsert_node_link(
                "node-1",
                "",
                "node",
                "PDF2",
                "node-target",
                "Target Workspace - Media - ID 2",
                "workspace-target",
                "node-target",
            ),
            "link-1",
        )
        self.assertTrue(command_bridge.remove_node_link("node-1", "link-1"))
        self.assertTrue(command_bridge.move_node_link("node-1", "link-1", 1))
        self.assertTrue(command_bridge.open_node_link("node-1", "link-1"))
        self.assertEqual(
            command_bridge.upsert_node_comment(
                "node-1",
                "",
                "Check this node.",
                "",
                "",
                False,
                True,
                False,
            ),
            "comment-1",
        )
        self.assertTrue(command_bridge.remove_node_comment("node-1", "comment-1"))
        self.assertTrue(command_bridge.set_node_comment_resolved("node-1", "comment-1", True))
        self.assertTrue(command_bridge.set_node_comment_pinned("node-1", "comment-1", True))
        self.assertTrue(command_bridge.resolve_all_node_comments("node-1"))
        self.assertTrue(command_bridge.mark_node_comments_read("node-1"))
        self.assertTrue(command_bridge.are_port_kinds_compatible("data", "data"))
        self.assertTrue(command_bridge.are_data_types_compatible("text", "text"))
        self.assertTrue(command_bridge.move_nodes_by_delta(["node-1", "node-2"], 10.0, -5.0))
        command_bridge.move_node("node-1", 160.0, 220.0)
        command_bridge.resize_node("node-1", 320.0, 180.0)
        command_bridge.set_node_geometry("node-1", 150.0, 210.0, 340.0, 190.0)

        self.assertEqual(
            host.calls,
            [
                ("set_graphics_minimap_expanded", (False,)),
                ("set_graphics_canvas_background_variant", ("white",)),
                ("set_graphics_show_port_labels", (False,)),
                ("set_graphics_node_elapsed_time_unit", ("milliseconds",)),
                ("set_graphics_node_elapsed_time_visibility", ("during_run",)),
                ("set_graphics_node_comment_editor_default", ("inspector",)),
                ("set_folder_explorer_column_widths", ({"name": 240},)),
                ("set_graphics_selection_toolbar_mode", ("side_rail",)),
                ("set_graphics_selection_toolbar_minimal_menu_trigger", ("right_click",)),
                ("request_open_subnode_scope", ("subnode-1",)),
                ("browse_node_property_path", ("node-1", "source_path", "C:/temp/current.txt")),
                ("internalize_node_property_path", ("node-1", "source_path", "C:/temp/current.txt")),
                ("pick_node_property_color", ("node-1", "accent_color", "#336699")),
                (
                    "request_drop_node_from_library",
                    ("core.logger", 120.0, 240.0, "port", "node-1", "payload", "edge-1"),
                ),
                ("video_frame_capture_path", ("video-1", 4567)),
                (
                    "request_save_image_crop_replace",
                    ("image-1", {"x": 0.25, "y": 0.1, "width": 0.5, "height": 0.8}),
                ),
                (
                    "request_create_video_frame_image_node",
                    ("video-1", "C:/temp/captured-frame.png", 4567, 320.0, 180.0, 512.0, 384.0),
                ),
                (
                    "request_create_video_timestamp_annotation",
                    ("video-1", 4567, 340.0, 220.0),
                ),
                (
                    "request_trim_video_clip_replace",
                    ("video-1", 1000, 4000, {"clip_enabled": True, "clip_start_ms": 1000, "clip_end_ms": 4000}),
                ),
                (
                    "request_trim_video_clip_copy",
                    (
                        "video-1",
                        1000,
                        4000,
                        360.0,
                        240.0,
                        {"clip_enabled": True, "clip_start_ms": 1000, "clip_end_ms": 4000},
                    ),
                ),
                ("request_connect_ports", ("node-1", "value", "node-2", "payload", False)),
            ],
        )
        self.assertEqual(host_source.calls, [])
        self.assertEqual(
            scene.calls,
            [
                ("select_node", ("node-1", True)),
                ("set_node_property", ("node-1", "message", "hello")),
                (
                    "upsert_node_link",
                    ("node-1", "", "url", "Docs", "https://example.com/docs", ""),
                ),
                (
                    "upsert_node_link",
                    (
                        "node-1",
                        "",
                        "node",
                        "PDF2",
                        "node-target",
                        "Target Workspace - Media - ID 2",
                        "workspace-target",
                        "node-target",
                    ),
                ),
                ("remove_node_link", ("node-1", "link-1")),
                ("move_node_link", ("node-1", "link-1", 1)),
                ("open_node_link", ("node-1", "link-1")),
                ("upsert_node_comment", ("node-1", "", "Check this node.", "", "", False, True, False)),
                ("remove_node_comment", ("node-1", "comment-1")),
                ("set_node_comment_resolved", ("node-1", "comment-1", True)),
                ("set_node_comment_pinned", ("node-1", "comment-1", True)),
                ("resolve_all_node_comments", ("node-1",)),
                ("mark_node_comments_read", ("node-1",)),
                ("are_port_kinds_compatible", ("data", "data")),
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
        self.assertEqual(
            state_bridge.workspace_scene_bounds_payload,
            {"x": -1600.0, "y": -900.0, "width": 3200.0, "height": 1800.0},
        )

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
        self.assertEqual(
            command_bridge.describe_mail_preview("C:/temp/message.eml"),
            {
                "source": "C:/temp/message.eml",
                "state": "ready",
                "preview_url": "file:///C:/temp/mail-preview.html",
            },
        )
        self.assertEqual(
            command_bridge.open_local_file_source("C:/temp/message.eml", False),
            {"success": True, "path": "C:/temp/message.eml", "error": {}},
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
                ("describe_mail_preview", ("C:/temp/message.eml",)),
                ("open_local_file_source", ("C:/temp/message.eml", False)),
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

    def test_tooltip_category_bridge_workspace_presenter_projects_effective_visibility(self) -> None:
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
                "shell": {
                    "tooltip_categories": {
                        "general": False,
                        "advanced": True,
                        "warning": False,
                        "critical": False,
                        "unknown": True,
                    },
                }
            },
        )

        self.assertEqual(
            resolved["shell"]["tooltip_categories"],
            {
                "general": False,
                "tutorial": True,
                "advanced": True,
                "warning": False,
                "inactive": True,
            },
        )
        self.assertFalse(presenter.graphics_show_tooltips)
        self.assertTrue(presenter.graphics_tooltip_categories[TOOLTIP_CATEGORY_ADVANCED])
        self.assertTrue(presenter.tooltip_category_enabled(TOOLTIP_CATEGORY_ADVANCED))
        self.assertFalse(presenter.tooltip_category_enabled(TOOLTIP_CATEGORY_WARNING))
        self.assertTrue(presenter.tooltip_category_enabled("critical"))
        self.assertEqual(
            presenter.graphics_tooltip_category_visibility,
            {
                "general": False,
                "tutorial": True,
                "advanced": True,
                "warning": False,
                "inactive": True,
                "critical": True,
            },
        )
        self.assertEqual(seen["graphics_preferences_changed"], 1)

    def test_workspace_tooltip_projections_are_computed_once_per_preferences_revision(self) -> None:
        host = _bridge_support._ShellWorkspacePresenterHostStub()
        presenter = ShellWorkspacePresenter(host, ui_state=host.workspace_ui_state)
        original_policy = workspace_presenter_module.tooltip_category_effectively_visible

        with mock.patch.object(
            workspace_presenter_module,
            "tooltip_category_effectively_visible",
            wraps=original_policy,
        ) as project_visibility:
            categories = presenter.graphics_tooltip_categories
            categories["general"] = False
            self.assertTrue(presenter.graphics_tooltip_categories["general"])
            _ = presenter.graphics_tooltip_category_visibility
            _ = presenter.graphics_tooltip_category_visibility
            self.assertTrue(presenter.tooltip_category_enabled("general"))
            self.assertEqual(project_visibility.call_count, len(TOOLTIP_CATEGORY_NAMES))

            host.workspace_ui_state.graphics_tooltip_categories["general"] = False
            host.graphics_preferences_changed.emit()

            self.assertFalse(presenter.tooltip_category_enabled("general"))
            self.assertEqual(project_visibility.call_count, 2 * len(TOOLTIP_CATEGORY_NAMES))

    def test_canvas_tooltip_projections_are_computed_once_per_preferences_revision(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        canvas_source = _bridge_support._GraphCanvasTooltipCanvasSourceStub()
        state_bridge = GraphCanvasStateBridge(
            host,
            shell_window=host,
            canvas_source=canvas_source,
            graphics_source=host,
            scene_bridge=_bridge_support._GraphCanvasSceneBridgeStub(),
            view_bridge=_bridge_support._GraphCanvasViewBridgeStub(),
        )
        original_normalize = graphics_preferences_module.normalize_tooltip_category_preferences
        original_visibility = graphics_preferences_module._tooltip_category_visibility_payload

        with (
            mock.patch.object(
                graphics_preferences_module,
                "normalize_tooltip_category_preferences",
                wraps=original_normalize,
            ) as normalize_categories,
            mock.patch.object(
                graphics_preferences_module,
                "_tooltip_category_visibility_payload",
                wraps=original_visibility,
            ) as project_visibility,
        ):
            categories = state_bridge.graphics_tooltip_categories
            categories["general"] = False
            self.assertTrue(state_bridge.graphics_tooltip_categories["general"])
            _ = state_bridge.graphics_tooltip_category_visibility
            _ = state_bridge.graphics_tooltip_category_visibility
            self.assertTrue(state_bridge.tooltip_category_enabled("general"))
            self.assertEqual(normalize_categories.call_count, 1)
            self.assertEqual(project_visibility.call_count, 1)

            host.graphics_tooltip_categories["general"] = False
            canvas_source.graphics_preferences_changed.emit()

            self.assertFalse(state_bridge.tooltip_category_enabled("general"))
            self.assertEqual(normalize_categories.call_count, 2)
            self.assertEqual(project_visibility.call_count, 2)

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

    def test_comment_peek_opens_via_graph_action_and_uses_command_bridge_helpers(self) -> None:
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

        command_bridge = GraphCanvasCommandBridge(
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

        self.assertTrue(command_bridge.can_open_comment_peek("comment-1"))
        self.assertFalse(command_bridge.can_open_comment_peek("logger-1"))
        self.assertTrue(
            action_bridge.trigger_graph_action(
                GraphActionId.OPEN_COMMENT_PEEK.value,
                {"node_id": "comment-1"},
            )
        )
        self.assertEqual(command_bridge.active_comment_peek_node_id(), "comment-1")
        self.assertTrue(command_bridge.request_close_comment_peek())
        self.assertEqual(command_bridge.active_comment_peek_node_id(), "")
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
