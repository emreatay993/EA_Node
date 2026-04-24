from __future__ import annotations

import unittest

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_COMPUTE_CATEGORY_PATH,
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_HELPERS_CATEGORY_PATH,
    DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_INPUTS_CATEGORY_PATH,
    DPF_NODE_CATEGORY,
    DPF_NODE_CATEGORY_PATH,
    DPF_OPERATORS_CATEGORY_PATH,
    DPF_VIEWER_CATEGORY_PATH,
    DPF_WORKFLOW_CATEGORY_PATH,
    operator_family_category_path,
)
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.category_paths import category_display


_DPF_HELPER_TYPE_IDS = {
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
}
_DPF_OPERATOR_TYPE_IDS = {
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_FIELD_OPS_NODE_TYPE_ID,
}
_DPF_SCOPING_TYPE_IDS = {
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
}
_DPF_ALL_TYPE_IDS = _DPF_HELPER_TYPE_IDS | _DPF_OPERATOR_TYPE_IDS
_ANNOTATION_CATEGORY_PATH = ("Annotation",)
_FLOWCHART_CATEGORY_PATH = ("Flowchart",)
_INPUT_OUTPUT_CATEGORY_PATH = ("Input / Output",)
_PLANNING_CATEGORY_PATH = ("Planning",)


