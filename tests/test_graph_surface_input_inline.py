from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]


class GraphSurfaceInputInlineTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        script = textwrap.dedent(
            """
            from pathlib import Path
            import textwrap

            from PyQt6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QUrl
            from PyQt6.QtGui import QKeyEvent
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtQuick import QQuickItem, QQuickWindow
            from PyQt6.QtTest import QTest
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

            def variant_value(value):
                return value.toVariant() if hasattr(value, "toVariant") else value

            def variant_list(value):
                normalized = variant_value(value)
                if normalized is None:
                    return []
                return list(normalized)

            def rect_field(rect, key):
                normalized = variant_value(rect)
                if isinstance(normalized, dict):
                    return float(normalized[key])
                try:
                    value = normalized[key]
                except Exception:
                    value = getattr(normalized, key)
                value = variant_value(value)
                return float(value() if callable(value) else value)

            def walk_items(item):
                if isinstance(item, QQuickItem):
                    yield item
                    for child in item.childItems():
                        yield from walk_items(child)

            def named_item(root, object_name, property_key=None):
                for child in walk_items(root):
                    if child.objectName() != object_name:
                        continue
                    if property_key is None or str(child.property("propertyKey")) == property_key:
                        return child
                raise AssertionError(f"Missing object {object_name!r} propertyKey={property_key!r}")

            def item_scene_point(item, x_factor=0.5, y_factor=0.5):
                scene_point = item.mapToScene(QPointF(item.width() * x_factor, item.height() * y_factor))
                return QPoint(round(scene_point.x()), round(scene_point.y()))

            probe_qml = textwrap.dedent(
                '''
                import QtQuick 2.15
                import "ea_node_editor/ui_qml/components/graph" as GraphComponents

                Item {
                    id: root
                    width: 480
                    height: 360

                    Item {
                        id: canvasProxy
                        objectName: "canvasProxy"
                        property string browseResultPath: ""
                        property var lastBrowseCall: ({})

                        function browseNodePropertyPath(nodeId, key, currentPath) {
                            lastBrowseCall = {
                                "nodeId": String(nodeId || ""),
                                "key": String(key || ""),
                                "currentPath": String(currentPath || "")
                            };
                            return browseResultPath;
                        }
                    }

                    function nodePayload() {
                        return {
                            "node_id": "node_inline_test",
                            "type_id": "core.logger",
                            "title": "Inline Probe",
                            "x": 96.0,
                            "y": 84.0,
                            "width": 236.0,
                            "height": 188.0,
                            "accent": "#2F89FF",
                            "collapsed": false,
                            "selected": false,
                            "runtime_behavior": "active",
                            "surface_family": "standard",
                            "surface_variant": "",
                            "surface_metrics": {
                                "default_width": 236.0,
                                "default_height": 188.0,
                                "min_width": 120.0,
                                "min_height": 50.0,
                                "collapsed_width": 130.0,
                                "collapsed_height": 36.0,
                                "header_height": 24.0,
                                "header_top_margin": 4.0,
                                "body_top": 30.0,
                                "body_height": 124.0,
                                "port_top": 154.0,
                                "port_height": 18.0,
                                "port_center_offset": 6.0,
                                "port_side_margin": 8.0,
                                "port_dot_radius": 3.5,
                                "resize_handle_size": 16.0,
                                "title_top": 4.0,
                                "title_height": 24.0,
                                "title_left_margin": 10.0,
                                "title_right_margin": 10.0,
                                "title_centered": false,
                                "body_left_margin": 8.0,
                                "body_right_margin": 8.0,
                                "body_bottom_margin": 8.0,
                                "show_header_background": true,
                                "show_accent_bar": true,
                                "use_host_chrome": true
                            },
                            "visual_style": {},
                            "can_enter_scope": false,
                            "ports": [],
                            "properties": {
                                "source_path": "/fixtures/original.txt",
                                "caption": "Line one"
                            },
                            "inline_properties": [
                                {
                                    "key": "source_path",
                                    "label": "Source",
                                    "inline_editor": "path",
                                    "value": "/fixtures/original.txt",
                                    "overridden_by_input": false,
                                    "input_port_label": "source_path"
                                },
                                {
                                    "key": "caption",
                                    "label": "Caption",
                                    "inline_editor": "textarea",
                                    "value": "Line one",
                                    "overridden_by_input": false,
                                    "input_port_label": "caption"
                                }
                            ]
                        };
                    }

                    GraphComponents.GraphNodeHost {
                        id: host
                        objectName: "probeHost"
                        nodeData: nodePayload()
                        canvasItem: canvasProxy
                    }
                }
                '''
            )
            component = QQmlComponent(engine)
            component.setData(probe_qml.encode("utf-8"), QUrl.fromLocalFile(str(repo_root) + "/"))
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load probe QML:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate probe QML:\\n" + errors)
            app.processEvents()
            """
        ) + "\n" + textwrap.dedent(body)
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            details = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
            self.fail(f"{label} probe failed with exit code {result.returncode}\n{details}")

    def test_inline_layer_publishes_control_scoped_rects_for_path_and_textarea_editors(self) -> None:
        self._run_qml_probe(
            "inline-rects",
            """
            host = probe.findChild(QObject, "probeHost")
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 5, embedded_rects

            widths = [rect_field(rect, "width") for rect in embedded_rects]
            heights = [rect_field(rect, "height") for rect in embedded_rects]
            ys = [rect_field(rect, "y") for rect in embedded_rects]

            assert widths[0] > 30.0, (widths, heights, ys, embedded_rects)
            assert widths[0] + widths[1] > 100.0, (widths, heights, ys, embedded_rects)
            assert widths[1] < 90.0, (widths, heights, ys, embedded_rects)
            assert heights[2] > 60.0, (widths, heights, ys, embedded_rects)
            assert widths[3] < 90.0, (widths, heights, ys, embedded_rects)
            assert widths[4] < 90.0, (widths, heights, ys, embedded_rects)
            assert max(ys[:2]) - min(ys[:2]) <= 4.0, (widths, heights, ys, embedded_rects)
            assert ys[2] > max(ys[:2]), (widths, heights, ys, embedded_rects)
            assert max(ys[3:]) - min(ys[3:]) <= 1.0, (widths, heights, ys, embedded_rects)
            """,
        )

    def test_inline_textarea_honors_dirty_shortcuts_and_explicit_commit(self) -> None:
        self._run_qml_probe(
            "inline-textarea",
            """
            host = probe.findChild(QObject, "probeHost")
            textarea = named_item(probe, "graphNodeInlineTextareaEditor", "caption")
            apply_button = named_item(probe, "graphNodeInlineTextareaApplyButton", "caption")
            reset_button = named_item(probe, "graphNodeInlineTextareaResetButton", "caption")

            commits = []
            host.inlinePropertyCommitted.connect(lambda node_id, key, value: commits.append((node_id, key, value)))

            window = QQuickWindow()
            window.resize(520, 420)
            host.setParentItem(window.contentItem())
            window.show()
            app.processEvents()

            textarea.forceActiveFocus()
            app.processEvents()
            textarea.setProperty("text", "Line one updated")
            app.processEvents()

            assert str(textarea.property("text")) == "Line one updated"
            assert bool(apply_button.property("enabled"))
            assert bool(reset_button.property("enabled"))

            app.sendEvent(
                textarea,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
            )
            app.sendEvent(
                textarea,
                QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
            )
            app.processEvents()

            assert str(textarea.property("text")) == "Line one"
            assert not bool(apply_button.property("enabled"))
            assert commits == []

            textarea.forceActiveFocus()
            app.processEvents()
            textarea.setProperty("text", "Line one again")
            app.processEvents()
            app.sendEvent(
                textarea,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier),
            )
            app.sendEvent(
                textarea,
                QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier),
            )
            app.processEvents()

            assert commits == [("node_inline_test", "caption", "Line one again")]
            window.close()
            host.setParentItem(None)
            host.deleteLater()
            window.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_inline_path_browse_routes_by_node_id_and_commits_selected_path(self) -> None:
        self._run_qml_probe(
            "inline-path-browse",
            """
            host = probe.findChild(QObject, "probeHost")
            canvas_proxy = probe.findChild(QObject, "canvasProxy")
            browse_button = named_item(probe, "graphNodeInlinePathBrowseButton", "source_path")

            interactions = []
            commits = []
            host.surfaceControlInteractionStarted.connect(lambda node_id: interactions.append(node_id))
            host.inlinePropertyCommitted.connect(lambda node_id, key, value: commits.append((node_id, key, value)))
            canvas_proxy.setProperty("browseResultPath", "/tmp/selected-path.png")

            window = QQuickWindow()
            window.resize(520, 420)
            host.setParentItem(window.contentItem())
            window.show()
            app.processEvents()

            QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, item_scene_point(browse_button))
            app.processEvents()

            browse_call = variant_value(canvas_proxy.property("lastBrowseCall"))
            assert browse_call["nodeId"] == "node_inline_test"
            assert browse_call["key"] == "source_path"
            assert browse_call["currentPath"] == "/fixtures/original.txt"
            assert interactions == ["node_inline_test"]
            assert commits == [("node_inline_test", "source_path", "/tmp/selected-path.png")]

            window.close()
            host.setParentItem(None)
            host.deleteLater()
            window.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )


if __name__ == "__main__":
    unittest.main()
