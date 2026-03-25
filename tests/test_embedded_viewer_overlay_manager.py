from __future__ import annotations

import unittest
from typing import Any

from PyQt6.QtCore import QObject, QPointF
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtWidgets import QWidget

from ea_node_editor.nodes.types import NodeRenderQualitySpec, NodeResult, NodeTypeSpec, PortSpec
from tests.main_window_shell.base import MainWindowShellTestBase


class _ViewerOverlayPlugin:
    def __init__(self, spec: NodeTypeSpec) -> None:
        self._spec = spec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult()


def _viewer_overlay_spec() -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id="tests.embedded_viewer_overlay",
        display_name="Embedded Viewer Overlay",
        category="Tests",
        icon="",
        ports=(
            PortSpec("fields", "in", "data", "dpf_field"),
            PortSpec("session", "out", "data", "dpf_view_session"),
        ),
        properties=(),
        surface_family="viewer",
        render_quality=NodeRenderQualitySpec(
            weight_class="heavy",
            max_performance_strategy="proxy_surface",
            supported_quality_tiers=("full", "proxy"),
        ),
    )


class _FakeInteractorWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.close_calls = 0

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self.close_calls += 1
        super().closeEvent(event)


class _FakeInteractorFactory:
    def __init__(self) -> None:
        self.create_calls = 0
        self.widgets: list[_FakeInteractorWidget] = []

    def __call__(self, parent: QWidget) -> _FakeInteractorWidget:
        self.create_calls += 1
        widget = _FakeInteractorWidget(parent)
        self.widgets.append(widget)
        return widget


