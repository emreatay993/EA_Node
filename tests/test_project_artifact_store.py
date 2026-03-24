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

    def test_unsaved_store_uses_temp_staging_root_hint_for_relative_staged_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProjectArtifactStore(project_path=None, metadata=None)
            staging_root = store.ensure_staging_root(temporary_root_parent=Path(temp_dir) / "session_staging")
            store.register_staged_entry(
                "pending_output",
                relative_path="outputs/run.txt",
                slot="process_run.stdout",
            )

            self.assertTrue(staging_root.exists())
            self.assertEqual(
                store.metadata["staging_root"],
                {
                    "kind": "session_temp",
                    "absolute_path": str(staging_root),
                },
            )
            self.assertEqual(
                store.resolve_staged_path(format_staged_artifact_ref("pending_output")),
                staging_root / "outputs" / "run.txt",
            )

    def test_register_staged_entry_replaces_existing_slot_and_deletes_prior_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            staging_root = Path(temp_dir) / "session_staging" / "project-123"
            old_path = staging_root / "outputs" / "old.txt"
            old_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.write_text("old", encoding="utf-8")
            store = ProjectArtifactStore(
                project_path=None,
                metadata={
                    "staging_root": {
                        "kind": "session_temp",
                        "absolute_path": str(staging_root),
                    },
                    "staged": {
                        "old_output": {
                            "relative_path": "outputs/old.txt",
                            "slot": "process_run.stdout",
                        }
                    },
                },
            )

            store.register_staged_entry(
                "new_output",
                relative_path="outputs/new.txt",
                slot="process_run.stdout",
            )

            self.assertNotIn("old_output", store.metadata["staged"])
            self.assertEqual(
                store.metadata["staged"]["new_output"],
                {
                    "relative_path": "outputs/new.txt",
                    "slot": "process_run.stdout",
                },
            )
            self.assertFalse(old_path.exists())

    def test_discard_staged_payloads_removes_unsaved_temp_root_and_clears_root_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            staging_root = Path(temp_dir) / "session_staging" / "project-123"
            payload_path = staging_root / "outputs" / "run.txt"
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            payload_path.write_text("payload", encoding="utf-8")
            store = ProjectArtifactStore(
                project_path=None,
                metadata={
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
                },
            )

            removed = store.discard_staged_payloads()

            self.assertTrue(removed)
            self.assertFalse(staging_root.exists())
            self.assertNotIn("staging_root", store.metadata)
            self.assertIn("pending_output", store.metadata["staged"])

    def test_commit_referenced_artifacts_promotes_unsaved_temp_entries_into_first_saved_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            staging_root = Path(temp_dir) / "session_staging" / "project-123"
            staged_path = staging_root / "outputs" / "run.txt"
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_text("staged output", encoding="utf-8")
            project_path = Path(temp_dir) / "projects" / "demo.sfe"
            store = ProjectArtifactStore(
                project_path=project_path,
                metadata={
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
                },
            )

            result = store.commit_referenced_artifacts(referenced_staged_ids={"pending_output"})

            managed_path = project_path.with_name("demo.data") / "artifacts" / "outputs" / "run.txt"
            self.assertEqual(
                result.ref_replacements,
                {
                    format_staged_artifact_ref("pending_output"): format_managed_artifact_ref("pending_output"),
                },
            )
            self.assertEqual(result.promoted_artifact_ids, ("pending_output",))
            self.assertEqual(result.pruned_artifact_ids, ())
            self.assertEqual(result.discarded_staged_ids, ())
            self.assertEqual(managed_path.read_text(encoding="utf-8"), "staged output")
            self.assertFalse(staged_path.exists())
            self.assertFalse(staging_root.exists())
            self.assertEqual(
                store.metadata,
                {
                    "artifacts": {
                        "pending_output": {
                            "relative_path": "artifacts/outputs/run.txt",
                        }
                    },
                    "staged": {},
                },
            )

    def test_commit_referenced_artifacts_replaces_existing_managed_copy_and_prunes_orphans(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "demo.sfe"
            layout = ProjectArtifactLayout.from_project_path(project_path)
            current_managed_path = layout.artifacts_root / "reports" / "result.txt"
            current_managed_path.parent.mkdir(parents=True, exist_ok=True)
            current_managed_path.write_text("old output", encoding="utf-8")
            orphan_path = layout.assets_root / "media" / "unused.png"
            orphan_path.parent.mkdir(parents=True, exist_ok=True)
            orphan_path.write_text("orphan", encoding="utf-8")
            staged_path = layout.staging_root / "reports" / "result.txt"
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_text("new output", encoding="utf-8")
            store = ProjectArtifactStore(
                project_path=project_path,
                metadata={
                    "artifacts": {
                        "current_output": {
                            "relative_path": "artifacts/reports/result.txt",
                        },
                        "orphan_asset": {
                            "relative_path": "assets/media/unused.png",
                        },
                    },
                    "staged": {
                        "current_output": {
                            "relative_path": ".staging/reports/result.txt",
                        }
                    },
                },
            )

            result = store.commit_referenced_artifacts(referenced_staged_ids={"current_output"})

            self.assertEqual(result.promoted_artifact_ids, ("current_output",))
            self.assertEqual(result.pruned_artifact_ids, ("orphan_asset",))
            self.assertEqual(result.discarded_staged_ids, ())
            self.assertEqual(current_managed_path.read_text(encoding="utf-8"), "new output")
            self.assertFalse(staged_path.exists())
            self.assertFalse(orphan_path.exists())
            self.assertEqual(
                store.metadata,
                {
                    "artifacts": {
                        "current_output": {
                            "relative_path": "artifacts/reports/result.txt",
                        }
                    },
                    "staged": {},
                },
            )

    def test_generated_output_style_staged_paths_promote_into_managed_artifacts_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "demo.sfe"
            artifact_id = "generated.ws_main.node_writer.written_path"
            relative_path = f"artifacts/generated/{artifact_id}.txt"
            store = ProjectArtifactStore(project_path=project_path, metadata=None)
            staging_root = store.ensure_staging_root()
            staged_path = staging_root / "artifacts" / "generated" / f"{artifact_id}.txt"
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_text("generated output", encoding="utf-8")

            store.register_staged_entry(
                artifact_id,
                relative_path=relative_path,
                slot=f"ws_main:node_writer:{artifact_id}",
            )

            result = store.commit_referenced_artifacts(referenced_staged_ids={artifact_id})

            managed_path = project_path.with_name("demo.data") / "artifacts" / "generated" / f"{artifact_id}.txt"
            self.assertEqual(result.promoted_artifact_ids, (artifact_id,))
            self.assertTrue(managed_path.exists())
            self.assertEqual(managed_path.read_text(encoding="utf-8"), "generated output")
            self.assertEqual(
                store.metadata["artifacts"][artifact_id]["relative_path"],
                relative_path,
            )
            self.assertEqual(store.metadata["staged"], {})

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
