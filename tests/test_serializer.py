from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.custom_workflows import export_custom_workflow_file, import_custom_workflow_file
from ea_node_editor.graph.transforms import group_selection_into_subnode
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.workspace.manager import WorkspaceManager

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "persistence"


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
        payload = json.loads((FIXTURES_DIR / "schema_v0_minimal.json").read_text(encoding="utf-8"))
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
        payload = json.loads((FIXTURES_DIR / "schema_v0_inconsistent.json").read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()