class EmbeddedViewerOverlayManagerTests(MainWindowShellTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.window.registry.register(lambda: _ViewerOverlayPlugin(_viewer_overlay_spec()))
        self.manager = self.window.embedded_viewer_overlay_manager
        self.assertIsNotNone(self.manager)
        self.factory = _FakeInteractorFactory()
        self.manager.set_interactor_factory(self.factory)
        self.workspace_id = self.window.workspace_manager.active_workspace_id()

    def _graph_canvas_quick_item(self) -> QQuickItem:
        canvas = self._graph_canvas_item()
        self.assertIsInstance(canvas, QQuickItem)
        return canvas

    def _add_viewer_node(
        self,
        *,
        x: float = 160.0,
        y: float = 90.0,
        width: float = 360.0,
        height: float = 280.0,
    ) -> str:
        node_id = self.window.scene.add_node_from_type("tests.embedded_viewer_overlay", x=x, y=y)
        self.window.scene.resize_node(node_id, width, height)
        self.app.processEvents()
        return node_id

    def _node_payload(self, node_id: str) -> dict[str, Any]:
        for payload in self.window.scene.nodes_model:
            if str(payload.get("node_id", "")) == node_id:
                return dict(payload)
        self.fail(f"Missing node payload for {node_id}")

    def _emit_viewer_event(
        self,
        *,
        event_type: str,
        node_id: str,
        session_id: str = "",
        keep_live: bool = False,
        live_policy: str = "focus_only",
        live_mode: str = "full",
    ) -> None:
        resolved_session_id = session_id or f"session::{node_id}"
        cache_state = "live_ready" if live_mode == "full" else "proxy_ready"
        self.window.execution_event.emit(
            {
                "type": event_type,
                "request_id": f"req::{event_type}::{node_id}",
                "workspace_id": self.workspace_id,
                "node_id": node_id,
                "session_id": resolved_session_id,
                "data_refs": {},
                "summary": {
                    "cache_state": cache_state,
                },
                "options": {
                    "session_state": "open",
                    "cache_state": cache_state,
                    "live_policy": live_policy,
                    "keep_live": keep_live,
                    "playback_state": "paused",
                    "live_mode": live_mode,
                },
            }
        )
        self.app.processEvents()

    def _close_viewer_session(self, *, node_id: str, session_id: str = "") -> None:
        resolved_session_id = session_id or f"session::{node_id}"
        self.window.execution_event.emit(
            {
                "type": "viewer_session_closed",
                "request_id": f"req::close::{node_id}",
                "workspace_id": self.workspace_id,
                "node_id": node_id,
                "session_id": resolved_session_id,
                "data_refs": {},
                "summary": {
                    "cache_state": "empty",
                    "close_reason": "test_close",
                },
                "options": {
                    "reason": "test_close",
                    "live_mode": "proxy",
                },
            }
        )
        self.app.processEvents()

    def _expected_overlay_rect(self, node_id: str):
        payload = self._node_payload(node_id)
        live_rect = payload["viewer_surface"]["live_rect"]
        graph_canvas = self._graph_canvas_quick_item()
        root_item = self.window.quick_widget.rootObject()
        self.assertIsInstance(root_item, QQuickItem)
        canvas_origin = graph_canvas.mapToItem(root_item, QPointF(0.0, 0.0))
        zoom = float(self.window.view.zoom_value)
        center_x = float(self.window.view.center_x)
        center_y = float(self.window.view.center_y)
        left = canvas_origin.x() + (float(graph_canvas.width()) * 0.5) + ((float(payload["x"]) + float(live_rect["x"]) - center_x) * zoom)
        top = canvas_origin.y() + (float(graph_canvas.height()) * 0.5) + ((float(payload["y"]) + float(live_rect["y"]) - center_y) * zoom)
        width = float(live_rect["width"]) * zoom
        height = float(live_rect["height"]) * zoom
        return (left, top, width, height)

    def _assert_rect_close(self, widget: QWidget, node_id: str, *, delta: float = 1.1) -> None:
        left, top, width, height = self._expected_overlay_rect(node_id)
        geometry = widget.geometry()
        self.assertAlmostEqual(float(geometry.x()), left, delta=delta)
        self.assertAlmostEqual(float(geometry.y()), top, delta=delta)
        self.assertAlmostEqual(float(geometry.width()), width, delta=delta)
        self.assertAlmostEqual(float(geometry.height()), height, delta=delta)

    def test_shell_window_creates_overlay_manager_parented_to_qquickwidget(self) -> None:
        self.assertIs(self.manager.parent(), self.window.quick_widget)
        self.assertIs(self.manager.quick_widget, self.window.quick_widget)

    def test_live_overlay_geometry_tracks_pan_zoom_and_node_move_resize(self) -> None:
        node_id = self._add_viewer_node()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        widget = self.manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        self.assertIsNotNone(widget)
        self.assertEqual(self.factory.create_calls, 1)
        self.assertTrue(container.isVisible())
        self.assertTrue(widget.isVisible())
        self._assert_rect_close(container, node_id)
        self.assertEqual(widget.geometry(), container.rect())

        self.window.view.set_view_state(1.35, 90.0, 40.0)
        self.app.processEvents()
        self.assertEqual(self.factory.create_calls, 1)
        self._assert_rect_close(container, node_id)

        self.window.scene.move_node(node_id, 280.0, 170.0)
        self.window.scene.resize_node(node_id, 420.0, 320.0)
        self.app.processEvents()
        self.assertEqual(self.factory.create_calls, 1)
        self._assert_rect_close(container, node_id)
        self.assertEqual(widget.geometry(), container.rect())

    def test_offscreen_culling_hides_overlay_reuses_widget_and_tears_down_on_close(self) -> None:
        node_id = self._add_viewer_node(x=120.0, y=80.0)
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        widget = self.manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        self.assertIsNotNone(widget)
        self.assertTrue(container.isVisible())

        self.window.view.set_view_state(1.0, 6000.0, 6000.0)
        self.app.processEvents()
        self.assertFalse(container.isVisible())
        self.assertFalse(widget.isVisible())
        self.assertEqual(self.factory.create_calls, 1)

        self.window.view.set_view_state(1.0, 0.0, 0.0)
        self.app.processEvents()
        self.assertTrue(container.isVisible())
        self.assertTrue(widget.isVisible())
        self.assertEqual(self.factory.create_calls, 1)

        self._close_viewer_session(node_id=node_id)
        self.app.processEvents()
        self.assertIsNone(self.manager.overlay_container(node_id, workspace_id=self.workspace_id))
        self.assertIsNone(self.manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(widget.close_calls, 1)

    def test_focus_only_sessions_show_one_live_overlay_until_keep_live_is_enabled(self) -> None:
        first_node_id = self._add_viewer_node(x=120.0, y=80.0)
        second_node_id = self._add_viewer_node(x=240.0, y=200.0)
        self.window.view.set_view_state(1.0, 200.0, 140.0)
        self.app.processEvents()

        self.window.scene.select_node(first_node_id, False)
        self.app.processEvents()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=first_node_id)
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=second_node_id)

        first_container = self.manager.overlay_container(first_node_id, workspace_id=self.workspace_id)
        second_container = self.manager.overlay_container(second_node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(first_container)
        self.assertTrue(first_container.isVisible())
        self.assertIsNone(second_container)

        self.window.scene.select_node(second_node_id, False)
        self.app.processEvents()
        self.assertIsNone(self.manager.overlay_container(second_node_id, workspace_id=self.workspace_id))

        # Under the P13 bridge contract, refocusing a proxy-demoted viewer requests
        # rematerialization before the overlay becomes live again.
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=second_node_id)
        second_container = self.manager.overlay_container(second_node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(second_container)
        self.assertFalse(first_container.isVisible())
        self.assertTrue(second_container.isVisible())

        self._emit_viewer_event(
            event_type="viewer_session_updated",
            node_id=first_node_id,
            keep_live=True,
            live_policy="keep_live",
        )
        self.app.processEvents()

        first_container = self.manager.overlay_container(first_node_id, workspace_id=self.workspace_id)
        second_container = self.manager.overlay_container(second_node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(first_container)
        self.assertIsNotNone(second_container)
        self.assertTrue(first_container.isVisible())
        self.assertTrue(second_container.isVisible())


if __name__ == "__main__":
    unittest.main()
