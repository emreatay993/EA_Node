from __future__ import annotations

import time
import unittest
from typing import Any
from unittest.mock import patch

from PyQt6.QtCore import QEvent, QObject, QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QImage, QKeyEvent
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtWidgets import QWidget

from ea_node_editor.addons.catalog import ANSYS_DPF_ADDON_ID
from ea_node_editor.app_preferences import default_app_preferences_document, set_addon_state
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_VIEWER_NODE_TYPE_ID,
    DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
)
from ea_node_editor.nodes.types import NodeRenderQualitySpec, NodeResult, NodeTypeSpec, PortSpec
from ea_node_editor.ui_qml.embedded_viewer_overlay_manager import VIEWER_SESSION_OVERLAY_OWNER
from ea_node_editor.ui_qml.dpf_viewer_widget_binder import DpfViewerWidgetBinder
from ea_node_editor.ui_qml import viewer_host_service as viewer_host_module
from ea_node_editor.ui_qml.viewer_host_service import ViewerHostService, _cache_relevant_options
from ea_node_editor.ui_qml.viewer_widget_binder import ViewerWidgetNoBind
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
        type_id="tests.viewer_host_service_overlay",
        display_name="Viewer Host Service Overlay",
        category_path=("Tests",),
        icon="",
        ports=(
            PortSpec("fields", "in", "data", 'COREX.Ansys.DPF.Field', required=False),
            PortSpec("session", "out", "data", 'COREX.Viewer.Session'),
        ),
        properties=(),
        surface_family="viewer",
        render_quality=NodeRenderQualitySpec(
            supported_quality_tiers=("full", "proxy"),
        ),
    )


class _ViewerExecutionClientStub:
    def __init__(self) -> None:
        self._request_counter = 0
        self.open_calls: list[dict[str, Any]] = []
        self.update_calls: list[dict[str, Any]] = []
        self.materialize_calls: list[dict[str, Any]] = []
        self.close_calls: list[dict[str, Any]] = []

    def _next_request_id(self, prefix: str) -> str:
        self._request_counter += 1
        return f"{prefix}_{self._request_counter}"

    def start_run(  # noqa: ANN001
        self,
        project_path: str,
        workspace_id: str,
        trigger=None,
        *,
        execution_backend=None,
        target_node_ids=(),
        trigger_publications=None,
        trigger_captures=None,
        clicked_trigger_node_id: str = "",
    ) -> str:
        return ""

    def open_viewer_session(self, **kwargs: Any) -> str:
        request_id = self._next_request_id("open")
        self.open_calls.append({"request_id": request_id, **kwargs})
        return request_id

    def update_viewer_session(self, **kwargs: Any) -> str:
        request_id = self._next_request_id("update")
        self.update_calls.append({"request_id": request_id, **kwargs})
        return request_id

    def materialize_viewer_data(self, **kwargs: Any) -> str:
        request_id = self._next_request_id("materialize")
        self.materialize_calls.append({"request_id": request_id, **kwargs})
        return request_id

    def close_viewer_session(self, **kwargs: Any) -> str:
        request_id = self._next_request_id("close")
        self.close_calls.append({"request_id": request_id, **kwargs})
        return request_id

    def shutdown(self) -> None:
        return None


class _FakeBinderWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.close_calls = 0

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self.close_calls += 1
        super().closeEvent(event)


class _ParentChangeRecorder(QObject):
    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self.records: list[dict[str, Any]] = []

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if isinstance(watched, QWidget) and event is not None and event.type() == QEvent.Type.ParentChange:
            parent = watched.parentWidget()
            window = parent.window() if parent is not None else None
            self.records.append(
                {
                    "parent": parent,
                    "parent_visible": bool(parent is not None and parent.isVisible()),
                    "window_visible": bool(window is not None and window.isVisible()),
                    "parent_has_handle": bool(window is not None and window.windowHandle() is not None),
                    "window_has_handle": bool(window is not None and window.windowHandle() is not None),
                }
            )
        return False


class _RecordingBinder:
    def __init__(
        self,
        *,
        reuse_current_widget: bool = True,
        no_bind_predicate=None,  # noqa: ANN001
        captured_camera_state: dict[str, Any] | None = None,
        captured_preview_image: QImage | None = None,
        fail_prepare: bool = False,
        fail_refresh: bool = False,
        pending_refreshes: int = 0,
    ) -> None:
        self.reuse_current_widget = reuse_current_widget
        self.no_bind_predicate = no_bind_predicate
        self.captured_camera_state = dict(captured_camera_state or {})
        self.captured_preview_image = captured_preview_image.copy() if isinstance(captured_preview_image, QImage) else QImage()
        self.bind_calls: list[dict[str, Any]] = []
        self.release_calls: list[dict[str, Any]] = []
        self.capture_calls: list[QWidget] = []
        self.capture_preview_calls: list[QWidget] = []
        self.activate_selection_calls: list[dict[str, Any]] = []
        self.selection_filter_calls: list[dict[str, Any]] = []
        self.fail_prepare = fail_prepare
        self.fail_refresh = fail_refresh
        self.pending_refreshes = max(0, int(pending_refreshes))
        self.lifecycle_calls: list[dict[str, Any]] = []
        self.widgets: list[_FakeBinderWidget] = []

    def bind_widget(self, request) -> QWidget | None:  # noqa: ANN001
        container = request.container
        destination_window = container.window() if isinstance(container, QWidget) else None
        self.bind_calls.append(
            {
                "workspace_id": request.workspace_id,
                "node_id": request.node_id,
                "session_id": request.session_id,
                "backend_id": request.backend_id,
                "transport_revision": request.transport_revision,
                "live_mode": request.live_mode,
                "cache_state": request.cache_state,
                "camera_state": dict(request.camera_state),
                "transport": dict(request.transport),
                "options": dict(request.options),
                "container_visible": bool(container is not None and container.isVisible()),
                "window_visible": bool(destination_window is not None and destination_window.isVisible()),
                "window_has_handle": bool(
                    destination_window is not None and destination_window.windowHandle() is not None
                ),
            }
        )
        if callable(self.no_bind_predicate) and self.no_bind_predicate(request):
            raise ViewerWidgetNoBind("tests requested no bind")
        if self.reuse_current_widget and isinstance(request.current_widget, _FakeBinderWidget):
            return request.current_widget
        widget = _FakeBinderWidget(request.container)
        self.widgets.append(widget)
        return widget

    def release_widget(self, request) -> None:  # noqa: ANN001
        self.lifecycle_calls.append(
            {
                "kind": "release",
                "widget": request.widget,
                "parent": request.widget.parent() if request.widget is not None else None,
            }
        )
        self.release_calls.append(
            {
                "workspace_id": request.workspace_id,
                "node_id": request.node_id,
                "session_id": request.session_id,
                "backend_id": request.backend_id,
                "transport_revision": request.transport_revision,
                "reason": request.reason,
                "widget": request.widget,
                "visible": bool(request.widget.isVisible()) if request.widget is not None else False,
            }
        )

    def prepare_for_reparent(self, widget: QWidget) -> None:
        self.lifecycle_calls.append(
            {
                "kind": "prepare",
                "widget": widget,
                "parent": widget.parent(),
            }
        )
        if self.fail_prepare:
            raise RuntimeError("test prepare failure")

    def refresh_after_attach(self, widget: QWidget) -> None:
        self.lifecycle_calls.append(
            {
                "kind": "refresh",
                "widget": widget,
                "parent": widget.parent(),
                "window_visible": widget.window().isVisible(),
            }
        )
        if self.pending_refreshes > 0:
            self.pending_refreshes -= 1
            pending = ViewerWidgetNoBind("test attachment pending")
            pending.retry_when_ready = True
            raise pending
        if self.fail_refresh:
            raise RuntimeError("test refresh failure")

    def capture_camera_state(self, widget: QWidget) -> dict[str, Any]:
        self.capture_calls.append(widget)
        return dict(self.captured_camera_state)

    def capture_preview_image(self, widget: QWidget) -> QImage:
        self.capture_preview_calls.append(widget)
        return self.captured_preview_image.copy()

    def activate_selection(self, widget: QWidget, entities: list[dict[str, Any]]) -> bool:
        self.activate_selection_calls.append(
            {
                "widget": widget,
                "entities": [dict(entity) for entity in entities],
            }
        )
        return True

    def set_selection_filter(self, widget: QWidget, value: str) -> bool:
        self.selection_filter_calls.append({"widget": widget, "value": value})
        return True


