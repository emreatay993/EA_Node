from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ea_node_editor.graph.file_issue_state import encode_file_repair_request
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.persistence.artifact_refs import format_managed_artifact_ref
from ea_node_editor.persistence.file_issues import collect_workspace_file_issue_map
from tests.conftest import ShellTestEnvironment

_REPO_ROOT = Path(__file__).resolve().parents[1]


class ProjectFileIssueTests(unittest.TestCase):
    def test_collect_workspace_file_issues_tracks_missing_owner_and_consumer_sources_only(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace

        image_node = model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Image Panel",
            80.0,
            80.0,
        )
        file_read_node = model.add_node(
            workspace.workspace_id,
            "io.file_read",
            "File Read",
            320.0,
            80.0,
        )
        file_write_node = model.add_node(
            workspace.workspace_id,
            "io.file_write",
            "File Write",
            560.0,
            80.0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            project_path = temp_root / "issues_demo.sfe"
            model.set_node_property(
                workspace.workspace_id,
                image_node.node_id,
                "source_path",
                str(temp_root / "missing-image.png"),
            )
            model.set_node_property(
                workspace.workspace_id,
                file_read_node.node_id,
                "path",
                format_managed_artifact_ref("missing_input"),
            )
            model.set_node_property(
                workspace.workspace_id,
                file_write_node.node_id,
                "path",
                "output.txt",
            )

            issue_map = collect_workspace_file_issue_map(
                workspace=workspace,
                registry=registry,
                project_path=str(project_path),
                project_metadata={
                    "artifact_store": {
                        "artifacts": {
                            "missing_input": {
                                "relative_path": "assets/files/missing-input.txt",
                            }
                        }
                    }
                },
            )

        self.assertEqual(issue_map[(image_node.node_id, "source_path")].issue_kind, "external_missing")
        self.assertEqual(issue_map[(file_read_node.node_id, "path")].issue_kind, "managed_missing")
        self.assertEqual(issue_map[(file_read_node.node_id, "path")].source_mode, "managed_copy")
        self.assertNotIn((file_write_node.node_id, "path"), issue_map)

    def test_shell_window_repairs_missing_external_consumer_path_without_managed_metadata(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        test_env = ShellTestEnvironment()
        temp_root = test_env.start()
        window = ShellWindow()
        try:
            repaired_path = temp_root / "repaired-input.txt"
            repaired_path.write_text("restored", encoding="utf-8")
            missing_path = str(temp_root / "missing-input.txt")

            node_id = window.scene.add_node_from_type("io.file_read", x=120.0, y=80.0)
            self.assertTrue(node_id)
            window.scene.set_node_property(node_id, "path", missing_path)
            window.scene.select_node(node_id, False)
            app.processEvents()

            path_item = _selected_property_item(window, "path")
            self.assertTrue(path_item["file_issue_active"])
            self.assertTrue(str(path_item["file_issue_request"]).startswith("ea-file-repair:"))

            with patch(
                "ea_node_editor.ui.shell.window_state.workspace_graph_actions.QFileDialog.getOpenFileName",
                return_value=(str(repaired_path), ""),
            ) as dialog_mock:
                relinked_path = window.browse_node_property_path(
                    node_id,
                    "path",
                    encode_file_repair_request(missing_path),
                )

            self.assertEqual(relinked_path, str(repaired_path))
            self.assertEqual(dialog_mock.call_count, 1)

            window.scene.set_node_property(node_id, "path", relinked_path)
            app.processEvents()

            path_item = _selected_property_item(window, "path")
            self.assertFalse(path_item["file_issue_active"])
            self.assertNotIn("artifact_store", window.model.project.metadata)
        finally:
            window.close()
            window.deleteLater()
            app.processEvents()
            test_env.stop()

    def test_shell_window_repairs_missing_managed_media_source_with_staged_copy(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        test_env = ShellTestEnvironment()
        temp_root = test_env.start()
        window = ShellWindow()
        try:
            source_fixture = _REPO_ROOT / "tests" / "fixtures" / "passive_nodes" / "reference_preview.png"
            managed_ref = format_managed_artifact_ref("managed_image")

            window.project_path = str(temp_root / "repair_demo.sfe")
            window.model.project.metadata = {
                "artifact_store": {
                    "artifacts": {
                        "managed_image": {
                            "relative_path": "assets/media/missing.png",
                        }
                    }
                }
            }

            node_id = window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
            self.assertTrue(node_id)
            window.scene.set_node_property(node_id, "source_path", managed_ref)
            window.scene.select_node(node_id, False)
            app.processEvents()

            path_item = _selected_property_item(window, "source_path")
            self.assertTrue(path_item["file_issue_active"])

            with patch(
                "ea_node_editor.ui.shell.window_state.workspace_graph_actions.QInputDialog.getItem",
                return_value=("Managed Copy", True),
            ) as mode_mock, patch(
                "ea_node_editor.ui.shell.window_state.workspace_graph_actions.QFileDialog.getOpenFileName",
                return_value=(str(source_fixture), ""),
            ) as dialog_mock:
                repaired_ref = window.browse_node_property_path(
                    node_id,
                    "source_path",
                    encode_file_repair_request(managed_ref),
                )

            self.assertEqual(repaired_ref, "artifact-stage://managed_image")
            self.assertEqual(mode_mock.call_count, 1)
            self.assertEqual(dialog_mock.call_count, 1)

            window.scene.set_node_property(node_id, "source_path", repaired_ref)
            app.processEvents()

            path_item = _selected_property_item(window, "source_path")
            self.assertFalse(path_item["file_issue_active"])
            self.assertEqual(
                window.model.project.metadata["artifact_store"]["staged"]["managed_image"]["relative_path"],
                ".staging/assets/media/managed_image.png",
            )
        finally:
            window.close()
            window.deleteLater()
            app.processEvents()
            test_env.stop()

    def test_shell_window_repairs_missing_staged_media_source_reusing_existing_artifact_id(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        test_env = ShellTestEnvironment()
        temp_root = test_env.start()
        window = ShellWindow()
        try:
            source_fixture = _REPO_ROOT / "tests" / "fixtures" / "passive_nodes" / "reference_preview.png"
            staged_ref = "artifact-stage://managed_image"

            window.project_path = str(temp_root / "repair_demo.sfe")
            window.model.project.metadata = {
                "artifact_store": {
                    "staged": {
                        "managed_image": {
                            "relative_path": ".staging/assets/media/managed_image.png",
                        }
                    }
                }
            }

            node_id = window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
            self.assertTrue(node_id)
            window.scene.set_node_property(node_id, "source_path", staged_ref)
            window.scene.select_node(node_id, False)
            app.processEvents()

            path_item = _selected_property_item(window, "source_path")
            self.assertTrue(path_item["file_issue_active"])

            with patch(
                "ea_node_editor.ui.shell.window_state.workspace_graph_actions.QInputDialog.getItem",
                return_value=("Managed Copy", True),
            ) as mode_mock, patch(
                "ea_node_editor.ui.shell.window_state.workspace_graph_actions.QFileDialog.getOpenFileName",
                return_value=(str(source_fixture), ""),
            ) as dialog_mock:
                repaired_ref = window.browse_node_property_path(
                    node_id,
                    "source_path",
                    encode_file_repair_request(staged_ref),
                )

            self.assertEqual(repaired_ref, staged_ref)
            self.assertEqual(mode_mock.call_count, 1)
            self.assertEqual(dialog_mock.call_count, 1)

            store = ProjectArtifactStore.from_project_metadata(
                project_path=window.project_path,
                project_metadata=window.model.project.metadata,
            )
            staged_path = store.resolve_staged_path(staged_ref)
            self.assertIsNotNone(staged_path)
            assert staged_path is not None
            self.assertTrue(staged_path.exists())
            self.assertEqual(staged_path.read_bytes(), source_fixture.read_bytes())
            self.assertEqual(
                window.model.project.metadata["artifact_store"]["staged"]["managed_image"]["relative_path"],
                ".staging/assets/media/managed_image.png",
            )
        finally:
            window.close()
            window.deleteLater()
            app.processEvents()
            test_env.stop()


def _selected_property_item(window, property_key: str) -> dict[str, object]:  # noqa: ANN001
    return next(
        item
        for item in window.selected_node_property_items
        if str(item.get("key", "")).strip() == property_key
    )


if __name__ == "__main__":
    unittest.main()
