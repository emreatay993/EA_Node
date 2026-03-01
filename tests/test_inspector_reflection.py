from __future__ import annotations

import os
import queue
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLineEdit

from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.scene import NodeGraphScene
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui.panels.inspector_panel import NodeInspectorPanel


class InspectorReflectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.scene = NodeGraphScene()
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)
        self.inspector = NodeInspectorPanel(self.registry)
        self.inspector.property_changed.connect(self.scene.set_node_property)
        self.inspector.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.inspector.close()
        self.scene.clear()
        self.app.processEvents()

    def _message_editor(self) -> QLineEdit:
        editors = self.inspector.property_group.findChildren(QLineEdit)
        if not editors:
            raise AssertionError("Expected at least one line editor in inspector")
        return editors[0]

    def test_text_property_edit_updates_model_immediately(self) -> None:
        node_id = self.scene.add_node_from_type("core.logger", 0.0, 0.0)
        node = self.model.project.workspaces[self.workspace_id].nodes[node_id]
        self.inspector.set_node(node)
        self.app.processEvents()

        editor = self._message_editor()
        editor.setText("updated from inspector")
        self.app.processEvents()

        updated = self.model.project.workspaces[self.workspace_id].nodes[node_id].properties["message"]
        self.assertEqual(updated, "updated from inspector")

    def test_inspector_property_change_is_visible_to_execution_context(self) -> None:
        start_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        logger_id = self.scene.add_node_from_type("core.logger", 120.0, 0.0)
        end_id = self.scene.add_node_from_type("core.end", 240.0, 0.0)
        self.scene.add_edge(start_id, "exec_out", logger_id, "exec_in")
        self.scene.add_edge(logger_id, "exec_out", end_id, "exec_in")

        logger_node = self.model.project.workspaces[self.workspace_id].nodes[logger_id]
        self.inspector.set_node(logger_node)
        self.app.processEvents()
        editor = self._message_editor()
        editor.setText("live inspector message")
        self.app.processEvents()

        event_queue: queue.Queue = queue.Queue()
        serializer = JsonProjectSerializer()
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


if __name__ == "__main__":
    unittest.main()
