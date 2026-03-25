from __future__ import annotations

import sys
import unittest
from pathlib import Path

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

try:
    import ansys.dpf.core as dpf
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    dpf = None

from ea_node_editor.execution.dpf_runtime_service import (
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
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
    DpfResultFileNodePlugin,
    DpfTimeScopingNodePlugin,
    DpfViewerNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_NODE_CATEGORY,
    DPF_OUTPUT_MODE_MEMORY,
    DPF_OUTPUT_MODE_STORED,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_VIEWER_LIVE_POLICY_VALUES,
    DPF_VIEWER_NODE_TYPE_ID,
)
from ea_node_editor.nodes.types import (
    DPF_FIELD_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_PUBLIC_DATA_TYPES,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
    DPF_VIEW_SESSION_DATA_TYPE,
    ExecutionContext,
)
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver

if dpf is not None:
    from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST


_EXPECTED_DPF_SPECS = {
    DPF_RESULT_FILE_NODE_TYPE_ID: {
        "display_name": "DPF Result File",
        "ports": ("exec_in", "path", "result_file", "normalized_path", "exec_out"),
        "properties": ("path", "output_mode"),
        "output_types": {"result_file": DPF_RESULT_FILE_DATA_TYPE, "normalized_path": "path"},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_MODEL_NODE_TYPE_ID: {
        "display_name": "DPF Model",
        "ports": ("exec_in", "result_file", "path", "model", "exec_out"),
        "properties": ("path", "output_mode"),
        "output_types": {"model": DPF_MODEL_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_MESH_SCOPING_NODE_TYPE_ID: {
        "display_name": "DPF Mesh Scoping",
        "ports": ("exec_in", "model", "scoping", "exec_out"),
        "properties": (
            "selection_mode",
            "named_selection",
            "node_ids",
            "element_ids",
            "location",
            "set_ids",
            "time_values",
            "output_mode",
        ),
        "output_types": {"scoping": DPF_SCOPING_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_TIME_SCOPING_NODE_TYPE_ID: {
        "display_name": "DPF Time Scoping",
        "ports": ("exec_in", "model", "scoping", "exec_out"),
        "properties": ("set_ids", "time_values", "output_mode"),
        "output_types": {"scoping": DPF_SCOPING_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_RESULT_FIELD_NODE_TYPE_ID: {
        "display_name": "DPF Result Field",
        "ports": ("exec_in", "model", "mesh_scoping", "time_scoping", "field", "exec_out"),
        "properties": ("result_name", "location", "set_ids", "time_values", "output_mode"),
        "output_types": {"field": DPF_FIELD_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_FIELD_OPS_NODE_TYPE_ID: {
        "display_name": "DPF Field Ops",
        "ports": ("exec_in", "field", "model", "field_out", "field_min", "field_max", "exec_out"),
        "properties": ("operation", "location", "output_mode"),
        "output_types": {
            "field_out": DPF_FIELD_DATA_TYPE,
            "field_min": DPF_FIELD_DATA_TYPE,
            "field_max": DPF_FIELD_DATA_TYPE,
        },
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_MESH_EXTRACT_NODE_TYPE_ID: {
        "display_name": "DPF Mesh Extract",
        "ports": ("exec_in", "model", "mesh_scoping", "mesh", "exec_out"),
        "properties": ("nodes_only", "output_mode"),
        "output_types": {"mesh": DPF_MESH_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_EXPORT_NODE_TYPE_ID: {
        "display_name": "DPF Export",
        "ports": ("exec_in", "field", "model", "mesh", "dataset", "exports", "csv", "png", "vtu", "vtm", "exec_out"),
        "properties": ("artifact_key", "export_formats", "output_mode"),
        "output_types": {
            "dataset": "any",
            "exports": "any",
            "csv": "path",
            "png": "path",
            "vtu": "path",
            "vtm": "path",
        },
        "output_mode_default": DPF_OUTPUT_MODE_STORED,
    },
    DPF_VIEWER_NODE_TYPE_ID: {
        "display_name": "DPF Viewer",
        "ports": ("exec_in", "field", "model", "mesh", "session", "exec_out"),
        "properties": ("viewer_live_policy", "output_mode"),
        "output_types": {"session": DPF_VIEW_SESSION_DATA_TYPE},
        "output_mode_default": "both",
        "surface_family": "viewer",
        "render_quality": {
            "weight_class": "heavy",
            "max_performance_strategy": "proxy_surface",
            "supported_quality_tiers": ("full", "proxy"),
        },
    },
}


class DpfNodeCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def _execution_context(
        self,
        node_type_id: str,
        *,
        inputs: dict[str, object] | None = None,
        properties: dict[str, object] | None = None,
        services: WorkerServices | None = None,
    ) -> ExecutionContext:
        resolver = ProjectArtifactResolver(project_path=None)
        return ExecutionContext(
            run_id="run_dpf_catalog",
            node_id=f"node_{node_type_id.replace('.', '_')}",
            workspace_id="ws_dpf_catalog",
            inputs=dict(inputs or {}),
            properties=self.registry.normalize_properties(node_type_id, dict(properties or {})),
            emit_log=lambda _level, _message: None,
            path_resolver=resolver.resolve_to_path,
            worker_services=services or WorkerServices(),
        )

    def test_public_dpf_data_type_contracts_remain_stable(self) -> None:
        self.assertEqual(
            DPF_PUBLIC_DATA_TYPES,
            (
                "dpf_model",
                "dpf_mesh",
                "dpf_field",
                "dpf_scoping",
                "dpf_view_session",
            ),
        )
        self.assertNotIn(DPF_RESULT_FILE_DATA_TYPE, DPF_PUBLIC_DATA_TYPES)

    def test_default_registry_registers_foundational_dpf_nodes(self) -> None:
        for type_id, expected in _EXPECTED_DPF_SPECS.items():
            spec = self.registry.get_spec(type_id)

            self.assertEqual(spec.display_name, expected["display_name"])
            self.assertEqual(spec.category, DPF_NODE_CATEGORY)
            self.assertEqual(spec.runtime_behavior, "active")
            self.assertEqual(spec.surface_family, expected.get("surface_family", "standard"))
            self.assertEqual(tuple(port.key for port in spec.ports), expected["ports"])
            self.assertEqual(tuple(prop.key for prop in spec.properties), expected["properties"])

            output_mode = next(prop for prop in spec.properties if prop.key == "output_mode")
            self.assertEqual(output_mode.default, expected["output_mode_default"])
            self.assertEqual(output_mode.enum_values, ("memory", "stored", "both"))
            if spec.type_id == DPF_VIEWER_NODE_TYPE_ID:
                live_policy = next(prop for prop in spec.properties if prop.key == "viewer_live_policy")
                self.assertEqual(live_policy.default, "focus_only")
                self.assertEqual(live_policy.enum_values, DPF_VIEWER_LIVE_POLICY_VALUES)
                self.assertEqual(spec.surface_family, expected["surface_family"])
                self.assertEqual(
                    spec.render_quality.supported_quality_tiers,
                    expected["render_quality"]["supported_quality_tiers"],
                )
                self.assertEqual(
                    spec.render_quality.max_performance_strategy,
                    expected["render_quality"]["max_performance_strategy"],
                )
                self.assertEqual(
                    spec.render_quality.weight_class,
                    expected["render_quality"]["weight_class"],
                )

            ports_by_key = {port.key: port for port in spec.ports}
            for port_key, data_type in expected["output_types"].items():
                self.assertEqual(ports_by_key[port_key].data_type, data_type)

    def test_default_registry_exposes_dpf_category_and_scoping_ports(self) -> None:
        dpf_specs = self.registry.filter_nodes(category=DPF_NODE_CATEGORY)

        self.assertEqual({spec.type_id for spec in dpf_specs}, set(_EXPECTED_DPF_SPECS))
        self.assertEqual(
            {spec.type_id for spec in self.registry.filter_nodes(data_type=DPF_SCOPING_DATA_TYPE, direction="out")},
            {DPF_MESH_SCOPING_NODE_TYPE_ID, DPF_TIME_SCOPING_NODE_TYPE_ID},
        )

    @unittest.skipIf(dpf is None, "ansys.dpf.core is not installed")
    def test_result_file_and_model_nodes_emit_handle_based_outputs(self) -> None:
        services = WorkerServices()

        result_ctx = self._execution_context(
            DPF_RESULT_FILE_NODE_TYPE_ID,
            inputs={"path": str(STATIC_ANALYSIS_RST)},
            services=services,
        )
        result_outputs = DpfResultFileNodePlugin().execute(result_ctx).outputs
        result_ref = result_outputs["result_file"]

        self.assertEqual(result_ref.kind, DPF_RESULT_FILE_HANDLE_KIND)
        self.assertEqual(result_outputs["normalized_path"], str(STATIC_ANALYSIS_RST))

        model_ctx = self._execution_context(
            DPF_MODEL_NODE_TYPE_ID,
            inputs={"result_file": result_ref},
            services=services,
        )
        model_outputs = DpfModelNodePlugin().execute(model_ctx).outputs
        model_ref = model_outputs["model"]

        self.assertEqual(model_ref.kind, DPF_MODEL_HANDLE_KIND)
        model = services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        self.assertIsInstance(model, dpf.Model)
        self.assertEqual(model.metadata.time_freq_support.n_sets, 2)

    @unittest.skipIf(dpf is None, "ansys.dpf.core is not installed")
    def test_mesh_scoping_node_supports_named_selection_and_raw_ids(self) -> None:
        services = WorkerServices()
        model_ref = services.dpf_runtime_service.load_model(STATIC_ANALYSIS_RST)

        named_selection_ctx = self._execution_context(
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={
                "selection_mode": "named_selection",
                "named_selection": "BOLT_NODES",
                "time_values": "2.0",
            },
            services=services,
        )
        named_selection_ref = DpfMeshScopingNodePlugin().execute(named_selection_ctx).outputs["scoping"]
        named_selection_scoping = services.resolve_handle(
            named_selection_ref,
            expected_kind=DPF_MESH_SCOPING_HANDLE_KIND,
        )

        self.assertEqual(named_selection_ref.metadata["scoping_kind"], "mesh")
        self.assertEqual(named_selection_ref.metadata["selection_mode"], "named_selection")
        self.assertEqual(named_selection_ref.metadata["named_selection"], "BOLT_NODES")
        self.assertEqual(named_selection_ref.metadata["set_ids"], [2])
        self.assertEqual(named_selection_ref.metadata["time_values"], [2.0])
        self.assertEqual(named_selection_scoping.location, "Nodal")
        self.assertEqual([int(value) for value in named_selection_scoping.ids], [11175, 11176])

        node_ids_ctx = self._execution_context(
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            properties={
                "selection_mode": "node_ids",
                "node_ids": "11175,11176",
                "location": "nodal",
            },
            services=services,
        )
        node_ids_ref = DpfMeshScopingNodePlugin().execute(node_ids_ctx).outputs["scoping"]
        node_ids_scoping = services.resolve_handle(node_ids_ref, expected_kind=DPF_MESH_SCOPING_HANDLE_KIND)

        self.assertEqual(node_ids_ref.kind, DPF_MESH_SCOPING_HANDLE_KIND)
        self.assertEqual(node_ids_ref.metadata["location"], "Nodal")
        self.assertEqual(node_ids_ref.metadata["ids"], [11175, 11176])
        self.assertEqual([int(value) for value in node_ids_scoping.ids], [11175, 11176])

        element_ids_ctx = self._execution_context(
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            properties={
                "selection_mode": "element_ids",
                "element_ids": "1,2",
                "location": "elemental",
            },
            services=services,
        )
        element_ids_ref = DpfMeshScopingNodePlugin().execute(element_ids_ctx).outputs["scoping"]
        element_ids_scoping = services.resolve_handle(
            element_ids_ref,
            expected_kind=DPF_MESH_SCOPING_HANDLE_KIND,
        )

        self.assertEqual(element_ids_ref.metadata["location"], "Elemental")
        self.assertEqual(element_ids_ref.metadata["ids"], [1, 2])
        self.assertEqual([int(value) for value in element_ids_scoping.ids], [1, 2])

    @unittest.skipIf(dpf is None, "ansys.dpf.core is not installed")
    def test_time_scoping_node_supports_set_ids_and_time_values(self) -> None:
        services = WorkerServices()
        model_ref = services.dpf_runtime_service.load_model(STATIC_ANALYSIS_RST)

        time_ctx = self._execution_context(
            DPF_TIME_SCOPING_NODE_TYPE_ID,
            inputs={"model": model_ref},
            properties={"set_ids": "1", "time_values": "2.0"},
            services=services,
        )
        time_ref = DpfTimeScopingNodePlugin().execute(time_ctx).outputs["scoping"]
        time_scoping = services.resolve_handle(time_ref, expected_kind=DPF_TIME_SCOPING_HANDLE_KIND)

        self.assertEqual(time_ref.kind, DPF_TIME_SCOPING_HANDLE_KIND)
        self.assertEqual(time_ref.metadata["scoping_kind"], "time")
        self.assertEqual(time_ref.metadata["selection_mode"], "set_ids+time_values")
        self.assertEqual(time_ref.metadata["set_ids"], [1, 2])
        self.assertEqual(time_ref.metadata["time_values"], [2.0])
        self.assertEqual([int(value) for value in time_scoping.ids], [1, 2])
        self.assertEqual(time_scoping.location, "TimeFreq")


if __name__ == "__main__":
    unittest.main()
