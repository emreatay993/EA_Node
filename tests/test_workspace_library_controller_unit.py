from __future__ import annotations

import unittest
from types import SimpleNamespace

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.controllers import WorkspaceLibraryController
from ea_node_editor.ui.shell.controllers.workflow_library_controller import WorkflowLibraryController
from ea_node_editor.ui.shell.controllers.workspace_drop_connect_ops import WorkspaceDropConnectOps
from ea_node_editor.ui.shell.controllers.workspace_graph_edit_controller import WorkspaceGraphEditController
from ea_node_editor.ui.shell.controllers.workspace_navigation_controller import WorkspaceNavigationController
from ea_node_editor.ui.shell.controllers.workspace_package_io_controller import WorkspacePackageIOController
from ea_node_editor.ui.shell.controllers.workspace_view_nav_ops import WorkspaceViewNavOps
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


class _ViewMutationWorkspaceManagerStub:
    def __init__(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id

    def active_workspace_id(self) -> str:
        return self._workspace_id


class _ViewMutationControllerStub:
    def __init__(self) -> None:
        self.save_calls = 0
        self.restore_calls = 0

    def save_active_view_state(self) -> None:
        self.save_calls += 1

    def restore_active_view_state(self) -> None:
        self.restore_calls += 1


class _ViewMutationHostStub:
    def __init__(self) -> None:
        self.model = GraphModel()
        self.workspace_manager = _ViewMutationWorkspaceManagerStub(self.model.active_workspace.workspace_id)
        self.workspace_state_changed = _SignalCounter()


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


class _DropConnectControllerStub:
    def __init__(self, workspace) -> None:  # noqa: ANN001
        self._workspace = workspace
        self.prompt_calls = 0

    def resolve_custom_workflow_definition(self, workflow_id: str) -> dict[str, object] | None:  # noqa: ARG002
        return None

    def active_workspace(self):
        return self._workspace

    def prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, object]],
    ) -> dict[str, object] | None:
        self.prompt_calls += 1
        return None

    def refresh_workspace_tabs(self) -> None:
        return


class WorkspaceLibraryControllerCapabilityCompositionTests(unittest.TestCase):
    def test_controller_initializes_focused_controller_owners_with_explicit_capabilities(self) -> None:
        controller = WorkspaceLibraryController(SimpleNamespace())  # type: ignore[arg-type]

        self.assertIsInstance(controller.workflow_library_controller, WorkflowLibraryController)
        self.assertIsInstance(controller.workspace_navigation_controller, WorkspaceNavigationController)
        self.assertIsInstance(controller.workspace_graph_edit_controller, WorkspaceGraphEditController)
        self.assertIsInstance(controller.workspace_package_io_controller, WorkspacePackageIOController)
        self.assertIsNot(controller._custom_workflow_capability, controller.workflow_library_controller)
        self.assertIsNot(controller._navigation_capability, controller.workspace_navigation_controller)
        self.assertIsNot(controller._edit_command_capability, controller.workspace_graph_edit_controller)
        self.assertIsNot(controller._import_export_capability, controller.workspace_package_io_controller)

    def test_internal_capabilities_delegate_only_to_focused_subcontrollers(self) -> None:
        controller = WorkspaceLibraryController(SimpleNamespace())  # type: ignore[arg-type]
        refresh_calls: list[str] = []
        controller.workspace_graph_edit_controller.selected_node_context = lambda: "selected"  # type: ignore[method-assign]
        controller.refresh_workspace_tabs = lambda: refresh_calls.append("tabs")  # type: ignore[method-assign]
        controller.workflow_library_controller.resolve_custom_workflow_definition = lambda workflow_id: {  # type: ignore[method-assign]
            "workflow_id": workflow_id
        }
        controller.workspace_package_io_controller.prompt_custom_workflow_export_definition = (  # type: ignore[method-assign]
            lambda definitions: definitions[0] if definitions else None
        )

        self.assertEqual(controller._custom_workflow_capability.selected_node_context(), "selected")
        controller._navigation_capability.refresh_workspace_tabs()
        self.assertEqual(refresh_calls, ["tabs"])
        self.assertEqual(
            controller._edit_command_capability.resolve_custom_workflow_definition("wf-1"),
            {"workflow_id": "wf-1"},
        )
        self.assertEqual(
            controller._import_export_capability._prompt_custom_workflow_export_definition(
                [{"workflow_id": "wf-2"}]
            ),
            {"workflow_id": "wf-2"},
        )


