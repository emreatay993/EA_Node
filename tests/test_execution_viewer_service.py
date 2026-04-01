from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

from ea_node_editor.execution.dpf_runtime.viewer_session_backend import (
    ViewerSessionMaterializationResult,
)
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_VIEWER_DATASET_HANDLE_KIND,
    DpfMaterializationResult,
)
from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.execution.protocol import (
    CloseViewerSessionCommand,
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    UpdateViewerSessionCommand,
    ViewerDataMaterializedEvent,
    ViewerSessionFailedEvent,
    ViewerSessionOpenedEvent,
    ViewerSessionUpdatedEvent,
    event_to_dict,
)
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.types import RuntimeArtifactRef


class _FakeDpfObject:
    def __init__(self, label: str) -> None:
        self.label = label

    def __repr__(self) -> str:
        return f"RAW<{self.label}>"


class ViewerSessionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.services = WorkerServices()
        self.service = self.services.viewer_session_service

    def _fake_materialize(self, calls: list[dict[str, object]]):  # noqa: ANN001
        def _materialize(
            value,  # noqa: ANN001
            *,
            model,  # noqa: ANN001
            mesh=None,  # noqa: ANN001
            output_profile: str,
            camera_state=None,  # noqa: ANN001
            artifact_store=None,  # noqa: ANN001
            artifact_key: str = "",
            export_formats=(),  # noqa: ANN001
            temporary_root_parent=None,  # noqa: ANN001
            run_id: str = "",
            owner_scope: str = "",
        ) -> DpfMaterializationResult:
            resolved_fields = self.services.resolve_handle(value, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND)
            resolved_model = self.services.resolve_handle(model, expected_kind=DPF_MODEL_HANDLE_KIND)
            calls.append(
                {
                    "fields_ref": value,
                    "model_ref": model,
                    "mesh_ref": mesh,
                    "artifact_key": artifact_key,
                    "output_profile": output_profile,
                    "camera_state": dict(camera_state or {}),
                    "export_formats": tuple(export_formats),
                    "artifact_store_present": artifact_store is not None,
                    "temporary_root_parent": temporary_root_parent,
                    "run_id": run_id,
                    "owner_scope": owner_scope,
                    "fields_label": resolved_fields.label,
                    "model_label": resolved_model.label,
                }
            )

            dataset_ref = None
            if output_profile in {"memory", "both"}:
                dataset_ref = self.services.register_handle(
                    _FakeDpfObject(f"dataset:{resolved_fields.label}:{resolved_model.label}"),
                    kind=DPF_VIEWER_DATASET_HANDLE_KIND,
                    owner_scope=owner_scope or "cache:tests:viewer_materialized",
                    metadata={"dataset_type": "fake_dataset", "array_names": ["U"]},
                )

            artifacts = {}
            if output_profile in {"stored", "both"}:
                artifacts["png"] = RuntimeArtifactRef.staged(
                    "viewer_preview_png",
                    metadata={"format": "png"},
                )

            return DpfMaterializationResult(
                output_profile=output_profile,
                dataset_ref=dataset_ref,
                artifacts=artifacts,
                summary={
                    "result_name": "displacement",
                    "field_count": 2,
                    "artifact_key": artifact_key,
                },
            )

        return _materialize

    @staticmethod
    def _fake_export_transport_bundle(
        _value,  # noqa: ANN001
        *,
        model,  # noqa: ANN001
        bundle_root,
        mesh=None,  # noqa: ANN001
        workspace_id: str = "",
        session_id: str = "",
        transport_revision: int = 0,
    ) -> dict[str, object]:
        root_path = Path(bundle_root)
        dataset_dir = root_path / "dataset"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        entry_file = "dataset/dataset.vtm"
        entry_path = root_path / entry_file
        entry_path.write_text("fake transport bundle", encoding="utf-8")
        manifest_path = root_path / "transport_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema": "ea.dpf.viewer_transport_bundle.v1",
                    "workspace_id": workspace_id,
                    "session_id": session_id,
                    "transport_revision": transport_revision,
                    "entry_file": entry_file,
                    "files": [entry_file],
                    "metadata": {
                        "model": repr(model),
                        "has_mesh": mesh is not None,
                    },
                },
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "kind": "dpf_transport_bundle",
            "version": 1,
            "schema": "ea.dpf.viewer_transport_bundle.v1",
            "manifest_path": str(manifest_path),
            "bundle_root": str(root_path),
            "entry_file": entry_file,
            "entry_path": str(entry_path),
            "files": [entry_file],
            "metadata": {
                "model": repr(model),
                "has_mesh": mesh is not None,
            },
        }

    def test_open_update_materialize_close_and_reopen_session_with_run_scoped_handles(self) -> None:
        calls: list[dict[str, object]] = []
        with (
            mock.patch.object(
                self.services.dpf_runtime_service,
                "materialize_viewer_dataset",
                side_effect=self._fake_materialize(calls),
            ),
            mock.patch.object(
                self.services.dpf_runtime_service,
                "export_viewer_transport_bundle",
                side_effect=self._fake_export_transport_bundle,
            ),
        ):
            fields_ref = self.services.register_handle(
                _FakeDpfObject("fields_run"),
                kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                run_id="run_viewer_service",
            )
            model_ref = self.services.register_handle(
                _FakeDpfObject("model_run"),
                kind=DPF_MODEL_HANDLE_KIND,
                run_id="run_viewer_service",
            )

            opened = self.service.open_session(
                OpenViewerSessionCommand(
                    request_id="viewer_req_open",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                    data_refs={"fields": fields_ref, "model": model_ref},
                    summary={"result_name": "displacement"},
                    options={"live_mode": "full"},
                )
            )

            self.assertIsInstance(opened, ViewerSessionOpenedEvent)
            self.assertEqual(opened.session_id, "session_live")
            self.assertEqual(opened.data_refs, {})
            self.assertEqual(opened.backend_id, DPF_EXECUTION_VIEWER_BACKEND_ID)
            self.assertTrue(opened.summary["has_source_data"])
            self.assertEqual(opened.options["live_mode"], "proxy")
            self.assertEqual(opened.live_open_status, "blocked")
            self.assertEqual(opened.live_open_blocker["code"], "transport_not_ready")

            self.services.cleanup_run("run_viewer_service")
            with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
                self.services.resolve_handle(fields_ref)
            with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
                self.services.resolve_handle(model_ref)

            updated = self.service.update_session(
                UpdateViewerSessionCommand(
                    request_id="viewer_req_update",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                    summary={"camera": {"zoom": 1.2}},
                    options={"selection": {"set_ids": [2]}},
                )
            )

            self.assertIsInstance(updated, ViewerSessionUpdatedEvent)
            self.assertEqual(updated.summary["camera"], {"zoom": 1.2})
            self.assertEqual(updated.options["selection"], {"set_ids": [2]})

            materialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                    options={"output_profile": "both", "export_formats": ["png"]},
                )
            )

            self.assertIsInstance(materialized, ViewerDataMaterializedEvent)
            if not isinstance(materialized, ViewerDataMaterializedEvent):
                self.fail("Expected viewer_data_materialized event")

            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["output_profile"], "both")
            self.assertEqual(calls[0]["artifact_key"], "node_viewer_session_live")
            self.assertEqual(calls[0]["export_formats"], ("png",))
            self.assertEqual(calls[0]["owner_scope"], "cache:viewer_session:ws_main:session_live")
            self.assertNotEqual(calls[0]["fields_ref"].owner_scope, "run:run_viewer_service")  # type: ignore[index]
            self.assertNotEqual(calls[0]["model_ref"].owner_scope, "run:run_viewer_service")  # type: ignore[index]

            dataset_ref = materialized.data_refs["dataset"]
            transport_manifest_path = Path(materialized.transport["manifest_path"])
            transport_entry_path = Path(materialized.transport["entry_path"])
            self.assertEqual(materialized.backend_id, DPF_EXECUTION_VIEWER_BACKEND_ID)
            self.assertEqual(materialized.transport["kind"], "dpf_transport_bundle")
            self.assertEqual(materialized.transport["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
            self.assertTrue(transport_manifest_path.is_file())
            self.assertTrue(transport_entry_path.is_file())
            self.assertGreaterEqual(materialized.transport_revision, 1)
            self.assertEqual(materialized.live_open_status, "ready")
            self.assertEqual(dataset_ref.kind, DPF_VIEWER_DATASET_HANDLE_KIND)
            self.assertEqual(dataset_ref.owner_scope, "cache:viewer_session:ws_main:session_live")
            self.assertEqual(materialized.data_refs["png"].artifact_id, "viewer_preview_png")
            self.assertEqual(materialized.options["live_mode"], "full")
            rematerialized_cached = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize_cached",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                    options={"output_profile": "both", "export_formats": ["png"]},
                )
            )
            self.assertIsInstance(rematerialized_cached, ViewerDataMaterializedEvent)
            if not isinstance(rematerialized_cached, ViewerDataMaterializedEvent):
                self.fail("Expected cached viewer_data_materialized event")
            self.assertEqual(len(calls), 1)
            self.assertEqual(rematerialized_cached.transport_revision, materialized.transport_revision)
            payload = event_to_dict(materialized)
            encoded_payload = json.dumps(payload, sort_keys=True)
            self.assertNotIn("RAW<fields_run>", encoded_payload)
            self.assertNotIn("RAW<model_run>", encoded_payload)

            closed = self.service.close_session(
                CloseViewerSessionCommand(
                    request_id="viewer_req_close",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                    options={"reason": "node_hidden", "release_handles": True},
                )
            )

            self.assertEqual(closed.summary["close_reason"], "node_hidden")
            self.assertEqual(closed.options["session_state"], "closed")
            with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
                self.services.resolve_handle(dataset_ref)
            self.assertFalse(transport_manifest_path.exists())
            self.assertFalse(transport_entry_path.exists())

            reopened = self.service.open_session(
                OpenViewerSessionCommand(
                    request_id="viewer_req_reopen",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                )
            )

            self.assertEqual(reopened.options["live_mode"], "proxy")
            self.assertEqual(reopened.live_open_status, "blocked")
            self.assertEqual(reopened.live_open_blocker["code"], "rerun_required")
            rematerialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_rematerialize",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                    options={"output_profile": "memory"},
                )
            )
            self.assertIsInstance(rematerialized, ViewerDataMaterializedEvent)
            if not isinstance(rematerialized, ViewerDataMaterializedEvent):
                self.fail("Expected rematerialized event")
            self.assertIn("dataset", rematerialized.data_refs)
            self.assertNotEqual(rematerialized.data_refs["dataset"].handle_id, dataset_ref.handle_id)

    def test_materialize_routes_backend_specific_dpf_work_through_backend_helper(self) -> None:
        self.service.prepare_workspace_context(
            workspace_id="ws_main",
            project_path="viewer_backend_demo.sfe",
        )
        self.service.open_session(
            OpenViewerSessionCommand(
                request_id="viewer_req_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_backend",
                data_refs={"fields": "fields_source", "model": "model_source"},
                options={"output_profile": "both"},
            )
        )
        dataset_ref = self.services.register_handle(
            _FakeDpfObject("dataset_backend"),
            kind=DPF_VIEWER_DATASET_HANDLE_KIND,
            owner_scope="cache:tests:viewer_backend",
        )
        png_ref = RuntimeArtifactRef.staged(
            "viewer_backend_png",
            metadata={"format": "png"},
        )

        with mock.patch.object(
            self.service._materialization_backend,
            "materialize",
            return_value=ViewerSessionMaterializationResult(
                data_refs={"dataset": dataset_ref, "png": png_ref},
                transport={
                    "kind": "dpf_transport_bundle",
                    "manifest_path": str(Path(__file__).resolve()),
                    "entry_path": str(Path(__file__).resolve()),
                },
                transport_revision=3,
                live_open_status="ready",
                summary={"result_name": "displacement"},
            ),
        ) as materialize:
            materialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_backend",
                    options={"output_profile": "both", "export_formats": ["png"]},
                )
            )

        self.assertIsInstance(materialized, ViewerDataMaterializedEvent)
        if not isinstance(materialized, ViewerDataMaterializedEvent):
            self.fail("Expected viewer_data_materialized event")

        request = materialize.call_args.args[0]
        self.assertEqual(request.workspace_id, "ws_main")
        self.assertEqual(request.node_id, "node_viewer")
        self.assertEqual(request.session_id, "session_backend")
        self.assertEqual(request.source_refs, {"fields": "fields_source", "model": "model_source"})
        self.assertEqual(request.output_profile, "both")
        self.assertEqual(request.camera_state, {})
        self.assertEqual(request.export_formats, ("png",))
        self.assertEqual(request.project_path, "viewer_backend_demo.sfe")
        self.assertEqual(materialized.data_refs["dataset"], dataset_ref)
        self.assertEqual(materialized.data_refs["png"], png_ref)
        self.assertEqual(materialized.transport_revision, 3)
        self.assertEqual(materialized.live_open_status, "ready")

    def test_materialize_passes_record_camera_state_into_backend_request(self) -> None:
        self.service.open_session(
            OpenViewerSessionCommand(
                request_id="viewer_req_open_camera",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_camera",
                data_refs={"fields": "fields_source", "model": "model_source"},
                summary={"camera": {"position": [1.0, 2.0, 3.0]}},
            )
        )
        self.service.update_session(
            UpdateViewerSessionCommand(
                request_id="viewer_req_update_camera",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_camera",
                camera_state={
                    "position": [9.0, 8.0, 7.0],
                    "focal_point": [0.0, 0.0, 0.0],
                    "viewup": [0.0, 1.0, 0.0],
                },
            )
        )

        with mock.patch.object(
            self.service._materialization_backend,
            "materialize",
            return_value=ViewerSessionMaterializationResult(),
        ) as materialize:
            materialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize_camera",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_camera",
                    options={"output_profile": "stored", "export_formats": ["png"]},
                )
            )

        self.assertIsInstance(materialized, ViewerDataMaterializedEvent)
        request = materialize.call_args.args[0]
        self.assertEqual(
            request.camera_state,
            {
                "position": [9.0, 8.0, 7.0],
                "focal_point": [0.0, 0.0, 0.0],
                "viewup": [0.0, 1.0, 0.0],
            },
        )

    def test_materialize_marks_rerun_required_when_transport_bundle_export_fails(self) -> None:
        calls: list[dict[str, object]] = []
        fields_ref = self.services.register_handle(
            _FakeDpfObject("fields_blocked"),
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:tests:viewer_fields_blocked",
        )
        model_ref = self.services.register_handle(
            _FakeDpfObject("model_blocked"),
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="cache:tests:viewer_model_blocked",
        )

        self.service.open_session(
            OpenViewerSessionCommand(
                request_id="viewer_req_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_blocked_transport",
                data_refs={"fields": fields_ref, "model": model_ref},
                options={"live_mode": "full"},
            )
        )

        with (
            mock.patch.object(
                self.services.dpf_runtime_service,
                "materialize_viewer_dataset",
                side_effect=self._fake_materialize(calls),
            ),
            mock.patch.object(
                self.services.dpf_runtime_service,
                "export_viewer_transport_bundle",
                side_effect=RuntimeError("bundle export failed"),
            ),
        ):
            materialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_blocked_transport",
                    options={"output_profile": "memory"},
                )
            )

            self.assertIsInstance(materialized, ViewerDataMaterializedEvent)
            if not isinstance(materialized, ViewerDataMaterializedEvent):
                self.fail("Expected viewer_data_materialized event")

            self.assertEqual(materialized.transport["kind"], "dpf_transport_bundle")
            self.assertFalse(materialized.transport.get("manifest_path"))
            self.assertFalse(materialized.transport.get("entry_path"))
            self.assertEqual(materialized.live_open_status, "blocked")
            self.assertEqual(materialized.live_open_blocker["code"], "rerun_required")
            self.assertEqual(materialized.summary["cache_state"], "proxy_ready")
            self.assertEqual(materialized.options["cache_state"], "proxy_ready")
            self.assertTrue(materialized.options["rerun_required"])

            rematerialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize_retry",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_blocked_transport",
                    options={"output_profile": "memory"},
                )
            )

        self.assertIsInstance(rematerialized, ViewerDataMaterializedEvent)
        self.assertEqual(len(calls), 2)

    def test_open_session_demotes_stale_materialized_handles_to_proxy_state(self) -> None:
        calls: list[dict[str, object]] = []
        with (
            mock.patch.object(
                self.services.dpf_runtime_service,
                "materialize_viewer_dataset",
                side_effect=self._fake_materialize(calls),
            ),
            mock.patch.object(
                self.services.dpf_runtime_service,
                "export_viewer_transport_bundle",
                side_effect=self._fake_export_transport_bundle,
            ),
        ):
            fields_ref = self.services.register_handle(
                _FakeDpfObject("fields_cached"),
                kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                owner_scope="cache:tests:viewer_fields",
            )
            model_ref = self.services.register_handle(
                _FakeDpfObject("model_cached"),
                kind=DPF_MODEL_HANDLE_KIND,
                owner_scope="cache:tests:viewer_model",
            )

            self.service.open_session(
                OpenViewerSessionCommand(
                    request_id="viewer_req_open",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_stale",
                    data_refs={"fields": fields_ref, "model": model_ref},
                )
            )
            materialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_stale",
                    options={"output_profile": "memory"},
                )
            )

            self.assertIsInstance(materialized, ViewerDataMaterializedEvent)
            if not isinstance(materialized, ViewerDataMaterializedEvent):
                self.fail("Expected viewer_data_materialized event")
            dataset_ref = materialized.data_refs["dataset"]
            self.assertTrue(self.services.release_handle(dataset_ref))

            reopened = self.service.open_session(
                OpenViewerSessionCommand(
                    request_id="viewer_req_reopen",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_stale",
                )
            )

            self.assertIsInstance(reopened, ViewerSessionOpenedEvent)
            self.assertNotIn("dataset", reopened.data_refs)
            self.assertEqual(reopened.options["live_mode"], "proxy")
            self.assertIn("dataset", reopened.summary["stale_ref_keys"])

    def test_materialize_fails_after_workspace_invalidation(self) -> None:
        fields_ref = self.services.register_handle(
            _FakeDpfObject("fields_cached"),
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:tests:viewer_fields",
        )
        model_ref = self.services.register_handle(
            _FakeDpfObject("model_cached"),
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="cache:tests:viewer_model",
        )

        self.service.open_session(
            OpenViewerSessionCommand(
                request_id="viewer_req_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_invalidated",
                data_refs={"fields": fields_ref, "model": model_ref},
            )
        )
        self.service.prepare_workspace_context(
            workspace_id="ws_main",
            invalidate_existing=True,
        )

        failed = self.service.materialize_data(
            MaterializeViewerDataCommand(
                request_id="viewer_req_materialize",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_invalidated",
            )
        )

        self.assertIsInstance(failed, ViewerSessionFailedEvent)
        self.assertIn("invalidated", failed.error)


if __name__ == "__main__":
    unittest.main()
