from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.artifact_refs import (
    format_managed_artifact_ref,
    format_staged_artifact_ref,
)
from ea_node_editor.ui.dialogs.project_save_as_dialog import ProjectSaveAsDialog
from ea_node_editor.ui.shell.controllers.project_session_controller import ProjectSessionController
from ea_node_editor.ui.shell.state import ShellProjectSessionState


class _SignalStub:
    def __init__(self) -> None:
        self.emit_count = 0

    def emit(self) -> None:
        self.emit_count += 1


class _ScriptEditorStub:
    def __init__(self) -> None:
        self.visible = False
        self.floating = False


class _WorkspaceLibraryControllerStub:
    def __init__(self) -> None:
        self.save_active_view_state_calls = 0
        self.refresh_workspace_tabs_calls = 0

    def save_active_view_state(self) -> None:
        self.save_active_view_state_calls += 1

    def refresh_workspace_tabs(self) -> None:
        self.refresh_workspace_tabs_calls += 1


class _SerializerStub:
    def __init__(self, persistent_document: dict) -> None:
        self._persistent_document = copy.deepcopy(persistent_document)
        self.saved_documents: list[tuple[str, dict]] = []

    def to_persistent_document(self, _project) -> dict:  # noqa: ANN001
        return copy.deepcopy(self._persistent_document)

    def save_document(self, path: str, document: dict) -> None:
        target = Path(path).with_suffix(".sfe")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = copy.deepcopy(document)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True), encoding="utf-8")
        self.saved_documents.append((str(target), payload))

    def to_document(self, project) -> dict:  # noqa: ANN001
        document = copy.deepcopy(self._persistent_document)
        document["metadata"] = copy.deepcopy(project.metadata)
        return document


class _SessionStoreStub:
    def __init__(self) -> None:
        self.discard_calls = 0
        self.persist_calls: list[dict] = []

    def discard_autosave_snapshot(self) -> None:
        self.discard_calls += 1

    def persist_session(self, **kwargs) -> None:  # noqa: ANN003
        self.persist_calls.append(copy.deepcopy(kwargs))


class _SceneStub:
    @staticmethod
    def selected_node_id() -> str:
        return ""


class _ProjectHostStub:
    def __init__(self, *, project_path: str, persistent_document: dict) -> None:
        self.project_session_state = ShellProjectSessionState()
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.model.project.project_id = str(persistent_document.get("project_id", "proj_save_as"))
        self.model.project.name = str(persistent_document.get("name", "Save As Demo"))
        workspace = self.model.active_workspace
        workspace_docs = persistent_document.get("workspaces", [])
        if workspace_docs:
            workspace_doc = workspace_docs[0]
            workspace.name = str(workspace_doc.get("name", workspace.name))
            for node_doc in workspace_doc.get("nodes", []):
                self.model.add_node(
                    workspace.workspace_id,
                    str(node_doc.get("type_id", "")),
                    str(node_doc.get("title", "")),
                    float(node_doc.get("x", 0.0)),
                    float(node_doc.get("y", 0.0)),
                    properties=copy.deepcopy(node_doc.get("properties", {})),
                    exposed_ports=copy.deepcopy(node_doc.get("exposed_ports", {})),
                )
        self.model.project.metadata = copy.deepcopy(persistent_document.get("metadata", {}))
        for workspace in self.model.project.workspaces.values():
            workspace.dirty = True
        self.project_path = project_path
        self.session_store = _SessionStoreStub()
        self.serializer = _SerializerStub(persistent_document)
        self.workspace_library_controller = _WorkspaceLibraryControllerStub()
        self.script_editor = _ScriptEditorStub()
        self.action_toggle_script_editor = object()
        self.scene = _SceneStub()
        self.project_meta_changed = _SignalStub()
        self.refresh_calls = 0

    def _refresh_recent_projects_menu(self) -> None:
        self.refresh_calls += 1


class _AcceptingSelfContainedSaveAsDialog:
    DialogCode = ProjectSaveAsDialog.DialogCode
    SELF_CONTAINED_COPY = ProjectSaveAsDialog.SELF_CONTAINED_COPY

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.args = args
        self.kwargs = kwargs

    def exec(self) -> int:
        return self.DialogCode.Accepted

    def selected_mode(self) -> str:
        return self.SELF_CONTAINED_COPY


class ProjectSaveAsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_defaults_to_self_contained_copy(self) -> None:
        dialog = ProjectSaveAsDialog(referenced_managed_count=2, referenced_staged_count=1)
        self.addCleanup(dialog.deleteLater)

        self.assertTrue(dialog.self_contained_copy_radio.isChecked())
        self.assertEqual(dialog.selected_mode(), ProjectSaveAsDialog.SELF_CONTAINED_COPY)
        self.assertIn("2 referenced managed files", dialog.self_contained_copy_radio.text())


