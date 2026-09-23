# Purpose: Dialog-free workspace/view navigation cores used by the automation handlers.
# Map: feature_routes/automation_api_mcp
# Tests: tests/test_workspace_navigation_noninteractive.py
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.ui.shell.controllers.workspace_navigation_controller import (
    WorkspaceCloseOutcome,
    WorkspaceNavigationController,
)
from ea_node_editor.workspace.manager import WorkspaceManager

_LOGGER_NAME = "ea_node_editor.ui.shell.controllers.workspace_navigation_controller"


class _SignalCounter:
    def __init__(self) -> None:
        self.calls = 0

    def emit(self) -> None:
        self.calls += 1


class _RuntimeHistoryStub:
    def __init__(self) -> None:
        self.cleared: list[str] = []

    def clear_workspace(self, workspace_id: str) -> None:
        self.cleared.append(workspace_id)


class _ExecutionClientStub:
    def __init__(self) -> None:
        self.retired: list[str] = []
        self.error: Exception | None = None

    def retire_workspace(self, workspace_id: str) -> None:
        self.retired.append(workspace_id)
        if self.error is not None:
            raise self.error


class _ArtifactStoreStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def rename_workspace_artifact_folder(
        self,
        *,
        workspace_id: str,
        old_name: str,
        new_name: str,
    ) -> bool:
        self.calls.append((workspace_id, old_name, new_name))
        return True


class _ProjectSessionControllerStub:
    def __init__(self) -> None:
        self.store = _ArtifactStoreStub()
        self.replaced: list[object] = []

    def project_artifact_store(self) -> _ArtifactStoreStub:
        return self.store

    def replace_project_artifact_store(self, store: object) -> None:
        self.replaced.append(store)


class _SearchScopeControllerStub:
    def __init__(self) -> None:
        self.restore_calls = 0
        self.discard_calls: list[tuple[str, str]] = []

    def restore_scope_camera(self) -> bool:
        self.restore_calls += 1
        return True

    def discard_scope_camera_for_view(self, workspace_id: str, view_id: str) -> None:
        self.discard_calls.append((workspace_id, view_id))


class _WorkspaceTabsStub:
    def __init__(self, host: _HostStub) -> None:
        self._host = host

    def count(self) -> int:
        return len(self._host.workspace_manager.list_workspaces())

    def tabData(self, index: int) -> str:  # noqa: N802 - Qt-style tab API
        refs = self._host.workspace_manager.list_workspaces()
        if 0 <= index < len(refs):
            return refs[index].workspace_id
        return ""


class _HostStub:
    def __init__(self) -> None:
        self.model = GraphModel()
        self.workspace_manager = WorkspaceManager(self.model)
        self.runtime_history = _RuntimeHistoryStub()
        self.execution_client = _ExecutionClientStub()
        self.project_session_controller = _ProjectSessionControllerStub()
        self.search_scope_controller = _SearchScopeControllerStub()
        self.workspace_state_changed = _SignalCounter()
        self.workspace_tabs = _WorkspaceTabsStub(self)
        self.sync_scope_calls = 0
        self.scene = SimpleNamespace(sync_scope_with_active_view=self._sync_scope_with_active_view)
        self.shell_host_presenter = SimpleNamespace()

    def _sync_scope_with_active_view(self) -> None:
        self.sync_scope_calls += 1


def _make_controller(
    host: _HostStub,
) -> tuple[WorkspaceNavigationController, dict[str, list[str]]]:
    controller = WorkspaceNavigationController(host)  # type: ignore[arg-type]
    calls: dict[str, list[str]] = {"refresh": [], "switch": [], "save": [], "restore": []}
    controller.refresh_workspace_tabs = lambda: calls["refresh"].append("refresh")  # type: ignore[method-assign]
    controller.switch_workspace = lambda workspace_id: calls["switch"].append(workspace_id)  # type: ignore[method-assign]
    controller.save_active_view_state = lambda: calls["save"].append("save")  # type: ignore[method-assign]
    controller.restore_active_view_state = lambda: calls["restore"].append("restore")  # type: ignore[method-assign]
    return controller, calls


