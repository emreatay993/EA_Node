# Purpose: Publish bundled, task-oriented DPF graph fragments in the node library.
# Map: docs/agent_maps/feature_routes/ansys_dpf_operator_viewer_transport.md
# Tests: tests/test_dpf_workflow_recipes.py
from __future__ import annotations

import copy
from typing import Any

from ea_node_editor.graph.fragment_payloads import (
    build_graph_fragment_payload,
    normalize_graph_fragment_payload,
)
from ea_node_editor.graph.record_payloads import (
    edge_instance_to_mapping,
    node_instance_to_mapping,
)
from ea_node_editor.graph.records import EdgeInstance, NodeInstance
from ea_node_editor.nodes.builtins.ansys_dpf_curated import (
    DpfWorkflowResultFieldsNodePlugin,
    DpfWorkflowResultSourceNodePlugin,
    DpfWorkflowResultViewerNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_curated_post import (
    DpfWorkflowFieldMathNodePlugin,
    DpfWorkflowMinMaxEnvelopeNodePlugin,
    DpfWorkflowStressInvariantsNodePlugin,
    DpfWorkflowTableExportNodePlugin,
    DpfWorkflowTimeHistoryProbeNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import DPF_NODE_CATEGORY
from ea_node_editor.nodes.builtins.plot.dpf import DPF_PLOT_NODE_DESCRIPTORS

DPF_RECIPE_CATEGORY_PATH = (DPF_NODE_CATEGORY, "Recipes")
DPF_RECIPE_WORKFLOW_IDS = (
    "wf_dpf_view_one_result",
    "wf_dpf_peak_all_sets",
    "wf_dpf_probe_over_time",
    "wf_dpf_stress_to_csv",
    "wf_dpf_compare_first_last",
)
_RECIPE_COLUMN_SPACING = 420.0
_COMPARE_ROW_SPACING = 420.0


def _plugin_spec(plugin_type: type[Any]) -> Any:
    return getattr(plugin_type, "__node_type_spec__")


_NODE_SPECS = {
    spec.type_id: spec
    for spec in (
        _plugin_spec(DpfWorkflowResultSourceNodePlugin),
        _plugin_spec(DpfWorkflowResultFieldsNodePlugin),
        _plugin_spec(DpfWorkflowResultViewerNodePlugin),
        _plugin_spec(DpfWorkflowMinMaxEnvelopeNodePlugin),
        _plugin_spec(DpfWorkflowTimeHistoryProbeNodePlugin),
        _plugin_spec(DpfWorkflowStressInvariantsNodePlugin),
        _plugin_spec(DpfWorkflowFieldMathNodePlugin),
        _plugin_spec(DpfWorkflowTableExportNodePlugin),
        next(descriptor.spec for descriptor in DPF_PLOT_NODE_DESCRIPTORS if descriptor.spec.type_id == "dpf.plot.line"),
    )
}


def _node(
    ref_id: str,
    type_id: str,
    x: float,
    y: float,
    **property_overrides: Any,
) -> dict[str, Any]:
    spec = _NODE_SPECS[type_id]
    properties = {prop.key: copy.deepcopy(prop.default) for prop in spec.properties}
    unknown_properties = set(property_overrides).difference(properties)
    if unknown_properties:
        raise KeyError(f"Unknown {type_id} recipe properties: {sorted(unknown_properties)}")
    properties.update(copy.deepcopy(property_overrides))
    return node_instance_to_mapping(
        NodeInstance(
            node_id=ref_id,
            type_id=type_id,
            title=spec.display_name,
            x=x,
            y=y,
            properties=properties,
            exposed_ports={port.key: bool(port.exposed) for port in spec.ports},
        ),
        node_id_key="ref_id",
    )


def _edge(source_ref_id: str, source_port_key: str, target_ref_id: str, target_port_key: str) -> dict[str, Any]:
    return edge_instance_to_mapping(
        EdgeInstance(
            edge_id="",
            source_node_id=source_ref_id,
            source_port_key=source_port_key,
            target_node_id=target_ref_id,
            target_port_key=target_port_key,
        ),
        edge_id_key=None,
        source_node_id_key="source_ref_id",
        target_node_id_key="target_ref_id",
    )


def _fragment(*, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = normalize_graph_fragment_payload(build_graph_fragment_payload(nodes=nodes, edges=edges))
    if normalized is None:
        raise RuntimeError("Bundled DPF recipe produced an invalid graph fragment.")
    return normalized


def _definition(
    workflow_id: str,
    name: str,
    description: str,
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "workflow_id": workflow_id,
        "name": name,
        "description": description,
        "revision": 1,
        "ports": [],
        "fragment": _fragment(nodes=nodes, edges=edges),
        "workflow_scope": "bundled",
        "category_path": list(DPF_RECIPE_CATEGORY_PATH),
    }


def _view_one_result() -> dict[str, Any]:
    return _definition(
        DPF_RECIPE_WORKFLOW_IDS[0],
        "View One Result",
        "Choose a result file, result type, scope, and set, then view it in the embedded DPF viewer.",
        nodes=[
            _node(
                "viewer",
                "dpf.workflow.result_viewer",
                0.0,
                0.0,
                path="",
                result_name="displacement",
                selection_mode="all",
                time_scope_mode="first_set",
            )
        ],
        edges=[],
    )


def _peak_over_all_sets() -> dict[str, Any]:
    return _definition(
        DPF_RECIPE_WORKFLOW_IDS[1],
        "Peak Over All Sets",
        "Choose a result file and quantity, then find its minimum and maximum over every result set.",
        nodes=[
            _node("source", "dpf.workflow.result_source", 0.0, 0.0, path=""),
            _node(
                "envelope",
                "dpf.workflow.min_max_envelope",
                _RECIPE_COLUMN_SPACING,
                0.0,
                result_name="displacement",
                time_scope_mode="all_sets",
            ),
        ],
        edges=[
            _edge("source", "model", "envelope", "model"),
        ],
    )


def _probe_over_time() -> dict[str, Any]:
    return _definition(
        DPF_RECIPE_WORKFLOW_IDS[2],
        "Probe Versus Time",
        "Choose a result file and scope, then plot one time or frequency history per selected entity.",
        nodes=[
            _node("source", "dpf.workflow.result_source", 0.0, 0.0, path=""),
            _node(
                "probe",
                "dpf.workflow.time_history_probe",
                _RECIPE_COLUMN_SPACING,
                0.0,
                result_name="displacement",
                selection_mode="choose_scope",
                time_scope_mode="all_sets",
            ),
            _node(
                "plot",
                "dpf.plot.line",
                2 * _RECIPE_COLUMN_SPACING,
                0.0,
                frame_selector="all",
                title="DPF Time History",
                x_label="Time / Frequency",
                y_label="Result",
            ),
        ],
        edges=[
            _edge("source", "model", "probe", "model"),
            _edge("probe", "series", "plot", "series"),
        ],
    )


def _stress_to_csv() -> dict[str, Any]:
    return _definition(
        DPF_RECIPE_WORKFLOW_IDS[3],
        "Von Mises Stress to CSV",
        "Choose a result file and scope, calculate von Mises stress, and export entity rows to CSV.",
        nodes=[
            _node("source", "dpf.workflow.result_source", 0.0, 0.0, path=""),
            _node(
                "stress",
                "dpf.workflow.stress_invariants",
                _RECIPE_COLUMN_SPACING,
                0.0,
                invariant="von_mises",
                time_scope_mode="first_set",
            ),
            _node(
                "export",
                "dpf.workflow.table_export",
                2 * _RECIPE_COLUMN_SPACING,
                0.0,
                artifact_key="von_mises_stress",
            ),
        ],
        edges=[
            _edge("source", "model", "stress", "model"),
            _edge("stress", "fields", "export", "fields"),
            _edge("source", "model", "export", "model"),
        ],
    )


def _compare_first_last() -> dict[str, Any]:
    return _definition(
        DPF_RECIPE_WORKFLOW_IDS[4],
        "Compare First and Last Result",
        "Choose a result file and quantity, then subtract the first result set from the last.",
        nodes=[
            _node(
                "source",
                "dpf.workflow.result_source",
                0.0,
                _COMPARE_ROW_SPACING / 2,
                path="",
            ),
            _node(
                "first",
                "dpf.workflow.result_fields",
                _RECIPE_COLUMN_SPACING,
                0.0,
                result_name="displacement",
                time_scope_mode="first_set",
            ),
            _node(
                "last",
                "dpf.workflow.result_fields",
                _RECIPE_COLUMN_SPACING,
                _COMPARE_ROW_SPACING,
                result_name="displacement",
                time_scope_mode="last_set",
            ),
            _node(
                "subtract",
                "dpf.workflow.field_math",
                2 * _RECIPE_COLUMN_SPACING,
                _COMPARE_ROW_SPACING / 2,
                operation="subtract",
            ),
        ],
        edges=[
            _edge("source", "model", "first", "model"),
            _edge("source", "model", "last", "model"),
            _edge("last", "fields", "subtract", "a"),
            _edge("first", "fields", "subtract", "b"),
        ],
    )


_ANSYS_DPF_WORKFLOW_DEFINITIONS = (
    _view_one_result(),
    _peak_over_all_sets(),
    _probe_over_time(),
    _stress_to_csv(),
    _compare_first_last(),
)


def create_ansys_dpf_workflow_definitions() -> tuple[dict[str, Any], ...]:
    return copy.deepcopy(_ANSYS_DPF_WORKFLOW_DEFINITIONS)


__all__ = [
    "DPF_RECIPE_CATEGORY_PATH",
    "DPF_RECIPE_WORKFLOW_IDS",
    "create_ansys_dpf_workflow_definitions",
]
