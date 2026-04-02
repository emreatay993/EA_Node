from __future__ import annotations

import unittest
from pathlib import Path

from ea_node_editor.graph import transforms
from ea_node_editor.graph.mutation_service import WorkspaceMutationService

REPO_ROOT = Path(__file__).resolve().parents[1]


class GraphArchitectureBoundaryTests(unittest.TestCase):
    def test_graph_mutation_service_uses_graph_owned_boundary_adapters(self) -> None:
        mutation_service_text = (REPO_ROOT / "ea_node_editor" / "graph" / "mutation_service.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "from ea_node_editor.ui.pdf_preview_provider import clamp_pdf_page_number",
            mutation_service_text,
        )
        self.assertNotIn(
            "from ea_node_editor.ui_qml.edge_routing import node_size",
            mutation_service_text,
        )
        self.assertNotIn("from ea_node_editor.graph.transforms import", mutation_service_text)
        self.assertIn(
            "from ea_node_editor.graph.boundary_adapters import GraphBoundaryAdapters, fallback_graph_boundary_adapters",
            mutation_service_text,
        )
        self.assertIn(
            "boundary_adapters: GraphBoundaryAdapters = field(default_factory=fallback_graph_boundary_adapters)",
            mutation_service_text,
        )
        self.assertIn("self.boundary_adapters.node_size(", mutation_service_text)
        self.assertIn("self.boundary_adapters.clamp_pdf_page_number(", mutation_service_text)

    def test_scene_bridge_injects_ui_boundary_implementations_without_global_installation(self) -> None:
        bridge_text = (REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_bridge.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("from ea_node_editor.graph.boundary_adapters import build_graph_boundary_adapters", bridge_text)
        self.assertIn("from ea_node_editor.ui.pdf_preview_provider import clamp_pdf_page_number", bridge_text)
        self.assertIn("from ea_node_editor.ui_qml.edge_routing import node_size", bridge_text)
        self.assertNotIn("set_graph_boundary_adapters(", bridge_text)
        self.assertIn("self._boundary_adapters = build_graph_boundary_adapters(", bridge_text)
        self.assertIn("self._payload_builder = GraphScenePayloadBuilder(boundary_adapters=self._boundary_adapters)", bridge_text)
        self.assertIn("boundary_adapters=self._boundary_adapters", bridge_text)

    def test_graph_model_externalizes_workspace_persistence_state(self) -> None:
        model_text = (REPO_ROOT / "ea_node_editor" / "graph" / "model.py").read_text(encoding="utf-8")
        codec_text = (REPO_ROOT / "ea_node_editor" / "persistence" / "project_codec.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("from ea_node_editor.persistence.overlay import", model_text)
        self.assertIn("return import_module(_PERSISTENCE_OVERLAY_MODULE)", model_text)
        self.assertNotIn("WorkspacePersistenceState", model_text)
        self.assertNotIn("persistence_state: WorkspacePersistenceState = field(", model_text)
        self.assertIn("restore_workspace_persistence_state(workspace, persistence_state)", codec_text)

    def test_graph_file_issue_module_is_a_boundary_adapter_to_persistence(self) -> None:
        file_issue_text = (REPO_ROOT / "ea_node_editor" / "graph" / "file_issue_state.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("from ea_node_editor.persistence.file_issues import (", file_issue_text)
        self.assertNotIn("ProjectArtifactResolver", file_issue_text)
        self.assertNotIn("_TRACKED_REPAIR_MODES", file_issue_text)

    def test_transform_surface_reexports_focused_operation_modules(self) -> None:
        self.assertEqual(transforms.collect_layout_node_bounds.__module__, "ea_node_editor.graph.transform_layout_ops")
        self.assertEqual(transforms.build_subtree_fragment_payload_data.__module__, "ea_node_editor.graph.transform_fragment_ops")
        self.assertEqual(transforms.plan_subnode_shell_pin_addition.__module__, "ea_node_editor.graph.transform_subnode_ops")
        self.assertEqual(transforms.group_selection_into_subnode.__module__, "ea_node_editor.graph.transform_grouping_ops")
        self.assertEqual(transforms.ungroup_subnode.__module__, "ea_node_editor.graph.transform_grouping_ops")

    def test_mutation_service_keeps_packet_owned_raw_write_helpers_internal(self) -> None:
        self.assertFalse(hasattr(WorkspaceMutationService, "add_node_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "add_edge_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "remove_node_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "remove_edge_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "set_node_parent_raw"))
        self.assertFalse(hasattr(WorkspaceMutationService, "set_node_fragment_state"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_add_node_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_add_edge_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_remove_node_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_remove_edge_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_set_node_parent_record"))
        self.assertTrue(hasattr(WorkspaceMutationService, "_set_node_fragment_state_record"))

    def test_closeout_docs_publish_architecture_followup_matrix_from_canonical_surfaces(self) -> None:
        architecture_text = (REPO_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
        qa_acceptance_text = (
            REPO_ROOT / "docs" / "specs" / "requirements" / "90_QA_ACCEPTANCE.md"
        ).read_text(encoding="utf-8")
        traceability_text = (
            REPO_ROOT / "docs" / "specs" / "requirements" / "TRACEABILITY_MATRIX.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md",
            architecture_text,
        )
        self.assertIn("REQ-QA-029", qa_acceptance_text)
        self.assertIn("ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md", qa_acceptance_text)
        self.assertIn("REQ-QA-029", traceability_text)
        self.assertIn("AC-REQ-QA-029-01", traceability_text)
        self.assertIn("ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md", traceability_text)


if __name__ == "__main__":
    unittest.main()
