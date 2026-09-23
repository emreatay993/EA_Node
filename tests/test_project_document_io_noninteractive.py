# Purpose: Prove the dialog-free document-IO seams (save_project_to_path, open_project_path_noninteractive,
#          new_project_noninteractive) never prompt, including when staged files must be published.
# Map: feature_routes/automation_api_mcp
# Tests: tests/test_project_document_io_noninteractive.py
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ea_node_editor.execution.runtime import CorexRuntime
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.artifact_store import ProjectArtifactLayout, ProjectArtifactStore
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.persistence.solution_repository import SolutionRepositoryFactory
from ea_node_editor.settings import PROJECT_NODE_INPUTS_DIRNAME
from ea_node_editor.ui.shell.controllers.project_session_controller import (
    ProjectSessionController,
)
from ea_node_editor.ui.shell.controllers.project_session_services_support.document_io_service import (
    ProjectOpenResult,
    ProjectSaveResult,
)
from ea_node_editor.ui.shell.controllers.run_projection_controller import (
    RunProjectionController,
)
from ea_node_editor.ui.shell.state import ShellProjectSessionState, ShellRunState
from ea_node_editor.workspace.manager import WorkspaceManager


class _SignalStub:
    def __init__(self) -> None:
        self.emit_calls = 0

    def emit(self, *args) -> None:  # noqa: ANN002
        self.emit_calls += 1


class _ScriptEditorStub:
    def __init__(self) -> None:
        self.visible = False
        self.floating = False
        self.panel_width = 0.0

    def set_visible(self, value: bool) -> None:
        self.visible = bool(value)

    def set_floating(self, value: bool) -> None:
        self.floating = bool(value)

    def set_width(self, value: float) -> None:
        self.panel_width = float(value)

    def set_node(self, node) -> None:  # noqa: ANN001
        pass

    def focus_editor(self) -> None:
        pass


class _ActionToggleStub:
    def setChecked(self, value: bool) -> None:  # noqa: N802
        pass


class _SceneStub:
    @staticmethod
    def selected_node_id() -> str:
        return ""


class _WorkspaceNavigationControllerStub:
    def __init__(self) -> None:
        self.save_active_view_state_calls = 0
        self.refresh_workspace_tabs_calls = 0
        self.switch_workspace_calls: list[str] = []

    def save_active_view_state(self) -> None:
        self.save_active_view_state_calls += 1

    def refresh_workspace_tabs(self) -> None:
        self.refresh_workspace_tabs_calls += 1

    def switch_workspace(self, workspace_id: str) -> None:
        self.switch_workspace_calls.append(str(workspace_id))


class _RuntimeHistoryStub:
    def clear_all(self) -> None:
        pass


class _ViewerHostServiceStub:
    def reset(self, *, reason: str = "") -> None:
        pass


class _ViewerSessionBridgeStub:
    def project_loaded(
        self, project, registry, *, reseed_on_next_reset: bool = False
    ) -> None:  # noqa: ANN001
        pass


class _SessionStoreStub:
    def __init__(self, root: Path) -> None:
        self._root = root
        self.discard_calls = 0
        self.persist_calls: list[dict] = []

    def staging_workspace_root(self) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root

    def discard_autosave_snapshot(self) -> None:
        self.discard_calls += 1

    def autosave_if_changed(self, **kwargs) -> str:  # noqa: ANN003
        return str(kwargs.get("last_fingerprint") or "stub-autosave-fingerprint")

    def persist_session(self, **kwargs) -> None:  # noqa: ANN003
        self.persist_calls.append(copy.deepcopy(kwargs))


