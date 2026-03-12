from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, QMetaObject, Qt, Q_ARG
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QMessageBox

from ea_node_editor.app import APP_STYLESHEET
from ea_node_editor.custom_workflows import import_custom_workflow_file
from ea_node_editor.ui.shell.window import ShellWindow


def _action_shortcuts(action) -> set[str]:  # noqa: ANN001
    return {
        sequence.toString(QKeySequence.SequenceFormat.PortableText)
        for sequence in action.shortcuts()
    }


class MainWindowShellTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(APP_STYLESHEET)

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._session_path = Path(self._temp_dir.name) / "last_session.json"
        self._autosave_path = Path(self._temp_dir.name) / "autosave.sfe"
        self._app_preferences_path = Path(self._temp_dir.name) / "app_preferences.json"
        self._global_custom_workflows_path = Path(self._temp_dir.name) / "custom_workflows_global.json"
        self._session_patch = patch(
            "ea_node_editor.ui.shell.window.recent_session_path",
            return_value=self._session_path,
        )
        self._autosave_patch = patch(
            "ea_node_editor.ui.shell.window.autosave_project_path",
            return_value=self._autosave_path,
        )
        self._app_preferences_patch = patch(
            "ea_node_editor.ui.shell.controllers.app_preferences_controller.app_preferences_path",
            return_value=self._app_preferences_path,
        )
        self._global_custom_workflows_patch = patch(
            "ea_node_editor.custom_workflows.global_store.global_custom_workflows_path",
            return_value=self._global_custom_workflows_path,
        )
        self._session_patch.start()
        self._autosave_patch.start()
        self._app_preferences_patch.start()
        self._global_custom_workflows_patch.start()
        self.window = ShellWindow()
        self.window.resize(1200, 800)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()
        self._session_patch.stop()
        self._autosave_patch.stop()
        self._app_preferences_patch.stop()
        self._global_custom_workflows_patch.stop()
        self._temp_dir.cleanup()

    def _active_workspace(self):
        workspace_id = self.window.workspace_manager.active_workspace_id()
        return workspace_id, self.window.model.project.workspaces[workspace_id]

    def _workspace_state(self) -> dict[str, object]:
        _workspace_id, workspace = self._active_workspace()
        nodes = {
            node_id: {
                "type_id": node.type_id,
                "title": node.title,
                "x": float(node.x),
                "y": float(node.y),
                "collapsed": bool(node.collapsed),
                "properties": dict(node.properties),
                "exposed_ports": dict(node.exposed_ports),
            }
            for node_id, node in workspace.nodes.items()
        }
        edges = {
            edge_id: (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
            )
            for edge_id, edge in workspace.edges.items()
        }
        return {"nodes": nodes, "edges": edges}

    def _graph_canvas_item(self) -> QObject:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        graph_canvas = root_object.findChild(QObject, "graphCanvas")
        self.assertIsNotNone(graph_canvas)
        return graph_canvas

    def _library_pane_item(self) -> QObject:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        library_pane = root_object.findChild(QObject, "libraryPane")
        self.assertIsNotNone(library_pane)
        return library_pane

    def _create_publishable_subnode(self, *, shell_title: str, output_label: str) -> tuple[str, str]:
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        self.window.scene.set_node_title(shell_id, shell_title)
        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        output_pin_id = self.window.scene.add_node_from_type("core.subnode_output", x=180.0, y=90.0)
        self.window.scene.set_node_property(output_pin_id, "label", output_label)
        self.window.scene.set_node_property(output_pin_id, "kind", "exec")
        self.window.scene.set_node_property(output_pin_id, "data_type", "any")
        self.assertTrue(self.window.request_navigate_scope_parent())
        self.window.scene.focus_node(shell_id)
        self.app.processEvents()
        return shell_id, output_pin_id

    def _create_nested_outer_inner_subnodes(self) -> tuple[str, str]:
        outer_id = self.window.scene.add_node_from_type("core.subnode", x=120.0, y=100.0)
        self.window.scene.set_node_title(outer_id, "Outer")
        self.assertTrue(self.window.request_open_subnode_scope(outer_id))

        outer_input_id = self.window.scene.add_node_from_type("core.subnode_input", x=20.0, y=80.0)
        self.window.scene.set_node_property(outer_input_id, "label", "Outer In")
        self.window.scene.set_node_property(outer_input_id, "kind", "exec")
        self.window.scene.set_node_property(outer_input_id, "data_type", "any")

        outer_output_id = self.window.scene.add_node_from_type("core.subnode_output", x=420.0, y=80.0)
        self.window.scene.set_node_property(outer_output_id, "label", "Outer Out")
        self.window.scene.set_node_property(outer_output_id, "kind", "exec")
        self.window.scene.set_node_property(outer_output_id, "data_type", "any")

        inner_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=160.0)
        self.window.scene.set_node_title(inner_id, "Inner")

        self.assertTrue(self.window.request_open_subnode_scope(inner_id))
        inner_input_id = self.window.scene.add_node_from_type("core.subnode_input", x=20.0, y=80.0)
        self.window.scene.set_node_property(inner_input_id, "label", "Inner In")
        self.window.scene.set_node_property(inner_input_id, "kind", "exec")
        self.window.scene.set_node_property(inner_input_id, "data_type", "any")

        inner_output_id = self.window.scene.add_node_from_type("core.subnode_output", x=420.0, y=80.0)
        self.window.scene.set_node_property(inner_output_id, "label", "Inner Out")
        self.window.scene.set_node_property(inner_output_id, "kind", "exec")
        self.window.scene.set_node_property(inner_output_id, "data_type", "any")

        logger_id = self.window.scene.add_node_from_type("core.logger", x=220.0, y=160.0)
        self.window.scene.add_edge(inner_input_id, "pin", logger_id, "exec_in")
        self.window.scene.add_edge(logger_id, "exec_out", inner_output_id, "pin")

        self.assertTrue(self.window.request_navigate_scope_parent())
        self.window.scene.add_edge(outer_input_id, "pin", inner_id, inner_input_id)
        self.window.scene.add_edge(inner_id, inner_output_id, outer_output_id, "pin")

        self.assertTrue(self.window.request_navigate_scope_parent())
        self.window.scene.focus_node(outer_id)
        self.app.processEvents()
        return outer_id, inner_id
