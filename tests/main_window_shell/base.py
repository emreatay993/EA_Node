from __future__ import annotations

import copy
import gc
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QEvent, QObject, QMetaObject, Qt, QUrl, Q_ARG
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QMessageBox

from ea_node_editor.custom_workflows import import_custom_workflow_file
from ea_node_editor.ui.shell.window import ShellWindow
from tests.conftest import ShellTestEnvironment


class _ShellTestExecutionClient:
    def __init__(self) -> None:
        self._callbacks: list[object] = []

    def subscribe(self, callback) -> None:  # noqa: ANN001
        self._callbacks.append(callback)

    def start_run(self, project_path: str, workspace_id: str, trigger=None) -> str:  # noqa: ANN001
        return ""

    def pause_run(self, run_id: str) -> None:
        return None

    def resume_run(self, run_id: str) -> None:
        return None

    def stop_run(self, run_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._callbacks.clear()


def _action_shortcuts(action) -> set[str]:  # noqa: ANN001
    return {
        sequence.toString(QKeySequence.SequenceFormat.PortableText)
        for sequence in action.shortcuts()
    }


class MainWindowShellTestBase(unittest.TestCase):
    """Base class for tests that need a full ``ShellWindow`` environment.

    Provides ``self.app``, ``self.window``, and convenient path accessors
    via ``self._env``.
    """

    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.app.setQuitOnLastWindowClosed(False)
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        gc.collect()
        self._env = ShellTestEnvironment()
        self._env.start()
        self._execution_client_patch = patch(
            "ea_node_editor.ui.shell.window.ProcessExecutionClient",
            _ShellTestExecutionClient,
        )
        self._execution_client_patch.start()
        self._temp_dir = self._env._temp_dir
        self._session_path = self._env.session_path
        self._autosave_path = self._env.autosave_path
        self._app_preferences_path = self._env.app_preferences_path
        self._global_custom_workflows_path = self._env.global_custom_workflows_path
        self.window = ShellWindow()
        self.window.resize(1200, 800)
        self.window.show()
        self.app.sendPostedEvents()
        self.app.processEvents()
        self.app.processEvents()

    def tearDown(self) -> None:
        window = self.window
        for timer_name in ("metrics_timer", "graph_hint_timer", "autosave_timer"):
            timer = getattr(window, timer_name, None)
            if timer is not None:
                timer.stop()
        window.close()
        quick_widget = getattr(window, "quick_widget", None)
        if quick_widget is not None:
            window.takeCentralWidget()
            quick_widget.setSource(QUrl())
            quick_widget.hide()
            quick_widget.deleteLater()
            window.quick_widget = None
        window.deleteLater()
        self.window = None
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self._env.stop()
        self._execution_client_patch.stop()
        gc.collect()

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
