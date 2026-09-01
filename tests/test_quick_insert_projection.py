from __future__ import annotations

import unittest

from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.runtime_contracts import (
    BOOLEAN_DATA_TYPE_ID,
    GRAPH_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
)
from ea_node_editor.ui.shell.library_projection import (
    build_combined_library_items,
    build_registry_library_items,
)
from ea_node_editor.ui.shell.quick_insert_projection import (
    build_canvas_quick_insert_items,
    build_connection_quick_insert_items,
)


class QuickInsertProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        registry = build_default_registry()
        cls.data_types = registry.data_types
        registry_items = build_registry_library_items(
            registry_specs=registry.all_specs()
        )
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
            query="trigger",
        )

        self.assertTrue(results)
        type_ids = [str(item.get("type_id", "")) for item in results]
        self.assertIn("core.trigger", type_ids)

    def test_connection_quick_insert_blank_query_keeps_compatible_matches(self) -> None:
        results = build_connection_quick_insert_items(
            combined_items=self.combined_items,
            data_types=self.data_types,
            query="",
            source_direction="out",
            source_kind="data",
            source_data_type=GRAPH_DATA_TYPE_ID,
        )

        self.assertTrue(results)
        self.assertTrue(all(item.get("compatible_port_labels") for item in results))

    def test_connection_quick_insert_filters_data_ports_by_type(self) -> None:
        results = build_connection_quick_insert_items(
            combined_items=self.combined_items,
            data_types=self.data_types,
            query="process",
            source_direction="out",
            source_kind="data",
            source_data_type=STRING_DATA_TYPE_ID,
            limit=100,
        )

        process_run = next(
            item for item in results if str(item.get("type_id", "")) == "io.process_run"
        )
        self.assertEqual(
            [str(port.get("key", "")) for port in process_run["compatible_ports"]],
            ["command", "stdin_text"],
        )
        incompatible = build_connection_quick_insert_items(
            combined_items=self.combined_items,
            data_types=self.data_types,
            query="process",
            source_direction="out",
            source_kind="data",
            source_data_type=BOOLEAN_DATA_TYPE_ID,
            limit=100,
        )
        self.assertNotIn(
            "io.process_run", {str(item.get("type_id", "")) for item in incompatible}
        )

    def test_connection_quick_insert_treats_primary_and_accepted_types_as_union(
        self,
    ) -> None:
        items = [
            {
                "type_id": "tests.union",
                "display_name": "Union",
                "ports": [
                    {
                        "key": "input",
                        "label": "Input",
                        "direction": "in",
                        "kind": "data",
                        "data_type": STRING_DATA_TYPE_ID,
                        "accepted_data_types": [INTEGER_DATA_TYPE_ID],
                    },
                    {
                        "key": "output",
                        "label": "Output",
                        "direction": "out",
                        "kind": "data",
                        "data_type": INTEGER_DATA_TYPE_ID,
                        "accepted_data_types": [],
                    },
                ],
            }
        ]

        primary_matches = build_connection_quick_insert_items(
            combined_items=items,
            data_types=self.data_types,
            query="",
            source_direction="out",
            source_kind="data",
            source_data_type=STRING_DATA_TYPE_ID,
        )
        alternative_matches = build_connection_quick_insert_items(
            combined_items=items,
            data_types=self.data_types,
            query="",
            source_direction="out",
            source_kind="data",
            source_data_type=INTEGER_DATA_TYPE_ID,
        )
        reverse_matches = build_connection_quick_insert_items(
            combined_items=items,
            data_types=self.data_types,
            query="",
            source_direction="in",
            source_kind="data",
            source_data_type=STRING_DATA_TYPE_ID,
            source_accepted_data_types=(INTEGER_DATA_TYPE_ID,),
        )

        self.assertEqual(
            [port["key"] for port in primary_matches[0]["compatible_ports"]],
            ["input"],
        )
        self.assertEqual(
            [port["key"] for port in alternative_matches[0]["compatible_ports"]],
            ["input"],
        )
        self.assertEqual(
            [port["key"] for port in reverse_matches[0]["compatible_ports"]],
            ["output"],
        )

    def test_connection_quick_insert_excludes_hidden_ports_in_both_directions(
        self,
    ) -> None:
        for source_direction, candidate_direction in (("out", "in"), ("in", "out")):
            with self.subTest(source_direction=source_direction):
                results = build_connection_quick_insert_items(
                    combined_items=[
                        {
                            "type_id": "tests.hidden",
                            "display_name": "Hidden",
                            "ports": [
                                {
                                    "key": "hidden",
                                    "direction": candidate_direction,
                                    "kind": "data",
                                    "data_type": STRING_DATA_TYPE_ID,
                                    "exposed": False,
                                }
                            ],
                        }
                    ],
                    data_types=self.data_types,
                    query="",
                    source_direction=source_direction,
                    source_kind="data",
                    source_data_type=STRING_DATA_TYPE_ID,
                )

                self.assertEqual(results, [])

    def test_connection_quick_insert_retains_runtime_check_matches_in_both_directions(
        self,
    ) -> None:
        self.assertEqual(
            self.data_types.compatibility(
                GRAPH_DATA_TYPE_ID,
                STRING_DATA_TYPE_ID,
            ).status,
            "runtime_check",
        )
        item = {
            "type_id": "tests.runtime_check",
            "display_name": "Runtime Check",
            "ports": [
                {
                    "key": "concrete_input",
                    "direction": "in",
                    "kind": "data",
                    "data_type": STRING_DATA_TYPE_ID,
                },
                {
                    "key": "abstract_output",
                    "direction": "out",
                    "kind": "data",
                    "data_type": GRAPH_DATA_TYPE_ID,
                },
            ],
        }

        forward = build_connection_quick_insert_items(
            combined_items=[item],
            data_types=self.data_types,
            query="",
            source_direction="out",
            source_kind="data",
            source_data_type=GRAPH_DATA_TYPE_ID,
        )
        reverse = build_connection_quick_insert_items(
            combined_items=[item],
            data_types=self.data_types,
            query="",
            source_direction="in",
            source_kind="data",
            source_data_type=STRING_DATA_TYPE_ID,
        )

        self.assertEqual(
            [port["key"] for port in forward[0]["compatible_ports"]],
            ["concrete_input"],
        )
        self.assertEqual(
            [port["key"] for port in reverse[0]["compatible_ports"]],
            ["abstract_output"],
        )

    def test_connection_quick_insert_neutral_flow_source_returns_flowchart_nodes(
        self,
    ) -> None:
        results = build_connection_quick_insert_items(
            combined_items=self.combined_items,
            data_types=self.data_types,
            query="",
            source_direction="neutral",
            source_kind="flow",
            source_data_type="flow",
            limit=100,
        )

        self.assertTrue(results)
        results_by_type = {str(item.get("type_id", "")): item for item in results}
        self.assertIn("passive.flowchart.process", results_by_type)
        self.assertIn("passive.planning.task_card", results_by_type)
        self.assertIn("passive.annotation.sticky_note", results_by_type)
        self.assertIn("passive.media.mail_panel", results_by_type)
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


