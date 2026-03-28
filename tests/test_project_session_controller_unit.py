from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.ui.shell.controllers.project_session_controller import ProjectSessionController
from ea_node_editor.ui.shell.state import ShellProjectSessionState


class _ScriptEditorStub:
    def __init__(self) -> None:
        self.visible = False
        self.floating = False
        self.focus_calls = 0
        self.nodes = []

    def set_visible(self, value: bool) -> None:
        self.visible = bool(value)

    def set_floating(self, value: bool) -> None:
        self.floating = bool(value)

    def focus_editor(self) -> None:
        self.focus_calls += 1

    def set_node(self, node) -> None:  # noqa: ANN001
        self.nodes.append(node)


class _ActionToggleStub:
    def __init__(self) -> None:
        self.checked = False

    def setChecked(self, value: bool) -> None:  # noqa: N802
        self.checked = bool(value)


class _SceneStub:
    def __init__(self, selected_node_id: str = "") -> None:
        self._selected_node_id = selected_node_id

    def selected_node_id(self) -> str:
        return self._selected_node_id


class _WorkspaceLibraryControllerStub:
    def __init__(self) -> None:
        self.save_active_view_state_calls = 0

    def save_active_view_state(self) -> None:
        self.save_active_view_state_calls += 1


class _SerializerStub:
    def to_document(self, project) -> dict:  # noqa: ANN001
        return {
            "project_id": project.project_id,
            "name": project.name,
            "metadata": copy.deepcopy(project.metadata),
        }


class _SessionStoreStub:
    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path
        self.discard_calls = 0
        self.persist_calls: list[dict] = []

    def staging_workspace_root(self) -> Path:
        root = self._base_path / "session_staging"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def discard_autosave_snapshot(self) -> None:
        self.discard_calls += 1

    def persist_session(self, **kwargs) -> None:  # noqa: ANN003
        self.persist_calls.append(copy.deepcopy(kwargs))


class _ProjectHostStub:
    def __init__(self, base_path: Path | None = None) -> None:
        self.project_session_state = ShellProjectSessionState()
        self.model = GraphModel()
        self.script_editor = _ScriptEditorStub()
        self.action_toggle_script_editor = _ActionToggleStub()
        self.scene = _SceneStub()
        self.project_path = ""
        self.session_store = _SessionStoreStub(base_path or Path.cwd())
        self.serializer = _SerializerStub()
        self.workspace_library_controller = _WorkspaceLibraryControllerStub()
        self.refresh_calls = 0

    def _refresh_recent_projects_menu(self) -> None:
        self.refresh_calls += 1


