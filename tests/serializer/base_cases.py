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


_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "persistence"


def _load_persistence_fixture(name: str) -> dict[str, object]:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _current_schema_minimal_payload() -> dict[str, object]:
    return _load_persistence_fixture("schema_current_minimal.json")


def _current_schema_inconsistent_payload() -> dict[str, object]:
    return _load_persistence_fixture("schema_current_inconsistent.json")


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


if __name__ == "__main__":
    unittest.main()
