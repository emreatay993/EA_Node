from __future__ import annotations

import unittest

from tests.graph_surface_pointer_regression import (
    QML_POINTER_REGRESSION_HELPERS,
    run_qml_probe,
)


class GraphSurfaceInputInlineTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            from pathlib import Path
            import textwrap

            from PyQt6.QtCore import QEvent, QObject, Qt, QUrl, pyqtProperty
            from PyQt6.QtGui import QKeyEvent
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

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

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
            engine.rootContext().setContextProperty("themeBridge", ThemeBridgeStub())
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridgeStub())

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
                                    "status_chip_text": "Stored",
                                    "status_chip_variant": "stored",
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
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

    def _run_comment_backdrop_probe(self, label: str, body: str) -> None:
        run_qml_probe(
            self,
            label,
            """
            from pathlib import Path
            import textwrap

            from PyQt6.QtCore import QEvent, QObject, Qt, QUrl, pyqtProperty
            from PyQt6.QtGui import QKeyEvent
            from PyQt6.QtQml import QQmlComponent, QQmlEngine
            from PyQt6.QtWidgets import QApplication

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

            app = QApplication.instance() or QApplication([])
            engine = QQmlEngine()
            engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
            engine.rootContext().setContextProperty("themeBridge", ThemeBridgeStub())
            engine.rootContext().setContextProperty("graphThemeBridge", GraphThemeBridgeStub())

            repo_root = Path.cwd()

            probe_qml = textwrap.dedent(
                '''
                import QtQuick 2.15
                import "ea_node_editor/ui_qml/components/graph" as GraphComponents

                Item {
                    id: root
                    width: 520
                    height: 400

                    QtObject {
                        id: sceneBridgeProxy
                        property var selected_node_lookup: ({
                            "node_comment_backdrop_inline_test": true
                        })
                    }

                    Item {
                        id: canvasProxy
                        objectName: "canvasProxy"
                        property var sceneBridge: sceneBridgeProxy

                        function browseNodePropertyPath(nodeId, key, currentPath) {
                            return currentPath;
                        }
                    }

                    function nodePayload() {
                        return {
                            "node_id": "node_comment_backdrop_inline_test",
                            "type_id": "passive.annotation.comment_backdrop",
                            "title": "Comment Backdrop",
                            "x": 72.0,
                            "y": 64.0,
                            "width": 340.0,
                            "height": 260.0,
                            "accent": "#2F89FF",
                            "collapsed": false,
                            "selected": true,
                            "runtime_behavior": "passive",
                            "surface_family": "comment_backdrop",
                            "surface_variant": "comment_backdrop",
                            "surface_metrics": {
                                "default_width": 320.0,
                                "default_height": 260.0,
                                "min_width": 220.0,
                                "min_height": 180.0,
                                "collapsed_width": 180.0,
                                "collapsed_height": 38.0,
                                "header_height": 32.0,
                                "header_top_margin": 8.0,
                                "body_top": 52.0,
                                "body_height": 190.0,
                                "port_top": 242.0,
                                "port_height": 0.0,
                                "port_center_offset": 0.0,
                                "port_side_margin": 0.0,
                                "port_dot_radius": 0.0,
                                "resize_handle_size": 16.0,
                                "title_top": 8.0,
                                "title_height": 24.0,
                                "title_left_margin": 12.0,
                                "title_right_margin": 12.0,
                                "title_centered": false,
                                "body_left_margin": 18.0,
                                "body_right_margin": 18.0,
                                "body_bottom_margin": 18.0,
                                "show_header_background": true,
                                "show_accent_bar": true,
                                "use_host_chrome": true
                            },
                            "visual_style": {},
                            "can_enter_scope": false,
                            "ports": [],
                            "properties": {
                                "title": "Comment Backdrop",
                                "body": "Grouped note"
                            }
                        };
                    }

                    GraphComponents.GraphNodeHost {
                        id: host
                        objectName: "probeHost"
                        nodeData: nodePayload()
                        canvasItem: canvasProxy
                        surfaceVariantOverride: "comment_backdrop_input_overlay"
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
            """,
            QML_POINTER_REGRESSION_HELPERS,
            body,
        )

    def test_inline_layer_publishes_control_scoped_rects_for_path_and_textarea_editors(self) -> None:
        self._run_qml_probe(
            "inline-rects",
            """
            host = probe.findChild(QObject, "probeHost")
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 4, embedded_rects

            widths = [rect_field(rect, "width") for rect in embedded_rects]
            heights = [rect_field(rect, "height") for rect in embedded_rects]
            ys = [rect_field(rect, "y") for rect in embedded_rects]

            assert widths[0] > 60.0, (widths, heights, ys, embedded_rects)
            assert heights[0] >= 18.0, (widths, heights, ys, embedded_rects)
            assert widths[1] > 120.0, (widths, heights, ys, embedded_rects)
            assert heights[1] > 60.0, (widths, heights, ys, embedded_rects)
            assert widths[2] < 90.0, (widths, heights, ys, embedded_rects)
            assert widths[3] < 90.0, (widths, heights, ys, embedded_rects)
            assert ys[0] < ys[1] < ys[2], (widths, heights, ys, embedded_rects)
            assert max(ys[2:]) - min(ys[2:]) <= 1.0, (widths, heights, ys, embedded_rects)
            """,
        )

    def test_graph_typography_inline_edge_inline_labels_and_status_chips_follow_shared_roles(self) -> None:
        self._run_qml_probe(
            "inline-typography",
            """
            host = probe.findChild(QObject, "probeHost")
            typography = host.findChild(QObject, "graphSharedTypography")
            source_label = named_item(probe, "graphNodeInlinePropertyLabel", "source_path")
            status_chip_label = named_item(probe, "graphNodeInlineStatusChipLabel", "source_path")

            assert typography is not None
            assert source_label.property("font").pixelSize() == int(typography.property("inlinePropertyPixelSize"))
            assert source_label.property("font").weight() == int(typography.property("inlinePropertyFontWeight"))
            assert status_chip_label.property("font").pixelSize() == int(typography.property("badgePixelSize"))
            assert status_chip_label.property("font").weight() == int(typography.property("badgeFontWeight"))

            host.setProperty("graphLabelPixelSize", 16)
            app.processEvents()

            assert int(typography.property("inlinePropertyPixelSize")) == 16
            assert int(typography.property("badgePixelSize")) == 15
            assert source_label.property("font").pixelSize() == 16
            assert source_label.property("font").weight() == int(typography.property("inlinePropertyFontWeight"))
            assert status_chip_label.property("font").pixelSize() == 15
            assert status_chip_label.property("font").weight() == int(typography.property("badgeFontWeight"))
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

            window = attach_host_to_window(host, 520, 420)

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
            dispose_host_window(host, window)
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

            window = attach_host_to_window(host, 520, 420)

            mouse_click(window, item_scene_point(browse_button))

            browse_call = variant_value(canvas_proxy.property("lastBrowseCall"))
            assert browse_call["nodeId"] == "node_inline_test"
            assert browse_call["key"] == "source_path"
            assert browse_call["currentPath"] == "/fixtures/original.txt"
            assert interactions == ["node_inline_test"]
            assert commits == [("node_inline_test", "source_path", "/tmp/selected-path.png")]

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_comment_backdrop_inline_body_editor_publishes_scoped_rects_and_commit_shortcuts(self) -> None:
        self._run_comment_backdrop_probe(
            "comment-backdrop-inline-textarea",
            """
            host = probe.findChild(QObject, "probeHost")
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            editor = named_item(probe, "graphCommentBackdropBodyEditor")
            textarea = named_item(probe, "graphCommentBackdropBodyEditorField", "body")
            apply_button = named_item(probe, "graphCommentBackdropBodyApplyButton", "body")
            reset_button = named_item(probe, "graphCommentBackdropBodyResetButton", "body")
            assert loader is not None
            assert editor is not None

            textarea_font = textarea.property("font")
            assert textarea_font.pixelSize() == int(round(float(host.property("passiveFontPixelSize"))))
            assert not textarea_font.bold()
            assert not bool(editor.property("showActionButtons"))
            assert not bool(apply_button.property("visible"))
            assert not bool(reset_button.property("visible"))

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 1, embedded_rects
            assert rect_field(embedded_rects[0], "width") > 180.0, embedded_rects

            commits = []
            host.inlinePropertyCommitted.connect(lambda node_id, key, value: commits.append((node_id, key, value)))

            window = attach_host_to_window(host, 560, 440)

            textarea.forceActiveFocus()
            app.processEvents()
            textarea.setProperty("text", "Grouped note draft")
            app.processEvents()

            assert not bool(apply_button.property("enabled"))
            assert not bool(reset_button.property("enabled"))

            app.sendEvent(
                textarea,
                QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
            )
            app.sendEvent(
                textarea,
                QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier),
            )
            app.processEvents()

            assert str(textarea.property("text")) == "Grouped note"
            assert commits == []

            textarea.forceActiveFocus()
            app.processEvents()
            textarea.setProperty("text", "Grouped note committed")
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

            assert commits == [("node_comment_backdrop_inline_test", "body", "Grouped note committed")]
            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_comment_backdrop_body_editor_yields_pointer_routing_inside_controls(self) -> None:
        self._run_comment_backdrop_probe(
            "comment-backdrop-pointer-routing",
            """
            host = probe.findChild(QObject, "probeHost")
            loader = host.findChild(QObject, "graphNodeSurfaceLoader")
            assert loader is not None

            embedded_rects = variant_list(loader.property("embeddedInteractiveRects"))
            assert len(embedded_rects) == 1, embedded_rects
            field_rect = embedded_rects[0]

            window = attach_host_to_window(host, 560, 440)

            control_point = host_scene_point(
                host,
                rect_field(field_rect, "x") + 12.0,
                rect_field(field_rect, "y") + 14.0,
            )
            body_local_x = rect_field(field_rect, "x") - 10.0
            body_local_y = rect_field(field_rect, "y") + 14.0
            body_point = host_scene_point(host, body_local_x, body_local_y)

            assert_host_pointer_routing(
                host,
                window,
                control_point,
                body_point,
                "node_comment_backdrop_inline_test",
                expected_body_local=(body_local_x, body_local_y),
            )

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_locked_input_rows_publish_padlock_contract_without_changing_row_geometry(self) -> None:
        self._run_qml_probe(
            "locked-input-row-contract",
            """
            host = probe.findChild(QObject, "probeHost")
            payload = variant_value(host.property("nodeData"))
            payload["properties"] = {
                "message": "Line one",
                "count": 7,
            }
            payload["ports"] = [
                {
                    "key": "message",
                    "label": "Message",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "str",
                    "connected": False,
                    "locked": True,
                    "allow_multiple_connections": False,
                },
                {
                    "key": "count",
                    "label": "Count",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "int",
                    "connected": False,
                    "locked": False,
                    "allow_multiple_connections": False,
                },
                {
                    "key": "result",
                    "label": "Result",
                    "direction": "out",
                    "kind": "data",
                    "data_type": "str",
                    "connected": False,
                    "allow_multiple_connections": False,
                },
            ]
            payload["inline_properties"] = [
                {
                    "key": "message",
                    "label": "Message",
                    "inline_editor": "text",
                    "value": "Line one",
                    "overridden_by_input": False,
                    "input_port_label": "message",
                },
                {
                    "key": "count",
                    "label": "Count",
                    "inline_editor": "number",
                    "value": 7,
                    "overridden_by_input": False,
                    "input_port_label": "count",
                },
            ]
            host.setProperty("nodeData", payload)
            app.processEvents()

            locked_row = named_item(probe, "graphNodeInputPortRow", "message")
            unlocked_row = named_item(probe, "graphNodeInputPortRow", "count")
            locked_tint = named_item(probe, "graphNodeInputPortLockedRowTint", "message")
            unlocked_tint = named_item(probe, "graphNodeInputPortLockedRowTint", "count")
            locked_label = named_item(probe, "graphNodeInputPortLabel", "message")
            unlocked_label = named_item(probe, "graphNodeInputPortLabel", "count")
            locked_padlock = named_item(probe, "graphNodeInputPortPadlock", "message")
            unlocked_padlock = named_item(probe, "graphNodeInputPortPadlock", "count")
            lock_toggle = named_item(probe, "graphNodeInputPortLockToggleMouseArea", "message")

            assert bool(locked_row.property("lockableState")) is True
            assert bool(locked_row.property("lockedState")) is True
            assert bool(unlocked_row.property("lockableState")) is True
            assert bool(unlocked_row.property("lockedState")) is False
            assert abs(float(locked_row.height()) - float(unlocked_row.height())) < 0.5
            assert bool(locked_tint.property("visible")) is True
            assert bool(unlocked_tint.property("visible")) is False
            assert float(locked_label.property("opacity")) < float(unlocked_label.property("opacity"))
            assert bool(locked_padlock.property("visible")) is True
            assert bool(unlocked_padlock.property("visible")) is True
            assert float(locked_padlock.property("opacity")) > float(unlocked_padlock.property("opacity"))
            assert bool(lock_toggle.property("visible")) is True
            """,
        )


if __name__ == "__main__":
    unittest.main()
