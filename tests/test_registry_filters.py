from __future__ import annotations

import unittest
from unittest.mock import patch

from ea_node_editor.addons.tabular_data import catalog as tabular_catalog
from ea_node_editor.addons.tabular_data.input_node import TABULAR_DATA_INPUT_NODE_TYPE_ID
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
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
    DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
    DPF_HELPERS_CATEGORY_PATH,
    DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_INPUTS_CATEGORY_PATH,
    DPF_NODE_CATEGORY,
    DPF_NODE_CATEGORY_PATH,
    DPF_RAW_API_MIRROR_CATEGORY_PATH,
    DPF_VIEWER_CATEGORY_PATH,
    DPF_WORKFLOW_CATEGORY_PATH,
    operator_family_category_path,
)
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.category_paths import category_display
from ea_node_editor.nodes.instance_resolution import resolve_instance_ports
from ea_node_editor.runtime_contracts import (
    ARRAY_DATA_REF_TYPE_ID,
    PATH_DATA_TYPE_ID,
    TABULAR_DATA_REF_TYPE_ID,
)


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
_UTILITIES_CATEGORY_PATH = ("Utilities",)
_CANVAS_CATEGORY_PATH = ("Utilities", "Canvas")
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
                "passive.flowchart.card",
                "passive.flowchart.callout",
                "passive.flowchart.multi_document",
                "passive.flowchart.tick",
                "passive.flowchart.timestamp",
                "passive.flowchart.message",
                "passive.flowchart.isometric_cube",
                "passive.flowchart.cube",
                "passive.flowchart.actor",
                "passive.flowchart.star",
                "passive.flowchart.x",
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
                "passive.annotation.text",
            },
        )
        self.assertTrue(results)
        self.assertTrue(all(spec.category == "Annotation" for spec in results))

    def test_group_is_listed_under_utilities_canvas_parent_and_leaf_filters(self) -> None:
        registry = build_default_registry()
        group_type_id = "passive.annotation.group_backdrop"

        parent_results = registry.filter_nodes(query="group", category_path=_UTILITIES_CATEGORY_PATH)
        leaf_results = registry.filter_nodes(query="group", category_path=_CANVAS_CATEGORY_PATH)

        self.assertIn(group_type_id, {spec.type_id for spec in parent_results})
        self.assertIn(group_type_id, {spec.type_id for spec in leaf_results})
        group_spec = next(spec for spec in leaf_results if spec.type_id == group_type_id)
        self.assertEqual(group_spec.display_name, "Group")
        self.assertEqual(group_spec.category_path, _CANVAS_CATEGORY_PATH)
        self.assertIn(_UTILITIES_CATEGORY_PATH, registry.category_paths())
        self.assertIn(_CANVAS_CATEGORY_PATH, registry.category_paths())

    def test_filter_by_text_and_category(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(query="excel", category_path=_INPUT_OUTPUT_CATEGORY_PATH)
        type_ids = {spec.type_id for spec in results}
        self.assertIn("io.excel_read", type_ids)
        self.assertIn("io.excel_write", type_ids)

    def test_filter_by_data_type_and_direction(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(data_type=PATH_DATA_TYPE_ID, direction="in")
        self.assertTrue(any(spec.type_id == "io.file_read" for spec in results))

    def test_tabular_data_input_is_filterable_when_addon_available(self) -> None:
        with patch.object(tabular_catalog, "_find_spec", return_value=object()):
            registry = build_default_registry()

        path_results = registry.filter_nodes(data_type=PATH_DATA_TYPE_ID, direction="in")
        tabular_results = registry.filter_nodes(
            data_type=TABULAR_DATA_REF_TYPE_ID,
            direction="out",
        )
        array_results = registry.filter_nodes(
            data_type=ARRAY_DATA_REF_TYPE_ID,
            direction="out",
        )

        self.assertIn(TABULAR_DATA_INPUT_NODE_TYPE_ID, {spec.type_id for spec in path_results})
        self.assertEqual([spec.type_id for spec in tabular_results], [TABULAR_DATA_INPUT_NODE_TYPE_ID])
        self.assertEqual([spec.type_id for spec in array_results], [TABULAR_DATA_INPUT_NODE_TYPE_ID])

    def test_filter_by_direction_only_returns_matching_nodes(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(direction="in")
        self.assertTrue(results)
        self.assertTrue(
            all(
                any(port.direction == "in" for port in resolve_instance_ports(spec, {}))
                for spec in results
            )
        )

    def test_combined_filters_apply_as_intersection(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(
            query="write",
            category_path=_INPUT_OUTPUT_CATEGORY_PATH,
            direction="in",
            data_type=PATH_DATA_TYPE_ID,
        )
        self.assertEqual(
            [spec.type_id for spec in results],
            ["io.excel_write", "io.image_export", "io.file_write"],
        )

    def test_filter_results_use_stable_predictable_sorting(self) -> None:
        registry = build_default_registry()
        first = [spec.type_id for spec in registry.filter_nodes(category_path=_INPUT_OUTPUT_CATEGORY_PATH)]
        second = [spec.type_id for spec in registry.filter_nodes(category_path=_INPUT_OUTPUT_CATEGORY_PATH)]
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            [
                spec.type_id
                for spec in sorted(
                    registry.filter_nodes(category_path=_INPUT_OUTPUT_CATEGORY_PATH),
                    key=lambda spec: (spec.display_name.casefold(), spec.type_id.casefold()),
                )
            ],
        )

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
        self.assertIn(DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_WORKFLOW_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_HELPERS_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_HELPERS_SCOPING_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_HELPERS_CONTAINERS_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_HELPERS_SUPPORT_CATEGORY_PATH, category_paths)
        self.assertIn(DPF_RAW_API_MIRROR_CATEGORY_PATH, category_paths)
        self.assertIn(operator_family_category_path("result"), category_paths)
        self.assertIn(operator_family_category_path("math"), category_paths)
        self.assertIn(DPF_VIEWER_CATEGORY_PATH, category_paths)
        self.assertIn(category_display(DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH), categories)
        self.assertIn(category_display(DPF_WORKFLOW_CATEGORY_PATH), categories)
        self.assertIn(category_display(DPF_HELPERS_SCOPING_CATEGORY_PATH), categories)
        self.assertIn(category_display(DPF_HELPERS_CONTAINERS_CATEGORY_PATH), categories)
        self.assertIn(category_display(DPF_HELPERS_SUPPORT_CATEGORY_PATH), categories)
        self.assertIn(category_display(operator_family_category_path("result")), categories)
        self.assertIn(category_display(operator_family_category_path("math")), categories)
        self.assertIn(category_display(DPF_VIEWER_CATEGORY_PATH), categories)
        self.assertNotIn(category_display(DPF_NODE_CATEGORY_PATH), categories)
        self.assertNotIn(category_display(DPF_HELPERS_CATEGORY_PATH), categories)
        # The flat Operators bucket is fully retired: every dpf.op.* mirror
        # lives under Advanced > Raw API Mirror now.
        self.assertNotIn(("Ansys DPF", "Operators"), category_paths)
        self.assertNotIn(category_display(("Ansys DPF", "Operators")), categories)
        self.assertIn(("Flowchart",), category_paths)


if __name__ == "__main__":
    unittest.main()
