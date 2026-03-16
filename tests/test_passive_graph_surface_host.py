from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

_REPO_ROOT = Path(__file__).resolve().parents[1]


class PassiveGraphSurfaceHostTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        script = textwrap.dedent(
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtQuick import QQuickItem
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.rootContext().setContextProperty("themeBridge", ThemeBridge(theme_id="stitch_dark"))
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridge(theme_id="graph_stitch_dark"))

            repo_root = Path.cwd()
            components_dir = repo_root / "ea_node_editor" / "ui_qml" / "components"
            graph_canvas_qml_path = components_dir / "GraphCanvas.qml"
            graph_node_host_qml_path = components_dir / "graph" / "GraphNodeHost.qml"
            node_card_qml_path = components_dir / "graph" / "NodeCard.qml"

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
                    "node_id": "node_surface_host_test",
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

            def named_child_items(root, object_name):
                matches = []

                def visit(item):
                    if not isinstance(item, QQuickItem):
                        return
                    if item.objectName() == object_name:
                        matches.append(item)
                    for child in item.childItems():
                        visit(child)

                visit(root)
                return matches
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
            details = "\n".join(
                part for part in (result.stdout.strip(), result.stderr.strip()) if part
            )
            self.fail(f"{label} probe failed with exit code {result.returncode}\n{details}")

    def test_graph_node_host_loads_standard_surface_for_standard_nodes(self) -> None:
        self._run_qml_probe(
            "standard-host",
            """
            host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            assert host.objectName() == "graphNodeCard"
            assert host.property("surfaceFamily") == "standard"
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "standard"
            assert host.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_node_host_falls_back_to_standard_surface_for_unknown_family(self) -> None:
        self._run_qml_probe(
            "fallback-host",
            """
            host = create_component(
                graph_node_host_qml_path,
                {"nodeData": node_payload(surface_family="mystery", surface_variant="sticky_note")},
            )
            assert host.property("surfaceFamily") == "mystery"
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None
            assert loader.property("loadedSurfaceKey") == "standard"
            assert host.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_node_host_uses_curve_rendering_for_node_text(self) -> None:
        self._run_qml_probe(
            "curve-rendering-host",
            """
            standard_host = create_component(graph_node_host_qml_path, {"nodeData": node_payload()})
            expected_render_type = standard_host.property("nodeTextRenderType")
            title_item = standard_host.findChild(QObject, "graphNodeTitle")
            input_labels = named_child_items(standard_host, "graphNodeInputPortLabel")
            assert title_item is not None
            assert len(input_labels) >= 1
            assert title_item.property("effectiveRenderType") == expected_render_type
            assert input_labels[0].property("effectiveRenderType") == expected_render_type

            annotation_payload = node_payload(surface_family="annotation", surface_variant="sticky_note")
            annotation_payload["runtime_behavior"] = "passive"
            annotation_payload["properties"] = {"body": "Sticky note"}
            annotation_host = create_component(graph_node_host_qml_path, {"nodeData": annotation_payload})
            annotation_text = annotation_host.findChild(QObject, "graphNodeAnnotationBodyText")
            assert annotation_text is not None
            assert annotation_text.property("effectiveRenderType") == annotation_host.property("nodeTextRenderType")

            planning_payload = node_payload(surface_family="planning", surface_variant="task_card")
            planning_payload["runtime_behavior"] = "passive"
            planning_payload["properties"] = {
                "body": "Follow up with render pass",
                "status": "in progress",
                "owner": "Alex",
                "due_date": "Tomorrow",
            }
            planning_host = create_component(graph_node_host_qml_path, {"nodeData": planning_payload})
            planning_text = planning_host.findChild(QObject, "graphNodePlanningBodyText")
            assert planning_text is not None
            assert planning_text.property("effectiveRenderType") == planning_host.property("nodeTextRenderType")

            media_payload = node_payload(surface_family="media", surface_variant="image_panel")
            media_payload["runtime_behavior"] = "passive"
            media_payload["properties"] = {"caption": "Preview caption"}
            media_host = create_component(graph_node_host_qml_path, {"nodeData": media_payload})
            caption_text = media_host.findChild(QObject, "graphNodeMediaCaption")
            assert caption_text is not None
            assert caption_text.property("effectiveRenderType") == media_host.property("nodeTextRenderType")
            """,
        )

    def test_node_card_wrapper_preserves_standard_host_contract(self) -> None:
        self._run_qml_probe(
            "node-card-wrapper",
            """
            node_card = create_component(
                node_card_qml_path,
                {"nodeData": node_payload(surface_family="annotation", surface_variant="sticky_note")},
            )
            assert node_card.objectName() == "graphNodeCard"
            assert node_card.property("surfaceFamily") == "standard"
            assert node_card.findChild(QObject, "graphNodeSurfaceLoader") is not None
            assert node_card.findChild(QObject, "graphNodeStandardSurface") is not None
            """,
        )

    def test_graph_canvas_keeps_graph_node_card_discoverability_through_host_delegate(self) -> None:
        self._run_qml_probe(
            "graph-canvas-host",
            """
            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) >= 1
            assert node_cards[0].findChild(QObject, "graphNodeStandardSurface") is not None
            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_keeps_live_drag_preview_continuous_when_snap_to_grid_is_enabled(self) -> None:
        self._run_qml_probe(
            "graph-canvas-snap-live-preview",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSignal

            class MainWindowBridge(QObject):
                snap_to_grid_changed = pyqtSignal()
                graphics_preferences_changed = pyqtSignal()

                @pyqtProperty(bool, notify=snap_to_grid_changed)
                def snap_to_grid_enabled(self):
                    return True

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_show_grid(self):
                    return True

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_show_minimap(self):
                    return True

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_node_shadow(self):
                    return True

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_strength(self):
                    return 70

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_softness(self):
                    return 50

                @pyqtProperty(int, notify=graphics_preferences_changed)
                def graphics_shadow_offset(self):
                    return 4

                @pyqtProperty(bool, notify=graphics_preferences_changed)
                def graphics_minimap_expanded(self):
                    return True

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)
            node_id = scene.nodes_model[0]["node_id"]

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)
            main_window_bridge = MainWindowBridge()

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "mainWindowBridge": main_window_bridge,
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]

            assert canvas.snapToGridEnabled() is True
            node_card.dragOffsetChanged.emit(node_id, 11.0, 9.0)
            app.processEvents()
            assert canvas.liveDragDxForNode(node_id) == 11.0
            assert canvas.liveDragDyForNode(node_id) == 9.0

            node_card.dragFinished.emit(node_id, 131.0, 149.0, True)
            app.processEvents()
            assert canvas.liveDragDxForNode(node_id) == 0.0
            assert canvas.liveDragDyForNode(node_id) == 0.0
            assert scene.nodes_model[0]["x"] == 140.0
            assert scene.nodes_model[0]["y"] == 140.0

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_temporarily_simplifies_node_shadow_during_wheel_zoom(self) -> None:
        self._run_qml_probe(
            "graph-canvas-shadow-quality",
            """
            from PyQt6.QtTest import QTest

            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            scene.add_node_from_type("core.logger", 120.0, 140.0)

            view = ViewportBridge()
            view.set_viewport_size(1280.0, 720.0)

            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "sceneBridge": scene,
                    "viewBridge": view,
                    "width": 1280.0,
                    "height": 720.0,
                },
            )
            node_cards = named_child_items(canvas, "graphNodeCard")
            assert len(node_cards) == 1
            node_card = node_cards[0]
            shadow_item = node_card.findChild(QObject, "graphNodeShadow")
            assert shadow_item is not None
            assert bool(shadow_item.property("visible"))
            assert not bool(canvas.property("interactionActive"))
            assert bool(canvas.property("highQualityRendering"))

            applied = canvas.applyWheelZoom(
                {"x": 640.0, "y": 360.0, "angleDelta": {"y": 120}, "inverted": False}
            )
            assert applied is True
            app.processEvents()
            assert bool(canvas.property("interactionActive"))
            assert not bool(canvas.property("highQualityRendering"))
            assert not bool(shadow_item.property("visible"))

            QTest.qWait(190)
            app.processEvents()
            assert not bool(canvas.property("interactionActive"))
            assert bool(canvas.property("highQualityRendering"))
            assert bool(shadow_item.property("visible"))

            canvas.deleteLater()
            app.processEvents()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_media_crop_mode_locks_host_drag_resize_and_ports(self) -> None:
        self._run_qml_probe(
            "media-host-lock",
            """
            import tempfile
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-lock.png"
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
                assert surface is not None
                assert loader is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break

                surface.setProperty("cropModeActive", True)
                app.processEvents()

                drag_area = host.findChild(QObject, "graphNodeDragArea")
                resize_area = host.findChild(QObject, "graphNodeResizeDragArea")
                input_areas = named_child_items(host, "graphNodeInputPortMouseArea")
                output_areas = named_child_items(host, "graphNodeOutputPortMouseArea")

                assert bool(host.property("surfaceInteractionLocked"))
                assert bool(loader.property("blocksHostInteraction"))
                assert drag_area is not None
                assert resize_area is not None
                assert not bool(drag_area.property("enabled"))
                assert not bool(resize_area.property("enabled"))
                assert len(input_areas) >= 1
                assert len(output_areas) >= 1
                assert not bool(input_areas[0].property("enabled"))
                assert not bool(output_areas[0].property("enabled"))

                handle_areas = named_child_items(host, "graphNodeMediaCropHandleMouseArea")
                handle_lookup = {
                    str(item.property("handleId")): item
                    for item in handle_areas
                }
                assert len(handle_lookup) == 8
                assert handle_lookup["top_left"].property("cursorShape") == Qt.CursorShape.SizeFDiagCursor
                assert handle_lookup["top_right"].property("cursorShape") == Qt.CursorShape.SizeBDiagCursor
                assert handle_lookup["top"].property("cursorShape") == Qt.CursorShape.SizeVerCursor
                assert handle_lookup["left"].property("cursorShape") == Qt.CursorShape.SizeHorCursor
            """,
        )