class RegistryFilterTests(unittest.TestCase):
    def test_flowchart_category_exposes_locked_passive_catalog(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(category_path=_FLOWCHART_CATEGORY_PATH)

        self.assertEqual(
            {spec.type_id for spec in results},
            {
                "passive.flowchart.start",
                "passive.flowchart.end",
                "passive.flowchart.process",
                "passive.flowchart.decision",
                "passive.flowchart.document",
                "passive.flowchart.connector",
                "passive.flowchart.input_output",
                "passive.flowchart.predefined_process",
                "passive.flowchart.database",
            },
        )
        self.assertTrue(results)
        self.assertTrue(all(spec.category == "Flowchart" for spec in results))

    def test_planning_category_exposes_locked_passive_catalog(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(category_path=_PLANNING_CATEGORY_PATH)

        self.assertEqual(
            {spec.type_id for spec in results},
            {
                "passive.planning.task_card",
                "passive.planning.milestone_card",
                "passive.planning.risk_card",
                "passive.planning.decision_card",
            },
        )
        self.assertTrue(results)
        self.assertTrue(all(spec.category == "Planning" for spec in results))

    def test_annotation_category_exposes_locked_passive_catalog(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(category_path=_ANNOTATION_CATEGORY_PATH)

        self.assertEqual(
            {spec.type_id for spec in results},
            {
                "passive.annotation.sticky_note",
                "passive.annotation.callout",
                "passive.annotation.section_header",
                "passive.annotation.comment_backdrop",
            },
        )
        self.assertTrue(results)
        self.assertTrue(all(spec.category == "Annotation" for spec in results))

    def test_filter_by_text_and_category(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(query="excel", category_path=_INPUT_OUTPUT_CATEGORY_PATH)
        type_ids = {spec.type_id for spec in results}
        self.assertIn("io.excel_read", type_ids)
        self.assertIn("io.excel_write", type_ids)

    def test_filter_by_data_type_and_direction(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(data_type="path", direction="in")
        self.assertTrue(any(spec.type_id == "io.file_read" for spec in results))

    def test_filter_by_direction_only_returns_matching_nodes(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(direction="in")
        self.assertTrue(results)
        self.assertTrue(all(any(port.direction == "in" for port in spec.ports) for spec in results))

    def test_combined_filters_apply_as_intersection(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(
            query="write",
            category_path=_INPUT_OUTPUT_CATEGORY_PATH,
            direction="in",
            data_type="path",
        )
        self.assertEqual([spec.type_id for spec in results], ["io.excel_write", "io.file_write"])

    def test_filter_results_use_stable_predictable_sorting(self) -> None:
        registry = build_default_registry()
        first = [spec.type_id for spec in registry.filter_nodes(category_path=_INPUT_OUTPUT_CATEGORY_PATH)]
        second = [spec.type_id for spec in registry.filter_nodes(category_path=_INPUT_OUTPUT_CATEGORY_PATH)]
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first, key=lambda item: item.lower()))

    def test_nested_category_registry_filter_accepts_parent_category_path(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(category_path=DPF_NODE_CATEGORY_PATH)

        result_type_ids = {spec.type_id for spec in results}
        self.assertTrue(_DPF_ALL_TYPE_IDS.issubset(result_type_ids))
        self.assertTrue(all(spec.category_path[0] == DPF_NODE_CATEGORY for spec in results))

    def test_nested_category_registry_legacy_flat_category_alias_is_not_descendant_inclusive(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(category=DPF_NODE_CATEGORY.lower())

        self.assertEqual(results, [])

    def test_nested_category_registry_leaf_category_path_filter_is_precise(self) -> None:
        registry = build_default_registry()
        scoping_results = registry.filter_nodes(category_path=DPF_HELPERS_SCOPING_CATEGORY_PATH)
        result_results = registry.filter_nodes(category_path=operator_family_category_path("result"))
        viewer_results = registry.filter_nodes(category_path=DPF_VIEWER_CATEGORY_PATH)

        self.assertTrue(_DPF_SCOPING_TYPE_IDS.issubset({spec.type_id for spec in scoping_results}))
        self.assertIn(DPF_RESULT_FIELD_NODE_TYPE_ID, {spec.type_id for spec in result_results})
        self.assertEqual([spec.type_id for spec in viewer_results], [DPF_VIEWER_NODE_TYPE_ID])
        self.assertTrue(all(spec.category_path == DPF_HELPERS_SCOPING_CATEGORY_PATH for spec in scoping_results))
        self.assertTrue(all(spec.category_path == operator_family_category_path("result") for spec in result_results))
        self.assertEqual(viewer_results[0].category_path, DPF_VIEWER_CATEGORY_PATH)

    def test_nested_category_registry_category_paths_include_dpf_ancestors(self) -> None:
        registry = build_default_registry()
        category_paths = registry.category_paths()
        categories = registry.categories()

        self.assertIn(DPF_NODE_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_INPUTS_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_COMPUTE_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_WORKFLOW_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_HELPERS_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_HELPERS_SCOPING_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_HELPERS_CONTAINERS_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_HELPERS_SUPPORT_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_OPERATORS_CATEGORY_PATH, category_paths)
        self.assertIn(operator_family_category_path("result"), category_paths)
        self.assertIn(operator_family_category_path("math"), category_paths)
        self.assertIn(DPF_VIEWER_CATEGORY_PATH, category_paths)
        self.assertIn(category_display(DPF_COMPUTE_CATEGORY_PATH), categories)
        self.assertIn(category_display(DPF_WORKFLOW_CATEGORY_PATH), categories)
        self.assertIn(category_display(DPF_HELPERS_SCOPING_CATEGORY_PATH), categories)
        self.assertIn(category_display(DPF_HELPERS_CONTAINERS_CATEGORY_PATH), categories)
        self.assertIn(category_display(DPF_HELPERS_SUPPORT_CATEGORY_PATH), categories)
        self.assertIn(category_display(operator_family_category_path("result")), categories)
        self.assertIn(category_display(operator_family_category_path("math")), categories)
        self.assertIn(category_display(DPF_VIEWER_CATEGORY_PATH), categories)
        self.assertNotIn(category_display(DPF_NODE_CATEGORY_PATH), categories)
        self.assertNotIn(category_display(DPF_HELPERS_CATEGORY_PATH), categories)
        self.assertNotIn(category_display(DPF_OPERATORS_CATEGORY_PATH), categories)
        self.assertIn(("Flowchart",), category_paths)


if __name__ == "__main__":
    unittest.main()
