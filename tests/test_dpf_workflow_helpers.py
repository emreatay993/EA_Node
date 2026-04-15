from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

dpf = pytest.importorskip("ansys.dpf.core")
pytest.importorskip("pyvista")

from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
    DPF_VIEWER_DATASET_HANDLE_KIND,
)
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
)
from ea_node_editor.nodes.node_specs import (
    DPF_DATA_SOURCES_DATA_TYPE,
    DPF_OBJECT_HANDLE_DATA_TYPE,
    DPF_STREAMS_CONTAINER_DATA_TYPE,
    DPF_WORKFLOW_DATA_TYPE,
)
from ea_node_editor.nodes.types import ExecutionContext
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver


class DpfWorkflowHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def _execution_context(
        self,
        node_type_id: str,
        *,
        inputs: dict[str, object] | None = None,
        properties: dict[str, object] | None = None,
        services: WorkerServices | None = None,
        project_path: Path | None = None,
        node_suffix: str = "",
    ) -> tuple[ExecutionContext, ProjectArtifactResolver]:
        resolver = ProjectArtifactResolver(project_path=project_path)
        ctx = ExecutionContext(
            run_id="run_dpf_helper",
            node_id=f"node_{node_type_id.replace('.', '_')}{node_suffix}",
            workspace_id="ws_dpf_helper",
            inputs=dict(inputs or {}),
            properties=self.registry.normalize_properties(node_type_id, dict(properties or {})),
            emit_log=lambda _level, _message: None,
            project_path=str(project_path) if project_path is not None else "",
            path_resolver=resolver.resolve_to_path,
            worker_services=services or WorkerServices(),
        )
        return ctx, resolver

    def _execute_node(
        self,
        node_type_id: str,
        *,
        inputs: dict[str, object] | None = None,
        properties: dict[str, object] | None = None,
        services: WorkerServices | None = None,
        project_path: Path | None = None,
        node_suffix: str = "",
    ) -> tuple[dict[str, object], ProjectArtifactResolver]:
        ctx, resolver = self._execution_context(
            node_type_id,
            inputs=inputs,
            properties=properties,
            services=services,
            project_path=project_path,
            node_suffix=node_suffix,
        )
        descriptor = self.registry.get_descriptor(node_type_id)
        return descriptor.factory().execute(ctx).outputs, resolver

    def test_fixture_backed_helper_chain_reaches_model_scoping_and_materialization(self) -> None:
        services = WorkerServices()

        data_sources_outputs, _ = self._execute_node(
            "dpf.helper.data_sources.data_sources",
            properties={"result_path": str(STATIC_ANALYSIS_RST)},
            services=services,
        )
        data_sources_ref = data_sources_outputs["data_sources"]
        self.assertEqual(data_sources_ref.kind, DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertEqual(data_sources_ref.metadata["dpf_data_type"], DPF_DATA_SOURCES_DATA_TYPE)

        updated_outputs, _ = self._execute_node(
            "dpf.helper.data_sources.set_result_file_path",
            inputs={"receiver": data_sources_ref, "result_path": str(STATIC_ANALYSIS_RST)},
            services=services,
        )
        updated_data_sources_ref = updated_outputs["updated_receiver"]
        self.assertEqual(updated_data_sources_ref.kind, DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertEqual(updated_data_sources_ref.metadata["dpf_data_type"], DPF_DATA_SOURCES_DATA_TYPE)

        model_outputs, _ = self._execute_node(
            "dpf.helper.model.model",
            inputs={"data_sources": updated_data_sources_ref},
            services=services,
        )
        model_ref = model_outputs["model"]
        self.assertEqual(model_ref.kind, DPF_MODEL_HANDLE_KIND)

        all_time_outputs, _ = self._execute_node(
            "dpf.helper.time_freq_scoping_factory.scoping_on_all_time_freqs",
            inputs={"obj": model_ref},
            services=services,
        )
        all_time_ref = all_time_outputs["scoping"]
        self.assertEqual(all_time_ref.kind, DPF_TIME_SCOPING_HANDLE_KIND)
        self.assertGreaterEqual(len(all_time_ref.metadata["set_ids"]), 1)

        field_outputs, _ = self._execute_node(
            DPF_RESULT_FIELD_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={"result_name": "displacement", "set_ids": "1"},
            services=services,
        )
        field_ref = field_outputs["field"]
        self.assertEqual(field_ref.kind, DPF_FIELD_HANDLE_KIND)

        fields_container_outputs, _ = self._execute_node(
            "dpf.helper.fields_container_factory.over_time_freq_fields_container",
            inputs={"field": field_ref},
            services=services,
        )
        fields_container_ref = fields_container_outputs["fields_container"]
        self.assertEqual(fields_container_ref.kind, DPF_FIELDS_CONTAINER_HANDLE_KIND)

        export_outputs, _ = self._execute_node(
            DPF_EXPORT_NODE_TYPE_ID,
            inputs={"field": field_ref, "model": model_ref},
            properties={"output_mode": "memory", "export_formats": "csv"},
            services=services,
            node_suffix="_memory_export",
        )
        self.assertEqual(export_outputs["dataset"].kind, DPF_VIEWER_DATASET_HANDLE_KIND)

    def test_synthetic_helper_nodes_create_runtime_objects(self) -> None:
        services = WorkerServices()

        workflow_outputs, _ = self._execute_node(
            "dpf.helper.workflow.workflow",
            services=services,
        )
        workflow_ref = workflow_outputs["workflow"]
        self.assertEqual(workflow_ref.kind, DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertEqual(workflow_ref.metadata["dpf_data_type"], DPF_WORKFLOW_DATA_TYPE)
        workflow_value = services.resolve_handle(workflow_ref, expected_kind=DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertIsInstance(workflow_value, dpf.Workflow)

        streams_outputs, _ = self._execute_node(
            "dpf.helper.streams_container.streams_container",
            services=services,
        )
        streams_ref = streams_outputs["streams_container"]
        self.assertEqual(streams_ref.kind, DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertEqual(streams_ref.metadata["dpf_data_type"], DPF_STREAMS_CONTAINER_DATA_TYPE)
        streams_value = services.resolve_handle(streams_ref, expected_kind=DPF_OBJECT_HANDLE_DATA_TYPE)
        self.assertIsInstance(streams_value, dpf.StreamsContainer)

        field_from_array_outputs, _ = self._execute_node(
            "dpf.helper.fields_factory.field_from_array",
            inputs={"arr": [1.0, 2.0, 3.0]},
            services=services,
        )
        field_ref = field_from_array_outputs["field"]
        self.assertEqual(field_ref.kind, DPF_FIELD_HANDLE_KIND)
        field_value = services.resolve_handle(field_ref, expected_kind=DPF_FIELD_HANDLE_KIND)
        self.assertIsInstance(field_value, dpf.Field)
        self.assertEqual(len(field_value.data), 3)

        create_scalar_field_outputs, _ = self._execute_node(
            "dpf.helper.fields_factory.create_scalar_field",
            properties={"num_entities": 4, "location": "Nodal"},
            services=services,
        )
        scalar_field_ref = create_scalar_field_outputs["field"]
        self.assertEqual(scalar_field_ref.kind, DPF_FIELD_HANDLE_KIND)

        fields_container_outputs, _ = self._execute_node(
            "dpf.helper.fields_container_factory.over_time_freq_fields_container",
            inputs={"field": field_ref},
            services=services,
        )
        fields_container_ref = fields_container_outputs["fields_container"]
        self.assertEqual(fields_container_ref.kind, DPF_FIELDS_CONTAINER_HANDLE_KIND)
        fields_container_value = services.resolve_handle(
            fields_container_ref,
            expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        )
        self.assertEqual(len(fields_container_value), 1)

        scoping_outputs, _ = self._execute_node(
            "dpf.helper.mesh_scoping_factory.nodal_scoping",
            properties={"node_ids": [1, 2, 3]},
            services=services,
        )
        scoping_ref = scoping_outputs["scoping"]
        self.assertEqual(scoping_ref.kind, DPF_MESH_SCOPING_HANDLE_KIND)
        self.assertEqual(scoping_ref.metadata["ids"], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
