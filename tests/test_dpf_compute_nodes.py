from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

dpf = pytest.importorskip("ansys.dpf.core")
pytest.importorskip("pyvista")

from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST, THERMAL_ANALYSIS_RTH
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_VIEWER_DATASET_HANDLE_KIND,
)
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.ansys_dpf import (
    DpfExportNodePlugin,
    DpfFieldOpsNodePlugin,
    DpfMeshExtractNodePlugin,
    DpfMeshScopingNodePlugin,
    DpfModelNodePlugin,
    DpfResultFieldNodePlugin,
    DpfTimeScopingNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
)
from ea_node_editor.nodes.types import ExecutionContext, RuntimeArtifactRef
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver


class DpfComputeNodeTests(unittest.TestCase):
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
            run_id="run_dpf_compute",
            node_id=f"node_{node_type_id.replace('.', '_')}{node_suffix}",
            workspace_id="ws_dpf_compute",
            inputs=dict(inputs or {}),
            properties=self.registry.normalize_properties(node_type_id, dict(properties or {})),
            emit_log=lambda _level, _message: None,
            project_path=str(project_path) if project_path is not None else "",
            path_resolver=resolver.resolve_to_path,
            worker_services=services or WorkerServices(),
        )
        return ctx, resolver

    def test_result_field_requires_single_active_set_and_supports_time_scoping_handles(self) -> None:
        services = WorkerServices()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )[0]
        ).outputs["model"]

        time_ctx, _ = self._execution_context(
            DPF_TIME_SCOPING_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={"set_ids": "2"},
            services=services,
        )
        time_ref = DpfTimeScopingNodePlugin().execute(time_ctx).outputs["scoping"]

        result_ctx, _ = self._execution_context(
            DPF_RESULT_FIELD_NODE_TYPE_ID,
            inputs={"model": model_ref, "time_scoping": time_ref},
            properties={"result_name": "displacement"},
            services=services,
        )
        field_ref = DpfResultFieldNodePlugin().execute(result_ctx).outputs["field"]
        field_value = services.resolve_handle(field_ref, expected_kind=DPF_FIELD_HANDLE_KIND)

        self.assertEqual(field_ref.kind, DPF_FIELD_HANDLE_KIND)
        self.assertEqual(field_ref.metadata["result_name"], "displacement")
        self.assertEqual(field_ref.metadata["set_id"], 2)
        self.assertEqual(field_ref.metadata["time_value"], 2.0)
        self.assertEqual(field_ref.metadata["time_scoping_handle_id"], time_ref.handle_id)
        self.assertIsInstance(field_value, dpf.Field)
        self.assertEqual(field_value.location, "Nodal")
        self.assertEqual(field_value.component_count, 3)

        invalid_ctx, _ = self._execution_context(
            DPF_RESULT_FIELD_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={"result_name": "displacement", "set_ids": "1,2"},
            services=services,
        )
        with self.assertRaisesRegex(ValueError, "exactly one active set"):
            DpfResultFieldNodePlugin().execute(invalid_ctx)

    def test_field_ops_norm_location_conversion_and_min_max_preserve_single_field_handles(self) -> None:
        services = WorkerServices()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )[0]
        ).outputs["model"]

        result_ctx, _ = self._execution_context(
            DPF_RESULT_FIELD_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={"result_name": "stress", "set_ids": "1"},
            services=services,
        )
        stress_ref = DpfResultFieldNodePlugin().execute(result_ctx).outputs["field"]

        norm_ctx, _ = self._execution_context(
            DPF_FIELD_OPS_NODE_TYPE_ID,
            inputs={"field": stress_ref},
            properties={"operation": "norm"},
            services=services,
        )
        norm_ref = DpfFieldOpsNodePlugin().execute(norm_ctx).outputs["field_out"]
        norm_field = services.resolve_handle(norm_ref, expected_kind=DPF_FIELD_HANDLE_KIND)

        self.assertEqual(norm_ref.kind, DPF_FIELD_HANDLE_KIND)
        self.assertEqual(norm_ref.metadata["operation"], "norm")
        self.assertEqual(norm_ref.metadata["set_id"], 1)
        self.assertEqual(norm_field.location, "ElementalNodal")
        self.assertEqual(norm_field.component_count, 1)

        convert_ctx, _ = self._execution_context(
            DPF_FIELD_OPS_NODE_TYPE_ID,
            inputs={"field": stress_ref, "model": model_ref},
            properties={"operation": "convert_location", "location": "nodal"},
            services=services,
        )
        converted_ref = DpfFieldOpsNodePlugin().execute(convert_ctx).outputs["field_out"]
        converted_field = services.resolve_handle(converted_ref, expected_kind=DPF_FIELD_HANDLE_KIND)

        self.assertEqual(converted_ref.metadata["requested_location"], "Nodal")
        self.assertEqual(converted_field.location, "Nodal")
        self.assertEqual(converted_field.component_count, 6)

        min_max_ctx, _ = self._execution_context(
            DPF_FIELD_OPS_NODE_TYPE_ID,
            inputs={"field": norm_ref},
            properties={"operation": "min_max"},
            services=services,
        )
        min_max_outputs = DpfFieldOpsNodePlugin().execute(min_max_ctx).outputs
        min_field = services.resolve_handle(min_max_outputs["field_min"], expected_kind=DPF_FIELD_HANDLE_KIND)
        max_field = services.resolve_handle(min_max_outputs["field_max"], expected_kind=DPF_FIELD_HANDLE_KIND)

        self.assertEqual(min_max_outputs["field_min"].metadata["reduction"], "min")
        self.assertEqual(min_max_outputs["field_max"].metadata["reduction"], "max")
        self.assertEqual(min_max_outputs["field_min"].metadata["set_id"], 1)
        self.assertEqual(min_field.component_count, 1)
        self.assertEqual(max_field.component_count, 1)
        self.assertEqual(min_field.scoping.size, 1)
        self.assertEqual(max_field.scoping.size, 1)

    def test_mesh_extract_returns_scoped_mesh_handle(self) -> None:
        services = WorkerServices()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )[0]
        ).outputs["model"]

        scoping_ctx, _ = self._execution_context(
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            properties={
                "selection_mode": "element_ids",
                "element_ids": "1,2",
                "location": "elemental",
            },
            services=services,
        )
        mesh_scoping_ref = DpfMeshScopingNodePlugin().execute(scoping_ctx).outputs["scoping"]

        mesh_ctx, _ = self._execution_context(
            DPF_MESH_EXTRACT_NODE_TYPE_ID,
            inputs={"model": model_ref, "mesh_scoping": mesh_scoping_ref},
            properties={"nodes_only": False},
            services=services,
        )
        mesh_ref = DpfMeshExtractNodePlugin().execute(mesh_ctx).outputs["mesh"]
        mesh = services.resolve_handle(mesh_ref, expected_kind=DPF_MESH_HANDLE_KIND)

        self.assertEqual(mesh_ref.kind, DPF_MESH_HANDLE_KIND)
        self.assertEqual(mesh_ref.metadata["element_count"], 2)
        self.assertEqual(mesh.elements.n_elements, 2)
        self.assertGreater(mesh.nodes.n_nodes, 0)

    def test_export_node_honors_memory_stored_and_both_output_modes(self) -> None:
        services = WorkerServices()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )[0]
        ).outputs["model"]
        field_ref = DpfResultFieldNodePlugin().execute(
            self._execution_context(
                DPF_RESULT_FIELD_NODE_TYPE_ID,
                inputs={"model": model_ref},
                properties={"result_name": "displacement", "set_ids": "1"},
                services=services,
            )[0]
        ).outputs["field"]

        memory_ctx, _ = self._execution_context(
            DPF_EXPORT_NODE_TYPE_ID,
            inputs={"field": field_ref, "model": model_ref},
            properties={"output_mode": "memory", "export_formats": "csv"},
            services=services,
            node_suffix="_memory",
        )
        memory_outputs = DpfExportNodePlugin().execute(memory_ctx).outputs
        self.assertIn("dataset", memory_outputs)
        self.assertNotIn("csv", memory_outputs)
        self.assertNotIn("exports", memory_outputs)
        self.assertEqual(memory_outputs["dataset"].kind, DPF_VIEWER_DATASET_HANDLE_KIND)

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "packet_p08_demo.sfe"

            stored_ctx, stored_resolver = self._execution_context(
                DPF_EXPORT_NODE_TYPE_ID,
                inputs={"field": field_ref, "model": model_ref},
                properties={
                    "output_mode": "stored",
                    "export_formats": "csv,vtu",
                    "artifact_key": "packet_export_stored",
                },
                services=services,
                project_path=project_path,
                node_suffix="_stored",
            )
            stored_outputs = DpfExportNodePlugin().execute(stored_ctx).outputs

            self.assertNotIn("dataset", stored_outputs)
            self.assertEqual(set(stored_outputs["exports"]), {"csv", "vtu"})
            self.assertIsInstance(stored_outputs["csv"], RuntimeArtifactRef)
            self.assertIsInstance(stored_outputs["vtu"], RuntimeArtifactRef)
            csv_path = stored_resolver.store.resolve_staged_path(stored_outputs["csv"])
            vtu_path = stored_resolver.store.resolve_staged_path(stored_outputs["vtu"])
            self.assertIsNotNone(csv_path)
            self.assertIsNotNone(vtu_path)
            if csv_path is None or vtu_path is None:
                self.fail("Stored export artifact refs did not resolve through the project artifact store.")
            self.assertTrue(csv_path.exists())
            self.assertTrue(vtu_path.is_dir())
            self.assertEqual(len(list(vtu_path.glob("*.vtu"))), 1)

            both_ctx, both_resolver = self._execution_context(
                DPF_EXPORT_NODE_TYPE_ID,
                inputs={"field": field_ref, "model": model_ref},
                properties={
                    "output_mode": "both",
                    "export_formats": "csv",
                    "artifact_key": "packet_export_both",
                },
                services=services,
                project_path=project_path,
                node_suffix="_both",
            )
            both_outputs = DpfExportNodePlugin().execute(both_ctx).outputs

            self.assertEqual(both_outputs["dataset"].kind, DPF_VIEWER_DATASET_HANDLE_KIND)
            self.assertEqual(set(both_outputs["exports"]), {"csv"})
            both_csv_path = both_resolver.store.resolve_staged_path(both_outputs["csv"])
            self.assertIsNotNone(both_csv_path)
            if both_csv_path is None:
                self.fail("Both-mode CSV artifact ref did not resolve through the project artifact store.")
            self.assertTrue(both_csv_path.exists())

    def test_result_field_supports_thermal_rth_fixture(self) -> None:
        services = WorkerServices()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(THERMAL_ANALYSIS_RTH)},
                services=services,
            )[0]
        ).outputs["model"]

        result_ctx, _ = self._execution_context(
            DPF_RESULT_FIELD_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={"result_name": "temperature", "set_ids": "1"},
            services=services,
        )
        field_ref = DpfResultFieldNodePlugin().execute(result_ctx).outputs["field"]
        field_value = services.resolve_handle(field_ref, expected_kind=DPF_FIELD_HANDLE_KIND)

        self.assertEqual(field_ref.metadata["result_name"], "temperature")
        self.assertEqual(field_ref.metadata["set_id"], 1)
        self.assertEqual(field_value.location, "Nodal")
        self.assertEqual(field_value.component_count, 1)
        self.assertGreater(field_value.scoping.size, 1000)


if __name__ == "__main__":
    unittest.main()
