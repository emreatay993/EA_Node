from __future__ import annotations

from pathlib import Path
import textwrap
import unittest
from unittest.mock import patch

from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    assert_no_graph_surface_pointer_regressions,
    run_qml_probe,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


class GraphSurfaceInputContractTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.ui.media_preview_provider import (
                LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
                LocalMediaPreviewImageProvider,
            )
            from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
            engine.rootContext().setContextProperty("themeBridge", ThemeBridge(theme_id="stitch_dark"))
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridge(theme_id="graph_stitch_dark"))

            repo_root = Path.cwd()
            components_dir = repo_root / "ea_node_editor" / "ui_qml" / "components"
            graph_canvas_qml_path = components_dir / "GraphCanvas.qml"
            graph_node_host_qml_path = components_dir / "graph" / "GraphNodeHost.qml"

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

            def node_payload(surface_family="standard", surface_variant=""):
                return {
                    "node_id": "node_surface_contract_test",
                    "type_id": "core.logger",
                    "title": "Logger",
                    "x": 120.0,
                    "y": 120.0,
                    "width": 210.0,
                    "height": 88.0,
                    "accent": "#2F89FF",
                    "collapsed": False,
                    "selected": False,
                    "runtime_behavior": "active",
                    "surface_family": surface_family,
                    "surface_variant": surface_variant,
                    "surface_metrics": {
                        "default_width": 210.0,
                        "default_height": 88.0,
                        "min_width": 120.0,
                        "min_height": 50.0,
                        "collapsed_width": 130.0,
                        "collapsed_height": 36.0,
                        "header_height": 24.0,
                        "header_top_margin": 4.0,
                        "body_left_margin": 8.0,
                        "body_right_margin": 8.0,
                        "body_top": 30.0,
                        "body_height": 30.0,
                        "port_top": 60.0,
                        "port_height": 18.0,
                        "port_center_offset": 6.0,
                        "port_side_margin": 8.0,
                        "port_dot_radius": 3.5,
                        "resize_handle_size": 16.0,
                    },
                    "visual_style": {},
                    "can_enter_scope": False,
                    "ports": [
                        {
                            "key": "exec_in",
                            "label": "Exec In",
                            "direction": "in",
                            "kind": "exec",
                            "data_type": "exec",
                            "connected": False,
                        },
                        {
                            "key": "exec_out",
                            "label": "Exec Out",
                            "direction": "out",
                            "kind": "exec",
                            "data_type": "exec",
                            "connected": False,
                        },
                    ],
                    "inline_properties": [
                        {
                            "key": "message",
                            "label": "Message",
                            "inline_editor": "text",
                            "value": "log message",
                            "overridden_by_input": False,
                            "input_port_label": "message",
                        }
                    ],
                }
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

    def test_graph_surface_pointer_audit_rejects_hover_proxy_shims_and_untracked_surface_mouse_areas(self) -> None:
        assert_no_graph_surface_pointer_regressions(self)

    def test_surface_loader_forwards_embedded_interactive_rects_for_inline_properties(self) -> None:
        self._run_qml_probe(
            "loader-embedded-rects",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))

            assert len(embedded_rects) == 1
            assert rect_field(embedded_rects[0], "x") > 80.0
            assert rect_field(embedded_rects[0], "y") >= 30.0
            assert rect_field(embedded_rects[0], "width") > 80.0
            assert rect_field(embedded_rects[0], "width") < 120.0
            assert rect_field(embedded_rects[0], "height") >= 18.0
            """,
        )

    def test_surface_loader_tracks_control_scoped_rects_for_all_core_inline_editors(self) -> None:
        self._run_qml_probe(
            "loader-core-inline-editor-rects",
            """
            payload = node_payload()
            payload["inline_properties"] = [
                {
                    "key": "enabled",
                    "label": "Enabled",
                    "inline_editor": "toggle",
                    "value": True,
                    "overridden_by_input": False,
                    "input_port_label": "enabled",
                },
                {
                    "key": "mode",
                    "label": "Mode",
                    "inline_editor": "enum",
                    "value": "two",
                    "enum_values": ["one", "two", "three"],
                    "overridden_by_input": False,
                    "input_port_label": "mode",
                },
                {
                    "key": "message",
                    "label": "Message",
                    "inline_editor": "text",
                    "value": "log message",
                    "overridden_by_input": False,
                    "input_port_label": "message",
                },
                {
                    "key": "count",
                    "label": "Count",
                    "inline_editor": "number",
                    "value": "5",
                    "overridden_by_input": False,
                    "input_port_label": "count",
                },
            ]

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 4

            xs = [rect_field(rect, "x") for rect in embedded_rects]
            widths = [rect_field(rect, "width") for rect in embedded_rects]
            ys = [rect_field(rect, "y") for rect in embedded_rects]

            assert all(x > 80.0 for x in xs)
            assert widths[0] < 40.0
            assert all(width > 80.0 for width in widths[1:])
            assert ys == sorted(ys)
            """,
        )

    def test_host_body_interactions_yield_inside_embedded_rects_but_still_work_adjacent_to_them(self) -> None:
        self._run_qml_probe(
            "embedded-rect-hit-testing",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            gesture_layer = host.findChild(QObject, "graphNodeHostGestureLayer")
            drag_area = host.findChild(QObject, "graphNodeDragArea")
            assert loader is not None
            assert gesture_layer is not None
            assert drag_area is not None
            assert drag_area.parentItem().objectName() == "graphNodeHostGestureLayer"

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 1
            row_rect = embedded_rects[0]
            assert rect_field(row_rect, "x") > 80.0

            window = attach_host_to_window(host)

            inside_point = host_scene_point(
                host,
                rect_field(row_rect, "x") + 8.0,
                rect_field(row_rect, "y") + rect_field(row_rect, "height") * 0.5,
            )
            body_local_x = rect_field(row_rect, "x") - 8.0
            body_local_y = rect_field(row_rect, "y") + rect_field(row_rect, "height") * 0.5
            body_point = host_scene_point(host, body_local_x, body_local_y)

            assert_host_pointer_routing(
                host,
                window,
                inside_point,
                body_point,
                "node_surface_contract_test",
                expected_body_local=(body_local_x, body_local_y),
            )

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_routes_surface_control_edits_by_explicit_node_id(self) -> None:
        self._run_qml_probe(
            "graph-canvas-surface-control-bridge",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

            class SceneBridgeStub(QObject):
                nodes_changed = pyqtSignal()
                edges_changed = pyqtSignal()

                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.set_node_property_calls = []
                    self._nodes_model = [node_payload()]
                    self._selected_node_lookup = {}

                @pyqtProperty("QVariantList", notify=nodes_changed)
                def nodes_model(self):
                    return self._nodes_model

                @pyqtProperty("QVariantList", notify=edges_changed)
                def edges_model(self):
                    return []

                @pyqtProperty("QVariantMap", notify=nodes_changed)
                def selected_node_lookup(self):
                    return self._selected_node_lookup

                @pyqtSlot(str)
                @pyqtSlot(str, bool)
                def select_node(self, node_id, additive=False):
                    normalized_node_id = str(node_id or "")
                    self.select_calls.append((normalized_node_id, bool(additive)))
                    self._selected_node_lookup = {normalized_node_id: True} if normalized_node_id else {}
                    self.nodes_changed.emit()

                @pyqtSlot(str, str, "QVariant")
                def set_node_property(self, node_id, key, value):
                    self.set_node_property_calls.append((str(node_id or ""), str(key or ""), variant_value(value)))

                @pyqtSlot(str, str, result=bool)
                def are_port_kinds_compatible(self, _source_kind, _target_kind):
                    return True

                @pyqtSlot(str, str, result=bool)
                def are_data_types_compatible(self, _source_type, _target_type):
                    return True

            class MainWindowBridgeStub(QObject):
                @pyqtProperty(bool, constant=True)
                def graphics_minimap_expanded(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, constant=True)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, constant=True)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, constant=True)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, constant=True)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                def __init__(self):
                    super().__init__()
                    self.set_selected_node_property_calls = []

                @pyqtSlot(str, "QVariant")
                def set_selected_node_property(self, key, value):
                    self.set_selected_node_property_calls.append((str(key or ""), variant_value(value)))

            scene_bridge = SceneBridgeStub()
            window_bridge = MainWindowBridgeStub()
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene_bridge,
                    "mainWindowBridge": window_bridge,
                },
            )
            def walk_items(item):
                yield item
                for child in item.childItems():
                    yield from walk_items(child)

            node_card = next((item for item in walk_items(canvas) if item.objectName() == "graphNodeCard"), None)
            assert node_card is not None

            canvas.setProperty(
                "pendingConnectionPort",
                {
                    "node_id": "pending-node",
                    "port_key": "exec_out",
                    "direction": "out",
                    "allow_multiple_connections": False,
                    "scene_x": 10.0,
                    "scene_y": 12.0,
                },
            )
            canvas.setProperty(
                "wireDragState",
                {
                    "node_id": "pending-node",
                    "port_key": "exec_out",
                    "source_direction": "out",
                    "start_x": 10.0,
                    "start_y": 12.0,
                    "cursor_x": 20.0,
                    "cursor_y": 30.0,
                    "press_screen_x": 40.0,
                    "press_screen_y": 50.0,
                    "active": True,
                },
            )
            canvas.setProperty(
                "wireDropCandidate",
                {
                    "node_id": "candidate-node",
                    "port_key": "exec_in",
                    "direction": "in",
                    "scene_x": 20.0,
                    "scene_y": 30.0,
                    "valid_drop": True,
                },
            )
            canvas.setProperty("edgeContextVisible", True)
            canvas.setProperty("nodeContextVisible", True)
            canvas.setProperty("selectedEdgeIds", ["edge-1"])
            app.processEvents()

            node_card.surfaceControlInteractionStarted.emit("node_surface_contract_test")
            app.processEvents()

            assert scene_bridge.select_calls == [("node_surface_contract_test", False)]
            assert canvas.property("pendingConnectionPort") is None
            assert canvas.property("wireDragState") is None
            assert canvas.property("wireDropCandidate") is None
            assert not bool(canvas.property("edgeContextVisible"))
            assert not bool(canvas.property("nodeContextVisible"))
            assert variant_list(canvas.property("selectedEdgeIds")) == []

            node_card.inlinePropertyCommitted.emit(
                "node_surface_contract_test",
                "message",
                "updated from graph surface",
            )
            app.processEvents()

            assert scene_bridge.set_node_property_calls == [
                ("node_surface_contract_test", "message", "updated from graph surface")
            ]
            assert window_bridge.set_selected_node_property_calls == []
            assert scene_bridge.select_calls == [
                ("node_surface_contract_test", False),
                ("node_surface_contract_test", False),
            ]

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_media_whole_surface_lock_remains_independent_from_local_interactive_rects(self) -> None:
        self._run_qml_probe(
            "media-whole-surface-lock",
            """
            import tempfile
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-contract.png"
                image = QImage(24, 18, QImage.Format.Format_ARGB32)
                image.fill(QColor("#2c85bf"))
                assert image.save(str(image_path))

                media_payload = node_payload(surface_family="media", surface_variant="image_panel")
                media_payload["runtime_behavior"] = "passive"
                media_payload["surface_metrics"] = {}
                media_payload["properties"] = {
                    "source_path": str(image_path),
                    "caption": "",
                    "fit_mode": "contain",
                }
                host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
                surface = host.findChild(QObject, "graphNodeMediaSurface")
                loader = host.findChild(QObject, "graphNodeSurfaceLoader")
                drag_area = host.findChild(QObject, "graphNodeDragArea")
                assert surface is not None
                assert loader is not None
                assert drag_area is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                window = attach_host_to_window(host)
                hover_host_local_point(window, host, 80.0, 44.0)

                assert len(variant_list(loader.property("embeddedInteractiveRects"))) == 1
                assert not bool(loader.property("blocksHostInteraction"))
                assert bool(drag_area.property("enabled"))

                surface.setProperty("cropModeActive", True)
                app.processEvents()

                assert len(variant_list(loader.property("embeddedInteractiveRects"))) == 10
                assert bool(loader.property("blocksHostInteraction"))
                assert not bool(drag_area.property("enabled"))

                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )

    def test_graph_scene_bridge_exposes_set_node_property_as_qml_slot(self) -> None:
        from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

        bridge = GraphSceneBridge()
        meta_object = bridge.metaObject()
        method_signatures = [
            bytes(meta_object.method(index).methodSignature()).decode("utf-8")
            for index in range(meta_object.methodOffset(), meta_object.methodCount())
        ]
        self.assertIn("set_node_property(QString,QString,QVariant)", method_signatures)

    def test_shell_window_browse_node_property_path_uses_explicit_node_id(self) -> None:
        from PyQt6.QtWidgets import QApplication

        from ea_node_editor.ui.shell.window import ShellWindow

        app = QApplication.instance() or QApplication([])
        window = ShellWindow()
        try:
            image_node_id = window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
            logger_node_id = window.scene.add_node_from_type("core.logger", x=360.0, y=80.0)
            self.assertTrue(image_node_id)
            self.assertTrue(logger_node_id)
            app.processEvents()

            picked_path = str(_REPO_ROOT / "tests" / "fixtures" / "graph-surface-picked-path.png")
            with patch(
                "ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName",
                return_value=(picked_path, ""),
            ) as dialog_mock:
                self.assertEqual(window.browse_selected_node_property_path("source_path", ""), "")
                self.assertEqual(
                    window.browse_node_property_path(image_node_id, "source_path", ""),
                    picked_path,
                )
                self.assertEqual(dialog_mock.call_count, 1)

            self.assertEqual(window.browse_node_property_path(logger_node_id, "message", ""), "")
        finally:
            window.close()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    unittest.main()
