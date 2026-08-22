from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import call, patch

from ea_node_editor.help.help_bridge import HelpBridge
from ea_node_editor.runtime_contracts import GRAPH_DATA_TYPE_ID, STRING_DATA_TYPE_ID


class _SceneStub:
    def __init__(self, node_id: str = "") -> None:
        self._node_id = node_id

    def selected_node_id(self) -> str:
        return self._node_id


class _ShellWindowStub:
    def __init__(self, node_id: str = "") -> None:
        self.scene = _SceneStub(node_id)
        self.registry = None


class _RegistryStub:
    def __init__(self, spec: object | None = None) -> None:
        self._spec = spec

    def spec_or_none(self, type_id: str) -> object:
        return self._spec or SimpleNamespace(display_name="DPF Result Fields", type_id=type_id)


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

    def test_show_help_for_selected_node_clears_stale_markdown(self) -> None:
        shell_window = _ShellWindowStub("node-1")
        bridge = HelpBridge(shell_window=shell_window)
        with patch(
            "ea_node_editor.help.help_bridge.markdown_for_node",
            return_value=("# Operator Spec", "dpf.op.foo", "Foo"),
        ):
            self.assertTrue(bridge.show_help_for_selected_node())
        self.assertEqual(bridge.markdown, "# Operator Spec")
        self.assertTrue(bridge.has_help)

        # Re-selecting a node without docs (non-DPF) must clear the stale help.
        with patch("ea_node_editor.help.help_bridge.markdown_for_node", return_value=None):
            self.assertFalse(bridge.show_help_for_selected_node())
        self.assertEqual(bridge.markdown, "")
        self.assertFalse(bridge.has_help)
        self.assertEqual(bridge.title, "")
        self.assertEqual(bridge.type_id, "")

    def test_can_show_help_for_selected_node_uses_current_selection(self) -> None:
        shell_window = _ShellWindowStub("node-1")
        bridge = HelpBridge(shell_window=shell_window)

        with patch(
            "ea_node_editor.help.help_bridge.markdown_for_node",
            return_value=("# Node Help", "core.logger", "Logger"),
        ) as lookup:
            self.assertTrue(bridge.can_show_help_for_selected_node())

        lookup.assert_called_once_with(shell_window, "node-1")

    def test_show_help_for_type_accepts_curated_dpf_workflow(self) -> None:
        shell_window = _ShellWindowStub()
        shell_window.registry = _RegistryStub()
        bridge = HelpBridge(shell_window=shell_window)

        with patch(
            "ea_node_editor.help.help_bridge.markdown_for_type_id",
            return_value="# DPF Result Fields",
        ) as lookup:
            result = bridge.show_help_for_type("dpf.workflow.result_fields")

        self.assertTrue(result)
        self.assertTrue(bridge.visible)
        self.assertEqual(bridge.title, "DPF Result Fields")
        self.assertEqual(bridge.type_id, "dpf.workflow.result_fields")
        lookup.assert_called_once_with("dpf.workflow.result_fields", shell_window.registry)

    def test_show_help_for_type_builds_structured_fallback_for_registered_node(self) -> None:
        spec = SimpleNamespace(
            display_name="Logger",
            type_id="core.logger",
            description="Writes values to the execution log.",
            keywords=("log", "debug"),
            ports=(
                SimpleNamespace(
                    key="message",
                    label="Message",
                    description="Message written to the log.",
                    direction="in",
                    kind="data",
                    data_type=STRING_DATA_TYPE_ID,
                    data_access="tree",
                ),
            ),
        )
        shell_window = _ShellWindowStub()
        shell_window.registry = _RegistryStub(spec)
        bridge = HelpBridge(shell_window=shell_window)
        requested: list[bool] = []
        bridge.help_tab_requested.connect(lambda: requested.append(True))

        result = bridge.show_help_for_type("core.logger")

        self.assertTrue(result)
        self.assertEqual(requested, [True])
        self.assertIn("# Logger", bridge.markdown)
        self.assertIn("**Keywords:** log, debug", bridge.markdown)
        self.assertIn("## Inputs", bridge.markdown)
        self.assertIn("Message written to the log.", bridge.markdown)
        self.assertNotIn("## Outputs", bridge.markdown)

    def test_show_help_for_type_renders_trigger_benchmark_copy(self) -> None:
        from ea_node_editor.nodes.builtins.core import TriggerNodePlugin

        shell_window = _ShellWindowStub()
        shell_window.registry = _RegistryStub(TriggerNodePlugin().spec())
        bridge = HelpBridge(shell_window=shell_window)

        self.assertTrue(bridge.show_help_for_type("core.trigger"))
        self.assertIn("# Trigger", bridge.markdown)
        self.assertIn(
            "Stop downstream nodes from running until you click the button.",
            bridge.markdown,
        )
        self.assertIn(
            "**Keywords:** button, action, run, dam, gate, block", bridge.markdown
        )
        self.assertIn("## Inputs", bridge.markdown)
        self.assertIn(
            f"- **Input** (`input`, `{GRAPH_DATA_TYPE_ID}`) — The data that is blocked until you "
            "click the button.",
            bridge.markdown,
        )
        self.assertIn("## Outputs", bridge.markdown)
        self.assertIn(
            f"- **Output** (`output`, `{GRAPH_DATA_TYPE_ID}`) — The current output. The output is "
            "not updated until you click the button.",
            bridge.markdown,
        )


if __name__ == "__main__":
    unittest.main()
