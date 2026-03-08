from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION


class SerializerV2MigrationRc2Tests(unittest.TestCase):
    def test_v1_document_is_auto_upgraded_to_v3_with_metadata_defaults(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        v1_doc = {
            "schema_version": 1,
            "project_id": "proj_v1",
            "name": "Legacy",
            "active_workspace_id": "ws_1",
            "workspace_order": ["ws_1"],
            "metadata": {"workspace_order": ["ws_1"]},
            "workspaces": [
                {
                    "workspace_id": "ws_1",
                    "name": "Workspace 1",
                    "active_view_id": "view_1",
                    "views": [
                        {"view_id": "view_1", "name": "V1", "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0}
                    ],
                    "nodes": [
                        {
                            "node_id": "node_1",
                            "type_id": "core.start",
                            "title": "Start",
                            "x": 0.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {},
                            "parent_node_id": None,
                        }
                    ],
                    "edges": [],
                }
            ],
        }
        project = serializer.from_document(v1_doc)
        self.assertEqual(project.schema_version, SCHEMA_VERSION)
        self.assertIn("ui", project.metadata)
        self.assertIn("workflow_settings", project.metadata)
        self.assertEqual(project.metadata.get("custom_workflows"), [])
        self.assertEqual(project.workspaces["ws_1"].views["view_1"].scope_path, [])

    def test_v2_document_is_auto_upgraded_to_v3_with_scope_path_and_custom_workflows(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        v2_doc = {
            "schema_version": 2,
            "project_id": "proj_v2",
            "name": "Legacy",
            "active_workspace_id": "ws_1",
            "workspace_order": ["ws_1"],
            "metadata": {
                "workspace_order": ["ws_1"],
                "custom_workflows": [
                    {
                        "workflow_id": "wf_keep",
                        "name": "Keep",
                        "description": "normalized",
                        "revision": 3,
                        "ports": [
                            {
                                "key": "value_out",
                                "label": "Value",
                                "direction": "out",
                                "kind": "data",
                                "data_type": "number",
                            }
                        ],
                        "fragment": {"root_node_id": "node_parent"},
                    },
                    {
                        "workflow_id": "wf_keep",
                        "name": "Drop Duplicate",
                        "fragment": {"root_node_id": "node_child"},
                    },
                ],
            },
            "workspaces": [
                {
                    "workspace_id": "ws_1",
                    "name": "Workspace 1",
                    "active_view_id": "view_1",
                    "views": [
                        {
                            "view_id": "view_1",
                            "name": "V1",
                            "zoom": 1.0,
                            "pan_x": 0.0,
                            "pan_y": 0.0,
                            "scope_path": ["node_parent", ""],
                        }
                    ],
                    "nodes": [
                        {
                            "node_id": "node_parent",
                            "type_id": "core.logger",
                            "title": "Parent",
                            "x": 0.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {},
                            "parent_node_id": None,
                        },
                        {
                            "node_id": "node_child",
                            "type_id": "core.end",
                            "title": "Child",
                            "x": 120.0,
                            "y": 40.0,
                            "collapsed": False,
                            "properties": {},
                            "exposed_ports": {},
                            "parent_node_id": "node_parent",
                        },
                    ],
                    "edges": [],
                }
            ],
        }

        project = serializer.from_document(v2_doc)
        self.assertEqual(project.schema_version, SCHEMA_VERSION)
        self.assertEqual(project.workspaces["ws_1"].views["view_1"].scope_path, ["node_parent"])
        self.assertEqual(
            project.metadata.get("custom_workflows"),
            [
                {
                    "workflow_id": "wf_keep",
                    "name": "Keep",
                    "description": "normalized",
                    "revision": 3,
                    "ports": [
                        {
                            "key": "value_out",
                            "label": "Value",
                            "direction": "out",
                            "kind": "data",
                            "data_type": "number",
                        }
                    ],
                    "fragment": {"root_node_id": "node_parent"},
                }
            ],
        )

    def test_v3_document_contains_normalized_ui_workflow_settings_and_custom_workflows(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        model = GraphModel()
        model.project.metadata["ui"] = {"script_editor": {"visible": True}}
        model.project.metadata["workflow_settings"] = {
            "solver_config": {"thread_count": 16},
        }
        model.project.metadata["custom_workflows"] = [
            {
                "workflow_id": "wf_keep",
                "name": "Keep",
                "ports": [],
                "fragment": {},
            },
            {
                "workflow_id": "wf_keep",
                "name": "Duplicate",
                "ports": [],
                "fragment": {},
            },
        ]
        doc = serializer.to_document(model.project)
        self.assertEqual(doc["schema_version"], SCHEMA_VERSION)
        self.assertIn("ui", doc["metadata"])
        self.assertIn("workflow_settings", doc["metadata"])
        self.assertEqual(doc["metadata"]["workflow_settings"]["solver_config"]["thread_count"], 16)
        self.assertIn("memory_limit_gb", doc["metadata"]["workflow_settings"]["solver_config"])
        self.assertEqual(
            doc["metadata"]["custom_workflows"],
            [
                {
                    "workflow_id": "wf_keep",
                    "name": "Keep",
                    "description": "",
                    "revision": 1,
                    "ports": [],
                    "fragment": {},
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