class WorkspaceLibraryControllerSurfaceDelegationTests(unittest.TestCase):
    def test_facade_delegates_custom_workflow_surface_to_focused_controller(self) -> None:
        controller = WorkspaceLibraryController(SimpleNamespace())  # type: ignore[arg-type]
        controller.workflow_library_controller.custom_workflow_library_items = lambda: [  # type: ignore[method-assign]
            {"workflow_id": "wf-1"}
        ]

        self.assertEqual(controller.custom_workflow_library_items(), [{"workflow_id": "wf-1"}])

    def test_facade_delegates_navigation_surface_to_focused_controller(self) -> None:
        controller = WorkspaceLibraryController(SimpleNamespace())  # type: ignore[arg-type]
        controller.workspace_navigation_controller.search_graph_nodes = lambda query, limit: [  # type: ignore[method-assign]
            {"query": query, "limit": limit}
        ]

        self.assertEqual(
            controller.search_graph_nodes("needle", 7),
            [{"query": "needle", "limit": 7}],
        )

    def test_facade_delegates_graph_edit_surface_to_focused_controller(self) -> None:
        controller = WorkspaceLibraryController(SimpleNamespace())  # type: ignore[arg-type]
        controller.workspace_graph_edit_controller.request_remove_edge = lambda edge_id: edge_id  # type: ignore[method-assign]

        self.assertEqual(controller.request_remove_edge("edge-1"), "edge-1")

    def test_facade_delegates_package_io_surface_to_focused_controller(self) -> None:
        controller = WorkspaceLibraryController(SimpleNamespace())  # type: ignore[arg-type]
        prompted: list[list[dict[str, object]]] = []

        def _prompt(definitions: list[dict[str, object]]) -> dict[str, object] | None:
            prompted.append(definitions)
            return definitions[0] if definitions else None

        controller.workspace_package_io_controller.prompt_custom_workflow_export_definition = _prompt  # type: ignore[method-assign]
        definition = {"workflow_id": "wf-1"}

        self.assertEqual(
            controller._prompt_custom_workflow_export_definition([definition]),
            definition,
        )
        self.assertEqual(prompted, [[definition]])


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


class WorkspaceViewNavOpsMutationServiceTests(unittest.TestCase):
    def test_create_view_uses_model_mutation_service_without_workspace_manager_view_helpers(self) -> None:
        from unittest.mock import patch

        host = _ViewMutationHostStub()
        controller = _ViewMutationControllerStub()
        ops = WorkspaceViewNavOps(host, controller)  # type: ignore[arg-type]

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Review", True)):
            ops.create_view()

        workspace = host.model.active_workspace
        self.assertEqual(controller.save_calls, 1)
        self.assertEqual(controller.restore_calls, 1)
        self.assertEqual(host.workspace_state_changed.calls, 1)
        self.assertEqual(len(workspace.views), 2)
        self.assertEqual(workspace.views[workspace.active_view_id].name, "Review")

    def test_switch_view_uses_model_mutation_service_without_workspace_manager_view_helpers(self) -> None:
        host = _ViewMutationHostStub()
        workspace = host.model.active_workspace
        alternate_view = host.model.mutation_service(workspace.workspace_id).create_view(name="Alt")
        controller = _ViewMutationControllerStub()
        ops = WorkspaceViewNavOps(host, controller)  # type: ignore[arg-type]

        ops.switch_view(alternate_view.view_id)

        self.assertEqual(controller.save_calls, 1)
        self.assertEqual(controller.restore_calls, 1)
        self.assertEqual(host.workspace_state_changed.calls, 1)
        self.assertEqual(workspace.active_view_id, alternate_view.view_id)


class WorkspaceDropConnectOpsValidationTests(unittest.TestCase):
    def test_auto_connect_dropped_node_to_port_skips_occupied_single_input(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        occupied_source = model.add_node(workspace.workspace_id, "core.start", "Start A", 0.0, 0.0)
        new_node = model.add_node(workspace.workspace_id, "core.start", "Start B", 0.0, 120.0)
        target = model.add_node(workspace.workspace_id, "core.end", "End", 320.0, 40.0)
        model.add_edge(workspace.workspace_id, occupied_source.node_id, "exec_out", target.node_id, "exec_in")

        host = SimpleNamespace(registry=registry, scene=SimpleNamespace())
        controller = _DropConnectControllerStub(workspace)
        ops = WorkspaceDropConnectOps(host, controller)  # type: ignore[arg-type]

        connected = ops.auto_connect_dropped_node_to_port(new_node.node_id, target.node_id, "exec_in")

        self.assertFalse(connected)
        self.assertEqual(controller.prompt_calls, 0)


if __name__ == "__main__":
    unittest.main()
