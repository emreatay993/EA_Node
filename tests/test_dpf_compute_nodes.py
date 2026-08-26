from __future__ import annotations

import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

dpf = pytest.importorskip("ansys.dpf.core")
pytest.importorskip("pyvista")

from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST, THERMAL_ANALYSIS_RTH
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
    DPF_VIEWER_DATASET_HANDLE_KIND,
)
from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.execution.worker_services import WorkerServices
from tests.typed_handle_support import dpf_worker_services
from ea_node_editor.nodes.ansys_dpf_data_types import DPF_SCOPING_DATA_TYPE
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.ansys_dpf import (
    DpfExportNodePlugin,
    DpfFieldOpsNodePlugin,
    DpfMeshExtractNodePlugin,
    DpfMeshScopingNodePlugin,
    DpfModelNodePlugin,
    DpfResultFieldNodePlugin,
    DpfTimeScopingNodePlugin,
    DpfWorkflowResultFieldsNodePlugin,
    DpfWorkflowResultSourceNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
    clone_handle_with_metadata,
)
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.nodes.runtime_refs import RuntimeArtifactRef
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
            worker_services=services or dpf_worker_services(),
        )
        return ctx, resolver

    def test_workflow_result_source_loads_result_file_and_model_from_one_path(self) -> None:
        services = dpf_worker_services()
        source_ctx, _ = self._execution_context(
            DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
            inputs={"path": str(STATIC_ANALYSIS_RST)},
            services=services,
        )

        plugin = DpfWorkflowResultSourceNodePlugin()
        outputs = plugin.execute(source_ctx).outputs
        repeated_outputs = plugin.execute(source_ctx).outputs

        self.assertEqual(outputs["result_file"].kind, DPF_RESULT_FILE_HANDLE_KIND)
        self.assertEqual(outputs["model"].kind, DPF_MODEL_HANDLE_KIND)
        self.assertEqual(outputs["result_file"].owner_scope, "run:run_dpf_compute")
        self.assertEqual(outputs["model"].owner_scope, "run:run_dpf_compute")
        self.assertEqual(
            repeated_outputs["result_file"].handle_id,
            outputs["result_file"].handle_id,
        )
        self.assertEqual(
            repeated_outputs["model"].handle_id,
            outputs["model"].handle_id,
        )
        self.assertEqual(outputs["normalized_path"], str(STATIC_ANALYSIS_RST))
        self.assertNotIn("exec_out", outputs)
        model = services.resolve_handle(outputs["model"], expected_kind=DPF_MODEL_HANDLE_KIND)
        self.assertIsInstance(model, dpf.Model)
        self.assertEqual(model.metadata.time_freq_support.n_sets, 2)
        service = services.dpf_runtime_service
        cached_result = next(iter(service._result_file_cache.values()))  # noqa: SLF001
        cached_model = next(iter(service._model_cache.values()))  # noqa: SLF001
        for cached_ref in (cached_result, cached_model):
            self.assertEqual(
                services.handle_registry.lease_count(
                    cached_ref,
                    owner_scope=cached_ref.owner_scope,
                ),
                1,
            )
            self.assertEqual(
                services.handle_registry.lease_count(
                    cached_ref,
                    owner_scope="run:run_dpf_compute",
                ),
                1,
            )

    def test_transient_clone_replaces_original_with_one_final_metadata_record(
        self,
    ) -> None:
        services = dpf_worker_services()
        ctx, _ = self._execution_context(
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            services=services,
        )
        native_scoping = object()
        original_ref = services.register_handle(
            native_scoping,
            data_type_id=DPF_SCOPING_DATA_TYPE,
            kind=DPF_MESH_SCOPING_HANDLE_KIND,
            run_id=ctx.run_id,
            metadata={"base": "metadata"},
        )

        final_ref = clone_handle_with_metadata(
            ctx,
            original_ref,
            expected_kind=DPF_MESH_SCOPING_HANDLE_KIND,
            metadata={"final": "metadata"},
            release_original=True,
        )

        self.assertNotEqual(final_ref.handle_id, original_ref.handle_id)
        self.assertEqual(
            final_ref.metadata,
            {"base": "metadata", "final": "metadata"},
        )
        self.assertEqual(services.handle_registry.active_handle_count, 1)
        self.assertEqual(
            services.handle_registry.lease_count(
                final_ref,
                owner_scope="run:run_dpf_compute",
            ),
            1,
        )
        self.assertIs(services.resolve_handle(final_ref), native_scoping)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(original_ref)

    def test_transient_clone_invalid_metadata_preserves_original_record(
        self,
    ) -> None:
        services = dpf_worker_services()
        ctx, _ = self._execution_context(
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            services=services,
        )
        native_scoping = object()
        original_ref = services.register_handle(
            native_scoping,
            data_type_id=DPF_SCOPING_DATA_TYPE,
            kind=DPF_MESH_SCOPING_HANDLE_KIND,
            run_id=ctx.run_id,
        )

        with self.assertRaisesRegex(TypeError, "strict JSON"):
            clone_handle_with_metadata(
                ctx,
                original_ref,
                expected_kind=DPF_MESH_SCOPING_HANDLE_KIND,
                metadata={"invalid": object()},
                release_original=True,
            )

        self.assertEqual(services.handle_registry.active_handle_count, 1)
        self.assertEqual(
            services.handle_registry.lease_count(
                original_ref,
                owner_scope="run:run_dpf_compute",
            ),
            1,
        )
        self.assertIs(services.resolve_handle(original_ref), native_scoping)

    def test_transient_clone_failure_leaves_original_stale_without_partial_record(
        self,
    ) -> None:
        services = dpf_worker_services()
        ctx, _ = self._execution_context(
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            services=services,
        )
        original_ref = services.register_handle(
            object(),
            data_type_id=DPF_SCOPING_DATA_TYPE,
            kind=DPF_MESH_SCOPING_HANDLE_KIND,
            run_id=ctx.run_id,
        )

        with (
            mock.patch.object(
                WorkerServices,
                "register_handle",
                side_effect=RuntimeError("final registration failed"),
            ),
            self.assertRaisesRegex(RuntimeError, "final registration failed"),
        ):
            clone_handle_with_metadata(
                ctx,
                original_ref,
                expected_kind=DPF_MESH_SCOPING_HANDLE_KIND,
                metadata={"final": "metadata"},
                release_original=True,
            )

        self.assertEqual(services.handle_registry.active_handle_count, 0)
        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            services.resolve_handle(original_ref)

    def test_workflow_result_fields_extracts_named_selection_with_defaulted_time_scoping(self) -> None:
        services = dpf_worker_services()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )[0]
        ).outputs["model"]

        fields_ctx, _ = self._execution_context(
            DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={
                "result_name": "displacement",
                "selection_mode": "named_selection",
                "named_selection": "BOLT_NODES",
                "location": "nodal",
            },
            services=services,
        )
        outputs = DpfWorkflowResultFieldsNodePlugin().execute(fields_ctx).outputs

        self.assertEqual(outputs["fields"].kind, DPF_FIELDS_CONTAINER_HANDLE_KIND)
        self.assertNotIn("field", outputs)
        self.assertEqual(outputs["mesh_scoping"].kind, DPF_MESH_SCOPING_HANDLE_KIND)
        self.assertEqual(outputs["time_scoping"].kind, DPF_TIME_SCOPING_HANDLE_KIND)
        fields_container = services.resolve_handle(
            outputs["fields"],
            expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        )
        self.assertEqual(len(fields_container), 1)
        self.assertEqual(outputs["fields"].metadata["result_name"], "displacement")
        self.assertEqual(outputs["fields"].metadata["field_count"], 1)
        self.assertEqual(outputs["fields"].metadata["set_ids"], [1])
        self.assertEqual(outputs["fields"].metadata["selection_mode"], "named_selection")
        self.assertEqual(outputs["fields"].metadata["mesh_scoping_handle_id"], outputs["mesh_scoping"].handle_id)
        self.assertEqual(outputs["fields"].metadata["time_scoping_handle_id"], outputs["time_scoping"].handle_id)
        self.assertEqual(outputs["mesh_scoping"].metadata["named_selection"], "BOLT_NODES")
        self.assertEqual(outputs["time_scoping"].metadata["set_ids"], [1])
        self.assertEqual(fields_container[0].location, "Nodal")
        self.assertEqual(fields_container[0].component_count, 3)

    def test_workflow_result_fields_keeps_multi_set_output_as_fields_container(self) -> None:
        services = dpf_worker_services()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )[0]
        ).outputs["model"]

        fields_ctx, _ = self._execution_context(
            DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={
                "result_name": "displacement",
                "time_scope_mode": "set_ids",
                "set_ids": "1,2",
            },
            services=services,
        )
        outputs = DpfWorkflowResultFieldsNodePlugin().execute(fields_ctx).outputs

        fields_container = services.resolve_handle(
            outputs["fields"],
            expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        )
        self.assertEqual(outputs["fields"].metadata["field_count"], 2)
        self.assertEqual(outputs["fields"].metadata["set_ids"], [1, 2])
        self.assertEqual(outputs["time_scoping"].metadata["set_ids"], [1, 2])
        self.assertEqual(len(fields_container), 2)
        self.assertNotIn("field", outputs)
        self.assertNotIn("mesh_scoping", outputs)

    def test_workflow_result_fields_time_scope_modes_use_only_the_active_selector(self) -> None:
        services = dpf_worker_services()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )[0]
        ).outputs["model"]

        cases = (
            ("first_set", {}, [1]),
            ("last_set", {}, [2]),
            ("all_sets", {}, [1, 2]),
            ("set_ids", {"set_ids": "2", "time_values": "not-a-number"}, [2]),
            ("time_values", {"set_ids": "not-an-integer", "time_values": "2.0"}, [2]),
        )
        for index, (mode, selectors, expected_set_ids) in enumerate(cases):
            with self.subTest(mode=mode):
                ctx, _ = self._execution_context(
                    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
                    inputs={"model": model_ref},
                    properties={"time_scope_mode": mode, **selectors},
                    services=services,
                    node_suffix=f"_{index}",
                )
                outputs = DpfWorkflowResultFieldsNodePlugin().execute(ctx).outputs
                self.assertEqual(outputs["fields"].metadata["set_ids"], expected_set_ids)
                self.assertEqual(outputs["fields"].metadata["time_scope_mode"], mode)
                self.assertEqual(outputs["time_scoping"].metadata["time_scope_mode"], mode)

        for mode, message in (
            ("set_ids", "requires set_ids"),
            ("time_values", "requires time_values"),
        ):
            with self.subTest(missing_selector=mode):
                ctx, _ = self._execution_context(
                    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
                    inputs={"model": model_ref},
                    properties={"time_scope_mode": mode},
                    services=services,
                    node_suffix=f"_missing_{mode}",
                )
                with self.assertRaisesRegex(ValueError, message):
                    DpfWorkflowResultFieldsNodePlugin().execute(ctx)

    def test_workflow_result_fields_infers_legacy_selector_when_time_mode_is_missing(self) -> None:
        services = dpf_worker_services()
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )[0]
        ).outputs["model"]

        for suffix, properties, expected_mode in (
            ("set_ids", {"set_ids": "2"}, "set_ids"),
            ("time_values", {"time_values": "2.0"}, "time_values"),
        ):
            with self.subTest(expected_mode=expected_mode):
                ctx = ExecutionContext(
                    run_id=f"run_dpf_compute_legacy_{suffix}",
                    node_id=f"node_dpf_workflow_legacy_{suffix}",
                    workspace_id="ws_dpf_compute",
                    inputs={"model": model_ref},
                    properties={
                        "result_name": "displacement",
                        "selection_mode": "all",
                        **properties,
                    },
                    emit_log=lambda _level, _message: None,
                    worker_services=services,
                )
                outputs = DpfWorkflowResultFieldsNodePlugin().execute(ctx).outputs
                self.assertEqual(outputs["fields"].metadata["set_ids"], [2])
                self.assertEqual(outputs["fields"].metadata["time_scope_mode"], expected_mode)

        ambiguous_ctx = ExecutionContext(
            run_id="run_dpf_compute_legacy_ambiguous",
            node_id="node_dpf_workflow_legacy_ambiguous",
            workspace_id="ws_dpf_compute",
            inputs={"model": model_ref},
            properties={
                "result_name": "displacement",
                "selection_mode": "all",
                "set_ids": "1",
                "time_values": "2.0",
            },
            emit_log=lambda _level, _message: None,
            worker_services=services,
        )
        with self.assertRaisesRegex(ValueError, "both legacy set_ids and time_values"):
            DpfWorkflowResultFieldsNodePlugin().execute(ambiguous_ctx)

    def test_result_field_requires_single_active_set_and_supports_time_scoping_handles(self) -> None:
        services = dpf_worker_services()
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

    def test_result_field_routes_operator_binding_through_generic_runtime_adapter(self) -> None:
        services = dpf_worker_services()
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
            properties={"result_name": "displacement", "set_ids": "1"},
            services=services,
        )

        with mock.patch.object(
            services.dpf_runtime_service,
            "invoke_operator",
            wraps=services.dpf_runtime_service.invoke_operator,
        ) as invoke_operator:
            field_ref = DpfResultFieldNodePlugin().execute(result_ctx).outputs["field"]

        self.assertEqual(invoke_operator.call_count, 1)
        self.assertEqual(invoke_operator.call_args.args[0], "dpf.result_field")
        self.assertEqual(invoke_operator.call_args.kwargs["properties"]["location"], "")
        self.assertEqual(tuple(invoke_operator.call_args.kwargs["properties"]["set_ids"]), (1,))
        self.assertIs(invoke_operator.call_args.kwargs["inputs"]["model"], model_ref)
        self.assertEqual(field_ref.metadata["result_name"], "displacement")
        self.assertEqual(field_ref.metadata["set_id"], 1)

    def test_field_ops_norm_location_conversion_and_min_max_preserve_single_field_handles(self) -> None:
        services = dpf_worker_services()
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
        services = dpf_worker_services()
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
        services = dpf_worker_services()
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
            project_path = Path(temp_dir) / "packet_p08_demo.cxproj"

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
        services = dpf_worker_services()
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