class CreateWorkspaceNamedTests(unittest.TestCase):
    def test_creates_active_workspace_and_clears_history(self) -> None:
        host = _HostStub()
        controller, calls = _make_controller(host)
        before = set(host.model.project.workspaces)

        workspace_id = controller.create_workspace_named("Automation")

        self.assertNotIn(workspace_id, before)
        self.assertEqual(host.model.project.workspaces[workspace_id].name, "Automation")
        self.assertEqual(host.workspace_manager.active_workspace_id(), workspace_id)
        self.assertEqual(host.runtime_history.cleared, [workspace_id])
        self.assertEqual(calls["refresh"], ["refresh"])
        self.assertEqual(calls["switch"], [workspace_id])

    def test_blank_names_fall_back_to_the_default_workspace_name(self) -> None:
        host = _HostStub()
        controller, _calls = _make_controller(host)

        first_id = controller.create_workspace_named(None)
        second_id = controller.create_workspace_named("")

        self.assertNotEqual(first_id, second_id)
        self.assertTrue(host.model.project.workspaces[first_id].name.strip())
        self.assertTrue(host.model.project.workspaces[second_id].name.strip())


class RenameWorkspaceToTests(unittest.TestCase):
    def test_renames_workspace_and_moves_its_artifact_folder(self) -> None:
        host = _HostStub()
        controller, calls = _make_controller(host)
        workspace_id = host.model.active_workspace.workspace_id
        old_name = host.model.project.workspaces[workspace_id].name

        self.assertTrue(controller.rename_workspace_to(workspace_id, "  Renamed  "))

        self.assertEqual(host.model.project.workspaces[workspace_id].name, "Renamed")
        store = host.project_session_controller.store
        self.assertEqual(store.calls, [(workspace_id, old_name, "Renamed")])
        self.assertEqual(host.project_session_controller.replaced, [store])
        self.assertEqual(calls["refresh"], ["refresh"])

    def test_rejects_unknown_empty_and_unchanged_names(self) -> None:
        host = _HostStub()
        controller, calls = _make_controller(host)
        workspace_id = host.model.active_workspace.workspace_id
        current_name = host.model.project.workspaces[workspace_id].name

        self.assertFalse(controller.rename_workspace_to("ws-missing", "Other"))
        self.assertFalse(controller.rename_workspace_to("", "Other"))
        self.assertFalse(controller.rename_workspace_to(workspace_id, "   "))
        self.assertFalse(controller.rename_workspace_to(workspace_id, current_name))

        self.assertEqual(host.model.project.workspaces[workspace_id].name, current_name)
        self.assertEqual(host.project_session_controller.store.calls, [])
        self.assertEqual(calls["refresh"], [])


class CloseWorkspaceNoninteractiveTests(unittest.TestCase):
    def test_dirty_workspace_is_kept_unless_discard_is_requested(self) -> None:
        host = _HostStub()
        controller, calls = _make_controller(host)
        keep_id = host.model.active_workspace.workspace_id
        target = host.model.create_workspace(name="Scratch")
        target.mark_dirty()

        kept = controller.close_workspace_noninteractive(target.workspace_id, discard_unsaved=False)

        self.assertFalse(kept.closed)
        self.assertEqual(kept.reason, "dirty")
        self.assertEqual(kept.retirement_error, "")
        self.assertEqual(kept.active_workspace_id, host.workspace_manager.active_workspace_id())
        self.assertIn(target.workspace_id, host.model.project.workspaces)
        self.assertEqual(host.execution_client.retired, [])
        self.assertEqual(host.runtime_history.cleared, [])
        self.assertEqual(calls["refresh"], [])

        closed = controller.close_workspace_noninteractive(target.workspace_id, discard_unsaved=True)

        self.assertEqual(
            closed,
            WorkspaceCloseOutcome(
                closed=True,
                reason="closed",
                retirement_error="",
                active_workspace_id=keep_id,
            ),
        )
        self.assertNotIn(target.workspace_id, host.model.project.workspaces)
        self.assertEqual(host.workspace_manager.active_workspace_id(), keep_id)
        self.assertEqual(host.execution_client.retired, [target.workspace_id])
        self.assertEqual(host.runtime_history.cleared, [target.workspace_id])
        self.assertEqual(calls["refresh"], ["refresh"])
        self.assertEqual(calls["switch"], [keep_id])

    def test_last_and_unknown_workspaces_are_reported_without_side_effects(self) -> None:
        host = _HostStub()
        controller, calls = _make_controller(host)
        only_id = host.model.active_workspace.workspace_id

        last = controller.close_workspace_noninteractive(only_id, discard_unsaved=True)
        unknown = controller.close_workspace_noninteractive("ws-missing", discard_unsaved=True)
        blank = controller.close_workspace_noninteractive("", discard_unsaved=True)

        self.assertEqual((last.closed, last.reason, last.active_workspace_id), (False, "last_workspace", only_id))
        self.assertEqual((unknown.closed, unknown.reason), (False, "unknown_workspace"))
        self.assertEqual((blank.closed, blank.reason), (False, "unknown_workspace"))
        self.assertIn(only_id, host.model.project.workspaces)
        self.assertEqual(host.execution_client.retired, [])
        self.assertEqual(host.runtime_history.cleared, [])
        self.assertEqual(calls["refresh"], [])
        self.assertEqual(calls["switch"], [])

    def test_retirement_failure_is_captured_and_logged_without_a_dialog(self) -> None:
        host = _HostStub()
        controller, calls = _make_controller(host)
        target = host.model.create_workspace(name="Scratch")
        host.execution_client.error = RuntimeError("cleanup failed")

        with (
            patch("PyQt6.QtWidgets.QMessageBox.warning") as warning,
            self.assertLogs(_LOGGER_NAME, level="ERROR") as logs,
        ):
            outcome = controller.close_workspace_noninteractive(target.workspace_id, discard_unsaved=True)

        warning.assert_not_called()
        self.assertTrue(outcome.closed)
        self.assertEqual(outcome.reason, "closed")
        self.assertEqual(outcome.retirement_error, "cleanup failed")
        self.assertTrue(any("retirement failed" in line for line in logs.output))
        self.assertNotIn(target.workspace_id, host.model.project.workspaces)
        self.assertEqual(host.runtime_history.cleared, [target.workspace_id])
        self.assertEqual(calls["refresh"], ["refresh"])
        self.assertEqual(calls["switch"], [host.workspace_manager.active_workspace_id()])


