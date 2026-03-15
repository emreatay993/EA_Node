from __future__ import annotations

from PyQt6.QtCore import QObject
from PyQt6.QtQuick import QQuickItem

from ea_node_editor.ui.shell.runtime_clipboard import build_graph_fragment_payload, serialize_graph_fragment_payload
from tests.main_window_shell.base import MainWindowShellTestBase
from tests.main_window_shell.shell_basics_and_search import *  # noqa: F401,F403
from tests.main_window_shell.drop_connect_and_workflow_io import *  # noqa: F401,F403
from tests.main_window_shell.edit_clipboard_history import *  # noqa: F401,F403
from tests.main_window_shell.passive_style_context_menus import *  # noqa: F401,F403
from tests.main_window_shell.passive_property_editors import *  # noqa: F401,F403
from tests.main_window_shell.view_library_inspector import *  # noqa: F401,F403


def _named_child_items(root: QObject, object_name: str) -> list[QQuickItem]:
    matches: list[QQuickItem] = []

    def _visit(item: QObject) -> None:
        if not isinstance(item, QQuickItem):
            return
        if item.objectName() == object_name:
            matches.append(item)
        for child in item.childItems():
            _visit(child)

    _visit(root)
    return matches


class MainWindowShellGraphCanvasHostTests(MainWindowShellTestBase):
    def test_graph_canvas_keeps_graph_node_card_discoverability_after_host_refactor(self) -> None:
        graph_canvas = self._graph_canvas_item()
        self.window.scene.add_node_from_type("core.logger", 180.0, 120.0)
        self.app.processEvents()

        node_cards = _named_child_items(graph_canvas, "graphNodeCard")
        self.assertGreaterEqual(len(node_cards), 1)
        self.assertIsNotNone(node_cards[0].findChild(QObject, "graphNodeStandardSurface"))

    def test_plain_text_graph_fragment_payload_is_ignored_by_paste(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.scene.add_node_from_type("core.start", x=25.0, y=35.0)
        before_state = self._workspace_state()
        before_depth = self.window.runtime_history.undo_depth(workspace_id)
        clipboard = self.app.clipboard()

        valid_text_payload = serialize_graph_fragment_payload(
            build_graph_fragment_payload(
                nodes=[
                    {
                        "ref_id": "ref-start",
                        "type_id": "core.start",
                        "title": "Start",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {},
                        "visual_style": {},
                        "parent_node_id": None,
                    }
                ],
                edges=[],
            )
        )
        self.assertIsNotNone(valid_text_payload)
        clipboard.setText(str(valid_text_payload))

        pasted = self.window.request_paste_selected_nodes()
        self.assertFalse(pasted)
        self.assertEqual(self._workspace_state(), before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_depth)


if __name__ == "__main__":
    import unittest

    unittest.main()
