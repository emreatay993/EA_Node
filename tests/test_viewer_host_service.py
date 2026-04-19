from __future__ import annotations

import unittest
from typing import Any

from PyQt6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtWidgets import QWidget

from ea_node_editor.addons.catalog import ANSYS_DPF_ADDON_ID
from ea_node_editor.app_preferences import default_app_preferences_document, set_addon_state
from ea_node_editor.nodes.builtins.ansys_dpf_common import DPF_VIEWER_NODE_TYPE_ID
from ea_node_editor.nodes.types import NodeRenderQualitySpec, NodeResult, NodeTypeSpec, PortSpec
from ea_node_editor.ui_qml.dpf_viewer_widget_binder import DpfViewerWidgetBinder
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


class _RecordingBinder:
    def __init__(
        self,
        *,
        reuse_current_widget: bool = True,
        no_bind_predicate=None,  # noqa: ANN001
        captured_camera_state: dict[str, Any] | None = None,
        captured_preview_image: QImage | None = None,
    ) -> None:
        self.reuse_current_widget = reuse_current_widget
        self.no_bind_predicate = no_bind_predicate
        self.captured_camera_state = dict(captured_camera_state or {})
        self.captured_preview_image = captured_preview_image.copy() if isinstance(captured_preview_image, QImage) else QImage()
        self.bind_calls: list[dict[str, Any]] = []
        self.release_calls: list[dict[str, Any]] = []
        self.capture_calls: list[QWidget] = []
        self.capture_preview_calls: list[QWidget] = []
        self.widgets: list[_FakeBinderWidget] = []

    def bind_widget(self, request) -> QWidget | None:  # noqa: ANN001
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
                "session_model": dict(request.session_model),
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

    def capture_camera_state(self, widget: QWidget) -> dict[str, Any]:
        self.capture_calls.append(widget)
        return dict(self.captured_camera_state)

    def capture_preview_image(self, widget: QWidget) -> QImage:
        self.capture_preview_calls.append(widget)
        return self.captured_preview_image.copy()


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
        self.assertEqual(binder.bind_calls[-1]["session_model"]["phase"], "open")
        self.assertEqual(binder.bind_calls[-1]["session_model"]["live_mode"], "full")
        self.assertEqual(binder.bind_calls[-1]["session_model"]["transport_revision"], 1)

        self._close_viewer_session(node_id=node_id)

        self.assertEqual(len(binder.release_calls), 1)
        self.assertIsNone(self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id))
        self.assertIsNone(self.overlay_manager.overlay_container(node_id, workspace_id=self.workspace_id))
        self.assertEqual(self.host_service.active_overlay_count, 0)
        self.assertEqual(binder.widgets[0].close_calls, 1)

    def test_host_service_registers_builtin_dpf_binder(self) -> None:
        self.assertIsInstance(
            self.host_service.binder_registry.lookup(DpfViewerWidgetBinder.backend_id),
            DpfViewerWidgetBinder,
        )

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
        self.app.processEvents()
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
        self.assertEqual(captured.size(), preview_image.size())
        self.assertEqual(len(binder.capture_preview_calls), 1)
        self.assertIs(
            binder.capture_preview_calls[0],
            self.overlay_manager.overlay_widget(node_id, workspace_id=self.workspace_id),
        )

    def test_snapshot_from_projected_state_prefers_projected_camera_state_during_pending_transition(self) -> None:
        snapshot = self.host_service._snapshot_from_projected_state(
            {
                "workspace_id": "ws_main",
                "node_id": "node_viewer",
                "session_id": "session::node_viewer",
                "phase": "open",
                "cache_state": "proxy_ready",
                "camera_state": {"position": [0.0, 0.0, 5.0]},
                "summary": {"cache_state": "proxy_ready"},
                "options": {
                    "backend_id": "tests.viewer_backend",
                    "live_mode": "proxy",
                    "live_open_status": "ready",
                    "transport_revision": 1,
                    "playback_state": "paused",
                    "step_index": 0,
                },
                "transport": {"kind": "tests_transport_bundle", "backend_id": "tests.viewer_backend"},
                "data_refs": {},
                "session_model": {
                    "workspace_id": "ws_main",
                    "node_id": "node_viewer",
                    "session_id": "session::node_viewer",
                    "phase": "open",
                    "playback_state": "paused",
                    "step_index": 0,
                    "playback": {"state": "paused", "step_index": 0},
                    "live_policy": "focus_only",
                    "keep_live": False,
                    "cache_state": "live_ready",
                    "invalidated_reason": "",
                    "close_reason": "",
                    "backend_id": "tests.viewer_backend",
                    "transport_revision": 1,
                    "live_mode": "full",
                    "live_open_status": "ready",
                    "live_open_blocker": {},
                    "data_refs": {},
                    "transport": {"kind": "tests_transport_bundle", "backend_id": "tests.viewer_backend"},
                    "camera_state": {"position": [9.0, 8.0, 7.0], "view_angle": 24.0},
                    "summary": {"cache_state": "live_ready"},
                    "options": {
                        "backend_id": "tests.viewer_backend",
                        "live_mode": "full",
                        "live_open_status": "ready",
                        "transport_revision": 1,
                        "playback_state": "paused",
                        "step_index": 0,
                    },
                },
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
        self.assertFalse(binder.release_calls[-1]["visible"])

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
