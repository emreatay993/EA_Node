from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.custom_workflows import export_custom_workflow_file, import_custom_workflow_file
from ea_node_editor.execution.compiler import compile_workspace_document
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.graph.transforms import group_selection_into_subnode
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.workspace.manager import WorkspaceManager


def _schema_v0_minimal_payload() -> dict[str, object]:
    return {
        "schema_version": 0,
        "project_id": "proj_legacy_minimal",
        "name": "Legacy Minimal",
        "active_workspace_id": "ws_missing",
        "workspaces": [
            {
                "workspace_id": "ws_a",
                "name": "Workspace A",
                "active_view_id": "view_missing",
                "views": [
                    {
                        "view_id": "view_a1",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                        "scope_path": [None, "", "   "],
                    }
                ],
                "nodes": [],
                "edges": [],
            },
            {
                "workspace_id": "ws_b",
                "name": "Workspace B",
                "active_view_id": "view_missing",
                "views": [
                    {
                        "view_id": "view_b1",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                    }
                ],
                "nodes": [],
                "edges": [],
            },
        ],
    }


def _schema_v0_inconsistent_payload() -> dict[str, object]:
    return {
        "schema_version": 0,
        "project_id": "proj_legacy_inconsistent",
        "name": "Legacy Inconsistent",
        "active_workspace_id": "ws_legacy",
        "workspaces": [
            {
                "workspace_id": "ws_legacy",
                "name": "Legacy Workspace",
                "active_view_id": "view_legacy",
                "views": [
                    {
                        "view_id": "view_legacy",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                    }
                ],
                "nodes": [
                    {
                        "node_id": "node_start",
                        "type_id": "core.start",
                        "title": "Start",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"exec_out": True, "trigger": True},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_logger",
                        "type_id": "core.logger",
                        "title": "Logger",
                        "x": 160.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"exec_in": False, "message": True, "exec_out": True},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_unknown",
                        "type_id": "plugin.missing_logger",
                        "title": "Unknown",
                        "x": 320.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {},
                        "parent_node_id": None,
                        "plugin_state": {"mode": "offline", "retries": [1, 2]},
                    },
                ],
                "edges": [
                    {
                        "edge_id": "edge_hidden",
                        "source_node_id": "node_start",
                        "source_port_key": "exec_out",
                        "target_node_id": "node_logger",
                        "target_port_key": "exec_in",
                    },
                    {
                        "edge_id": "edge_valid",
                        "source_node_id": "node_start",
                        "source_port_key": "trigger",
                        "target_node_id": "node_logger",
                        "target_port_key": "message",
                    },
                    {
                        "edge_id": "edge_duplicate",
                        "source_node_id": "node_start",
                        "source_port_key": "exec_out",
                        "target_node_id": "node_logger",
                        "target_port_key": "message",
                    },
                    {
                        "edge_id": "edge_unknown",
                        "source_node_id": "node_unknown",
                        "source_port_key": "exec_out",
                        "target_node_id": "node_logger",
                        "target_port_key": "message",
                        "label": "Unknown link",
                        "visual_style": {"stroke": "dot"},
                        "plugin_edge_state": {"route": "fallback"},
                    },
                ],
            }
        ],
    }


def _missing_plugin_round_trip_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_missing_plugin_round_trip",
        "name": "Missing Plugin Round Trip",
        "active_workspace_id": "ws_plugin",
        "workspace_order": ["ws_plugin"],
        "workspaces": [
            {
                "workspace_id": "ws_plugin",
                "name": "Workspace Plugin",
                "active_view_id": "view_plugin",
                "views": [
                    {
                        "view_id": "view_plugin",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                    }
                ],
                "nodes": [
                    {
                        "node_id": "node_start",
                        "type_id": "core.start",
                        "title": "Start",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"exec_out": True, "trigger": True},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_unknown",
                        "type_id": "plugin.missing_transform",
                        "title": "Missing Transform",
                        "x": 160.0,
                        "y": 0.0,
                        "collapsed": True,
                        "properties": {"threshold": 0.75},
                        "exposed_ports": {"plugin_in": True},
                        "visual_style": {"fill": "#123456"},
                        "parent_node_id": None,
                        "custom_width": 280.0,
                        "plugin_payload": {"preset": "wide", "stops": ["a", "b"]},
                    },
                    {
                        "node_id": "node_end",
                        "type_id": "core.end",
                        "title": "End",
                        "x": 320.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"exec_in": True},
                        "parent_node_id": None,
                    },
                ],
                "edges": [
                    {
                        "edge_id": "edge_valid",
                        "source_node_id": "node_start",
                        "source_port_key": "exec_out",
                        "target_node_id": "node_end",
                        "target_port_key": "exec_in",
                    },
                    {
                        "edge_id": "edge_unknown_to_known",
                        "source_node_id": "node_unknown",
                        "source_port_key": "plugin_out",
                        "target_node_id": "node_end",
                        "target_port_key": "exec_in",
                        "label": "Plugin path",
                        "visual_style": {"stroke": "dashed"},
                        "plugin_edge_payload": {"waypoints": [1, 2, 3]},
                    },
                ],
            }
        ],
        "metadata": {},
    }


