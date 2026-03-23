from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ea_node_editor.persistence.artifact_refs import (
    ManagedArtifactRef,
    StagedArtifactRef,
    format_managed_artifact_ref,
    format_staged_artifact_ref,
    parse_artifact_ref,
)
from ea_node_editor.persistence.artifact_store import (
    ArtifactStoreState,
    ProjectArtifactLayout,
    ProjectArtifactStore,
    artifact_store_metadata_from_project_metadata,
    normalize_artifact_store_metadata,
)


class ProjectArtifactStoreTests(unittest.TestCase):
    def test_layout_derives_sibling_sidecar_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "demo_project.sfe"
            layout = ProjectArtifactLayout.from_project_path(project_path)

        self.assertEqual(layout.project_file, project_path)
        self.assertEqual(layout.sidecar_root, project_path.with_name("demo_project.data"))
        self.assertEqual(layout.assets_root, project_path.with_name("demo_project.data") / "assets")
        self.assertEqual(layout.artifacts_root, project_path.with_name("demo_project.data") / "artifacts")
        self.assertEqual(layout.staging_root, project_path.with_name("demo_project.data") / ".staging")
        self.assertEqual(
            layout.staging_recovery_root,
            project_path.with_name("demo_project.data") / ".staging" / "recovery",
        )

    def test_normalize_artifact_store_metadata_keeps_valid_entries_and_defaults_empty_maps(self) -> None:
        normalized = normalize_artifact_store_metadata(
            {
                "owner": "packet-p01",
                "artifacts": {
                    "image_source": {"path": r"assets\media\diagram.png"},
                    "bad_path": {"path": "../escape.txt"},
                },
                "staged": {
                    "pending_output": {
                        "path": r".staging\outputs\run.txt",
                        "slot": "process_run.stdout",
                    }
                },
            }
        )

        self.assertEqual(normalized["owner"], "packet-p01")
        self.assertEqual(
            normalized["artifacts"],
            {
                "image_source": {"relative_path": "assets/media/diagram.png"},
            },
        )
        self.assertEqual(
            normalized["staged"],
            {
                "pending_output": {
                    "relative_path": ".staging/outputs/run.txt",
                    "slot": "process_run.stdout",
                }
            },
        )

    def test_store_resolves_managed_and_staged_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "demo.sfe"
            store = ProjectArtifactStore(
                project_path=project_path,
                metadata={
                    "artifacts": {
                        "image_source": {"relative_path": "assets/media/diagram.png"},
                    },
                    "staged": {
                        "pending_output": {"relative_path": ".staging/outputs/run.txt"},
                    },
                },
            )

            self.assertEqual(
                store.resolve_managed_path("image_source"),
                project_path.with_name("demo.data") / "assets" / "media" / "diagram.png",
            )
            self.assertEqual(
                store.resolve_managed_path(format_managed_artifact_ref("image_source")),
                project_path.with_name("demo.data") / "assets" / "media" / "diagram.png",
            )
            self.assertEqual(
                store.resolve_staged_path(format_staged_artifact_ref("pending_output")),
                project_path.with_name("demo.data") / ".staging" / "outputs" / "run.txt",
            )

    def test_project_metadata_helper_extracts_normalized_artifact_store_state(self) -> None:
        project_metadata = {
            "artifact_store": {
                "artifacts": {
                    "generated_output": {
                        "root": "artifacts",
                        "path": "reports/result.csv",
                    }
                }
            }
        }

        self.assertEqual(
            artifact_store_metadata_from_project_metadata(project_metadata),
            {
                "artifacts": {
                    "generated_output": {
                        "relative_path": "artifacts/reports/result.csv",
                    }
                },
                "staged": {},
            },
        )
        self.assertEqual(
            ArtifactStoreState.from_metadata(project_metadata["artifact_store"]).to_metadata(),
            {
                "artifacts": {
                    "generated_output": {
                        "relative_path": "artifacts/reports/result.csv",
                    }
                },
                "staged": {},
            },
        )

    def test_artifact_ref_helpers_keep_managed_and_staged_refs_distinct(self) -> None:
        managed = parse_artifact_ref("artifact://diagram_asset")
        staged = parse_artifact_ref("artifact-stage://diagram_asset")

        self.assertEqual(managed, ManagedArtifactRef("diagram_asset"))
        self.assertEqual(staged, StagedArtifactRef("diagram_asset"))
        self.assertEqual(format_managed_artifact_ref("diagram_asset"), "artifact://diagram_asset")
        self.assertEqual(format_staged_artifact_ref("diagram_asset"), "artifact-stage://diagram_asset")


if __name__ == "__main__":
    unittest.main()
