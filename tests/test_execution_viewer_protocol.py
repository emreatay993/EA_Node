from __future__ import annotations

import unittest
from pathlib import Path

from ea_node_editor.execution.protocol import (
    CloseViewerSessionCommand,
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    ProtocolErrorEvent,
    ViewerDataMaterializedEvent,
    ViewerSessionClosedEvent,
    ViewerSessionFailedEvent,
    ViewerSessionOpenedEvent,
    ViewerSessionUpdatedEvent,
    UpdateViewerSessionCommand,
    command_to_dict,
    dict_to_command,
    dict_to_event,
    event_to_dict,
)
from ea_node_editor.nodes.types import RuntimeArtifactRef, RuntimeHandleRef


class _FakeDpfObject:
    pass


class ViewerExecutionProtocolTests(unittest.TestCase):
    def test_dpf_viewer_protocol_edge_is_owned_by_adapter_module(self) -> None:
        builtins_dir = Path(__file__).resolve().parents[1] / "ea_node_editor" / "nodes" / "builtins"
        ansys_dpf_text = (builtins_dir / "ansys_dpf.py").read_text(encoding="utf-8")
        viewer_text = (builtins_dir / "ansys_dpf_viewer.py").read_text(encoding="utf-8")
        adapter_text = (builtins_dir / "ansys_dpf_viewer_adapter.py").read_text(encoding="utf-8")

        self.assertNotIn("from ea_node_editor.execution.protocol import", ansys_dpf_text)
        self.assertNotIn("from ea_node_editor.execution.protocol import", viewer_text)
        self.assertIn("from ea_node_editor.execution.protocol import", adapter_text)

    def test_viewer_command_family_round_trips_runtime_refs_and_options(self) -> None:
        shared_handle = RuntimeHandleRef(
            handle_id="viewer_dataset_001",
            kind="dpf.viewer_dataset",
            owner_scope="workspace:ws_main",
            worker_generation=5,
            metadata={"array_names": ["U"]},
        )
        preview_artifact = RuntimeArtifactRef.managed(
            "viewer_preview_png",
            metadata={"format": "png"},
        )

        commands = [
            OpenViewerSessionCommand(
                request_id="viewer_req_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_existing",
                data_refs={
                    "dataset": shared_handle,
                    "preview": preview_artifact,
                },
                summary={"result_name": "displacement", "set_ids": [1, 2]},
                options={"live_mode": "proxy", "focus_only": True},
            ),
            UpdateViewerSessionCommand(
                request_id="viewer_req_update",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_existing",
                data_refs={"dataset": shared_handle},
                summary={"camera": {"position": [1.0, 2.0, 3.0]}},
                options={"selection": {"set_ids": [2]}},
            ),
            CloseViewerSessionCommand(
                request_id="viewer_req_close",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_existing",
                options={"reason": "node_hidden"},
            ),
            MaterializeViewerDataCommand(
                request_id="viewer_req_materialize",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_existing",
                options={"output_profile": "both", "export_formats": ["png", "vtm"]},
            ),
        ]

        for command in commands:
            with self.subTest(command_type=command.type):
                payload = command_to_dict(command)
                self.assertEqual(payload["type"], command.type)
                self.assertEqual(payload["request_id"], command.request_id)
                self.assertEqual(payload["workspace_id"], "ws_main")
                self.assertEqual(payload["node_id"], "node_viewer")
                self.assertEqual(payload["session_id"], "session_existing")

                if "data_refs" in payload:
                    self.assertEqual(
                        payload["data_refs"].get("dataset"),
                        {
                            "__ea_runtime_value__": "handle_ref",
                            "handle_id": "viewer_dataset_001",
                            "kind": "dpf.viewer_dataset",
                            "owner_scope": "workspace:ws_main",
                            "worker_generation": 5,
                            "metadata": {"array_names": ["U"]},
                        },
                    )

                restored = dict_to_command(payload)
                self.assertIsInstance(restored, type(command))
                self.assertEqual(restored.request_id, command.request_id)
                self.assertEqual(restored.workspace_id, command.workspace_id)
                self.assertEqual(restored.node_id, command.node_id)
                self.assertEqual(restored.session_id, command.session_id)

                if isinstance(restored, (OpenViewerSessionCommand, UpdateViewerSessionCommand)):
                    self.assertIsInstance(restored.data_refs["dataset"], RuntimeHandleRef)
                if isinstance(restored, OpenViewerSessionCommand):
                    self.assertIsInstance(restored.data_refs["preview"], RuntimeArtifactRef)

    def test_viewer_event_family_round_trips_runtime_refs_and_summaries(self) -> None:
        dataset_ref = RuntimeHandleRef(
            handle_id="viewer_dataset_live",
            kind="dpf.viewer_dataset",
            owner_scope="viewer:session_live",
            worker_generation=7,
            metadata={"dataset_type": "UnstructuredGrid"},
        )
        staged_png = RuntimeArtifactRef.staged(
            "viewer_png_export",
            metadata={"format": "png"},
        )

        events = [
            ViewerSessionOpenedEvent(
                request_id="viewer_req_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_live",
                data_refs={"dataset": dataset_ref},
                summary={"dataset_type": "UnstructuredGrid", "array_names": ["U"]},
                options={"live_mode": "proxy"},
            ),
            ViewerSessionUpdatedEvent(
                request_id="viewer_req_update",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_live",
                data_refs={"dataset": dataset_ref},
                summary={"camera": {"zoom": 1.25}},
                options={"selection": {"set_ids": [1]}},
            ),
            ViewerSessionClosedEvent(
                request_id="viewer_req_close",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_live",
                summary={"reason": "node_removed"},
                options={"release_handles": True},
            ),
            ViewerDataMaterializedEvent(
                request_id="viewer_req_materialize",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_live",
                data_refs={
                    "dataset": dataset_ref,
                    "png": staged_png,
                },
                summary={"output_profile": "both", "field_count": 2},
                options={"export_formats": ["png"]},
            ),
            ViewerSessionFailedEvent(
                request_id="viewer_req_fail",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_live",
                command="materialize_viewer_data",
                error="viewer session expired",
            ),
        ]

        for event in events:
            with self.subTest(event_type=event.type):
                payload = event_to_dict(event)
                self.assertEqual(payload["type"], event.type)
                restored = dict_to_event(payload)
                self.assertIsInstance(restored, type(event))
                self.assertEqual(restored.request_id, event.request_id)
                self.assertEqual(restored.workspace_id, event.workspace_id)
                self.assertEqual(restored.node_id, event.node_id)
                self.assertEqual(restored.session_id, event.session_id)

                if isinstance(restored, (ViewerSessionOpenedEvent, ViewerSessionUpdatedEvent, ViewerDataMaterializedEvent)):
                    self.assertIsInstance(restored.data_refs["dataset"], RuntimeHandleRef)
                if isinstance(restored, ViewerDataMaterializedEvent):
                    self.assertIsInstance(restored.data_refs["png"], RuntimeArtifactRef)

    def test_protocol_error_event_round_trips_request_correlation(self) -> None:
        event = ProtocolErrorEvent(
            workspace_id="ws_main",
            request_id="viewer_req_fail",
            command="update_viewer_session",
            error="Unknown command type.",
        )

        payload = event_to_dict(event)
        self.assertEqual(payload["request_id"], "viewer_req_fail")
        self.assertEqual(payload["command"], "update_viewer_session")

        restored = dict_to_event(payload)
        self.assertIsInstance(restored, ProtocolErrorEvent)
        self.assertEqual(restored.workspace_id, event.workspace_id)
        self.assertEqual(restored.request_id, event.request_id)
        self.assertEqual(restored.command, event.command)
        self.assertEqual(restored.error, event.error)

    def test_viewer_command_payloads_reject_non_json_safe_objects(self) -> None:
        command = OpenViewerSessionCommand(
            request_id="viewer_req_bad",
            workspace_id="ws_main",
            node_id="node_viewer",
            data_refs={"raw_dpf_object": _FakeDpfObject()},
        )

        with self.assertRaisesRegex(TypeError, "JSON-safe"):
            command_to_dict(command)


if __name__ == "__main__":
    unittest.main()
