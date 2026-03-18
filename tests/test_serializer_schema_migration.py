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


if __name__ == "__main__":
    unittest.main()
