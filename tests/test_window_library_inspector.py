from __future__ import annotations

import unittest

from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.window_library_inspector import (
    build_canvas_quick_insert_items,
    build_combined_library_items,
    build_connection_quick_insert_items,
    build_registry_library_items,
)


class WindowLibraryInspectorQuickInsertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        registry = build_default_registry()
        registry_items = build_registry_library_items(registry_specs=registry.all_specs())
        cls.combined_items = build_combined_library_items(
            registry_items=registry_items,
            custom_workflow_items=[],
        )

    def test_canvas_quick_insert_blank_query_returns_no_results(self) -> None:
        self.assertEqual(
            build_canvas_quick_insert_items(
                combined_items=self.combined_items,
                query="",
            ),
            [],
        )
        self.assertEqual(
            build_canvas_quick_insert_items(
                combined_items=self.combined_items,
                query="   ",
            ),
            [],
        )

    def test_canvas_quick_insert_non_empty_query_returns_matches(self) -> None:
        results = build_canvas_quick_insert_items(
            combined_items=self.combined_items,
            query="start",
        )

        self.assertGreaterEqual(len(results), 2)
        type_ids = [str(item.get("type_id", "")) for item in results]
        self.assertIn("core.start", type_ids)
        self.assertIn("passive.flowchart.start", type_ids)

    def test_connection_quick_insert_blank_query_keeps_compatible_matches(self) -> None:
        results = build_connection_quick_insert_items(
            combined_items=self.combined_items,
            query="",
            source_direction="out",
            source_kind="data",
            source_data_type="any",
        )

        self.assertTrue(results)
        self.assertTrue(all(item.get("compatible_port_labels") for item in results))

    def test_connection_quick_insert_neutral_flow_source_returns_flowchart_nodes(self) -> None:
        results = build_connection_quick_insert_items(
            combined_items=self.combined_items,
            query="",
            source_direction="neutral",
            source_kind="flow",
            source_data_type="flow",
            limit=100,
        )

        self.assertTrue(results)
        results_by_type = {
            str(item.get("type_id", "")): item
            for item in results
        }
        self.assertIn("passive.flowchart.process", results_by_type)
        self.assertIn("passive.planning.task_card", results_by_type)
        self.assertIn("passive.annotation.sticky_note", results_by_type)
        self.assertIn("passive.media.image_panel", results_by_type)
        self.assertNotIn("core.start", results_by_type)
        self.assertEqual(
            results_by_type["passive.flowchart.process"]["compatible_port_labels"],
            ["top", "right", "bottom", "left"],
        )
        self.assertEqual(
            results_by_type["passive.planning.task_card"]["compatible_port_labels"],
            ["top", "right", "bottom", "left"],
        )
        self.assertEqual(
            results_by_type["passive.flowchart.process"]["compatible_direction"],
            "neutral",
        )


if __name__ == "__main__":
    unittest.main()