class _ViewStateBinder(_RecordingBinder):
    def __init__(self, *, view_state: dict[str, Any] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.view_state = dict(view_state or {})
        self.capture_view_state_calls: list[QWidget] = []
        self.restore_calls: list[dict[str, Any]] = []

    def capture_view_state(self, widget: QWidget) -> dict[str, Any]:
        self.capture_view_state_calls.append(widget)
        return dict(self.view_state)

    def restore_view_state(self, widget: QWidget, state) -> bool:  # noqa: ANN001
        self.restore_calls.append(dict(state))
        return True


class _FakeCameraWidget(_FakeBinderWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.view_calls: list[str] = []
        self.reset_camera_calls = 0
        self.render_calls = 0

    def view_isometric(self) -> None:
        self.view_calls.append("iso")

    def view_xy(self) -> None:
        self.view_calls.append("xy")

    def view_xz(self) -> None:
        self.view_calls.append("xz")

    def view_yz(self) -> None:
        self.view_calls.append("yz")

    def reset_camera(self) -> None:
        self.reset_camera_calls += 1

    def render(self) -> None:
        self.render_calls += 1


class _CameraStatsBinder(_RecordingBinder):
    def __init__(self, *, stats: dict[str, Any] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.stats = dict(stats or {})

    def bind_widget(self, request) -> QWidget | None:  # noqa: ANN001
        if self.reuse_current_widget and isinstance(request.current_widget, _FakeCameraWidget):
            return request.current_widget
        widget = _FakeCameraWidget(request.container)
        self.widgets.append(widget)
        return widget

    def render_stats(self, widget: QWidget) -> dict[str, Any]:
        return dict(self.stats)


class ViewerHostAttachRefreshUnitTests(unittest.TestCase):
    def test_retryable_attach_refresh_has_an_explicit_pending_result(self) -> None:
        class PendingBinder:
            @staticmethod
            def refresh_after_attach(_widget) -> None:  # noqa: ANN001
                pending = ViewerWidgetNoBind("test attachment pending")
                pending.retry_when_ready = True
                raise pending

        host = ViewerHostService()
        try:
            self.assertIsNone(
                host._refresh_widget_after_presentation_attach(PendingBinder(), object())
            )
            self.assertEqual(host.last_error, "")
        finally:
            host.shutdown()

    def test_explicit_false_attach_refresh_is_a_terminal_failure(self) -> None:
        class FailedBinder:
            @staticmethod
            def refresh_after_attach(_widget) -> bool:  # noqa: ANN001
                return False

        host = ViewerHostService()
        try:
            self.assertFalse(
                host._refresh_widget_after_presentation_attach(FailedBinder(), object())
            )
            self.assertEqual(
                host.last_error,
                "Viewer could not refresh after attachment.",
            )
        finally:
            host.shutdown()


class ViewerHostServiceTests(MainWindowShellTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.window.registry.register(lambda: _ViewerOverlayPlugin(_viewer_overlay_spec()))
        self.window.execution_client = _ViewerExecutionClientStub()
        self.host_service = self.window.viewer_host_service
        self.bridge = self.window.viewer_session_bridge
        self.overlay_manager = self.window.embedded_viewer_overlay_manager
        self.assertIsNotNone(self.overlay_manager)
        self.workspace_id = self.window.workspace_manager.active_workspace_id()

    def _add_viewer_node(
        self,
        *,
        x: float = 160.0,
        y: float = 90.0,
        width: float = 360.0,
        height: float = 280.0,
    ) -> str:
        node_id = self.window.scene.add_node_from_type("tests.viewer_host_service_overlay", x=x, y=y)
        self.window.scene.resize_node(node_id, width, height)
        self.app.processEvents()
        return node_id

    def _add_dpf_viewer_node(
        self,
        *,
        x: float = 160.0,
        y: float = 90.0,
        width: float = 360.0,
        height: float = 280.0,
    ) -> str:
        node_id = self.window.scene.add_node_from_type(DPF_VIEWER_NODE_TYPE_ID, x=x, y=y)
        self.window.scene.resize_node(node_id, width, height)
        self.window.view.set_view_state(1.0, x + (width * 0.5), y + (height * 0.5))
        self.app.processEvents()
        return node_id

    def _content_fullscreen_viewer_viewport(self) -> QQuickItem:
        root_item = self.window.quick_widget.rootObject()
        self.assertIsInstance(root_item, QQuickItem)
        item = root_item.findChild(QObject, "contentFullscreenViewerViewport")
        self.assertIsInstance(item, QQuickItem)
        return item

    def _assert_rect_matches_item(self, widget: QWidget, item: QQuickItem, *, delta: float = 1.1) -> None:
        root_item = self.window.quick_widget.rootObject()
        self.assertIsInstance(root_item, QQuickItem)
        top_left = item.mapToItem(root_item, QPointF(0.0, 0.0))
        bottom_right = item.mapToItem(root_item, QPointF(item.width(), item.height()))
        expected = QRectF(top_left, bottom_right).normalized()
        geometry = widget.geometry()
        self.assertAlmostEqual(float(geometry.x()), float(expected.x()), delta=delta)
        self.assertAlmostEqual(float(geometry.y()), float(expected.y()), delta=delta)
        self.assertAlmostEqual(float(geometry.width()), float(expected.width()), delta=delta)
        self.assertAlmostEqual(float(geometry.height()), float(expected.height()), delta=delta)

    def _assert_rect_not_matches_item(self, widget: QWidget, item: QQuickItem, *, delta: float = 1.1) -> None:
        root_item = self.window.quick_widget.rootObject()
        self.assertIsInstance(root_item, QQuickItem)
        top_left = item.mapToItem(root_item, QPointF(0.0, 0.0))
        bottom_right = item.mapToItem(root_item, QPointF(item.width(), item.height()))
        expected = QRectF(top_left, bottom_right).normalized()
        geometry = widget.geometry()
        differs = (
            abs(float(geometry.x()) - float(expected.x())) > delta
            or abs(float(geometry.y()) - float(expected.y())) > delta
            or abs(float(geometry.width()) - float(expected.width())) > delta
            or abs(float(geometry.height()) - float(expected.height())) > delta
        )
        self.assertTrue(differs)

    def _emit_viewer_event(
        self,
        *,
        event_type: str,
        node_id: str,
        backend_id: str = "tests.viewer_backend",
        session_id: str = "",
        transport_revision: int = 1,
        keep_live: bool = False,
        live_policy: str = "focus_only",
        live_mode: str = "full",
        cache_state: str = "live_ready",
        live_open_status: str = "ready",
        transport: dict[str, Any] | None = None,
    ) -> None:
        resolved_session_id = session_id or f"session::{node_id}"
        resolved_transport = transport or {
            "kind": "tests_transport_bundle",
            "backend_id": backend_id,
            "manifest_path": f"C:/temp/{resolved_session_id}/manifest.json",
            "entry_path": f"C:/temp/{resolved_session_id}/entry.json",
        }
        playback = {
            "state": "paused",
            "step_index": 0,
        }
        self.window.execution_event.emit(
            {
                "type": event_type,
                "request_id": f"req::{event_type}::{node_id}::{transport_revision}",
                "workspace_id": self.workspace_id,
                "node_id": node_id,
                "session_id": resolved_session_id,
                "backend_id": backend_id,
                "data_refs": {
                    "dataset": {
                        "kind": "tests.dataset",
                        "handle_id": f"dataset::{node_id}::{transport_revision}",
                    }
                },
                "transport": resolved_transport,
                "transport_revision": transport_revision,
                "live_open_status": live_open_status,
                "live_open_blocker": {} if live_open_status == "ready" else {"code": "tests_blocked"},
                "camera_state": {"zoom": 1.0 + (transport_revision * 0.1)},
                "playback_state": playback,
                "summary": {
                    "cache_state": cache_state,
                    "backend_id": backend_id,
                    "transport_revision": transport_revision,
                    "live_open_status": live_open_status,
                    "camera_state": {"zoom": 1.0 + (transport_revision * 0.1)},
                },
                "options": {
                    "session_state": "open",
                    "cache_state": cache_state,
                    "backend_id": backend_id,
                    "transport_revision": transport_revision,
                    "live_open_status": live_open_status,
                    "live_policy": live_policy,
                    "keep_live": keep_live,
                    "playback_state": playback["state"],
                    "step_index": playback["step_index"],
                    "playback": playback,
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
                "summary": {
                    "cache_state": "proxy_ready",
                    "close_reason": "test_close",
                },
                "options": {
                    "cache_state": "proxy_ready",
                    "reason": "test_close",
                    "live_mode": "proxy",
                },
            }
        )
        self.app.processEvents()

    def test_shell_window_exposes_host_service_context_and_binds_registered_backend(self) -> None:
        context_service = self.window.quick_widget.rootContext().contextProperty("viewerHostService")
        self.assertIs(context_service, self.host_service)
        context_control = self.window.quick_widget.rootContext().contextProperty("viewerControlBridge")
        self.assertIs(context_control, self.window.viewer_control_bridge)

        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        container = self.overlay_manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertEqual(len(binder.bind_calls), 1)
        self.assertIsNotNone(widget)
        self.assertIsNotNone(container)
        self.assertTrue(widget.isVisible())
        self.assertTrue(container.isVisible())
        self.assertEqual(self.host_service.active_overlay_count, 1)
        self.assertEqual(self.host_service.last_error, "")
        self.assertEqual(binder.bind_calls[-1]["live_mode"], "full")
        self.assertEqual(binder.bind_calls[-1]["transport_revision"], 1)
        snapshots = self.overlay_manager.export_overlay_snapshots()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].owner, VIEWER_SESSION_OVERLAY_OWNER)
        self.assertEqual(snapshots[0].workspace_id, self.workspace_id)
        self.assertEqual(snapshots[0].node_id, node_id)
        self.assertGreater(snapshots[0].rect.width(), 0.0)
        self.assertGreater(snapshots[0].rect.height(), 0.0)

        self._close_viewer_session(node_id=node_id)

        self.assertEqual(len(binder.release_calls), 1)
        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertIsNone(self.overlay_manager.overlay_container(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.host_service.active_overlay_count, 0)
        self.assertEqual(binder.widgets[0].close_calls, 1)

    def test_refresh_failure_does_not_publish_embedded_overlay_ready(self) -> None:
        binder = _RecordingBinder(fail_refresh=True)
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self.host_service.set_embedded_interaction_active(node_id, True)

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        self.assertFalse(self.host_service.embedded_live_overlay_ready(node_id))
        self.assertEqual(self.host_service.active_overlay_count, 0)
        self.assertIsNone(
            self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        )
        self.assertEqual(self.host_service.last_error, "test refresh failure")
        self.assertEqual(binder.release_calls[-1]["reason"], "attach_refresh_error")

    def test_host_service_registers_builtin_dpf_binder(self) -> None:
        self.assertIsInstance(
            self.host_service.binder_registry.lookup(DpfViewerWidgetBinder.backend_id),
            DpfViewerWidgetBinder,
        )

    def test_binders_are_lazy_reused_and_custom_registration_survives_first_initialization(self) -> None:
        with patch.object(
            viewer_host_module,
            "create_live_viewer_widget_binders",
            return_value=(),
        ) as binder_factory:
            unopened = ViewerHostService()
            unopened.shutdown()
            self.assertIs(unopened.binder_registry, unopened._binder_registry)  # noqa: SLF001
            binder_factory.assert_not_called()

            service = ViewerHostService()
            custom_binder = _RecordingBinder()
            service.register_binder("tests.lazy.custom", custom_binder)
            binder_factory.assert_not_called()

            registry = service.binder_registry
            self.assertIs(registry.lookup("tests.lazy.custom"), custom_binder)
            self.assertIs(service.binder_registry, registry)
            binder_factory.assert_called_once_with(preferences_document=None)
            service.shutdown()

    def test_mesh_edge_option_change_rebinds_active_overlay(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_dpf_viewer_node()
        self.window.scene.select_node(node_id, False)
        self.app.processEvents()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        first_widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(first_widget)
        self.assertEqual(len(binder.bind_calls), 1)
        self.assertNotIn(DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY, binder.bind_calls[-1]["options"])

        self.assertTrue(
            self.bridge.sync_node_property_option(
                node_id,
                DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
                True,
                {"workspace_id": self.workspace_id},
            )
        )
        self.app.processEvents()

        self.assertEqual(len(binder.bind_calls), 2)
        self.assertIs(
            self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id),
            first_widget,
        )
        self.assertTrue(binder.bind_calls[-1]["options"][DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY])
        self.assertTrue(
            self.window.execution_client.update_calls[-1]["options"][
                DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY
            ]
        )

    def test_view_option_change_migrates_camera_state_across_rebind(self) -> None:
        binder = _ViewStateBinder(view_state={"zoom": 3.3})
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_dpf_viewer_node()
        self.window.scene.select_node(node_id, False)
        self.app.processEvents()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)
        self.assertEqual(len(binder.bind_calls), 1)

        self.assertTrue(
            self.bridge.sync_node_property_option(
                node_id,
                DPF_VIEWER_SHOW_MESH_EDGES_PROPERTY,
                True,
                {"workspace_id": self.workspace_id},
            )
        )
        self.app.processEvents()

        self.assertEqual(len(binder.bind_calls), 2)
        self.assertEqual(len(binder.capture_view_state_calls), 1)
        self.assertEqual(binder.restore_calls, [{"zoom": 3.3}])

    def test_transport_revision_change_drops_cached_camera_state(self) -> None:
        binder = _ViewStateBinder(view_state={"zoom": 3.3})
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_dpf_viewer_node()
        self.window.scene.select_node(node_id, False)
        self.app.processEvents()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)
        self.assertEqual(len(binder.bind_calls), 1)

        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            transport_revision=2,
        )

        self.assertEqual(len(binder.bind_calls), 2)
        self.assertEqual(binder.restore_calls, [])

    def test_render_stats_and_camera_slots_route_to_bound_widget(self) -> None:
        binder = _CameraStatsBinder(stats={"min": 1.5, "max": 4.5, "component": "Y"})
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_dpf_viewer_node()
        self.window.scene.select_node(node_id, False)
        self.app.processEvents()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)
        widget = binder.widgets[0]

        stats = self.host_service.viewer_render_stats(node_id)
        self.assertEqual(stats["min"], 1.5)
        self.assertEqual(stats["component"], "Y")

        self.assertTrue(self.host_service.apply_standard_view(node_id, "xy"))
        self.assertEqual(widget.view_calls, ["xy"])
        self.assertGreaterEqual(widget.render_calls, 1)

        self.assertTrue(self.host_service.reset_overlay_camera(node_id))
        self.assertEqual(widget.reset_camera_calls, 1)

        self.assertFalse(self.host_service.apply_standard_view(node_id, "bogus"))
        self.assertEqual(widget.view_calls, ["xy"])
        self.assertEqual(self.host_service.viewer_render_stats("missing-node"), {})
        self.assertFalse(self.host_service.reset_overlay_camera("missing-node"))

        entities = [
            {
                "layer_id": "primary",
                "source_fingerprint": "a" * 64,
                "entity_kind": "cad_face",
                "entity_id": "part:1/face:7",
            }
        ]
        self.assertTrue(self.host_service.activate_viewer_selection(node_id, entities))
        self.assertEqual(
            binder.activate_selection_calls[-1],
            {"widget": widget, "entities": entities},
        )
        self.assertTrue(self.host_service.set_viewer_selection_filter(node_id, "cad_face"))
        self.assertEqual(
            binder.selection_filter_calls[-1],
            {"widget": widget, "value": "cad_face"},
        )

    def test_cache_relevant_options_ignore_probe_but_keep_visual_keys(self) -> None:
        filtered = _cache_relevant_options(
            {"hover_probe": True, "colormap": "jet", "show_minmax_markers": True, "step_index": 3}
        )
        self.assertNotIn("hover_probe", filtered)
        self.assertNotIn("step_index", filtered)
        self.assertEqual(filtered["colormap"], "jet")
        self.assertTrue(filtered["show_minmax_markers"])

    def test_camera_snapshot_and_apply_route_through_binder(self) -> None:
        binder = _ViewStateBinder(
            view_state={"zoom": 2.0},
            captured_camera_state={"zoom": 9.0},
        )
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_dpf_viewer_node()
        self.window.scene.select_node(node_id, False)
        self.app.processEvents()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        snapshot = self.host_service.camera_state_snapshot(node_id)
        self.assertEqual(snapshot, {"zoom": 9.0})

        self.assertTrue(self.host_service.apply_overlay_camera_state(node_id, {"zoom": 5.5}))
        self.assertEqual(binder.restore_calls[-1], {"zoom": 5.5})
        self.assertFalse(self.host_service.apply_overlay_camera_state("missing-node", {"zoom": 1.0}))

    def test_export_viewer_screenshot_saves_capture_and_handles_cancel(self) -> None:
        import tempfile
        from pathlib import Path

        capture = QImage(8, 8, QImage.Format.Format_ARGB32)
        capture.fill(0xFF00FF00)
        binder = _RecordingBinder(captured_preview_image=capture)
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_dpf_viewer_node()
        self.window.scene.select_node(node_id, False)
        self.app.processEvents()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        presenter = self.window.shell_host_presenter
        original_picker = presenter.save_file_dialog
        with tempfile.TemporaryDirectory() as temp_dir:
            target = str(Path(temp_dir) / "viewer_shot.png")
            presenter.save_file_dialog = lambda **kwargs: target  # type: ignore[method-assign]
            try:
                result = self.host_service.export_viewer_screenshot(node_id)
            finally:
                presenter.save_file_dialog = original_picker  # type: ignore[method-assign]
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["path"], target)
            self.assertTrue(Path(target).is_file())

        presenter.save_file_dialog = lambda **kwargs: ""  # type: ignore[method-assign]
        try:
            cancelled = self.host_service.export_viewer_screenshot(node_id)
        finally:
            presenter.save_file_dialog = original_picker  # type: ignore[method-assign]
        self.assertFalse(cancelled["ok"])
        self.assertEqual(cancelled["error"], "")

        self.assertTrue(self.host_service.copy_viewer_screenshot_to_clipboard(node_id))
        self.assertFalse(self.app.clipboard().image().isNull())

        missing = self.host_service.export_viewer_screenshot("missing-node")
        self.assertFalse(missing["ok"])
        self.assertTrue(missing["error"])

    def test_rebuild_addon_binders_removes_disabled_dpf_binder_and_preserves_custom_binders(self) -> None:
        custom_binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend.custom", custom_binder)
        disabled_preferences = set_addon_state(
            default_app_preferences_document(),
            ANSYS_DPF_ADDON_ID,
            enabled=False,
            pending_restart=False,
        )

        self.host_service.rebuild_addon_binders(preferences_document=disabled_preferences)

        self.assertIsNone(self.host_service.binder_registry.lookup(DpfViewerWidgetBinder.backend_id))
        self.assertIs(
            self.host_service.binder_registry.lookup("tests.viewer_backend.custom"),
            custom_binder,
        )

        reenabled_preferences = set_addon_state(
            disabled_preferences,
            ANSYS_DPF_ADDON_ID,
            enabled=True,
            pending_restart=False,
        )
        self.host_service.rebuild_addon_binders(preferences_document=reenabled_preferences)

        self.assertIsInstance(
            self.host_service.binder_registry.lookup(DpfViewerWidgetBinder.backend_id),
            DpfViewerWidgetBinder,
        )
        self.assertIs(
            self.host_service.binder_registry.lookup("tests.viewer_backend.custom"),
            custom_binder,
        )

    def test_focus_only_projection_keeps_one_bound_overlay_until_keep_live_enabled(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        first_node_id = self._add_viewer_node(x=120.0, y=80.0)
        second_node_id = self._add_viewer_node(x=240.0, y=200.0)

        self.window.scene.select_node(first_node_id, False)
        self.app.processEvents()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=first_node_id)
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=second_node_id)

        self.assertIsNotNone(self.overlay_manager.overlay_widget(first_node_id, workspace_id=self.workspace_id))
        self.assertIsNone(self.overlay_manager.overlay_widget(second_node_id, workspace_id=self.workspace_id))

        self.window.scene.select_node(second_node_id, False)
        # The surface defers set_embedded_interaction_active via Qt.callLater
        # (it re-emits sessions_changed, so it must run outside binding
        # updates), and the live-exit demotion additionally waits for the
        # swapped proxy preview frame (or its timeout) before the overlay
        # hides; settle until the handoff completes.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            self.app.processEvents()
            if self.overlay_manager.overlay_widget(first_node_id, workspace_id=self.workspace_id) is None:
                break
            time.sleep(0.01)
        self.assertIsNone(self.overlay_manager.overlay_widget(first_node_id, workspace_id=self.workspace_id))
        self.assertIsNotNone(self.overlay_manager.overlay_widget(second_node_id, workspace_id=self.workspace_id))
        recent_updates = self.window.execution_client.update_calls[-2:]
        self.assertEqual({call["node_id"] for call in recent_updates}, {first_node_id, second_node_id})
        self.assertEqual({call["options"]["live_mode"] for call in recent_updates}, {"full", "proxy"})

        self._emit_viewer_event(
            event_type="viewer_session_updated",
            node_id=first_node_id,
            keep_live=True,
            live_policy="focus_only",
            live_mode="full",
        )

        self.assertIsNotNone(self.overlay_manager.overlay_widget(first_node_id, workspace_id=self.workspace_id))
        self.assertIsNotNone(self.overlay_manager.overlay_widget(second_node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.host_service.active_overlay_count, 2)

    def test_transport_revision_rebinds_and_unknown_backend_unbinds_with_error(self) -> None:
        binder = _RecordingBinder(reuse_current_widget=False)
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            transport_revision=1,
        )
        first_widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(first_widget)
        self.assertEqual(len(binder.bind_calls), 1)

        self._emit_viewer_event(
            event_type="viewer_session_updated",
            node_id=node_id,
            transport_revision=2,
        )
        second_widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(second_widget)
        self.assertEqual(len(binder.bind_calls), 2)
        self.assertIsNot(first_widget, second_widget)
        self.assertEqual(binder.bind_calls[-1]["transport_revision"], 2)
        self.assertEqual(first_widget.close_calls, 1)

        self._emit_viewer_event(
            event_type="viewer_session_updated",
            node_id=node_id,
            backend_id="tests.unknown_backend",
            transport_revision=3,
        )
        self.assertEqual(len(binder.release_calls), 1)
        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertIn("tests.unknown_backend", self.host_service.last_error)
        self.assertEqual(self.host_service.active_overlay_count, 0)

    def test_missing_transport_no_bind_cleans_up_existing_overlay_widget(self) -> None:
        binder = _RecordingBinder(
            no_bind_predicate=lambda request: not request.transport.get("manifest_path") or not request.transport.get("entry_path")
        )
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            transport_revision=1,
        )
        initial_widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(initial_widget)
        self.assertEqual(self.host_service.active_overlay_count, 1)

        self._emit_viewer_event(
            event_type="viewer_session_updated",
            node_id=node_id,
            transport_revision=2,
            transport={
                "kind": "tests_transport_bundle",
                "backend_id": "tests.viewer_backend",
                "manifest_path": "",
                "entry_path": "",
            },
        )

        self.assertEqual(len(binder.release_calls), 1)
        self.assertEqual(binder.release_calls[-1]["reason"], "no_bind")
        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.host_service.active_overlay_count, 0)
        self.assertEqual(self.host_service.last_error, "")

    def test_suspend_sync_keeps_preflight_reset_overlay_released_until_resume(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            transport_revision=1,
        )
        self.assertIsNotNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.host_service.active_overlay_count, 1)

        self.host_service.suspend_sync(reason="workspace_rerun_preflight")
        self.host_service.reset(reason="workspace_rerun_preflight")
        self.app.processEvents()

        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.host_service.active_overlay_count, 0)

        self.bridge.project_workspace_run_required(
            self.workspace_id,
            reason="workspace_rerun",
            run_id="run_live",
        )
        self.app.processEvents()

        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.host_service.active_overlay_count, 0)

        self.host_service.resume_sync()
        self.app.processEvents()

        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.host_service.active_overlay_count, 0)
        self.assertEqual(len(binder.bind_calls), 1)
        self.assertEqual(len(binder.release_calls), 1)
        self.assertEqual(binder.release_calls[-1]["reason"], "workspace_rerun_preflight")

    def test_capture_overlay_camera_state_delegates_to_bound_binder(self) -> None:
        binder = _RecordingBinder(
            captured_camera_state={
                "position": [3.0, 4.0, 5.0],
                "focal_point": [0.0, 0.0, 0.0],
                "viewup": [0.0, 1.0, 0.0],
            }
        )
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        captured = self.host_service.capture_overlay_camera_state(
            node_id,
            workspace_id=self.workspace_id,
        )

        self.assertEqual(captured, binder.captured_camera_state)
        self.assertEqual(len(binder.capture_calls), 1)
        self.assertIs(
            binder.capture_calls[0],
            self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id),
        )

    def test_capture_overlay_preview_image_prefers_binder_capture_hook(self) -> None:
        preview_image = QImage(20, 12, QImage.Format.Format_ARGB32)
        preview_image.fill(0xFF67D487)
        binder = _RecordingBinder(captured_preview_image=preview_image)
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        captured = self.host_service.capture_overlay_preview_image(
            node_id,
            workspace_id=self.workspace_id,
        )

        self.assertFalse(captured.isNull())
        container = self.overlay_manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(container)
        self.assertEqual(captured.size(), container.size())
        self.assertEqual(len(binder.capture_preview_calls), 1)
        self.assertIs(
            binder.capture_preview_calls[0],
            self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id),
        )

    def test_embedded_live_exit_captures_in_memory_viewer_preview_cache(self) -> None:
        preview_image = QImage(20, 12, QImage.Format.Format_ARGB32)
        preview_image.fill(QColor("#67D487"))
        binder = _RecordingBinder(captured_preview_image=preview_image)
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)
        self.host_service.set_embedded_interaction_active(node_id, True)
        self.app.processEvents()
        live_widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        container = self.overlay_manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(live_widget)
        self.assertIsNotNone(container)
        self.assertTrue(self.host_service.embedded_live_overlay_ready(node_id))

        self.host_service.set_embedded_interaction_active(node_id, False)
        self.app.processEvents()

        provider = self.window._viewer_preview_cache_provider
        source = self.host_service.cached_preview_source(node_id)
        self.assertTrue(source.startswith("image://viewer-preview-cache/"))
        self.assertEqual(self.host_service.preview_cache_revision, 1)
        self.assertEqual(binder.capture_preview_calls[-1], live_widget)
        cached, cached_size = provider.requestImage(source.split("image://viewer-preview-cache/", 1)[1], QSize())
        self.assertEqual(cached_size, container.size())
        self.assertEqual(cached.pixelColor(0, 0), QColor("#67D487"))

    def _open_live_embedded_viewer(self) -> str:
        preview_image = QImage(20, 12, QImage.Format.Format_ARGB32)
        preview_image.fill(QColor("#2F89FF"))
        binder = _RecordingBinder(captured_preview_image=preview_image)
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)
        self.host_service.set_embedded_interaction_active(node_id, True)
        self.app.processEvents()
        self.assertTrue(self.host_service.embedded_live_overlay_ready(node_id))
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "full")
        return node_id

    def test_embedded_live_exit_defers_demotion_until_preview_swap_renders(self) -> None:
        node_id = self._open_live_embedded_viewer()
        key = (self.workspace_id, node_id)

        with patch.object(viewer_host_module, "_EMBEDDED_EXIT_DEMOTION_TIMEOUT_MS", 5000):
            self.host_service.set_embedded_interaction_active(node_id, False)
            self.app.processEvents()
            self.app.processEvents()

            # The bridge demotion (and with it the overlay teardown) waits
            # for the swapped proxy frame instead of racing the reveal.
            self.assertIn(key, self.host_service._pending_embedded_exit_demotions)
            self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "full")
            self.assertIsNotNone(
                self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
            )

            source = self.host_service.cached_preview_source(node_id)
            self.assertTrue(source.startswith("image://viewer-preview-cache/"))
            self.host_service.notify_cached_preview_swapped(node_id, source)
            pending = self.host_service._pending_embedded_exit_demotions.get(key)
            if pending is not None:
                self.assertTrue(pending.armed)
                self.host_service._on_exit_render_gate_frame()
            self.app.processEvents()
            self.app.processEvents()

        self.assertNotIn(key, self.host_service._pending_embedded_exit_demotions)
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "proxy")
        self.assertIsNone(self.host_service._exit_render_gate_window)

    def test_embedded_live_exit_demotion_times_out_without_swap_confirmation(self) -> None:
        node_id = self._open_live_embedded_viewer()
        key = (self.workspace_id, node_id)

        with patch.object(viewer_host_module, "_EMBEDDED_EXIT_DEMOTION_TIMEOUT_MS", 20):
            self.host_service.set_embedded_interaction_active(node_id, False)
            self.assertIn(key, self.host_service._pending_embedded_exit_demotions)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline:
                self.app.processEvents()
                if self.bridge.session_state(node_id)["options"]["live_mode"] == "proxy":
                    break
                time.sleep(0.01)

        self.assertNotIn(key, self.host_service._pending_embedded_exit_demotions)
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "proxy")

    def test_embedded_reactivation_cancels_pending_exit_demotion(self) -> None:
        node_id = self._open_live_embedded_viewer()
        key = (self.workspace_id, node_id)

        with patch.object(viewer_host_module, "_EMBEDDED_EXIT_DEMOTION_TIMEOUT_MS", 20):
            self.host_service.set_embedded_interaction_active(node_id, False)
            self.assertIn(key, self.host_service._pending_embedded_exit_demotions)
            self.host_service.set_embedded_interaction_active(node_id, True)
            self.assertNotIn(key, self.host_service._pending_embedded_exit_demotions)

            # Give the cancelled timeout a chance to fire; the serial guard
            # must keep it from demoting the re-entered session.
            deadline = time.monotonic() + 0.3
            while time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)

        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "full")
        self.assertTrue(self.host_service.embedded_live_overlay_ready(node_id))

    def test_snapshot_from_projected_state_prefers_projected_camera_state_during_pending_transition(self) -> None:
        snapshot = self.host_service._snapshot_from_projected_state(
            {
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "session_id": "session::node_viewer",
                "phase": "open",
                "cache_state": "live_ready",
                "backend_id": "tests.viewer_backend",
                "transport_revision": 1,
                "live_mode": "full",
                "live_open_status": "ready",
                "live_open_blocker": {},
                "camera_state": {"position": [9.0, 8.0, 7.0], "view_angle": 24.0},
                "playback": {"state": "paused", "step_index": 0},
                "summary": {"cache_state": "live_ready"},
                "options": {
                    "playback_state": "paused",
                    "step_index": 0,
                },
                "transport": {"kind": "tests_transport_bundle", "backend_id": "tests.viewer_backend"},
                "data_refs": {},
            }
        )

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.camera_state, {"position": [9.0, 8.0, 7.0], "view_angle": 24.0})

    def test_first_refocus_rebind_uses_projected_camera_before_authoritative_full_event(self) -> None:
        binder = _RecordingBinder(
            captured_camera_state={
                "position": [11.0, 12.0, 13.0],
                "focal_point": [1.0, 2.0, 3.0],
                "viewup": [0.0, 1.0, 0.0],
                "view_angle": 28.0,
            }
        )
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        session_id = ""
        stale_camera = {"position": [0.0, 0.0, 5.0], "view_angle": 15.0}

        def emit_event(*, event_type: str, request_id: str, live_mode: str, camera_state: dict[str, Any]) -> None:
            self.window.execution_event.emit(
                {
                    "type": event_type,
                    "request_id": request_id,
                    "workspace_id": self.workspace_id,
                    "node_id": node_id,
                    "session_id": session_id,
                    "backend_id": "tests.viewer_backend",
                    "data_refs": {
                        "dataset": {
                            "kind": "tests.dataset",
                            "handle_id": f"dataset::{node_id}",
                        }
                    },
                    "transport": {
                        "kind": "tests_transport_bundle",
                        "backend_id": "tests.viewer_backend",
                        "manifest_path": f"C:/temp/{session_id}/manifest.json",
                        "entry_path": f"C:/temp/{session_id}/entry.json",
                    },
                    "transport_revision": 1,
                    "live_open_status": "ready",
                    "live_open_blocker": {},
                    "camera_state": dict(camera_state),
                    "playback_state": {
                        "state": "paused",
                        "step_index": 0,
                    },
                    "summary": {
                        "cache_state": "live_ready",
                        "backend_id": "tests.viewer_backend",
                        "transport_revision": 1,
                        "live_open_status": "ready",
                        "camera_state": dict(camera_state),
                    },
                    "options": {
                        "session_state": "open",
                        "cache_state": "live_ready",
                        "backend_id": "tests.viewer_backend",
                        "transport_revision": 1,
                        "live_open_status": "ready",
                        "live_policy": "focus_only",
                        "keep_live": False,
                        "playback_state": "paused",
                        "step_index": 0,
                        "playback": {
                            "state": "paused",
                            "step_index": 0,
                        },
                        "live_mode": live_mode,
                    },
                }
            )
            self.app.processEvents()

        self.window.scene.select_node(node_id, False)
        self.app.processEvents()
        opened_session_id = self.bridge.open(
            node_id,
            {
                "data_refs": {"fields": f"fields::{node_id}"},
                "backend_id": "tests.viewer_backend",
            },
        )
        self.assertTrue(opened_session_id.startswith("viewer_session_"))
        session_id = opened_session_id

        open_call = self.window.execution_client.open_calls[-1]
        emit_event(
            event_type="viewer_data_materialized",
            request_id=open_call["request_id"],
            live_mode="full",
            camera_state=stale_camera,
        )
        self.assertEqual(binder.bind_calls[-1]["camera_state"], stale_camera)
        self.assertIsNotNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))

        self.assertTrue(self.bridge.clear_viewer_focus())
        self.app.processEvents()
        proxy_update = self.window.execution_client.update_calls[-1]
        self.assertEqual(proxy_update["options"]["live_mode"], "proxy")
        self.assertEqual(proxy_update["camera_state"], binder.captured_camera_state)
        self.assertEqual(len(binder.release_calls), 1)
        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))

        emit_event(
            event_type="viewer_session_updated",
            request_id=proxy_update["request_id"],
            live_mode="proxy",
            camera_state=stale_camera,
        )
        self.assertEqual(self.bridge.session_state(node_id)["camera_state"], binder.captured_camera_state)

        self.assertTrue(self.bridge.focus_session(node_id))
        self.app.processEvents()
        refocus_update = self.window.execution_client.update_calls[-1]
        self.assertEqual(refocus_update["options"]["live_mode"], "full")
        self.assertEqual(refocus_update["camera_state"], binder.captured_camera_state)

        self.assertIsNotNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(binder.bind_calls[-1]["live_mode"], "full")
        self.assertEqual(binder.bind_calls[-1]["camera_state"], binder.captured_camera_state)

    def test_content_fullscreen_bridge_retargets_existing_live_widget_to_shell_viewport_and_restores(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_dpf_viewer_node()

        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        container = self.overlay_manager.overlay_container(node_id, workspace_id=self.workspace_id)
        self.assertIsNotNone(widget)
        self.assertIsNotNone(container)
        self.assertEqual(len(binder.bind_calls), 1)
        node_geometry = container.geometry()

        self.assertTrue(self.window.content_fullscreen_bridge.request_open_node(node_id))
        self.app.processEvents()
        self.app.processEvents()

        fullscreen_viewport = self._content_fullscreen_viewer_viewport()
        self.assertTrue(fullscreen_viewport.isVisible())
        self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        self.assertEqual(len(binder.bind_calls), 1)
        self._assert_rect_matches_item(container, fullscreen_viewport)
        self.assertGreater(container.geometry().width(), node_geometry.width())

        self.window.content_fullscreen_bridge.request_close()
        self.app.processEvents()
        self.app.processEvents()

        self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        self.assertEqual(len(binder.bind_calls), 1)
        self.assertEqual(len(binder.release_calls), 0)
        self._assert_rect_not_matches_item(container, fullscreen_viewport)

    def test_detached_viewer_reuses_widget_and_fullscreen_temporarily_takes_precedence(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        session_id = f"session::{node_id}"
        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            session_id=session_id,
            live_mode="proxy",
            cache_state="proxy_ready",
            live_open_status="blocked",
        )

        self.assertEqual(self.host_service.detached_viewer_count, 0)
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()
        self.assertEqual(self.bridge._focused_viewer_node_id(self.workspace_id), node_id)
        self.assertEqual(self.host_service.detached_viewer_count, 0)
        self.assertEqual(self.host_service._pending_detached_sessions[(self.workspace_id, node_id)], session_id)

        self._emit_viewer_event(
            event_type="viewer_session_updated",
            node_id=node_id,
            session_id=session_id,
            live_mode="full",
            cache_state="live_ready",
            live_open_status="ready",
            keep_live=True,
        )

        key = (self.workspace_id, node_id)
        detached = self.host_service._detached_windows[key]
        widget = detached.widget
        self.assertIsInstance(widget, QWidget)
        self.assertEqual(self.host_service._pending_detached_sessions, {})
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.assertIs(self.host_service._detached_windows[key], detached)
        self.assertEqual(self.host_service.detached_viewer_count, 1)
        self.assertIs(detached.widget, widget)
        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertTrue(self.host_service.detached_viewer_active(node_id))
        self.assertEqual(len(binder.bind_calls), 1)
        self.assertTrue(binder.bind_calls[0]["container_visible"])
        self.assertTrue(binder.bind_calls[0]["window_visible"])
        self.assertTrue(binder.bind_calls[0]["window_has_handle"])
        cycle_calls: list[tuple[str, int]] = []
        control = self.window.viewer_control_bridge
        original_cycle = control.cycle_viewer_camera_bookmark
        control.cycle_viewer_camera_bookmark = (  # type: ignore[method-assign]
            lambda cycle_node_id, delta: cycle_calls.append((cycle_node_id, delta)) or True
        )
        try:
            for shortcut_key in (Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                event = QKeyEvent(QEvent.Type.KeyPress, shortcut_key, Qt.KeyboardModifier.NoModifier)
                self.assertTrue(self.host_service._fullscreen_shortcut_filter.eventFilter(widget, event))
        finally:
            control.cycle_viewer_camera_bookmark = original_cycle  # type: ignore[method-assign]
        self.assertEqual(cycle_calls, [(node_id, -1), (node_id, 1)])

        self.assertTrue(self.window.content_fullscreen_bridge.request_open_node(node_id))
        self.app.processEvents()
        self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        self.assertIsNone(detached.widget)
        self.assertFalse(detached.isVisible())

        self.window.content_fullscreen_bridge.request_close()
        self.app.processEvents()
        self.assertIs(detached.widget, widget)
        self.assertTrue(detached.isVisible())
        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))

        detached.close()
        self.app.processEvents()
        self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        self.assertFalse(self.host_service.detached_viewer_active(node_id))

        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()
        self.assertIs(self.host_service._detached_windows[key].widget, widget)
        self.assertTrue(self.host_service.close_detached_viewer(node_id))
        self.app.processEvents()
        self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        self.assertEqual(len(binder.release_calls), 0)
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()

        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            session_id=f"replacement::{node_id}",
            transport_revision=2,
            keep_live=True,
        )

        self.assertFalse(self.host_service.detached_viewer_active(node_id))
        self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        self.assertEqual(binder.bind_calls[-1]["session_id"], f"replacement::{node_id}")
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()
        self.assertIn(widget, self.host_service._shortcut_filtered_widgets)

        self.host_service.reset(reason="test_reset")
        self.assertEqual(self.host_service._shortcut_filtered_widgets, set())
        self.assertEqual(self.host_service.detached_viewer_count, 0)
        self.assertEqual(self.host_service._pending_detached_sessions, {})

    def test_detached_viewer_holds_live_session_across_focus_loss(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()
        key = (self.workspace_id, node_id)
        self.assertIn(key, self.host_service._detached_windows)
        detached = self.host_service._detached_windows[key]
        widget = detached.widget
        self.assertIsInstance(widget, QWidget)
        self.assertTrue(self.host_service.detached_viewer_active(node_id))

        # Canvas gestures clear viewer focus; the detached presentation must
        # keep the session live instead of collapsing to a proxy and closing.
        self.assertTrue(self.bridge.clear_viewer_focus())
        self.app.processEvents()
        self.app.processEvents()
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "full")
        self.assertIs(self.host_service._detached_windows.get(key), detached)
        self.assertIs(detached.widget, widget)
        self.assertTrue(self.host_service.detached_viewer_active(node_id))

        # The inline surface deactivating embedded interaction must not demote it either.
        self.host_service.set_embedded_interaction_active(node_id, False)
        self.app.processEvents()
        self.app.processEvents()
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "full")
        self.assertIs(self.host_service._detached_windows.get(key), detached)

        # Docking releases the hold, so the focus-only policy demotes normally again.
        self.assertTrue(self.host_service.close_detached_viewer(node_id))
        self.app.processEvents()
        self.assertFalse(self.host_service.detached_viewer_active(node_id))
        self.assertNotIn(key, self.bridge._viewer_presentation_holds)
        self.assertTrue(self.bridge.clear_viewer_focus())
        self.app.processEvents()
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "proxy")

    def test_pending_detached_viewer_reports_active_and_releases_hold_on_close(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        session_id = f"session::{node_id}"
        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            session_id=session_id,
            live_mode="proxy",
            cache_state="proxy_ready",
            live_open_status="blocked",
        )

        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        key = (self.workspace_id, node_id)
        self.assertIn(key, self.host_service._pending_detached_sessions)
        self.assertTrue(self.host_service.detached_viewer_active(node_id))
        self.assertIn(key, self.bridge._viewer_presentation_holds)

        # Closing while the detach is still pending abandons it and releases the hold.
        self.assertTrue(self.host_service.close_detached_viewer(node_id))
        self.assertFalse(self.host_service.detached_viewer_active(node_id))
        self.assertNotIn(key, self.host_service._pending_detached_sessions)
        self.assertNotIn(key, self.bridge._viewer_presentation_holds)

    def test_detached_reparent_lifecycle_prepares_and_refreshes_the_same_widget(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            keep_live=True,
        )

        key = (self.workspace_id, node_id)
        widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        inline_container = self.overlay_manager.overlay_container(
            node_id,
            workspace_id=self.workspace_id,
        )
        self.assertIsInstance(widget, QWidget)
        self.assertIs(widget.parent(), inline_container)
        parent_changes = _ParentChangeRecorder(widget)
        widget.installEventFilter(parent_changes)

        binder.lifecycle_calls.clear()
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()
        detached = self.host_service._detached_windows[key]
        self.assertIs(detached.widget, widget)
        self.assertIsNotNone(detached.selection_controls)
        selection_root = detached.selection_controls.rootObject()
        self.assertIsNotNone(selection_root)
        self.assertEqual(selection_root.objectName(), "viewerSelectionControls")
        self.assertEqual(selection_root.property("nodeId"), node_id)
        self.assertTrue(selection_root.property("detachedPresentation"))
        detached_layout = detached.layout()
        self.assertEqual(
            detached_layout.getItemPosition(detached_layout.indexOf(detached.selection_controls)),
            (0, 0, 1, 2),
        )
        self.assertEqual(
            detached_layout.getItemPosition(detached_layout.indexOf(detached.container)),
            (1, 0, 1, 1),
        )
        self.assertEqual(
            detached_layout.getItemPosition(detached_layout.indexOf(detached.quick_controls)),
            (2, 0, 1, 2),
        )
        self.assertEqual(
            [call["kind"] for call in binder.lifecycle_calls],
            ["prepare", "refresh"],
        )
        self.assertIs(binder.lifecycle_calls[0]["parent"], inline_container)
        self.assertIs(binder.lifecycle_calls[1]["parent"], detached.container)
        self.assertTrue(binder.lifecycle_calls[1]["window_visible"])
        detached_parent_change = next(
            record for record in parent_changes.records if record["parent"] is detached.container
        )
        self.assertTrue(detached_parent_change["parent_visible"])
        self.assertTrue(detached_parent_change["window_visible"])
        self.assertTrue(detached_parent_change["parent_has_handle"])
        self.assertTrue(detached_parent_change["window_has_handle"])

        binder.lifecycle_calls.clear()
        self.assertTrue(self.window.content_fullscreen_bridge.request_open_node(node_id))
        self.app.processEvents()
        self.app.processEvents()
        self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        fullscreen_container = self.overlay_manager.overlay_container(
            node_id,
            workspace_id=self.workspace_id,
        )
        self.assertEqual(
            [call["kind"] for call in binder.lifecycle_calls],
            ["prepare", "refresh"],
        )
        self.assertIs(binder.lifecycle_calls[0]["parent"], detached.container)
        self.assertIs(binder.lifecycle_calls[-1]["parent"], fullscreen_container)

        binder.lifecycle_calls.clear()
        self.window.content_fullscreen_bridge.request_close()
        self.app.processEvents()
        self.app.processEvents()
        self.assertIs(detached.widget, widget)
        self.assertEqual(
            [call["kind"] for call in binder.lifecycle_calls],
            ["prepare", "refresh"],
        )
        self.assertIs(binder.lifecycle_calls[0]["parent"], fullscreen_container)
        self.assertIs(binder.lifecycle_calls[1]["parent"], detached.container)

        binder.lifecycle_calls.clear()
        self.assertTrue(self.host_service.close_detached_viewer(node_id))
        self.app.processEvents()
        self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
        self.assertEqual(
            [call["kind"] for call in binder.lifecycle_calls],
            ["prepare", "refresh"],
        )
        self.assertIs(
            binder.lifecycle_calls[-1]["parent"],
            self.overlay_manager.overlay_container(node_id, workspace_id=self.workspace_id),
        )

        for close_from_window in (False, True):
            binder.lifecycle_calls.clear()
            self.assertTrue(self.host_service.open_detached_viewer(node_id))
            self.app.processEvents()
            active_window = self.host_service._detached_windows[key]
            self.assertIs(active_window.widget, widget)
            self.assertEqual(
                [call["kind"] for call in binder.lifecycle_calls],
                ["prepare", "refresh"],
            )

            binder.lifecycle_calls.clear()
            if close_from_window:
                active_window.close()
            else:
                self.assertTrue(self.host_service.close_detached_viewer(node_id))
            self.app.processEvents()
            self.assertIs(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id), widget)
            self.assertEqual(
                [call["kind"] for call in binder.lifecycle_calls],
                ["prepare", "refresh"],
            )

        binder.lifecycle_calls.clear()
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()
        binder.lifecycle_calls.clear()
        self.host_service.reset(reason="test_reset")
        self.assertEqual(
            [call["kind"] for call in binder.lifecycle_calls],
            ["prepare", "release"],
        )
        self.assertIs(binder.lifecycle_calls[0]["parent"], binder.lifecycle_calls[1]["parent"])
        self.assertEqual(self.host_service.detached_viewer_count, 0)

    def test_detached_side_panel_follows_qml_implicit_width(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            keep_live=True,
        )

        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()
        window = self.host_service._detached_windows[(self.workspace_id, node_id)]
        panel = window.side_panel
        self.assertIsNotNone(panel)
        root = panel.rootObject()
        self.assertIsNotNone(root)

        self.assertTrue(root.property("panelCollapsed"))
        self.assertEqual(panel.minimumWidth(), 28)
        self.assertEqual(panel.maximumWidth(), 28)

        root.setProperty("panelCollapsed", False)
        self.app.processEvents()
        self.assertEqual(panel.minimumWidth(), 288)
        self.assertEqual(panel.maximumWidth(), 288)

        root.setProperty("panelCollapsed", True)
        self.app.processEvents()
        self.assertEqual(panel.minimumWidth(), 28)
        self.assertEqual(panel.maximumWidth(), 28)

    def test_detached_close_is_aborted_when_reparent_prepare_fails(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            keep_live=True,
        )
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()

        key = (self.workspace_id, node_id)
        window = self.host_service._detached_windows[key]
        widget = window.widget
        self.assertIsNotNone(widget)
        binder.fail_prepare = True

        self.assertFalse(self.host_service.close_detached_viewer(node_id))
        self.assertIs(self.host_service._detached_windows[key], window)
        self.assertIs(window.widget, widget)
        self.assertIs(widget.parent(), window.container)

        window.close()
        self.app.processEvents()
        self.assertIs(self.host_service._detached_windows[key], window)
        self.assertIs(window.widget, widget)

        binder.fail_prepare = False
        self.assertTrue(self.host_service.close_detached_viewer(node_id))
        self.app.processEvents()
        self.assertNotIn(key, self.host_service._detached_windows)

    def test_detached_redock_refresh_failure_does_not_publish_inline_ready(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self.host_service.set_embedded_interaction_active(node_id, True)
        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            keep_live=True,
        )
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()

        binder.fail_refresh = True
        self.assertTrue(self.host_service.close_detached_viewer(node_id))
        self.app.processEvents()

        self.assertFalse(self.host_service.embedded_live_overlay_ready(node_id))
        self.assertEqual(self.host_service.active_overlay_count, 0)
        self.assertIsNone(
            self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        )
        self.assertEqual(self.host_service.last_error, "test refresh failure")
        self.assertEqual(binder.release_calls[-1]["reason"], "attach_refresh_error")

    def test_pending_first_attach_is_not_published_until_refresh_completes(self) -> None:
        binder = _RecordingBinder(pending_refreshes=1)
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self.host_service.set_embedded_interaction_active(node_id, True)

        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            keep_live=True,
        )

        key = (self.workspace_id, node_id)
        widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        self.assertIsInstance(widget, QWidget)
        self.assertNotIn(key, self.host_service._bound_overlays)
        self.assertEqual(self.host_service.active_overlay_count, 0)
        self.assertFalse(self.host_service.embedded_live_overlay_ready(node_id))
        self.assertEqual(self.host_service.last_error, "")
        self.assertEqual(binder.release_calls, [])

        self.host_service._schedule_sync()
        self.app.processEvents()

        self.assertIn(key, self.host_service._bound_overlays)
        self.assertEqual(self.host_service.active_overlay_count, 1)
        self.assertTrue(self.host_service.embedded_live_overlay_ready(node_id))
        self.assertEqual(self.host_service.last_error, "")

    def test_fullscreen_detach_retargets_pending_first_attach_without_closing_widget(self) -> None:
        binder = _RecordingBinder(pending_refreshes=1)
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self.assertTrue(self.window.content_fullscreen_bridge.request_open_node(node_id))
        self.app.processEvents()

        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            keep_live=True,
        )

        key = (self.workspace_id, node_id)
        widget = self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id)
        self.assertIsInstance(widget, _FakeBinderWidget)
        self.assertNotIn(key, self.host_service._bound_overlays)

        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()

        detached = self.host_service._detached_windows[key]
        self.assertIs(detached.widget, widget)
        self.assertIs(widget.parent(), detached.container)
        self.assertEqual(widget.close_calls, 0)

    def test_detached_retarget_refresh_failure_does_not_advance_binding(self) -> None:
        binder = _RecordingBinder()
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()
        self.host_service.set_embedded_interaction_active(node_id, True)
        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            keep_live=True,
        )

        binder.fail_refresh = True
        self.assertTrue(self.host_service.open_detached_viewer(node_id))
        self.app.processEvents()

        key = (self.workspace_id, node_id)
        self.assertNotIn(key, self.host_service._bound_overlays)
        self.assertIsNone(self.host_service._detached_windows[key].widget)
        self.assertFalse(self.host_service.embedded_live_overlay_ready(node_id))
        self.assertEqual(self.host_service.last_error, "test refresh failure")
        self.assertEqual(binder.release_calls[-1]["reason"], "attach_refresh_error")

    def test_window_deactivate_blurs_live_viewer_and_captures_camera(self) -> None:
        preview_image = QImage(24, 16, QImage.Format.Format_ARGB32)
        preview_image.fill(0xFF5DA9FF)
        binder = _RecordingBinder(
            captured_camera_state={
                "position": [7.0, 8.0, 9.0],
                "focal_point": [0.0, 0.0, 0.0],
                "viewup": [0.0, 1.0, 0.0],
                "view_angle": 26.0,
            },
            captured_preview_image=preview_image,
        )
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self.window.scene.select_node(node_id, False)
        self.app.processEvents()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        self.assertIsNotNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "full")

        self.app.sendEvent(self.window, QEvent(QEvent.Type.WindowDeactivate))
        self.app.processEvents()

        self.assertEqual(len(binder.capture_calls), 1)
        self.assertEqual(len(self.window.execution_client.update_calls), 1)
        blur_update = self.window.execution_client.update_calls[-1]
        self.assertEqual(blur_update["node_id"], node_id)
        self.assertEqual(blur_update["options"]["live_mode"], "proxy")
        self.assertEqual(blur_update["camera_state"], binder.captured_camera_state)
        self.assertEqual(len(binder.release_calls), 1)
        self.assertTrue(binder.release_calls[-1]["visible"])

    def test_window_deactivate_leaves_keep_live_session_in_full_mode(self) -> None:
        binder = _RecordingBinder(
            captured_camera_state={
                "position": [7.0, 8.0, 9.0],
                "focal_point": [0.0, 0.0, 0.0],
                "viewup": [0.0, 1.0, 0.0],
            }
        )
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self.window.scene.select_node(node_id, False)
        self.app.processEvents()
        self._emit_viewer_event(
            event_type="viewer_data_materialized",
            node_id=node_id,
            keep_live=True,
            live_policy="focus_only",
        )

        self.assertIsNotNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "full")

        self.app.sendEvent(self.window, QEvent(QEvent.Type.WindowDeactivate))
        self.app.processEvents()

        self.assertEqual(len(binder.capture_calls), 0)
        self.assertEqual(len(self.window.execution_client.update_calls), 0)
        self.assertEqual(len(binder.release_calls), 0)
        self.assertIsNotNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.bridge.session_state(node_id)["options"]["live_mode"], "full")

    def test_application_inactive_blurs_live_viewer_once(self) -> None:
        binder = _RecordingBinder(
            captured_camera_state={
                "position": [2.0, 3.0, 4.0],
                "focal_point": [0.0, 0.0, 0.0],
                "viewup": [0.0, 1.0, 0.0],
            }
        )
        self.host_service.register_binder("tests.viewer_backend", binder)
        node_id = self._add_viewer_node()

        self.window.scene.select_node(node_id, False)
        self.app.processEvents()
        self._emit_viewer_event(event_type="viewer_data_materialized", node_id=node_id)

        self.window._handle_application_state_changed(Qt.ApplicationState.ApplicationInactive)
        self.window._handle_application_state_changed(Qt.ApplicationState.ApplicationSuspended)
        self.app.processEvents()

        self.assertEqual(len(binder.capture_calls), 1)
        self.assertEqual(len(self.window.execution_client.update_calls), 1)
        self.assertEqual(self.window.execution_client.update_calls[-1]["options"]["live_mode"], "proxy")


if __name__ == "__main__":
    unittest.main()
