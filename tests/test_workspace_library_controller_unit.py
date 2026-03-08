from __future__ import annotations

from contextlib import nullcontext
import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.ui.graph_interactions import GraphActionResult
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


class WorkspaceLibraryControllerUnitTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
