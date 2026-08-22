from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest import mock

from ea_node_editor.addons.catalog import ANSYS_DPF_ADDON_ID
from ea_node_editor.addons.hot_apply import apply_addon_enabled_state
from ea_node_editor.app_preferences import default_app_preferences_document
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
    QueryViewerSessionCommand,
    UpdateViewerSessionCommand,
    ViewerDataMaterializedEvent,
    ViewerSessionClosedEvent,
    ViewerSessionFailedEvent,
    ViewerSessionOpenedEvent,
    ViewerQueryResultEvent,
    ViewerSessionUpdatedEvent,
    event_to_dict,
)
from ea_node_editor.execution.viewer_backend import (
    ViewerBackendMaterializationResult,
    ViewerBackendQueryResult,
)
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.execution.viewer_backend_engineering import (
    ENGINEERING_VIEWER_BACKEND_ID,
)
from ea_node_editor.execution.viewer_session_service import (
    build_run_required_viewer_session_model,
    coerce_viewer_session_model,
)
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_VIEWER_DATASET_DATA_TYPE,
)
from ea_node_editor.runtime_contracts import (
    COREX_VIEWER_SESSION_HANDLE_KIND,
    PATH_DATA_TYPE_ID,
    RuntimeArtifactRef,
    VIEWER_SESSION_DATA_TYPE_ID,
)
from tests.typed_handle_support import dpf_worker_services


class _FakeDpfObject:
    def __init__(self, label: str) -> None:
        self.label = label

    def __repr__(self) -> str:
        return f"RAW<{self.label}>"


class ViewerSessionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.services = dpf_worker_services()
        self.service = self.services.viewer_session_service

    def test_viewer_session_service_facade_stays_within_packet_budget(self) -> None:
        execution_dir = (
            Path(__file__).resolve().parents[1] / "ea_node_editor" / "execution"
        )
        facade_path = execution_dir / "viewer_session_service.py"
        support_path = execution_dir / "viewer_session_service_support.py"
        facade_text = facade_path.read_text(encoding="utf-8")

        self.assertFalse(support_path.exists())
        self.assertNotIn("base64.b85decode", facade_text)
        self.assertNotIn("zlib.decompress", facade_text)
        self.assertIn("class ViewerSessionService", facade_text)

    def test_session_handle_exposes_identity_only_and_resolves_current_projection(
        self,
    ) -> None:
        session_id = "viewer_session_contract"
        self.service.open_session(
            OpenViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id=session_id,
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                summary={"result_name": "displacement"},
                options={"live_mode": "proxy"},
            )
        )

        handle = self.service.session_handle("ws_main", session_id)
        projection = self.services.resolve_handle(
            handle,
            expected_data_type=VIEWER_SESSION_DATA_TYPE_ID,
            expected_kind=COREX_VIEWER_SESSION_HANDLE_KIND,
        )

        self.assertEqual(handle.data_type_id, VIEWER_SESSION_DATA_TYPE_ID)
        self.assertEqual(handle.kind, COREX_VIEWER_SESSION_HANDLE_KIND)
        self.assertEqual(
            handle.metadata,
            {
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "session_id": session_id,
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
            },
        )
        self.assertEqual(projection["session_id"], session_id)
        self.assertEqual(projection["summary"]["result_name"], "displacement")

    def test_viewer_lease_survives_run_cleanup_without_duplicate_updates(
        self,
    ) -> None:
        disposed: list[str] = []
        fields_value = _FakeDpfObject("leased_fields")
        fields_ref = self.services.register_handle(
            fields_value,
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_viewer_lease",
            dispose=lambda: disposed.append("fields"),
        )
        model_ref = self.services.register_handle(
            _FakeDpfObject("leased_model"),
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            run_id="run_viewer_lease",
        )
        command = OpenViewerSessionCommand(
            workspace_id="ws_main",
            node_id="node_viewer",
            session_id="session_lease",
            backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
            data_refs={"fields": fields_ref, "model": model_ref},
        )

        self.service.open_session(command)
        record = self.service._sessions[("ws_main", "session_lease")]  # noqa: SLF001
        viewer_fields_ref = record.source_refs["fields_container"]
        viewer_scope = record.owner_scope

        self.assertEqual(viewer_fields_ref.handle_id, fields_ref.handle_id)
        self.assertEqual(viewer_fields_ref.owner_scope, viewer_scope)
        self.assertEqual(
            self.services.handle_registry.lease_count(
                fields_ref,
                owner_scope=viewer_scope,
            ),
            1,
        )
        self.assertIs(self.services.resolve_handle(fields_ref), fields_value)

        self.service.update_session(
            UpdateViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_lease",
                data_refs={"fields": fields_ref, "model": model_ref},
            )
        )
        self.assertEqual(
            self.services.handle_registry.lease_count(
                fields_ref,
                owner_scope=viewer_scope,
            ),
            1,
        )

        session_projection_ref = self.service.session_handle(
            "ws_main",
            "session_lease",
        )
        self.services.cleanup_run("run_viewer_lease")
        with self.assertRaisesRegex(StaleHandleError, "owner_scope is stale"):
            self.services.resolve_handle(fields_ref)
        self.assertIs(
            self.services.resolve_handle(viewer_fields_ref),
            fields_value,
        )

        closed = self.service.close_session(
            CloseViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_lease",
            )
        )
        closed_again = self.service.close_session(
            CloseViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_lease",
            )
        )

        self.assertEqual(closed.options["session_state"], "closed")
        self.assertEqual(closed_again.options["session_state"], "closed")
        self.assertEqual(disposed, ["fields"])
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            self.services.resolve_handle(viewer_fields_ref)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            self.services.resolve_handle(session_projection_ref)

    def test_viewer_ref_replacement_acquires_new_lease_before_releasing_old(
        self,
    ) -> None:
        session_scope: list[str] = []
        replacement_ref = self.services.register_handle(
            _FakeDpfObject("replacement"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_replace_new",
        )
        observed_new_lease_counts: list[int] = []

        def dispose_previous() -> None:
            observed_new_lease_counts.append(
                self.services.handle_registry.lease_count(
                    replacement_ref,
                    owner_scope=session_scope[0],
                )
            )

        previous_ref = self.services.register_handle(
            _FakeDpfObject("previous"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_replace_old",
            dispose=dispose_previous,
        )
        self.service.open_session(
            OpenViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_replace",
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                data_refs={"fields": previous_ref},
            )
        )
        record = self.service._sessions[("ws_main", "session_replace")]  # noqa: SLF001
        session_scope.append(record.owner_scope)
        self.services.cleanup_run("run_replace_old")

        updated = self.service.update_session(
            UpdateViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_replace",
                data_refs={"fields": replacement_ref},
            )
        )

        record = self.service._sessions[("ws_main", "session_replace")]  # noqa: SLF001
        self.assertIsInstance(updated, ViewerSessionUpdatedEvent)
        self.assertEqual(observed_new_lease_counts, [1])
        self.assertEqual(
            record.source_refs["fields_container"].handle_id,
            replacement_ref.handle_id,
        )

    def test_colliding_external_session_keys_have_distinct_owner_scopes(
        self,
    ) -> None:
        first_ref = self.services.register_handle(
            _FakeDpfObject("first"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_collision_first",
        )
        second_ref = self.services.register_handle(
            _FakeDpfObject("second"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_collision_second",
        )
        for workspace_id, session_id, data_ref in (
            ("a:b", "c", first_ref),
            ("a", "b:c", second_ref),
        ):
            self.service.open_session(
                OpenViewerSessionCommand(
                    workspace_id=workspace_id,
                    node_id="node_viewer",
                    session_id=session_id,
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                    data_refs={"fields": data_ref},
                )
            )

        first_record = self.service._sessions[("a:b", "c")]  # noqa: SLF001
        second_record = self.service._sessions[("a", "b:c")]  # noqa: SLF001
        first_viewer_ref = first_record.source_refs["fields_container"]
        second_viewer_ref = second_record.source_refs["fields_container"]
        self.assertNotEqual(first_record.owner_scope, second_record.owner_scope)

        self.services.cleanup_run("run_collision_first")
        self.services.cleanup_run("run_collision_second")
        self.service.close_session(
            CloseViewerSessionCommand(
                workspace_id="a:b",
                node_id="node_viewer",
                session_id="c",
            )
        )

        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            self.services.resolve_handle(first_viewer_ref)
        self.assertEqual(
            self.services.resolve_handle(second_viewer_ref).label,
            "second",
        )
        self.service.close_session(
            CloseViewerSessionCommand(
                workspace_id="a",
                node_id="node_viewer",
                session_id="b:c",
            )
        )

    def test_alias_inputs_are_deduplicated_before_leasing_and_replacement(
        self,
    ) -> None:
        disposed: list[str] = []
        alias_ref = self.services.register_handle(
            _FakeDpfObject("alias"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_alias",
            dispose=lambda: disposed.append("alias"),
        )
        previous_ref = self.services.register_handle(
            _FakeDpfObject("previous"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_previous",
            dispose=lambda: disposed.append("previous"),
        )
        replacement_ref = self.services.register_handle(
            _FakeDpfObject("replacement"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_replacement",
            dispose=lambda: disposed.append("replacement"),
        )

        self.service.open_session(
            OpenViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_aliases",
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                data_refs={
                    "fields": alias_ref,
                    "fields_container": previous_ref,
                },
            )
        )
        record = self.service._sessions[("ws_main", "session_aliases")]  # noqa: SLF001
        self.assertEqual(
            record.source_refs["fields_container"].handle_id,
            previous_ref.handle_id,
        )
        self.assertEqual(
            self.services.handle_registry.lease_count(
                alias_ref,
                owner_scope=record.owner_scope,
            ),
            0,
        )
        self.assertEqual(
            self.services.handle_registry.lease_count(
                previous_ref,
                owner_scope=record.owner_scope,
            ),
            1,
        )

        self.services.cleanup_run("run_alias")
        self.services.cleanup_run("run_previous")
        self.assertEqual(disposed, ["alias"])

        self.service.update_session(
            UpdateViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_aliases",
                data_refs={
                    "fields": replacement_ref,
                    "fields_container": replacement_ref,
                },
            )
        )
        self.assertEqual(
            self.services.handle_registry.lease_count(
                replacement_ref,
                owner_scope=record.owner_scope,
            ),
            1,
        )
        self.assertEqual(disposed, ["alias", "previous"])

        self.services.cleanup_run("run_replacement")
        self.service.close_session(
            CloseViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_aliases",
            )
        )
        self.assertEqual(disposed, ["alias", "previous", "replacement"])

    def test_explicit_close_reports_disposal_failure_after_complete_cleanup(
        self,
    ) -> None:
        disposed: list[str] = []

        def fail_disposal() -> None:
            disposed.append("failed")
            raise RuntimeError("private disposal detail")

        failing_ref = self.services.register_handle(
            _FakeDpfObject("failing"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            run_id="run_close_failure",
            dispose=fail_disposal,
        )
        successful_ref = self.services.register_handle(
            _FakeDpfObject("successful"),
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            run_id="run_close_failure",
            dispose=lambda: disposed.append("successful"),
        )
        artifact_ref = RuntimeArtifactRef.staged(
            "viewer_close_artifact",
            data_type_id=PATH_DATA_TYPE_ID,
            schema_version=1,
            format="png",
            size_bytes=0,
            sha256="0" * 64,
            provenance="corex.test.fixture",
        )
        other_workspace_ref = self.services.register_handle(
            _FakeDpfObject("other_workspace"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:tests:other_workspace",
        )
        for workspace_id, session_id, refs in (
            (
                "ws_main",
                "session_close_failure",
                {
                    "fields": failing_ref,
                    "model": successful_ref,
                    "png": artifact_ref,
                },
            ),
            (
                "ws_other",
                "session_other",
                {"fields": other_workspace_ref},
            ),
        ):
            self.service.open_session(
                OpenViewerSessionCommand(
                    workspace_id=workspace_id,
                    node_id="node_viewer",
                    session_id=session_id,
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                    data_refs=refs,
                )
            )
        other_record = self.service._sessions[  # noqa: SLF001
            ("ws_other", "session_other")
        ]
        other_viewer_ref = other_record.source_refs["fields_container"]
        self.services.cleanup_run("run_close_failure")

        failed = self.service.close_session(
            CloseViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_close_failure",
            )
        )
        closed_again = self.service.close_session(
            CloseViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_close_failure",
            )
        )

        self.assertCountEqual(disposed, ["failed", "successful"])
        self.assertIsInstance(failed, ViewerSessionFailedEvent)
        self.assertEqual(
            failed.error,
            "Viewer session cleanup failed.",
        )
        self.assertNotIn("private disposal detail", failed.error)
        self.assertIsInstance(closed_again, ViewerSessionClosedEvent)
        self.assertEqual(
            closed_again.options["session_state"],
            "closed",
        )
        closed_record = self.service._sessions[  # noqa: SLF001
            ("ws_main", "session_close_failure")
        ]
        self.assertEqual(closed_record.session_state, "closed")
        self.assertEqual(
            closed_record.summary["cleanup_error"],
            "Runtime handle disposal failed.",
        )
        self.assertEqual(closed_record.materialized_refs["png"], artifact_ref)
        self.assertIs(
            self.services.resolve_handle(other_viewer_ref),
            self.services.resolve_handle(other_workspace_ref),
        )

    def test_invalidation_and_reset_warn_and_continue_across_sessions(self) -> None:
        disposed: list[str] = []

        def failing_dispose() -> None:
            disposed.append("failed")
            raise RuntimeError("automatic cleanup failed")

        refs = (
            self.services.register_handle(
                _FakeDpfObject("failed"),
                data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
                kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                run_id="run_auto_cleanup",
                dispose=failing_dispose,
            ),
            self.services.register_handle(
                _FakeDpfObject("successful"),
                data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
                kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                run_id="run_auto_cleanup",
                dispose=lambda: disposed.append("successful"),
            ),
        )
        for index, runtime_ref in enumerate(refs):
            self.service.open_session(
                OpenViewerSessionCommand(
                    workspace_id="ws_main",
                    node_id=f"node_{index}",
                    session_id=f"session_{index}",
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                    data_refs={"fields": runtime_ref},
                )
            )
        viewer_refs = tuple(
            self.service._sessions[("ws_main", f"session_{index}")].source_refs[  # noqa: SLF001
                "fields_container"
            ]
            for index in range(2)
        )
        self.services.cleanup_run("run_auto_cleanup")

        with self.assertLogs(
            "ea_node_editor.execution.handle_registry",
            level="WARNING",
        ):
            self.service.invalidate_workspace(
                "ws_main",
                reason="workspace_rerun",
            )

        self.assertCountEqual(disposed, ["failed", "successful"])
        for runtime_ref in viewer_refs:
            with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
                self.services.resolve_handle(runtime_ref)

        reset_disposed: list[str] = []

        def failing_reset_dispose() -> None:
            reset_disposed.append("failed")
            raise RuntimeError("reset failure")

        reset_ref = self.services.register_handle(
            _FakeDpfObject("reset_failed"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:tests:reset_failure",
            dispose=failing_reset_dispose,
        )
        self.services.register_handle(
            _FakeDpfObject("reset_successful"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:tests:reset_success",
            dispose=lambda: reset_disposed.append("successful"),
        )
        reset_warnings: list[str] = []
        previous_generation = self.services.worker_generation
        self.services.reset(warn=reset_warnings.append)
        self.assertEqual(self.services.worker_generation, previous_generation + 1)
        self.assertCountEqual(reset_disposed, ["failed", "successful"])
        self.assertEqual(
            reset_warnings,
            ["Runtime handle automatic disposal failed."],
        )
        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            self.services.resolve_handle(reset_ref)

    def test_query_command_returns_serializable_backend_result_with_session_context(
        self,
    ) -> None:
        self.service.open_session(
            OpenViewerSessionCommand(
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_query",
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                summary={"result_name": "displacement"},
                options={"representation": "surface"},
            )
        )
        backend = self.services.viewer_backend_registry.resolve(
            DPF_EXECUTION_VIEWER_BACKEND_ID
        )
        with mock.patch.object(
            backend,
            "query",
            create=True,
            return_value=ViewerBackendQueryResult(
                supported=True,
                value={"distance": 5.0, "length_unit": "mm"},
            ),
        ) as query:
            event = self.service.handle_command(
                QueryViewerSessionCommand(
                    request_id="viewer_req_query",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_query",
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                    query_type="distance",
                    payload={"point_a": [0, 0, 0], "point_b": [3, 4, 0]},
                )
            )

        self.assertIsInstance(event, ViewerQueryResultEvent)
        self.assertTrue(event.supported)
        self.assertEqual(event.value["distance"], 5.0)
        request = query.call_args.args[0]
        self.assertEqual(request.query_type, "distance")
        self.assertEqual(request.session_summary["result_name"], "displacement")
        self.assertEqual(request.session_options["representation"], "surface")

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
            node_workspace_id: str = "",
            node_workspace_name: str = "",
            node_id: str = "",
            node_title: str = "",
            node_type: str = "",
        ) -> DpfMaterializationResult:
            resolved_fields = self.services.resolve_handle(
                value, expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND
            )
            resolved_model = self.services.resolve_handle(
                model, expected_kind=DPF_MODEL_HANDLE_KIND
            )
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
                    _FakeDpfObject(
                        f"dataset:{resolved_fields.label}:{resolved_model.label}"
                    ),
                    data_type_id=DPF_VIEWER_DATASET_DATA_TYPE,
                    kind=DPF_VIEWER_DATASET_HANDLE_KIND,
                    owner_scope=owner_scope or "cache:tests:viewer_materialized",
                    metadata={"dataset_type": "fake_dataset", "array_names": ["U"]},
                )

            artifacts = {}
            if output_profile in {"stored", "both"}:
                artifacts["png"] = RuntimeArtifactRef.staged(
                    "viewer_preview_png",
                    data_type_id=PATH_DATA_TYPE_ID,
                    schema_version=1,
                    format="png",
                    size_bytes=0,
                    sha256="0" * 64,
                    provenance="corex.test.fixture",
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

    def test_open_update_materialize_close_and_reopen_session_with_run_scoped_handles(
        self,
    ) -> None:
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
                data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
                kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                run_id="run_viewer_service",
            )
            model_ref = self.services.register_handle(
                _FakeDpfObject("model_run"),
                data_type_id=DPF_MODEL_DATA_TYPE,
                kind=DPF_MODEL_HANDLE_KIND,
                run_id="run_viewer_service",
            )

            opened = self.service.open_session(
                OpenViewerSessionCommand(
                    request_id="viewer_req_open",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live",
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
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
            self.assertEqual(opened.live_open_blocker["code"], "rerun_required")
            self.assertNotIn("session_model", opened.summary)
            self.assertEqual(opened.summary["result_name"], "displacement")
            viewer_owner_scope = self.service._sessions[  # noqa: SLF001
                ("ws_main", "session_live")
            ].owner_scope

            self.services.cleanup_run("run_viewer_service")
            with self.assertRaisesRegex(StaleHandleError, "owner_scope is stale"):
                self.services.resolve_handle(fields_ref)
            with self.assertRaisesRegex(StaleHandleError, "owner_scope is stale"):
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
            self.assertEqual(calls[0]["owner_scope"], viewer_owner_scope)
            self.assertNotEqual(
                calls[0]["fields_ref"].owner_scope, "run:run_viewer_service"
            )  # type: ignore[index]
            self.assertNotEqual(
                calls[0]["model_ref"].owner_scope, "run:run_viewer_service"
            )  # type: ignore[index]

            dataset_ref = materialized.data_refs["dataset"]
            transport_manifest_path = Path(materialized.transport["manifest_path"])
            transport_entry_path = Path(materialized.transport["entry_path"])
            self.assertEqual(materialized.backend_id, DPF_EXECUTION_VIEWER_BACKEND_ID)
            self.assertEqual(materialized.transport["kind"], "dpf_transport_bundle")
            self.assertEqual(
                materialized.transport["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID
            )
            self.assertTrue(transport_manifest_path.is_file())
            self.assertTrue(transport_entry_path.is_file())
            self.assertGreaterEqual(materialized.transport_revision, 1)
            self.assertEqual(materialized.live_open_status, "ready")
            self.assertEqual(dataset_ref.kind, DPF_VIEWER_DATASET_HANDLE_KIND)
            self.assertEqual(dataset_ref.owner_scope, viewer_owner_scope)
            self.assertEqual(
                materialized.data_refs["png"].artifact_id, "viewer_preview_png"
            )
            self.assertEqual(materialized.options["live_mode"], "full")
            self.assertNotIn("session_model", materialized.summary)
            self.assertEqual(materialized.options["live_mode"], "full")
            self.assertEqual(
                materialized.summary["transport_revision"],
                materialized.transport_revision,
            )
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
            self.assertEqual(
                rematerialized_cached.transport_revision,
                materialized.transport_revision,
            )
            payload = event_to_dict(
                materialized,
                catalog=self.services.data_types,
            )
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
            self.assertNotIn("session_model", closed.summary)
            self.assertEqual(closed.summary["close_reason"], "node_hidden")
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
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
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
            self.assertIsInstance(rematerialized, ViewerSessionFailedEvent)
            self.assertIn("missing cached fields/model refs", rematerialized.error)
            self.assertEqual(len(calls), 1)

    def test_materialize_routes_backend_specific_dpf_work_through_backend_helper(
        self,
    ) -> None:
        self.service.prepare_workspace_context(
            workspace_id="ws_main",
            project_path="viewer_backend_demo.cxproj",
        )
        self.service.open_session(
            OpenViewerSessionCommand(
                request_id="viewer_req_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_backend",
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                data_refs={"fields": "fields_source", "model": "model_source"},
                options={"output_profile": "both"},
            )
        )
        dataset_ref = self.services.register_handle(
            _FakeDpfObject("dataset_backend"),
            data_type_id=DPF_VIEWER_DATASET_DATA_TYPE,
            kind=DPF_VIEWER_DATASET_HANDLE_KIND,
            owner_scope="cache:tests:viewer_backend",
        )
        png_ref = RuntimeArtifactRef.staged(
            "viewer_backend_png",
            data_type_id=PATH_DATA_TYPE_ID,
            schema_version=1,
            format="png",
            size_bytes=0,
            sha256="0" * 64,
            provenance="corex.test.fixture",
        )

        dpf_backend = self.services.viewer_backend_registry.resolve(
            DPF_EXECUTION_VIEWER_BACKEND_ID
        )
        with mock.patch.object(
            dpf_backend,
            "materialize",
            return_value=ViewerBackendMaterializationResult(
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
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
        self.assertEqual(
            request.source_refs,
            {"fields_container": "fields_source", "model": "model_source"},
        )
        self.assertEqual(request.output_profile, "both")
        self.assertEqual(request.session_summary["camera_state"], {})
        self.assertEqual(request.export_formats, ("png",))
        self.assertEqual(request.project_path, "viewer_backend_demo.cxproj")
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
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
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

        dpf_backend = self.services.viewer_backend_registry.resolve(
            DPF_EXECUTION_VIEWER_BACKEND_ID
        )
        with mock.patch.object(
            dpf_backend,
            "materialize",
            return_value=ViewerBackendMaterializationResult(
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
            ),
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
            request.session_summary["camera_state"],
            {
                "position": [9.0, 8.0, 7.0],
                "focal_point": [0.0, 0.0, 0.0],
                "viewup": [0.0, 1.0, 0.0],
            },
        )

    def test_materialize_marks_rerun_required_when_transport_bundle_export_fails(
        self,
    ) -> None:
        calls: list[dict[str, object]] = []
        fields_ref = self.services.register_handle(
            _FakeDpfObject("fields_blocked"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:tests:viewer_fields_blocked",
        )
        model_ref = self.services.register_handle(
            _FakeDpfObject("model_blocked"),
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="cache:tests:viewer_model_blocked",
        )

        self.service.open_session(
            OpenViewerSessionCommand(
                request_id="viewer_req_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_blocked_transport",
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
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

    def test_open_session_demotes_stale_materialized_handles_to_proxy_state(
        self,
    ) -> None:
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
                data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
                kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                owner_scope="cache:tests:viewer_fields",
            )
            model_ref = self.services.register_handle(
                _FakeDpfObject("model_cached"),
                data_type_id=DPF_MODEL_DATA_TYPE,
                kind=DPF_MODEL_HANDLE_KIND,
                owner_scope="cache:tests:viewer_model",
            )

            self.service.open_session(
                OpenViewerSessionCommand(
                    request_id="viewer_req_open",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_stale",
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
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
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                )
            )

            self.assertIsInstance(reopened, ViewerSessionOpenedEvent)
            self.assertNotIn("dataset", reopened.data_refs)
            self.assertEqual(reopened.options["live_mode"], "proxy")
            self.assertIn("dataset", reopened.summary["stale_ref_keys"])

    def test_options_update_preserves_live_transport_without_materialized_refs(
        self,
    ) -> None:
        transport = {
            "kind": "engineering_scene_bundle",
            "backend_id": ENGINEERING_VIEWER_BACKEND_ID,
        }
        opened = self.service.open_session(
            OpenViewerSessionCommand(
                request_id="viewer_req_open_engineering",
                workspace_id="ws_main",
                node_id="node_engineering_viewer",
                session_id="session_engineering",
                backend_id=ENGINEERING_VIEWER_BACKEND_ID,
                transport=transport,
                transport_revision=1,
                live_open_status="ready",
                options={"live_mode": "proxy"},
            )
        )

        self.assertIsInstance(opened, ViewerSessionOpenedEvent)
        updated = self.service.update_session(
            UpdateViewerSessionCommand(
                request_id="viewer_req_focus_engineering",
                workspace_id="ws_main",
                node_id="node_engineering_viewer",
                session_id="session_engineering",
                options={"live_mode": "full"},
            )
        )

        self.assertIsInstance(updated, ViewerSessionUpdatedEvent)
        self.assertEqual(updated.transport, transport)
        self.assertEqual(updated.live_open_status, "ready")
        self.assertEqual(updated.summary["cache_state"], "live_ready")
        self.assertFalse(updated.summary["has_materialized_data"])
        self.assertFalse(updated.options["rerun_required"])
        self.assertEqual(updated.options["live_mode"], "full")

    def test_hot_apply_rebuild_clears_cached_dpf_transport_and_restores_live_materialization(
        self,
    ) -> None:
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
                data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
                kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                owner_scope="cache:tests:viewer_fields",
            )
            model_ref = self.services.register_handle(
                _FakeDpfObject("model_cached"),
                data_type_id=DPF_MODEL_DATA_TYPE,
                kind=DPF_MODEL_HANDLE_KIND,
                owner_scope="cache:tests:viewer_model",
            )

            self.service.open_session(
                OpenViewerSessionCommand(
                    request_id="viewer_req_open",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live_toggle",
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                    data_refs={"fields": fields_ref, "model": model_ref},
                )
            )
            materialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live_toggle",
                    options={"output_profile": "memory"},
                )
            )

            manifest_path = Path(materialized.transport["manifest_path"])
            entry_path = Path(materialized.transport["entry_path"])
            self.assertTrue(manifest_path.is_file())
            self.assertTrue(entry_path.is_file())

            disabled = apply_addon_enabled_state(
                ANSYS_DPF_ADDON_ID,
                enabled=False,
                preferences_document=default_app_preferences_document(),
                worker_services=self.services,
            )

            self.assertFalse(manifest_path.exists())
            self.assertFalse(entry_path.exists())
            with self.assertRaises(LookupError):
                self.services.viewer_backend_registry.resolve(
                    DPF_EXECUTION_VIEWER_BACKEND_ID
                )

            reenabled = apply_addon_enabled_state(
                ANSYS_DPF_ADDON_ID,
                enabled=True,
                preferences_document=disabled.preferences_document,
                worker_services=self.services,
            )

            fields_ref = self.services.register_handle(
                _FakeDpfObject("fields_reenabled"),
                data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
                kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
                owner_scope="cache:tests:viewer_fields_reenabled",
            )
            model_ref = self.services.register_handle(
                _FakeDpfObject("model_reenabled"),
                data_type_id=DPF_MODEL_DATA_TYPE,
                kind=DPF_MODEL_HANDLE_KIND,
                owner_scope="cache:tests:viewer_model_reenabled",
            )
            self.service.open_session(
                OpenViewerSessionCommand(
                    request_id="viewer_req_open_reenabled",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live_toggle_reenabled",
                    backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
                    data_refs={"fields": fields_ref, "model": model_ref},
                )
            )
            rematerialized = self.service.materialize_data(
                MaterializeViewerDataCommand(
                    request_id="viewer_req_materialize_reenabled",
                    workspace_id="ws_main",
                    node_id="node_viewer",
                    session_id="session_live_toggle_reenabled",
                    options={"output_profile": "memory"},
                )
            )

        self.assertEqual(reenabled.apply_policy, "hot_apply")
        self.assertTrue(Path(rematerialized.transport["manifest_path"]).is_file())
        self.assertTrue(Path(rematerialized.transport["entry_path"]).is_file())
        self.assertNotEqual(
            rematerialized.transport["manifest_path"], str(manifest_path)
        )

    def test_materialize_fails_after_workspace_invalidation(self) -> None:
        fields_ref = self.services.register_handle(
            _FakeDpfObject("fields_cached"),
            data_type_id=DPF_FIELDS_CONTAINER_DATA_TYPE,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="cache:tests:viewer_fields",
        )
        model_ref = self.services.register_handle(
            _FakeDpfObject("model_cached"),
            data_type_id=DPF_MODEL_DATA_TYPE,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope="cache:tests:viewer_model",
        )

        self.service.open_session(
            OpenViewerSessionCommand(
                request_id="viewer_req_open",
                workspace_id="ws_main",
                node_id="node_viewer",
                session_id="session_invalidated",
                backend_id=DPF_EXECUTION_VIEWER_BACKEND_ID,
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

    def test_coerce_viewer_session_model_normalizes_current_typed_projection(
        self,
    ) -> None:
        payload = {
            "request_id": "viewer_req_open",
            "workspace_id": "ws_main",
            "node_id": "node_viewer",
            "session_id": "session_authoritative",
            "phase": "open",
            "request_id": "viewer_req_open",
            "playback_state": "paused",
            "step_index": 2,
            "playback": {"state": "paused", "step_index": 2},
            "live_policy": "focus_only",
            "keep_live": False,
            "cache_state": "live_ready",
            "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
            "transport_revision": 4,
            "live_mode": "full",
            "live_open_status": "ready",
            "live_open_blocker": {},
            "data_refs": {"dataset": {"kind": "tests.dataset"}},
            "transport": {
                "kind": "dpf_transport_bundle",
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
            },
            "camera_state": {"zoom": 1.25},
            "summary": {"result_name": "displacement", "cache_state": "live_ready"},
            "options": {"live_mode": "proxy", "playback_state": "playing"},
        }

        session = coerce_viewer_session_model(payload)

        self.assertEqual(session["phase"], "open")
        self.assertEqual(session["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(session["transport_revision"], 4)
        self.assertEqual(session["live_mode"], "full")
        self.assertEqual(session["playback"]["state"], "paused")
        self.assertEqual(session["summary"]["result_name"], "displacement")
        self.assertEqual(session["data_refs"], {"dataset": {"kind": "tests.dataset"}})

    def test_build_run_required_viewer_session_model_clears_live_transport_but_keeps_projection_summary(
        self,
    ) -> None:
        session_model = build_run_required_viewer_session_model(
            {
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "session_id": "session_blocked",
                "phase": "open",
                "playback_state": "paused",
                "step_index": 5,
                "live_policy": "focus_only",
                "keep_live": False,
                "cache_state": "live_ready",
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                "transport_revision": 8,
                "live_open_status": "ready",
                "data_refs": {"dataset": {"kind": "tests.dataset"}},
                "transport": {
                    "kind": "dpf_transport_bundle",
                    "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
                    "manifest_path": "C:/temp/viewer/manifest.json",
                    "entry_path": "C:/temp/viewer/entry.vtm",
                },
                "camera_state": {"zoom": 1.1},
                "summary": {"result_name": "displacement", "set_label": "Set 4"},
                "options": {
                    "live_mode": "full",
                    "playback_state": "paused",
                    "step_index": 5,
                },
            },
            reason="workspace_rerun",
            run_id="run_live",
        )

        self.assertEqual(session_model["phase"], "blocked")
        self.assertEqual(session_model["live_open_status"], "blocked")
        self.assertTrue(session_model["live_open_blocker"]["rerun_required"])
        self.assertEqual(session_model["summary"]["result_name"], "displacement")
        self.assertEqual(
            session_model["summary"]["live_transport_release_reason"], "workspace_rerun"
        )
        self.assertEqual(session_model["summary"]["run_id"], "run_live")
        self.assertEqual(
            session_model["transport"],
            {
                "kind": "dpf_transport_bundle",
                "backend_id": DPF_EXECUTION_VIEWER_BACKEND_ID,
            },
        )
        self.assertEqual(session_model["data_refs"], {})
        self.assertEqual(session_model["options"]["live_mode"], "proxy")


if __name__ == "__main__":
    unittest.main()
