from __future__ import annotations

import unittest
from types import SimpleNamespace

from ea_node_editor.ui.shell.controllers import WorkspaceLibraryController
from tests.workspace_library_controller_unit.core_ops import *  # noqa: F401,F403
from tests.workspace_library_controller_unit.custom_workflow_io import *  # noqa: F401,F403


class _SignalCounter:
    def __init__(self) -> None:
        self.calls = 0

    def emit(self) -> None:
        self.calls += 1


class _SearchScopeControllerStub:
    def __init__(self) -> None:
        self.restore_calls = 0
        self.discard_calls: list[tuple[str, str]] = []

    def restore_scope_camera(self) -> bool:
        self.restore_calls += 1
        return True

    def discard_scope_camera_for_view(self, workspace_id: str, view_id: str) -> None:
        self.discard_calls.append((workspace_id, view_id))


class _CloseViewWorkspace:
    def __init__(self) -> None:
        self.views = {"view-1": object(), "view-2": object()}
        self.active_view_id = "view-2"

    def ensure_default_view(self) -> None:
        return


class _CloseViewWorkspaceManager:
    def __init__(self, workspace: _CloseViewWorkspace) -> None:
        self._workspace = workspace
        self.closed: list[tuple[str, str]] = []

    def active_workspace_id(self) -> str:
        return "ws-1"

    def close_view(self, workspace_id: str, view_id: str) -> None:
        self.closed.append((workspace_id, view_id))
        self._workspace.views.pop(view_id, None)
        if self._workspace.active_view_id == view_id and self._workspace.views:
            self._workspace.active_view_id = next(iter(self._workspace.views))


class _CloseViewHostStub:
    def __init__(self) -> None:
        workspace = _CloseViewWorkspace()
        self.model = SimpleNamespace(project=SimpleNamespace(workspaces={"ws-1": workspace}))
        self.workspace_manager = _CloseViewWorkspaceManager(workspace)
        self.sync_scope_calls = 0
        self.scene = SimpleNamespace(sync_scope_with_active_view=self._sync_scope_with_active_view)
        self.search_scope_controller = _SearchScopeControllerStub()
        self.workspace_state_changed = _SignalCounter()

    def _sync_scope_with_active_view(self) -> None:
        self.sync_scope_calls += 1


class WorkspaceLibraryControllerCloseViewTests(unittest.TestCase):
    def test_close_view_uses_search_scope_controller_for_camera_state(self) -> None:
        host = _CloseViewHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        restore_calls: list[str] = []
        controller.restore_active_view_state = lambda: restore_calls.append("restore")  # type: ignore[method-assign]

        closed = controller.close_view("view-2")

        self.assertTrue(closed)
        self.assertEqual(host.workspace_manager.closed, [("ws-1", "view-2")])
        self.assertEqual(restore_calls, ["restore"])
        self.assertEqual(host.sync_scope_calls, 1)
        self.assertEqual(host.search_scope_controller.restore_calls, 1)
        self.assertEqual(host.search_scope_controller.discard_calls, [("ws-1", "view-2")])
        self.assertEqual(host.workspace_state_changed.calls, 1)


if __name__ == "__main__":
    unittest.main()
