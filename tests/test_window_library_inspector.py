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
from ea_node_editor.graph.records import NodeLinkRecord
from ea_node_editor.nodes.category_paths import category_display, category_key
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.node_specs import PropertyConditionSpec, PropertySpec
from ea_node_editor.runtime_contracts import (
    BOOLEAN_DATA_TYPE_ID,
    DOUBLE_DATA_TYPE_ID,
    GRAPH_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
    Interval1D,
)
from ea_node_editor.ui.shell.window_library_inspector import (
    build_canvas_quick_insert_items,
    build_combined_library_items,
    build_connection_quick_insert_items,
    build_display_library_items,
    build_filtered_library_items,
    build_grouped_library_items,
    build_library_category_options,
    build_registry_library_items,
    build_selected_node_header_data,
    build_selected_node_link_items,
    build_selected_node_property_items,
    rank_node_library_usage,
)
from ea_node_editor.ui.shell.inspector_flow import coerce_editor_input_value


class WindowLibraryInspectorUsageRankingTests(unittest.TestCase):
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


class WindowLibraryInspectorQuickInsertTests(unittest.TestCase):
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


class WindowLibraryInspectorFolderExplorerTests(unittest.TestCase):
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

        rows = build_grouped_library_items(filtered_items=filtered)
        self.assertEqual([row["kind"] for row in rows], ["category", "node"])
        self.assertEqual(rows[0]["category_key"], category_key(("Input / Output",)))
        self.assertEqual(rows[1]["type_id"], "io.folder_explorer")
        self.assertEqual(
            rows[1]["ancestor_category_keys"], [category_key(("Input / Output",))]
        )

    def test_folder_explorer_current_path_property_is_folder_path_editor_payload(
        self,
    ) -> None:
        spec = self.registry.get_spec("io.folder_explorer")
        node = SimpleNamespace(
            type_id="io.folder_explorer",
            node_id="node-folder-explorer",
            properties={"current_path": "C:/Projects/Input"},
            port_labels={},
            exposed_ports={},
        )

        items = build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
        )
        items_by_key = {str(item["key"]): item for item in items}

        self.assertEqual(set(items_by_key), {"current_path"})
        current_path = items_by_key["current_path"]
        self.assertEqual(current_path["label"], "Current Path")
        self.assertEqual(current_path["type"], "path")
        self.assertEqual(current_path["editor_mode"], "path")
        self.assertEqual(current_path["inline_editor"], "")
        self.assertEqual(current_path["path_dialog_mode"], "folder")
        self.assertEqual(current_path["group"], "Source")


class WindowLibraryInspectorNodeLinkTests(unittest.TestCase):
    def test_selected_node_link_items_preserve_order_and_resolve_target_metadata(
        self,
    ) -> None:
        node = SimpleNamespace(
            links=[
                NodeLinkRecord(
                    link_id="link-url",
                    kind="url",
                    title="Project docs",
                    target="https://example.com/docs",
                    subtitle="",
                ),
                NodeLinkRecord(
                    link_id="link-file",
                    kind="file",
                    title="Report",
                    target=r"C:\Projects\reports\summary.pdf",
                    subtitle="Local copy",
                ),
                NodeLinkRecord(
                    link_id="link-node",
                    kind="node",
                    title="Logger node",
                    target="node-logger",
                ),
                NodeLinkRecord(
                    link_id="link-cross-node",
                    kind="node",
                    title="PDF2",
                    target="node-pdf2",
                    target_workspace_id="ws-reports",
                    target_node_id="node-pdf2",
                ),
                NodeLinkRecord(
                    link_id="link-workspace",
                    kind="workspace",
                    title="Analysis workspace",
                    target="ws-analysis",
                ),
                NodeLinkRecord(
                    link_id="link-missing",
                    kind="node",
                    title="Missing target",
                    target="node-missing",
                ),
            ],
        )
        workspace_nodes = {
            "node-logger": SimpleNamespace(title="Logger", type_id="core.logger"),
        }
        workspaces = {
            "ws-analysis": SimpleNamespace(name="Analysis"),
            "ws-reports": SimpleNamespace(
                name="Reports",
                nodes={
                    "node-pdf2": SimpleNamespace(
                        title="PDF2", type_id="passive.media.video_panel"
                    ),
                },
            ),
        }

        items = build_selected_node_link_items(
            node=node,
            workspace_nodes=workspace_nodes,
            workspaces=workspaces,
        )

        self.assertEqual(
            [item["id"] for item in items],
            [
                "link-url",
                "link-file",
                "link-node",
                "link-cross-node",
                "link-workspace",
                "link-missing",
            ],
        )
        self.assertEqual(items[0]["kind"], "url")
        self.assertEqual(items[0]["type_label"], "Web")
        self.assertEqual(items[0]["breadcrumb"], "example.com")
        self.assertEqual(items[0]["icon"], "world-www")
        self.assertEqual(items[0]["type_color"], "#3BA9F5")
        self.assertFalse(items[0]["can_move_up"])
        self.assertTrue(items[0]["can_move_down"])

        self.assertEqual(items[1]["breadcrumb"], "Local copy")
        self.assertEqual(items[1]["icon"], "file-text")
        self.assertEqual(items[2]["breadcrumb"], "Logger")
        self.assertEqual(items[2]["icon"], "hierarchy-2")
        self.assertEqual(items[3]["breadcrumb"], "Reports - PDF2")
        self.assertEqual(items[3]["target_workspace_id"], "ws-reports")
        self.assertEqual(items[3]["target_node_id"], "node-pdf2")
        self.assertEqual(items[4]["breadcrumb"], "Analysis")
        self.assertEqual(items[4]["icon"], "layout-dashboard")
        self.assertEqual(items[5]["breadcrumb"], "Missing node")
        self.assertTrue(items[5]["can_move_up"])
        self.assertFalse(items[5]["can_move_down"])
        self.assertEqual([item["index"] for item in items], [0, 1, 2, 3, 4, 5])


