from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

try:
    import ansys.dpf.core as dpf
except ModuleNotFoundError:  # pragma: no cover - optional dependency guard
    dpf = None

from ea_node_editor.addons.ansys_dpf import catalog as ansys_dpf_catalog
from ea_node_editor.addons.ansys_dpf.metadata import (
    ANSYS_DPF_ADDON_MANIFEST,
    ANSYS_DPF_ARTIFACTS,
    ANSYS_DPF_RUNTIME_BACKENDS,
    ANSYS_DPF_SURFACE_CAPABILITIES,
    ANSYS_DPF_TOOLCHAINS,
)
from ea_node_editor.addons.ansys_dpf.helper_catalog import (
    load_ansys_dpf_helper_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.curated_catalog import (
    load_ansys_dpf_curated_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    load_ansys_dpf_operator_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.plot_catalog import (
    load_ansys_dpf_plot_plugin_descriptors,
)
from ea_node_editor.app_preferences import (
    AppPreferencesStore,
    default_app_preferences_document,
    set_ansys_dpf_plugin_state,
)
from ea_node_editor.execution.dpf_runtime_service import (
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
)
from ea_node_editor.execution.worker_services import WorkerServices
from tests.typed_handle_support import dpf_worker_services
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins import ansys_dpf as ansys_dpf_module
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL,
    DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL,
    DPF_FIELD_OPS_VARIANT_MIN_MAX,
    DPF_FIELD_OPS_VARIANT_NORM,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_NODE_SOURCE_METADATA_BY_TYPE_ID,
    DPF_OUTPUT_MODE_MEMORY,
    DPF_OUTPUT_MODE_STORED,
    DPF_PORT_SOURCE_METADATA_BY_TYPE_ID,
    DPF_PROPERTY_SOURCE_METADATA_BY_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_RESULT_FIELD_OPERATOR_VARIANT_KEY,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
    DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
    DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
    DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
    DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
    DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
    DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
    DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
    normalize_dpf_descriptor_spec,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
    DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_NODE_CATEGORY,
    DPF_NODE_CATEGORY_PATH,
    DPF_VIEWER_CATEGORY_PATH,
    DPF_WORKFLOW_CATEGORY_PATH,
    operator_family_category_path,
    operator_family_path,
)
from ea_node_editor.nodes.builtins.plot.dpf import (
    DPF_PLOT_CATEGORY_PATH,
    DPF_PLOT_NODE_TYPE_IDS,
)
from ea_node_editor.nodes.ansys_dpf_data_types import DPF_FIELDS_CONTAINER_DATA_TYPE
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELD_DATA_TYPE,
    DPF_MESH_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
    DPF_PUBLIC_DATA_TYPES,
    DPF_RESULT_FILE_DATA_TYPE,
    DPF_SCOPING_DATA_TYPE,
)
from ea_node_editor.nodes.category_paths import category_display
from ea_node_editor.nodes.core_data_types import (
    VIEWER_SESSION_DATA_TYPE_ID as VIEWER_SESSION_DATA_TYPE,
)
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.nodes.readiness import evaluate_node_readiness
from ea_node_editor.ui_qml.node_title_icon_sources import NODE_TITLE_ICON_ASSET_ROOT, title_icon_source_for_node_payload
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver

if dpf is not None:
    from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST

DpfExportNodePlugin = ansys_dpf_module.DpfExportNodePlugin
DpfFieldOpsNodePlugin = ansys_dpf_module.DpfFieldOpsNodePlugin
DpfMeshExtractNodePlugin = ansys_dpf_module.DpfMeshExtractNodePlugin
DpfMeshScopingNodePlugin = ansys_dpf_module.DpfMeshScopingNodePlugin
DpfModelNodePlugin = ansys_dpf_module.DpfModelNodePlugin
DpfResultFieldNodePlugin = ansys_dpf_module.DpfResultFieldNodePlugin
DpfResultFileNodePlugin = ansys_dpf_module.DpfResultFileNodePlugin
DpfTimeScopingNodePlugin = ansys_dpf_module.DpfTimeScopingNodePlugin
DpfViewerNodePlugin = ansys_dpf_module.DpfViewerNodePlugin
DpfWorkflowResultFieldsNodePlugin = ansys_dpf_module.DpfWorkflowResultFieldsNodePlugin
DpfWorkflowResultSourceNodePlugin = ansys_dpf_module.DpfWorkflowResultSourceNodePlugin
DpfWorkflowResultViewerNodePlugin = ansys_dpf_module.DpfWorkflowResultViewerNodePlugin
DpfWorkflowMinMaxEnvelopeNodePlugin = ansys_dpf_module.DpfWorkflowMinMaxEnvelopeNodePlugin
DpfWorkflowTimeHistoryProbeNodePlugin = ansys_dpf_module.DpfWorkflowTimeHistoryProbeNodePlugin
DpfWorkflowStressInvariantsNodePlugin = ansys_dpf_module.DpfWorkflowStressInvariantsNodePlugin
DpfWorkflowModeShapeViewerNodePlugin = ansys_dpf_module.DpfWorkflowModeShapeViewerNodePlugin
DpfWorkflowFieldMathNodePlugin = ansys_dpf_module.DpfWorkflowFieldMathNodePlugin
DpfWorkflowTableExportNodePlugin = ansys_dpf_module.DpfWorkflowTableExportNodePlugin


