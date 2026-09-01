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
np = pytest.importorskip("numpy")

from ansys_dpf_core.fixture_paths import MODAL_ANALYSIS_RST, STATIC_ANALYSIS_RST
from ea_node_editor.addons.ansys_dpf.plot_catalog import (
    load_ansys_dpf_plot_plugin_descriptors,
)
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
)
from ea_node_editor.execution.worker_services import WorkerServices
from tests.typed_handle_support import dpf_worker_services
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.ansys_dpf_data_types import DPF_MODEL_DATA_TYPE
from ea_node_editor.nodes.builtins.ansys_dpf import (
    DpfWorkflowFieldMathNodePlugin,
    DpfWorkflowMinMaxEnvelopeNodePlugin,
    DpfWorkflowModeShapeViewerNodePlugin,
    DpfWorkflowResultFieldsNodePlugin,
    DpfWorkflowStressInvariantsNodePlugin,
    DpfWorkflowTableExportNodePlugin,
    DpfWorkflowTimeHistoryProbeNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_curated_post import (
    _resolve_fields_container_input,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
    DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
    DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
    DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
    DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
    DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
)
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.runtime_contracts.value_refs import (
    RuntimeArtifactRef,
    RuntimeHandleRef,
)
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.runtime_contracts import (
    COREX_VIEWER_SESSION_HANDLE_KIND,
    VIEWER_SESSION_DATA_TYPE_ID,
)

_BOLT_NAMED_SELECTION = "BOLT_NODES"


class DpfWorkflowPostNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def test_fields_container_guard_rejects_correct_kind_with_wrong_semantic_type(
        self,
    ) -> None:
        spoof = RuntimeHandleRef(
            data_type_id=DPF_MODEL_DATA_TYPE,
            schema_version=1,
            handle_id="spoof-fields",
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope="run:spoof",
            worker_generation=1,
        )

        with self.assertRaisesRegex(TypeError, "dpf.field or dpf.fields_container"):
            _resolve_fields_container_input(
                object(),
                spoof,
                node_name="DPF Field Math",
                port_label="A",
            )

    def test_table_export_inputs_use_tree_access(self) -> None:
        spec = self.registry.get_spec(DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID)
        inputs = [port for port in spec.ports if port.direction == "in"]
        self.assertEqual({port.key for port in inputs}, {"fields", "model"})
        self.assertTrue(all(port.data_access == "tree" for port in inputs))

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
            run_id="run_dpf_workflow_post",
            node_id=f"node_{node_type_id.replace('.', '_')}{node_suffix}",
            workspace_id="ws_dpf_workflow_post",
            inputs=dict(inputs or {}),
            properties=self.registry.normalize_properties(node_type_id, dict(properties or {})),
            emit_log=lambda _level, _message: None,
            project_path=str(project_path) if project_path is not None else "",
            path_resolver=resolver.resolve_to_path,
            worker_services=services or dpf_worker_services(),
        )
        return ctx, resolver

    def _model_ref(self, services: WorkerServices, path: Path):
        return services.dpf_runtime_service.load_model(path)

    def _bolt_node_ids(self, services: WorkerServices, model_ref) -> list[int]:
        model = services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        return [int(item) for item in model.metadata.named_selection(_BOLT_NAMED_SELECTION).ids]

    def test_min_max_envelope_defaults_to_all_sets_and_reports_extreme_location(self) -> None:
        services = dpf_worker_services()
        model_ref = self._model_ref(services, STATIC_ANALYSIS_RST)
        node_ids = self._bolt_node_ids(services, model_ref)

        ctx, _ = self._execution_context(
            DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={
                "result_name": "displacement",
                "selection_mode": "named_selection",
                "named_selection": _BOLT_NAMED_SELECTION,
            },
            services=services,
        )
        outputs = DpfWorkflowMinMaxEnvelopeNodePlugin().execute(ctx).outputs

        self.assertNotIn("exec_out", outputs)
        self.assertEqual(outputs["fields"].kind, DPF_FIELDS_CONTAINER_HANDLE_KIND)
        self.assertEqual(outputs["envelope_min"].kind, DPF_FIELD_HANDLE_KIND)
        self.assertEqual(outputs["envelope_max"].kind, DPF_FIELD_HANDLE_KIND)

        per_set_table = outputs["per_set_table"]
        self.assertEqual([row["set_id"] for row in per_set_table], [1, 2])
        self.assertEqual([row["time_value"] for row in per_set_table], [1.0, 2.0])
        for row in per_set_table:
            self.assertIn(row["max_entity_id"], node_ids)
            self.assertLessEqual(row["min"], row["max"])

        summary = outputs["summary"]
        self.assertEqual(summary["location"], "Nodal")
        self.assertEqual(summary["max"]["value"], max(row["max"] for row in per_set_table))
        self.assertIn(summary["max"]["entity_id"], node_ids)
        self.assertEqual(len(summary["max"]["coordinates"]), 3)

        envelope_max = services.resolve_handle(
            outputs["envelope_max"], expected_kind=DPF_FIELD_HANDLE_KIND
        )
        self.assertEqual(int(envelope_max.scoping.size), len(node_ids))

    def test_time_history_probe_series_feeds_dpf_line_plot_with_time_axis(self) -> None:
        services = dpf_worker_services()
        model_ref = self._model_ref(services, STATIC_ANALYSIS_RST)
        node_ids = self._bolt_node_ids(services, model_ref)

        ctx, _ = self._execution_context(
            DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={
                "result_name": "displacement",
                "selection_mode": "named_selection",
                "named_selection": _BOLT_NAMED_SELECTION,
            },
            services=services,
        )
        outputs = DpfWorkflowTimeHistoryProbeNodePlugin().execute(ctx).outputs

        self.assertEqual(outputs["time_values"], [1.0, 2.0])
        self.assertEqual(len(outputs["table"]), len(node_ids) * 2)
        series_ref = outputs["series"]
        self.assertEqual(series_ref.kind, DPF_FIELDS_CONTAINER_HANDLE_KIND)
        self.assertEqual(series_ref.metadata["x_axis"], "time")

        line_plot = next(
            descriptor
            for descriptor in load_ansys_dpf_plot_plugin_descriptors()
            if descriptor.spec.type_id == "dpf.plot.line"
        ).factory()
        plot_ctx, _ = self._execution_context(
            "dpf.plot.line",
            inputs={"series": series_ref},
            properties={"frame_selector": "all"},
            services=services,
        )
        render_request, _properties = line_plot._build_render_request(plot_ctx)  # noqa: SLF001
        self.assertEqual(len(render_request.series), len(node_ids))
        for item in render_request.series:
            self.assertEqual(item["x"], [1.0, 2.0])
            self.assertIn("entity", item["label"])

    def test_time_history_probe_rejects_unscoped_selection(self) -> None:
        services = dpf_worker_services()
        model_ref = self._model_ref(services, STATIC_ANALYSIS_RST)
        # Registry normalization coerces the off-enum value "all" back to the
        # explicit choose_scope drop state, which gives targeted next-step guidance.
        normalized_ctx, _ = self._execution_context(
            DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={"result_name": "displacement", "selection_mode": "all"},
            services=services,
        )
        with self.assertRaisesRegex(ValueError, "requires a scope"):
            DpfWorkflowTimeHistoryProbeNodePlugin().execute(normalized_ctx)

        raw_ctx = ExecutionContext(
            run_id="run_dpf_workflow_post",
            node_id="node_probe_raw_all",
            workspace_id="ws_dpf_workflow_post",
            inputs={"model": model_ref},
            properties={"result_name": "displacement", "selection_mode": "all"},
            emit_log=lambda _level, _message: None,
            worker_services=services,
        )
        with self.assertRaisesRegex(ValueError, "selection_mode must be one of"):
            DpfWorkflowTimeHistoryProbeNodePlugin().execute(raw_ctx)

    def test_stress_invariants_produce_scalar_fields_with_expected_identities(self) -> None:
        services = dpf_worker_services()
        model_ref = self._model_ref(services, STATIC_ANALYSIS_RST)

        def _invariant_values(invariant: str) -> np.ndarray:
            ctx, _ = self._execution_context(
                DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
                inputs={"model": model_ref},
                properties={
                    "invariant": invariant,
                    "selection_mode": "named_selection",
                    "named_selection": _BOLT_NAMED_SELECTION,
                    "location": "nodal",
                    "time_scope_mode": "set_ids",
                    "set_ids": "1",
                },
                services=services,
                node_suffix=f"_{invariant}",
            )
            outputs = DpfWorkflowStressInvariantsNodePlugin().execute(ctx).outputs
            self.assertEqual(outputs["fields"].kind, DPF_FIELDS_CONTAINER_HANDLE_KIND)
            self.assertEqual(outputs["fields"].metadata["operation"], invariant)
            self.assertNotIn("field", outputs)
            container = services.resolve_handle(outputs["fields"])
            self.assertEqual(int(container[0].component_count), 1)
            return np.asarray(container[0].data, dtype=float).reshape(-1)

        von_mises = _invariant_values("von_mises")
        principal_1 = _invariant_values("principal_1")
        principal_3 = _invariant_values("principal_3")
        intensity = _invariant_values("intensity")

        self.assertTrue(bool(np.all(von_mises >= 0.0)))
        self.assertTrue(bool(np.all(principal_1 >= principal_3 - 1e-6)))
        self.assertTrue(bool(np.allclose(intensity, principal_1 - principal_3, rtol=1e-4, atol=1e-3)))

    def test_field_math_add_matches_scale_by_two(self) -> None:
        services = dpf_worker_services()
        model_ref = self._model_ref(services, STATIC_ANALYSIS_RST)
        fields_ctx, _ = self._execution_context(
            DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={
                "result_name": "displacement",
                "time_scope_mode": "set_ids",
                "set_ids": "1",
            },
            services=services,
        )
        fields_ref = DpfWorkflowResultFieldsNodePlugin().execute(fields_ctx).outputs["fields"]

        add_ctx, _ = self._execution_context(
            DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
            inputs={"a": fields_ref, "b": fields_ref},
            properties={"operation": "add"},
            services=services,
            node_suffix="_add",
        )
        add_outputs = DpfWorkflowFieldMathNodePlugin().execute(add_ctx).outputs

        scale_ctx, _ = self._execution_context(
            DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
            inputs={"a": fields_ref},
            properties={"operation": "scale", "scalar": 2.0},
            services=services,
            node_suffix="_scale",
        )
        scale_outputs = DpfWorkflowFieldMathNodePlugin().execute(scale_ctx).outputs

        added = services.resolve_handle(add_outputs["fields"])
        scaled = services.resolve_handle(scale_outputs["fields"])
        self.assertTrue(
            bool(
                np.allclose(
                    np.asarray(added[0].data, dtype=float),
                    np.asarray(scaled[0].data, dtype=float),
                    rtol=1e-9,
                )
            )
        )
        self.assertNotIn("field", add_outputs)
        self.assertEqual(add_outputs["fields"].metadata["operation"], "add")

        missing_b_ctx, _ = self._execution_context(
            DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
            inputs={"a": fields_ref},
            properties={"operation": "subtract"},
            services=services,
            node_suffix="_missing_b",
        )
        with self.assertRaisesRegex(ValueError, "requires a second fields container"):
            DpfWorkflowFieldMathNodePlugin().execute(missing_b_ctx)

    def test_table_export_stages_csv_with_coordinates(self) -> None:
        services = dpf_worker_services()
        model_ref = self._model_ref(services, STATIC_ANALYSIS_RST)
        node_ids = self._bolt_node_ids(services, model_ref)
        fields_ctx, _ = self._execution_context(
            DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={
                "result_name": "displacement",
                "selection_mode": "named_selection",
                "named_selection": _BOLT_NAMED_SELECTION,
                "time_scope_mode": "set_ids",
                "set_ids": "1,2",
            },
            services=services,
        )
        fields_ref = DpfWorkflowResultFieldsNodePlugin().execute(fields_ctx).outputs["fields"]

        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "table_export_demo.cxproj"
            ctx, resolver = self._execution_context(
                DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
                inputs={"fields": fields_ref, "model": model_ref},
                properties={"artifact_key": "bolt_table"},
                services=services,
                project_path=project_path,
            )
            outputs = DpfWorkflowTableExportNodePlugin().execute(ctx).outputs

            self.assertEqual(len(outputs["table"]), len(node_ids) * 2)
            first_row = outputs["table"][0]
            for column in ("entity_id", "x", "y", "z", "set_id", "time_value", "magnitude"):
                self.assertIn(column, first_row)
            self.assertIsInstance(outputs["csv"], RuntimeArtifactRef)
            self.assertEqual(set(outputs["exports"]), {"csv"})

            csv_path = resolver.store.resolve_staged_path(outputs["csv"])
            self.assertIsNotNone(csv_path)
            csv_lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertTrue(csv_lines[0].startswith("entity_id,x,y,z,set_id,time_value"))
            self.assertEqual(len(csv_lines), len(node_ids) * 2 + 1)

    def test_table_export_memory_mode_returns_rows_without_artifacts(self) -> None:
        services = dpf_worker_services()
        model_ref = self._model_ref(services, STATIC_ANALYSIS_RST)
        fields_ctx, _ = self._execution_context(
            DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={
                "result_name": "displacement",
                "time_scope_mode": "set_ids",
                "set_ids": "1",
            },
            services=services,
        )
        fields_ref = DpfWorkflowResultFieldsNodePlugin().execute(fields_ctx).outputs["fields"]

        ctx, _ = self._execution_context(
            DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
            inputs={"fields": fields_ref, "model": model_ref},
            properties={"output_mode": "memory"},
            services=services,
            node_suffix="_memory",
        )
        outputs = DpfWorkflowTableExportNodePlugin().execute(ctx).outputs
        self.assertNotIn("csv", outputs)
        self.assertNotIn("exports", outputs)
        self.assertGreater(len(outputs["table"]), 0)


class DpfModeShapeViewerNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        pytest.importorskip("pyvista")
        self.registry = build_default_registry()

    def _execution_context(
        self,
        *,
        properties: dict[str, object],
        services: WorkerServices,
    ) -> ExecutionContext:
        resolver = ProjectArtifactResolver(project_path=None)
        return ExecutionContext(
            run_id="run_dpf_mode_shape",
            node_id="node_dpf_mode_shape",
            workspace_id="ws_dpf_mode_shape",
            inputs={},
            properties=self.registry.normalize_properties(
                DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID, dict(properties)
            ),
            emit_log=lambda _level, _message: None,
            path_resolver=resolver.resolve_to_path,
            worker_services=services,
        )

    def test_mode_shape_viewer_extracts_selected_mode_and_reports_frequency(self) -> None:
        services = dpf_worker_services()
        ctx = self._execution_context(
            properties={"path": str(MODAL_ANALYSIS_RST), "mode": "2"},
            services=services,
        )
        outputs = DpfWorkflowModeShapeViewerNodePlugin().execute(ctx).outputs

        self.assertNotIn("exec_out", outputs)
        self.assertGreater(outputs["frequency"], 0.0)
        self.assertEqual(outputs["fields"].metadata["set_ids"], [2])
        self.assertIn("session", outputs)
        self.assertNotIn("field", outputs)
        session_ref = outputs["session"]
        self.assertIsInstance(session_ref, RuntimeHandleRef)
        session = services.resolve_handle(
            session_ref,
            expected_data_type=VIEWER_SESSION_DATA_TYPE_ID,
            expected_kind=COREX_VIEWER_SESSION_HANDLE_KIND,
        )
        self.assertEqual(session["options"]["deform_scale"], "auto")

        model = services.resolve_handle(outputs["model"], expected_kind=DPF_MODEL_HANDLE_KIND)
        expected_frequency = float(model.metadata.time_freq_support.time_frequencies.data[1])
        self.assertAlmostEqual(outputs["frequency"], expected_frequency, places=6)

    def test_mode_shape_viewer_rejects_out_of_range_or_invalid_mode(self) -> None:
        services = dpf_worker_services()
        ctx = self._execution_context(
            properties={"path": str(MODAL_ANALYSIS_RST), "mode": "99"},
            services=services,
        )
        with self.assertRaisesRegex(ValueError, "set_ids must stay within"):
            DpfWorkflowModeShapeViewerNodePlugin().execute(ctx)

        invalid_ctx = self._execution_context(
            properties={"path": str(MODAL_ANALYSIS_RST), "mode": "not_a_mode"},
            services=services,
        )
        with self.assertRaisesRegex(ValueError, "positive integer mode number"):
            DpfWorkflowModeShapeViewerNodePlugin().execute(invalid_ctx)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
