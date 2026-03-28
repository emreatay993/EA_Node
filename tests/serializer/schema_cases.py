from __future__ import annotations

from ea_node_editor.execution.compiler import compile_workspace_document
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.project_codec import ProjectDocumentFlavor, ProjectPersistenceEnvelope
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION
from tests.serializer.base_cases import (
    _current_schema_inconsistent_payload,
    _current_schema_minimal_payload,
    _missing_plugin_parent_payload,
    _missing_plugin_round_trip_payload,
)


class SerializerSchemaMixin:
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

    def test_migration_prefers_dpf_model_result_file_input_over_path_edge(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_dpf_conflict",
            "name": "dpf conflict",
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
                            "node_id": "node_result_file",
                            "type_id": "dpf.result_file",
                            "title": "DPF Result File",
                            "x": 0.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {"path": "C:/tmp/source.rst"},
                            "exposed_ports": {},
                            "parent_node_id": None,
                        },
                        {
                            "node_id": "node_model",
                            "type_id": "dpf.model",
                            "title": "DPF Model",
                            "x": 180.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {"path": "C:/tmp/stale.rst"},
                            "exposed_ports": {},
                            "parent_node_id": None,
                        },
                    ],
                    "edges": [
                        {
                            "edge_id": "edge_path",
                            "source_node_id": "node_result_file",
                            "source_port_key": "normalized_path",
                            "target_node_id": "node_model",
                            "target_port_key": "path",
                        },
                        {
                            "edge_id": "edge_result_file",
                            "source_node_id": "node_result_file",
                            "source_port_key": "result_file",
                            "target_node_id": "node_model",
                            "target_port_key": "result_file",
                        },
                    ],
                }
            ],
            "metadata": {},
        }

        project = serializer.from_document(payload)
        workspace = project.workspaces["ws_a"]

        self.assertEqual(set(workspace.edges), {"edge_result_file"})
        edge = workspace.edges["edge_result_file"]
        self.assertEqual(
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key),
            ("node_result_file", "result_file", "node_model", "result_file"),
        )
        self.assertEqual(workspace.nodes["node_model"].properties["path"], "C:/tmp/stale.rst")

    def test_current_schema_fixture_adds_defaults_and_normalizes_workspace_and_view(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = _current_schema_minimal_payload()
        project = serializer.from_document(payload)

        self.assertEqual(project.schema_version, SCHEMA_VERSION)
        self.assertEqual(project.active_workspace_id, "ws_a")
        self.assertEqual(project.metadata.get("workspace_order"), ["ws_a", "ws_b"])
        self.assertEqual(project.metadata.get("custom_workflows"), [])
        self.assertEqual(project.workspaces["ws_b"].active_view_id, "view_b1")
        self.assertEqual(project.workspaces["ws_a"].views["view_a1"].scope_path, [])
        self.assertEqual(project.workspaces["ws_b"].views["view_b1"].scope_path, [])

    def test_current_schema_fixture_repairs_invalid_hidden_and_duplicate_edges(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = _current_schema_inconsistent_payload()
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

    def test_from_document_rejects_pre_current_schema_payload(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = _current_schema_minimal_payload()
        payload["schema_version"] = SCHEMA_VERSION - 1

        with self.assertRaisesRegex(ValueError, "Only schema version"):
            serializer.from_document(payload)

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
        runtime_envelope = ProjectPersistenceEnvelope.from_document(runtime_doc)
        self.assertEqual(runtime_envelope.document_flavor, ProjectDocumentFlavor.RUNTIME)
        self.assertEqual(
            set(runtime_envelope.workspace_envelope("ws_plugin").unresolved_node_docs),
            {"node_unknown"},
        )
        self.assertEqual(
            set(runtime_envelope.workspace_envelope("ws_plugin").unresolved_edge_docs),
            {"edge_unknown_to_known"},
        )

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
