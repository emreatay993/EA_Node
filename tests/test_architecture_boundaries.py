from __future__ import annotations

import unittest
from pathlib import Path


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
        self.assertIn("from ea_node_editor.graph.boundary_adapters import clamp_pdf_page_number, node_size", mutation_service_text)

    def test_scene_bridge_installs_ui_boundary_implementations(self) -> None:
        bridge_text = (REPO_ROOT / "ea_node_editor" / "ui_qml" / "graph_scene_bridge.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("from ea_node_editor.graph.boundary_adapters import set_graph_boundary_adapters", bridge_text)
        self.assertIn("from ea_node_editor.ui.pdf_preview_provider import clamp_pdf_page_number", bridge_text)
        self.assertIn("from ea_node_editor.ui_qml.edge_routing import node_size", bridge_text)
        self.assertIn("set_graph_boundary_adapters(", bridge_text)


if __name__ == "__main__":
    unittest.main()
