from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]


class GraphSurfaceInputContractTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        script = textwrap.dedent(
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtQuick import QQuickItem
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

            def variant_value(value):
                return value.toVariant() if hasattr(value, "toVariant") else value

            def variant_list(value):
                normalized = variant_value(value)
                if normalized is None:
                    return []
                return list(normalized)
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
            details = "\\n".join(
                part for part in (result.stdout.strip(), result.stderr.strip()) if part
            )
            self.fail(f"{label} probe failed with exit code {result.returncode}\\n{details}")

    def test_surface_loader_forwards_embedded_interactive_rects_for_inline_properties(self) -> None:
        self._run_qml_probe(
            "loader-embedded-rects",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))

            assert len(embedded_rects) == 1
            assert rect_field(embedded_rects[0], "x") >= 8.0
            assert rect_field(embedded_rects[0], "y") >= 30.0
            assert rect_field(embedded_rects[0], "width") > 150.0
            assert rect_field(embedded_rects[0], "height") >= 26.0
            """,
        )

    def test_host_body_interactions_yield_inside_embedded_rects_but_still_work_adjacent_to_them(self) -> None:
        self._run_qml_probe(
            "embedded-rect-hit-testing",
            """
            from PyQt6.QtCore import QPoint, QPointF, Qt
            from PyQt6.QtQuick import QQuickWindow
            from PyQt6.QtTest import QTest

            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 1
            row_rect = embedded_rects[0]

            window = QQuickWindow()
            window.resize(480, 360)
            host.setParentItem(window.contentItem())
            window.show()
            app.processEvents()

            inside_point = host.mapToScene(
                QPointF(rect_field(row_rect, "x") + 8.0, rect_field(row_rect, "y") + rect_field(row_rect, "height") * 0.5)
            )
            body_point = host.mapToScene(QPointF(rect_field(row_rect, "x") - 4.0, rect_field(row_rect, "y") + 6.0))

            clicked = []
            opened = []
            contexts = []
            host.nodeClicked.connect(lambda node_id, additive: clicked.append((node_id, additive)))
            host.nodeOpenRequested.connect(lambda node_id: opened.append(node_id))
            host.nodeContextRequested.connect(lambda node_id, local_x, local_y: contexts.append((node_id, local_x, local_y)))

            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(inside_point.x()), round(inside_point.y())),
            )
            QTest.mouseDClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(inside_point.x()), round(inside_point.y())),
            )
            QTest.mouseClick(
                window,
                Qt.MouseButton.RightButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(inside_point.x()), round(inside_point.y())),
            )
            app.processEvents()

            assert clicked == []
            assert opened == []
            assert contexts == []

            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(body_point.x()), round(body_point.y())),
            )
            QTest.mouseDClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(body_point.x()), round(body_point.y())),
            )
            QTest.mouseClick(
                window,
                Qt.MouseButton.RightButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(body_point.x()), round(body_point.y())),
            )
            app.processEvents()

            assert len(clicked) >= 1
            assert all(entry == ("node_surface_contract_test", False) for entry in clicked)
            assert opened == ["node_surface_contract_test"]
            assert len(contexts) == 1
            assert contexts[0][0] == "node_surface_contract_test"

            window.close()
            host.setParentItem(None)
            host.deleteLater()
            window.deleteLater()
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
            from PyQt6.QtCore import QPoint, QPointF
            from PyQt6.QtGui import QColor, QImage
            from PyQt6.QtQuick import QQuickWindow
            from PyQt6.QtTest import QTest

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

                window = QQuickWindow()
                window.resize(480, 360)
                host.setParentItem(window.contentItem())
                window.show()
                app.processEvents()

                hover_point = host.mapToScene(QPointF(80.0, 44.0))
                QTest.mouseMove(window, QPoint(round(hover_point.x()), round(hover_point.y())))
                for _index in range(5):
                    app.processEvents()

                assert len(variant_list(loader.property("embeddedInteractiveRects"))) == 1
                assert not bool(loader.property("blocksHostInteraction"))
                assert bool(drag_area.property("enabled"))

                surface.setProperty("cropModeActive", True)
                app.processEvents()

                assert len(variant_list(loader.property("embeddedInteractiveRects"))) == 0
                assert bool(loader.property("blocksHostInteraction"))
                assert not bool(drag_area.property("enabled"))

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