class ViewCoreTests(unittest.TestCase):
    def test_create_view_named_returns_the_new_active_view(self) -> None:
        host = _HostStub()
        controller, calls = _make_controller(host)
        workspace = host.model.active_workspace
        source_view_id = workspace.active_view_state().view_id

        named_id = controller.create_view_named("Review")
        default_id = controller.create_view_named(None)

        self.assertNotIn("", (named_id, default_id))
        self.assertNotEqual(named_id, source_view_id)
        self.assertEqual(workspace.views[named_id].name, "Review")
        self.assertTrue(workspace.views[default_id].name.strip())
        self.assertEqual(workspace.active_view_id, default_id)
        self.assertEqual(calls["save"], ["save", "save"])
        self.assertEqual(calls["restore"], ["restore", "restore"])
        self.assertEqual(host.workspace_state_changed.calls, 2)

    def test_rename_view_to_renames_only_known_views_with_new_names(self) -> None:
        host = _HostStub()
        controller, _calls = _make_controller(host)
        workspace = host.model.active_workspace
        view_id = workspace.active_view_state().view_id

        self.assertTrue(controller.rename_view_to(view_id, " Inspect "))

        self.assertEqual(workspace.views[view_id].name, "Inspect")
        self.assertEqual(host.workspace_state_changed.calls, 1)

        self.assertFalse(controller.rename_view_to("view-missing", "Other"))
        self.assertFalse(controller.rename_view_to("", "Other"))
        self.assertFalse(controller.rename_view_to(view_id, "   "))
        self.assertFalse(controller.rename_view_to(view_id, "Inspect"))

        self.assertEqual(workspace.views[view_id].name, "Inspect")
        self.assertEqual(host.workspace_state_changed.calls, 1)

    def test_close_view_without_errors_keeps_the_last_view_silently(self) -> None:
        host = _HostStub()
        controller, _calls = _make_controller(host)
        workspace = host.model.active_workspace
        only_view_id = workspace.active_view_state().view_id

        with patch("PyQt6.QtWidgets.QMessageBox.warning") as warning:
            self.assertFalse(controller.close_view(only_view_id, show_errors=False))
            warning.assert_not_called()

            self.assertFalse(controller.close_view(only_view_id))
            warning.assert_called_once()

        self.assertIn(only_view_id, workspace.views)
        self.assertEqual(host.workspace_state_changed.calls, 0)

    def test_close_view_closes_a_non_last_view_without_dialogs(self) -> None:
        host = _HostStub()
        controller, calls = _make_controller(host)
        workspace = host.model.active_workspace
        first_view_id = workspace.active_view_state().view_id
        second_view_id = controller.create_view_named("Second")
        host.workspace_state_changed.calls = 0

        with patch("PyQt6.QtWidgets.QMessageBox.warning") as warning:
            self.assertTrue(controller.close_view(second_view_id, show_errors=False))

        warning.assert_not_called()
        self.assertNotIn(second_view_id, workspace.views)
        self.assertEqual(workspace.active_view_id, first_view_id)
        self.assertEqual(calls["restore"], ["restore", "restore"])
        self.assertEqual(host.sync_scope_calls, 1)
        self.assertEqual(host.search_scope_controller.restore_calls, 1)
        self.assertEqual(
            host.search_scope_controller.discard_calls,
            [(workspace.workspace_id, second_view_id)],
        )
        self.assertEqual(host.workspace_state_changed.calls, 1)


