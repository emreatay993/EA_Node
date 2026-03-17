from __future__ import annotations

import unittest

from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    run_qml_probe,
)


class PassiveGraphSurfaceHostTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            from pathlib import Path

            from PyQt6.QtCore import QObject, QUrl
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui.media_preview_provider import (
                LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
                LocalMediaPreviewImageProvider,
            )
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
            from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
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
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

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

    def test_standard_host_keeps_port_labels_tied_to_port_handles(self) -> None:
        self._run_qml_probe(
            "port-label-geometry-host",
            """
            payload = node_payload()
            payload["width"] = 320.0
            payload["surface_metrics"]["default_width"] = 320.0
            payload["ports"][0]["label"] = "in"
            payload["ports"][1]["label"] = "out"

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            input_dot = named_child_items(host, "graphNodeInputPortDot")[0]
            output_dot = named_child_items(host, "graphNodeOutputPortDot")[0]
            input_label = named_child_items(host, "graphNodeInputPortLabel")[0]
            output_label = named_child_items(host, "graphNodeOutputPortLabel")[0]

            gap = float(host.property("_portLabelGap"))
            max_width = float(host.property("_portLabelMaxWidth"))
            output_implicit_width = float(output_label.property("implicitWidth"))

            assert abs(input_label.x() - (input_dot.x() + input_dot.width() + gap)) < 0.5
            assert abs((output_label.x() + output_label.width()) - (output_dot.x() - gap)) < 0.5
            assert output_label.width() < max_width
            assert abs(output_label.width() - output_implicit_width) < 0.5
            """,
        )

    def test_graph_node_host_routes_body_click_open_and_context_from_below_surface_layer(self) -> None:
        self._run_qml_probe(
            "host-body-interactions-below-surface",
            """
            from PyQt6.QtQml import QQmlProperty

            payload = node_payload()
            payload["inline_properties"] = []
            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            drag_area = host.findChild(QObject, "graphNodeDragArea")

            assert loader is not None
            assert drag_area is not None

            surface_layer = loader.parentItem()
            assert surface_layer is not None
            assert float(surface_layer.property("z")) > float(drag_area.property("z"))
            assert abs(float(drag_area.property("width")) - float(host.property("width"))) < 0.5
            assert abs(float(drag_area.property("height")) - float(host.property("height"))) < 0.5

            drag_target = QQmlProperty.read(drag_area, "drag.target")
            assert drag_target is not None
            assert drag_target.property("objectName") == "graphNodeCard"
            assert drag_target.property("nodeData")["node_id"] == "node_surface_host_test"

            window = attach_host_to_window(host)
            body_point = host_scene_point(host, 105.0, 44.0)
            events = host_pointer_events(host)

            mouse_click(window, body_point)
            assert events["clicked"] == [("node_surface_host_test", False)]

            mouse_double_click(window, body_point)
            assert events["opened"] == ["node_surface_host_test"]

            mouse_click(window, body_point, Qt.MouseButton.RightButton)
            assert len(events["contexts"]) == 1
            assert events["contexts"][0][0] == "node_surface_host_test"
            assert abs(float(events["contexts"][0][1]) - 105.0) < 0.5
            assert abs(float(events["contexts"][0][2]) - 44.0) < 0.5

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
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

    def test_graph_canvas_drag_moves_all_selected_nodes_together(self) -> None:
        self._run_qml_probe(
            "graph-canvas-multi-drag-selection",
            """
            model = GraphModel()
            registry = build_default_registry()
            workspace_id = model.active_workspace.workspace_id
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, workspace_id)
            first_node_id = scene.add_node_from_type("core.logger", 120.0, 140.0)
            second_node_id = scene.add_node_from_type("core.start", 320.0, 180.0)
            scene.select_node(first_node_id, False)
            scene.select_node(second_node_id, True)

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
            node_cards = {
                card.property("nodeData")["node_id"]: card
                for card in named_child_items(canvas, "graphNodeCard")
            }
            assert set(scene.selected_node_lookup) == {first_node_id, second_node_id}
            drag_node_ids = canvas.dragNodeIdsForAnchor(second_node_id)
            if hasattr(drag_node_ids, "toVariant"):
                drag_node_ids = drag_node_ids.toVariant()
            assert list(drag_node_ids) == [second_node_id, first_node_id]

            before = {item["node_id"]: (item["x"], item["y"]) for item in scene.nodes_model}
            node_cards[second_node_id].dragOffsetChanged.emit(second_node_id, 25.0, 15.0)
            app.processEvents()
            assert canvas.liveDragDxForNode(first_node_id) == 25.0
            assert canvas.liveDragDyForNode(first_node_id) == 15.0
            assert canvas.liveDragDxForNode(second_node_id) == 25.0
            assert canvas.liveDragDyForNode(second_node_id) == 15.0

            node_cards[second_node_id].dragFinished.emit(second_node_id, 345.0, 195.0, True)
            app.processEvents()
            after = {item["node_id"]: (item["x"], item["y"]) for item in scene.nodes_model}

            assert canvas.liveDragDxForNode(first_node_id) == 0.0
            assert canvas.liveDragDyForNode(first_node_id) == 0.0
            assert canvas.liveDragDxForNode(second_node_id) == 0.0
            assert canvas.liveDragDyForNode(second_node_id) == 0.0
            assert after[first_node_id] == (before[first_node_id][0] + 25.0, before[first_node_id][1] + 15.0)
            assert after[second_node_id] == (before[second_node_id][0] + 25.0, before[second_node_id][1] + 15.0)

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
            from tests.qt_wait import wait_for_condition_or_raise

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

            wait_for_condition_or_raise(
                lambda: (
                    not bool(canvas.property("interactionActive"))
                    and bool(canvas.property("highQualityRendering"))
                    and bool(shadow_item.property("visible"))
                ),
                timeout_ms=190,
                app=app,
                timeout_message="Timed out waiting for wheel-zoom rendering quality to recover.",
            )
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
                embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))

                assert bool(host.property("surfaceInteractionLocked"))
                assert bool(loader.property("blocksHostInteraction"))
                assert host.findChild(QObject, "graphNodeSurfaceHoverActionButton") is None
                assert len(embedded_rects) == 10
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
                assert float(handle_lookup["top_left"].property("width")) > 12.0
                assert float(handle_lookup["top_left"].property("height")) > 12.0
                assert handle_lookup["top_left"].property("cursorShape") == Qt.CursorShape.SizeFDiagCursor
                assert handle_lookup["top_right"].property("cursorShape") == Qt.CursorShape.SizeBDiagCursor
                assert handle_lookup["top"].property("cursorShape") == Qt.CursorShape.SizeVerCursor
                assert handle_lookup["left"].property("cursorShape") == Qt.CursorShape.SizeHorCursor
            """,
        )

    def test_media_surface_publishes_direct_crop_button_rect_without_host_hover_proxy(self) -> None:
        self._run_qml_probe(
            "media-direct-crop-button",
            """
            import tempfile
            from PyQt6.QtGui import QColor, QImage

            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "media-hover-action.png"
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
                crop_button = host.findChild(QObject, "graphNodeMediaCropButton")
                assert surface is not None
                assert loader is not None
                assert crop_button is not None

                for _index in range(40):
                    app.processEvents()
                    if str(surface.property("previewState")) == "ready":
                        break
                assert str(surface.property("previewState")) == "ready"

                window = attach_host_to_window(host)

                hover_host_local_point(window, host, 80.0, 44.0)

                embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
                crop_button_rect = crop_button.property("interactiveRect")

                assert host.findChild(QObject, "graphNodeSurfaceHoverActionButton") is None
                assert loader.metaObject().indexOfProperty("hoverActionHitRect") == -1
                assert surface.metaObject().indexOfProperty("hoverActionHitRect") == -1
                assert bool(crop_button.property("visible"))
                assert len(embedded_rects) == 1
                assert abs(rect_field(embedded_rects[0], "x") - rect_field(crop_button_rect, "x")) < 0.5
                assert abs(rect_field(embedded_rects[0], "y") - rect_field(crop_button_rect, "y")) < 0.5
                assert abs(rect_field(embedded_rects[0], "width") - rect_field(crop_button_rect, "width")) < 0.5
                assert abs(rect_field(embedded_rects[0], "height") - rect_field(crop_button_rect, "height")) < 0.5

                dispose_host_window(host, window)
                engine.deleteLater()
                app.processEvents()
            """,
        )