_EXPECTED_DPF_SPECS = {
    DPF_RESULT_FILE_NODE_TYPE_ID: {
        "display_name": "DPF Result File",
        "ports": ('path', "result_file", "normalized_path"),
        "properties": ('path', "output_mode"),
        "output_types": {"result_file": DPF_RESULT_FILE_DATA_TYPE, "normalized_path": 'COREX.DataTypes.Path'},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
        "required_inputs": ('path',),
    },
    DPF_MODEL_NODE_TYPE_ID: {
        "display_name": "DPF Model",
        "ports": ("result_file", 'path', "model"),
        "properties": ('path', "output_mode"),
        "output_types": {"model": DPF_MODEL_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID: {
        "display_name": "DPF Result Source",
        "surface_family": "dpf_workflow",
        "ports": ('path', "result_file", "model", "normalized_path"),
        "properties": ('path',),
        "output_types": {
            "result_file": DPF_RESULT_FILE_DATA_TYPE,
            "model": DPF_MODEL_DATA_TYPE,
            "normalized_path": 'COREX.DataTypes.Path',
        },
        "required_inputs": ('path',),
    },
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID: {
        "display_name": "DPF Result Fields",
        "surface_family": "dpf_workflow",
        "ports": ("model", "fields", "mesh_scoping", "time_scoping"),
        "properties": (
            "result_name",
            "selection_mode",
            "named_selection",
            "node_ids",
            "element_ids",
            "location",
            "time_scope_mode",
            "set_ids",
            "time_values",
        ),
        "output_types": {
            "fields": DPF_FIELDS_CONTAINER_DATA_TYPE,
            "mesh_scoping": DPF_SCOPING_DATA_TYPE,
            "time_scoping": DPF_SCOPING_DATA_TYPE,
        },
        "required_inputs": ("model",),
        "time_scope_default": "first_set",
    },
    DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID: {
        "display_name": "DPF Result Viewer",
        "ports": (
            'path',
            "result_file",
            "model",
            "fields",
            "mesh_scoping",
            "time_scoping",
            "mesh",
            "session",
            "normalized_path",
        ),
        "properties": (
            'path',
            "result_name",
            "selection_mode",
            "named_selection",
            "node_ids",
            "element_ids",
            "location",
            "time_scope_mode",
            "set_ids",
            "time_values",
            "output_mode",
            DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
            "colormap",
            "result_component",
            "scalar_range_mode",
            "scalar_range_min",
            "scalar_range_max",
            "show_scalar_bar",
            "deform_scale",
            "hover_probe",
            "show_minmax_markers",
            "viewer_background",
            "camera_bookmarks",
        ),
        "output_types": {
            "result_file": DPF_RESULT_FILE_DATA_TYPE,
            "model": DPF_MODEL_DATA_TYPE,
            "fields": DPF_FIELDS_CONTAINER_DATA_TYPE,
            "mesh_scoping": DPF_SCOPING_DATA_TYPE,
            "time_scoping": DPF_SCOPING_DATA_TYPE,
            "mesh": DPF_MESH_DATA_TYPE,
            "session": VIEWER_SESSION_DATA_TYPE,
            "normalized_path": 'COREX.DataTypes.Path',
        },
        "output_mode_default": "both",
        "time_scope_default": "first_set",
        "surface_family": "viewer",
        "render_quality": {
            "supported_quality_tiers": ("full", "proxy"),
        },
        "required_inputs": ('path',),
    },
    DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID: {
        "display_name": "DPF Min/Max Envelope",
        "surface_family": "dpf_workflow",
        "ports": (
            "model",
            "envelope_min",
            "envelope_max",
            "fields",
            "per_set_table",
            "summary",
        ),
        "properties": (
            "result_name",
            "selection_mode",
            "named_selection",
            "node_ids",
            "element_ids",
            "location",
            "time_scope_mode",
            "set_ids",
            "time_values",
        ),
        "output_types": {
            "envelope_min": DPF_FIELD_DATA_TYPE,
            "envelope_max": DPF_FIELD_DATA_TYPE,
            "fields": DPF_FIELDS_CONTAINER_DATA_TYPE,
            "per_set_table": 'COREX.DataTypes.Any',
            "summary": 'COREX.DataTypes.Any',
        },
        "required_inputs": ("model",),
        "time_scope_default": "all_sets",
    },
    DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID: {
        "display_name": "DPF Time History Probe",
        "surface_family": "dpf_workflow",
        "ports": ("model", "series", "table", "time_values"),
        "properties": (
            "result_name",
            "selection_mode",
            "named_selection",
            "node_ids",
            "element_ids",
            "location",
            "time_scope_mode",
            "set_ids",
            "time_values",
        ),
        "output_types": {
            "series": DPF_FIELDS_CONTAINER_DATA_TYPE,
            "table": 'COREX.DataTypes.Any',
            "time_values": 'COREX.DataTypes.Any',
        },
        "required_inputs": ("model",),
        "selection_mode_default": "choose_scope",
        "time_scope_default": "all_sets",
    },
    DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID: {
        "display_name": "DPF Stress Invariants",
        "surface_family": "dpf_workflow",
        "ports": ("model", "fields", "mesh_scoping", "time_scoping"),
        "properties": (
            "invariant",
            "selection_mode",
            "named_selection",
            "node_ids",
            "element_ids",
            "location",
            "time_scope_mode",
            "set_ids",
            "time_values",
        ),
        "output_types": {
            "fields": DPF_FIELDS_CONTAINER_DATA_TYPE,
            "mesh_scoping": DPF_SCOPING_DATA_TYPE,
            "time_scoping": DPF_SCOPING_DATA_TYPE,
        },
        "required_inputs": ("model",),
        "time_scope_default": "first_set",
    },
    DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID: {
        "display_name": "DPF Mode Shape Viewer",
        "ports": (
            'path',
            "result_file",
            "model",
            "fields",
            "mesh_scoping",
            "time_scoping",
            "mesh",
            "session",
            "frequency",
            "normalized_path",
        ),
        "properties": (
            'path',
            "mode",
            "selection_mode",
            "named_selection",
            "node_ids",
            "element_ids",
            "location",
            "output_mode",
            DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
            "colormap",
            "result_component",
            "scalar_range_mode",
            "scalar_range_min",
            "scalar_range_max",
            "show_scalar_bar",
            "deform_scale",
            "hover_probe",
            "show_minmax_markers",
            "viewer_background",
            "camera_bookmarks",
        ),
        "output_types": {
            "result_file": DPF_RESULT_FILE_DATA_TYPE,
            "model": DPF_MODEL_DATA_TYPE,
            "fields": DPF_FIELDS_CONTAINER_DATA_TYPE,
            "mesh_scoping": DPF_SCOPING_DATA_TYPE,
            "time_scoping": DPF_SCOPING_DATA_TYPE,
            "mesh": DPF_MESH_DATA_TYPE,
            "session": VIEWER_SESSION_DATA_TYPE,
            "frequency": 'COREX.DataTypes.Double',
            "normalized_path": 'COREX.DataTypes.Path',
        },
        "output_mode_default": "both",
        "deform_scale_default": "auto",
        "surface_family": "viewer",
        "render_quality": {
            "supported_quality_tiers": ("full", "proxy"),
        },
        "required_inputs": ('path',),
    },
    DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID: {
        "display_name": "DPF Field Math",
        "surface_family": "dpf_workflow",
        "ports": ("a", "b", "fields"),
        "properties": ("operation", "scalar"),
        "output_types": {
            "fields": DPF_FIELDS_CONTAINER_DATA_TYPE,
        },
        "required_inputs": ("a",),
    },
    DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID: {
        "display_name": "DPF Table Export",
        "surface_family": "dpf_workflow",
        "ports": ("fields", "model", "csv", "table", "exports"),
        "properties": ("artifact_key", "include_coordinates", "output_mode"),
        "output_types": {
            "csv": 'COREX.DataTypes.Path',
            "table": 'COREX.DataTypes.Any',
            "exports": 'COREX.DataTypes.Any',
        },
        "output_mode_default": DPF_OUTPUT_MODE_STORED,
        "required_inputs": ("fields", "model"),
    },
    DPF_MESH_SCOPING_NODE_TYPE_ID: {
        "display_name": "DPF Mesh Scoping",
        "ports": ("model", "scoping"),
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
        "ports": ("model", "scoping"),
        "properties": ("set_ids", "time_values", "output_mode"),
        "output_types": {"scoping": DPF_SCOPING_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
    },
    DPF_RESULT_FIELD_NODE_TYPE_ID: {
        "display_name": "DPF Result Field",
        "ports": ("model", "mesh_scoping", "time_scoping", "field"),
        "properties": ("result_name", "location", "set_ids", "time_values", "output_mode"),
        "output_types": {"field": DPF_FIELD_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
        "required_inputs": ("model",),
    },
    DPF_FIELD_OPS_NODE_TYPE_ID: {
        "display_name": "DPF Field Ops",
        "ports": ("field", "model", "field_out", "field_min", "field_max"),
        "properties": ("operation", "location", "output_mode"),
        "output_types": {
            "field_out": DPF_FIELD_DATA_TYPE,
            "field_min": DPF_FIELD_DATA_TYPE,
            "field_max": DPF_FIELD_DATA_TYPE,
        },
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
        "required_inputs": ("field",),
    },
    DPF_MESH_EXTRACT_NODE_TYPE_ID: {
        "display_name": "DPF Mesh Extract",
        "ports": ("model", "mesh_scoping", "mesh"),
        "properties": ("nodes_only", "output_mode"),
        "output_types": {"mesh": DPF_MESH_DATA_TYPE},
        "output_mode_default": DPF_OUTPUT_MODE_MEMORY,
        "required_inputs": ("model",),
    },
    DPF_EXPORT_NODE_TYPE_ID: {
        "display_name": "DPF Export",
        "ports": ("field", "model", "mesh", "dataset", "exports", "csv", "png", "vtu", "vtm"),
        "properties": ("artifact_key", "export_formats", "output_mode"),
        "output_types": {
            "dataset": 'COREX.DataTypes.Any',
            "exports": 'COREX.DataTypes.Any',
            "csv": 'COREX.DataTypes.Path',
            "png": 'COREX.DataTypes.Path',
            "vtu": 'COREX.DataTypes.Path',
            "vtm": 'COREX.DataTypes.Path',
        },
        "output_mode_default": DPF_OUTPUT_MODE_STORED,
        "required_inputs": ("field", "model"),
    },
    DPF_VIEWER_NODE_TYPE_ID: {
        "display_name": "DPF Viewer",
        "ports": ("field", "model", "mesh", "session"),
        "properties": (
            "output_mode",
            DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
            "colormap",
            "result_component",
            "scalar_range_mode",
            "scalar_range_min",
            "scalar_range_max",
            "show_scalar_bar",
            "deform_scale",
            "hover_probe",
            "show_minmax_markers",
            "viewer_background",
            "camera_bookmarks",
        ),
        "output_types": {"session": VIEWER_SESSION_DATA_TYPE},
        "output_mode_default": "both",
        "surface_family": "viewer",
        "render_quality": {
            "supported_quality_tiers": ("full", "proxy"),
        },
        "required_inputs": ("model",),
    },
}

_EXPECTED_DPF_TITLE_ICON_PATHS = {
    DPF_RESULT_FILE_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_MODEL_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_MESH_SCOPING_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_TIME_SCOPING_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_RESULT_FIELD_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_FIELD_OPS_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_MESH_EXTRACT_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_EXPORT_NODE_TYPE_ID: "dpf/ansys.svg",
    DPF_VIEWER_NODE_TYPE_ID: "dpf/ansys.svg",
}

_EXPECTED_DPF_CATEGORY_PATHS = {
    DPF_RESULT_FILE_NODE_TYPE_ID: DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
    DPF_MODEL_NODE_TYPE_ID: DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
    DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_MESH_SCOPING_NODE_TYPE_ID: DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_TIME_SCOPING_NODE_TYPE_ID: DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_RESULT_FIELD_NODE_TYPE_ID: operator_family_category_path("result"),
    DPF_FIELD_OPS_NODE_TYPE_ID: operator_family_category_path("math"),
    DPF_MESH_EXTRACT_NODE_TYPE_ID: DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
    DPF_EXPORT_NODE_TYPE_ID: DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_VIEWER_NODE_TYPE_ID: DPF_VIEWER_CATEGORY_PATH,
}

_EXPECTED_DPF_DESCRIPTOR_ORDER = (
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_FIELD_OPS_NODE_TYPE_ID,
)

_GENERATED_DPF_RESULT_OPERATOR_TYPE_ID = "dpf.op.result.displacement"
_GENERATED_DPF_MATH_OPERATOR_TYPE_ID = "dpf.op.math.add"


class DpfNodeCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._preferences_path = Path(self._temp_dir.name) / "app_preferences.json"
        self._store = AppPreferencesStore(path_provider=lambda: self._preferences_path)
        self.registry = build_default_registry(app_preferences_store=self._store)

    def tearDown(self) -> None:
        ansys_dpf_catalog.invalidate_ansys_dpf_descriptor_cache()
        self._temp_dir.cleanup()

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
            worker_services=services or dpf_worker_services(),
        )

    def test_public_dpf_data_type_contracts_remain_stable(self) -> None:
        self.assertEqual(
            DPF_PUBLIC_DATA_TYPES,
            (
                DPF_MODEL_DATA_TYPE,
                DPF_MESH_DATA_TYPE,
                DPF_FIELD_DATA_TYPE,
                DPF_SCOPING_DATA_TYPE,
                VIEWER_SESSION_DATA_TYPE,
            ),
        )
        self.assertNotIn(DPF_RESULT_FILE_DATA_TYPE, DPF_PUBLIC_DATA_TYPES)

    def test_dpf_plugin_availability_reports_missing_dependency_without_crashing(self) -> None:
        with patch.object(ansys_dpf_catalog, "_find_spec", return_value=None):
            availability = ansys_dpf_catalog.get_ansys_dpf_plugin_availability()

        self.assertFalse(availability.is_available)
        self.assertEqual(availability.state, "missing_dependency")
        self.assertEqual(availability.missing_dependencies, (ansys_dpf_catalog.ANSYS_DPF_DEPENDENCY,))

    def test_ansys_dpf_catalog_returns_no_descriptors_when_dependency_is_missing(self) -> None:
        with patch.object(ansys_dpf_catalog, "_find_spec", return_value=None):
            self.assertEqual(ansys_dpf_catalog.load_ansys_dpf_plugin_descriptors(), ())

        self.assertFalse(hasattr(ansys_dpf_module, "ANSYS_DPF_PLUGIN_DESCRIPTORS"))
        self.assertFalse(hasattr(ansys_dpf_module, "ANSYS_DPF_NODE_PLUGINS"))

    def test_dpf_backend_uses_package_owned_addon_manifest_metadata(self) -> None:
        backend = ansys_dpf_catalog.ANSYS_DPF_PLUGIN_BACKEND

        self.assertIsNotNone(backend.addon_manifest)
        self.assertEqual(backend.addon_manifest, ANSYS_DPF_ADDON_MANIFEST)
        self.assertEqual(backend.plugin_id, ANSYS_DPF_ADDON_MANIFEST.addon_id)
        self.assertEqual(backend.display_name, ANSYS_DPF_ADDON_MANIFEST.display_name)
        self.assertEqual(backend.runtime_backends, ANSYS_DPF_RUNTIME_BACKENDS)
        self.assertEqual(backend.toolchains, ANSYS_DPF_TOOLCHAINS)
        self.assertEqual(backend.artifacts, ANSYS_DPF_ARTIFACTS)
        self.assertEqual(backend.surface_capabilities, ANSYS_DPF_SURFACE_CAPABILITIES)
        self.assertEqual(backend.contract_manifest, ANSYS_DPF_ADDON_MANIFEST.contract_manifest)

    def test_default_registry_keeps_non_dpf_nodes_when_backend_is_missing(self) -> None:
        with patch.object(ansys_dpf_catalog, "_find_spec", return_value=None):
            registry = build_default_registry(app_preferences_store=self._store)

        self.assertIsNotNone(registry.spec_or_none("core.constant"))
        self.assertEqual(registry.filter_nodes(category=DPF_NODE_CATEGORY), [])
        self.assertNotIn(DPF_NODE_CATEGORY_PATH, registry.category_paths())
        self.assertIsNone(registry.spec_or_none(DPF_RESULT_FILE_NODE_TYPE_ID))

    def test_build_default_registry_refreshes_descriptor_cache_when_dpf_version_changes(self) -> None:
        exact_version = "0.15.0.dev1+build.42"
        self._store.persist_document(
            set_ansys_dpf_plugin_state(
                default_app_preferences_document(),
                version="0.14.0",
                catalog_cache_version="0.14.0",
            )
        )
        ansys_dpf_catalog.invalidate_ansys_dpf_descriptor_cache()

        with (
            patch.object(ansys_dpf_catalog, "_find_spec", return_value=object()),
            patch.object(
                ansys_dpf_catalog,
                "resolve_ansys_dpf_plugin_version",
                return_value=exact_version,
            ),
            patch.object(
                ansys_dpf_catalog,
                "_build_ansys_dpf_plugin_descriptors",
                return_value=(),
            ) as build_descriptors,
            patch("ea_node_editor.addons.registry_contributions.register_plugin_backends", return_value=[]),
            patch(
                "ea_node_editor.nodes.plugin_loader.discover_configured_static_plugins",
                return_value=[],
            ),
        ):
            build_default_registry(app_preferences_store=self._store)

        document = self._store.load_document()
        self.assertEqual(document["plugins"]["ansys_dpf"]["version"], exact_version)
        self.assertEqual(document["plugins"]["ansys_dpf"]["catalog_cache_version"], exact_version)
        build_descriptors.assert_called_once_with()

    def test_build_default_registry_skips_descriptor_rebuild_when_dpf_version_is_unchanged(self) -> None:
        exact_version = "0.15.0.dev1+build.42"
        self._store.persist_document(
            set_ansys_dpf_plugin_state(
                default_app_preferences_document(),
                version=exact_version,
                catalog_cache_version=exact_version,
            )
        )
        ansys_dpf_catalog.invalidate_ansys_dpf_descriptor_cache()

        with (
            patch.object(ansys_dpf_catalog, "_find_spec", return_value=object()),
            patch.object(
                ansys_dpf_catalog,
                "resolve_ansys_dpf_plugin_version",
                return_value=exact_version,
            ),
            patch.object(
                ansys_dpf_catalog,
                "_build_ansys_dpf_plugin_descriptors",
                return_value=(),
            ) as build_descriptors,
            patch("ea_node_editor.addons.registry_contributions.register_plugin_backends", return_value=[]),
            patch(
                "ea_node_editor.nodes.plugin_loader.discover_configured_static_plugins",
                return_value=[],
            ),
        ):
            build_default_registry(app_preferences_store=self._store)

        document = self._store.load_document()
        self.assertEqual(document["plugins"]["ansys_dpf"]["version"], exact_version)
        self.assertEqual(document["plugins"]["ansys_dpf"]["catalog_cache_version"], exact_version)
        build_descriptors.assert_not_called()

    def test_build_default_registry_leaves_dpf_plugin_state_untouched_when_dependency_is_missing(self) -> None:
        persisted = self._store.persist_document(
            set_ansys_dpf_plugin_state(
                default_app_preferences_document(),
                version="0.15.0.dev1+build.42",
                catalog_cache_version="0.15.0.dev1+build.42",
            )
        )
        before = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        ansys_dpf_catalog.invalidate_ansys_dpf_descriptor_cache()

        with patch.object(ansys_dpf_catalog, "_find_spec", return_value=None):
            build_default_registry(app_preferences_store=self._store)

        after = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(after, before)
        self.assertEqual(self._store.load_document()["plugins"]["ansys_dpf"], persisted["plugins"]["ansys_dpf"])

    @unittest.skipIf(dpf is None, "ansys.dpf.core is not installed")
    def test_default_registry_registers_foundational_dpf_nodes(self) -> None:
        for type_id, expected in _EXPECTED_DPF_SPECS.items():
            spec = self.registry.get_spec(type_id)

            self.assertEqual(spec.display_name, expected["display_name"])
            self.assertEqual(spec.runtime_behavior, "active")
            self.assertEqual(spec.surface_family, expected.get("surface_family", "standard"))
            self.assertEqual(tuple(port.key for port in spec.ports), expected["ports"])
            self.assertEqual(tuple(prop.key for prop in spec.properties), expected["properties"])

            properties_by_key = {prop.key: prop for prop in spec.properties}
            if "output_mode_default" in expected:
                output_mode = properties_by_key["output_mode"]
                self.assertEqual(output_mode.default, expected["output_mode_default"])
                self.assertEqual(output_mode.enum_values, ("memory", "stored", "both"))
            else:
                self.assertNotIn("output_mode", properties_by_key)
            ports_by_key = {port.key: port for port in spec.ports}
            for port_key in expected.get("required_inputs", ()):
                self.assertTrue(ports_by_key[port_key].required)
            if "time_scope_default" in expected:
                time_scope = properties_by_key["time_scope_mode"]
                self.assertEqual(time_scope.default, expected["time_scope_default"])
                self.assertEqual(
                    time_scope.enum_values,
                    ("first_set", "last_set", "all_sets", "set_ids", "time_values"),
                )
            if "selection_mode_default" in expected:
                self.assertEqual(
                    properties_by_key["selection_mode"].default,
                    expected["selection_mode_default"],
                )
            if "deform_scale_default" in expected:
                self.assertEqual(
                    properties_by_key["deform_scale"].default,
                    expected["deform_scale_default"],
                )
            if spec.type_id == DPF_VIEWER_NODE_TYPE_ID:
                self.assertEqual(
                    ports_by_key["field"].accepted_data_types,
                    (DPF_FIELD_DATA_TYPE, DPF_FIELDS_CONTAINER_DATA_TYPE),
                )
            if spec.type_id in {
                DPF_VIEWER_NODE_TYPE_ID,
                DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
                DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
            }:
                show_edges = properties_by_key[DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY]
                self.assertEqual(show_edges.type, "bool")
                self.assertFalse(show_edges.default)
                self.assertEqual(show_edges.inspector_editor, "toggle")
                self.assertEqual(show_edges.group, "View")
                self.assertEqual(spec.surface_family, expected["surface_family"])
                self.assertEqual(
                    spec.render_quality.supported_quality_tiers,
                    expected["render_quality"]["supported_quality_tiers"],
                )

            for port_key, data_type in expected["output_types"].items():
                self.assertEqual(ports_by_key[port_key].data_type, data_type)

    @unittest.skipIf(dpf is None, "ansys.dpf.core is not installed")
    def test_nested_category_registry_dpf_catalog_publishes_library_taxonomy_paths(self) -> None:
        for type_id in _EXPECTED_DPF_SPECS:
            with self.subTest(type_id=type_id):
                spec = self.registry.get_spec(type_id)
                expected_path = _EXPECTED_DPF_CATEGORY_PATHS[type_id]
                self.assertEqual(spec.category_path, expected_path)
                self.assertEqual(spec.category, category_display(expected_path))

    def test_operator_backed_dpf_descriptors_publish_normalized_source_metadata_contract(self) -> None:
        descriptors = {
            descriptor.spec.type_id: descriptor.spec
            for descriptor in ansys_dpf_catalog.load_ansys_dpf_plugin_descriptors()
        }

        result_field = descriptors[DPF_RESULT_FIELD_NODE_TYPE_ID]
        self.assertEqual(result_field.source_metadata.backend, "ansys.dpf.core")
        self.assertEqual(len(result_field.source_metadata.variants), 1)
        self.assertEqual(
            result_field.source_metadata.variants[0].key,
            DPF_RESULT_FIELD_OPERATOR_VARIANT_KEY,
        )
        self.assertEqual(
            result_field.source_metadata.variants[0].operator_name_template,
            "result.{result_name}",
        )
        self.assertEqual(result_field.source_metadata.source_path, "ansys.dpf.core.operators.result")
        self.assertEqual(result_field.source_metadata.family_path, operator_family_path("result"))
        self.assertEqual(result_field.source_metadata.stability, "core")
        result_ports = {port.key: port for port in result_field.ports}
        self.assertEqual(result_ports["model"].source_metadata.pin_name, "data_sources")
        self.assertEqual(result_ports["model"].source_metadata.presence, "required")
        self.assertEqual(result_ports["time_scoping"].source_metadata.pin_name, "time_scoping")
        self.assertEqual(
            result_ports["time_scoping"].source_metadata.exclusive_group,
            DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
        )
        self.assertEqual(result_ports["field"].source_metadata.pin_name, "fields_container")
        self.assertEqual(result_ports["field"].source_metadata.pin_direction, "output")
        result_properties = {prop.key: prop for prop in result_field.properties}
        self.assertEqual(result_properties["location"].source_metadata.pin_name, "requested_location")
        self.assertEqual(
            result_properties["location"].source_metadata.omission_semantics,
            "operator_default",
        )
        self.assertEqual(result_properties["set_ids"].source_metadata.pin_name, "time_scoping")
        self.assertEqual(result_properties["time_values"].source_metadata.pin_name, "time_scoping")
        self.assertEqual(
            result_properties["set_ids"].source_metadata.exclusive_group,
            DPF_TIME_SELECTION_EXCLUSIVE_GROUP,
        )

        field_ops = descriptors[DPF_FIELD_OPS_NODE_TYPE_ID]
        self.assertEqual(
            {variant.key for variant in field_ops.source_metadata.variants},
            {
                DPF_FIELD_OPS_VARIANT_NORM,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL,
                DPF_FIELD_OPS_VARIANT_MIN_MAX,
            },
        )
        self.assertEqual(field_ops.source_metadata.source_path, "ansys.dpf.core.operators.math")
        self.assertEqual(field_ops.source_metadata.family_path, operator_family_path("math"))
        self.assertEqual(field_ops.source_metadata.stability, "core")
        field_ops_ports = {port.key: port for port in field_ops.ports}
        self.assertEqual(field_ops_ports["field"].source_metadata.pin_name, "fields_container")
        self.assertEqual(
            set(field_ops_ports["field"].source_metadata.variant_keys),
            {
                DPF_FIELD_OPS_VARIANT_NORM,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL,
                DPF_FIELD_OPS_VARIANT_MIN_MAX,
            },
        )
        self.assertEqual(field_ops_ports["model"].source_metadata.pin_name, "mesh")
        self.assertEqual(
            set(field_ops_ports["model"].source_metadata.variant_keys),
            {
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_NODAL,
                DPF_FIELD_OPS_VARIANT_CONVERT_LOCATION_ELEMENTAL,
            },
        )
        self.assertEqual(field_ops_ports["field_out"].source_metadata.pin_name, "fields_container")
        self.assertEqual(field_ops_ports["field_min"].source_metadata.pin_name, "field_min")
        self.assertEqual(field_ops_ports["field_max"].source_metadata.pin_name, "field_max")

        displacement = descriptors[_GENERATED_DPF_RESULT_OPERATOR_TYPE_ID]
        self.assertEqual(displacement.category_path, operator_family_category_path("result"))
        self.assertEqual(displacement.source_metadata.variants[0].operator_name, "U")
        self.assertEqual(
            displacement.source_metadata.source_path,
            "ansys.dpf.core.operators.result.displacement",
        )
        self.assertEqual(displacement.source_metadata.family_path, operator_family_path("result"))
        self.assertEqual(displacement.source_metadata.stability, "core")
        displacement_ports = {port.key: port for port in displacement.ports}
        self.assertTrue(displacement_ports["data_sources"].required)
        self.assertTrue(displacement_ports["data_sources"].exposed)
        self.assertEqual(
            displacement_ports["data_sources"].data_type,
            "COREX.Ansys.DPF.DataSources",
        )
        self.assertFalse(displacement_ports["time_scoping"].exposed)
        self.assertIn(
            DPF_SCOPING_DATA_TYPE,
            displacement_ports["time_scoping"].accepted_data_types,
        )
        displacement_properties = {prop.key: prop for prop in displacement.properties}
        self.assertEqual(displacement_properties["bool_rotate_to_global"].type, "bool")
        self.assertTrue(displacement_properties["bool_rotate_to_global"].expose_port_toggle)

        self.assertIsNone(descriptors[DPF_MODEL_NODE_TYPE_ID].source_metadata)
        self.assertIsNone(descriptors[DPF_EXPORT_NODE_TYPE_ID].source_metadata)
        self.assertIsNone(descriptors[DPF_VIEWER_NODE_TYPE_ID].source_metadata)

    def test_dpf_source_metadata_tables_cover_operator_backed_descriptor_keys(self) -> None:
        self.assertEqual(
            set(DPF_NODE_SOURCE_METADATA_BY_TYPE_ID),
            {DPF_RESULT_FIELD_NODE_TYPE_ID, DPF_FIELD_OPS_NODE_TYPE_ID},
        )
        self.assertEqual(
            set(DPF_PORT_SOURCE_METADATA_BY_TYPE_ID[DPF_RESULT_FIELD_NODE_TYPE_ID]),
            {"model", "mesh_scoping", "time_scoping", "field"},
        )
        self.assertEqual(
            set(DPF_PROPERTY_SOURCE_METADATA_BY_TYPE_ID[DPF_RESULT_FIELD_NODE_TYPE_ID]),
            {"location", "set_ids", "time_values"},
        )
        self.assertEqual(
            set(DPF_PORT_SOURCE_METADATA_BY_TYPE_ID[DPF_FIELD_OPS_NODE_TYPE_ID]),
            {"field", "model", "field_out", "field_min", "field_max"},
        )
        self.assertNotIn(DPF_FIELD_OPS_NODE_TYPE_ID, DPF_PROPERTY_SOURCE_METADATA_BY_TYPE_ID)

    def test_dpf_descriptors_declare_and_evaluate_readiness_centrally(self) -> None:
        specs = {
            plugin().spec().type_id: normalize_dpf_descriptor_spec(plugin().spec())
            for plugin in (
                DpfResultFileNodePlugin,
                DpfModelNodePlugin,
                DpfMeshScopingNodePlugin,
                DpfTimeScopingNodePlugin,
                DpfResultFieldNodePlugin,
                DpfFieldOpsNodePlugin,
                DpfMeshExtractNodePlugin,
                DpfExportNodePlugin,
                DpfViewerNodePlugin,
                DpfWorkflowResultSourceNodePlugin,
                DpfWorkflowResultViewerNodePlugin,
                DpfWorkflowModeShapeViewerNodePlugin,
            )
        }
        for spec in specs.values():
            for port in spec.ports:
                if port.direction == "in" and port.kind == "data":
                    self.assertIsInstance(port.required, bool, (spec.type_id, port.key))

        def issues(
            type_id: str,
            *,
            present_ports: tuple[str, ...] = (),
            overridden_ports: tuple[str, ...] = (),
            properties: dict[str, object] | None = None,
        ):
            return evaluate_node_readiness(
                specs[type_id],
                port_has_value={key: True for key in present_ports},
                overridden_port_keys=overridden_ports,
                properties=properties or {},
            )

        model_issues = issues(DPF_MODEL_NODE_TYPE_ID)
        self.assertEqual(model_issues[0].target_keys, ("result_file", "path"))
        self.assertFalse(issues(DPF_MODEL_NODE_TYPE_ID, properties={"path": "model.rst"}))
        self.assertTrue(
            issues(
                DPF_MODEL_NODE_TYPE_ID,
                overridden_ports=("path",),
                properties={"path": "model.rst"},
            )
        )

        named_selection_issues = issues(
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            properties={"selection_mode": "named_selection"},
        )
        self.assertEqual(
            {issue.target_keys for issue in named_selection_issues},
            {("model",), ("named_selection",)},
        )
        self.assertEqual(
            issues(
                DPF_MESH_SCOPING_NODE_TYPE_ID,
                properties={"selection_mode": "node_ids"},
            )[0].target_keys,
            ("node_ids",),
        )

        self.assertEqual(
            issues(DPF_TIME_SCOPING_NODE_TYPE_ID)[0].target_keys,
            ("set_ids", "time_values"),
        )
        self.assertFalse(
            issues(DPF_TIME_SCOPING_NODE_TYPE_ID, properties={"set_ids": "1"})
        )
        self.assertEqual(
            issues(DPF_TIME_SCOPING_NODE_TYPE_ID, properties={"time_values": "0.0"})[0].target_keys,
            ("model",),
        )

        field_ops = specs[DPF_FIELD_OPS_NODE_TYPE_ID]
        field_ops_ports = {port.key: port for port in field_ops.ports}
        self.assertTrue(field_ops_ports["field"].required)
        self.assertFalse(field_ops_ports["model"].required)
        self.assertFalse(
            issues(
                DPF_FIELD_OPS_NODE_TYPE_ID,
                present_ports=("field",),
                properties={"operation": "norm"},
            )
        )
        self.assertEqual(
            issues(
                DPF_FIELD_OPS_NODE_TYPE_ID,
                present_ports=("field",),
                properties={"operation": "convert_location"},
            )[0].target_keys,
            ("model",),
        )

    def test_dpf_catalog_descriptors_remain_authoritative_and_stable(self) -> None:
        descriptors = ansys_dpf_catalog.load_ansys_dpf_plugin_descriptors()
        node_plugins = tuple(descriptor.factory for descriptor in descriptors)

        if dpf is None:
            self.assertEqual(descriptors, ())
            self.assertEqual(node_plugins, ())
            return

        actual_type_ids = tuple(descriptor.spec.type_id for descriptor in descriptors)
        helper_type_ids = tuple(
            descriptor.spec.type_id
            for descriptor in load_ansys_dpf_helper_plugin_descriptors()
        )
        plot_type_ids = tuple(
            descriptor.spec.type_id
            for descriptor in load_ansys_dpf_plot_plugin_descriptors()
        )
        curated_type_ids = tuple(
            descriptor.spec.type_id
            for descriptor in load_ansys_dpf_curated_plugin_descriptors()
        )
        operator_type_ids = tuple(
            descriptor.spec.type_id
            for descriptor in load_ansys_dpf_operator_plugin_descriptors()
        )

        self.assertEqual(actual_type_ids[: len(helper_type_ids)], helper_type_ids)
        curated_start = len(helper_type_ids)
        self.assertEqual(
            actual_type_ids[curated_start : curated_start + len(curated_type_ids)],
            curated_type_ids,
        )
        plot_start = curated_start + len(curated_type_ids)
        self.assertEqual(
            actual_type_ids[plot_start : plot_start + len(plot_type_ids)],
            plot_type_ids,
        )
        operator_start = plot_start + len(plot_type_ids)
        self.assertEqual(
            actual_type_ids[operator_start : operator_start + len(operator_type_ids)],
            operator_type_ids,
        )
        self.assertEqual(plot_type_ids, DPF_PLOT_NODE_TYPE_IDS)
        self.assertEqual(
            operator_type_ids[:2],
            (DPF_RESULT_FIELD_NODE_TYPE_ID, DPF_FIELD_OPS_NODE_TYPE_ID),
        )
        self.assertIn(_GENERATED_DPF_RESULT_OPERATOR_TYPE_ID, actual_type_ids)
        self.assertIn(_GENERATED_DPF_MATH_OPERATOR_TYPE_ID, actual_type_ids)
        self.assertTrue(any(type_id.startswith("dpf.op.") for type_id in actual_type_ids))
        self.assertEqual(tuple(descriptor.factory for descriptor in descriptors), node_plugins)

    def test_title_icon_dpf_specs_use_packaged_relative_assets(self) -> None:
        for plugin_factory in (
            DpfResultFileNodePlugin,
            DpfModelNodePlugin,
            DpfMeshScopingNodePlugin,
            DpfTimeScopingNodePlugin,
            DpfResultFieldNodePlugin,
            DpfFieldOpsNodePlugin,
            DpfMeshExtractNodePlugin,
            DpfExportNodePlugin,
            DpfViewerNodePlugin,
            DpfWorkflowResultSourceNodePlugin,
            DpfWorkflowResultFieldsNodePlugin,
            DpfWorkflowResultViewerNodePlugin,
            DpfWorkflowMinMaxEnvelopeNodePlugin,
            DpfWorkflowTimeHistoryProbeNodePlugin,
            DpfWorkflowStressInvariantsNodePlugin,
            DpfWorkflowModeShapeViewerNodePlugin,
            DpfWorkflowFieldMathNodePlugin,
            DpfWorkflowTableExportNodePlugin,
        ):
            spec = plugin_factory().spec()
            expected_icon = _EXPECTED_DPF_TITLE_ICON_PATHS[spec.type_id]
            asset_path = NODE_TITLE_ICON_ASSET_ROOT / expected_icon

            self.assertEqual(spec.icon, expected_icon)
            self.assertEqual(title_icon_source_for_node_payload(spec), asset_path.resolve().as_uri())

    def test_default_registry_exposes_dpf_category_and_scoping_ports(self) -> None:
        dpf_specs = self.registry.filter_nodes(category_path=DPF_NODE_CATEGORY_PATH)

        if dpf is None:
            self.assertEqual(dpf_specs, [])
            self.assertNotIn(DPF_NODE_CATEGORY_PATH, self.registry.category_paths())
            self.assertEqual(
                self.registry.filter_nodes(data_type=DPF_SCOPING_DATA_TYPE, direction="out"),
                [],
            )
            return

        dpf_type_ids = {spec.type_id for spec in dpf_specs}
        self.assertTrue(set(_EXPECTED_DPF_SPECS).issubset(dpf_type_ids))
        self.assertTrue(set(DPF_PLOT_NODE_TYPE_IDS).issubset(dpf_type_ids))
        self.assertIn(_GENERATED_DPF_RESULT_OPERATOR_TYPE_ID, dpf_type_ids)
        self.assertIn(_GENERATED_DPF_MATH_OPERATOR_TYPE_ID, dpf_type_ids)
        self.assertGreater(len(dpf_type_ids), len(_EXPECTED_DPF_SPECS))
        self.assertTrue(
            {
                DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
                DPF_WORKFLOW_CATEGORY_PATH,
                DPF_HELPERS_SCOPING_CATEGORY_PATH,
                DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
                DPF_HELPERS_SUPPORT_CATEGORY_PATH,
                DPF_VIEWER_CATEGORY_PATH,
                DPF_PLOT_CATEGORY_PATH,
                operator_family_category_path("result"),
                operator_family_category_path("math"),
            }.issubset({spec.category_path for spec in dpf_specs})
        )
        self.assertIn(DPF_NODE_CATEGORY_PATH, self.registry.category_paths())
        scoping_output_type_ids = {
            spec.type_id
            for spec in self.registry.filter_nodes(data_type=DPF_SCOPING_DATA_TYPE, direction="out")
        }
        self.assertTrue(
            {DPF_MESH_SCOPING_NODE_TYPE_ID, DPF_TIME_SCOPING_NODE_TYPE_ID}.issubset(scoping_output_type_ids)
        )
        self.assertTrue(any(type_id.startswith("dpf.op.") for type_id in scoping_output_type_ids))

    @unittest.skipIf(dpf is None, "ansys.dpf.core is not installed")
    def test_result_file_and_model_nodes_emit_handle_based_outputs(self) -> None:
        services = dpf_worker_services()

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
        services = dpf_worker_services()
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
        services = dpf_worker_services()
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
        # Set ids are cumulative set numbers; the step-based location would
        # mis-read them as load steps on multi-substep (e.g. modal) results.
        self.assertEqual(time_scoping.location, "TimeFreq_sets")


if __name__ == "__main__":
    unittest.main()
