from __future__ import annotations

import unittest
from unittest.mock import call, patch

from ea_node_editor.help.help_bridge import HelpBridge


class _SceneStub:
    def __init__(self, node_id: str = "") -> None:
        self._node_id = node_id

    def selected_node_id(self) -> str:
        return self._node_id


class _ShellWindowStub:
    def __init__(self, node_id: str = "") -> None:
        self.scene = _SceneStub(node_id)
        self.registry = None


class HelpBridgeSelectedNodeTests(unittest.TestCase):
    def test_show_help_for_selected_node_requests_help_tab_without_docs(self) -> None:
        shell_window = _ShellWindowStub("node-1")
        bridge = HelpBridge(shell_window=shell_window)
        requested: list[bool] = []
        bridge.help_tab_requested.connect(lambda: requested.append(True))

        with patch("ea_node_editor.help.help_bridge.markdown_for_node", return_value=None) as lookup:
            result = bridge.show_help_for_selected_node()

        self.assertFalse(result)
        self.assertEqual(requested, [True])
        self.assertFalse(bridge.visible)
        lookup.assert_called_once_with(shell_window, "node-1")

    def test_show_help_for_selected_node_loads_markdown_for_selected_node(self) -> None:
        shell_window = _ShellWindowStub("node-1")
        bridge = HelpBridge(shell_window=shell_window)
        requested: list[bool] = []
        bridge.help_tab_requested.connect(lambda: requested.append(True))

        with patch(
            "ea_node_editor.help.help_bridge.markdown_for_node",
            return_value=("# Node Help", "core.logger", "Logger"),
        ) as lookup:
            result = bridge.show_help_for_selected_node()

        self.assertTrue(result)
        self.assertEqual(requested, [True])
        self.assertTrue(bridge.visible)
        self.assertEqual(bridge.markdown, "# Node Help")
        self.assertEqual(bridge.type_id, "core.logger")
        self.assertEqual(bridge.title, "Logger")
        self.assertEqual(
            lookup.call_args_list,
            [call(shell_window, "node-1"), call(shell_window, "node-1")],
        )

    def test_can_show_help_for_selected_node_uses_current_selection(self) -> None:
        shell_window = _ShellWindowStub("node-1")
        bridge = HelpBridge(shell_window=shell_window)

        with patch(
            "ea_node_editor.help.help_bridge.markdown_for_node",
            return_value=("# Node Help", "core.logger", "Logger"),
        ) as lookup:
            self.assertTrue(bridge.can_show_help_for_selected_node())

        lookup.assert_called_once_with(shell_window, "node-1")


if __name__ == "__main__":
    unittest.main()
