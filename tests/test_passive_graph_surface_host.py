from __future__ import annotations

import unittest

from tests.graph_surface import (
    PassiveGraphSurfaceHostBoundaryTests,
    PassiveGraphSurfaceHostTests,
    PassiveGraphSurfaceInlineEditorTests,
    PassiveGraphSurfaceMediaAndScopeTests,
)
from tests.graph_surface.environment import GraphSurfaceInputContractTestBase


class LockedPlaceholderGraphHostTests(GraphSurfaceInputContractTestBase):
    def test_locked_placeholder_routes_to_addon_manager_and_blocks_mutations(self) -> None:
        self._run_qml_probe(
            "locked-placeholder-host-contract",
            """
            from PyQt6.QtCore import QObject, pyqtSlot

            class AddonManagerBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.requests = []

                @pyqtSlot(str)
                def requestOpen(self, focus_addon_id):
                    self.requests.append(str(focus_addon_id))

            addon_bridge = AddonManagerBridgeStub()
            engine.rootContext().setContextProperty("addonManagerBridge", addon_bridge)

            payload = node_payload()
            payload["read_only"] = True
            payload["unresolved"] = True
            payload["addon_id"] = "tests.addons.signal_pack"
            payload["addon_display_name"] = "Signal Pack"
            payload["addon_version"] = "2.4.1"
            payload["unavailable_reason"] = "Install Signal Pack 2.4.1 to restore this node."
            payload["ports"] = [
                {"key": "message", "label": "Message", "direction": "in", "kind": "data", "data_type": "str", "connected": False, "lockable": True, "locked": False},
                {"key": "result", "label": "Result", "direction": "out", "kind": "data", "data_type": "str", "connected": False},
            ]
            payload["inline_properties"] = [{"key": "message", "label": "Message", "inline_editor": "text", "value": "log message", "overridden_by_input": False, "input_port_label": "message"}]
            payload["locked_state"] = {
                "reason": "missing_addon",
                "label": "Requires add-on",
                "summary": "Install Signal Pack 2.4.1 to restore this node.",
                "focus_addon_id": "tests.addons.signal_pack",
            }

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            locked_chip = named_item(host, "graphNodeLockedChip")
            locked_stripe = named_item(host, "graphNodeLockedAccentStripe")
            locked_ribbon = named_item(host, "graphNodeLockedPlaceholderRibbon")
            locked_label = named_item(host, "graphNodeLockedPlaceholderLabel")
            package_label = named_item(host, "graphNodeLockedPlaceholderPackage")
            manager_button = named_item(host, "graphNodeLockedPlaceholderButton")
            locked_overlay = named_item(host, "graphNodeLockedOverlay")
            input_padlock = named_item(host, "graphNodeInputPortPadlock", "message")
            output_padlock = named_item(host, "graphNodeOutputPortPadlock", "result")
            input_toggle = named_item(host, "graphNodeInputPortLockToggleMouseArea", "message")
            input_label = named_item(host, "graphNodeInputPortLabel", "message")
            output_label = named_item(host, "graphNodeOutputPortLabel", "result")

            assert bool(host.property("graphReadOnly")) is True
            assert bool(host.property("lockedPlaceholderActive")) is True
            assert bool(host.property("surfaceInteractionLocked")) is True
            assert bool(host.property("sharedHeaderTitleEditable")) is False
            assert bool(host.property("canEnterScope")) is False
            assert str(host.property("lockedPlaceholderPackageText") or "") == "Signal Pack v2.4.1"
            assert bool(locked_chip.property("visible")) is True
            assert bool(locked_stripe.property("visible")) is True
            assert bool(locked_ribbon.property("visible")) is True
            assert str(locked_label.property("text") or "") == "Requires add-on"
            assert str(package_label.property("text") or "") == "Signal Pack v2.4.1"
            assert bool(manager_button.property("visible")) is True
            assert bool(locked_overlay.property("visible")) is True
            assert bool(input_padlock.property("visible")) is True
            assert bool(output_padlock.property("visible")) is True
            assert bool(input_toggle.property("visible")) is False
            assert float(input_label.property("opacity")) < 0.7
            assert float(output_label.property("opacity")) < 0.7

            common_actions = [variant_value(action) for action in variant_list(host.property("commonNodeActions"))]
            assert len(common_actions) == 1
            assert common_actions[0]["id"] == "openAddonManager"
            assert common_actions[0]["enabled"] is True

            requested_actions = []
            host.nodeActionRequested.connect(lambda node_id, action_id, action_payload: requested_actions.append((node_id, action_id, action_payload)))
            assert bool(host.beginInlineTitleEdit()) is False
            assert bool(host.dispatchSurfaceAction("run")) is False

            host.dispatchNodeAction("delete", {"reason": "blocked"})
            settle_events(2)
            assert requested_actions == []

            host.dispatchNodeAction("openAddonManager", None)
            settle_events(2)
            assert addon_bridge.requests == ["tests.addons.signal_pack"]

            action_rect = variant_value(host.property("lockedPlaceholderActionRect"))
            assert rect_field(action_rect, "width") > 0.0
            assert rect_field(action_rect, "height") > 0.0

            events = host_pointer_events(host)
            window = attach_host_to_window(host, 520, 360)
            action_point = host_scene_point(
                host,
                rect_field(action_rect, "x") + rect_field(action_rect, "width") * 0.5,
                rect_field(action_rect, "y") + rect_field(action_rect, "height") * 0.5,
            )
            mouse_click(window, action_point)
            settle_events(4)

            assert events["clicked"] == [("node_surface_contract_test", False)]
            assert events["opened"] == []
            assert len(addon_bridge.requests) == 2
            assert addon_bridge.requests[-1] == "tests.addons.signal_pack"

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

__all__ = [
    "PassiveGraphSurfaceHostBoundaryTests",
    "PassiveGraphSurfaceHostTests",
    "PassiveGraphSurfaceInlineEditorTests",
    "PassiveGraphSurfaceMediaAndScopeTests",
    "LockedPlaceholderGraphHostTests",
]

if __name__ == "__main__":
    unittest.main()