def _missing_plugin_parent_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_missing_parent",
        "name": "Missing Parent",
        "active_workspace_id": "ws",
        "workspace_order": ["ws"],
        "workspaces": [
            {
                "workspace_id": "ws",
                "name": "WS",
                "active_view_id": "view",
                "views": [
                    {
                        "view_id": "view",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                    }
                ],
                "nodes": [
                    {
                        "node_id": "missing_shell",
                        "type_id": "plugin.missing_shell",
                        "title": "Missing",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "known_child",
                        "type_id": "core.logger",
                        "title": "Logger",
                        "x": 10.0,
                        "y": 10.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"exec_in": True, "message": True, "exec_out": True},
                        "parent_node_id": "missing_shell",
                    },
                ],
                "edges": [],
            }
        ],
        "metadata": {},
    }


class SerializerTests(unittest.TestCase):
    def test_round_trip_preserves_workspace_view_and_graph(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        view = model.create_view(workspace.workspace_id, name="V2")
        model.set_active_view(workspace.workspace_id, view.view_id)
        node_a = model.add_node(workspace.workspace_id, "core.start", "Start", 10, 20)
        node_b = model.add_node(workspace.workspace_id, "core.end", "End", 80, 120)
        edge = model.add_edge(workspace.workspace_id, node_a.node_id, "exec_out", node_b.node_id, "exec_in")

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        self.assertEqual(loaded.active_workspace_id, workspace.workspace_id)
        loaded_ws = loaded.workspaces[workspace.workspace_id]
        self.assertEqual(loaded_ws.active_view_id, view.view_id)
        self.assertIn(node_a.node_id, loaded_ws.nodes)
        self.assertIn(node_b.node_id, loaded_ws.nodes)
        self.assertIn(edge.edge_id, loaded_ws.edges)

    def test_round_trip_preserves_custom_view_order(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        first_view_id = workspace.active_view_id
        second_view_id = model.create_view(workspace.workspace_id, name="Inspection").view_id
        third_view_id = model.create_view(workspace.workspace_id, name="Review").view_id
        model.move_view(workspace.workspace_id, 2, 0)

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        loaded_workspace = loaded.workspaces[workspace.workspace_id]
        self.assertEqual(list(loaded_workspace.views), [third_view_id, first_view_id, second_view_id])
        self.assertEqual(loaded_workspace.active_view_id, third_view_id)

    def test_round_trip_preserves_node_and_edge_visual_metadata_contracts(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        node_a = model.add_node(workspace.workspace_id, "core.start", "Start", 10, 20)
        node_b = model.add_node(workspace.workspace_id, "core.end", "End", 80, 120)
        node_a.visual_style = {"fill": "#102030", "badge": {"shape": "pill"}}
        node_b.visual_style = {"outline": {"width": 2}}
        edge = model.add_edge(workspace.workspace_id, node_a.node_id, "exec_out", node_b.node_id, "exec_in")
        edge.label = "Primary path"
        edge.visual_style = {"stroke": "dashed", "arrow": {"kind": "none"}}

        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_document(model.project)
        workspace_doc = next(ws for ws in doc["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == node_a.node_id)
        edge_doc = next(item for item in workspace_doc["edges"] if item["edge_id"] == edge.edge_id)

        self.assertEqual(doc["schema_version"], SCHEMA_VERSION)
        self.assertEqual(
            doc["metadata"]["ui"]["passive_style_presets"],
            {"node_presets": [], "edge_presets": []},
        )
        self.assertEqual(node_doc["visual_style"], {"fill": "#102030", "badge": {"shape": "pill"}})
        self.assertEqual(edge_doc["label"], "Primary path")
        self.assertEqual(edge_doc["visual_style"], {"stroke": "dashed", "arrow": {"kind": "none"}})

        loaded = serializer.from_document(doc)
        loaded_ws = loaded.workspaces[workspace.workspace_id]

        self.assertEqual(
            loaded_ws.nodes[node_a.node_id].visual_style,
            {"fill": "#102030", "badge": {"shape": "pill"}},
        )
        self.assertEqual(loaded_ws.nodes[node_b.node_id].visual_style, {"outline": {"width": 2}})
        self.assertEqual(loaded_ws.edges[edge.edge_id].label, "Primary path")
        self.assertEqual(
            loaded_ws.edges[edge.edge_id].visual_style,
            {"stroke": "dashed", "arrow": {"kind": "none"}},
        )

    def test_round_trip_normalizes_project_local_passive_style_presets(self) -> None:
        model = GraphModel()
        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_document(model.project)
        doc["metadata"]["ui"]["passive_style_presets"] = {
            "node_presets": [
                {
                    "preset_id": "NodePresetBad",
                    "name": " Flow Warm ",
                    "style": {
                        "fill_color": "#112233",
                        "border_width": "2.5",
                        "ignored": True,
                    },
                },
                {
                    "preset_id": "",
                    "name": " ",
                    "style": {
                        "text_color": "#445566",
                        "font_size": "15",
                    },
                },
            ],
            "edge_presets": [
                {
                    "preset_id": "edge_preset_deadbeef",
                    "name": " Link ",
                    "style": {
                        "stroke_color": "#abcdef",
                        "stroke_width": "3",
                        "stroke_pattern": "dashed",
                        "arrow_head": "open",
                        "ignored": "value",
                    },
                },
                {
                    "preset_id": "edge_preset_deadbeef",
                    "name": "",
                    "style": {
                        "label_text_color": "#010203",
                        "label_background_color": "#AABBCC",
                    },
                },
            ],
        }

        loaded = serializer.from_document(doc)
        presets = loaded.metadata["ui"]["passive_style_presets"]

        self.assertEqual(len(presets["node_presets"]), 2)
        self.assertRegex(presets["node_presets"][0]["preset_id"], r"^node_preset_[0-9a-f]{8}$")
        self.assertRegex(presets["node_presets"][1]["preset_id"], r"^node_preset_[0-9a-f]{8}$")
        self.assertNotEqual(presets["node_presets"][0]["preset_id"], presets["node_presets"][1]["preset_id"])
        self.assertEqual(presets["node_presets"][0]["name"], "Flow Warm")
        self.assertEqual(presets["node_presets"][1]["name"], "Node Preset 2")
        self.assertEqual(
            presets["node_presets"][0]["style"],
            {
                "fill_color": "#112233",
                "border_width": 2.5,
            },
        )
        self.assertEqual(
            presets["node_presets"][1]["style"],
            {
                "text_color": "#445566",
                "font_size": 15,
            },
        )

        self.assertEqual(len(presets["edge_presets"]), 2)
        self.assertEqual(presets["edge_presets"][0]["preset_id"], "edge_preset_deadbeef")
        self.assertRegex(presets["edge_presets"][1]["preset_id"], r"^edge_preset_[0-9a-f]{8}$")
        self.assertNotEqual(presets["edge_presets"][0]["preset_id"], presets["edge_presets"][1]["preset_id"])
        self.assertEqual(presets["edge_presets"][0]["name"], "Link")
        self.assertEqual(presets["edge_presets"][1]["name"], "Edge Preset 2")
        self.assertEqual(
            presets["edge_presets"][0]["style"],
            {
                "stroke_color": "#abcdef",
                "stroke_width": 3.0,
                "stroke_pattern": "dashed",
                "arrow_head": "open",
            },
        )
        self.assertEqual(
            presets["edge_presets"][1]["style"],
            {
                "label_text_color": "#010203",
                "label_background_color": "#AABBCC",
            },
        )

        saved_doc = serializer.to_document(loaded)
        self.assertEqual(saved_doc["metadata"]["ui"]["passive_style_presets"], presets)

    def test_round_trip_preserves_passive_image_panel_properties_and_size(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "passive.media.image_panel",
            "Image Panel",
            25.0,
            45.0,
            properties={
                "source_path": r"C:\fixtures\diagram.png",
                "caption": "System overview\nRevision 2",
                "fit_mode": "cover",
            },
        )
        model.set_node_size(workspace.workspace_id, node.node_id, 348.0, 258.0)

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        loaded_node = loaded.workspaces[workspace.workspace_id].nodes[node.node_id]
        self.assertEqual(loaded_node.type_id, "passive.media.image_panel")
        self.assertEqual(
            loaded_node.properties,
            {
                "source_path": r"C:\fixtures\diagram.png",
                "caption": "System overview\nRevision 2",
                "fit_mode": "cover",
            },
        )
        self.assertEqual(loaded_node.custom_width, 348.0)
        self.assertEqual(loaded_node.custom_height, 258.0)

    def test_load_preserves_sparse_passive_image_panel_properties_while_coercing_present_values(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_document(model.project)
        workspace_doc = next(ws for ws in doc["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        workspace_doc["nodes"].append(
            {
                "node_id": "node_image_panel_sparse",
                "type_id": "passive.media.image_panel",
                "title": "Image Panel",
                "x": 25.0,
                "y": 45.0,
                "collapsed": False,
                "properties": {
                    "source_path": r"C:\fixtures\diagram.png",
                    "fit_mode": "cover",
                    "crop_w": "0.5",
                    "crop_h": None,
                },
                "exposed_ports": {},
                "visual_style": {},
                "parent_node_id": None,
                "custom_width": 348.0,
                "custom_height": 258.0,
            }
        )

        loaded = serializer.from_document(doc)

        loaded_node = loaded.workspaces[workspace.workspace_id].nodes["node_image_panel_sparse"]
        self.assertEqual(
            loaded_node.properties,
            {
                "source_path": r"C:\fixtures\diagram.png",
                "fit_mode": "cover",
                "crop_w": 0.5,
                "crop_h": 1.0,
            },
        )

    def test_round_trip_preserves_passive_pdf_panel_properties_and_size(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "passive.media.pdf_panel",
            "PDF Panel",
            40.0,
            60.0,
            properties={
                "source_path": r"C:\fixtures\manual.pdf",
                "page_number": 4,
                "caption": "Review packet\nSecond pass",
            },
        )
        model.set_node_size(workspace.workspace_id, node.node_id, 312.0, 428.0)

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        loaded_node = loaded.workspaces[workspace.workspace_id].nodes[node.node_id]
        self.assertEqual(loaded_node.type_id, "passive.media.pdf_panel")
        self.assertEqual(
            loaded_node.properties,
            {
                "source_path": r"C:\fixtures\manual.pdf",
                "page_number": 4,
                "caption": "Review packet\nSecond pass",
            },
        )
        self.assertEqual(loaded_node.custom_width, 312.0)
        self.assertEqual(loaded_node.custom_height, 428.0)

    def test_round_trip_preserves_workspace_order_active_workspace_and_view_cameras(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        manager.move_workspace(1, 0)
        manager.set_active_workspace(second)

        first_ws = model.project.workspaces[first]
        first_v1 = first_ws.views[first_ws.active_view_id]
        first_v1.zoom = 1.1
        first_v1.pan_x = 10.0
        first_v1.pan_y = 20.0
        first_v2 = model.create_view(first, name="V2")
        model.project.workspaces[first].views[first_v2.view_id].zoom = 1.8
        model.project.workspaces[first].views[first_v2.view_id].pan_x = 150.0
        model.project.workspaces[first].views[first_v2.view_id].pan_y = -45.0
        model.set_active_view(first, first_v2.view_id)

        second_ws = model.project.workspaces[second]
        second_v1 = second_ws.views[second_ws.active_view_id]
        second_v1.zoom = 0.85
        second_v1.pan_x = -12.0
        second_v1.pan_y = 34.0
        second_v2 = model.create_view(second, name="V2")
        model.project.workspaces[second].views[second_v2.view_id].zoom = 2.2
        model.project.workspaces[second].views[second_v2.view_id].pan_x = 300.0
        model.project.workspaces[second].views[second_v2.view_id].pan_y = 99.0
        model.set_active_view(second, second_v2.view_id)

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        self.assertEqual(loaded.metadata.get("workspace_order"), [second, first])
        self.assertEqual(loaded.active_workspace_id, second)
        self.assertEqual(loaded.workspaces[first].active_view_id, first_v2.view_id)
        self.assertEqual(loaded.workspaces[second].active_view_id, second_v2.view_id)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].zoom, 1.1)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].pan_x, 10.0)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].pan_y, 20.0)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].zoom, 1.8)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].pan_x, 150.0)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].pan_y, -45.0)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].zoom, 0.85)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].pan_x, -12.0)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].pan_y, 34.0)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].zoom, 2.2)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].pan_x, 300.0)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].pan_y, 99.0)

    def test_round_trip_preserves_scope_path_and_normalized_custom_workflows(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        parent = model.add_node(workspace.workspace_id, "core.logger", "Group", 40.0, 60.0)
        child = model.add_node(workspace.workspace_id, "core.end", "End", 120.0, 160.0)
        child.parent_node_id = parent.node_id
        view = workspace.views[workspace.active_view_id]
        view.scope_path = [parent.node_id]
        model.project.metadata["custom_workflows"] = [
            {
                "workflow_id": "wf_valid",
                "name": "Valid Workflow",
                "description": "kept",
                "revision": 2,
                "ports": [
                    {
                        "key": "exec_in",
                        "label": "Exec In",
                        "direction": "in",
                        "kind": "exec",
                        "data_type": "any",
                    }
                ],
                "fragment": {"root_node_id": parent.node_id},
            },
            {
                "workflow_id": "wf_valid",
                "name": "Duplicate",
                "fragment": {"root_node_id": child.node_id},
            },
            {
                "workflow_id": "wf_missing_fragment",
                "name": "Invalid",
                "fragment": [],
            },
        ]

        serializer = JsonProjectSerializer(build_default_registry())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        loaded_view = loaded.workspaces[workspace.workspace_id].views[workspace.active_view_id]
        self.assertEqual(loaded_view.scope_path, [parent.node_id])
        self.assertEqual(
            loaded.metadata.get("custom_workflows"),
            [
                {
                    "workflow_id": "wf_valid",
                    "name": "Valid Workflow",
                    "description": "kept",
                    "revision": 2,
                    "ports": [
                        {
                            "key": "exec_in",
                            "label": "Exec In",
                            "direction": "in",
                            "kind": "exec",
                            "data_type": "any",
                        }
                    ],
                    "fragment": {"root_node_id": parent.node_id},
                }
            ],
        )

    def test_custom_workflow_eawf_round_trip_preserves_snapshot_fidelity(self) -> None:
        definition = {
            "workflow_id": "wf_roundtrip",
            "name": "Roundtrip Workflow",
            "description": "portable snapshot",
            "revision": 5,
            "ports": [
                {
                    "key": "exec_in",
                    "label": "Exec In",
                    "direction": "in",
                    "kind": "exec",
                    "data_type": "any",
                },
                {
                    "key": "payload",
                    "label": "Payload",
                    "direction": "out",
                    "kind": "data",
                    "data_type": "json",
                },
            ],
            "fragment": {
                "kind": "ea-node-editor/graph-fragment",
                "version": 1,
                "nodes": [
                    {
                        "ref_id": "note_a",
                        "type_id": "tests.passive_note",
                        "title": "Note A",
                        "x": 10.0,
                        "y": 20.0,
                        "visual_style": {"fill": "#ffeaa7", "outline": {"width": 2}},
                    },
                    {
                        "ref_id": "note_b",
                        "type_id": "tests.passive_note",
                        "title": "Note B",
                        "x": 220.0,
                        "y": 80.0,
                        "visual_style": {"fill": "#dfe6e9"},
                    },
                ],
                "edges": [
                    {
                        "source_ref_id": "note_a",
                        "source_port_key": "flow_out",
                        "target_ref_id": "note_b",
                        "target_port_key": "flow_in",
                        "label": "Primary path",
                        "visual_style": {"stroke": "dashed", "arrow": {"kind": "none"}},
                    }
                ],
            },
            "source_shell_ref_id": "node_shell",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "workflow_export"
            saved_path = export_custom_workflow_file(definition, path)
            self.assertEqual(saved_path.suffix, ".eawf")

            payload = json.loads(saved_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("kind"), "ea-node-editor/custom-workflow")
            self.assertEqual(payload.get("version"), 1)

            imported = import_custom_workflow_file(saved_path)

        self.assertEqual(imported, definition)

    def test_round_trip_preserves_grouped_subnode_parenting_and_boundary_edges(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        start_a = model.add_node(workspace.workspace_id, "core.start", "Start A", 20.0, 20.0)
        start_b = model.add_node(workspace.workspace_id, "core.start", "Start B", 20.0, 220.0)
        logger_a = model.add_node(workspace.workspace_id, "core.logger", "Logger A", 280.0, 20.0)
        logger_b = model.add_node(workspace.workspace_id, "core.logger", "Logger B", 280.0, 220.0)
        end_a = model.add_node(workspace.workspace_id, "core.end", "End A", 640.0, 0.0)
        end_b = model.add_node(workspace.workspace_id, "core.end", "End B", 640.0, 140.0)
        end_c = model.add_node(workspace.workspace_id, "core.end", "End C", 640.0, 280.0)
        end_d = model.add_node(workspace.workspace_id, "core.end", "End D", 640.0, 420.0)

        model.add_edge(workspace.workspace_id, start_a.node_id, "exec_out", logger_a.node_id, "exec_in")
        model.add_edge(workspace.workspace_id, start_b.node_id, "exec_out", logger_b.node_id, "exec_in")
        model.add_edge(workspace.workspace_id, logger_a.node_id, "exec_out", end_a.node_id, "exec_in")
        model.add_edge(workspace.workspace_id, logger_a.node_id, "exec_out", end_b.node_id, "exec_in")
        model.add_edge(workspace.workspace_id, logger_b.node_id, "exec_out", end_c.node_id, "exec_in")
        model.add_edge(workspace.workspace_id, logger_b.node_id, "exec_out", end_d.node_id, "exec_in")

        grouped = group_selection_into_subnode(
            model=model,
            registry=registry,
            workspace_id=workspace.workspace_id,
            selected_node_ids=[logger_a.node_id, logger_b.node_id],
            scope_path=[],
            shell_x=280.0,
            shell_y=120.0,
        )
        self.assertIsNotNone(grouped)
        assert grouped is not None

        shell_id = grouped.shell_node_id
        edge_signature_before = {
            (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
            )
            for edge in workspace.edges.values()
            if edge.source_node_id == shell_id or edge.target_node_id == shell_id
        }
        self.assertTrue(edge_signature_before)

        serializer = JsonProjectSerializer(registry)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        loaded_ws = loaded.workspaces[workspace.workspace_id]
        self.assertIn(shell_id, loaded_ws.nodes)
        expected_children = [logger_a.node_id, logger_b.node_id, *grouped.created_pin_node_ids]
        for node_id in expected_children:
            self.assertIn(node_id, loaded_ws.nodes)
            self.assertEqual(loaded_ws.nodes[node_id].parent_node_id, shell_id)

        edge_signature_after = {
            (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
            )
            for edge in loaded_ws.edges.values()
            if edge.source_node_id == shell_id or edge.target_node_id == shell_id
        }
        self.assertEqual(edge_signature_after, edge_signature_before)

    def test_save_output_is_deterministic_and_uses_workspace_order(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        manager.move_workspace(1, 0)
        manager.set_active_workspace(second)

        workspace = model.project.workspaces[second]
        workspace.ensure_default_view()
        view = workspace.views[workspace.active_view_id]
        view.zoom = 1.42
        view.pan_x = -30.0
        view.pan_y = 45.0
        source = model.add_node(second, "core.start", "Start", 12.0, 20.0)
        target = model.add_node(second, "core.logger", "Logger", 80.0, 20.0)
        edge = model.add_edge(second, source.node_id, "trigger", target.node_id, "message")
        self.assertIsNotNone(edge.edge_id)

        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_document(model.project)
        self.assertEqual(doc["workspace_order"], [second, first])
        self.assertEqual([ws["workspace_id"] for ws in doc["workspaces"]], [second, first])
        self.assertEqual(doc["active_workspace_id"], second)

        with tempfile.TemporaryDirectory() as temp_dir:
            path_a = Path(temp_dir) / "a.sfe"
            path_b = Path(temp_dir) / "b.sfe"
            serializer.save(str(path_a), model.project)
            serializer.save(str(path_b), model.project)
            self.assertEqual(path_a.read_text(encoding="utf-8"), path_b.read_text(encoding="utf-8"))

    def test_migration_normalizes_conflicting_target_inputs_deterministically(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_conflict",
            "name": "conflict",
            "active_workspace_id": "ws_a",
            "workspace_order": ["ws_a"],
            "workspaces": [
                {
                    "workspace_id": "ws_a",
                    "name": "Workspace",
                    "active_view_id": "view_a",
                    "views": [
                        {
                            "view_id": "view_a",
                            "name": "V1",
                            "zoom": 1.0,
                            "pan_x": 0.0,
                            "pan_y": 0.0,
                        }
                    ],
                    "nodes": [
                        {
                            "node_id": "node_start",
                            "type_id": "core.start",
                            "title": "Start",
                            "x": 0.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {"exec_out": True, "trigger": True},
                            "parent_node_id": None,
                        },
                        {
                            "node_id": "node_logger",
                            "type_id": "core.logger",
                            "title": "Logger",
                            "x": 160.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {"exec_in": True, "message": True, "exec_out": True},
                            "parent_node_id": None,
                        },
                        {
                            "node_id": "node_end",
                            "type_id": "core.end",
                            "title": "End",
                            "x": 320.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {"exec_in": True},
                            "parent_node_id": None,
                        },
                    ],
                    "edges": [
                        {
                            "edge_id": "edge_a",
                            "source_node_id": "node_start",
                            "source_port_key": "exec_out",
                            "target_node_id": "node_end",
                            "target_port_key": "exec_in",
                        },
                        {
                            "edge_id": "edge_z",
                            "source_node_id": "node_logger",
                            "source_port_key": "exec_out",
                            "target_node_id": "node_end",
                            "target_port_key": "exec_in",
                        },
                    ],
                }
            ],
            "metadata": {},
        }

        project = serializer.from_document(payload)
        workspace = project.workspaces["ws_a"]
        self.assertEqual(set(workspace.edges), {"edge_a"})
        edge = workspace.edges["edge_a"]
        self.assertEqual(
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key),
            ("node_start", "exec_out", "node_end", "exec_in"),
        )

    def test_migrate_v0_fixture_adds_defaults_and_normalizes_workspace_and_view(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = _schema_v0_minimal_payload()
        project = serializer.from_document(payload)

        self.assertEqual(project.schema_version, SCHEMA_VERSION)
        self.assertEqual(project.active_workspace_id, "ws_a")
        self.assertEqual(project.metadata.get("workspace_order"), ["ws_a", "ws_b"])
        self.assertEqual(project.metadata.get("custom_workflows"), [])
        self.assertEqual(project.workspaces["ws_b"].active_view_id, "view_b1")
        self.assertEqual(project.workspaces["ws_a"].views["view_a1"].scope_path, [])
        self.assertEqual(project.workspaces["ws_b"].views["view_b1"].scope_path, [])

    def test_migrate_v0_fixture_repairs_invalid_hidden_and_duplicate_edges(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = _schema_v0_inconsistent_payload()
        project = serializer.from_document(payload)

        self.assertEqual(project.schema_version, SCHEMA_VERSION)
        workspace = project.workspaces["ws_legacy"]
        self.assertNotIn("node_unknown", workspace.nodes)
        self.assertEqual(set(workspace.edges), {"edge_valid"})
        edge = workspace.edges["edge_valid"]
        self.assertEqual(
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key),
            ("node_start", "trigger", "node_logger", "message"),
        )
        self.assertEqual(project.metadata.get("workspace_order"), ["ws_legacy"])

        self.assertEqual(set(workspace.unresolved_node_docs), {"node_unknown"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_unknown"})
        self.assertEqual(
            workspace.unresolved_node_docs["node_unknown"]["plugin_state"],
            {"mode": "offline", "retries": [1, 2]},
        )
        self.assertEqual(
            workspace.unresolved_edge_docs["edge_unknown"]["plugin_edge_state"],
            {"route": "fallback"},
        )

        round_tripped = serializer.to_persistent_document(project)
        workspace_doc = round_tripped["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        edges_by_id = {edge["edge_id"]: edge for edge in workspace_doc["edges"]}
        self.assertEqual(nodes_by_id["node_unknown"], payload["workspaces"][0]["nodes"][2])
        self.assertEqual(edges_by_id["edge_unknown"], payload["workspaces"][0]["edges"][3])

    def test_round_trip_preserves_missing_plugin_payload_across_normalization(self) -> None:
        registry = build_default_registry()
        serializer = JsonProjectSerializer(registry)
        payload = _missing_plugin_round_trip_payload()

        project = serializer.from_document(payload)
        workspace = project.workspaces["ws_plugin"]

        self.assertNotIn("node_unknown", workspace.nodes)
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_unknown"})
        self.assertEqual(set(workspace.edges), {"edge_valid"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_unknown_to_known"})

        normalize_project_for_registry(project, registry)
        workspace = project.workspaces["ws_plugin"]
        self.assertNotIn("node_unknown", workspace.nodes)
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_unknown"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_unknown_to_known"})

        runtime_doc = serializer.to_document(project)
        runtime_workspace_doc = runtime_doc["workspaces"][0]
        self.assertEqual(
            [node["node_id"] for node in runtime_workspace_doc["nodes"]],
            ["node_end", "node_start"],
        )
        self.assertEqual([edge["edge_id"] for edge in runtime_workspace_doc["edges"]], ["edge_valid"])
        self.assertIn("_runtime_unresolved_workspaces", runtime_doc["metadata"])

        compiled = compile_workspace_document(runtime_workspace_doc, registry)
        self.assertEqual(
            [node["node_id"] for node in compiled["nodes"]],
            ["node_end", "node_start"],
        )
        self.assertEqual(
            compiled["edges"],
            [
                {
                    "source_node_id": "node_start",
                    "source_port_key": "exec_out",
                    "target_node_id": "node_end",
                    "target_port_key": "exec_in",
                }
            ],
        )

        reloaded_from_runtime_doc = serializer.from_document(runtime_doc)
        reloaded_workspace = reloaded_from_runtime_doc.workspaces["ws_plugin"]
        self.assertEqual(set(reloaded_workspace.unresolved_node_docs), {"node_unknown"})
        self.assertEqual(set(reloaded_workspace.unresolved_edge_docs), {"edge_unknown_to_known"})

        authored_doc = serializer.to_persistent_document(project)
        workspace_doc = authored_doc["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        edges_by_id = {edge["edge_id"]: edge for edge in workspace_doc["edges"]}

        self.assertEqual(nodes_by_id["node_unknown"], payload["workspaces"][0]["nodes"][1])
        self.assertEqual(edges_by_id["edge_unknown_to_known"], payload["workspaces"][0]["edges"][1])
        self.assertEqual(serializer.to_persistent_document(reloaded_from_runtime_doc), authored_doc)
        self.assertEqual(
            edges_by_id["edge_valid"],
            {
                "edge_id": "edge_valid",
                "source_node_id": "node_start",
                "source_port_key": "exec_out",
                "target_node_id": "node_end",
                "target_port_key": "exec_in",
                "label": "",
                "visual_style": {},
            },
        )

    def test_from_document_sanitizes_live_parent_links_to_unresolved_nodes(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = _missing_plugin_parent_payload()

        project = serializer.from_document(payload)
        workspace = project.workspaces["ws"]

        self.assertEqual(sorted(workspace.nodes), ["known_child"])
        self.assertEqual(sorted(workspace.unresolved_node_docs), ["missing_shell"])
        self.assertIsNone(workspace.nodes["known_child"].parent_node_id)
        self.assertEqual(
            workspace.authored_node_overrides["known_child"],
            {"parent_node_id": "missing_shell"},
        )

        authored_doc = serializer.to_persistent_document(project)
        workspace_doc = authored_doc["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        self.assertEqual(nodes_by_id["known_child"]["parent_node_id"], "missing_shell")


if __name__ == "__main__":
    unittest.main()
