from __future__ import annotations

import copy
import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer, ProjectSessionMetadata
from tests.serializer.round_trip_cases import SerializerRoundTripMixin
from tests.serializer.schema_cases import SerializerSchemaMixin
from tests.serializer.workflow_cases import SerializerWorkflowMixin
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


class SerializerTests(SerializerRoundTripMixin, SerializerWorkflowMixin, SerializerSchemaMixin, unittest.TestCase):
    def test_project_session_metadata_exposes_typed_substructures_and_preserves_extra_namespaces(self) -> None:
        metadata = ProjectSessionMetadata.from_mapping(
            {
                "ui": {
                    "script_editor": {
                        "visible": True,
                    },
                    "panel_state": {
                        "inspector": "expanded",
                    },
                },
                "workflow_settings": {
                    "solver_config": {
                        "thread_count": 16,
                    },
                },
                "artifact_store": {
                    "staged": {
                        "pending_output": {
                            "relative_path": "outputs/run.txt",
                            "slot": "process_run.stdout",
                        }
                    }
                },
            }
        )

        self.assertTrue(metadata.ui.script_editor.visible)
        self.assertFalse(metadata.ui.script_editor.floating)
        self.assertEqual(metadata.ui.extra["panel_state"], {"inspector": "expanded"})
        self.assertEqual(metadata.workflow_settings["solver_config"]["thread_count"], 16)
        self.assertIn("memory_limit_gb", metadata.workflow_settings["solver_config"])
        self.assertEqual(metadata.extra["artifact_store"]["staged"]["pending_output"]["slot"], "process_run.stdout")

        round_tripped = metadata.to_mapping()
        self.assertEqual(
            round_tripped["ui"]["script_editor"],
            {
                "visible": True,
                "floating": False,
            },
        )
        self.assertEqual(round_tripped["ui"]["panel_state"], {"inspector": "expanded"})
        self.assertEqual(
            round_tripped["artifact_store"],
            copy.deepcopy(metadata.extra["artifact_store"]),
        )

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


class SerializerPortLockingTests(unittest.TestCase):
    def test_persistent_document_round_trip_preserves_locked_ports_and_view_filters(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "core.logger",
            "Logger",
            120.0,
            80.0,
            properties={"message": "inline"},
        )
        node.locked_ports = {"message": True, "shadow": False}
        view = workspace.views[workspace.active_view_id]
        view.hide_locked_ports = True
        view.hide_optional_ports = True

        document = serializer.to_persistent_document(model.project)
        workspace_doc = next(ws for ws in document["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == node.node_id)
        view_doc = next(item for item in workspace_doc["views"] if item["view_id"] == view.view_id)

        self.assertEqual(node_doc["locked_ports"], {"message": True, "shadow": False})
        self.assertTrue(view_doc["hide_locked_ports"])
        self.assertTrue(view_doc["hide_optional_ports"])

        loaded = serializer.from_document(document)
        loaded_workspace = loaded.workspaces[workspace.workspace_id]
        loaded_node = loaded_workspace.nodes[node.node_id]
        loaded_view = loaded_workspace.views[view.view_id]

        self.assertEqual(loaded_node.locked_ports, {"message": True, "shadow": False})
        self.assertTrue(loaded_view.hide_locked_ports)
        self.assertTrue(loaded_view.hide_optional_ports)

    def test_load_defaults_locked_ports_and_view_filters_when_fields_are_missing(self) -> None:
        serializer = JsonProjectSerializer(build_default_registry())
        model = GraphModel()
        workspace = model.active_workspace
        node = model.add_node(
            workspace.workspace_id,
            "core.logger",
            "Logger",
            40.0,
            60.0,
        )

        document = serializer.to_persistent_document(model.project)
        workspace_doc = next(ws for ws in document["workspaces"] if ws["workspace_id"] == workspace.workspace_id)
        node_doc = next(item for item in workspace_doc["nodes"] if item["node_id"] == node.node_id)
        view_doc = next(item for item in workspace_doc["views"] if item["view_id"] == workspace.active_view_id)
        node_doc.pop("locked_ports", None)
        view_doc.pop("hide_locked_ports", None)
        view_doc.pop("hide_optional_ports", None)

        loaded = serializer.from_document(document)
        loaded_workspace = loaded.workspaces[workspace.workspace_id]
        loaded_node = loaded_workspace.nodes[node.node_id]
        loaded_view = loaded_workspace.views[workspace.active_view_id]

        self.assertEqual(loaded_node.locked_ports, {})
        self.assertFalse(loaded_view.hide_locked_ports)
        self.assertFalse(loaded_view.hide_optional_ports)


if __name__ == "__main__":
    unittest.main()
