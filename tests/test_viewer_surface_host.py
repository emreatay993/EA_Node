from __future__ import annotations

import unittest

from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    run_qml_probe,
)


class ViewerSurfaceHostTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.ui.icon_registry import (
                UI_ICON_PROVIDER_ID,
                UiIconImageProvider,
                UiIconRegistryBridge,
            )
            from ea_node_editor.ui.media_preview_provider import (
                LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
                LocalMediaPreviewImageProvider,
            )

            class ThemeBridgeStub(QObject):
                @pyqtProperty("QVariantMap", constant=True)
                def palette(self):
                    return {
                        "accent": "#2F89FF",
                        "border": "#3a4355",
                        "canvas_bg": "#151821",
                        "canvas_major_grid": "#2f3644",
                        "canvas_minor_grid": "#222833",
                        "group_title_fg": "#d5dbea",
                        "hover": "#33405c",
                        "muted_fg": "#95a0b8",
                        "panel_bg": "#1b1f2a",
                        "panel_title_fg": "#eef3ff",
                        "pressed": "#22304a",
                        "toolbar_bg": "#202635",
                    }

            class GraphThemeBridgeStub(QObject):
                @pyqtProperty("QVariantMap", constant=True)
                def node_palette(self):
                    return {
                        "card_bg": "#1f2431",
                        "card_border": "#414a5d",
                        "card_selected_border": "#5da9ff",
                        "header_bg": "#252c3c",
                        "header_fg": "#eef3ff",
                        "inline_driven_fg": "#aeb8ce",
                        "inline_input_bg": "#18202d",
                        "inline_input_border": "#465066",
                        "inline_input_fg": "#eef3ff",
                        "inline_label_fg": "#d5dbea",
                        "inline_row_bg": "#202635",
                        "inline_row_border": "#3a4355",
                        "port_interactive_border": "#8ca0c7",
                        "port_interactive_fill": "#101521",
                        "port_interactive_ring_border": "#7fb2ff",
                        "port_interactive_ring_fill": "#1a2233",
                        "port_label_fg": "#d5dbea",
                        "scope_badge_bg": "#1f3657",
                        "scope_badge_border": "#4c7bc0",
                        "scope_badge_fg": "#eef3ff",
                    }

                @pyqtProperty("QVariantMap", constant=True)
                def port_kind_palette(self):
                    return {
                        "data": "#7AA8FF",
                        "exec": "#67D487",
                        "completed": "#E4CE7D",
                        "failed": "#D94F4F",
                    }

                @pyqtProperty("QVariantMap", constant=True)
                def edge_palette(self):
                    return {
                        "invalid_drag_stroke": "#D94F4F",
                        "preview_stroke": "#95a0b8",
                        "selected_stroke": "#5da9ff",
                        "valid_drag_stroke": "#67D487",
                    }

            class ViewerSessionBridgeStub(QObject):
                sessions_changed = pyqtSignal()
                last_error_changed = pyqtSignal()

                def __init__(self, parent=None):
                    super().__init__(parent)
                    self.open_calls = []
                    self.update_calls = []
                    self.close_calls = []
                    self.focus_calls = []
                    self.clear_focus_calls = 0
                    self.session_state_calls = []
                    self._last_error = ""
                    self._state = self._build_state()

                def _build_state(
                    self,
                    *,
                    phase="open",
                    playback_state="paused",
                    step_index=3,
                    live_policy="focus_only",
                    keep_live=False,
                    cache_state="proxy_ready",
                    live_mode="proxy",
                    session_id="session::node_viewer_surface_host",
                    last_command="open",
                    backend_id="backend.viewer",
                    transport_revision=7,
                    live_open_status="ready",
                    live_open_blocker=None,
                    transport=None,
                    data_refs=None,
                    invalidated_reason="",
                    close_reason="",
                ):
                    if live_open_blocker is None:
                        live_open_blocker = {}
                    if transport is None:
                        transport = {
                            "kind": "bundle",
                            "backend_id": backend_id,
                            "bundle_path": "C:/temp/viewer_bundle",
                        }
                    if data_refs is None:
                        data_refs = {
                            "fields": {"kind": "handle_ref", "handle_id": "handle::fields"},
                            "png": {
                                "__ea_runtime_value__": "artifact_ref",
                                "ref": "artifact://viewer_proxy_png",
                                "artifact_id": "viewer_proxy_png",
                                "scope": "managed",
                            },
                        }
                    return {
                        "workspace_id": "ws_main",
                        "node_id": "node_viewer_surface_host",
                        "session_id": session_id,
                        "phase": phase,
                        "request_id": "req::viewer",
                        "last_command": last_command,
                        "last_error": self._last_error,
                        "playback_state": playback_state,
                        "step_index": step_index,
                        "live_policy": live_policy,
                        "keep_live": keep_live,
                        "cache_state": cache_state,
                        "backend_id": backend_id,
                        "transport_revision": transport_revision,
                        "live_open_status": live_open_status,
                        "live_open_blocker": dict(live_open_blocker),
                        "invalidated_reason": invalidated_reason,
                        "close_reason": close_reason,
                        "data_refs": dict(data_refs),
                        "transport": dict(transport),
                        "summary": {
                            "result_name": "Displacement",
                            "set_label": "Set 4",
                            "cache_state": cache_state,
                            "backend_id": backend_id,
                            "transport_revision": transport_revision,
                            "live_open_status": live_open_status,
                            "live_open_blocker": dict(live_open_blocker),
                        },
                        "options": {
                            "live_mode": live_mode,
                            "playback_state": playback_state,
                            "step_index": step_index,
                            "live_policy": live_policy,
                            "keep_live": keep_live,
                            "backend_id": backend_id,
                            "transport_revision": transport_revision,
                            "live_open_status": live_open_status,
                            "live_open_blocker": dict(live_open_blocker),
                        },
                    }

                def _set_state(self, **updates):
                    state = dict(self._state or self._build_state())
                    summary = dict(state.get("summary", {}))
                    options = dict(state.get("options", {}))
                    summary_updates = dict(updates.pop("summary", {}))
                    options_updates = dict(updates.pop("options", {}))
                    state.update(updates)
                    summary.update(summary_updates)
                    options.update(options_updates)
                    state["summary"] = summary
                    state["options"] = options
                    self._state = state
                    self.sessions_changed.emit()

                @pyqtProperty("QVariantList", notify=sessions_changed)
                def sessions_model(self):
                    return [dict(self._state)] if self._state is not None else []

                @pyqtProperty(str, notify=last_error_changed)
                def last_error(self):
                    return self._last_error

                @pyqtSlot(str, result="QVariantMap")
                def session_state(self, node_id):
                    self.session_state_calls.append(str(node_id))
                    if str(node_id) != "node_viewer_surface_host" or self._state is None:
                        return {}
                    return dict(self._state)

                @pyqtSlot(str, result=str)
                def open(self, node_id):
                    self.open_calls.append({"node_id": str(node_id)})
                    self._set_state(
                        phase="opening",
                        last_command="open",
                        close_reason="",
                        options={
                            "live_mode": "proxy",
                            "playback_state": "paused",
                        },
                    )
                    return "session::node_viewer_surface_host"

                @pyqtSlot(str, result=bool)
                def close(self, node_id):
                    self.close_calls.append({"node_id": str(node_id)})
                    self._set_state(
                        phase="closed",
                        last_command="close",
                        close_reason="user_close",
                        cache_state="proxy_ready",
                        options={
                            "live_mode": "proxy",
                            "playback_state": "paused",
                        },
                        summary={
                            "cache_state": "proxy_ready",
                            "close_reason": "user_close",
                        },
                    )
                    return True

                @pyqtSlot(str, result=bool)
                def play(self, node_id):
                    self.update_calls.append({"command": "play", "node_id": str(node_id)})
                    self._set_state(
                        playback_state="playing",
                        last_command="play",
                        options={"playback_state": "playing"},
                    )
                    return True

                @pyqtSlot(str, result=bool)
                def pause(self, node_id):
                    self.update_calls.append({"command": "pause", "node_id": str(node_id)})
                    self._set_state(
                        playback_state="paused",
                        last_command="pause",
                        options={"playback_state": "paused"},
                    )
                    return True

                @pyqtSlot(str, result=bool)
                def step(self, node_id):
                    self.update_calls.append({"command": "step", "node_id": str(node_id)})
                    next_step = int(self._state.get("step_index", 0)) + 1
                    self._set_state(
                        step_index=next_step,
                        playback_state="paused",
                        last_command="step",
                        options={
                            "step_index": next_step,
                            "playback_state": "paused",
                        },
                    )
                    return True

                @pyqtSlot(str, str, result=bool)
                def set_live_policy(self, node_id, live_policy):
                    normalized = str(live_policy or "").strip() or "focus_only"
                    self.update_calls.append(
                        {"command": "set_live_policy", "node_id": str(node_id), "value": normalized}
                    )
                    self._set_state(
                        live_policy=normalized,
                        last_command="set_live_policy",
                        options={"live_policy": normalized},
                    )
                    return True

                @pyqtSlot(str, bool, result=bool)
                def set_keep_live(self, node_id, keep_live):
                    normalized = bool(keep_live)
                    self.update_calls.append(
                        {"command": "set_keep_live", "node_id": str(node_id), "value": normalized}
                    )
                    self._set_state(
                        keep_live=normalized,
                        last_command="set_keep_live",
                        options={"keep_live": normalized},
                    )
                    return True

                @pyqtSlot(str, result=bool)
                def focus_session(self, node_id):
                    self.focus_calls.append(str(node_id))
                    return True

                @pyqtSlot(result=bool)
                def clear_viewer_focus(self):
                    self.clear_focus_calls += 1
                    return True

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.addImageProvider(UI_ICON_PROVIDER_ID, UiIconImageProvider())
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
            engine.rootContext().setContextProperty("uiIcons", UiIconRegistryBridge())
            engine.rootContext().setContextProperty("themeBridge", ThemeBridgeStub())
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridgeStub())

            repo_root = Path.cwd()
            graph_node_host_qml_path = repo_root / "ea_node_editor" / "ui_qml" / "components" / "graph" / "GraphNodeHost.qml"

            def create_component(path, initial_properties):
                component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
                if component.status() != QQmlComponent.Status.Ready:
                    errors = "\\n".join(error.toString() for error in component.errors())
                    raise AssertionError(f"Failed to load {path.name}:\\n{errors}")
                if hasattr(component, "createWithInitialProperties"):
                    obj = component.createWithInitialProperties(initial_properties)
                else:
                    obj = component.create()
                    for key, value in initial_properties.items():
                        obj.setProperty(key, value)
                if obj is None:
                    errors = "\\n".join(error.toString() for error in component.errors())
                    raise AssertionError(f"Failed to instantiate {path.name}:\\n{errors}")
                app.processEvents()
                return obj

            def viewer_payload():
                return {
                    "node_id": "node_viewer_surface_host",
                    "type_id": "tests.viewer_surface_host",
                    "title": "Viewer Host",
                    "x": 120.0,
                    "y": 90.0,
                    "width": 296.0,
                    "height": 236.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": True,
                    "runtime_behavior": "active",
                    "surface_family": "viewer",
                    "surface_variant": "",
                    "render_quality": {
                        "weight_class": "heavy",
                        "max_performance_strategy": "proxy_surface",
                        "supported_quality_tiers": ["full", "proxy"],
                    },
                    "surface_metrics": {
                        "default_width": 296.0,
                        "default_height": 236.0,
                        "min_width": 220.0,
                        "min_height": 208.0,
                        "collapsed_width": 130.0,
                        "collapsed_height": 36.0,
                        "header_height": 24.0,
                        "header_top_margin": 4.0,
                        "body_top": 30.0,
                        "body_height": 176.0,
                        "port_top": 206.0,
                        "port_height": 18.0,
                        "port_center_offset": 6.0,
                        "port_side_margin": 8.0,
                        "port_dot_radius": 3.5,
                        "resize_handle_size": 16.0,
                        "title_top": 4.0,
                        "title_height": 24.0,
                        "title_left_margin": 10.0,
                        "title_right_margin": 42.0,
                        "title_centered": False,
                        "body_left_margin": 14.0,
                        "body_right_margin": 14.0,
                        "body_bottom_margin": 12.0,
                        "show_header_background": True,
                        "show_accent_bar": True,
                        "use_host_chrome": True,
                        "standard_title_full_width": 0.0,
                        "standard_left_label_width": 0.0,
                        "standard_right_label_width": 0.0,
                        "standard_port_gutter": 21.5,
                        "standard_center_gap": 24.0,
                        "standard_port_label_min_width": 0.0,
                    },
                    "viewer_surface": {
                        "body_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                        "proxy_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                        "live_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                        "overlay_target": "body",
                        "proxy_surface_supported": True,
                        "live_surface_supported": True,
                    },
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [
                        {
                            "key": "fields",
                            "label": "Fields",
                            "direction": "in",
                            "kind": "data",
                            "data_type": "dpf_field",
                            "connected": False,
                        },
                        {
                            "key": "session",
                            "label": "Session",
                            "direction": "out",
                            "kind": "data",
                            "data_type": "dpf_view_session",
                            "connected": False,
                        },
                    ],
                    "inline_properties": [],
                }
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

    def test_viewer_surface_controls_follow_bridge_state_and_route_actions(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-actions",
            """
            from PyQt6.QtCore import QMetaObject, Q_ARG

            bridge = ViewerSessionBridgeStub()
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            proxy_image = host.findChild(QObject, "graphNodeViewerProxyImage")
            status_text = host.findChild(QObject, "graphNodeViewerStatusText")
            mode_label = host.findChild(QObject, "graphNodeViewerSurfaceModeLabel")
            assert surface is not None
            assert host.findChild(QObject, "graphNodeViewerSessionButton") is None
            assert host.findChild(QObject, "graphNodeViewerPlayPauseButton") is None
            assert host.findChild(QObject, "graphNodeViewerStepButton") is None
            assert host.findChild(QObject, "graphNodeViewerKeepLiveButton") is None
            assert host.findChild(QObject, "graphNodeViewerFocusPolicyChip") is None
            assert host.findChild(QObject, "graphNodeViewerKeepPolicyChip") is None
            assert host.findChild(QObject, "graphNodeViewerMoreButton") is None
            assert host.findChild(QObject, "graphNodeViewerQuickActions") is None
            assert proxy_image is not None
            assert status_text is not None
            assert mode_label is not None

            def dispatch(action_id):
                QMetaObject.invokeMethod(surface, "dispatchSurfaceAction", Q_ARG("QVariant", action_id))

            def action_by_id(actions, target_id):
                return next(action for action in actions if action["id"] == target_id)

            interactions = []
            host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
            pointer_events = host_pointer_events(host)
            window = attach_host_to_window(host, width=640, height=480)
            try:
                assert surface.property("viewerBridgeAvailable")
                assert surface.property("viewerPhase") == "open"
                assert surface.property("viewerPlaybackState") == "paused"
                assert surface.property("viewerLivePolicy") == "focus_only"
                assert not bool(surface.property("viewerKeepLive"))
                assert surface.property("viewerLiveMode") == "proxy"
                assert bool(surface.property("proxySurfaceActive"))
                assert not bool(surface.property("liveSurfaceActive"))
                assert not bool(surface.property("viewerShowsPlaceholder"))
                assert status_text.property("text") == "Proxy viewer ready"
                assert mode_label.property("text") == "Proxy"
                assert variant_list(surface.property("viewerInteractiveRects")) == []

                actions = variant_list(surface.property("surfaceActions"))
                assert [action["id"] for action in actions] == ["openSession", "playPause", "step", "keepLive", "fullscreen"]
                assert action_by_id(actions, "openSession")["icon"] == "stop"
                assert action_by_id(actions, "playPause")["icon"] == "run"
                assert not bool(action_by_id(actions, "keepLive")["primary"])

                assert bool(proxy_image.property("visible"))
                proxy_image_source = proxy_image.property("source")
                proxy_image_source_text = proxy_image_source.toString() if hasattr(proxy_image_source, "toString") else str(proxy_image_source)
                assert proxy_image_source_text.startswith("image://local-media-preview/preview?source=")

                dispatch("playPause")
                settle_events(5)
                assert bridge.update_calls[-1]["command"] == "play"
                assert bridge.focus_calls[-1] == "node_viewer_surface_host"
                assert surface.property("viewerPlaybackState") == "playing"
                playing_actions = variant_list(surface.property("surfaceActions"))
                assert action_by_id(playing_actions, "playPause")["icon"] == "pause"

                dispatch("step")
                settle_events(5)
                assert bridge.update_calls[-1]["command"] == "step"
                assert int(surface.property("viewerStepIndex")) == 4

                dispatch("keepLive")
                settle_events(5)
                assert bridge.update_calls[-1] == {
                    "command": "set_keep_live",
                    "node_id": "node_viewer_surface_host",
                    "value": True,
                }
                assert surface.property("viewerLivePolicy") == "focus_only"
                assert bool(surface.property("viewerKeepLive"))
                keep_live_actions = variant_list(surface.property("surfaceActions"))
                assert bool(action_by_id(keep_live_actions, "keepLive")["primary"])

                dispatch("openSession")
                settle_events(5)
                assert bridge.close_calls == [{"node_id": "node_viewer_surface_host"}]
                assert surface.property("viewerPhase") == "closed"
                assert bool(surface.property("viewerShowsPlaceholder"))
                closed_actions = variant_list(surface.property("surfaceActions"))
                assert action_by_id(closed_actions, "openSession")["icon"] == "open-session"
                assert status_text.property("text") == "Ready to open viewer session"
                assert mode_label.property("text") == "Overlay"

                dispatch("openSession")
                settle_events(5)
                assert bridge.open_calls == [{"node_id": "node_viewer_surface_host"}]
                assert surface.property("viewerPhase") == "opening"
                opening_actions = variant_list(surface.property("surfaceActions"))
                assert action_by_id(opening_actions, "openSession")["icon"] == "open-session"
                assert status_text.property("text") == "Opening viewer session"
                assert mode_label.property("text") == "Opening"
                assert len(interactions) >= 5
                assert all(node_id == "node_viewer_surface_host" for node_id in interactions)
                assert len(bridge.session_state_calls) >= 1
                assert all(node_id == "node_viewer_surface_host" for node_id in bridge.session_state_calls)
                assert pointer_events["clicked"] == []
                assert pointer_events["opened"] == []
                assert pointer_events["contexts"] == []
            finally:
                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_viewer_surface_blurs_live_session_on_drag_and_resize_press(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-blur-on-drag-start",
            """
            from PyQt6.QtCore import Qt
            from PyQt6.QtTest import QTest

            bridge = ViewerSessionBridgeStub()
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            drag_area = host.findChild(QObject, "graphNodeDragArea")
            resize_areas = named_child_items(host, "graphNodeResizeDragArea")
            assert drag_area is not None
            assert len(resize_areas) >= 1

            window = attach_host_to_window(host, width=640, height=480)
            try:
                header_point = host_scene_point(host, 18.0, 12.0)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, header_point)
                settle_events(3)
                assert bridge.clear_focus_calls == 1
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, header_point)
                settle_events(3)

                resize_point = item_scene_point(resize_areas[0])
                QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, resize_point)
                settle_events(3)
                assert bridge.clear_focus_calls == 2
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, resize_point)
                settle_events(3)
            finally:
                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_viewer_surface_defaults_to_closed_bridge_contract_without_context_property(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-default-contract",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            status_text = host.findChild(QObject, "graphNodeViewerStatusText")
            mode_label = host.findChild(QObject, "graphNodeViewerSurfaceModeLabel")
            assert surface is not None
            assert host.findChild(QObject, "graphNodeViewerSessionButton") is None
            assert host.findChild(QObject, "graphNodeViewerMoreButton") is None
            assert status_text is not None
            assert mode_label is not None

            contract = variant_value(surface.property("viewerSurfaceContract"))
            bridge_binding = variant_value(surface.property("viewerBridgeBinding"))
            interactive_rects = variant_list(surface.property("viewerInteractiveRects"))
            actions = variant_list(surface.property("surfaceActions"))

            assert not bool(surface.property("viewerBridgeAvailable"))
            assert surface.property("viewerPhase") == "closed"
            assert bool(surface.property("viewerShowsPlaceholder"))
            assert status_text.property("text") == "Viewer bridge unavailable"
            assert mode_label.property("text") == "Overlay"
            assert contract["bridge_binding"]["phase"] == "closed"
            assert not bool(contract["bridge_binding"]["bridge_available"])
            assert bridge_binding["phase"] == "closed"
            assert interactive_rects == []
            open_session_action = next(action for action in actions if action["id"] == "openSession")
            assert not bool(open_session_action["enabled"])
            """,
        )

    def test_viewer_surface_contract_live_rect_tracks_inner_viewport_frame(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-live-rect-viewport",
            """
            bridge = ViewerSessionBridgeStub()
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            body_frame = host.findChild(QObject, "graphNodeViewerBodyFrame")
            viewport = host.findChild(QObject, "graphNodeViewerViewport")
            assert surface is not None
            assert body_frame is not None
            assert viewport is not None

            window = attach_host_to_window(host, width=640, height=480)
            try:
                contract = variant_value(surface.property("viewerSurfaceContract"))
                live_rect = contract["live_rect"]
                assert abs(float(live_rect["width"]) - float(viewport.property("width"))) <= 0.5
                assert abs(float(live_rect["height"]) - float(viewport.property("height"))) <= 0.5
                assert float(live_rect["y"]) > float(body_frame.property("y"))
            finally:
                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_viewer_surface_body_frame_uses_live_host_metrics_when_payload_rect_is_stale(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-stale-body-rect",
            """
            bridge = ViewerSessionBridgeStub()
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            payload = viewer_payload()
            payload["height"] = 320.0
            payload["viewer_surface"] = {
                "body_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "proxy_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "live_rect": {"x": 14.0, "y": 30.0, "width": 268.0, "height": 176.0},
                "overlay_target": "body",
                "proxy_surface_supported": True,
                "live_surface_supported": True,
            }

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            body_frame = host.findChild(QObject, "graphNodeViewerBodyFrame")
            assert surface is not None
            assert body_frame is not None

            window = attach_host_to_window(host, width=640, height=480)
            try:
                metrics = variant_value(host.property("surfaceMetrics"))
                contract = variant_value(surface.property("viewerSurfaceContract"))
                body_height = float(body_frame.property("height"))

                assert abs(float(metrics["body_height"]) - 260.0) < 0.1, metrics
                assert abs(body_height - float(metrics["body_height"])) < 0.1
                assert abs(float(contract["body_rect"]["height"]) - float(metrics["body_height"])) < 0.1
                assert float(contract["body_rect"]["height"]) > 176.0
            finally:
                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_viewer_surface_reflects_proxy_demotion_and_live_restoration(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-proxy-restore",
            """
            bridge = ViewerSessionBridgeStub()
            bridge._set_state(
                cache_state="live_ready",
                options={"live_mode": "full"},
                summary={"camera": {"zoom": 1.2}},
            )
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            status_text = host.findChild(QObject, "graphNodeViewerStatusText")
            mode_label = host.findChild(QObject, "graphNodeViewerSurfaceModeLabel")
            assert surface is not None
            assert status_text is not None
            assert mode_label is not None

            window = attach_host_to_window(host, width=640, height=480)
            try:
                assert bool(surface.property("liveSurfaceActive"))
                assert not bool(surface.property("proxySurfaceActive"))
                assert status_text.property("text") == "Live overlay active"
                assert mode_label.property("text") == "Live"

                bridge._set_state(
                    cache_state="proxy_ready",
                    options={"live_mode": "proxy"},
                    summary={"demoted_reason": "focus_only"},
                )
                settle_events(5)
                assert not bool(surface.property("liveSurfaceActive"))
                assert bool(surface.property("proxySurfaceActive"))
                assert "focus_only" in str(surface.property("viewerHintText"))
                assert status_text.property("text") == "Proxy viewer ready"
                assert mode_label.property("text") == "Proxy"

                bridge._set_state(
                    cache_state="live_ready",
                    options={"live_mode": "full"},
                    summary={"demoted_reason": ""},
                )
                settle_events(5)
                assert bool(surface.property("liveSurfaceActive"))
                assert not bool(surface.property("proxySurfaceActive"))
                assert "Demoted to proxy" not in str(surface.property("viewerHintText"))
                assert status_text.property("text") == "Live overlay active"
                assert mode_label.property("text") == "Live"
            finally:
                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_viewer_surface_uses_preview_ref_when_png_ref_is_absent(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-preview-ref-fallback",
            """
            import tempfile
            from urllib.parse import quote

            from PyQt6.QtGui import QImage

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_file.close()
            preview_path = Path(temp_file.name)
            preview_image = QImage(18, 12, QImage.Format.Format_ARGB32)
            preview_image.fill(0xFF5DA9FF)
            assert preview_image.save(str(preview_path), "PNG")

            bridge = ViewerSessionBridgeStub()
            bridge._set_state(
                cache_state="proxy_ready",
                options={"live_mode": "proxy"},
                data_refs={"preview": str(preview_path)},
            )
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            proxy_image = host.findChild(QObject, "graphNodeViewerProxyImage")
            assert surface is not None
            assert proxy_image is not None

            window = attach_host_to_window(host, width=640, height=480)
            try:
                settle_events(5)
                assert bool(surface.property("proxySurfaceActive"))
                assert bool(surface.property("viewerPreviewAvailable"))
                assert bool(proxy_image.property("visible"))
                proxy_image_source = proxy_image.property("source")
                proxy_image_source_text = proxy_image_source.toString() if hasattr(proxy_image_source, "toString") else str(proxy_image_source)
                assert proxy_image_source_text.startswith("image://local-media-preview/preview?source=")
                assert quote(str(preview_path), safe="") in proxy_image_source_text
            finally:
                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
                try:
                    preview_path.unlink()
                except OSError:
                    pass
            """,
        )

    def test_viewer_surface_compact_strip_reports_error_and_run_required_states(self) -> None:
        self._run_qml_probe(
            "viewer-surface-host-error-run-required",
            """
            bridge = ViewerSessionBridgeStub()
            engine.rootContext().setContextProperty("viewerSessionBridge", bridge)

            host = create_component(graph_node_host_qml_path, {"nodeData": viewer_payload()})
            surface = host.findChild(QObject, "graphNodeViewerSurface")
            status_text = host.findChild(QObject, "graphNodeViewerStatusText")
            mode_label = host.findChild(QObject, "graphNodeViewerSurfaceModeLabel")
            headline = host.findChild(QObject, "graphNodeViewerSurfaceHeadline")
            hint = host.findChild(QObject, "graphNodeViewerSurfaceHint")
            assert surface is not None
            assert host.findChild(QObject, "graphNodeViewerSessionButton") is None
            assert host.findChild(QObject, "graphNodeViewerMoreButton") is None
            assert status_text is not None
            assert mode_label is not None
            assert headline is not None
            assert hint is not None

            def open_session_action():
                actions = variant_list(surface.property("surfaceActions"))
                return next(action for action in actions if action["id"] == "openSession")

            window = attach_host_to_window(host, width=640, height=480)
            try:
                bridge._last_error = "launch failed"
                bridge.last_error_changed.emit()
                bridge._set_state(phase="error", last_command="open")
                settle_events(5)
                assert bool(surface.property("viewerShowsPlaceholder"))
                assert status_text.property("text") == "launch failed"
                assert mode_label.property("text") == "Proxy"
                assert headline.property("text") == "launch failed"
                assert hint.property("text") == "launch failed"

                bridge._last_error = ""
                bridge.last_error_changed.emit()
                bridge._set_state(
                    phase="blocked",
                    cache_state="proxy_ready",
                    live_mode="proxy",
                    live_open_status="blocked",
                    live_open_blocker={
                        "code": "rerun_required",
                        "reason": "Live viewer transport is unavailable and requires rerun.",
                        "rerun_required": True,
                    },
                    transport={"kind": "bundle", "backend_id": "backend.viewer"},
                    summary={
                        "result_name": "Displacement",
                        "set_label": "Set 4",
                        "rerun_required": True,
                        "live_transport_release_reason": "project_reload",
                    },
                    options={"rerun_required": True},
                )
                settle_events(5)
                assert bool(surface.property("viewerShowsPlaceholder"))
                assert not bool(open_session_action()["enabled"])
                assert status_text.property("text") == "Rerun required before live open"
                assert mode_label.property("text") == "Blocked"
                assert headline.property("text") == "Rerun required before live open"
                assert "requires rerun" in str(hint.property("text"))
                assert host.findChild(QObject, "graphNodeViewerResultMeta") is None
                assert host.findChild(QObject, "graphNodeViewerSelectionMeta") is None
                assert host.findChild(QObject, "graphNodeViewerStepMeta") is None
                assert host.findChild(QObject, "graphNodeViewerStatusMeta") is None
                assert variant_list(surface.property("viewerInteractiveRects")) == []
            finally:
                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )


if __name__ == "__main__":
    unittest.main()
