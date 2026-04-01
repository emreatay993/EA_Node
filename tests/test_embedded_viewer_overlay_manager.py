from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import patch

from PyQt6.QtCore import QEvent, QPointF, QRectF
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtWidgets import QWidget

from ea_node_editor.nodes.types import NodeRenderQualitySpec, NodeResult, NodeTypeSpec, PortSpec
from ea_node_editor.ui_qml.embedded_viewer_overlay_manager import EmbeddedViewerOverlaySpec
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


class _FakeOverlayWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.close_calls = 0

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self.close_calls += 1
        super().closeEvent(event)


class EmbeddedViewerOverlayManagerTests(MainWindowShellTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.window.registry.register(lambda: _ViewerOverlayPlugin(_viewer_overlay_spec()))
        self.manager = self.window.embedded_viewer_overlay_manager
        self.assertIsNotNone(self.manager)
        self.workspace_id = self.window.workspace_manager.active_workspace_id()

    def _graph_canvas_quick_item(self) -> QQuickItem:
        canvas = self._graph_canvas_item()
        self.assertIsInstance(canvas, QQuickItem)
        return canvas

    def _walk_items(self, item: QQuickItem):
        yield item
        for child in item.childItems():
            if isinstance(child, QQuickItem):
                yield from self._walk_items(child)

    def _graph_node_card(self, node_id: str) -> QQuickItem:
        for item in self._walk_items(self._graph_canvas_quick_item()):
            if item.objectName() != "graphNodeCard":
                continue
            node_data = item.property("nodeData") or {}
            if str(node_data.get("node_id", "")) == node_id:
                return item
        self.fail(f"Missing graphNodeCard for {node_id!r}")

    def _graph_viewer_body_frame(self, node_id: str) -> QQuickItem:
        node_card = self._graph_node_card(node_id)
        for item in self._walk_items(node_card):
            if item.objectName() == "graphNodeViewerBodyFrame":
                return item
        self.fail(f"Missing graphNodeViewerBodyFrame for {node_id!r}")

    def _graph_viewer_viewport(self, node_id: str) -> QQuickItem:
        node_card = self._graph_node_card(node_id)
        for item in self._walk_items(node_card):
            if item.objectName() == "graphNodeViewerViewport":
                return item
        self.fail(f"Missing graphNodeViewerViewport for {node_id!r}")

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
        self.window.view.set_view_state(1.0, x + (width * 0.5), y + (height * 0.5))
        self.app.processEvents()
        return node_id

    def _node_payload(self, node_id: str) -> dict[str, Any]:
        for payload in self.window.scene.nodes_model:
            if str(payload.get("node_id", "")) == node_id:
                return dict(payload)
        self.fail(f"Missing node payload for {node_id}")

    def _activate_overlay(self, node_id: str, *, session_id: str = "") -> _FakeOverlayWidget:
        widget = _FakeOverlayWidget()
        self.manager.set_active_overlays(
            (
                EmbeddedViewerOverlaySpec(
                    workspace_id=self.workspace_id,
                    node_id=node_id,
                    session_id=session_id or f"session::{node_id}",
                ),
            )
        )
        self.assertTrue(
            self.manager.attach_overlay_widget(
                node_id,
                widget,
                workspace_id=self.workspace_id,
            )
        )
        self.app.processEvents()
        return widget

    def _expected_overlay_rect(
        self,
        node_id: str,
        *,
        scene_x: float | None = None,
        scene_y: float | None = None,
        scene_width: float | None = None,
        scene_height: float | None = None,
    ):
        del scene_x, scene_y, scene_width, scene_height
        viewport_frame = self._graph_viewer_viewport(node_id)
        graph_canvas = self._graph_canvas_quick_item()
        root_item = self.window.quick_widget.rootObject()
        self.assertIsInstance(root_item, QQuickItem)
        top_left = viewport_frame.mapToItem(root_item, QPointF(0.0, 0.0))
        bottom_right = viewport_frame.mapToItem(
            root_item,
            QPointF(viewport_frame.width(), viewport_frame.height()),
        )
        viewport_rect = QRectF(top_left, bottom_right).normalized()
        canvas_origin = graph_canvas.mapToItem(root_item, QPointF(0.0, 0.0))
        canvas_rect = QRectF(
            float(canvas_origin.x()),
            float(canvas_origin.y()),
            float(graph_canvas.width()),
            float(graph_canvas.height()),
        )
        viewport_rect = viewport_rect.intersected(canvas_rect)
        left = float(viewport_rect.x())
        top = float(viewport_rect.y())
        width = float(viewport_rect.width())
        height = float(viewport_rect.height())
        return (left, top, width, height)

    def _assert_rect_close(
        self,
        widget: QWidget,
        node_id: str,
        *,
        scene_x: float | None = None,
        scene_y: float | None = None,
        scene_width: float | None = None,
        scene_height: float | None = None,
        delta: float = 1.1,
    ) -> None:
        left, top, width, height = self._expected_overlay_rect(
            node_id,
            scene_x=scene_x,
            scene_y=scene_y,
            scene_width=scene_width,
            scene_height=scene_height,
        )
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
        widget = self._activate_overlay(node_id)

        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        self.assertIs(self.manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        self.assertTrue(container.isVisible())
        self.assertTrue(widget.isVisible())
        self._assert_rect_close(container, node_id)
        self.assertEqual(widget.geometry(), container.rect())

        self.window.view.set_view_state(1.15, 320.0, 220.0)
        self.app.processEvents()
        self.assertTrue(container.isVisible())
        self._assert_rect_close(container, node_id)
        self.assertEqual(widget.geometry(), container.rect())

    def test_live_overlay_geometry_tracks_rendered_node_position_changes(self) -> None:
        node_id = self._add_viewer_node()
        widget = self._activate_overlay(node_id)
        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        node_card = self._graph_node_card(node_id)
        initial_geometry = container.geometry()

        self.assertTrue(node_card.setProperty("x", float(node_card.x()) + 48.0))
        self.assertTrue(node_card.setProperty("y", float(node_card.y()) + 26.0))
        self.app.processEvents()

        moved_geometry = container.geometry()
        self.assertAlmostEqual(float(moved_geometry.x()), float(initial_geometry.x()) + 48.0, delta=1.1)
        self.assertAlmostEqual(float(moved_geometry.y()), float(initial_geometry.y()) + 26.0, delta=1.1)
        self.assertAlmostEqual(float(moved_geometry.width()), float(initial_geometry.width()), delta=1.1)
        self.assertAlmostEqual(float(moved_geometry.height()), float(initial_geometry.height()), delta=1.1)
        self.assertEqual(widget.geometry(), container.rect())

    def test_live_overlay_geometry_tracks_graph_canvas_drag_preview_offsets(self) -> None:
        node_id = self._add_viewer_node()
        widget = self._activate_overlay(node_id)
        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        canvas = self._graph_canvas_quick_item()
        initial_geometry = container.geometry()

        self.assertTrue(canvas.setProperty("liveDragOffsets", {node_id: {"dx": 48.0, "dy": 26.0}}))
        self.app.processEvents()

        moved_geometry = container.geometry()
        self.assertAlmostEqual(float(moved_geometry.x()), float(initial_geometry.x()) + 48.0, delta=1.1)
        self.assertAlmostEqual(float(moved_geometry.y()), float(initial_geometry.y()) + 26.0, delta=1.1)
        self.assertAlmostEqual(float(moved_geometry.width()), float(initial_geometry.width()), delta=1.1)
        self.assertAlmostEqual(float(moved_geometry.height()), float(initial_geometry.height()), delta=1.1)
        self.assertEqual(widget.geometry(), container.rect())
        self.assertTrue(widget.isVisible())

        self.assertTrue(canvas.setProperty("liveDragOffsets", {}))
        self.app.processEvents()
        self._assert_rect_close(container, node_id)
        self.assertTrue(widget.isVisible())

    def test_live_overlay_geometry_tracks_rendered_resize_preview_state(self) -> None:
        node_id = self._add_viewer_node()
        widget = self._activate_overlay(node_id)
        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        node_card = self._graph_node_card(node_id)

        self.assertTrue(node_card.setProperty("_liveGeometryActive", True))
        self.assertTrue(node_card.setProperty("_liveX", 214.0))
        self.assertTrue(node_card.setProperty("_liveY", 142.0))
        self.assertTrue(node_card.setProperty("_liveWidth", 472.0))
        self.assertTrue(node_card.setProperty("_liveHeight", 338.0))
        self.app.processEvents()
        self._assert_rect_close(
            container,
            node_id,
            scene_x=214.0,
            scene_y=142.0,
            scene_width=472.0,
            scene_height=338.0,
        )
        self.assertEqual(widget.geometry(), container.rect())

        self.assertTrue(node_card.setProperty("_liveGeometryActive", False))
        self.app.processEvents()
        self.app.processEvents()
        self._assert_rect_close(container, node_id)

    def test_live_overlay_geometry_uses_inner_viewport_instead_of_full_body_frame(self) -> None:
        node_id = self._add_viewer_node()
        self._activate_overlay(node_id)
        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        body_frame = self._graph_viewer_body_frame(node_id)
        viewport_frame = self._graph_viewer_viewport(node_id)

        body_top_left = body_frame.mapToItem(self.window.quick_widget.rootObject(), QPointF(0.0, 0.0))
        viewport_top_left = viewport_frame.mapToItem(self.window.quick_widget.rootObject(), QPointF(0.0, 0.0))

        self.assertAlmostEqual(float(container.geometry().width()), float(viewport_frame.width()), delta=1.1)
        self.assertAlmostEqual(float(container.geometry().height()), float(viewport_frame.height()), delta=1.1)
        self.assertGreater(float(container.geometry().y()), float(body_top_left.y()))
        self.assertGreater(float(viewport_top_left.y()), float(body_top_left.y()))

    def test_offscreen_culling_hides_overlay_reuses_widget_and_tears_down_when_deactivated(self) -> None:
        node_id = self._add_viewer_node(x=120.0, y=80.0)
        widget = self._activate_overlay(node_id)

        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        self.assertTrue(container.isVisible())

        self.window.view.set_view_state(1.0, 6000.0, 6000.0)
        self.app.processEvents()
        self.assertFalse(container.isVisible())
        self.assertFalse(widget.isVisible())

        node_payload = self._node_payload(node_id)
        self.window.view.set_view_state(
            1.0,
            float(node_payload["x"]) + (float(node_payload["width"]) * 0.5),
            float(node_payload["y"]) + (float(node_payload["height"]) * 0.5),
        )
        self.app.processEvents()
        self.assertTrue(container.isVisible())
        self.assertTrue(widget.isVisible())

        self.manager.set_active_overlays(())
        self.app.processEvents()
        self.assertIsNone(self.manager.overlay_container(node_id, workspace_id=self.workspace_id))
        self.assertIsNone(self.manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(widget.close_calls, 1)

    def test_detach_overlay_widget_keeps_active_container_ready_for_clean_rebind(self) -> None:
        node_id = self._add_viewer_node()
        first_widget = self._activate_overlay(node_id)

        container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        self.assertIs(self.manager.overlay_widget(node_id, workspace_id=self.workspace_id), first_widget)

        self.manager.detach_overlay_widget(node_id, workspace_id=self.workspace_id)
        self.app.processEvents()

        self.assertEqual(first_widget.close_calls, 1)
        self.assertIsNone(self.manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        rebound_container = self.manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIs(rebound_container, container)
        self.assertFalse(rebound_container.isVisible())

        second_widget = _FakeOverlayWidget()
        self.assertTrue(
            self.manager.attach_overlay_widget(
                node_id,
                second_widget,
                workspace_id=self.workspace_id,
            )
        )
        self.app.processEvents()

        self.assertIs(self.manager.overlay_widget(node_id, workspace_id=self.workspace_id), second_widget)
        self.assertIs(self.manager.overlay_container(node_id, workspace_id=self.workspace_id), container)
        self.assertTrue(container.isVisible())
        self.assertTrue(second_widget.isVisible())
        self._assert_rect_close(container, node_id)
        self.assertEqual(second_widget.geometry(), container.rect())

    def test_paint_and_update_request_events_do_not_queue_overlay_sync(self) -> None:
        self.app.processEvents()
        self.manager._sync_queued = False
        self.manager.eventFilter(self.window.quick_widget, QEvent(QEvent.Type.Paint))
        self.assertFalse(self.manager._sync_queued)
        self.manager.eventFilter(self.window.quick_widget, QEvent(QEvent.Type.UpdateRequest))
        self.assertFalse(self.manager._sync_queued)

    def test_run_queued_sync_does_not_requeue_without_new_work(self) -> None:
        self.manager._sync_queued = True

        with patch.object(self.manager, "sync") as sync_mock:
            self.manager._run_queued_sync()

        sync_mock.assert_called_once_with()
        self.assertFalse(self.manager._sync_queued)


if __name__ == "__main__":
    unittest.main()
