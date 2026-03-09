from __future__ import annotations

from contextlib import nullcontext
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ea_node_editor.custom_workflows import export_custom_workflow_file, import_custom_workflow_file
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.graph_interactions import GraphActionResult
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui.shell.controllers.workspace_library_controller import WorkspaceLibraryController


class _GraphInteractionsStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str]] = []

    def connect_ports(self, node_a_id: str, port_a: str, node_b_id: str, port_b: str) -> GraphActionResult:
        self.calls.append((node_a_id, port_a, node_b_id, port_b))
        return GraphActionResult(True, "")


class _WorkspaceHostStub:
    def __init__(self) -> None:
        self._graph_interactions = _GraphInteractionsStub()


class _WorkspaceManagerStub:
    def __init__(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id

    def active_workspace_id(self) -> str:
        return self._workspace_id


class _RuntimeHistoryStub:
    def __init__(self) -> None:
        self.undo_return: object | None = object()
        self.redo_return: object | None = object()
        self.undo_calls: list[str] = []
        self.redo_calls: list[str] = []

    def undo_workspace(self, workspace_id: str, workspace: object) -> object | None:  # noqa: ARG002
        self.undo_calls.append(workspace_id)
        return self.undo_return

    def redo_workspace(self, workspace_id: str, workspace: object) -> object | None:  # noqa: ARG002
        self.redo_calls.append(workspace_id)
        return self.redo_return

    def grouped_action(self, workspace_id: str, action_type: str, workspace: object):  # noqa: ARG002
        return nullcontext()


class _SceneStub:
    def __init__(self) -> None:
        self.refreshed_workspaces: list[str] = []

    def refresh_workspace_from_model(self, workspace_id: str) -> None:
        self.refreshed_workspaces.append(workspace_id)


class _UndoRedoHostStub:
    def __init__(self) -> None:
        self._graph_interactions = _GraphInteractionsStub()
        self.model = GraphModel()
        self.runtime_history = _RuntimeHistoryStub()
        workspace_id = self.model.active_workspace.workspace_id
        self.workspace_manager = _WorkspaceManagerStub(workspace_id)
        self.scene = _SceneStub()


class _PointStub:
    def __init__(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y


class _RectStub:
    def center(self) -> _PointStub:
        return _PointStub(5.0, 9.0)


class _ViewportStub:
    def rect(self) -> _RectStub:
        return _RectStub()


class _ViewStub:
    def viewport(self) -> _ViewportStub:
        return _ViewportStub()

    def mapToScene(self, point: object) -> _PointStub:  # noqa: ARG002
        return _PointStub(120.0, 340.0)


class _ClipboardSceneStub:
    def __init__(self) -> None:
        self.fragment_payload: dict[str, object] | None = None
        self.paste_calls: list[tuple[dict[str, object], float, float]] = []

    def serialize_selected_subgraph_fragment(self) -> dict[str, object] | None:
        return self.fragment_payload

    def paste_subgraph_fragment(self, payload: dict[str, object], center_x: float, center_y: float) -> bool:
        self.paste_calls.append((payload, center_x, center_y))
        return True


class _SignalStub:
    def __init__(self) -> None:
        self.calls = 0

    def emit(self) -> None:
        self.calls += 1


class _ClipboardHostStub:
    def __init__(self) -> None:
        self._graph_interactions = _GraphInteractionsStub()
        self.scene = _ClipboardSceneStub()
        self.view = _ViewStub()
        self.selected_node_changed = _SignalStub()


class _ScopeFocusSceneStub:
    def __init__(self) -> None:
        self.open_scope_calls: list[str] = []
        self.focus_calls: list[str] = []
        self.focus_results: dict[str, _PointStub | None] = {}

    def open_scope_for_node(self, node_id: str) -> bool:
        self.open_scope_calls.append(node_id)
        return True

    def focus_node(self, node_id: str):
        self.focus_calls.append(node_id)
        return self.focus_results.get(node_id, _PointStub(1.0, 2.0))


class _ScopeFocusHostStub:
    def __init__(self) -> None:
        self._graph_interactions = _GraphInteractionsStub()
        self.model = GraphModel()
        workspace_id = self.model.active_workspace.workspace_id
        self.workspace_manager = _WorkspaceManagerStub(workspace_id)
        self.scene = _ScopeFocusSceneStub()


class _PinPropertySceneStub:
    def __init__(self) -> None:
        self.property_calls: list[tuple[str, str, object]] = []
        self.refreshed_workspaces: list[str] = []

    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        self.property_calls.append((node_id, key, value))

    def refresh_workspace_from_model(self, workspace_id: str) -> None:
        self.refreshed_workspaces.append(workspace_id)


class _ScriptEditorStub:
    def __init__(self) -> None:
        self.current_node_id = ""

    def set_node(self, _node: object) -> None:
        return


class _PinPropertyHostStub:
    def __init__(self) -> None:
        self._graph_interactions = _GraphInteractionsStub()
        self.model = GraphModel()
        workspace_id = self.model.active_workspace.workspace_id
        self.workspace_manager = _WorkspaceManagerStub(workspace_id)
        self.scene = _PinPropertySceneStub()
        self.script_editor = _ScriptEditorStub()
        self.selected_node_changed = _SignalStub()


class _PublishSceneStub:
    def __init__(self) -> None:
        self._selected_node_id = ""
        self.active_scope_path: list[str] = []

    def selected_node_id(self) -> str:
        return self._selected_node_id


class _PublishHostStub:
    def __init__(self) -> None:
        self._graph_interactions = _GraphInteractionsStub()
        self.model = GraphModel()
        self.registry = build_default_registry()
        workspace_id = self.model.active_workspace.workspace_id
        self.workspace_manager = _WorkspaceManagerStub(workspace_id)
        self.active_workspace_id = workspace_id
        self.scene = _PublishSceneStub()
        self.node_library_changed = _SignalStub()
        self.project_meta_changed = _SignalStub()


class WorkspaceLibraryControllerUnitTests(unittest.TestCase):
    @staticmethod
    def _valid_fragment_payload() -> dict[str, object]:
        return {
            "kind": "ea-node-editor/graph-fragment",
            "version": 1,
            "nodes": [
                {
                    "ref_id": "node_a",
                    "type_id": "core.start",
                    "title": "Start",
                    "x": 10.0,
                    "y": 20.0,
                    "collapsed": False,
                    "properties": {},
                    "exposed_ports": {"exec_out": True},
                    "parent_node_id": None,
                }
            ],
            "edges": [],
        }

    def test_request_connect_ports_delegates_and_wraps_result(self) -> None:
        host = _WorkspaceHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]

        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]

        result = controller.request_connect_ports("node_a", "out", "node_b", "in")

        self.assertTrue(result.ok)
        self.assertTrue(result.payload)
        self.assertTrue(refreshed["value"])
        self.assertEqual(host._graph_interactions.calls, [("node_a", "out", "node_b", "in")])

    def test_undo_delegates_to_runtime_history_and_refreshes_scene(self) -> None:
        host = _UndoRedoHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]

        undone = controller.undo()

        workspace_id = host.workspace_manager.active_workspace_id()
        self.assertTrue(undone)
        self.assertEqual(host.runtime_history.undo_calls, [workspace_id])
        self.assertEqual(host.scene.refreshed_workspaces, [workspace_id])
        self.assertTrue(refreshed["value"])

    def test_redo_returns_false_when_runtime_history_has_no_entry(self) -> None:
        host = _UndoRedoHostStub()
        host.runtime_history.redo_return = None
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]

        redone = controller.redo()

        workspace_id = host.workspace_manager.active_workspace_id()
        self.assertFalse(redone)
        self.assertEqual(host.runtime_history.redo_calls, [workspace_id])
        self.assertEqual(host.scene.refreshed_workspaces, [])
        self.assertFalse(refreshed["value"])

    def test_cut_selected_nodes_routes_through_delete_selected_path(self) -> None:
        host = _ClipboardHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        delete_calls: list[list[object]] = []

        controller.copy_selected_nodes_to_clipboard = lambda: True  # type: ignore[method-assign]

        def _delete_selected(edge_ids: list[object]) -> ControllerResult[bool]:
            delete_calls.append(list(edge_ids))
            return ControllerResult(True, payload=True)

        controller.request_delete_selected_graph_items = _delete_selected  # type: ignore[method-assign]

        cut = controller.cut_selected_nodes_to_clipboard()

        self.assertTrue(cut)
        self.assertEqual(delete_calls, [[]])

    def test_paste_nodes_from_clipboard_uses_viewport_center_and_refreshes(self) -> None:
        host = _ClipboardHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]
        payload = self._valid_fragment_payload()
        controller._read_graph_fragment_from_clipboard = lambda: payload  # type: ignore[method-assign]

        pasted = controller.paste_nodes_from_clipboard()

        self.assertTrue(pasted)
        self.assertEqual(host.scene.paste_calls, [(payload, 120.0, 340.0)])
        self.assertEqual(host.selected_node_changed.calls, 1)
        self.assertTrue(refreshed["value"])

    def test_paste_nodes_from_clipboard_offsets_consecutive_pastes(self) -> None:
        host = _ClipboardHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        payload = self._valid_fragment_payload()
        controller._read_graph_fragment_from_clipboard = lambda: payload  # type: ignore[method-assign]
        controller.refresh_workspace_tabs = lambda: None  # type: ignore[method-assign]

        first = controller.paste_nodes_from_clipboard()
        second = controller.paste_nodes_from_clipboard()

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertEqual(host.scene.paste_calls[0], (payload, 120.0, 340.0))
        self.assertEqual(host.scene.paste_calls[1], (payload, 160.0, 380.0))

    def test_paste_nodes_from_clipboard_is_noop_when_clipboard_is_missing(self) -> None:
        host = _ClipboardHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]
        controller._read_graph_fragment_from_clipboard = lambda: None  # type: ignore[method-assign]

        pasted = controller.paste_nodes_from_clipboard()

        self.assertFalse(pasted)
        self.assertEqual(host.scene.paste_calls, [])
        self.assertEqual(host.selected_node_changed.calls, 0)
        self.assertFalse(refreshed["value"])

    def test_jump_to_graph_node_opens_scope_before_focus(self) -> None:
        host = _ScopeFocusHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        workspace_id = host.workspace_manager.active_workspace_id()
        node_id = host.model.add_node(
            workspace_id,
            type_id="core.logger",
            title="Target",
            x=20.0,
            y=10.0,
        ).node_id

        controller.reveal_parent_chain = lambda _workspace_id, _node_id: []  # type: ignore[method-assign]
        controller.center_on_selection = lambda: True  # type: ignore[method-assign]

        jumped = controller.jump_to_graph_node(workspace_id, node_id)

        self.assertTrue(jumped)
        self.assertEqual(host.scene.open_scope_calls, [node_id])
        self.assertEqual(host.scene.focus_calls, [node_id])

    def test_focus_failed_node_opens_scope_for_each_focus_candidate(self) -> None:
        host = _ScopeFocusHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        workspace_id = host.workspace_manager.active_workspace_id()

        controller.reveal_parent_chain = lambda _workspace_id, _node_id: ["ancestor_a"]  # type: ignore[method-assign]
        focused: list[str] = []
        controller.center_on_node = lambda node_id: focused.append(node_id) or True  # type: ignore[method-assign]
        host.scene.focus_results = {
            "node_target": _PointStub(5.0, 7.0),
            "ancestor_a": _PointStub(9.0, 3.0),
        }

        controller.focus_failed_node(workspace_id, "node_target", "")

        self.assertEqual(host.scene.open_scope_calls, ["node_target"])
        self.assertEqual(host.scene.focus_calls, ["node_target"])
        self.assertEqual(focused, ["node_target"])

    def test_on_node_property_changed_refreshes_shell_payload_for_direct_child_pin(self) -> None:
        host = _PinPropertyHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]
        workspace_id = host.workspace_manager.active_workspace_id()
        shell_node = host.model.add_node(
            workspace_id,
            type_id="core.subnode",
            title="Subnode",
            x=40.0,
            y=50.0,
        )
        pin_node = host.model.add_node(
            workspace_id,
            type_id="core.subnode_input",
            title="Subnode Input",
            x=80.0,
            y=120.0,
        )
        pin_node.parent_node_id = shell_node.node_id

        controller.on_node_property_changed(pin_node.node_id, "label", "Data In")

        self.assertEqual(host.scene.property_calls, [(pin_node.node_id, "label", "Data In")])
        self.assertEqual(host.scene.refreshed_workspaces, [workspace_id])
        self.assertEqual(host.selected_node_changed.calls, 1)
        self.assertTrue(refreshed["value"])

    def test_on_node_property_changed_skips_shell_refresh_for_non_pin_nodes(self) -> None:
        host = _PinPropertyHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        controller.refresh_workspace_tabs = lambda: None  # type: ignore[method-assign]
        workspace_id = host.workspace_manager.active_workspace_id()
        logger_node = host.model.add_node(
            workspace_id,
            type_id="core.logger",
            title="Logger",
            x=20.0,
            y=20.0,
        )

        controller.on_node_property_changed(logger_node.node_id, "message", "hello")

        self.assertEqual(host.scene.property_calls, [(logger_node.node_id, "message", "hello")])
        self.assertEqual(host.scene.refreshed_workspaces, [])

    def test_publish_custom_workflow_from_selected_subnode_persists_snapshot(self) -> None:
        host = _PublishHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        workspace_id = host.workspace_manager.active_workspace_id()

        shell = host.model.add_node(
            workspace_id,
            type_id="core.subnode",
            title="Reusable Shell",
            x=120.0,
            y=80.0,
            properties=host.registry.default_properties("core.subnode"),
            exposed_ports={},
        )
        pin = host.model.add_node(
            workspace_id,
            type_id="core.subnode_output",
            title="Subnode Output",
            x=260.0,
            y=120.0,
            properties=host.registry.default_properties("core.subnode_output"),
            exposed_ports={"pin": True},
        )
        pin.parent_node_id = shell.node_id
        pin.properties["label"] = "Exec Out"
        pin.properties["kind"] = "exec"
        pin.properties["data_type"] = "any"
        shell.exposed_ports[pin.node_id] = True
        host.scene._selected_node_id = shell.node_id

        published = controller.publish_custom_workflow_from_selected_subnode()

        self.assertTrue(published.ok)
        self.assertTrue(published.payload)
        definitions = host.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(definitions), 1)
        definition = definitions[0]
        self.assertEqual(definition["name"], "Reusable Shell")
        self.assertEqual(definition["revision"], 1)
        self.assertEqual(definition["ports"][0]["direction"], "out")
        self.assertEqual(definition["ports"][0]["kind"], "exec")
        self.assertEqual(definition["fragment"]["kind"], "ea-node-editor/graph-fragment")
        self.assertEqual(host.project_meta_changed.calls, 1)
        self.assertEqual(host.node_library_changed.calls, 1)
        library_items = controller.custom_workflow_library_items()
        self.assertEqual(len(library_items), 1)
        self.assertTrue(str(library_items[0]["type_id"]).startswith("custom_workflow:"))

    def test_publish_custom_workflow_from_current_scope_updates_revision(self) -> None:
        host = _PublishHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        workspace_id = host.workspace_manager.active_workspace_id()

        shell = host.model.add_node(
            workspace_id,
            type_id="core.subnode",
            title="Scoped Shell",
            x=80.0,
            y=40.0,
            properties=host.registry.default_properties("core.subnode"),
            exposed_ports={},
        )
        pin = host.model.add_node(
            workspace_id,
            type_id="core.subnode_input",
            title="Subnode Input",
            x=30.0,
            y=100.0,
            properties=host.registry.default_properties("core.subnode_input"),
            exposed_ports={"pin": True},
        )
        pin.parent_node_id = shell.node_id
        pin.properties["label"] = "Payload A"
        shell.exposed_ports[pin.node_id] = True
        host.scene.active_scope_path = [shell.node_id]

        first_publish = controller.publish_custom_workflow_from_current_scope()
        self.assertTrue(first_publish.ok)

        pin.properties["label"] = "Payload B"
        second_publish = controller.publish_custom_workflow_from_current_scope()
        self.assertTrue(second_publish.ok)

        definitions = host.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(definitions), 1)
        definition = definitions[0]
        self.assertEqual(definition["name"], "Scoped Shell")
        self.assertEqual(definition["revision"], 2)
        self.assertEqual(definition["ports"][0]["label"], "Payload B")

    def test_export_custom_workflow_writes_eawf_payload(self) -> None:
        host = _PublishHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        definitions = [
            {
                "workflow_id": "wf_export",
                "name": "Workflow Export",
                "description": "Export test",
                "revision": 3,
                "ports": [
                    {
                        "key": "exec_out",
                        "label": "Exec Out",
                        "direction": "out",
                        "kind": "exec",
                        "data_type": "any",
                    }
                ],
                "fragment": {
                    "kind": "ea-node-editor/graph-fragment",
                    "version": 1,
                    "nodes": [],
                    "edges": [],
                },
            }
        ]
        host.model.project.metadata["custom_workflows"] = definitions
        controller._prompt_custom_workflow_export_definition = lambda items: items[0]  # type: ignore[method-assign]

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "workflow_export"
            with (
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(target_path), "Custom Workflow (*.eawf)"),
                ),
                patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
                patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
            ):
                controller.export_custom_workflow()

            saved_path = target_path.with_suffix(".eawf")
            self.assertTrue(saved_path.exists())
            imported = import_custom_workflow_file(saved_path)

        self.assertEqual(imported["workflow_id"], "wf_export")
        self.assertEqual(imported["name"], "Workflow Export")
        self.assertEqual(imported["revision"], 3)
        self.assertEqual(imported["ports"][0]["label"], "Exec Out")
        self.assertEqual(info_mock.call_count, 1)
        self.assertEqual(warning_mock.call_count, 0)

    def test_custom_workflow_export_label_hides_internal_workflow_id(self) -> None:
        label = WorkspaceLibraryController._custom_workflow_export_label(
            {
                "workflow_id": "wf_export",
                "name": "Workflow Export",
                "revision": 3,
            }
        )
        self.assertEqual(label, "Workflow Export (rev 3)")
        self.assertNotIn("wf_export", label)

    def test_import_custom_workflow_replaces_existing_definition_and_emits_signals(self) -> None:
        host = _PublishHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        host.model.project.metadata["custom_workflows"] = [
            {
                "workflow_id": "wf_sync",
                "name": "Old Name",
                "description": "old",
                "revision": 1,
                "ports": [
                    {
                        "key": "exec_out",
                        "label": "Old",
                        "direction": "out",
                        "kind": "exec",
                        "data_type": "any",
                    }
                ],
                "fragment": {"kind": "ea-node-editor/graph-fragment", "version": 1, "nodes": [], "edges": []},
            }
        ]
        imported_definition = {
            "workflow_id": "wf_sync",
            "name": "Imported Name",
            "description": "new",
            "revision": 7,
            "ports": [
                {
                    "key": "payload",
                    "label": "Payload",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "json",
                }
            ],
            "fragment": {"kind": "ea-node-editor/graph-fragment", "version": 1, "nodes": [], "edges": []},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            import_path = export_custom_workflow_file(imported_definition, Path(temp_dir) / "import_target")
            with (
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                    return_value=(str(import_path), "Custom Workflow (*.eawf)"),
                ),
                patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
                patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
            ):
                controller.import_custom_workflow()

        definitions = host.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0], imported_definition)
        self.assertEqual(host.project_meta_changed.calls, 1)
        self.assertEqual(host.node_library_changed.calls, 1)
        self.assertEqual(info_mock.call_count, 1)
        self.assertEqual(warning_mock.call_count, 0)


if __name__ == "__main__":
    unittest.main()
