from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ea_node_editor.addons.tabular_data import catalog as tabular_catalog
from ea_node_editor.addons.tabular_data.input_node import (
    TABULAR_DATA_INPUT_DISPLAY_NAME,
    TABULAR_DATA_INPUT_NODE_TYPE_ID,
)
from ea_node_editor.custom_workflows.codec import custom_workflow_library_items
from ea_node_editor.nodes.category_paths import category_display, category_key
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.runtime_contracts import (
    DOUBLE_DATA_TYPE_ID,
    GRAPH_DATA_TYPE_ID,
)
from ea_node_editor.ui.shell.library_projection import (
    build_combined_library_items,
    build_filtered_library_items,
    build_library_category_tree,
    build_library_category_options,
    build_registry_library_items,
    project_display_library_items,
    project_grouped_library_items,
    projected_port_declared_data_types,
    rank_node_library_usage,
)


class LibraryProjectionUsageRankingTests(unittest.TestCase):
    def test_recent_usage_ranks_by_frequency_then_recency_and_ignores_unavailable_items(
        self,
    ) -> None:
        items = [
            {
                "type_id": "core.alpha",
                "display_name": "Alpha",
                "library_source": "node_registry",
            },
            {
                "type_id": "core.beta",
                "display_name": "Beta",
                "library_source": "node_registry",
            },
            {
                "type_id": "core.gamma",
                "display_name": "Gamma",
                "library_source": "node_registry",
            },
            {
                "type_id": "core.delta",
                "display_name": "Delta",
                "library_source": "node_registry",
            },
            {
                "type_id": "core.epsilon",
                "display_name": "Epsilon",
                "library_source": "node_registry",
            },
            {
                "type_id": "core.zeta",
                "display_name": "Zeta",
                "library_source": "node_registry",
            },
            {
                "type_id": "custom_workflow:demo",
                "display_name": "Demo",
                "library_source": "custom_workflow",
            },
        ]

        ranked = rank_node_library_usage(
            combined_items=items,
            usage=[
                "core.delta",
                "core.epsilon",
                "core.zeta",
                "core.beta",
                "core.alpha",
                "custom_workflow:demo",
                "missing.node",
                "core.beta",
                "core.gamma",
                "core.alpha",
            ],
        )

        self.assertEqual(
            [item["type_id"] for item in ranked],
            ["core.alpha", "core.beta", "core.gamma", "core.zeta", "core.epsilon"],
        )


class LibraryProjectionRegistryTests(unittest.TestCase):
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

    def test_projected_port_declared_types_keep_primary_then_unique_alternatives(
        self,
    ) -> None:
        self.assertEqual(
            projected_port_declared_data_types(
                {
                    "data_type": "Primary",
                    "accepted_data_types": ["Alternative", "Primary", "Alternative"],
                }
            ),
            ("Primary", "Alternative"),
        )
        self.assertEqual(projected_port_declared_data_types({}), (GRAPH_DATA_TYPE_ID,))

    def test_registry_library_items_keep_declared_data_port_order(self) -> None:
        excel_write_item = next(
            item
            for item in self.combined_items
            if str(item.get("type_id", "")) == "io.excel_write"
        )

        input_keys = [
            str(port.get("key", ""))
            for port in excel_write_item["ports"]
            if port.get("direction") == "in"
        ]
        output_keys = [
            str(port.get("key", ""))
            for port in excel_write_item["ports"]
            if port.get("direction") == "out"
        ]

        self.assertEqual(input_keys, ["rows", "path"])
        self.assertEqual(output_keys, ["written_path"])

    def test_registry_browser_payload_projects_help_metadata_and_real_port_labels(
        self,
    ) -> None:
        spec = SimpleNamespace(
            type_id="example.sum",
            display_name="Sum",
            category_path=("Math",),
            icon="calculate",
            runtime_behavior="active",
            surface_family="standard",
            surface_variant="",
            description="Adds two values.",
            keywords=("add", "total"),
            ports=(
                SimpleNamespace(
                    key="left_value",
                    label="Left Value",
                    description="First value to add.",
                    direction="in",
                    kind="data",
                    data_type=DOUBLE_DATA_TYPE_ID,
                    side="left",
                    exposed=True,
                ),
            ),
        )

        item = build_registry_library_items(registry_specs=[spec])[0]

        self.assertEqual(item["keywords"], ["add", "total"])
        self.assertEqual(item["library_visual"]["kind"], "catalog_icon")
        self.assertEqual(item["ports"][0]["label"], "Left Value")
        self.assertEqual(item["ports"][0]["description"], "First value to add.")


class LibraryProjectionFolderExplorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = build_default_registry()
        cls.registry_items = build_registry_library_items(
            registry_specs=cls.registry.all_specs(),
        )
        cls.combined_items = build_combined_library_items(
            registry_items=cls.registry_items,
            custom_workflow_items=[],
        )

    def test_folder_explorer_is_discoverable_in_input_output_library_group(
        self,
    ) -> None:
        folder_item = next(
            item
            for item in self.registry_items
            if str(item.get("type_id", "")) == "io.folder_explorer"
        )

        self.assertEqual(folder_item["display_name"], "Folder Explorer")
        self.assertEqual(folder_item["category_path"], ("Input / Output",))
        self.assertEqual(folder_item["category_key"], category_key(("Input / Output",)))
        self.assertEqual(folder_item["category_display"], "Input / Output")
        self.assertEqual(folder_item["library_source"], "node_registry")
        self.assertEqual(
            [port["key"] for port in folder_item["ports"]],
            ["current"],
        )

        filtered = build_filtered_library_items(
            combined_items=self.combined_items,
            query="folder explorer",
            category=category_key(("Input / Output",)),
            data_type="",
            direction="",
        )
        self.assertEqual([item["type_id"] for item in filtered], ["io.folder_explorer"])

        rows = project_grouped_library_items(
            category_tree=build_library_category_tree(filtered)
        )
        self.assertEqual([row["kind"] for row in rows], ["category", "node"])
        self.assertEqual(rows[0]["category_key"], category_key(("Input / Output",)))
        self.assertEqual(rows[1]["type_id"], "io.folder_explorer")
        self.assertEqual(
            rows[1]["ancestor_category_keys"], [category_key(("Input / Output",))]
        )


class LibraryProjectionTabularDataInputTests(unittest.TestCase):
    def test_tabular_data_input_library_item_is_availability_gated(self) -> None:
        with patch.object(tabular_catalog, "_find_spec", return_value=None):
            unavailable_registry = build_default_registry()
        self.assertIsNone(
            unavailable_registry.spec_or_none(TABULAR_DATA_INPUT_NODE_TYPE_ID)
        )

        with patch.object(tabular_catalog, "_find_spec", return_value=object()):
            registry = build_default_registry()
        registry_items = build_registry_library_items(
            registry_specs=registry.all_specs()
        )
        tabular_item = next(
            item
            for item in registry_items
            if str(item.get("type_id", "")) == TABULAR_DATA_INPUT_NODE_TYPE_ID
        )

        self.assertEqual(tabular_item["display_name"], TABULAR_DATA_INPUT_DISPLAY_NAME)
        self.assertEqual(tabular_item["category_path"], ("Data",))
        self.assertEqual(tabular_item["library_source"], "node_registry")
        self.assertEqual(
            [port["key"] for port in tabular_item["ports"]],
            ["path", "table_data", "array_data"],
        )


def _port(
    *,
    key: str = "value",
    direction: str = "out",
    kind: str = "data",
    data_type: str = GRAPH_DATA_TYPE_ID,
    accepted_data_types: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        key=key,
        direction=direction,
        kind=kind,
        data_type=data_type,
        accepted_data_types=accepted_data_types,
        side="",
        exposed=True,
    )


def _spec(
    type_id: str,
    display_name: str,
    category_path: tuple[str, ...],
    *,
    ports: tuple[SimpleNamespace, ...] | None = None,
    icon: str = "fixture",
    runtime_behavior: str = "active",
    surface_family: str = "standard",
    surface_variant: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        type_id=type_id,
        display_name=display_name,
        category_path=category_path,
        category=category_display(category_path),
        icon=icon,
        description=f"{display_name} description",
        ports=ports or (_port(),),
        runtime_behavior=runtime_behavior,
        surface_family=surface_family,
        surface_variant=surface_variant,
    )