class QuickInsertProjectionCategoryTests(unittest.TestCase):
    def test_quick_insert_nested_category_library_payload_shows_full_path(
        self,
    ) -> None:
        path = ("Ansys DPF", "Compute")
        combined_items = build_combined_library_items(
            registry_items=[
                {
                    "type_id": "fixture.quick_insert",
                    "display_name": "Quick Insert Candidate",
                    "category_path": path,
                    "description": "Quick Insert Candidate description",
                    "ports": [
                        {
                            "key": "target",
                            "direction": "in",
                            "kind": "data",
                            "data_type": GRAPH_DATA_TYPE_ID,
                        }
                    ],
                }
            ],
            custom_workflow_items=[],
        )

        canvas_results = build_canvas_quick_insert_items(
            combined_items=combined_items,
            query="Ansys DPF > Compute",
        )
        self.assertEqual(canvas_results[0]["category"], "Ansys DPF > Compute")
        self.assertEqual(canvas_results[0]["category_display"], "Ansys DPF > Compute")

        connection_results = build_connection_quick_insert_items(
            combined_items=combined_items,
            data_types=build_default_registry().data_types,
            query="Ansys DPF > Compute",
            source_direction="out",
            source_kind="data",
            source_data_type=GRAPH_DATA_TYPE_ID,
        )
        self.assertEqual(connection_results[0]["category"], "Ansys DPF > Compute")


if __name__ == "__main__":
    unittest.main()
