from __future__ import annotations

import unittest

from ea_node_editor.addons.ansys_dpf import catalog as ansys_dpf_catalog
from ea_node_editor.addons.ansys_dpf.helper_catalog import (
    load_ansys_dpf_helper_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.curated_catalog import (
    load_ansys_dpf_curated_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.operator_catalog import (
    load_ansys_dpf_operator_plugin_descriptors,
)
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
    DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
    DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
    DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
    DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
    DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
    DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
    DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
    DPF_ADVANCED_CATEGORY_PATH,
    DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_HELPERS_FACTORIES_CATEGORY_PATH,
    DPF_HELPERS_MODELS_CATEGORY_PATH,
    DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_INPUTS_CATEGORY_PATH,
    DPF_NODE_CATEGORY_PATH,
    DPF_OPERATOR_FAMILY_ORDER,
    DPF_VIEWER_CATEGORY_PATH,
    DPF_WORKFLOW_CATEGORY_PATH,
    helper_role_category_path,
    operator_family_category_path,
    operator_family_from_source_path,
    operator_family_path,
    operator_source_path,
)


class DpfLibraryTaxonomyTests(unittest.TestCase):
    def tearDown(self) -> None:
        ansys_dpf_catalog.invalidate_ansys_dpf_descriptor_cache()

    def test_taxonomy_defines_first_wave_roots_and_helper_roles(self) -> None:
        self.assertEqual(DPF_NODE_CATEGORY_PATH, ("Ansys DPF",))
        self.assertEqual(DPF_INPUTS_CATEGORY_PATH, ("Ansys DPF", "Inputs"))
        self.assertEqual(DPF_WORKFLOW_CATEGORY_PATH, ("Ansys DPF", "Workflow"))
        self.assertEqual(DPF_VIEWER_CATEGORY_PATH, ("Ansys DPF", "Viewer"))
        self.assertEqual(DPF_ADVANCED_CATEGORY_PATH, ("Ansys DPF", "Advanced"))
        self.assertEqual(
            DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
            ("Ansys DPF", "Advanced", "Building Blocks"),
        )
        self.assertEqual(helper_role_category_path("models"), DPF_HELPERS_MODELS_CATEGORY_PATH)
        self.assertEqual(helper_role_category_path("scoping"), DPF_HELPERS_SCOPING_CATEGORY_PATH)
        self.assertEqual(helper_role_category_path("factories"), DPF_HELPERS_FACTORIES_CATEGORY_PATH)
        self.assertEqual(helper_role_category_path("containers"), DPF_HELPERS_CONTAINERS_CATEGORY_PATH)
        self.assertEqual(helper_role_category_path("support"), DPF_HELPERS_SUPPORT_CATEGORY_PATH)

    def test_operator_family_mapping_tracks_library_family_names(self) -> None:
        self.assertEqual(DPF_OPERATOR_FAMILY_ORDER[:6], ("result", "math", "utility", "mesh", "averaging", "logic"))
        self.assertEqual(operator_source_path("result"), "ansys.dpf.core.operators.result")
        self.assertEqual(operator_family_from_source_path("ansys.dpf.core.operators.math.norm_fc"), "math")
        self.assertEqual(
            operator_family_category_path("result"),
            ("Ansys DPF", "Advanced", "Raw API Mirror", "Result"),
        )
        self.assertEqual(operator_family_path("math"), ("Advanced", "Raw API Mirror", "Math"))
        self.assertEqual(
            operator_family_category_path("serialization"),
            ("Ansys DPF", "Advanced", "Raw API Mirror", "Serialization"),
        )

    def test_catalog_split_keeps_helper_and_operator_scopes_disjoint(self) -> None:
        foundational_helper_type_ids = {
            DPF_RESULT_FILE_NODE_TYPE_ID,
            DPF_MODEL_NODE_TYPE_ID,
            DPF_MESH_SCOPING_NODE_TYPE_ID,
            DPF_TIME_SCOPING_NODE_TYPE_ID,
            DPF_MESH_EXTRACT_NODE_TYPE_ID,
            DPF_EXPORT_NODE_TYPE_ID,
            DPF_VIEWER_NODE_TYPE_ID,
        }
        foundational_operator_type_ids = {DPF_RESULT_FIELD_NODE_TYPE_ID, DPF_FIELD_OPS_NODE_TYPE_ID}
        curated_workflow_type_ids = {
            DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID,
            DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID,
            DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID,
            DPF_WORKFLOW_MIN_MAX_ENVELOPE_NODE_TYPE_ID,
            DPF_WORKFLOW_TIME_HISTORY_PROBE_NODE_TYPE_ID,
            DPF_WORKFLOW_STRESS_INVARIANTS_NODE_TYPE_ID,
            DPF_WORKFLOW_MODE_SHAPE_VIEWER_NODE_TYPE_ID,
            DPF_WORKFLOW_FIELD_MATH_NODE_TYPE_ID,
            DPF_WORKFLOW_TABLE_EXPORT_NODE_TYPE_ID,
        }
        helper_descriptors = load_ansys_dpf_helper_plugin_descriptors()
        curated_descriptors = load_ansys_dpf_curated_plugin_descriptors()
        operator_descriptors = load_ansys_dpf_operator_plugin_descriptors()

        helper_type_ids = {
            descriptor.spec.type_id
            for descriptor in helper_descriptors
            if descriptor.spec.type_id in foundational_helper_type_ids
        }
        operator_type_ids = {
            descriptor.spec.type_id
            for descriptor in operator_descriptors
            if descriptor.spec.type_id in foundational_operator_type_ids
        }
        curated_type_ids = {
            descriptor.spec.type_id
            for descriptor in curated_descriptors
            if descriptor.spec.type_id in curated_workflow_type_ids
        }

        self.assertEqual(helper_type_ids, foundational_helper_type_ids)
        self.assertEqual(curated_type_ids, curated_workflow_type_ids)
        self.assertEqual(operator_type_ids, foundational_operator_type_ids)
        self.assertFalse(helper_type_ids & operator_type_ids)
        self.assertFalse(helper_type_ids & curated_type_ids)
        self.assertFalse(curated_type_ids & operator_type_ids)

        descriptors = {
            descriptor.spec.type_id: descriptor.spec
            for descriptor in ansys_dpf_catalog.load_ansys_dpf_plugin_descriptors()
        }
        self.assertEqual(
            descriptors[DPF_RESULT_FILE_NODE_TYPE_ID].category_path,
            DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
        )
        self.assertEqual(
            descriptors[DPF_MODEL_NODE_TYPE_ID].category_path,
            DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
        )
        self.assertEqual(
            descriptors[DPF_WORKFLOW_RESULT_SOURCE_NODE_TYPE_ID].category_path,
            DPF_WORKFLOW_CATEGORY_PATH,
        )
        self.assertEqual(
            descriptors[DPF_WORKFLOW_RESULT_FIELDS_NODE_TYPE_ID].category_path,
            DPF_WORKFLOW_CATEGORY_PATH,
        )
        self.assertEqual(
            descriptors[DPF_WORKFLOW_RESULT_VIEWER_NODE_TYPE_ID].category_path,
            DPF_WORKFLOW_CATEGORY_PATH,
        )
        self.assertEqual(
            descriptors[DPF_MESH_SCOPING_NODE_TYPE_ID].category_path,
            DPF_HELPERS_SCOPING_CATEGORY_PATH,
        )
        self.assertEqual(
            descriptors[DPF_TIME_SCOPING_NODE_TYPE_ID].category_path,
            DPF_HELPERS_SCOPING_CATEGORY_PATH,
        )
        self.assertEqual(
            descriptors[DPF_MESH_EXTRACT_NODE_TYPE_ID].category_path,
            DPF_ADVANCED_BUILDING_BLOCKS_CATEGORY_PATH,
        )
        self.assertEqual(
            descriptors[DPF_EXPORT_NODE_TYPE_ID].category_path,
            DPF_HELPERS_SUPPORT_CATEGORY_PATH,
        )
        self.assertEqual(descriptors[DPF_VIEWER_NODE_TYPE_ID].category_path, DPF_VIEWER_CATEGORY_PATH)
        self.assertEqual(
            descriptors[DPF_RESULT_FIELD_NODE_TYPE_ID].category_path,
            operator_family_category_path("result"),
        )
        self.assertEqual(
            descriptors[DPF_FIELD_OPS_NODE_TYPE_ID].category_path,
            operator_family_category_path("math"),
        )


if __name__ == "__main__":
    unittest.main()
