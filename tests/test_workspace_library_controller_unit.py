from __future__ import annotations

import unittest

from ea_node_editor.ui.graph_interactions import GraphActionResult
from ea_node_editor.ui.shell.controllers.workspace_library_controller import WorkspaceLibraryController


class _GraphInteractionsStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str]] = []

    def connect_ports(self, node_a_id: str, port_a: str, node_b_id: str, port_b: str) -> GraphActionResult:
        self.calls.append((node_a_id, port_a, node_b_id, port_b))
        return GraphActionResult(True, "")


class _WorkspaceHostStub:
    def __init__(self) -> None:
        self._graph_interactions = _GraphInteractionsStub()


class WorkspaceLibraryControllerUnitTests(unittest.TestCase):
    def test_request_connect_ports_delegates_and_wraps_result(self) -> None:
        host = _WorkspaceHostStub()
        controller = WorkspaceLibraryController(host)  # type: ignore[arg-type]

        refreshed = {"value": False}

        def _mark_refreshed() -> None:
            refreshed["value"] = True

        controller.refresh_workspace_tabs = _mark_refreshed  # type: ignore[method-assign]

        result = controller.request_connect_ports("node_a", "out", "node_b", "in")

        self.assertTrue(result.ok)
        self.assertTrue(result.payload)
        self.assertTrue(refreshed["value"])
        self.assertEqual(host._graph_interactions.calls, [("node_a", "out", "node_b", "in")])


if __name__ == "__main__":
    unittest.main()
