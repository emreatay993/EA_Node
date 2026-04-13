from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.presenters.graph_canvas_presenter import GraphCanvasPresenter
from ea_node_editor.ui.shell.presenters.state import build_default_shell_workspace_ui_state
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from ea_node_editor.ui_qml.graph_geometry.standard_metrics import (
    node_surface_metrics,
    standard_inline_body_height,
    standard_inline_row_height,
    standard_inline_textarea_row_height,
)
from ea_node_editor.ui_qml.graph_surface_metrics import surface_port_local_point
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from tests.graph_surface.environment import GraphSurfaceInputContractTestBase

_REPO_ROOT = Path(__file__).resolve().parents[1]


class GraphSurfaceInputControlsTests(unittest.TestCase):
    def _run_qml_probe(self, label: str, body: str) -> None:
        probe_qml = textwrap.dedent(
            """
            import QtQuick 2.15
            import QtQuick.Controls 2.15
            import "ea_node_editor/ui_qml/components/graph" as GraphComponents
            import "ea_node_editor/ui_qml/components/graph/surface_controls" as GraphSurfaceControls

            Item {
                id: root
                width: 240
                height: 280
                objectName: "probeRoot"

                Item {
                    id: hostItem
                    objectName: "probeHost"
                    x: 10
                    y: 8
                    width: 200
                    height: 120
                    property int graphFontSize: 15
                    property int graphFontWeight: Font.DemiBold
                    property var graphSharedTypography: ({
                        "inlinePropertyPixelSize": graphFontSize,
                        "inlinePropertyFontWeight": graphFontWeight,
                        "badgePixelSize": Math.max(9, graphFontSize - 1),
                        "badgeFontWeight": Font.Bold
                    })
                    property color inlineInputBackgroundColor: "#223344"
                    property color inlineInputBorderColor: "#556677"
                    property color inlineInputTextColor: "#ddeeff"
                    property color selectedOutlineColor: "#66ccff"
                    property color headerTextColor: "#f7f7f0"
                    property color surfaceColor: "#111111"
                    property int nodeTextRenderType: Text.QtRendering

                    Item {
                        id: offsetContainer
                        x: 12
                        y: 18
                        width: 180
                        height: 80

                        Rectangle {
                            id: targetRect
                            objectName: "probeTargetRect"
                            x: 5
                            y: 7
                            width: 40
                            height: 18
                            color: "#00000000"
                        }

                        GraphSurfaceControls.GraphSurfaceInteractiveRegion {
                            id: region
                            objectName: "probeRegion"
                            host: hostItem
                            targetItem: targetRect
                        }

                        GraphSurfaceControls.GraphSurfaceButton {
                            id: button
                            objectName: "probeButton"
                            host: hostItem
                            x: 50
                            y: 10
                            width: 56
                            height: 24
                            text: "Run"
                        }

                        GraphSurfaceControls.GraphSurfaceTextField {
                            id: field
                            objectName: "probeField"
                            host: hostItem
                            x: 10
                            y: 38
                            width: 110
                            height: 24
                            text: "hello"
                        }

                        GraphSurfaceControls.GraphSurfaceComboBox {
                            id: combo
                            objectName: "probeCombo"
                            host: hostItem
                            x: 128
                            y: 38
                            width: 60
                            height: 24
                            model: ["one", "two"]
                            currentIndex: 1
                        }

                        GraphSurfaceControls.GraphSurfaceCheckBox {
                            id: check
                            objectName: "probeCheck"
                            host: hostItem
                            x: 128
                            y: 10
                            width: 44
                            height: 20
                            checked: true
                            text: ""
                        }
                    }
                }

                Item {
                    id: inlineHost
                    objectName: "probeInlineHost"
                    y: 132
                    width: 220
                    height: 132
                    property var inlineProperties: [
                        {
                            "key": "enabled",
                            "label": "Enabled",
                            "inline_editor": "toggle",
                            "value": true,
                            "overridden_by_input": false,
                            "input_port_label": "enabled"
                        },
                        {
                            "key": "mode",
                            "label": "Mode",
                            "inline_editor": "enum",
                            "value": "two",
                            "enum_values": ["one", "two", "three"],
                            "overridden_by_input": false,
                            "input_port_label": "mode"
                        },
                        {
                            "key": "message",
                            "label": "Message",
                            "inline_editor": "text",
                            "value": "hello",
                            "overridden_by_input": false,
                            "input_port_label": "message"
                        },
                        {
                            "key": "count",
                            "label": "Count",
                            "inline_editor": "number",
                            "value": 7,
                            "overridden_by_input": false,
                            "input_port_label": "count"
                        }
                    ]
                    property var nodeData: ({ "node_id": "probe_node" })
                    property int inlineBodyHeight: 132
                    property color inlineRowColor: "#24262c"
                    property color inlineRowBorderColor: "#4a4f5a"
                    property color inlineLabelColor: "#d0d5de"
                    property color inlineDrivenTextColor: "#bdc5d3"
                    property color inlineInputBackgroundColor: "#223344"
                    property color inlineInputBorderColor: "#556677"
                    property color inlineInputTextColor: "#ddeeff"
                    property color selectedOutlineColor: "#66ccff"
                    property color surfaceColor: "#111111"
                    property int nodeTextRenderType: Text.QtRendering
                    property int _inlineRowSpacing: 4
                    property int _inlineRowHeight: 26
                    property var surfaceMetrics: ({
                        "body_left_margin": 8,
                        "body_right_margin": 8,
                        "body_top": 30
                    })

                    signal surfaceControlInteractionStarted(string nodeId)
                    signal inlinePropertyCommitted(string nodeId, string key, var value)

                    function inlineEditorText(modelData) {
                        return String(modelData.value === undefined || modelData.value === null ? "" : modelData.value);
                    }

                    GraphComponents.GraphInlinePropertiesLayer {
                        id: inlineLayer
                        objectName: "probeInlineLayer"
                        anchors.fill: parent
                        host: inlineHost
                    }
                }

                function triggerRegionStart() {
                    region.beginControl();
                }
            }
            """
        )
        script = (
            textwrap.dedent(
                """
                from pathlib import Path

                from PyQt6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt, QUrl
                from PyQt6.QtGui import QColor, QFont
                from PyQt6.QtQml import QQmlComponent, QQmlEngine
                from PyQt6.QtQuick import QQuickItem, QQuickWindow
                from PyQt6.QtTest import QTest
                from PyQt6.QtWidgets import QApplication

                app = QApplication.instance() or QApplication([])
                engine = QQmlEngine()
                repo_root = Path.cwd()

                def load_probe():
                    component = QQmlComponent(engine)
                    component.setData(
                        PROBE_QML.encode("utf-8"),
                        QUrl.fromLocalFile(str(repo_root) + "/"),
                    )
                    if component.status() != QQmlComponent.Status.Ready:
                        errors = "\\n".join(error.toString() for error in component.errors())
                        raise AssertionError("Failed to load probe QML:\\n" + errors)
                    probe = component.create()
                    if probe is None:
                        errors = "\\n".join(error.toString() for error in component.errors())
                        raise AssertionError("Failed to instantiate probe QML:\\n" + errors)
                    app.processEvents()
                    return probe

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

                def color_name(value):
                    color = variant_value(value)
                    if isinstance(color, QColor):
                        return color.name().lower()
                    return QColor(color).name().lower()

                def named_item(root, object_name):
                    found = root.findChild(QObject, object_name)
                    if found is None:
                        raise AssertionError("Missing object: " + object_name)
                    return found

                def attach_window(root):
                    window = QQuickWindow()
                    window.resize(320, 220)
                    if isinstance(root, QQuickItem):
                        root.setParentItem(window.contentItem())
                    window.show()
                    app.processEvents()
                    return window

                PROBE_QML = """
            )
            + repr(probe_qml)
            + textwrap.dedent(
                """
                """
            )
            + "\n"
            + textwrap.dedent(body)
        )
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

    def test_interactive_region_maps_host_space_rect_and_emits_control_start(self) -> None:
        self._run_qml_probe(
            "interactive-region",
            """
            root = load_probe()
            region = named_item(root, "probeRegion")

            starts = []
            region.controlStarted.connect(lambda: starts.append("started"))
            QMetaObject.invokeMethod(region, "beginControl")
            app.processEvents()

            rects = variant_list(region.property("embeddedInteractiveRects"))
            assert len(rects) == 1
            assert abs(rect_field(rects[0], "x") - 17.0) < 0.5
            assert abs(rect_field(rects[0], "y") - 25.0) < 0.5
            assert abs(rect_field(rects[0], "width") - 40.0) < 0.5
            assert abs(rect_field(rects[0], "height") - 18.0) < 0.5
            assert starts == ["started"]
            """,
        )

    def test_button_and_text_field_publish_rects_and_host_styling(self) -> None:
        self._run_qml_probe(
            "button-text-field",
            """
            root = load_probe()
            button = named_item(root, "probeButton")
            field = named_item(root, "probeField")

            button_rects = variant_list(button.property("embeddedInteractiveRects"))
            assert len(button_rects) == 1
            assert abs(rect_field(button_rects[0], "x") - 62.0) < 0.5
            assert abs(rect_field(button_rects[0], "y") - 28.0) < 0.5
            assert color_name(button.property("resolvedForegroundColor")) == "#f7f7f0"
            assert button.property("font").pixelSize() == 15

            field_rects = variant_list(field.property("embeddedInteractiveRects"))
            assert len(field_rects) == 1
            assert abs(rect_field(field_rects[0], "x") - 22.0) < 0.5
            assert abs(rect_field(field_rects[0], "y") - 56.0) < 0.5
            assert color_name(field.property("resolvedBackgroundColor")) == "#223344"
            assert color_name(field.property("resolvedBorderColor")) == "#556677"
            assert field.property("font").pixelSize() == 15
            assert field.property("font").weight() == int(QFont.Weight.DemiBold)

            button_starts = []
            field_starts = []
            button.controlStarted.connect(lambda: button_starts.append("started"))
            field.controlStarted.connect(lambda: field_starts.append("started"))

            window = attach_window(root)
            button_point = button.mapToScene(QPointF(button.width() * 0.5, button.height() * 0.5))
            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(button_point.x()), round(button_point.y())),
            )
            app.processEvents()

            field.forceActiveFocus()
            app.processEvents()

            assert button_starts == ["started"]
            assert field_starts == ["started"]
            assert color_name(field.property("resolvedBorderColor")) == "#66ccff"
            host = named_item(root, "probeHost")
            host.setProperty("graphFontSize", 17)
            app.processEvents()
            assert button.property("font").pixelSize() == 17
            assert field.property("font").pixelSize() == 17
            window.close()
            app.processEvents()
            """,
        )

    def test_combo_box_and_check_box_emit_control_start_and_keep_surface_contracts(self) -> None:
        self._run_qml_probe(
            "combo-checkbox",
            """
            root = load_probe()
            combo = named_item(root, "probeCombo")
            check = named_item(root, "probeCheck")
            host = named_item(root, "probeHost")

            assert color_name(combo.property("resolvedTextColor")) == "#ddeeff"
            assert color_name(combo.property("resolvedBackgroundColor")) == "#223344"
            assert color_name(check.property("resolvedIndicatorBorderColor")) == "#66ccff"
            assert combo.property("font").pixelSize() == 15
            assert combo.property("font").weight() == int(QFont.Weight.DemiBold)
            assert check.property("font").pixelSize() == 15
            assert len(variant_list(combo.property("embeddedInteractiveRects"))) == 1
            assert len(variant_list(check.property("embeddedInteractiveRects"))) == 1

            combo_starts = []
            check_starts = []
            combo.controlStarted.connect(lambda: combo_starts.append("started"))
            check.controlStarted.connect(lambda: check_starts.append("started"))

            window = attach_window(root)
            combo_point = combo.mapToScene(QPointF(combo.width() * 0.5, combo.height() * 0.5))
            check_point = check.mapToScene(QPointF(check.width() * 0.5, check.height() * 0.5))

            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(combo_point.x()), round(combo_point.y())),
            )
            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(round(check_point.x()), round(check_point.y())),
            )
            app.processEvents()

            assert combo_starts == ["started"]
            assert check_starts == ["started"]
            host.setProperty("graphFontSize", 17)
            app.processEvents()
            assert combo.property("font").pixelSize() == 17
            assert check.property("font").pixelSize() == 17
            window.close()
            app.processEvents()
            """,
        )

    def test_inline_properties_layer_publishes_control_scoped_rects_for_core_editors(self) -> None:
        self._run_qml_probe(
            "inline-layer-core-editors",
            """
            root = load_probe()
            inline_layer = named_item(root, "probeInlineLayer")

            rects = variant_list(inline_layer.property("embeddedInteractiveRects"))
            assert len(rects) == 4

            xs = [rect_field(rect, "x") for rect in rects]
            widths = [rect_field(rect, "width") for rect in rects]
            ys = [rect_field(rect, "y") for rect in rects]

            assert all(x > 90.0 for x in xs)
            assert widths[0] < 40.0
            assert widths[1] > 90.0
            assert widths[2] > 90.0
            assert widths[3] > 90.0
            assert ys == sorted(ys)
            """,
        )


