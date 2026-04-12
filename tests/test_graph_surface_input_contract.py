from __future__ import annotations

import unittest

import pytest

from tests.graph_surface import (
    GraphSurfaceBoundaryContractTests,
    GraphSurfaceInlineEditorContractTests,
    GraphSurfaceInputContractTests,
    GraphSurfaceMediaAndScopeContractTests,
)
from tests.graph_surface.environment import GraphSurfaceInputContractTestBase

pytestmark = pytest.mark.xdist_group("p03_graph_surface")


class GraphSurfaceLockedPortContractTests(GraphSurfaceInputContractTestBase):
    def test_graph_node_host_emits_locked_input_port_double_click_contract(self) -> None:
        self._run_qml_probe(
            "locked-port-double-click-contract",
            """
            payload = node_payload()
            payload["ports"] = [
                {"key": "message", "label": "Message", "direction": "in", "kind": "data", "data_type": "str", "connected": False, "locked": True, "lockable": True},
                {"key": "details", "label": "Details", "direction": "in", "kind": "data", "data_type": "json", "connected": False, "locked": True, "lockable": False},
            ]
            payload["inline_properties"] = [
                {"key": "message", "label": "Message", "inline_editor": "text", "value": "locked text", "overridden_by_input": False, "input_port_label": "message"},
                {"key": "details", "label": "Details", "inline_editor": "text", "value": "{\\"note\\": \\"raw\\"}", "overridden_by_input": False, "input_port_label": "details"},
            ]

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            locked_row = named_item(host, "graphNodeInputPortRow", "message")
            unsupported_row = named_item(host, "graphNodeInputPortRow", "details")
            locked_dot = named_item(host, "graphNodeInputPortDot", "message")
            locked_padlock = named_item(host, "graphNodeInputPortPadlock", "message")
            lock_toggle = named_item(host, "graphNodeInputPortLockToggleMouseArea", "message")
            unsupported_toggle = named_item(host, "graphNodeInputPortLockToggleMouseArea", "details")

            assert bool(locked_row.property("lockableState")) is True
            assert bool(locked_row.property("lockedState")) is True
            assert bool(unsupported_row.property("lockableState")) is False
            assert bool(unsupported_row.property("lockedState")) is False
            assert abs(item_scene_point(locked_dot).x() - item_scene_point(locked_padlock).x()) < 1.0
            assert abs(item_scene_point(locked_dot).y() - item_scene_point(locked_padlock).y()) < 1.0
            assert bool(lock_toggle.property("visible")) is True
            assert bool(unsupported_toggle.property("visible")) is False

            events = []
            host.portDoubleClicked.connect(
                lambda node_id, port_key, direction, locked: events.append((node_id, port_key, direction, locked))
            )
            window = attach_host_to_window(host, 480, 360)
            mouse_click(window, item_scene_point(lock_toggle))
            settle_events(4)
            assert events == [], events

            mouse_double_click(window, item_scene_point(lock_toggle))
            settle_events(4)

            assert events == [("node_surface_contract_test", "message", "in", True)], events

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_node_host_emits_unlocked_lockable_input_double_click_contract(self) -> None:
        self._run_qml_probe(
            "unlocked-lockable-port-double-click-contract",
            """
            payload = node_payload()
            payload["ports"] = [
                {"key": "message", "label": "Message", "direction": "in", "kind": "data", "data_type": "str", "lockable": True, "locked": False},
            ]

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            unlocked_row = named_item(host, "graphNodeInputPortRow", "message")
            unlocked_mouse = named_item(host, "graphNodeInputPortMouseArea", "message")

            assert bool(unlocked_row.property("lockableState")) is True
            assert bool(unlocked_row.property("lockedState")) is False

            events = []
            host.portDoubleClicked.connect(
                lambda node_id, port_key, direction, locked: events.append((node_id, port_key, direction, locked))
            )
            window = attach_host_to_window(host, 480, 360)
            mouse_double_click(window, item_scene_point(unlocked_mouse))
            settle_events(4)

            assert events == [("node_surface_contract_test", "message", "in", False)], events

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

__all__ = [
    "GraphSurfaceBoundaryContractTests",
    "GraphSurfaceInlineEditorContractTests",
    "GraphSurfaceInputContractTests",
    "GraphSurfaceLockedPortContractTests",
    "GraphSurfaceMediaAndScopeContractTests",
]

if __name__ == "__main__":
    unittest.main()
