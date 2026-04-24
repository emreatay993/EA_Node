from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ea_node_editor.execution.protocol import (
    NodeCompletedEvent,
    StartRunCommand,
    command_to_dict,
    coerce_start_run_command,
    dict_to_command,
    dict_to_event,
    event_to_dict,
)
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    RuntimeSnapshotContext,
)
from ea_node_editor.execution.runtime_dto import RuntimeWorkspace
from ea_node_editor.execution.runtime_value_codec import (
    deserialize_runtime_value,
    serialize_runtime_value,
)
from ea_node_editor.nodes.builtins.integrations import FileReadNodePlugin, FileWriteNodePlugin
from ea_node_editor.nodes.types import ExecutionContext, RuntimeArtifactRef
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore


class ExecutionArtifactRefProtocolTests(unittest.TestCase):
    def test_runtime_artifact_payload_shape_stays_wire_compatible_through_codec(self) -> None:
        payload = {
            "__ea_runtime_value__": "artifact_ref",
            "ref": "artifact-stage://stored_stdout",
            "artifact_id": "stored_stdout",
            "scope": "staged",
            "metadata": {"line_count": 4},
        }

        restored = deserialize_runtime_value(payload)
        self.assertIsInstance(restored, RuntimeArtifactRef)
        self.assertEqual(
            serialize_runtime_value(restored),
            payload,
        )

    def test_node_completed_event_round_trips_runtime_artifact_ref_payloads(self) -> None:
        event = NodeCompletedEvent(
            run_id="run_artifact",
            workspace_id="ws_main",
            node_id="node_process",
            outputs={
                "stdout": RuntimeArtifactRef.staged("stored_stdout"),
                "preview": "inline preview",
            },
        )

        payload = event_to_dict(event)

        self.assertEqual(
            payload["outputs"]["stdout"],
            {
                "__ea_runtime_value__": "artifact_ref",
                "ref": "artifact-stage://stored_stdout",
                "artifact_id": "stored_stdout",
                "scope": "staged",
            },
        )
        self.assertEqual(payload["outputs"]["preview"], "inline preview")

        restored = dict_to_event(payload)
        self.assertIsInstance(restored.outputs["stdout"], RuntimeArtifactRef)
        self.assertEqual(restored.outputs["stdout"].ref, "artifact-stage://stored_stdout")
        self.assertEqual(restored.outputs["preview"], "inline preview")

    def test_start_run_command_round_trips_runtime_snapshot_artifact_payloads(self) -> None:
        snapshot = RuntimeSnapshot(
            schema_version=1,
            project_id="project_demo",
            metadata={
                "artifact_cache": {
                    "stdout": RuntimeArtifactRef.managed("stored_report"),
                }
            },
        )
        command = StartRunCommand(
            run_id="run_demo",
            workspace_id="ws_main",
            trigger={"kind": "manual"},
            runtime_snapshot=snapshot,
        )

        payload = command_to_dict(command)

        self.assertEqual(
            payload["runtime_snapshot"]["metadata"]["artifact_cache"]["stdout"],
            {
                "__ea_runtime_value__": "artifact_ref",
                "ref": "artifact://stored_report",
                "artifact_id": "stored_report",
                "scope": "managed",
            },
        )

        restored = dict_to_command(payload)
        self.assertIsNotNone(restored.runtime_snapshot)
        if restored.runtime_snapshot is None:
            self.fail("runtime snapshot was not restored")
        restored_ref = restored.runtime_snapshot.metadata["artifact_cache"]["stdout"]
        self.assertIsInstance(restored_ref, RuntimeArtifactRef)
        self.assertEqual(restored_ref.ref, "artifact://stored_report")

    def test_runtime_snapshot_preserves_queue_safe_metadata_artifact_refs(self) -> None:
        snapshot = RuntimeSnapshot(
            schema_version=1,
            project_id="project_artifacts",
            metadata={
                "artifact_cache": {
                    "stdout": RuntimeArtifactRef.managed("stored_report"),
                    "preview": RuntimeArtifactRef.staged("preview_png"),
                }
            },
        )

        self.assertEqual(
            snapshot.to_document()["metadata"]["artifact_cache"],
            {
                "stdout": {
                    "__ea_runtime_value__": "artifact_ref",
                    "ref": "artifact://stored_report",
                    "artifact_id": "stored_report",
                    "scope": "managed",
                },
                "preview": {
                    "__ea_runtime_value__": "artifact_ref",
                    "ref": "artifact-stage://preview_png",
                    "artifact_id": "preview_png",
                    "scope": "staged",
                },
            },
        )

    def test_start_run_command_requires_runtime_snapshot_payload(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires runtime_snapshot"):
            coerce_start_run_command(
                {
                    "run_id": "run_missing_snapshot",
                    "workspace_id": "ws_main",
                    "project_path": "demo.sfe",
                    "trigger": {"kind": "manual"},
                }
            )

    def test_runtime_snapshot_mapping_requires_workspace_order(self) -> None:
        with self.assertRaisesRegex(ValueError, "workspace_order"):
            RuntimeSnapshot.from_mapping(
                {
                    "schema_version": 1,
                    "project_id": "project_demo",
                    "active_workspace_id": "ws_main",
                    "workspaces": [],
                    "metadata": {},
                }
            )

    def test_runtime_workspace_mapping_requires_document_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "document_fields"):
            RuntimeWorkspace.from_mapping(
                {
                    "workspace_id": "ws_main",
                    "name": "Main",
                    "nodes": [],
                    "edges": [],
                }
            )

    def test_execution_context_resolves_runtime_artifact_inputs_through_project_artifact_resolver(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_path = Path(temp_dir) / "stored_stdout.txt"
            artifact_path.write_text("stored output", encoding="utf-8")
            resolver = ProjectArtifactResolver(
                project_path=None,
                project_metadata={
                    "artifact_store": {
                        "artifacts": {},
                        "staged": {
                            "stored_stdout": {
                                "absolute_path": str(artifact_path),
                            }
                        },
                    }
                },
            )
            ctx = ExecutionContext(
                run_id="run_demo",
                node_id="node_consumer",
                workspace_id="ws_main",
                inputs={"artifact": RuntimeArtifactRef.staged("stored_stdout")},
                properties={},
                emit_log=lambda _level, _message: None,
                path_resolver=resolver.resolve_to_path,
            )

            self.assertEqual(ctx.resolve_input_path("artifact"), artifact_path)
            self.assertEqual(
                ctx.resolve_path_value("artifact-stage://stored_stdout"),
                artifact_path,
            )

    def test_file_write_managed_output_updates_runtime_store_and_downstream_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "managed_output_demo.sfe"
            runtime_snapshot = RuntimeSnapshot(
                schema_version=1,
                project_id="project_demo",
                metadata={},
            )
            artifact_store = ProjectArtifactStore.from_project_metadata(
                project_path=project_path,
                project_metadata=runtime_snapshot.metadata,
            )
            runtime_snapshot_context = RuntimeSnapshotContext.from_snapshot(
                runtime_snapshot,
                project_path=str(project_path),
                artifact_store=artifact_store,
            )
            resolver = ProjectArtifactResolver(
                project_path=project_path,
                artifact_store=artifact_store,
            )

            write_ctx = ExecutionContext(
                run_id="run_demo",
                node_id="node_writer",
                workspace_id="ws_main",
                inputs={"text": "managed output"},
                properties={"path": "", "as_json": False},
                emit_log=lambda _level, _message: None,
                trigger={},
                project_path=str(project_path),
                runtime_snapshot=runtime_snapshot,
                runtime_snapshot_context=runtime_snapshot_context,
                path_resolver=resolver.resolve_to_path,
            )

            write_result = FileWriteNodePlugin().execute(write_ctx)

            written_ref = write_result.outputs["written_path"]
            self.assertIsInstance(written_ref, RuntimeArtifactRef)
            if not isinstance(written_ref, RuntimeArtifactRef):
                self.fail("managed output did not return a runtime artifact ref")
            self.assertEqual(written_ref.scope, "staged")

            staged_path = resolver.resolve_to_path(written_ref.ref)
            if staged_path is None:
                self.fail("managed output artifact ref did not resolve to a staged file")
            self.assertTrue(staged_path.exists())
            self.assertEqual(staged_path.read_text(encoding="utf-8"), "managed output")
            self.assertEqual(runtime_snapshot.metadata, {})
            self.assertIn(
                written_ref.artifact_id,
                runtime_snapshot_context.project_metadata()["artifact_store"]["staged"],
            )

            read_ctx = ExecutionContext(
                run_id="run_demo",
                node_id="node_reader",
                workspace_id="ws_main",
                inputs={"path": written_ref},
                properties={"path": ""},
                emit_log=lambda _level, _message: None,
                trigger={},
                project_path=str(project_path),
                runtime_snapshot=runtime_snapshot,
                runtime_snapshot_context=runtime_snapshot_context,
                path_resolver=resolver.resolve_to_path,
            )

            read_result = FileReadNodePlugin().execute(read_ctx)
            self.assertEqual(read_result.outputs["text"], "managed output")


if __name__ == "__main__":
    unittest.main()
