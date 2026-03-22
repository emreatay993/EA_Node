from __future__ import annotations

import queue
import unittest

from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from tests.passive_property_editor_fixtures import (
    PASSIVE_EDITOR_FIXTURE_TYPE_ID,
    register_passive_editor_fixture,
)


class InspectorReflectionTests(unittest.TestCase):

    def setUp(self) -> None:
        self.registry = build_default_registry()
        register_passive_editor_fixture(self.registry)
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.scene = GraphSceneBridge()
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)

    def test_property_update_via_scene_bridge_updates_model_immediately(self) -> None:
        node_id = self.scene.add_node_from_type("core.logger", 0.0, 0.0)

        self.scene.set_node_property(node_id, "message", "updated from inspector")

        updated = self.model.project.workspaces[self.workspace_id].nodes[node_id].properties["message"]
        self.assertEqual(updated, "updated from inspector")

    def test_property_change_is_visible_to_execution_context(self) -> None:
        start_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        logger_id = self.scene.add_node_from_type("core.logger", 120.0, 0.0)
        end_id = self.scene.add_node_from_type("core.end", 240.0, 0.0)
        self.scene.add_edge(start_id, "exec_out", logger_id, "exec_in")
        self.scene.add_edge(logger_id, "exec_out", end_id, "exec_in")

        self.scene.set_node_property(logger_id, "message", "live inspector message")

        event_queue: queue.Queue = queue.Queue()
        serializer = JsonProjectSerializer(build_default_registry())
        run_workflow(
            {
                "run_id": "run_inspector_reflection",
                "workspace_id": self.workspace_id,
                "project_doc": serializer.to_document(self.model.project),
                "trigger": {},
            },
            event_queue,
        )

        logs: list[dict] = []
        while not event_queue.empty():
            event = event_queue.get()
            if event.get("type") == "log":
                logs.append(event)
        self.assertTrue(any(entry.get("message") == "live inspector message" for entry in logs))

    def test_multiline_property_update_via_scene_bridge_preserves_full_text(self) -> None:
        node_id = self.scene.add_node_from_type(PASSIVE_EDITOR_FIXTURE_TYPE_ID, 0.0, 0.0)
        updated_text = "First line\nSecond line\nThird line"

        self.scene.set_node_property(node_id, "notes_blob", updated_text)

        node = self.model.project.workspaces[self.workspace_id].nodes[node_id]
        self.assertEqual(node.properties["notes_blob"], updated_text)

    def test_flowchart_title_property_update_via_scene_bridge_syncs_node_title(self) -> None:
        node_id = self.scene.add_node_from_type("passive.flowchart.decision", 0.0, 0.0)

        self.scene.set_node_property(node_id, "title", "Approved")

        node = self.model.project.workspaces[self.workspace_id].nodes[node_id]
        self.assertEqual(node.properties["title"], "Approved")
        self.assertEqual(node.title, "Approved")

    def test_flowchart_set_node_title_writes_back_title_property(self) -> None:
        node_id = self.scene.add_node_from_type("passive.flowchart.process", 0.0, 0.0)

        self.scene.set_node_title(node_id, "Validate Input")

        node = self.model.project.workspaces[self.workspace_id].nodes[node_id]
        self.assertEqual(node.title, "Validate Input")
        self.assertEqual(node.properties["title"], "Validate Input")

    def test_standard_node_title_property_update_via_scene_bridge_trims_and_keeps_node_title_canonical(self) -> None:
        node_id = self.scene.add_node_from_type("core.logger", 0.0, 0.0)

        self.scene.set_node_property(node_id, "title", "   ")

        node = self.model.project.workspaces[self.workspace_id].nodes[node_id]
        self.assertEqual(node.title, "Logger")
        self.assertNotIn("title", node.properties)

        self.scene.set_node_property(node_id, "title", "  Approval Logger  ")

        self.assertEqual(node.title, "Approval Logger")
        self.assertNotIn("title", node.properties)

    def test_standard_node_batch_title_update_via_scene_bridge_updates_title_without_declared_title_property(self) -> None:
        node_id = self.scene.add_node_from_type("core.logger", 0.0, 0.0)

        changed = self.scene.set_node_properties(
            node_id,
            {
                "title": "  Batch Logger  ",
                "message": "updated from batch",
            },
        )

        self.assertTrue(changed)
        node = self.model.project.workspaces[self.workspace_id].nodes[node_id]
        self.assertEqual(node.title, "Batch Logger")
        self.assertEqual(node.properties["message"], "updated from batch")
        self.assertNotIn("title", node.properties)


if __name__ == "__main__":
    unittest.main()