class ProjectSaveAsFlowTests(unittest.TestCase):
    maxDiff = None

    def _build_persistent_document(self, *, external_path: str) -> dict:
        return {
            "schema_version": 1,
            "project_id": "proj_save_as",
            "name": "Save As Demo",
            "active_workspace_id": "ws_1",
            "workspace_order": ["ws_1"],
            "workspaces": [
                {
                    "workspace_id": "ws_1",
                    "name": "Main",
                    "dirty": True,
                    "active_view_id": "view_1",
                    "views": [
                        {
                            "view_id": "view_1",
                            "name": "Main",
                            "zoom": 1.0,
                            "pan_x": 0.0,
                            "pan_y": 0.0,
                            "scope_path": [],
                        }
                    ],
                    "nodes": [
                        {
                            "node_id": "node_managed",
                            "type_id": "passive.media.image_panel",
                            "title": "Managed",
                            "x": 0.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {
                                "source_path": format_managed_artifact_ref("managed_image"),
                            },
                            "exposed_ports": {},
                        },
                        {
                            "node_id": "node_staged",
                            "type_id": "passive.media.image_panel",
                            "title": "Staged",
                            "x": 120.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {
                                "source_path": format_staged_artifact_ref("pending_output"),
                            },
                            "exposed_ports": {},
                        },
                        {
                            "node_id": "node_external",
                            "type_id": "passive.media.image_panel",
                            "title": "External",
                            "x": 240.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {
                                "source_path": external_path,
                            },
                            "exposed_ports": {},
                        },
                    ],
                    "edges": [],
                }
            ],
            "metadata": {
                "artifact_store": {
                    "artifacts": {
                        "managed_image": {
                            "relative_path": "assets/media/diagram.png",
                        }
                    },
                    "staged": {
                        "pending_output": {
                            "relative_path": ".staging/outputs/run.txt",
                            "slot": "process_run.stdout",
                        }
                    },
                }
            },
        }

    def test_save_as_copies_referenced_managed_files_and_excludes_staging_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "source_project.sfe"
            source_managed_path = source_project.with_name("source_project.data") / "assets" / "media" / "diagram.png"
            source_managed_path.parent.mkdir(parents=True, exist_ok=True)
            source_managed_path.write_text("managed payload", encoding="utf-8")
            source_staging_path = source_project.with_name("source_project.data") / ".staging" / "outputs" / "run.txt"
            source_staging_path.parent.mkdir(parents=True, exist_ok=True)
            source_staging_path.write_text("staged payload", encoding="utf-8")
            external_path = str((root / "external" / "linked.png").resolve())
            Path(external_path).parent.mkdir(parents=True, exist_ok=True)
            Path(external_path).write_text("external payload", encoding="utf-8")
            persistent_document = self._build_persistent_document(external_path=external_path)

            target_project = root / "copies" / "clone_project.sfe"
            stale_managed_path = target_project.with_name("clone_project.data") / "artifacts" / "stale.txt"
            stale_managed_path.parent.mkdir(parents=True, exist_ok=True)
            stale_managed_path.write_text("stale", encoding="utf-8")
            stale_staging_path = target_project.with_name("clone_project.data") / ".staging" / "outputs" / "old.txt"
            stale_staging_path.parent.mkdir(parents=True, exist_ok=True)
            stale_staging_path.write_text("stale staging", encoding="utf-8")

            host = _ProjectHostStub(project_path=str(source_project), persistent_document=persistent_document)
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            with patch.object(
                ProjectSessionController,
                "_prompt_project_files_action",
                return_value=True,
            ), patch(
                "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                return_value=(str(target_project), "EA Project (*.sfe)"),
            ), patch(
                "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                _AcceptingSelfContainedSaveAsDialog,
            ):
                controller.save_project_as()

            saved_path = target_project.with_suffix(".sfe")
            saved_doc = json.loads(saved_path.read_text(encoding="utf-8"))
            copied_managed_path = saved_path.with_name("clone_project.data") / "assets" / "media" / "diagram.png"
            copied_staging_path = saved_path.with_name("clone_project.data") / ".staging" / "outputs" / "run.txt"

            self.assertEqual(host.project_path, str(saved_path))
            self.assertEqual(host.project_session_state.recent_project_paths, [str(saved_path)])
            self.assertFalse(next(iter(host.model.project.workspaces.values())).dirty)
            self.assertEqual(host.project_meta_changed.emit_count, 1)
            self.assertEqual(host.workspace_library_controller.refresh_workspace_tabs_calls, 1)
            self.assertEqual(host.session_store.discard_calls, 1)
            self.assertEqual(
                saved_doc["metadata"]["artifact_store"],
                {
                    "artifacts": {
                        "managed_image": {
                            "relative_path": "assets/media/diagram.png",
                        }
                    },
                    "staged": {},
                },
            )
            self.assertEqual(copied_managed_path.read_text(encoding="utf-8"), "managed payload")
            self.assertFalse(copied_staging_path.exists())
            self.assertFalse(stale_managed_path.exists())
            self.assertFalse(stale_staging_path.exists())

            workspace_doc = saved_doc["workspaces"][0]
            saved_nodes = {node["node_id"]: node for node in workspace_doc["nodes"]}
            self.assertEqual(
                saved_nodes["node_managed"]["properties"]["source_path"],
                format_managed_artifact_ref("managed_image"),
            )
            self.assertEqual(
                saved_nodes["node_staged"]["properties"]["source_path"],
                format_staged_artifact_ref("pending_output"),
            )
            self.assertEqual(saved_nodes["node_external"]["properties"]["source_path"], external_path)

    def test_save_as_prompts_with_staged_and_broken_summary_before_file_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "source_project.sfe"
            managed_path = source_project.with_name("source_project.data") / "assets" / "media" / "diagram.png"
            managed_path.parent.mkdir(parents=True, exist_ok=True)
            managed_path.write_text("managed payload", encoding="utf-8")
            staged_path = source_project.with_name("source_project.data") / ".staging" / "outputs" / "run.txt"
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_text("staged payload", encoding="utf-8")
            missing_external_path = str((root / "external" / "missing.png").resolve())
            persistent_document = self._build_persistent_document(external_path=missing_external_path)

            host = _ProjectHostStub(project_path=str(source_project), persistent_document=persistent_document)
            controller = ProjectSessionController(host)  # type: ignore[arg-type]
            target_project = root / "copies" / "clone_project.sfe"

            with patch.object(
                ProjectSessionController,
                "_prompt_project_files_action",
                return_value=True,
            ) as prompt, patch(
                "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                return_value=(str(target_project), "EA Project (*.sfe)"),
            ), patch(
                "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                _AcceptingSelfContainedSaveAsDialog,
            ):
                controller.save_project_as()

        self.assertEqual(prompt.call_count, 1)
        snapshot = prompt.call_args.kwargs["snapshot"]
        self.assertEqual(snapshot.managed_count, 1)
        self.assertEqual(snapshot.staged_count, 1)
        self.assertEqual(snapshot.broken_count, 1)

    def test_save_as_cancelled_from_project_file_prompt_skips_file_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "source_project.sfe"
            managed_path = source_project.with_name("source_project.data") / "assets" / "media" / "diagram.png"
            managed_path.parent.mkdir(parents=True, exist_ok=True)
            managed_path.write_text("managed payload", encoding="utf-8")
            missing_external_path = str((root / "external" / "missing.png").resolve())
            persistent_document = self._build_persistent_document(external_path=missing_external_path)

            host = _ProjectHostStub(project_path=str(source_project), persistent_document=persistent_document)
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            with patch.object(
                ProjectSessionController,
                "_prompt_project_files_action",
                return_value=False,
            ) as prompt, patch(
                "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
            ) as file_dialog, patch(
                "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                _AcceptingSelfContainedSaveAsDialog,
            ):
                controller.save_project_as()

        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(file_dialog.call_count, 0)
        self.assertEqual(host.serializer.saved_documents, [])

    def test_save_as_plain_project_without_managed_data_still_switches_to_new_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target_project = root / "copies" / "plain_project.sfe"
            persistent_document = {
                "schema_version": 1,
                "project_id": "proj_plain",
                "name": "Plain Project",
                "active_workspace_id": "ws_1",
                "workspace_order": ["ws_1"],
                "workspaces": [
                    {
                        "workspace_id": "ws_1",
                        "name": "Main",
                        "dirty": True,
                        "active_view_id": "view_1",
                        "views": [
                            {
                                "view_id": "view_1",
                                "name": "Main",
                                "zoom": 1.0,
                                "pan_x": 0.0,
                                "pan_y": 0.0,
                                "scope_path": [],
                            }
                        ],
                        "nodes": [],
                        "edges": [],
                    }
                ],
                "metadata": {},
            }
            host = _ProjectHostStub(project_path="", persistent_document=persistent_document)
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            with patch.object(
                ProjectSessionController,
                "_prompt_project_files_action",
                return_value=True,
            ), patch(
                "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                return_value=(str(target_project), "EA Project (*.sfe)"),
            ), patch(
                "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                _AcceptingSelfContainedSaveAsDialog,
            ):
                controller.save_project_as()

            saved_doc = json.loads(target_project.read_text(encoding="utf-8"))
            self.assertEqual(host.project_path, str(target_project))
            self.assertEqual(
                saved_doc["metadata"]["artifact_store"],
                {
                    "artifacts": {},
                    "staged": {},
                },
            )


if __name__ == "__main__":
    unittest.main()