class _ProjectHostStub:
    """Minimal document-IO host: real serializer + runtime, stubbed shell surfaces."""

    def __init__(self, root: Path, *, project_id: str = "proj_noninteractive") -> None:
        self.project_session_state = ShellProjectSessionState()
        self.run_state = ShellRunState()
        self.registry = build_default_registry()
        self.serializer = JsonProjectSerializer(self.registry)
        self.model = GraphModel()
        self.model.project.project_id = project_id
        self.model.project.name = "Noninteractive"
        self.workspace_manager = WorkspaceManager(self.model)
        self.project_path = ""
        self.session_store = _SessionStoreStub(root / "session")
        self.execution_client = CorexRuntime(
            registry=self.registry,
            solution_repository_factory=SolutionRepositoryFactory(),
        )
        self.execution_client.reset_project_session(project_id, self.project_path)
        self.execution_client.bind_project_solution_store(project_id, self.project_path, None)
        self.workspace_navigation_controller = _WorkspaceNavigationControllerStub()
        self.script_editor = _ScriptEditorStub()
        self.action_toggle_script_editor = _ActionToggleStub()
        self.scene = _SceneStub()
        self.runtime_history = _RuntimeHistoryStub()
        self.viewer_host_service = _ViewerHostServiceStub()
        self.viewer_session_bridge = _ViewerSessionBridgeStub()
        self.library_pane_reset_requested = _SignalStub()
        self.node_library_changed = _SignalStub()
        self.node_execution_state_changed = _SignalStub()
        self.run_failure_changed = _SignalStub()
        self.project_meta_changed = _SignalStub()
        self.app_preferences_controller = mock.Mock()
        self.run_projection_controller = RunProjectionController(self)  # type: ignore[arg-type]

    def _refresh_recent_projects_menu(self) -> None:
        pass

    def _commit_node_execution_state_change(self) -> None:
        self.run_state.node_execution_revision += 1
        self.node_execution_state_changed.emit()


class ProjectDocumentIONoninteractiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self.root = Path(self._temp_dir.name)
        # Every dialog class the interactive paths reach is replaced by a Mock so
        # any accidental dialog construction or static call is recorded.
        message_box_patch = mock.patch("PyQt6.QtWidgets.QMessageBox", new=mock.Mock(name="QMessageBox"))
        file_dialog_patch = mock.patch("PyQt6.QtWidgets.QFileDialog", new=mock.Mock(name="QFileDialog"))
        self.message_box = message_box_patch.start()
        self.file_dialog = file_dialog_patch.start()
        self.addCleanup(message_box_patch.stop)
        self.addCleanup(file_dialog_patch.stop)

    def tearDown(self) -> None:
        self.assertEqual(self.message_box.mock_calls, [])
        self.assertEqual(self.file_dialog.mock_calls, [])

    def _host_and_controller(self, **kwargs) -> tuple[_ProjectHostStub, ProjectSessionController]:  # noqa: ANN003
        host = _ProjectHostStub(self.root, **kwargs)
        return host, ProjectSessionController(host)  # type: ignore[arg-type]

    @staticmethod
    def _mark_dirty(host: _ProjectHostStub, dirty: bool = True) -> None:
        for workspace in host.model.project.workspaces.values():
            workspace.dirty = dirty

    def _target(self, name: str) -> Path:
        target = self.root / "projects" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _saved_project_file(self, name: str = "saved.cxproj", *, project_id: str = "proj_saved") -> Path:
        host, controller = self._host_and_controller(project_id=project_id)
        target = self._target(name)
        result = controller.save_project_to_path(target)
        self.assertEqual(result.status, "saved", result.reason_code)
        return target

    # ------------------------------------------------------------------ save

    def test_save_project_to_path_requires_a_path_for_unsaved_projects(self) -> None:
        host, controller = self._host_and_controller()

        for missing in (None, "", "   "):
            with self.subTest(path=missing):
                result = controller.save_project_to_path(missing)
                self.assertIsInstance(result, ProjectSaveResult)
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.reason_code, "save_path_required")
                self.assertEqual(result.target_path, "")

        self.assertEqual(host.project_path, "")
        self.assertFalse(controller.document_io_active())

    def test_save_project_to_path_saves_as_then_resaves_bound_project(self) -> None:
        host, controller = self._host_and_controller()
        self._mark_dirty(host)
        target = self._target("demo.cxproj")

        result = controller.save_project_to_path(target)

        self.assertEqual(result.status, "saved", result.reason_code)
        self.assertEqual(result.reason_code, "save_succeeded")
        self.assertEqual(Path(result.target_path), target)
        self.assertTrue(target.is_file())
        self.assertEqual(host.project_path, str(target))
        self.assertFalse(any(ws.dirty for ws in host.model.project.workspaces.values()))
        # Non-dialog side effects of the interactive finish path are kept.
        self.assertGreaterEqual(host.workspace_navigation_controller.refresh_workspace_tabs_calls, 1)
        self.assertGreaterEqual(host.session_store.discard_calls, 1)
        self.assertGreaterEqual(len(host.session_store.persist_calls), 1)
        self.assertGreaterEqual(host.project_meta_changed.emit_calls, 1)
        self.assertIn(str(target), host.project_session_state.recent_project_paths)

        # No path -> replace the bound project; same path -> also replace_current.
        self._mark_dirty(host)
        self.assertEqual(controller.save_project_to_path(None).status, "saved")
        self.assertEqual(controller.save_project_to_path(str(target)).status, "saved")
        self.assertEqual(host.project_path, str(target))

        # A distinct path re-targets the bound project (Save As).
        other = self._target("copy.cxproj")
        self.assertEqual(controller.save_project_to_path(other).status, "saved")
        self.assertTrue(other.is_file())
        self.assertEqual(host.project_path, str(other))
        self.assertTrue(target.is_file())

    def test_save_project_to_path_failures_are_returned_without_dialogs(self) -> None:
        host, controller = self._host_and_controller()
        existing = self._target("existing.cxproj")
        existing.write_text("{}", encoding="utf-8")

        result = controller.save_project_to_path(existing)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason_code, "save_destination_exists")
        self.assertEqual(host.project_path, "")

    # ----------------------------------------------------------------- guard

    def test_guard_held_reports_in_progress_and_document_io_active(self) -> None:
        host, controller = self._host_and_controller()
        guard = controller._document_service._save_guard  # noqa: SLF001
        target = self._target("guarded.cxproj")
        self.assertFalse(controller.document_io_active())
        self.assertTrue(guard.acquire(False))
        try:
            self.assertTrue(controller.document_io_active())
            save_result = controller.save_project_to_path(target)
            self.assertEqual(save_result.status, "failed")
            self.assertEqual(save_result.reason_code, "save_in_progress")
            self.assertFalse(target.exists())

            open_result = controller.open_project_path_noninteractive(target, discard_unsaved=True)
            self.assertFalse(open_result.ok)
            self.assertEqual(open_result.reason_code, "open_in_progress")

            new_result = controller.new_project_noninteractive(discard_unsaved=True)
            self.assertFalse(new_result.ok)
            self.assertEqual(new_result.reason_code, "open_in_progress")
            self.assertTrue(controller.document_io_active())
        finally:
            guard.release()
        self.assertFalse(controller.document_io_active())

    # ------------------------------------------------------------------ open

    def test_open_project_path_noninteractive_reports_missing_and_invalid_paths(self) -> None:
        host, controller = self._host_and_controller()
        project_before = host.model.project

        missing = controller.open_project_path_noninteractive(
            self.root / "missing.cxproj", discard_unsaved=True
        )
        self.assertIsInstance(missing, ProjectOpenResult)
        self.assertFalse(missing.ok)
        self.assertEqual(missing.reason_code, "not_found")
        self.assertEqual(Path(missing.project_path), self.root / "missing.cxproj")
        self.assertIn("missing.cxproj", missing.message)

        invalid = controller.open_project_path_noninteractive("   ", discard_unsaved=True)
        self.assertFalse(invalid.ok)
        self.assertEqual(invalid.reason_code, "invalid_path")

        self.assertIs(host.model.project, project_before)
        self.assertEqual(host.project_path, "")

    def test_open_project_path_noninteractive_reports_load_failures(self) -> None:
        host, controller = self._host_and_controller()
        corrupt = self._target("corrupt.cxproj")
        corrupt.write_text("not json", encoding="utf-8")
        project_before = host.model.project

        result = controller.open_project_path_noninteractive(corrupt, discard_unsaved=True)

        self.assertFalse(result.ok)
        self.assertEqual(result.reason_code, "load_failed")
        self.assertTrue(result.message)
        self.assertIs(host.model.project, project_before)
        self.assertEqual(host.project_path, "")

    def test_open_project_path_noninteractive_respects_unsaved_changes(self) -> None:
        saved = self._saved_project_file()
        host, controller = self._host_and_controller(project_id="proj_dirty_current")
        self._mark_dirty(host)
        project_before = host.model.project

        blocked = controller.open_project_path_noninteractive(saved, discard_unsaved=False)

        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.reason_code, "project_dirty")
        self.assertIs(host.model.project, project_before)
        self.assertEqual(host.model.project.project_id, "proj_dirty_current")
        self.assertEqual(host.project_path, "")
        self.assertTrue(all(ws.dirty for ws in host.model.project.workspaces.values()))

        host.run_state.failed_node_id = "node-failed"
        opened = controller.open_project_path_noninteractive(saved, discard_unsaved=True)

        self.assertTrue(opened.ok)
        self.assertEqual(opened.reason_code, "opened")
        self.assertEqual(Path(opened.project_path), saved)
        self.assertEqual(opened.message, "")
        self.assertIsNot(host.model.project, project_before)
        self.assertEqual(host.model.project.project_id, "proj_saved")
        self.assertEqual(host.project_path, str(saved))
        self.assertIn(str(saved), host.project_session_state.recent_project_paths)
        # The controller facade resets runtime surfaces exactly like open_project_path.
        self.assertEqual(host.run_state.failed_node_id, "")
        self.assertEqual(host.run_failure_changed.emit_calls, 1)

    def test_saved_project_round_trips_through_noninteractive_open(self) -> None:
        host, controller = self._host_and_controller(project_id="proj_round_trip")
        host.model.project.name = "Round Trip"
        target = self._target("round_trip.cxproj")
        self.assertEqual(controller.save_project_to_path(target).status, "saved")

        self.assertTrue(controller.new_project_noninteractive(discard_unsaved=False).ok)
        self.assertEqual(host.project_path, "")
        self.assertEqual(host.model.project.project_id, "proj_local")

        opened = controller.open_project_path_noninteractive(target, discard_unsaved=False)

        self.assertTrue(opened.ok, opened.reason_code)
        self.assertEqual(host.model.project.project_id, "proj_round_trip")
        self.assertEqual(host.model.project.name, "Round Trip")
        self.assertEqual(host.project_path, str(target))
        self.assertFalse(any(ws.dirty for ws in host.model.project.workspaces.values()))

    # ---------------------------------------------------------- staged files

    def test_staged_file_publishes_on_save_and_reopens_without_prompts(self) -> None:
        # B3: the interactive save/open paths prompt when staged files exist; these seams must not.
        host, controller = self._host_and_controller(project_id="proj_staged")
        workspace_id = host.workspace_manager.active_workspace_id()
        node = host.model.add_node(workspace_id, "media.panel", "Picture", 0.0, 0.0)
        source = self.root / "inputs" / "picture.png"
        source.parent.mkdir(parents=True, exist_ok=True)
        payload = b"\x89PNG\r\n\x1a\n" + b"staged-payload"
        source.write_bytes(payload)

        staged_ref = controller.stage_node_artifact_file(
            source,
            artifact_prefix="image_source",
            io_dir=PROJECT_NODE_INPUTS_DIRNAME,
            subdirectory="media",
            filename=source.name,
            node_id=node.node_id,
        )
        self.assertTrue(staged_ref.startswith("temp://"), staged_ref)
        staged_path = controller.project_artifact_store().resolve_staged_path(staged_ref)
        self.assertIsNotNone(staged_path)
        host.model.set_node_property(workspace_id, node.node_id, "source", staged_ref)
        self._mark_dirty(host)

        target = self._target("staged.cxproj")
        result = controller.save_project_to_path(target)

        self.assertEqual(result.status, "saved", result.reason_code)
        self.assertEqual(self.message_box.mock_calls, [])
        self.assertEqual(self.file_dialog.mock_calls, [])
        saved_project = host.serializer.load(str(target))
        saved_ref = str(saved_project.workspaces[workspace_id].nodes[node.node_id].properties["source"])
        self.assertTrue(saved_ref.startswith("saved://"), saved_ref)
        saved_store = ProjectArtifactStore.from_project_metadata(
            project_path=target, project_metadata=saved_project.metadata
        )
        published = saved_store.resolve_managed_path(saved_ref)
        self.assertIsNotNone(published)
        assert published is not None
        sidecar_root = ProjectArtifactLayout.from_project_path(target).sidecar_root
        self.assertTrue(published.resolve().is_relative_to(sidecar_root.resolve()), published)
        self.assertEqual(published.read_bytes(), payload)

        reopen_host, reopen_controller = self._host_and_controller(project_id="proj_reopen")
        opened = reopen_controller.open_project_path_noninteractive(target, discard_unsaved=False)

        self.assertTrue(opened.ok, opened.reason_code)
        self.assertEqual(Path(opened.project_path), target)
        reopened = reopen_host.model.project.workspaces[workspace_id].nodes[node.node_id]
        self.assertEqual(reopened.properties["source"], saved_ref)
        reopened_path = reopen_controller.project_artifact_store().resolve_managed_path(saved_ref)
        self.assertIsNotNone(reopened_path)
        assert reopened_path is not None
        self.assertEqual(reopened_path.read_bytes(), payload)

    # ------------------------------------------------------------------- new

    def test_new_project_noninteractive_dirty_and_discard_cases(self) -> None:
        host, controller = self._host_and_controller(project_id="proj_before_new")
        self._mark_dirty(host)
        project_before = host.model.project

        blocked = controller.new_project_noninteractive(discard_unsaved=False)

        self.assertIsInstance(blocked, ProjectOpenResult)
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.reason_code, "project_dirty")
        self.assertEqual(blocked.project_path, "")
        self.assertIs(host.model.project, project_before)
        self.assertEqual(host.model.project.project_id, "proj_before_new")

        host.run_state.failed_node_id = "node-failed"
        replaced = controller.new_project_noninteractive(discard_unsaved=True)

        self.assertTrue(replaced.ok)
        self.assertEqual(replaced.reason_code, "opened")
        self.assertEqual(replaced.project_path, "")
        self.assertEqual(replaced.message, "")
        self.assertIsNot(host.model.project, project_before)
        self.assertEqual(host.model.project.project_id, "proj_local")
        self.assertEqual(host.project_path, "")
        self.assertFalse(any(ws.dirty for ws in host.model.project.workspaces.values()))
        self.assertEqual(host.run_state.failed_node_id, "")
        self.assertEqual(host.workspace_navigation_controller.refresh_workspace_tabs_calls, 1)
        self.assertEqual(len(host.workspace_navigation_controller.switch_workspace_calls), 1)

        # A clean project is replaced even without discard_unsaved.
        clean = controller.new_project_noninteractive(discard_unsaved=False)
        self.assertTrue(clean.ok)

    # --------------------------------------------------------------- results

    def test_result_types_reject_inconsistent_values(self) -> None:
        with self.assertRaises(ValueError):
            ProjectOpenResult(True, "project_dirty", "", "")
        with self.assertRaises(ValueError):
            ProjectOpenResult(False, "opened", "", "")
        with self.assertRaises(ValueError):
            ProjectOpenResult(False, "unknown", "", "")
        with self.assertRaises(ValueError):
            ProjectSaveResult("saved", "save_path_required", "")
        self.assertEqual(
            ProjectSaveResult("failed", "save_path_required", "").reason_code,
            "save_path_required",
        )


if __name__ == "__main__":
    unittest.main()
