from __future__ import annotations

import unittest

from ea_node_editor.nodes.bootstrap import build_default_registry


class RegistryFilterTests(unittest.TestCase):
    def test_filter_by_text_and_category(self) -> None:
        registry = build_default_registry()
        results = registry.filter_nodes(query="excel", category="Input / Output")
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
            category="Input / Output",
            direction="in",
            data_type="path",
        )
        self.assertEqual([spec.type_id for spec in results], ["io.excel_write", "io.file_write"])

    def test_filter_results_use_stable_predictable_sorting(self) -> None:
        registry = build_default_registry()
        first = [spec.type_id for spec in registry.filter_nodes(category="Input / Output")]
        second = [spec.type_id for spec in registry.filter_nodes(category="Input / Output")]
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first, key=lambda item: item.lower()))


if __name__ == "__main__":
    unittest.main()
