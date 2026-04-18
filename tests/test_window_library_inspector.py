from __future__ import annotations

import unittest
from types import SimpleNamespace

from ea_node_editor.custom_workflows.codec import custom_workflow_library_items
from ea_node_editor.nodes.category_paths import category_display, category_key
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.node_specs import PropertySpec
from ea_node_editor.ui.shell.window_library_inspector import (
    build_canvas_quick_insert_items,
    build_combined_library_items,
    build_connection_quick_insert_items,
    build_filtered_library_items,
    build_grouped_library_items,
    build_library_category_options,
    build_registry_library_items,
    build_selected_node_header_data,
    build_selected_node_property_items,
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

    def test_registry_library_items_promote_exec_ports_to_top_of_each_side(self) -> None:
        excel_write_item = next(
            item for item in self.combined_items if str(item.get("type_id", "")) == "io.excel_write"
        )

        input_keys = [str(port.get("key", "")) for port in excel_write_item["ports"] if port.get("direction") == "in"]
        output_keys = [
            str(port.get("key", ""))
            for port in excel_write_item["ports"]
            if port.get("direction") == "out"
        ]

        self.assertEqual(input_keys, ["exec_in", "rows", "path"])
        self.assertEqual(output_keys, ["exec_out", "written_path"])


def _port(
    *,
    key: str = "value",
    direction: str = "out",
    kind: str = "data",
    data_type: str = "any",
) -> SimpleNamespace:
    return SimpleNamespace(
        key=key,
        direction=direction,
        kind=kind,
        data_type=data_type,
        side="",
        exposed=True,
    )


def _spec(
    type_id: str,
    display_name: str,
    category_path: tuple[str, ...],
    *,
    ports: tuple[SimpleNamespace, ...] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        type_id=type_id,
        display_name=display_name,
        category_path=category_path,
        category=category_display(category_path),
        icon="fixture",
        description=f"{display_name} description",
        ports=ports or (_port(),),
    )


class WindowLibraryInspectorNestedCategoryLibraryPayloadTests(unittest.TestCase):
    def test_registry_items_nested_category_library_payload_projects_path_metadata(self) -> None:
        path = ("Ansys DPF", "Compute", "Stress")
        [item] = build_registry_library_items(
            registry_specs=[
                _spec("fixture.dpf_stress", "DPF Stress", path),
            ]
        )

        self.assertEqual(item["category_path"], path)
        self.assertEqual(item["category_key"], category_key(path))
        self.assertEqual(item["category_display"], "Ansys DPF > Compute > Stress")
        self.assertEqual(item["category"], "Ansys DPF > Compute > Stress")
        self.assertEqual(item["root_category"], "Ansys DPF")

    def test_grouped_rows_nested_category_library_payload_flattens_trie_with_metadata(self) -> None:
        registry_items = build_registry_library_items(
            registry_specs=[
                _spec("fixture.root_direct", "Root Direct", ("Root",)),
                _spec("fixture.beta_leaf", "Beta Leaf", ("Root", "Beta", "Leaf")),
                _spec("fixture.alpha_leaf", "Alpha Leaf", ("Root", "Alpha", "Leaf")),
                _spec("fixture.alpha_direct", "Alpha Direct", ("Root", "Alpha")),
            ]
        )
        rows = build_grouped_library_items(filtered_items=registry_items)

        category_rows = [row for row in rows if row["kind"] == "category"]
        self.assertEqual(
            [row["category"] for row in category_rows],
            [
                "Root",
                "Root > Alpha",
                "Root > Alpha > Leaf",
                "Root > Beta",
                "Root > Beta > Leaf",
            ],
        )
        self.assertEqual([row["label"] for row in category_rows], ["Root", "Alpha", "Leaf", "Beta", "Leaf"])
        self.assertEqual([row["depth"] for row in category_rows], [0, 1, 2, 1, 2])
        self.assertEqual(
            category_rows[2]["ancestor_category_keys"],
            [category_key(("Root",)), category_key(("Root", "Alpha"))],
        )
        leaf_keys = {
            row["category_key"]
            for row in category_rows
            if row["label"] == "Leaf"
        }
        self.assertEqual(
            leaf_keys,
            {
                category_key(("Root", "Alpha", "Leaf")),
                category_key(("Root", "Beta", "Leaf")),
            },
        )
        root_category_index = next(
            index for index, row in enumerate(rows) if row["kind"] == "category" and row["category"] == "Root"
        )
        alpha_category_index = next(
            index for index, row in enumerate(rows) if row["kind"] == "category" and row["category"] == "Root > Alpha"
        )
        alpha_leaf_category_index = next(
            index
            for index, row in enumerate(rows)
            if row["kind"] == "category" and row["category"] == "Root > Alpha > Leaf"
        )
        alpha_direct_index = next(
            index for index, row in enumerate(rows) if row.get("type_id") == "fixture.alpha_direct"
        )
        root_direct_index = next(
            index for index, row in enumerate(rows) if row.get("type_id") == "fixture.root_direct"
        )
        self.assertLess(root_category_index, alpha_category_index)
        self.assertLess(alpha_category_index, alpha_leaf_category_index)
        self.assertLess(alpha_leaf_category_index, alpha_direct_index)
        self.assertLess(alpha_direct_index, root_direct_index)

    def test_filters_and_options_nested_category_library_payload_are_path_backed(self) -> None:
        combined_items = build_combined_library_items(
            registry_items=build_registry_library_items(
                registry_specs=[
                    _spec("fixture.compute", "Compute Node", ("Ansys DPF", "Compute")),
                    _spec("fixture.viewer", "Viewer Node", ("Ansys DPF", "Viewer")),
                    _spec("fixture.io", "Input Node", ("Input / Output",)),
                ]
            ),
            custom_workflow_items=[],
        )

        root_filtered = build_filtered_library_items(
            combined_items=combined_items,
            query="",
            category=category_key(("Ansys DPF",)),
            data_type="",
            direction="",
        )
        self.assertEqual(
            {item["type_id"] for item in root_filtered},
            {"fixture.compute", "fixture.viewer"},
        )

        compute_filtered = build_filtered_library_items(
            combined_items=combined_items,
            query="",
            category=category_key(("Ansys DPF", "Compute")),
            data_type="",
            direction="",
        )
        self.assertEqual([item["type_id"] for item in compute_filtered], ["fixture.compute"])

        query_filtered = build_filtered_library_items(
            combined_items=combined_items,
            query="Ansys DPF > Viewer",
            category="",
            data_type="",
            direction="",
        )
        self.assertEqual([item["type_id"] for item in query_filtered], ["fixture.viewer"])

        options = build_library_category_options(
            combined_items=combined_items,
            registry_categories=[("Ansys DPF",), ("Ansys DPF", "Compute"), ("Input / Output",)],
        )
        options_by_label = {option["label"]: option for option in options}
        self.assertEqual(options_by_label["Ansys DPF"]["value"], category_key(("Ansys DPF",)))
        self.assertEqual(
            options_by_label["Ansys DPF > Compute"]["value"],
            category_key(("Ansys DPF", "Compute")),
        )
        self.assertEqual(options_by_label["Input / Output"]["value"], category_key(("Input / Output",)))

    def test_custom_workflows_nested_category_library_payload_use_single_segment_path(self) -> None:
        [custom_item] = custom_workflow_library_items(
            [
                {
                    "workflow_id": "wf_nested_payload",
                    "name": "Reusable Flow",
                    "ports": [],
                    "fragment": {"nodes": [], "edges": []},
                }
            ]
        )

        self.assertEqual(custom_item["category_path"], ("Custom Workflows",))
        self.assertEqual(custom_item["category_key"], category_key(("Custom Workflows",)))
        self.assertEqual(custom_item["category"], "Custom Workflows")

        [combined_item] = build_combined_library_items(
            registry_items=[],
            custom_workflow_items=[custom_item],
        )
        self.assertEqual(combined_item["category_path"], ("Custom Workflows",))
        self.assertEqual(combined_item["root_category"], "Custom Workflows")

    def test_quick_insert_and_header_nested_category_library_payload_show_full_paths(self) -> None:
        path = ("Ansys DPF", "Compute")
        [item] = build_registry_library_items(
            registry_specs=[
                _spec(
                    "fixture.quick_insert",
                    "Quick Insert Candidate",
                    path,
                    ports=(_port(key="target", direction="in", kind="data", data_type="any"),),
                )
            ]
        )
        combined_items = build_combined_library_items(registry_items=[item], custom_workflow_items=[])

        canvas_results = build_canvas_quick_insert_items(
            combined_items=combined_items,
            query="Ansys DPF > Compute",
        )
        self.assertEqual(canvas_results[0]["category"], "Ansys DPF > Compute")
        self.assertEqual(canvas_results[0]["category_display"], "Ansys DPF > Compute")

        connection_results = build_connection_quick_insert_items(
            combined_items=combined_items,
            query="Ansys DPF > Compute",
            source_direction="out",
            source_kind="data",
            source_data_type="any",
        )
        self.assertEqual(connection_results[0]["category"], "Ansys DPF > Compute")

        header = build_selected_node_header_data(
            node=SimpleNamespace(title="", type_id="fixture.quick_insert", node_id="node-1"),
            spec=_spec("fixture.quick_insert", "Quick Insert Candidate", path),
            workflow_nodes={"node-1": SimpleNamespace(type_id="fixture.quick_insert")},
        )
        metadata = {item["label"]: item["value"] for item in header["metadata_items"]}
        self.assertEqual(metadata["Category"], "Ansys DPF > Compute")


class WindowLibraryInspectorPropertyGroupTests(unittest.TestCase):
    def test_property_items_emit_group_with_fallback_when_unset(self) -> None:
        spec = SimpleNamespace(
            type_id="fixture.grouped",
            display_name="Grouped Node",
            category_path=("Fixtures",),
            category=category_display(("Fixtures",)),
            icon="fixture",
            description="Grouped Node description",
            ports=(),
            properties=(
                PropertySpec(
                    key="source_path",
                    type="str",
                    default="",
                    label="Source Path",
                    group="Source",
                ),
                PropertySpec(
                    key="comment",
                    type="str",
                    default="",
                    label="Comment",
                ),
            ),
        )
        node = SimpleNamespace(
            type_id="fixture.grouped",
            node_id="node-1",
            properties={},
        )

        items = build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
        )
        items_by_key = {str(item["key"]): item for item in items}

        self.assertEqual(items_by_key["source_path"]["group"], "Source")
        self.assertEqual(items_by_key["comment"]["group"], "Properties")


if __name__ == "__main__":
    unittest.main()
