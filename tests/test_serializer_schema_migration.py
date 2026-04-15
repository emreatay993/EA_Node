from __future__ import annotations

import unittest

from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
    DpfModelNodePlugin,
    DpfResultFileNodePlugin,
)
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION


def _workspace_doc(workspace_id: str, name: str) -> dict[str, object]:
    view_id = f"{workspace_id}_view_1"
    return {
        "workspace_id": workspace_id,
        "name": name,
        "active_view_id": view_id,
        "views": [
            {
                "view_id": view_id,
                "name": "V1",
                "zoom": 1.0,
                "pan_x": 0.0,
                "pan_y": 0.0,
            }
        ],
        "nodes": [],
        "edges": [],
    }


def _dpf_rebind_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_dpf_rebind",
        "name": "DPF Rebind",
        "active_workspace_id": "ws_dpf",
        "workspace_order": ["ws_dpf"],
        "workspaces": [
            {
                "workspace_id": "ws_dpf",
                "name": "Workspace DPF",
                "active_view_id": "view_dpf",
                "views": [
                    {
                        "view_id": "view_dpf",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                    }
                ],
                "nodes": [
                    {
                        "node_id": "node_result",
                        "type_id": "dpf.result_file",
                        "title": "Result File",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {"path": "C:/tmp/example.rst"},
                        "exposed_ports": {"result_file": True, "exec_out": True},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_model",
                        "type_id": "dpf.model",
                        "title": "Model",
                        "x": 280.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"result_file": False, "model": True, "exec_in": True},
                        "parent_node_id": None,
                    },
                ],
                "edges": [
                    {
                        "edge_id": "edge_result_data",
                        "source_node_id": "node_result",
                        "source_port_key": "result_file",
                        "target_node_id": "node_model",
                        "target_port_key": "result_file",
                    },
                    {
                        "edge_id": "edge_result_exec",
                        "source_node_id": "node_result",
                        "source_port_key": "exec_out",
                        "target_node_id": "node_model",
                        "target_port_key": "exec_in",
                    },
                ],
            }
        ],
        "metadata": {},
    }


def _generated_dpf_rebind_payload() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": "proj_generated_dpf_rebind",
        "name": "Generated DPF Rebind",
        "active_workspace_id": "ws_dpf",
        "workspace_order": ["ws_dpf"],
        "workspaces": [
            {
                "workspace_id": "ws_dpf",
                "name": "Workspace DPF",
                "active_view_id": "view_dpf",
                "views": [
                    {
                        "view_id": "view_dpf",
                        "name": "V1",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                    }
                ],
                "nodes": [
                    {
                        "node_id": "node_streams_container",
                        "type_id": "dpf.helper.streams_container.streams_container",
                        "title": "Saved Streams Container",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {"streams_container": True, "exec_out": True},
                        "port_labels": {"streams_container": "Saved Streams Container"},
                        "parent_node_id": None,
                    },
                    {
                        "node_id": "node_displacement",
                        "type_id": "dpf.op.result.displacement",
                        "title": "Saved Displacement",
                        "x": 280.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {"read_cyclic": 2, "phi": 45.0},
                        "exposed_ports": {"streams_container": False, "fields_container_2": True, "exec_in": True},
                        "port_labels": {
                            "streams_container": "Hidden Saved Streams Container",
                            "fields_container_2": "Saved Fields",
                        },
                        "parent_node_id": None,
                    },
                ],
                "edges": [
                    {
                        "edge_id": "edge_generated_streams",
                        "source_node_id": "node_streams_container",
                        "source_port_key": "streams_container",
                        "target_node_id": "node_displacement",
                        "target_port_key": "streams_container",
                    }
                ],
            }
        ],
        "metadata": {},
    }


