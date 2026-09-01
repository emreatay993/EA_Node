from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

dpf = pytest.importorskip("ansys.dpf.core")
pytest.importorskip("pyvista")

from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_VIEWER_DATASET_HANDLE_KIND,
)
from ea_node_editor.execution.viewer_messages import (
    CloseViewerSessionCommand,
    OpenViewerSessionCommand,
)
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.execution.worker_services import WorkerServices
from tests.typed_handle_support import dpf_worker_services
from ea_node_editor.nodes.ansys_dpf_data_types import DPF_MODEL_DATA_TYPE
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.ansys_dpf import (
    DpfModelNodePlugin,
    DpfResultFieldNodePlugin,
    DpfViewerNodePlugin,
    DpfWorkflowResultViewerNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_MODEL_NODE_TYPE_ID,
    DPF_OUTPUT_MODE_MEMORY,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
    DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
    DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
    wrap_field_handle_as_fields_container,
)
from ea_node_editor.nodes.builtins.ansys_dpf_viewer_adapter import (
    open_dpf_viewer_session_payload,
)
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.runtime_contracts.value_refs import RuntimeHandleRef
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.runtime_contracts import (
    COREX_VIEWER_SESSION_HANDLE_KIND,
    VIEWER_SESSION_DATA_TYPE_ID,
)
from ea_node_editor.settings import SCHEMA_VERSION


class DpfViewerNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def test_viewer_adapter_rejects_fields_kind_with_wrong_semantic_type(self) -> None:
        spoof = RuntimeHandleRef(
            data_type_id=DPF_MODEL_DATA_TYPE,
            schema_version=1,
            handle_id="spoof-fields",
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="run:spoof",
            worker_generation=1,
        )

        with self.assertRaisesRegex(TypeError, "dpf.field or dpf.fields_container"):
            open_dpf_viewer_session_payload(
                SimpleNamespace(),
                fields_ref=spoof,
                model_ref=None,
                mesh_ref=None,
                output_mode=DPF_OUTPUT_MODE_MEMORY,
            )

    def _execution_context(
        self,
        node_type_id: str,
        *,
        inputs: dict[str, object] | None = None,
        properties: dict[str, object] | None = None,
        services: WorkerServices | None = None,
        node_id: str | None = None,
    ) -> ExecutionContext:
        resolver = ProjectArtifactResolver(project_path=None)
        return ExecutionContext(
            run_id="run_dpf_viewer",
            node_id=node_id or f"node_{node_type_id.replace('.', '_')}",
            workspace_id="ws_dpf_viewer",
            inputs=dict(inputs or {}),
            properties=self.registry.normalize_properties(node_type_id, dict(properties or {})),
            emit_log=lambda _level, _message: None,
            path_resolver=resolver.resolve_to_path,
            worker_services=services or dpf_worker_services(),
        )

    def _model_and_field_refs(self, services: WorkerServices) -> tuple[object, object]:
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )
        ).outputs["model"]
        field_ref = DpfResultFieldNodePlugin().execute(
            self._execution_context(
                DPF_RESULT_FIELD_NODE_TYPE_ID,
                inputs={"model": model_ref},
                properties={"result_name": "displacement", "set_ids": "2"},
                services=services,
            )
        ).outputs["field"]
        return model_ref, field_ref

    def _viewer_session_projection(
        self,
        services: WorkerServices,
        value: object,
    ) -> dict[str, object]:
        self.assertIsInstance(value, RuntimeHandleRef)
        assert isinstance(value, RuntimeHandleRef)
        self.assertEqual(value.data_type_id, VIEWER_SESSION_DATA_TYPE_ID)
        self.assertEqual(value.kind, COREX_VIEWER_SESSION_HANDLE_KIND)
        self.assertEqual(
            set(value.metadata),
            {"workspace_id", "node_id", "session_id", "backend_id"},
        )
        projection = services.resolve_handle(
            value,
            expected_data_type=VIEWER_SESSION_DATA_TYPE_ID,
            expected_kind=COREX_VIEWER_SESSION_HANDLE_KIND,
        )
        self.assertIsInstance(projection, dict)
        return projection

    def _viewer_scene_document(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_dpf_hot_apply",
            "name": "DPF Hot Apply",
            "active_workspace_id": "ws_dpf_viewer",
            "workspace_order": ["ws_dpf_viewer"],
            "workspaces": [
                {
                    "workspace_id": "ws_dpf_viewer",
                    "name": "Workspace DPF",
                    "active_view_id": "view_dpf",
                    "views": [
                        {
                            "view_id": "view_dpf",
                            "name": "V1",
                            "zoom": 1.0,
                            "pan_x": 0.0,
                            "pan_y": 0.0,
                        }
                    ],
                    "nodes": [
                        {
                            "node_id": "node_dpf_viewer",
                            "type_id": DPF_VIEWER_NODE_TYPE_ID,
                            "title": "DPF Viewer",
                            "x": 120.0,
                            "y": 80.0,
                            "collapsed": False,
                            "properties": self.registry.default_properties(DPF_VIEWER_NODE_TYPE_ID),
                            "parent_node_id": None,
                        }
                    ],
                    "edges": [],
                }
            ],
            "metadata": {},
        }

    def test_viewer_node_seeds_cached_session_payload_in_proxy_mode(self) -> None:
        services = dpf_worker_services()
        model_ref, field_ref = self._model_and_field_refs(services)

        session_payload = self._viewer_session_projection(
            services,
            DpfViewerNodePlugin().execute(
                self._execution_context(
                    DPF_VIEWER_NODE_TYPE_ID,
                    inputs={"field": field_ref, "model": model_ref},
                    services=services,
                    node_id="node_viewer_packet_p13",
                )
            ).outputs["session"],
        )

        self.assertEqual(session_payload["workspace_id"], "ws_dpf_viewer")
        self.assertEqual(session_payload["node_id"], "node_viewer_packet_p13")
        self.assertTrue(session_payload["session_id"].startswith("viewer_session_"))
        self.assertEqual(session_payload["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(session_payload["summary"]["result_name"], "displacement")
        self.assertEqual(session_payload["summary"]["set_id"], 2)
        self.assertEqual(session_payload["summary"]["set_label"], "Set 2")
        self.assertEqual(session_payload["summary"]["cache_state"], "live_ready")
        self.assertEqual(session_payload["live_open_status"], "ready")
        self.assertEqual(session_payload["options"]["output_profile"], "both")
        self.assertEqual(session_payload["options"]["live_mode"], "proxy")
        self.assertEqual(session_payload["options"]["session_state"], "open")
        self.assertFalse(session_payload["options"][DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY])
        self.assertGreaterEqual(int(session_payload["transport_revision"]), 1)
        self.assertEqual(session_payload["transport"]["kind"], "dpf_transport_bundle")
        self.assertIn("manifest_path", session_payload["transport"])
        self.assertIn("entry_path", session_payload["transport"])
        self.assertEqual(session_payload["data_refs"]["dataset"].kind, DPF_VIEWER_DATASET_HANDLE_KIND)

    def test_viewer_node_carries_mesh_edge_toggle_into_session_options(self) -> None:
        services = dpf_worker_services()
        model_ref, field_ref = self._model_and_field_refs(services)

        session_payload = self._viewer_session_projection(
            services,
            DpfViewerNodePlugin().execute(
                self._execution_context(
                    DPF_VIEWER_NODE_TYPE_ID,
                    inputs={"field": field_ref, "model": model_ref},
                    properties={DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY: True},
                    services=services,
                    node_id="node_viewer_show_mesh_edges",
                )
            ).outputs["session"],
        )

        self.assertTrue(session_payload["options"][DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY])

    def test_viewer_node_seeds_normalized_view_pack_options_into_session(self) -> None:
        services = dpf_worker_services()
        model_ref, field_ref = self._model_and_field_refs(services)

        session_payload = self._viewer_session_projection(
            services,
            DpfViewerNodePlugin().execute(
                self._execution_context(
                    DPF_VIEWER_NODE_TYPE_ID,
                    inputs={"field": field_ref, "model": model_ref},
                    properties={
                        "colormap": "turbo",
                        "result_component": "y",
                        "scalar_range_mode": "custom",
                        "scalar_range_min": "1.5",
                        "scalar_range_max": "junk",
                        "show_scalar_bar": False,
                        "deform_scale": "-4",
                    },
                    services=services,
                    node_id="node_viewer_view_pack",
                )
            ).outputs["session"],
        )

        options = session_payload["options"]
        self.assertEqual(options["colormap"], "turbo")
        self.assertEqual(options["result_component"], "y")
        self.assertEqual(options["scalar_range_mode"], "custom")
        self.assertEqual(options["scalar_range_min"], "1.5")
        self.assertEqual(options["scalar_range_max"], "")
        self.assertFalse(options["show_scalar_bar"])
        self.assertEqual(options["deform_scale"], "off")
        self.assertFalse(options[DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY])

    def test_viewer_summary_passes_time_values_ranges_and_unit(self) -> None:
        from ea_node_editor.nodes.builtins.ansys_dpf_viewer_adapter import (
            viewer_summary_from_metadata,
        )

        summary = viewer_summary_from_metadata(
            {
                "result_name": "displacement",
                "field_count": 2,
                "set_ids": [1, 2],
                "unit": "mm",
                "location": "Nodal",
                "time_values": [1.0, 2.5],
                "value_ranges": [
                    {"min": 0.0, "max": 0.5, "component_min": [0.0], "component_max": [0.5]},
                    {"min": 0.1, "max": 2.0, "component_min": [0.1], "component_max": [2.0]},
                ],
            }
        )

        self.assertEqual(summary["unit"], "mm")
        self.assertEqual(summary["location"], "Nodal")
        self.assertEqual(summary["time_values"], [1.0, 2.5])
        self.assertEqual(len(summary["value_ranges"]), 2)
        self.assertEqual(summary["value_ranges"][1]["max"], 2.0)
        self.assertEqual(summary["time_value"], 1.0)
        self.assertEqual(summary["set_id"], 1)

    def test_viewer_node_accepts_fields_container_input_directly(self) -> None:
        services = dpf_worker_services()
        model_ref, field_ref = self._model_and_field_refs(services)
        wrap_ctx = self._execution_context(
            DPF_VIEWER_NODE_TYPE_ID,
            services=services,
            node_id="node_wrap_fields_container",
        )
        fields_ref = wrap_field_handle_as_fields_container(
            wrap_ctx,
            field_ref,
            node_name="DPF Viewer Test",
        )

        session_payload = self._viewer_session_projection(
            services,
            DpfViewerNodePlugin().execute(
                self._execution_context(
                    DPF_VIEWER_NODE_TYPE_ID,
                    inputs={"field": fields_ref, "model": model_ref},
                    services=services,
                    node_id="node_viewer_fields_container_input",
                )
            ).outputs["session"],
        )

        self.assertEqual(fields_ref.kind, DPF_FIELDS_CONTAINER_HANDLE_KIND)
        self.assertEqual(session_payload["summary"]["result_name"], "displacement")
        self.assertEqual(session_payload["summary"]["set_id"], 2)
        self.assertEqual(session_payload["summary"]["field_count"], 1)
        self.assertEqual(session_payload["data_refs"]["dataset"].kind, DPF_VIEWER_DATASET_HANDLE_KIND)

    def test_workflow_result_viewer_loads_fields_and_opens_viewer_session_from_path(self) -> None:
        services = dpf_worker_services()

        outputs = DpfWorkflowResultViewerNodePlugin().execute(
            self._execution_context(
                DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                properties={
                    "result_name": "displacement",
                    "time_scope_mode": "set_ids",
                    "set_ids": "2",
                    DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY: True,
                },
                services=services,
                node_id="node_workflow_result_viewer",
            )
        ).outputs

        self.assertEqual(outputs["normalized_path"], str(STATIC_ANALYSIS_RST))
        self.assertEqual(outputs["fields"].kind, DPF_FIELDS_CONTAINER_HANDLE_KIND)
        self.assertNotIn("field", outputs)
        self.assertNotIn("mesh_scoping", outputs)
        self.assertEqual(outputs["fields"].metadata["set_ids"], [2])
        session_payload = self._viewer_session_projection(
            services,
            outputs["session"],
        )
        self.assertEqual(session_payload["summary"]["result_name"], "displacement")
        self.assertEqual(session_payload["summary"]["set_id"], 2)
        self.assertTrue(
            session_payload["options"][DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY]
        )
        self.assertEqual(
            session_payload["data_refs"]["dataset"].kind,
            DPF_VIEWER_DATASET_HANDLE_KIND,
        )

    def test_viewer_node_reopen_restores_result_summary_in_proxy_mode(self) -> None:
        services = dpf_worker_services()
        model_ref, field_ref = self._model_and_field_refs(services)

        session_payload = self._viewer_session_projection(
            services,
            DpfViewerNodePlugin().execute(
                self._execution_context(
                    DPF_VIEWER_NODE_TYPE_ID,
                    inputs={"field": field_ref, "model": model_ref},
                    properties={
                        "output_mode": "memory",
                    },
                    services=services,
                    node_id="node_viewer_reopen_packet_p13",
                )
            ).outputs["session"],
        )

        closed = services.viewer_session_service.close_session(
            CloseViewerSessionCommand(
                workspace_id="ws_dpf_viewer",
                node_id="node_viewer_reopen_packet_p13",
                session_id=session_payload["session_id"],
                options={"reason": "test_demote", "release_handles": True},
            )
        )
        reopened = services.viewer_session_service.open_session(
            OpenViewerSessionCommand(
                workspace_id="ws_dpf_viewer",
                node_id="node_viewer_reopen_packet_p13",
                session_id=session_payload["session_id"],
            )
        )

        self.assertEqual(closed.summary["close_reason"], "test_demote")
        self.assertEqual(reopened.summary["result_name"], "displacement")
        self.assertEqual(reopened.summary["set_label"], "Set 2")
        self.assertEqual(reopened.options["live_mode"], "proxy")
        self.assertEqual(reopened.summary["cache_state"], "proxy_ready")
        self.assertEqual(reopened.backend_id, DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(reopened.live_open_status, "blocked")
        self.assertEqual(reopened.live_open_blocker["code"], "rerun_required")

if __name__ == "__main__":
    unittest.main()