class LibraryProjectionNestedCategoryPayloadTests(unittest.TestCase):
    def test_registry_items_nested_category_library_payload_projects_path_metadata(
        self,
    ) -> None:
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
        self.assertEqual(item["runtime_behavior"], "active")
        self.assertEqual(item["surface_family"], "standard")
        self.assertEqual(item["surface_variant"], "")
        self.assertEqual(
            item["library_visual"],
            {
                "kind": "catalog_icon",
                "runtime_behavior": "active",
                "surface_family": "standard",
                "surface_variant": "",
                "shape_id": "",
                "icon": "fixture",
            },
        )

    def test_grouped_rows_nested_category_library_payload_flattens_trie_with_metadata(
        self,
    ) -> None:
        registry_items = build_registry_library_items(
            registry_specs=[
                _spec("fixture.root_direct", "Root Direct", ("Root",)),
                _spec("fixture.beta_leaf", "Beta Leaf", ("Root", "Beta", "Leaf")),
                _spec("fixture.alpha_leaf", "Alpha Leaf", ("Root", "Alpha", "Leaf")),
                _spec("fixture.alpha_direct", "Alpha Direct", ("Root", "Alpha")),
            ]
        )
        rows = project_grouped_library_items(
            category_tree=build_library_category_tree(registry_items)
        )

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
        self.assertEqual(
            [row["label"] for row in category_rows],
            ["Root", "Alpha", "Leaf", "Beta", "Leaf"],
        )
        self.assertEqual([row["depth"] for row in category_rows], [0, 1, 2, 1, 2])
        self.assertEqual(
            category_rows[2]["ancestor_category_keys"],
            [category_key(("Root",)), category_key(("Root", "Alpha"))],
        )
        leaf_keys = {
            row["category_key"] for row in category_rows if row["label"] == "Leaf"
        }
        self.assertEqual(
            leaf_keys,
            {
                category_key(("Root", "Alpha", "Leaf")),
                category_key(("Root", "Beta", "Leaf")),
            },
        )
        root_category_index = next(
            index
            for index, row in enumerate(rows)
            if row["kind"] == "category" and row["category"] == "Root"
        )
        alpha_category_index = next(
            index
            for index, row in enumerate(rows)
            if row["kind"] == "category" and row["category"] == "Root > Alpha"
        )
        alpha_leaf_category_index = next(
            index
            for index, row in enumerate(rows)
            if row["kind"] == "category" and row["category"] == "Root > Alpha > Leaf"
        )
        alpha_direct_index = next(
            index
            for index, row in enumerate(rows)
            if row.get("type_id") == "fixture.alpha_direct"
        )
        root_direct_index = next(
            index
            for index, row in enumerate(rows)
            if row.get("type_id") == "fixture.root_direct"
        )
        alpha_direct_row = rows[alpha_direct_index]
        self.assertEqual(alpha_direct_row["library_visual"]["kind"], "catalog_icon")
        self.assertEqual(alpha_direct_row["runtime_behavior"], "active")
        self.assertLess(root_category_index, alpha_category_index)
        self.assertLess(alpha_category_index, alpha_leaf_category_index)
        self.assertLess(alpha_leaf_category_index, alpha_direct_index)
        self.assertLess(alpha_direct_index, root_direct_index)

    def test_display_rows_icon_mode_groups_passive_flowchart_visuals_into_tile_rows(
        self,
    ) -> None:
        registry_items = build_registry_library_items(
            registry_specs=[
                _spec("fixture.active", "Active Node", ("Flowchart",)),
                _spec(
                    "passive.flowchart.callout",
                    "Callout",
                    ("Flowchart",),
                    icon="chat_bubble",
                    runtime_behavior="passive",
                    surface_family="flowchart",
                    surface_variant="callout",
                ),
                _spec(
                    "passive.flowchart.process",
                    "Process",
                    ("Flowchart",),
                    icon="crop_din",
                    runtime_behavior="passive",
                    surface_family="flowchart",
                    surface_variant="process",
                ),
                _spec(
                    "passive.flowchart.decision",
                    "Decision",
                    ("Flowchart",),
                    icon="diamond",
                    runtime_behavior="passive",
                    surface_family="flowchart",
                    surface_variant="decision",
                ),
            ]
        )

        category_tree = build_library_category_tree(registry_items)
        text_rows = project_grouped_library_items(category_tree=category_tree)
        icon_rows = project_display_library_items(
            category_tree=category_tree,
            passive_node_library_display_mode="icon",
        )

        self.assertEqual(
            [row["kind"] for row in text_rows],
            ["category", "node", "node", "node", "node"],
        )
        self.assertEqual(
            [row["kind"] for row in icon_rows],
            ["category", "node", "passive_icon_grid"],
        )
        grid_row = icon_rows[2]
        self.assertEqual(
            grid_row["ancestor_category_keys"], [category_key(("Flowchart",))]
        )
        self.assertEqual(
            [item["type_id"] for item in grid_row["items"]],
            [
                "passive.flowchart.callout",
                "passive.flowchart.decision",
                "passive.flowchart.process",
            ],
        )
        callout_visual = grid_row["items"][0]["library_visual"]
        self.assertEqual(callout_visual["kind"], "flowchart_shape")
        self.assertEqual(callout_visual["shape_id"], "callout")
        self.assertEqual(callout_visual["icon"], "")
        self.assertGreater(callout_visual["aspect_ratio"], 1.0)

    def test_flowchart_multi_document_library_visual_uses_metric_contract_aspect_ratio(
        self,
    ) -> None:
        registry = build_default_registry()
        items = build_registry_library_items(registry_specs=registry.all_specs())
        item_by_type = {str(item["type_id"]): item for item in items}

        visual = item_by_type["passive.flowchart.multi_document"]["library_visual"]

        self.assertEqual(visual["kind"], "flowchart_shape")
        self.assertEqual(visual["shape_id"], "multi_document")
        self.assertAlmostEqual(visual["aspect_ratio"], 228.0 / 128.0, places=6)

    def test_filters_and_options_nested_category_library_payload_are_path_backed(
        self,
    ) -> None:
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
        self.assertEqual(
            [item["type_id"] for item in compute_filtered], ["fixture.compute"]
        )

        query_filtered = build_filtered_library_items(
            combined_items=combined_items,
            query="Ansys DPF > Viewer",
            category="",
            data_type="",
            direction="",
        )
        self.assertEqual(
            [item["type_id"] for item in query_filtered], ["fixture.viewer"]
        )

        options = build_library_category_options(
            combined_items=combined_items,
            registry_categories=[
                ("Ansys DPF",),
                ("Ansys DPF", "Compute"),
                ("Input / Output",),
            ],
        )
        options_by_label = {option["label"]: option for option in options}
        self.assertEqual(
            options_by_label["Ansys DPF"]["value"], category_key(("Ansys DPF",))
        )
        self.assertEqual(
            options_by_label["Ansys DPF > Compute"]["value"],
            category_key(("Ansys DPF", "Compute")),
        )
        self.assertEqual(
            options_by_label["Input / Output"]["value"],
            category_key(("Input / Output",)),
        )

    def test_custom_workflows_nested_category_library_payload_use_single_segment_path(
        self,
    ) -> None:
        [custom_item] = custom_workflow_library_items(
            [
                {
                    "workflow_id": "wf_nested_payload",
                    "name": "Reusable Flow",
                    "ports": [],
                    "fragment": {
                        "kind": "ea-node-editor/graph-fragment",
                        "version": 2,
                        "nodes": [
                            {
                                "ref_id": "node_a",
                                "type_id": "core.constant",
                                "title": "Constant",
                                "x": 10.0,
                                "y": 20.0,
                                "collapsed": False,
                                "properties": {"value": 1},
                                "exposed_ports": {},
                                "parent_node_id": None,
                            }
                        ],
                        "edges": [],
                    },
                }
            ]
        )

        self.assertEqual(custom_item["category_path"], ("Custom Workflows",))
        self.assertEqual(
            custom_item["category_key"], category_key(("Custom Workflows",))
        )
        self.assertEqual(custom_item["category"], "Custom Workflows")

        [combined_item] = build_combined_library_items(
            registry_items=[],
            custom_workflow_items=[custom_item],
        )
        self.assertEqual(combined_item["category_path"], ("Custom Workflows",))
        self.assertEqual(combined_item["root_category"], "Custom Workflows")


if __name__ == "__main__":
    unittest.main()