class ProjectSessionControllerUnitTests(unittest.TestCase):
    def test_metadata_defaults_are_merged_without_dropping_existing_values(self) -> None:
        host = _ProjectHostStub()
        host.model.project.metadata = {
            "workflow_settings": {
                "solver_config": {"thread_count": 16},
            },
            "ui": {
                "script_editor": {"visible": True},
            },
        }
        controller = ProjectSessionController(host)  # type: ignore[arg-type]

        controller.ensure_project_metadata_defaults()

        metadata = host.model.project.metadata
        self.assertEqual(metadata["workflow_settings"]["solver_config"]["thread_count"], 16)
        self.assertIn("memory_limit_gb", metadata["workflow_settings"]["solver_config"])
        self.assertTrue(metadata["ui"]["script_editor"]["visible"])
        self.assertIn("floating", metadata["ui"]["script_editor"])
        self.assertIn("passive_style_presets", metadata["ui"])

    def test_recent_project_paths_are_normalized_deduplicated_and_capped(self) -> None:
        host = _ProjectHostStub()
        controller = ProjectSessionController(host)  # type: ignore[arg-type]

        normalized = controller.set_recent_project_paths(
            [
                " first_project ",
                "first_project.sfe",
                "",
                ".",
                *(f"project_{index}" for index in range(2, 20)),
            ],
            persist=False,
        )

        self.assertEqual(normalized[0], "first_project.sfe")
        self.assertEqual(len(normalized), 10)
        self.assertEqual(len(set(normalized)), len(normalized))
        self.assertEqual(host.project_session_state.recent_project_paths, normalized)
        self.assertEqual(host.refresh_calls, 1)

    def test_add_and_remove_recent_project_paths_normalize_suffixes(self) -> None:
        host = _ProjectHostStub()
        controller = ProjectSessionController(host)  # type: ignore[arg-type]

        with mock.patch.object(controller._session_service, "persist_session") as persist_session:
            controller.set_recent_project_paths(["alpha.sfe", "beta.sfe"], persist=False)
            updated = controller.add_recent_project_path("beta", persist=True)
            self.assertEqual(updated[:2], ["beta.sfe", "alpha.sfe"])

            updated = controller.remove_recent_project_path("alpha", persist=True)
            self.assertEqual(updated, ["beta.sfe"])
            self.assertEqual(persist_session.call_count, 2)

    def test_controller_routes_project_session_actions_through_service_authorities(self) -> None:
        host = _ProjectHostStub()
        controller = ProjectSessionController(host)  # type: ignore[arg-type]
        snapshot = mock.sentinel.snapshot
        issue = mock.sentinel.issue
        recovered_project = host.model.project

        with (
            mock.patch.object(controller._document_service, "save_project") as save_project,
            mock.patch.object(controller._document_service, "save_project_as") as save_project_as,
            mock.patch.object(controller._document_service, "open_project") as open_project,
            mock.patch.object(
                controller._document_service,
                "open_project_path",
                return_value=True,
            ) as open_project_path,
            mock.patch.object(
                controller._project_files_service,
                "prompt_project_files_action",
                return_value=True,
            ) as prompt_project_files_action,
            mock.patch.object(controller._project_files_service, "show_project_files_dialog") as show_project_files_dialog,
            mock.patch.object(
                controller._project_files_service,
                "repair_project_file_issue",
                return_value=True,
            ) as repair_project_file_issue,
            mock.patch.object(
                controller._session_service,
                "prompt_recover_autosave",
                return_value=mock.sentinel.choice,
            ) as prompt_recover_autosave,
        ):
            controller.save_project()
            controller.save_project_as()
            controller.open_project()
            self.assertTrue(controller.open_project_path("example.sfe", show_errors=False))
            self.assertTrue(
                controller._prompt_project_files_action(
                    title="Save Project",
                    text="summary",
                    continue_label="Save Project",
                    cancel_standard_button=object(),
                    snapshot=snapshot,
                    context_key="save",
                    allow_repair=True,
                    always_prompt=True,
                )
            )
            controller.show_project_files_dialog(snapshot=snapshot, allow_repair=True)
            self.assertTrue(controller._repair_project_file_issue(issue))
            self.assertIs(
                controller.prompt_recover_autosave(recovered_project),
                mock.sentinel.choice,
            )

        save_project.assert_called_once_with()
        save_project_as.assert_called_once_with()
        open_project.assert_called_once_with()
        open_project_path.assert_called_once_with("example.sfe", show_errors=False)
        prompt_project_files_action.assert_called_once_with(
            title="Save Project",
            text="summary",
            continue_label="Save Project",
            cancel_standard_button=mock.ANY,
            snapshot=snapshot,
            context_key="save",
            allow_repair=True,
            always_prompt=True,
        )
        show_project_files_dialog.assert_called_once_with(snapshot=snapshot, allow_repair=True)
        repair_project_file_issue.assert_called_once_with(issue)
        prompt_recover_autosave.assert_called_once_with(recovered_project)

    def test_restore_script_editor_state_requires_selected_node_for_visibility(self) -> None:
        host = _ProjectHostStub()
        host.model.project.metadata = {
            "ui": {
                "script_editor": {
                    "visible": True,
                    "floating": True,
                }
            }
        }
        controller = ProjectSessionController(host)  # type: ignore[arg-type]

        controller.restore_script_editor_state()
        self.assertTrue(host.script_editor.floating)
        self.assertFalse(host.script_editor.visible)
        self.assertFalse(host.action_toggle_script_editor.checked)

        host.scene = _SceneStub(selected_node_id="node_1")
        controller.restore_script_editor_state()
        self.assertTrue(host.script_editor.visible)
        self.assertTrue(host.action_toggle_script_editor.checked)

    def test_close_session_discards_staged_scratch_and_persists_lightweight_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            host = _ProjectHostStub(Path(temp_dir))
            staging_root = host.session_store.staging_workspace_root() / "project-123"
            payload_path = staging_root / "outputs" / "run.txt"
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            payload_path.write_text("payload", encoding="utf-8")
            host.model.project.metadata = {
                "artifact_store": {
                    "staging_root": {
                        "kind": "session_temp",
                        "absolute_path": str(staging_root),
                    },
                    "staged": {
                        "pending_output": {
                            "relative_path": "outputs/run.txt",
                            "slot": "process_run.stdout",
                        }
                    },
                }
            }
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            controller.close_session()

            self.assertFalse(staging_root.exists())
            self.assertEqual(host.session_store.discard_calls, 1)
            self.assertEqual(len(host.session_store.persist_calls), 1)
            persisted_doc = host.session_store.persist_calls[0]["project_doc"]
            self.assertNotIn("staging_root", persisted_doc["metadata"]["artifact_store"])
            self.assertIn("pending_output", persisted_doc["metadata"]["artifact_store"]["staged"])
            self.assertEqual(host.workspace_library_controller.save_active_view_state_calls, 1)


if __name__ == "__main__":
    unittest.main()
