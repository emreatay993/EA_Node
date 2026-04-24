from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ea_node_editor.custom_workflows import export_custom_workflow_file, import_custom_workflow_file
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.transforms import group_selection_into_subnode
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.workspace.manager import WorkspaceManager


class SerializerWorkflowMixin:
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
