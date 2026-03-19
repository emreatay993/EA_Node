from __future__ import annotations

import unittest

from ea_node_editor.nodes.bootstrap import build_default_registry
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

    def test_migrate_legacy_document_uses_workspace_payload_order_when_order_is_missing(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": 0,
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
                            "source_port_key": "flow_out",
                            "target_node_id": "node_end",
                            "target_port_key": "flow_in",
                        },
                        {
                            "edge_id": "edge_b",
                            "source_node_id": "node_start_b",
                            "source_port_key": "flow_out",
                            "target_node_id": "node_end",
                            "target_port_key": "flow_in",
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
                ("node_start_a", "flow_out", "node_end", "flow_in"),
                ("node_start_b", "flow_out", "node_end", "flow_in"),
            },
        )

    def test_migrate_preserves_unresolved_node_and_edge_payloads_losslessly(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        payload = {
            "schema_version": 0,
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


if __name__ == "__main__":
    unittest.main()