class WindowLibraryInspectorTabularDataInputTests(unittest.TestCase):
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

    def test_tabular_data_input_property_items_use_file_path_and_semantic_groups(
        self,
    ) -> None:
        with patch.object(tabular_catalog, "_find_spec", return_value=object()):
            registry = build_default_registry()
        spec = registry.get_spec(TABULAR_DATA_INPUT_NODE_TYPE_ID)
        node = SimpleNamespace(
            type_id=TABULAR_DATA_INPUT_NODE_TYPE_ID,
            node_id="node-tabular-input",
            properties={"path": "C:/Projects/data/weather.csv"},
            port_labels={},
            exposed_ports={},
        )

        items = build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
        )
        items_by_key = {str(item["key"]): item for item in items}

        self.assertEqual(items_by_key["path"]["editor_mode"], "path")
        self.assertEqual(items_by_key["path"]["path_dialog_mode"], "file")
        self.assertEqual(items_by_key["path"]["group"], "Source")
        self.assertEqual(items_by_key["selected_object"]["label"], "Data Source")
        self.assertEqual(items_by_key["selected_object"]["group"], "Selection")
        self.assertIn("multiple sheets", items_by_key["selected_object"]["help_text"])
        self.assertNotIn("array_slice_2d", items_by_key)
        self.assertEqual(items_by_key["array_slice_2d_row_start"]["label"], "Start Row")
        self.assertEqual(items_by_key["array_slice_2d_row_start"]["value"], 1)
        self.assertEqual(items_by_key["array_slice_2d_row_count"]["value"], 50)
        self.assertEqual(items_by_key["array_slice_2d_column_start"]["value"], "A")
        self.assertEqual(items_by_key["array_slice_2d_column_count"]["value"], 50)
        self.assertEqual(
            items_by_key["array_slice_2d_summary"]["editor_mode"], "summary"
        )
        self.assertEqual(
            items_by_key["array_slice_2d_summary"]["value"], "Rows 1-50, Columns A-AX"
        )
        self.assertEqual(items_by_key["cache_policy"]["group"], "Cache")
        self.assertEqual(items_by_key["project_managed_source"]["group"], "Portability")

    def test_tabular_selection_items_come_from_property_edit_adapter(self) -> None:
        with patch.object(tabular_catalog, "_find_spec", return_value=object()):
            registry = build_default_registry()
        spec = registry.get_spec(TABULAR_DATA_INPUT_NODE_TYPE_ID)
        node = SimpleNamespace(
            type_id=TABULAR_DATA_INPUT_NODE_TYPE_ID,
            node_id="node-tabular-input",
            properties={"path": "C:/Projects/data/weather.csv"},
            port_labels={},
            exposed_ports={},
        )

        items = build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
            property_edit_adapters=(),
        )
        items_by_key = {str(item["key"]): item for item in items}

        self.assertNotIn("array_slice_2d", items_by_key)
        self.assertNotIn("array_slice_2d_row_start", items_by_key)
        self.assertNotIn("array_slice_2d_summary", items_by_key)
        self.assertNotIn("help_text", items_by_key["selected_object"])


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


