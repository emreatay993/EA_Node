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


class _CreateWorkspaceManagerStub:
    def __init__(self) -> None:
        self.create_calls: list[str | None] = []

    def create_workspace(self, name: str | None = None) -> str:
        self.create_calls.append(name)
        return "ws-created"


class _RuntimeHistoryStub:
    def __init__(self) -> None:
        self.cleared: list[str] = []

    def clear_workspace(self, workspace_id: str) -> None:
        self.cleared.append(workspace_id)


class _CreateWorkspaceHostStub:
    def __init__(self) -> None:
        self.workspace_manager = _CreateWorkspaceManagerStub()
        self.runtime_history = _RuntimeHistoryStub()


class _PointStub:
    def __init__(self, x_value: float, y_value: float) -> None:
        self._x = x_value
        self._y = y_value

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y


class _ViewportRectStub:
    def center(self) -> object:
        return object()


class _ViewportStub:
    def rect(self) -> _ViewportRectStub:
        return _ViewportRectStub()


class _ViewStub:
    def viewport(self) -> _ViewportStub:
        return _ViewportStub()

    def mapToScene(self, _point: object) -> _PointStub:
        return _PointStub(125.0, 220.0)


class _LibraryInsertHostStub:
    def __init__(self) -> None:
        self.view = _ViewStub()


class WorkspaceLibraryControllerCapabilityCompositionTests(unittest.TestCase):
    def test_controller_initializes_business_capability_owners(self) -> None:
        controller = WorkspaceLibraryController(SimpleNamespace())  # type: ignore[arg-type]

        self.assertTrue(hasattr(controller, "_custom_workflow_capability"))
        self.assertTrue(hasattr(controller, "_navigation_capability"))
        self.assertTrue(hasattr(controller, "_edit_command_capability"))
        self.assertTrue(hasattr(controller, "_import_export_capability"))


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


class WorkspaceLibraryControllerDelegationTests(unittest.TestCase):
    def test_create_workspace_uses_controller_refresh_and_switch_hooks(self) -> None:
        from unittest.mock import patch

        host = _CreateWorkspaceHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        refresh_calls: list[str] = []
        switch_calls: list[str] = []
        controller.refresh_workspace_tabs = lambda: refresh_calls.append("refresh")  # type: ignore[method-assign]
        controller.switch_workspace = lambda workspace_id: switch_calls.append(workspace_id)  # type: ignore[method-assign]

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Refactor Scope", True)):
            controller.create_workspace()

        self.assertEqual(host.workspace_manager.create_calls, ["Refactor Scope"])
        self.assertEqual(host.runtime_history.cleared, ["ws-created"])
        self.assertEqual(refresh_calls, ["refresh"])
        self.assertEqual(switch_calls, ["ws-created"])

    def test_add_node_from_library_uses_controller_insert_hook_before_refresh(self) -> None:
        host = _LibraryInsertHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]
        insert_calls: list[tuple[str, float, float]] = []
        refresh_calls: list[str] = []

        def _insert(type_id: str, x_value: float, y_value: float) -> str:
            insert_calls.append((type_id, x_value, y_value))
            return "node-1"

        controller.insert_library_node = _insert  # type: ignore[method-assign]
        controller.refresh_workspace_tabs = lambda: refresh_calls.append("refresh")  # type: ignore[method-assign]

        controller.add_node_from_library("core.logger")

        self.assertEqual(insert_calls, [("core.logger", 125.0, 220.0)])
        self.assertEqual(refresh_calls, ["refresh"])


if __name__ == "__main__":
    unittest.main()