class PromptingMethodsDelegateTests(unittest.TestCase):
    def test_prompting_methods_call_the_dialog_free_cores(self) -> None:
        host = _HostStub()
        controller, _calls = _make_controller(host)
        workspace_id = host.model.active_workspace.workspace_id
        view_id = host.model.active_workspace.active_view_state().view_id
        prompts: list[str] = []

        def prompt_text_value(*, title: str, label: str, text: str = "") -> tuple[str, bool]:
            prompts.append(title)
            return "Prompted", True

        host.shell_host_presenter = SimpleNamespace(prompt_text_value=prompt_text_value)

        with (
            patch.object(controller, "create_workspace_named", return_value="ws-new") as create_ws,
            patch.object(controller, "rename_workspace_to", return_value=True) as rename_ws,
            patch.object(controller, "rename_view_to", return_value=True) as rename_view,
            patch.object(controller._ops, "create_view_named", return_value="view-new") as create_view,
        ):
            controller.create_workspace()
            self.assertTrue(controller.rename_workspace_by_id(workspace_id))
            self.assertTrue(controller.rename_view(view_id))
            controller.create_view()

        create_ws.assert_called_once_with("Prompted")
        rename_ws.assert_called_once_with(workspace_id, "Prompted")
        rename_view.assert_called_once_with(view_id, "Prompted")
        create_view.assert_called_once_with("Prompted")
        self.assertEqual(prompts, ["New Workspace", "Rename Workspace", "Rename View", "New View"])

    def test_cancelled_prompts_never_reach_the_cores(self) -> None:
        host = _HostStub()
        controller, _calls = _make_controller(host)
        workspace_id = host.model.active_workspace.workspace_id
        view_id = host.model.active_workspace.active_view_state().view_id
        host.shell_host_presenter = SimpleNamespace(prompt_text_value=lambda **_kwargs: ("", False))

        with (
            patch.object(controller, "create_workspace_named") as create_ws,
            patch.object(controller, "rename_workspace_to") as rename_ws,
            patch.object(controller, "rename_view_to") as rename_view,
            patch.object(controller._ops, "create_view_named") as create_view,
        ):
            controller.create_workspace()
            self.assertFalse(controller.rename_workspace_by_id(workspace_id))
            self.assertFalse(controller.rename_view(view_id))
            controller.create_view()

        create_ws.assert_not_called()
        rename_ws.assert_not_called()
        rename_view.assert_not_called()
        create_view.assert_not_called()

    def test_workspace_tab_close_delegates_to_the_core_and_keeps_its_dialogs(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        host = _HostStub()
        controller, _calls = _make_controller(host)
        only_id = host.model.active_workspace.workspace_id

        with (
            patch("PyQt6.QtWidgets.QMessageBox.warning") as warning,
            patch.object(
                controller,
                "close_workspace_noninteractive",
                wraps=controller.close_workspace_noninteractive,
            ) as core,
        ):
            controller.on_workspace_tab_close(0)

        core.assert_called_once_with(only_id, discard_unsaved=True)
        warning.assert_called_once()
        self.assertIn("last workspace", str(warning.call_args.args[2]))
        self.assertIn(only_id, host.model.project.workspaces)

        host.model.project.workspaces[only_id].mark_dirty()
        with (
            patch(
                "PyQt6.QtWidgets.QMessageBox.question",
                return_value=QMessageBox.StandardButton.No,
            ) as question,
            patch.object(controller, "close_workspace_noninteractive") as declined_core,
        ):
            controller.on_workspace_tab_close(0)

        question.assert_called_once()
        declined_core.assert_not_called()
        self.assertIn(only_id, host.model.project.workspaces)


if __name__ == "__main__":
    unittest.main()
