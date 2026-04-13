from __future__ import annotations

import pytest

from ea_node_editor.ui.shell.presenters.workspace_presenter import ShellWorkspacePresenter
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from tests.main_window_shell import bridge_support as _bridge_support
from tests.main_window_shell.bridge_support import (
    GraphCanvasBridgeTests as _GraphCanvasBridgeTests,
)

pytestmark = pytest.mark.xdist_group("p03_bridge_contracts")


class GraphCanvasBridgeTests(_GraphCanvasBridgeTests):
    __test__ = True

    def test_graph_typography_bridge_workspace_presenter_snapshots_graph_label_pixel_size(self) -> None:
        host = _bridge_support._ShellWorkspacePresenterHostStub()
        presenter = ShellWorkspacePresenter(host, ui_state=host.workspace_ui_state)
        seen = {"graphics_preferences_changed": 0}
        presenter.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "graphics_preferences_changed",
                seen["graphics_preferences_changed"] + 1,
            )
        )

        resolved = presenter.apply_graphics_preferences(
            {"typography": {"graph_label_pixel_size": 17}},
        )

        self.assertEqual(
            resolved["typography"]["graph_label_pixel_size"],
            17,
        )
        self.assertEqual(host.workspace_ui_state.graph_label_pixel_size, 17)
        self.assertEqual(presenter.graphics_graph_label_pixel_size, 17)
        self.assertEqual(seen["graphics_preferences_changed"], 1)

    def test_graph_typography_bridge_state_and_legacy_bridges_share_graph_label_pixel_size_property(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        scene = _bridge_support._GraphCanvasSceneBridgeStub()
        view = _bridge_support._GraphCanvasViewBridgeStub()
        bridge = _bridge_support._build_explicit_graph_canvas_bridge(
            parent=host,
            shell_window=host,
            canvas_source=host,
            host_source=host,
            scene_bridge=scene,
            view_bridge=view,
        )
        state_bridge = bridge.state_bridge
        seen = {
            "graphics_preferences_changed": 0,
            "legacy_graphics_preferences_changed": 0,
        }
        state_bridge.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "graphics_preferences_changed",
                seen["graphics_preferences_changed"] + 1,
            )
        )
        bridge.graphics_preferences_changed.connect(
            lambda: seen.__setitem__(
                "legacy_graphics_preferences_changed",
                seen["legacy_graphics_preferences_changed"] + 1,
            )
        )

        self.assertEqual(state_bridge.graphics_graph_label_pixel_size, 10)
        self.assertEqual(bridge.graphics_graph_label_pixel_size, 10)

        host.graphics_graph_label_pixel_size = 15
        host.graphics_preferences_changed.emit()

        self.assertEqual(state_bridge.graphics_graph_label_pixel_size, 15)
        self.assertEqual(bridge.graphics_graph_label_pixel_size, 15)
        self.assertEqual(
            seen,
            {
                "graphics_preferences_changed": 1,
                "legacy_graphics_preferences_changed": 1,
            },
        )

    def test_graph_canvas_command_bridge_routes_comment_peek_to_scene_bridge_layer(self) -> None:
        host = _bridge_support._GraphCanvasShellHostStub()
        scene = _bridge_support._GraphCanvasSceneBridgeStub()

        def can_open_comment_peek(node_id: str) -> bool:
            scene.calls.append(("can_open_comment_peek", (node_id,)))
            return node_id == "comment-1"

        def open_comment_peek(node_id: str) -> bool:
            scene.calls.append(("open_comment_peek", (node_id,)))
            if node_id != "comment-1":
                return False
            scene.active_comment_peek_node_id = node_id
            return True

        def close_comment_peek() -> bool:
            scene.calls.append(("close_comment_peek", ()))
            if not getattr(scene, "active_comment_peek_node_id", ""):
                return False
            scene.active_comment_peek_node_id = ""
            return True

        scene.active_comment_peek_node_id = ""
        scene.can_open_comment_peek = can_open_comment_peek
        scene.open_comment_peek = open_comment_peek
        scene.close_comment_peek = close_comment_peek

        bridge = GraphCanvasCommandBridge(
            host,
            shell_window=host,
            canvas_source=host,
            host_source=host,
            scene_bridge=scene,
            view_bridge=_bridge_support._GraphCanvasViewBridgeStub(),
        )

        self.assertTrue(bridge.can_open_comment_peek("comment-1"))
        self.assertFalse(bridge.can_open_comment_peek("logger-1"))
        self.assertTrue(bridge.request_open_comment_peek("comment-1"))
        self.assertEqual(bridge.active_comment_peek_node_id(), "comment-1")
        self.assertTrue(bridge.request_close_comment_peek())
        self.assertEqual(bridge.active_comment_peek_node_id(), "")
        self.assertEqual(
            scene.calls,
            [
                ("can_open_comment_peek", ("comment-1",)),
                ("can_open_comment_peek", ("logger-1",)),
                ("open_comment_peek", ("comment-1",)),
                ("close_comment_peek", ()),
            ],
        )
        self.assertNotIn(("request_open_subnode_scope", ("comment-1",)), host.calls)


__all__ = ["GraphCanvasBridgeTests"]