class WindowLibraryInspectorNestedCategoryLibraryPayloadTests(unittest.TestCase):
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

        text_rows = build_display_library_items(
            filtered_items=registry_items,
            passive_node_library_display_mode="text_icon",
        )
        icon_rows = build_display_library_items(
            filtered_items=registry_items,
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
        items = build_registry_library_items(
            registry_specs=registry.all_specs()
        )
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

    def test_quick_insert_and_header_nested_category_library_payload_show_full_paths(
        self,
    ) -> None:
        path = ("Ansys DPF", "Compute")
        [item] = build_registry_library_items(
            registry_specs=[
                _spec(
                    "fixture.quick_insert",
                    "Quick Insert Candidate",
                    path,
                    ports=(
                        _port(key="target", direction="in", kind="data"),
                    ),
                )
            ]
        )
        combined_items = build_combined_library_items(
            registry_items=[item], custom_workflow_items=[]
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

        header = build_selected_node_header_data(
            node=SimpleNamespace(
                title="", type_id="fixture.quick_insert", node_id="node-1"
            ),
            spec=_spec("fixture.quick_insert", "Quick Insert Candidate", path),
            workflow_nodes={"node-1": SimpleNamespace(type_id="fixture.quick_insert")},
        )
        metadata = {item["label"]: item["value"] for item in header["metadata_items"]}
        self.assertEqual(metadata["Category"], "Ansys DPF > Compute")


class WindowLibraryInspectorPropertyGroupTests(unittest.TestCase):
    def test_interval_editor_input_keeps_declared_endpoint_order(self) -> None:
        default = Interval1D(0.0, 1.0)

        self.assertEqual(
            coerce_editor_input_value(
                "interval_1d", {"start": 8.0, "end": 2.0}, default
            ),
            Interval1D(8.0, 2.0),
        )
        self.assertIs(
            coerce_editor_input_value("interval_1d", {"start": True, "end": 2.0}, default),
            default,
        )
        self.assertIs(
            coerce_editor_input_value(
                "interval_1d", {"start": float("nan"), "end": 2.0}, default
            ),
            default,
        )
        self.assertIs(
            coerce_editor_input_value(
                "interval_1d", {"start": 2.0, "end": float("inf")}, default
            ),
            default,
        )

    def test_property_items_reuse_interval_and_condition_presentation(self) -> None:
        spec = SimpleNamespace(
            type_id="fixture.inspector_interval",
            display_name="Inspector Interval",
            category_path=("Fixtures",),
            category=category_display(("Fixtures",)),
            icon="fixture",
            ports=(),
            dynamic_port_groups=(),
            properties=(
                PropertySpec(
                    key="mode",
                    type="enum",
                    default="None",
                    label="Mode",
                    enum_values=("None", "Manual"),
                    inline_editor="enum",
                ),
                PropertySpec(
                    key="color_map",
                    type="enum",
                    default="Rainbow",
                    label="Color map",
                    enum_values=("Rainbow", "Viridis"),
                    inline_editor="enum",
                    searchable=True,
                ),
                PropertySpec(
                    key="result_bound",
                    type="interval_1d",
                    default=Interval1D(10.0, 2.0),
                    label="Result bound",
                    minimum=0.0,
                    maximum=10.0,
                    step=0.5,
                    inline_editor="interval_slider",
                    interval_direction="decreasing",
                    enabled_when=PropertyConditionSpec("mode", ("Manual",)),
                ),
            ),
        )
        node = SimpleNamespace(
            type_id=spec.type_id,
            node_id="node-interval",
            properties={},
        )

        items = {
            str(item["key"]): item
            for item in build_selected_node_property_items(
                node=node,
                spec=spec,
                subnode_pin_type_ids=set(),
            )
        }
        interval = items["result_bound"]

        self.assertEqual(interval["editor_mode"], "interval_slider")
        self.assertEqual(interval["value"], {"start": 10.0, "end": 2.0})
        self.assertEqual(interval["display_value"], {"start": 10.0, "end": 2.0})
        self.assertFalse(interval["condition_enabled"])
        self.assertFalse(interval["editor_enabled"])
        self.assertEqual(
            interval["editor_disabled_reason"],
            "Available when Mode is Manual.",
        )
        self.assertTrue(items["color_map"]["searchable"])

        node.properties["mode"] = "Manual"
        enabled_interval = {
            str(item["key"]): item
            for item in build_selected_node_property_items(
                node=node,
                spec=spec,
                subnode_pin_type_ids=set(),
            )
        }["result_bound"]
        self.assertTrue(enabled_interval["condition_enabled"])
        self.assertTrue(enabled_interval["editor_enabled"])

    def test_property_items_emit_group_with_fallback_when_unset(self) -> None:
        spec = SimpleNamespace(
            type_id="fixture.grouped",
            display_name="Grouped Node",
            category_path=("Fixtures",),
            category=category_display(("Fixtures",)),
            icon="fixture",
            description="Grouped Node description",
            ports=(),
            dynamic_port_groups=(),
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

    def test_property_items_flag_dirty_when_value_differs_from_default(self) -> None:
        spec = SimpleNamespace(
            type_id="fixture.dirty",
            display_name="Dirty Node",
            category_path=("Fixtures",),
            category=category_display(("Fixtures",)),
            icon="fixture",
            description="Dirty Node description",
            ports=(),
            dynamic_port_groups=(),
            properties=(
                PropertySpec(
                    key="source_path",
                    type="str",
                    default="",
                    label="Source Path",
                ),
                PropertySpec(
                    key="nodes_only",
                    type="bool",
                    default=False,
                    label="Nodes Only",
                ),
            ),
        )

        def _items_for(properties: dict) -> dict:
            node = SimpleNamespace(
                type_id="fixture.dirty",
                node_id="node-1",
                properties=properties,
            )
            items = build_selected_node_property_items(
                node=node,
                spec=spec,
                subnode_pin_type_ids=set(),
            )
            return {str(item["key"]): item for item in items}

        absent = _items_for({})
        self.assertFalse(absent["source_path"]["dirty"])
        self.assertFalse(absent["nodes_only"]["dirty"])

        equal_to_default = _items_for({"source_path": "", "nodes_only": False})
        self.assertFalse(equal_to_default["source_path"]["dirty"])
        self.assertFalse(equal_to_default["nodes_only"]["dirty"])

        diverged = _items_for({"source_path": "C:/data/run.rst", "nodes_only": True})
        self.assertTrue(diverged["source_path"]["dirty"])
        self.assertTrue(diverged["nodes_only"]["dirty"])

        mixed = _items_for({"source_path": "C:/data/run.rst"})
        self.assertTrue(mixed["source_path"]["dirty"])
        self.assertFalse(mixed["nodes_only"]["dirty"])

    def test_web_page_viewer_start_location_uses_source_storage_picker(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("web.page_viewer")
        node = SimpleNamespace(
            type_id="web.page_viewer",
            node_id="node-web",
            port_labels={},
            exposed_ports={},
            properties={
                "start_location": "https://example.com",
                "persist_browser_state": True,
            },
        )

        items = build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
        )
        items_by_key = {str(item["key"]): item for item in items}
        start_location = items_by_key["start_location"]

        self.assertEqual(start_location["editor_mode"], "path")
        self.assertEqual(start_location["path_dialog_mode"], "file")
        self.assertEqual(
            start_location["path_source_modes"], ["managed_copy", "external_link"]
        )
        self.assertTrue(start_location["path_supports_managed_copy"])
        self.assertTrue(start_location["path_supports_external_link"])
        self.assertEqual(start_location["path_current_source_mode"], "external_link")
        self.assertEqual(start_location["group"], "Source")

        node.properties["start_location"] = "temp://managed_html"
        items = build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
        )
        start_location = {str(item["key"]): item for item in items}["start_location"]
        self.assertEqual(start_location["path_current_source_mode"], "managed_copy")


if __name__ == "__main__":
    unittest.main()
