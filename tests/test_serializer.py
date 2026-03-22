from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from tests.serializer.round_trip_cases import SerializerRoundTripMixin
from tests.serializer.schema_cases import SerializerSchemaMixin
from tests.serializer.workflow_cases import SerializerWorkflowMixin
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


class SerializerTests(SerializerRoundTripMixin, SerializerWorkflowMixin, SerializerSchemaMixin, unittest.TestCase):
    def test_comment_backdrop_load_recomputes_membership_and_drops_persisted_membership_fields(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        backdrop = model.add_node(
            workspace.workspace_id,
            "passive.annotation.comment_backdrop",
            "Comment Backdrop",
            80.0,
            80.0,
        )
        model.set_node_size(workspace.workspace_id, backdrop.node_id, 360.0, 240.0)
        logger = model.add_node(workspace.workspace_id, "core.logger", "Logger", 140.0, 140.0)

        serializer = JsonProjectSerializer(registry)
        document = serializer.to_document(model.project)
        workspace_doc = next(ws for ws in document["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        backdrop_doc = next(node for node in workspace_doc["nodes"] if node["node_id"] == backdrop.node_id)
        logger_doc = next(node for node in workspace_doc["nodes"] if node["node_id"] == logger.node_id)
        backdrop_doc.update(
            {
                "owner_backdrop_id": "stale-owner",
                "backdrop_depth": 99,
                "member_node_ids": ["stale-node"],
                "member_backdrop_ids": ["stale-backdrop"],
                "contained_node_ids": ["stale-node"],
                "contained_backdrop_ids": ["stale-backdrop"],
            }
        )
        logger_doc.update(
            {
                "owner_backdrop_id": "wrong-backdrop",
                "backdrop_depth": 42,
            }
        )

        loaded_project = serializer.from_document(document)
        reserialized = serializer.to_document(loaded_project)
        reserialized_workspace_doc = next(
            ws for ws in reserialized["workspaces"] if ws["workspace_id"] == workspace.workspace_id
        )
        serialized_nodes = {
            node["node_id"]: node
            for node in reserialized_workspace_doc["nodes"]
        }
        for node_id in (backdrop.node_id, logger.node_id):
            for key in (
                "owner_backdrop_id",
                "backdrop_depth",
                "member_node_ids",
                "member_backdrop_ids",
                "contained_node_ids",
                "contained_backdrop_ids",
            ):
                self.assertNotIn(key, serialized_nodes[node_id])

        loaded_model = GraphModel(loaded_project)
        scene = GraphSceneBridge()
        scene.set_workspace(loaded_model, registry, workspace.workspace_id)
        payloads = {
            payload["node_id"]: payload
            for payload in [*scene.nodes_model, *scene.backdrop_nodes_model]
        }
        self.assertEqual(payloads[logger.node_id]["owner_backdrop_id"], backdrop.node_id)
        self.assertEqual(payloads[logger.node_id]["backdrop_depth"], 1)
        self.assertEqual(payloads[backdrop.node_id]["member_node_ids"], [logger.node_id])


if __name__ == "__main__":
    unittest.main()