class GraphSurfaceInlineMetricTypographyTests(unittest.TestCase):
    def test_standard_inline_surface_metrics_follow_graph_label_size(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("core.logger")

        default_body_height = standard_inline_body_height(spec, graph_label_pixel_size=10)
        large_body_height = standard_inline_body_height(spec, graph_label_pixel_size=16)

        self.assertEqual(standard_inline_row_height(10), 26.0)
        self.assertEqual(standard_inline_textarea_row_height(10), 104.0)
        self.assertEqual(standard_inline_row_height(16), 32.0)
        self.assertEqual(standard_inline_textarea_row_height(16), 128.0)
        self.assertEqual(default_body_height, 64.0)
        self.assertEqual(large_body_height, 76.0)
        self.assertGreater(large_body_height, default_body_height)

        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        node = model.add_node(workspace_id, "core.logger", "Logger", 32.0, 48.0)

        default_metrics = node_surface_metrics(node, spec, graph_label_pixel_size=10)
        large_metrics = node_surface_metrics(node, spec, graph_label_pixel_size=16)
        large_icon_metrics = node_surface_metrics(
            node,
            spec,
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )
        first_input_port_key = next(port.key for port in spec.ports if port.direction == "in")
        baseline_port_point = surface_port_local_point(
            node,
            spec,
            first_input_port_key,
            {node.node_id: node},
            graph_label_pixel_size=16,
        )
        large_icon_port_point = surface_port_local_point(
            node,
            spec,
            first_input_port_key,
            {node.node_id: node},
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )

        self.assertEqual(default_metrics.body_height, 64.0)
        self.assertEqual(large_metrics.body_height, 76.0)
        self.assertGreater(large_metrics.default_height, default_metrics.default_height)
        self.assertEqual(large_icon_metrics.header_height, 54.0)
        self.assertEqual(large_icon_metrics.title_height, 54.0)
        self.assertEqual(large_icon_metrics.body_top - large_metrics.body_top, 30.0)
        self.assertEqual(large_icon_metrics.port_top - large_metrics.port_top, 30.0)
        self.assertEqual(large_icon_metrics.default_height - large_metrics.default_height, 30.0)
        self.assertEqual(large_icon_port_point[1] - baseline_port_point[1], 30.0)

    def test_scene_payload_builder_applies_title_icon_size_to_standard_nodes(self) -> None:
        class _ThemeSource:
            graphics_graph_label_pixel_size = 16
            graphics_node_title_icon_pixel_size = 50

        class _ThemeBridge:
            theme = "stitch_dark"

            def __init__(self, parent: object) -> None:
                self._parent = parent

            def parent(self) -> object:
                return self._parent

        model = GraphModel()
        registry = build_default_registry()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(workspace_id, "core.logger", "Logger", 32.0, 48.0)

        builder = GraphScenePayloadBuilder()
        nodes_payload, backdrop_nodes_payload, _minimap_nodes_payload, _edges_payload = builder.rebuild_partitioned_models(
            model=model,
            registry=registry,
            workspace_id=workspace_id,
            scope_path=(),
            graph_theme_bridge=_ThemeBridge(_ThemeSource()),
        )

        self.assertEqual(len(backdrop_nodes_payload), 0)
        self.assertEqual(len(nodes_payload), 1)
        payload = nodes_payload[0]
        self.assertEqual(payload["surface_metrics"]["header_height"], 54.0)
        self.assertEqual(payload["surface_metrics"]["title_height"], 54.0)
        self.assertEqual(payload["surface_metrics"]["body_top"], 60.0)
        self.assertGreater(payload["height"], 50.0)

    def test_scene_payload_builder_reads_title_icon_size_from_graph_canvas_presenter(self) -> None:
        class _SearchScopeState:
            graphics_minimap_expanded = True
            snap_to_grid_enabled = False

        class _SearchScopeController:
            def set_snap_to_grid_enabled(self, enabled: bool) -> None:
                self.snap_to_grid_enabled = bool(enabled)

            def set_graphics_minimap_expanded(self, expanded: bool) -> None:
                self.graphics_minimap_expanded = bool(expanded)

            def navigate_scope(self, callback):
                return callback()

        class _Host(QObject):
            graphics_preferences_changed = pyqtSignal()
            snap_to_grid_changed = pyqtSignal()

            def __init__(self) -> None:
                super().__init__()
                self.workspace_ui_state = build_default_shell_workspace_ui_state(
                    {
                        "typography": {
                            "graph_label_pixel_size": 16,
                            "graph_node_icon_pixel_size_override": 50,
                        }
                    }
                )
                self.search_scope_state = _SearchScopeState()
                self.search_scope_controller = _SearchScopeController()
                self.app_preferences_controller = object()
                self.scene = object()
                self.workspace_library_controller = object()
                self.graph_canvas_presenter = GraphCanvasPresenter(
                    self,
                    workspace_presenter=object(),
                    library_presenter=object(),
                    inspector_presenter=object(),
                )

            def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
                del message, timeout_ms

            def clear_graph_hint(self) -> None:
                return

        class _ThemeBridge:
            theme = "stitch_dark"

            def __init__(self, parent: object) -> None:
                self._parent = parent

            def parent(self) -> object:
                return self._parent

        host = _Host()
        model = GraphModel()
        registry = build_default_registry()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(workspace_id, "core.logger", "Logger", 32.0, 48.0)

        builder = GraphScenePayloadBuilder()
        nodes_payload, _backdrop_nodes_payload, _minimap_nodes_payload, _edges_payload = builder.rebuild_partitioned_models(
            model=model,
            registry=registry,
            workspace_id=workspace_id,
            scope_path=(),
            graph_theme_bridge=_ThemeBridge(host),
        )

        self.assertEqual(len(nodes_payload), 1)
        payload = nodes_payload[0]
        self.assertEqual(host.graph_canvas_presenter.graphics_node_title_icon_pixel_size, 50)
        self.assertEqual(payload["surface_metrics"]["header_height"], 54.0)
        self.assertEqual(payload["surface_metrics"]["title_height"], 54.0)
        self.assertEqual(payload["surface_metrics"]["body_top"], 60.0)

    def test_graph_scene_bridge_rebuilds_standard_node_metrics_when_icon_size_changes(self) -> None:
        class _SceneHost(QObject):
            graphics_preferences_changed = pyqtSignal()

            def __init__(self) -> None:
                super().__init__()
                self.graph_canvas_presenter = None
                self.graphics_graph_label_pixel_size = 16
                self.graphics_graph_node_icon_pixel_size_override = None
                self.graphics_node_title_icon_pixel_size = 16
                self.graphics_show_port_labels = True

        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(workspace_id, "core.logger", "Logger", 32.0, 48.0)

        host = _SceneHost()
        scene = GraphSceneBridge(host)
        scene.bind_graph_theme_bridge(GraphThemeBridge(host, theme_id="stitch_dark"))
        scene.set_workspace(model, registry, workspace_id)

        initial_payload = scene.nodes_model[0]
        self.assertEqual(initial_payload["surface_metrics"]["header_height"], 24.0)

        rebuild_events: list[str] = []
        scene.nodes_changed.connect(lambda: rebuild_events.append("nodes"))

        host.graphics_node_title_icon_pixel_size = 50
        host.graphics_preferences_changed.emit()

        updated_payload = scene.nodes_model[0]
        self.assertGreaterEqual(len(rebuild_events), 1)
        self.assertEqual(updated_payload["surface_metrics"]["header_height"], 54.0)
        self.assertEqual(updated_payload["surface_metrics"]["title_height"], 54.0)
        self.assertEqual(updated_payload["surface_metrics"]["body_top"], 60.0)
        self.assertGreater(updated_payload["height"], initial_payload["height"])


class GraphSurfaceLockedPortCanvasTests(GraphSurfaceInputContractTestBase):
    def test_graph_canvas_lock_toggle_hit_target_tracks_locked_state(self) -> None:
        self._run_qml_probe(
            "graph-canvas-lock-toggle-hit-target",
            """
            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            model = GraphModel()
            registry = build_default_registry()
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, model.active_workspace.workspace_id)

            view = ViewportBridge()
            view.set_viewport_size(640.0, 480.0)
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                scene_bridge=scene,
                view_bridge=view,
            )

            node_id = scene.add_node_from_type("core.logger", 120.0, 120.0)
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )
            settle_events(4)

            workspace = model.active_workspace
            node = workspace.nodes[node_id]
            canvas_command_bridge = variant_value(canvas.property("canvasCommandBridge"))
            bridge = canvas_command_bridge.scene_command_source
            assert bridge is not None
            if not node.locked_ports.get("message"):
                assert bridge.set_port_locked(node_id, "message", True) is True
                settle_events(4)
            assert node.locked_ports.get("message") is True, node.locked_ports

            lock_toggle = named_item(canvas, "graphNodeInputPortLockToggleMouseArea", "message")
            assert bool(lock_toggle.property("visible")) is True, variant_value(lock_toggle.property("visible"))
            input_layers = named_item(canvas, "graphCanvasInputLayers")
            window = attach_host_to_window(canvas, 760, 520)

            lock_point = item_scene_point(lock_toggle)
            hit_target = input_layers._lockToggleTargetAtScreen(lock_point.x(), lock_point.y())
            assert hit_target is not None
            assert str(hit_target.property("nodeId")) == node_id
            assert str(hit_target.property("propertyKey")) == "message"
            assert str(hit_target.property("portDirection")) == "in"
            assert bool(hit_target.property("lockedState")) is True

            assert canvas.togglePortLock(node_id, "message", True) is True
            settle_events(4)
            assert node.locked_ports.get("message") is False, node.locked_ports

            lock_toggle = named_item(canvas, "graphNodeInputPortLockToggleMouseArea", "message")
            assert bool(lock_toggle.property("visible")) is False
            hit_target = input_layers._lockToggleTargetAtScreen(lock_point.x(), lock_point.y())
            assert hit_target is None

            assert canvas.togglePortLock(node_id, "message", False) is True
            settle_events(4)
            assert node.locked_ports.get("message") is True, node.locked_ports

            dispose_host_window(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_graph_canvas_suppresses_locked_input_candidates_for_click_and_wire_flows(self) -> None:
        self._run_qml_probe(
            "graph-canvas-locked-target-suppression",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSlot

            from ea_node_editor.graph.model import GraphModel
            from ea_node_editor.nodes.bootstrap import build_default_registry
            from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
            from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

            class PortLockShellBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.connect_calls = []

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

                @pyqtProperty(str, constant=True)
                def graphics_performance_mode(self):
                    return "full_fidelity"

                @pyqtProperty(bool, constant=True)
                def snap_to_grid_enabled(self):
                    return False

                @pyqtProperty(float, constant=True)
                def snap_grid_size(self):
                    return 20.0

                @pyqtSlot(str, str, str, str, result=bool)
                def request_connect_ports(self, node_a_id, port_a, node_b_id, port_b):
                    self.connect_calls.append(
                        (
                            str(node_a_id or ""),
                            str(port_a or ""),
                            str(node_b_id or ""),
                            str(port_b or ""),
                        )
                    )
                    return True

            model = GraphModel()
            registry = build_default_registry()
            scene = GraphSceneBridge()
            scene.set_workspace(model, registry, model.active_workspace.workspace_id)
            shell_bridge = PortLockShellBridgeStub()

            view = ViewportBridge()
            view.set_viewport_size(640.0, 480.0)
            canvas_state_bridge, canvas_command_bridge = build_canvas_bridges(
                shell_bridge=shell_bridge,
                scene_bridge=scene,
                view_bridge=view,
            )

            source_id = scene.add_node_from_type("core.constant", 24.0, 24.0)
            target_id = scene.add_node_from_type("core.logger", 360.0, 140.0)
            canvas = create_component(
                graph_canvas_qml_path,
                {
                    "canvasStateBridge": canvas_state_bridge,
                    "canvasCommandBridge": canvas_command_bridge,
                    "width": 640.0,
                    "height": 480.0,
                },
            )
            settle_events(4)

            lock_toggle = named_item(canvas, "graphNodeInputPortLockToggleMouseArea", "message")
            assert bool(lock_toggle.property("visible")) is True

            window = attach_host_to_window(canvas, 760, 520)
            message_dot = named_item(canvas, "graphNodeInputPortDot", "message")
            message_point = item_scene_point(message_dot)

            source_port = variant_value(canvas._scenePortData(source_id, "as_text"))
            assert source_port is not None

            source_drag = {
                "node_id": source_id,
                "port_key": "as_text",
                "source_direction": str(source_port["direction"]),
                "kind": str(source_port["kind"]),
                "data_type": str(source_port["data_type"]),
                "allow_multiple_connections": bool(source_port.get("allow_multiple_connections", False)),
                "locked": bool(source_port.get("locked", False)),
                "start_x": 0.0,
                "start_y": 0.0,
                "cursor_x": 0.0,
                "cursor_y": 0.0,
            }

            assert variant_value(
                canvas._nearestDropCandidateForWireDrag(
                    message_point.x(),
                    message_point.y(),
                    source_drag,
                    28.0,
                )
            ) is None

            canvas.handlePortClick(source_id, "as_text", "out", 0.0, 0.0)
            app.processEvents()

            pending = variant_value(canvas.property("pendingConnectionPort"))
            assert pending["node_id"] == source_id
            assert pending["port_key"] == "as_text"

            canvas.handlePortClick(target_id, "message", "in", 0.0, 0.0)
            app.processEvents()

            pending = variant_value(canvas.property("pendingConnectionPort"))
            assert pending["node_id"] == source_id
            assert pending["port_key"] == "as_text"
            assert shell_bridge.connect_calls == []

            assert scene.set_port_locked(target_id, "message", False) is True
            settle_events(4)

            candidate = variant_value(
                canvas._nearestDropCandidateForWireDrag(
                    message_point.x(),
                    message_point.y(),
                    source_drag,
                    28.0,
                )
            )
            assert candidate is not None
            assert candidate["node_id"] == target_id
            assert candidate["port_key"] == "message"
            assert bool(candidate["valid_drop"]) is True

            canvas.handlePortClick(target_id, "message", "in", 0.0, 0.0)
            app.processEvents()

            assert shell_bridge.connect_calls == [(source_id, "as_text", target_id, "message")]
            assert canvas.property("pendingConnectionPort") is None

            dispose_host_window(canvas, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )


class GraphSurfaceLockedInputControlsTests(GraphSurfaceInputContractTestBase):
    def test_locked_input_dot_uses_forbidden_cursor_and_suppresses_pointer_signals(self) -> None:
        self._run_qml_probe(
            "locked-input-pointer-controls",
            """
            payload = node_payload()
            payload["node_id"] = "node_locked_controls"
            payload["properties"] = {
                "message": "log message",
                "count": 1,
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
                    "lockable": True,
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
                    "lockable": True,
                    "allow_multiple_connections": False,
                },
                {
                    "key": "result",
                    "label": "Result",
                    "direction": "out",
                    "kind": "data",
                    "data_type": "str",
                    "connected": False,
                    "lockable": False,
                    "allow_multiple_connections": False,
                },
            ]
            payload["inline_properties"] = [
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
                    "value": 1,
                    "overridden_by_input": False,
                    "input_port_label": "count",
                },
            ]

            host = create_component(graph_node_host_qml_path, {"nodeData": payload})
            locked_row = named_item(host, "graphNodeInputPortRow", "message")
            unlocked_row = named_item(host, "graphNodeInputPortRow", "count")
            locked_mouse = named_item(host, "graphNodeInputPortMouseArea", "message")
            unlocked_mouse = named_item(host, "graphNodeInputPortMouseArea", "count")

            assert bool(locked_row.property("lockedState")) is True
            assert bool(unlocked_row.property("lockedState")) is False
            assert locked_mouse.property("cursorShape") == Qt.CursorShape.ForbiddenCursor
            assert unlocked_mouse.property("cursorShape") == Qt.CursorShape.PointingHandCursor

            click_events = []
            hover_events = []
            drag_start_events = []
            drag_finish_events = []
            host.portClicked.connect(
                lambda node_id, port_key, direction, scene_x, scene_y: click_events.append(
                    (node_id, port_key, direction)
                )
            )
            host.portHoverChanged.connect(
                lambda node_id, port_key, direction, scene_x, scene_y, hovered: hover_events.append(
                    (node_id, port_key, direction, hovered)
                )
            )
            host.portDragStarted.connect(
                lambda node_id, port_key, direction, scene_x, scene_y, screen_x, screen_y: drag_start_events.append(
                    (node_id, port_key, direction)
                )
            )
            host.portDragFinished.connect(
                lambda node_id, port_key, direction, scene_x, scene_y, screen_x, screen_y, drag_active: drag_finish_events.append(
                    (node_id, port_key, direction, drag_active)
                )
            )

            window = attach_host_to_window(host, 520, 320)
            locked_point = item_scene_point(locked_mouse)
            unlocked_point = item_scene_point(unlocked_mouse)

            QTest.mouseMove(window, locked_point)
            settle_events(4)
            mouse_click(window, locked_point)
            QTest.mousePress(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                locked_point,
            )
            QTest.mouseMove(window, QPoint(locked_point.x() + 24, locked_point.y()))
            QTest.mouseRelease(
                window,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
                QPoint(locked_point.x() + 24, locked_point.y()),
            )
            settle_events(4)

            assert click_events == []
            assert hover_events == []
            assert drag_start_events == []
            assert drag_finish_events == []

            dispose_host_window(host, window)
            engine.deleteLater()
            app.processEvents()
            """,
        )


if __name__ == "__main__":
    unittest.main()