class SerializerSchemaMigrationTests(unittest.TestCase):
    def test_migrate_prefers_explicit_workspace_order_and_normalizes_metadata_copy(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_explicit_order",
            "name": "Explicit Order",
            "active_workspace_id": "missing_workspace",
            "workspace_order": ["ws_a", "ws_b"],
            "workspaces": [
                _workspace_doc("ws_b", "Workspace B"),
                _workspace_doc("ws_a", "Workspace A"),
            ],
            "metadata": {
                "workspace_order": ["ws_b", "ws_a"],
                "ui": {
                    "passive_style_presets": {
                        "node_presets": [
                            {
                                "preset_id": "NodePreset",
                                "name": " Warm ",
                                "style": {
                                    "fill_color": "#102030",
                                    "border_width": "2.5",
                                    "ignored": True,
                                },
                            }
                        ]
                    }
                },
            },
        }

        migrated = serializer.migrate(payload)

        self.assertEqual(migrated["workspace_order"], ["ws_a", "ws_b"])
        self.assertEqual(migrated["metadata"]["workspace_order"], ["ws_a", "ws_b"])
        self.assertEqual([workspace["workspace_id"] for workspace in migrated["workspaces"]], ["ws_a", "ws_b"])
        self.assertEqual(migrated["active_workspace_id"], "ws_a")
        self.assertEqual(
            migrated["metadata"]["ui"]["passive_style_presets"]["node_presets"][0]["name"],
            "Warm",
        )
        self.assertEqual(
            migrated["metadata"]["ui"]["passive_style_presets"]["node_presets"][0]["style"],
            {"fill_color": "#102030", "border_width": 2.5},
        )

    def test_migrate_current_schema_document_uses_workspace_payload_order_when_order_is_missing(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_payload_order",
            "name": "Payload Order",
            "active_workspace_id": "",
            "workspaces": [
                _workspace_doc("ws_b", "Workspace B"),
                _workspace_doc("ws_a", "Workspace A"),
            ],
            "metadata": {},
        }

        migrated = serializer.migrate(payload)

        self.assertEqual(migrated["workspace_order"], ["ws_b", "ws_a"])
        self.assertEqual(migrated["metadata"]["workspace_order"], ["ws_b", "ws_a"])
        self.assertEqual([workspace["workspace_id"] for workspace in migrated["workspaces"]], ["ws_b", "ws_a"])
        self.assertEqual(migrated["active_workspace_id"], "ws_b")

    def test_migrate_normalizes_session_metadata_substructures_and_preserves_extra_ui_keys(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_session_metadata",
            "name": "Session Metadata",
            "workspace_order": ["ws"],
            "active_workspace_id": "ws",
            "workspaces": [_workspace_doc("ws", "Workspace")],
            "metadata": {
                "ui": {
                    "script_editor": {
                        "visible": True,
                    },
                    "panel_state": {
                        "library": "collapsed",
                    },
                },
                "workflow_settings": {
                    "solver_config": {
                        "thread_count": 16,
                    }
                },
            },
        }

        migrated = serializer.migrate(payload)

        self.assertEqual(
            migrated["metadata"]["ui"]["script_editor"],
            {
                "visible": True,
                "floating": False,
            },
        )
        self.assertEqual(migrated["metadata"]["ui"]["panel_state"], {"library": "collapsed"})
        self.assertEqual(migrated["metadata"]["workflow_settings"]["solver_config"]["thread_count"], 16)
        self.assertIn("memory_limit_gb", migrated["metadata"]["workflow_settings"]["solver_config"])

    def test_migrate_and_load_known_node_without_title_uses_registry_display_name(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_missing_title",
            "name": "Missing Title",
            "workspace_order": ["ws"],
            "active_workspace_id": "ws",
            "workspaces": [
                {
                    "workspace_id": "ws",
                    "name": "Workspace",
                    "active_view_id": "view",
                    "views": [
                        {
                            "view_id": "view",
                            "name": "V1",
                            "zoom": 1.0,
                            "pan_x": 0.0,
                            "pan_y": 0.0,
                            "scope_path": [],
                        }
                    ],
                    "nodes": [
                        {
                            "node_id": "node1",
                            "type_id": "core.start",
                        }
                    ],
                    "edges": [],
                }
            ],
            "metadata": {},
        }

        migrated = serializer.migrate(payload)
        project = serializer.from_document(payload)

        self.assertEqual(migrated["workspaces"][0]["nodes"][0]["title"], "Start")
        self.assertEqual(project.workspaces["ws"].nodes["node1"].title, "Start")

    def test_migrate_rejects_pre_current_schema_document(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION - 1,
            "project_id": "proj_legacy",
            "name": "Legacy",
            "active_workspace_id": "",
            "workspaces": [_workspace_doc("ws_a", "Workspace A")],
            "metadata": {},
        }

        with self.assertRaisesRegex(ValueError, "Only schema version"):
            serializer.migrate(payload)

    def test_migrate_preserves_multiple_connections_for_allow_multiple_target_ports(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_flowchart_multi",
            "name": "Flowchart Multi",
            "active_workspace_id": "ws_a",
            "workspace_order": ["ws_a"],
            "workspaces": [
                {
                    "workspace_id": "ws_a",
                    "name": "Workspace A",
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
                            "node_id": "node_start_a",
                            "type_id": "passive.flowchart.start",
                            "title": "Start A",
                            "x": 0.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {"flow_out": True},
                            "parent_node_id": None,
                        },
                        {
                            "node_id": "node_start_b",
                            "type_id": "passive.flowchart.start",
                            "title": "Start B",
                            "x": 0.0,
                            "y": 120.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {"flow_out": True},
                            "parent_node_id": None,
                        },
                        {
                            "node_id": "node_end",
                            "type_id": "passive.flowchart.end",
                            "title": "End",
                            "x": 320.0,
                            "y": 60.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {"flow_in": True},
                            "parent_node_id": None,
                        },
                    ],
                    "edges": [
                        {
                            "edge_id": "edge_a",
                            "source_node_id": "node_start_a",
                            "source_port_key": "right",
                            "target_node_id": "node_end",
                            "target_port_key": "left",
                        },
                        {
                            "edge_id": "edge_b",
                            "source_node_id": "node_start_b",
                            "source_port_key": "right",
                            "target_node_id": "node_end",
                            "target_port_key": "left",
                        },
                    ],
                }
            ],
            "metadata": {},
        }

        project = serializer.from_document(payload)
        workspace = project.workspaces["ws_a"]

        self.assertEqual(set(workspace.edges), {"edge_a", "edge_b"})
        self.assertEqual(
            {
                (
                    edge.source_node_id,
                    edge.source_port_key,
                    edge.target_node_id,
                    edge.target_port_key,
                )
                for edge in workspace.edges.values()
            },
            {
                ("node_start_a", "right", "node_end", "left"),
                ("node_start_b", "right", "node_end", "left"),
            },
        )

    def test_migrate_current_schema_document_preserves_unresolved_node_and_edge_payloads_losslessly(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": SCHEMA_VERSION,
            "project_id": "proj_missing_plugin",
            "name": "Missing Plugin",
            "active_workspace_id": "ws_a",
            "workspaces": [
                {
                    "workspace_id": "ws_a",
                    "name": "Workspace A",
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
                            "node_id": "node_unknown",
                            "type_id": "plugin.missing_node",
                            "title": "Missing",
                            "x": 180.0,
                            "y": 0.0,
                            "collapsed": True,
                            "properties": {"threshold": 0.5},
                            "exposed_ports": {"plugin_in": True},
                            "visual_style": {"fill": "#334455"},
                            "parent_node_id": None,
                            "plugin_payload": {"mode": "offline"},
                        },
                    ],
                    "edges": [
                        {
                            "edge_id": "edge_unknown",
                            "source_node_id": "node_unknown",
                            "source_port_key": "plugin_out",
                            "target_node_id": "node_start",
                            "target_port_key": "trigger",
                            "label": "Unknown",
                            "visual_style": {"stroke": "dashed"},
                            "plugin_edge_payload": {"weight": 2},
                        }
                    ],
                }
            ],
            "metadata": {},
        }

        migrated = serializer.migrate(payload)

        workspace_doc = migrated["workspaces"][0]
        nodes_by_id = {node["node_id"]: node for node in workspace_doc["nodes"]}
        edges_by_id = {edge["edge_id"]: edge for edge in workspace_doc["edges"]}

        self.assertEqual(nodes_by_id["node_unknown"], payload["workspaces"][0]["nodes"][1])
        self.assertEqual(edges_by_id["edge_unknown"], payload["workspaces"][0]["edges"][0])
        self.assertEqual(set(edges_by_id), {"edge_unknown"})

    def test_normalize_project_for_registry_rebinds_previously_unresolved_dpf_nodes_and_edges(self) -> None:
        missing_registry = NodeRegistry()
        serializer = JsonProjectSerializer(missing_registry)
        project = serializer.from_document(_dpf_rebind_payload())
        workspace = project.workspaces["ws_dpf"]

        self.assertEqual(workspace.nodes, {})
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_result", "node_model"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_result_data", "edge_result_exec"})

        rebind_registry = NodeRegistry()
        rebind_registry.register(DpfResultFileNodePlugin)
        rebind_registry.register(DpfModelNodePlugin)

        normalize_project_for_registry(project, rebind_registry)
        workspace = project.workspaces["ws_dpf"]

        self.assertEqual(set(workspace.nodes), {"node_result", "node_model"})
        self.assertEqual(set(workspace.edges), {"edge_result_data", "edge_result_exec"})
        self.assertEqual(workspace.unresolved_node_docs, {})
        self.assertEqual(workspace.unresolved_edge_docs, {})
        self.assertFalse(workspace.nodes["node_model"].exposed_ports["result_file"])

    def test_normalize_project_for_registry_rebinds_generated_dpf_nodes_and_hidden_edges(self) -> None:
        missing_registry = NodeRegistry()
        serializer = JsonProjectSerializer(missing_registry)
        project = serializer.from_document(_generated_dpf_rebind_payload())
        workspace = project.workspaces["ws_dpf"]

        self.assertEqual(workspace.nodes, {})
        self.assertEqual(set(workspace.unresolved_node_docs), {"node_streams_container", "node_displacement"})
        self.assertEqual(set(workspace.unresolved_edge_docs), {"edge_generated_streams"})

        rebind_registry = build_default_registry()
        if rebind_registry.spec_or_none("dpf.op.result.displacement") is None:
            self.skipTest("Generated DPF operator descriptors are not available in this environment.")

        normalize_project_for_registry(project, rebind_registry)
        workspace = project.workspaces["ws_dpf"]

        self.assertEqual(set(workspace.nodes), {"node_streams_container", "node_displacement"})
        self.assertEqual(set(workspace.edges), {"edge_generated_streams"})
        self.assertEqual(workspace.unresolved_node_docs, {})
        self.assertEqual(workspace.unresolved_edge_docs, {})
        self.assertFalse(workspace.nodes["node_displacement"].exposed_ports["streams_container"])
        self.assertEqual(workspace.nodes["node_displacement"].properties["read_cyclic"], 2)
        self.assertEqual(workspace.nodes["node_displacement"].port_labels["fields_container_2"], "Saved Fields")


if __name__ == "__main__":
    unittest.main()
