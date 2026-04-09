from __future__ import annotations

import pytest

from ea_node_editor.ui.shell.presenters.workspace_presenter import ShellWorkspacePresenter
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


__all__ = ["GraphCanvasBridgeTests"]
