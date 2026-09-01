from __future__ import annotations

import unittest
from types import SimpleNamespace

from ea_node_editor.nodes.builtins.ansys_dpf import (
    DpfExportNodePlugin,
    DpfFieldOpsNodePlugin,
    DpfMeshExtractNodePlugin,
    DpfMeshScopingNodePlugin,
    DpfModelNodePlugin,
    DpfResultFieldNodePlugin,
    DpfResultFileNodePlugin,
    DpfTimeScopingNodePlugin,
    DpfWorkflowFieldMathNodePlugin,
    DpfWorkflowMinMaxEnvelopeNodePlugin,
    DpfWorkflowModeShapeViewerNodePlugin,
    DpfWorkflowResultFieldsNodePlugin,
    DpfWorkflowResultSourceNodePlugin,
    DpfWorkflowResultViewerNodePlugin,
    DpfWorkflowStressInvariantsNodePlugin,
    DpfWorkflowTableExportNodePlugin,
    DpfWorkflowTimeHistoryProbeNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import dpf_output_mode_property
from ea_node_editor.ui.shell.inspector_projection import (
    build_selected_node_property_items,
)


def _groups_by_key(spec) -> dict[str, str]:
    return {prop.key: prop.group for prop in spec.properties}


class DpfOutputModeFactoryGroupTests(unittest.TestCase):
    def test_factory_defaults_to_post_group(self) -> None:
        self.assertEqual(dpf_output_mode_property().group, "Post")

    def test_factory_group_override_round_trips(self) -> None:
        self.assertEqual(dpf_output_mode_property(group="Source").group, "Source")


class DpfConcreteSpecGroupTests(unittest.TestCase):
    def test_result_file_node_properties_match_source_post_mapping(self) -> None:
        groups = _groups_by_key(DpfResultFileNodePlugin().spec())
        self.assertEqual(groups, {"path": "Source", "output_mode": "Post"})

    def test_model_node_properties_match_source_post_mapping(self) -> None:
        groups = _groups_by_key(DpfModelNodePlugin().spec())
        self.assertEqual(groups, {"path": "Source", "output_mode": "Post"})

    def test_workflow_result_source_properties_match_source_post_mapping(self) -> None:
        groups = _groups_by_key(DpfWorkflowResultSourceNodePlugin().spec())
        self.assertEqual(groups, {"path": "Source"})

    def test_workflow_result_fields_properties_cluster_selection_time_and_post(self) -> None:
        groups = _groups_by_key(DpfWorkflowResultFieldsNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "result_name": "Selection",
                "selection_mode": "Selection",
                "named_selection": "Selection",
                "node_ids": "Selection",
                "element_ids": "Selection",
                "location": "Selection",
                "time_scope_mode": "Time",
                "set_ids": "Time",
                "time_values": "Time",
            },
        )

    def test_workflow_result_viewer_properties_cluster_source_selection_time_post_and_view(self) -> None:
        groups = _groups_by_key(DpfWorkflowResultViewerNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "path": "Source",
                "result_name": "Selection",
                "selection_mode": "Selection",
                "named_selection": "Selection",
                "node_ids": "Selection",
                "element_ids": "Selection",
                "location": "Selection",
                "time_scope_mode": "Time",
                "set_ids": "Time",
                "time_values": "Time",
                "output_mode": "Post",
                "show_mesh_edges": "View",
                "colormap": "View",
                "result_component": "View",
                "scalar_range_mode": "View",
                "scalar_range_min": "View",
                "scalar_range_max": "View",
                "show_scalar_bar": "View",
                "deform_scale": "View",
                "hover_probe": "View",
                "show_minmax_markers": "View",
                "viewer_background": "View",
                "camera_bookmarks": "View",
            },
        )

    def test_workflow_min_max_envelope_properties_cluster_selection_time_and_post(self) -> None:
        groups = _groups_by_key(DpfWorkflowMinMaxEnvelopeNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "result_name": "Selection",
                "selection_mode": "Selection",
                "named_selection": "Selection",
                "node_ids": "Selection",
                "element_ids": "Selection",
                "location": "Selection",
                "time_scope_mode": "Time",
                "set_ids": "Time",
                "time_values": "Time",
            },
        )

    def test_workflow_time_history_probe_properties_cluster_selection_time_and_post(self) -> None:
        groups = _groups_by_key(DpfWorkflowTimeHistoryProbeNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "result_name": "Selection",
                "selection_mode": "Selection",
                "named_selection": "Selection",
                "node_ids": "Selection",
                "element_ids": "Selection",
                "location": "Selection",
                "time_scope_mode": "Time",
                "set_ids": "Time",
                "time_values": "Time",
            },
        )

    def test_workflow_stress_invariants_properties_cluster_selection_time_and_post(self) -> None:
        groups = _groups_by_key(DpfWorkflowStressInvariantsNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "invariant": "Selection",
                "selection_mode": "Selection",
                "named_selection": "Selection",
                "node_ids": "Selection",
                "element_ids": "Selection",
                "location": "Selection",
                "time_scope_mode": "Time",
                "set_ids": "Time",
                "time_values": "Time",
            },
        )

    def test_workflow_mode_shape_viewer_properties_cluster_source_selection_post_and_view(self) -> None:
        groups = _groups_by_key(DpfWorkflowModeShapeViewerNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "path": "Source",
                "mode": "Selection",
                "selection_mode": "Selection",
                "named_selection": "Selection",
                "node_ids": "Selection",
                "element_ids": "Selection",
                "location": "Selection",
                "output_mode": "Post",
                "show_mesh_edges": "View",
                "colormap": "View",
                "result_component": "View",
                "scalar_range_mode": "View",
                "scalar_range_min": "View",
                "scalar_range_max": "View",
                "show_scalar_bar": "View",
                "deform_scale": "View",
                "hover_probe": "View",
                "show_minmax_markers": "View",
                "viewer_background": "View",
                "camera_bookmarks": "View",
            },
        )

    def test_workflow_field_math_properties_are_entirely_post(self) -> None:
        groups = _groups_by_key(DpfWorkflowFieldMathNodePlugin().spec())
        self.assertEqual(
            groups,
            {"operation": "Post", "scalar": "Post"},
        )

    def test_workflow_table_export_properties_are_entirely_post(self) -> None:
        groups = _groups_by_key(DpfWorkflowTableExportNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "artifact_key": "Post",
                "include_coordinates": "Post",
                "output_mode": "Post",
            },
        )

    def test_mesh_scoping_node_properties_cluster_selection_and_post(self) -> None:
        groups = _groups_by_key(DpfMeshScopingNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "selection_mode": "Selection",
                "named_selection": "Selection",
                "node_ids": "Selection",
                "element_ids": "Selection",
                "location": "Selection",
                "set_ids": "Selection",
                "time_values": "Selection",
                "output_mode": "Post",
            },
        )

    def test_time_scoping_node_properties_cluster_selection_and_post(self) -> None:
        groups = _groups_by_key(DpfTimeScopingNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "set_ids": "Selection",
                "time_values": "Selection",
                "output_mode": "Post",
            },
        )

    def test_result_field_node_properties_cluster_selection_and_post(self) -> None:
        groups = _groups_by_key(DpfResultFieldNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "result_name": "Selection",
                "location": "Selection",
                "set_ids": "Selection",
                "time_values": "Selection",
                "output_mode": "Post",
            },
        )

    def test_field_ops_node_properties_are_entirely_post(self) -> None:
        groups = _groups_by_key(DpfFieldOpsNodePlugin().spec())
        self.assertEqual(
            groups,
            {"operation": "Post", "location": "Post", "output_mode": "Post"},
        )

    def test_mesh_extract_node_properties_are_entirely_post(self) -> None:
        groups = _groups_by_key(DpfMeshExtractNodePlugin().spec())
        self.assertEqual(groups, {"nodes_only": "Post", "output_mode": "Post"})

    def test_export_node_properties_are_entirely_post(self) -> None:
        groups = _groups_by_key(DpfExportNodePlugin().spec())
        self.assertEqual(
            groups,
            {
                "artifact_key": "Post",
                "export_formats": "Post",
                "output_mode": "Post",
            },
        )


class DpfPayloadEmitsMultipleGroupsTests(unittest.TestCase):
    def test_mesh_scoping_payload_emits_selection_and_advanced_groups(self) -> None:
        spec = DpfMeshScopingNodePlugin().spec()
        node = SimpleNamespace(
            type_id=spec.type_id,
            node_id="dpf-mesh-scoping-node",
            properties={},
            port_labels={},
            exposed_ports={},
        )
        items = build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
        )
        emitted = {str(item["group"]) for item in items}
        self.assertIn("Selection", emitted)
        self.assertIn("Advanced", emitted)
        self.assertNotIn("Properties", emitted)


if __name__ == "__main__":
    unittest.main()
