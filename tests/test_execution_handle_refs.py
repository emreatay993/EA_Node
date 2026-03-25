from __future__ import annotations

import unittest

from ea_node_editor.execution.protocol import (
    NodeCompletedEvent,
    StartRunCommand,
    command_to_dict,
    dict_to_command,
    dict_to_event,
    event_to_dict,
)
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot
from ea_node_editor.execution.runtime_value_codec import (
    deserialize_runtime_value,
    serialize_runtime_value,
)
from ea_node_editor.nodes.types import RuntimeHandleRef


class ExecutionHandleRefProtocolTests(unittest.TestCase):
    def test_node_completed_event_round_trips_runtime_handle_ref_payloads(self) -> None:
        event = NodeCompletedEvent(
            run_id="run_handle",
            workspace_id="ws_main",
            node_id="node_export",
            outputs={
                "mesh_handle": RuntimeHandleRef(
                    handle_id="mesh_001",
                    kind="dpf.mesh",
                    owner_scope="run:run_handle",
                    worker_generation=7,
                    metadata={"label": "primary"},
                ),
            },
        )

        payload = event_to_dict(event)

        self.assertEqual(
            payload["outputs"]["mesh_handle"],
            {
                "__ea_runtime_value__": "handle_ref",
                "handle_id": "mesh_001",
                "kind": "dpf.mesh",
                "owner_scope": "run:run_handle",
                "worker_generation": 7,
                "metadata": {"label": "primary"},
            },
        )

        restored = dict_to_event(payload)
        runtime_ref = restored.outputs["mesh_handle"]
        self.assertIsInstance(runtime_ref, RuntimeHandleRef)
        if not isinstance(runtime_ref, RuntimeHandleRef):
            self.fail("runtime handle ref did not round-trip through NodeCompletedEvent")
        self.assertEqual(runtime_ref.handle_id, "mesh_001")
        self.assertEqual(runtime_ref.kind, "dpf.mesh")
        self.assertEqual(runtime_ref.owner_scope, "run:run_handle")
        self.assertEqual(runtime_ref.worker_generation, 7)
        self.assertEqual(runtime_ref.metadata, {"label": "primary"})

    def test_start_run_command_round_trips_runtime_snapshot_handle_payloads(self) -> None:
        snapshot = RuntimeSnapshot(
            schema_version=1,
            project_id="project_demo",
            metadata={
                "viewer_state": {
                    "field_handle": RuntimeHandleRef(
                        handle_id="field_123",
                        kind="dpf.field",
                        owner_scope="workspace:ws_main",
                        worker_generation=11,
                    )
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
            payload["runtime_snapshot"]["metadata"]["viewer_state"]["field_handle"],
            {
                "__ea_runtime_value__": "handle_ref",
                "handle_id": "field_123",
                "kind": "dpf.field",
                "owner_scope": "workspace:ws_main",
                "worker_generation": 11,
            },
        )

        restored = dict_to_command(payload)
        self.assertIsNotNone(restored.runtime_snapshot)
        if restored.runtime_snapshot is None:
            self.fail("runtime snapshot was not restored")
        restored_ref = restored.runtime_snapshot.metadata["viewer_state"]["field_handle"]
        self.assertIsInstance(restored_ref, RuntimeHandleRef)
        if not isinstance(restored_ref, RuntimeHandleRef):
            self.fail("runtime handle ref did not round-trip through RuntimeSnapshot")
        self.assertEqual(restored_ref.handle_id, "field_123")
        self.assertEqual(restored_ref.kind, "dpf.field")
        self.assertEqual(restored_ref.owner_scope, "workspace:ws_main")
        self.assertEqual(restored_ref.worker_generation, 11)

    def test_deserialize_runtime_value_rejects_unknown_runtime_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported runtime value marker"):
            deserialize_runtime_value(
                {
                    "__ea_runtime_value__": "unknown_ref",
                    "value": "bad",
                }
            )

    def test_deserialize_runtime_value_rejects_incomplete_handle_payload(self) -> None:
        with self.assertRaisesRegex(ValueError, "owner_scope must be a non-empty string"):
            deserialize_runtime_value(
                {
                    "__ea_runtime_value__": "handle_ref",
                    "handle_id": "field_123",
                    "kind": "dpf.field",
                    "worker_generation": 3,
                }
            )

    def test_serialize_runtime_value_rejects_malformed_runtime_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "Runtime value marker must be a non-empty string"):
            serialize_runtime_value(
                {
                    "__ea_runtime_value__": "",
                    "value": "bad",
                }
            )


if __name__ == "__main__":
    unittest.main()
