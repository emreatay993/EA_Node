from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.graph.model import GraphModel, NodeInstance
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeRenderQualitySpec, NodeResult, NodeTypeSpec, PortSpec
from ea_node_editor.ui.shell.presenters.graph_canvas_presenter import GraphCanvasPresenter
from ea_node_editor.ui.shell.presenters.state import build_default_shell_workspace_ui_state
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_scene_payload_builder import GraphScenePayloadBuilder
from ea_node_editor.ui_qml.graph_geometry.standard_metrics import (
    node_surface_metrics,
    resolved_node_surface_size,
    standard_inline_body_height,
    standard_inline_row_height,
    standard_inline_textarea_row_height,
)
from ea_node_editor.ui_qml.graph_geometry.surface_contract import VIEWER_LEGACY_DEFAULT_BODY_HEIGHTS
from ea_node_editor.ui_qml.graph_surface_metrics import surface_port_local_point
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from tests.graph_surface.environment import GraphSurfaceInputContractTestBase

_REPO_ROOT = Path(__file__).resolve().parents[1]


class _ViewerSurfacePlugin:
    def __init__(self, spec: NodeTypeSpec) -> None:
        self._spec = spec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult()


def _viewer_surface_spec() -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id="tests.viewer_surface_input_controls",
        display_name="Viewer Controls",
        category_path=("Tests",),
        icon="",
        ports=(
            PortSpec("field", "in", "data", "dpf_field"),
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


class GraphNodeFloatingToolbarProbeTests(unittest.TestCase):
    def _run_toolbar_probe(self, label: str, body: str) -> None:
        probe_qml = textwrap.dedent(
            """
            import QtQuick 2.15
            import QtQuick.Controls 2.15
            import "ea_node_editor/ui_qml/components/graph/overlay" as GraphOverlay

            Item {
                id: probeRoot
                width: 640
                height: 480
                objectName: "floatingToolbarProbeRoot"

                Item {
                    id: fakeHost
                    objectName: "floatingToolbarProbeHost"
                    x: 200
                    y: 180
                    width: 200
                    height: 80

                    property var nodeData: ({ "node_id": "probe_node" })
                    property var surfaceMetrics: ({
                        "floating_toolbar": {
                            "toolbar_height": 32,
                            "button_size": 24,
                            "button_gap": 4,
                            "internal_padding": 4,
                            "gap_from_node": 6,
                            "safety_margin": 8,
                            "hysteresis": 8,
                            "animation_duration_ms": 0
                        }
                    })
                    property var availableActions: ([
                        { "id": "rename", "label": "Rename", "icon": "edit", "kind": "common", "enabled": true, "primary": false },
                        { "id": "duplicate", "label": "Duplicate", "icon": "duplicate", "kind": "common", "enabled": true, "primary": false },
                        { "id": "delete", "label": "Delete", "icon": "delete", "kind": "common", "enabled": true, "primary": false, "destructive": true }
                    ])
                    property bool toolbarActive: true
                    property color nodeThemeColor: "#5da9ff"
                    property real worldOffset: 0
                    property bool _liveGeometryActive: false
                    property real _liveX: 0
                    property real _liveY: 0
                    property color inlineInputBackgroundColor: "#22242a"
                    property color inlineInputBorderColor: "#4a4f5a"
                    property color headerTextColor: "#eef3ff"
                    property var graphSharedTypography: ({ "inlinePropertyPixelSize": 12 })
                    property var canvasItem: null

                    signal surfaceControlInteractionStarted(string nodeId)
                    signal nodeActionRequested(string nodeId, string actionId, var payload)

                    function dispatchNodeAction(actionId, payload) {
                        fakeHost.nodeActionRequested(
                            String(fakeHost.nodeData && fakeHost.nodeData.node_id || ""),
                            String(actionId || ""),
                            payload || null
                        )
                    }
                }

                GraphOverlay.GraphNodeFloatingToolbar {
                    id: toolbar
                    objectName: "floatingToolbarProbeToolbar"
                    host: fakeHost
                    visibleSceneRectPayload: ({ "x": 0, "y": 0, "width": 640, "height": 480 })
                }
            }
            """
        )
        script = (
            textwrap.dedent(
                """
                from pathlib import Path

                from PyQt6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt, QUrl
                from PyQt6.QtGui import QColor, QKeySequence
                from PyQt6.QtQml import QQmlComponent, QQmlEngine
                from PyQt6.QtQuick import QQuickItem, QQuickWindow
                from PyQt6.QtTest import QTest
                from PyQt6.QtWidgets import QApplication

                from ea_node_editor.ui.icon_registry import (
                    UI_ICON_PROVIDER_ID,
                    UiIconImageProvider,
                    UiIconRegistryBridge,
                )

                app = QApplication.instance() or QApplication([])
                engine = QQmlEngine()
                engine.addImageProvider(UI_ICON_PROVIDER_ID, UiIconImageProvider())
                engine.rootContext().setContextProperty("uiIcons", UiIconRegistryBridge())
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

                def walk_items(item):
                    if isinstance(item, QQuickItem):
                        yield item
                        for child in item.childItems():
                            yield from walk_items(child)

                def named_item(root, object_name):
                    for child in walk_items(root):
                        if child.objectName() == object_name:
                            return child
                    raise AssertionError("Missing object: " + object_name)

                def attach_window(root):
                    window = QQuickWindow()
                    window.resize(640, 480)
                    root.setParentItem(window.contentItem())
                    window.show()
                    app.processEvents()
                    return window

                PROBE_QML = """
            )
            + repr(probe_qml)
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
            self.fail(f"{label} probe failed with exit code {result.returncode}\n{details}")

    def test_floating_toolbar_publishes_rect_and_dispatches_each_action_exactly_once(self) -> None:
        self._run_toolbar_probe(
            "floating-toolbar-rect-and-click-dispatch",
            """
            root = load_probe()
            host = named_item(root, "floatingToolbarProbeHost")
            toolbar = named_item(root, "floatingToolbarProbeToolbar")

            assert bool(toolbar.property("visible"))
            assert float(toolbar.property("width")) > 0.0
            assert float(toolbar.property("height")) > 0.0

            rect = variant_value(toolbar.property("toolbarRect"))
            assert rect_field(rect, "width") > 0.0
            assert rect_field(rect, "height") > 0.0

            embedded = variant_list(toolbar.property("embeddedInteractiveRects"))
            assert len(embedded) == 1
            assert rect_field(embedded[0], "width") > 0.0

            events = []
            host.nodeActionRequested.connect(
                lambda node_id, action_id, payload: events.append((str(node_id), str(action_id)))
            )

            window = attach_window(root)
            try:
                for action_id in ("rename", "duplicate", "delete"):
                    button = named_item(root, "graphNodeFloatingToolbarAction_" + action_id)
                    center = button.mapToScene(
                        QPointF(float(button.width()) * 0.5, float(button.height()) * 0.5)
                    )
                    QTest.mouseClick(
                        window,
                        Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier,
                        QPoint(round(center.x()), round(center.y())),
                    )
                    app.processEvents()

                assert events == [
                    ("probe_node", "rename"),
                    ("probe_node", "duplicate"),
                    ("probe_node", "delete"),
                ], events
            finally:
                window.close()
                app.processEvents()
            """,
        )

    def test_floating_toolbar_buttons_support_keyboard_tab_and_enter(self) -> None:
        self._run_toolbar_probe(
            "floating-toolbar-keyboard-parity",
            """
            root = load_probe()
            host = named_item(root, "floatingToolbarProbeHost")

            events = []
            host.nodeActionRequested.connect(
                lambda node_id, action_id, payload: events.append((str(node_id), str(action_id)))
            )

            window = attach_window(root)
            try:
                first_button = named_item(root, "graphNodeFloatingToolbarAction_rename")
                first_button.forceActiveFocus()
                app.processEvents()
                assert bool(first_button.property("activeFocus"))

                QTest.keyClick(window, Qt.Key.Key_Return)
                app.processEvents()
                assert events == [("probe_node", "rename")], events

                second_button = named_item(root, "graphNodeFloatingToolbarAction_duplicate")
                second_button.forceActiveFocus()
                app.processEvents()
                assert bool(second_button.property("activeFocus"))

                QTest.keyClick(window, Qt.Key.Key_Enter)
                app.processEvents()
                assert events == [
                    ("probe_node", "rename"),
                    ("probe_node", "duplicate"),
                ], events
            finally:
                window.close()
                app.processEvents()
            """,
        )

    def test_floating_toolbar_visibility_tracks_host_toolbar_active_flag(self) -> None:
        self._run_toolbar_probe(
            "floating-toolbar-toolbar-active-tracking",
            """
            root = load_probe()
            host = named_item(root, "floatingToolbarProbeHost")
            toolbar = named_item(root, "floatingToolbarProbeToolbar")

            assert bool(host.property("toolbarActive"))
            assert bool(toolbar.property("visible"))

            host.setProperty("toolbarActive", False)
            app.processEvents()
            assert not bool(host.property("toolbarActive"))
            assert not bool(toolbar.property("visible"))

            host.setProperty("toolbarActive", True)
            app.processEvents()
            assert bool(toolbar.property("visible"))

            host.setProperty("availableActions", [])
            app.processEvents()
            assert not bool(toolbar.property("visible"))
            """,
        )


class GraphSurfaceInlineMetricTypographyTests(unittest.TestCase):
    def _viewer_registry(self) -> tuple[NodeRegistry, NodeTypeSpec]:
        spec = _viewer_surface_spec()
        registry = NodeRegistry()
        registry.register(lambda: _ViewerSurfacePlugin(spec))
        return registry, spec

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

    def test_viewer_surface_metrics_follow_graph_title_icon_size(self) -> None:
        spec = _viewer_surface_spec()
        node = NodeInstance(
            node_id="node_viewer_surface_input_controls",
            type_id=spec.type_id,
            title="Viewer Controls",
            x=32.0,
            y=48.0,
        )

        default_metrics = node_surface_metrics(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
        )
        large_icon_metrics = node_surface_metrics(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )
        baseline_port_point = surface_port_local_point(
            node,
            spec,
            "field",
            {node.node_id: node},
            graph_label_pixel_size=16,
        )
        large_icon_port_point = surface_port_local_point(
            node,
            spec,
            "field",
            {node.node_id: node},
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )

        self.assertEqual(default_metrics.header_height, 24.0)
        self.assertEqual(default_metrics.body_top, 30.0)
        self.assertEqual(large_icon_metrics.header_height, 54.0)
        self.assertEqual(large_icon_metrics.title_height, 54.0)
        self.assertEqual(large_icon_metrics.body_top - default_metrics.body_top, 30.0)
        self.assertEqual(large_icon_metrics.port_top - default_metrics.port_top, 30.0)
        self.assertEqual(large_icon_metrics.default_height - default_metrics.default_height, 30.0)
        self.assertEqual(large_icon_metrics.body_height, default_metrics.body_height)
        self.assertEqual(large_icon_port_point[1] - baseline_port_point[1], 30.0)

    def test_dpf_viewer_metrics_follow_graph_label_size_for_port_rows(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("dpf.viewer")
        node = NodeInstance(
            node_id="node_dpf_viewer_input_controls",
            type_id=spec.type_id,
            title="DPF Viewer",
            x=32.0,
            y=48.0,
        )

        default_metrics = node_surface_metrics(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=10,
            graph_node_icon_pixel_size=50,
        )
        large_metrics = node_surface_metrics(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )

        self.assertEqual(default_metrics.port_height, 18.0)
        self.assertEqual(large_metrics.port_height, 24.0)
        self.assertEqual(large_metrics.body_top, default_metrics.body_top)
        self.assertEqual(large_metrics.body_height, default_metrics.body_height)
        self.assertEqual(large_metrics.default_height - default_metrics.default_height, 24.0)
        self.assertEqual(large_metrics.min_height - default_metrics.min_height, 24.0)

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

    def test_scene_payload_builder_applies_title_icon_size_to_viewer_nodes(self) -> None:
        class _ThemeSource:
            graphics_graph_label_pixel_size = 16
            graphics_node_title_icon_pixel_size = 50

        class _ThemeBridge:
            theme = "stitch_dark"

            def __init__(self, parent: object) -> None:
                self._parent = parent

            def parent(self) -> object:
                return self._parent

        registry, spec = self._viewer_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(workspace_id, spec.type_id, spec.display_name, 32.0, 48.0)

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
        self.assertEqual(payload["surface_family"], "viewer")
        self.assertEqual(payload["surface_metrics"]["header_height"], 54.0)
        self.assertEqual(payload["surface_metrics"]["title_height"], 54.0)
        self.assertEqual(payload["surface_metrics"]["body_top"], 60.0)
        self.assertEqual(payload["viewer_surface"]["live_rect"]["y"], 60.0)
        self.assertEqual(payload["viewer_surface"]["live_rect"]["height"], 176.0)
        self.assertEqual(payload["surface_metrics"]["port_height"], 24.0)
        self.assertEqual(payload["height"], 272.0)

    def test_scene_payload_builder_applies_graph_label_port_height_to_dpf_viewer_nodes(self) -> None:
        class _ThemeSource:
            graphics_graph_label_pixel_size = 16
            graphics_node_title_icon_pixel_size = 50

        class _ThemeBridge:
            theme = "stitch_dark"

            def __init__(self, parent: object) -> None:
                self._parent = parent

            def parent(self) -> object:
                return self._parent

        registry = build_default_registry()
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        model.add_node(workspace_id, "dpf.viewer", "DPF Viewer", 32.0, 48.0)

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
        self.assertEqual(payload["surface_family"], "viewer")
        self.assertEqual(payload["surface_metrics"]["body_top"], 60.0)
        self.assertEqual(payload["surface_metrics"]["body_height"], 176.0)
        self.assertEqual(payload["surface_metrics"]["port_height"], 24.0)
        self.assertEqual(payload["surface_metrics"]["min_height"], 316.0)
        self.assertEqual(payload["viewer_surface"]["live_rect"]["y"], 60.0)
        self.assertEqual(payload["viewer_surface"]["live_rect"]["height"], 176.0)
        self.assertEqual(payload["height"], 344.0)

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

    def test_viewer_surface_size_clamps_stale_custom_height_when_header_grows(self) -> None:
        spec = _viewer_surface_spec()
        node = NodeInstance(
            node_id="node_viewer_surface_input_controls",
            type_id=spec.type_id,
            title="Viewer Controls",
            x=32.0,
            y=48.0,
        )

        baseline_height = resolved_node_surface_size(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
        )[1]
        node.custom_height = float(baseline_height)

        grown_metrics = node_surface_metrics(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )
        grown_size = resolved_node_surface_size(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )

        self.assertGreater(grown_metrics.default_height, baseline_height)
        self.assertLess(grown_metrics.min_height, grown_metrics.default_height)
        self.assertEqual(grown_size[1], grown_metrics.default_height)

    def test_viewer_surface_size_clamps_legacy_default_height_when_body_chrome_grows(self) -> None:
        spec = _viewer_surface_spec()
        node = NodeInstance(
            node_id="node_viewer_surface_legacy_height",
            type_id=spec.type_id,
            title="Viewer Controls",
            x=32.0,
            y=48.0,
        )

        current_metrics = node_surface_metrics(node, spec, {node.node_id: node})
        legacy_body_height = float(VIEWER_LEGACY_DEFAULT_BODY_HEIGHTS[-1])
        legacy_height = (
            float(current_metrics.default_height)
            - (float(current_metrics.body_height) - legacy_body_height)
            + 0.5
        )
        node.custom_height = legacy_height

        resolved_size = resolved_node_surface_size(
            node,
            spec,
            {node.node_id: node},
        )

        self.assertGreater(legacy_height, current_metrics.default_height)
        self.assertEqual(resolved_size[1], current_metrics.default_height)

    def test_viewer_surface_metrics_shrink_body_to_fit_custom_height_between_minimum_and_default(self) -> None:
        spec = NodeTypeSpec(
            type_id="tests.viewer_surface_input_controls.multiport",
            display_name="Viewer Controls",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec("field", "in", "data", "dpf_field"),
                PortSpec("model", "in", "data", "dpf_model"),
                PortSpec("mesh", "in", "data", "dpf_mesh"),
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
        node = NodeInstance(
            node_id="node_viewer_surface_input_controls_mid_height",
            type_id=spec.type_id,
            title="Viewer Controls",
            x=32.0,
            y=48.0,
        )

        default_metrics = node_surface_metrics(node, spec, {node.node_id: node})
        self.assertGreater(default_metrics.default_height, default_metrics.min_height)

        midway_height = float(default_metrics.default_height - 18.0)
        self.assertGreater(midway_height, float(default_metrics.min_height))
        node.custom_height = midway_height

        shrunk_metrics = node_surface_metrics(node, spec, {node.node_id: node})
        expected_body_height = (
            midway_height
            - float(shrunk_metrics.body_top)
            - 3.0 * float(shrunk_metrics.port_height)
            - float(shrunk_metrics.body_bottom_margin)
        )

        self.assertLess(shrunk_metrics.body_height, default_metrics.body_height)
        self.assertAlmostEqual(float(shrunk_metrics.body_height), expected_body_height, places=6)
        self.assertAlmostEqual(
            float(shrunk_metrics.port_top)
            + 3.0 * float(shrunk_metrics.port_height)
            + float(shrunk_metrics.body_bottom_margin),
            midway_height,
            places=6,
        )

    def test_standard_surface_size_clamps_stale_custom_height_when_header_grows(self) -> None:
        registry = build_default_registry()
        spec = registry.get_spec("core.logger")
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        node = model.add_node(workspace_id, "core.logger", "Logger", 32.0, 48.0)

        baseline_height = resolved_node_surface_size(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
        )[1]
        node.custom_height = float(baseline_height)

        grown_metrics = node_surface_metrics(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )
        grown_size = resolved_node_surface_size(
            node,
            spec,
            {node.node_id: node},
            graph_label_pixel_size=16,
            graph_node_icon_pixel_size=50,
        )

        self.assertGreater(grown_metrics.default_height, baseline_height)
        self.assertEqual(grown_metrics.min_height, grown_metrics.default_height)
        self.assertEqual(grown_size[1], grown_metrics.default_height)

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
    def test_graph_canvas_content_fullscreen_f11_routes_selection_and_hint_contract(self) -> None:
        self._run_qml_probe(
            "graph-canvas-content-fullscreen-shortcut",
            """
            from PyQt6.QtCore import pyqtProperty, pyqtSlot

            class ContentFullscreenBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.is_open = False
                    self.open_calls = []
                    self.close_calls = 0
                    self.eligible_node_ids = {"media_node"}
                    self.last_error_value = "The selected node does not support content fullscreen."

                @pyqtProperty(bool)
                def open(self):
                    return self.is_open

                @pyqtProperty(str)
                def last_error(self):
                    return self.last_error_value

                @pyqtSlot(str, result=bool)
                def can_open_node(self, node_id):
                    return str(node_id or "") in self.eligible_node_ids

                @pyqtSlot(str, result=bool)
                def request_open_node(self, node_id):
                    normalized = str(node_id or "")
                    self.open_calls.append(normalized)
                    if normalized in self.eligible_node_ids:
                        self.is_open = True
                        self.last_error_value = ""
                        return True
                    self.last_error_value = "The selected node does not support content fullscreen."
                    return False

                @pyqtSlot()
                def request_close(self):
                    self.close_calls += 1
                    self.is_open = False

            class ShellBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.hints = []

                @pyqtSlot(str, int)
                def show_graph_hint(self, message, timeout_ms):
                    self.hints.append((str(message or ""), int(timeout_ms)))

            bridge = ContentFullscreenBridgeStub()
            shell_bridge = ShellBridgeStub()
            engine.rootContext().setContextProperty("contentFullscreenBridge", bridge)
            engine.rootContext().setContextProperty("shellBridge", shell_bridge)

            component = QQmlComponent(engine)
            component.setData(
                b'''
                import QtQuick 2.15
                import "ea_node_editor/ui_qml/components/graph_canvas" as GraphCanvasComponents

                Item {
                    id: probeRoot
                    objectName: "contentFullscreenShortcutProbe"
                    width: 400
                    height: 300
                    property var selectedIds: []

                    function selectedNodeIds() {
                        return selectedIds;
                    }

                    GraphCanvasComponents.GraphCanvasInputLayers {
                        id: inputLayers
                        objectName: "graphCanvasInputLayers"
                        canvasItem: probeRoot
                        shellCommandBridge: shellBridge
                    }

                    function triggerShortcut() {
                        return inputLayers._handleContentFullscreenShortcut();
                    }
                }
                ''',
                QUrl.fromLocalFile(str(repo_root) + "/"),
            )
            if component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to load shortcut probe:\\n" + errors)
            probe = component.create()
            if probe is None:
                errors = "\\n".join(error.toString() for error in component.errors())
                raise AssertionError("Failed to instantiate shortcut probe:\\n" + errors)
            app.processEvents()

            probe.setProperty("selectedIds", ["media_node"])
            assert probe.triggerShortcut() is True
            app.processEvents()
            assert bridge.open_calls == ["media_node"]
            assert bridge.is_open is True
            assert shell_bridge.hints == []

            assert probe.triggerShortcut() is True
            app.processEvents()
            assert bridge.close_calls == 1
            assert bridge.is_open is False

            probe.setProperty("selectedIds", ["unsupported_node"])
            assert probe.triggerShortcut() is True
            app.processEvents()
            assert bridge.open_calls == ["media_node", "unsupported_node"]
            assert shell_bridge.hints[-1] == (
                "The selected node does not support content fullscreen.",
                2400,
            )

            probe.setProperty("selectedIds", ["media_node", "viewer_node"])
            assert probe.triggerShortcut() is True
            app.processEvents()
            assert bridge.open_calls == ["media_node", "unsupported_node"]
            assert shell_bridge.hints[-1] == (
                "Select one media or viewer node for fullscreen.",
                2400,
            )

            probe.deleteLater()
            engine.deleteLater()
            app.processEvents()
            """,
        )

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


class GraphSurfaceLockedNodeCanvasRoutingTests(GraphSurfaceInputContractTestBase):
    def test_locked_node_context_menu_only_exposes_addon_manager_affordance(self) -> None:
        self._run_qml_probe(
            "locked-node-context-menu-routing",
            """
            import textwrap

            from PyQt6.QtCore import QObject, pyqtSlot, QUrl
            from PyQt6.QtQml import QQmlComponent

            class AddonManagerBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.requests = []

                @pyqtSlot(str)
                def requestOpen(self, focus_addon_id):
                    self.requests.append(str(focus_addon_id))

            addon_bridge = AddonManagerBridgeStub()
            engine.rootContext().setContextProperty("addonManagerBridge", addon_bridge)

            menus_qml_path = components_dir / "graph_canvas" / "GraphCanvasContextMenus.qml"
            payload = node_payload()
            payload["node_id"] = "node_locked_context"
            payload["read_only"] = True
            payload["unresolved"] = True
            payload["addon_id"] = "tests.addons.signal_pack"
            payload["locked_state"] = {
                "focus_addon_id": "tests.addons.signal_pack",
                "label": "Requires add-on",
            }
            canvas_component = QQmlComponent(engine)
            canvas_component.setData(
                textwrap.dedent(
                    '''
                    import QtQuick 2.15

                    Item {
                        property bool nodeContextVisible: true
                        property real contextMenuX: 16
                        property real contextMenuY: 22
                        property string nodeContextNodeId: "node_locked_context"
                        property var payload: ({})
                        property int closeCalls: 0

                        function _sceneNodePayload(nodeId) {
                            return String(nodeId || "") === nodeContextNodeId ? payload : ({})
                        }

                        function _nodeCanEnterScope(nodeId) {
                            return String(nodeId || "") === nodeContextNodeId
                        }

                        function _nodeSupportsPassiveStyle(nodeId) {
                            return String(nodeId || "") === nodeContextNodeId
                        }

                        function selectedNodeIds() {
                            return []
                        }

                        function _closeContextMenus() {
                            closeCalls += 1
                            nodeContextVisible = false
                        }
                    }
                    '''
                ).encode("utf-8"),
                QUrl.fromLocalFile(str(repo_root) + "/"),
            )
            if canvas_component.status() != QQmlComponent.Status.Ready:
                errors = "\\n".join(error.toString() for error in canvas_component.errors())
                raise AssertionError("Failed to load canvas stub QML:\\n" + errors)
            canvas_item = canvas_component.create()
            if canvas_item is None:
                errors = "\\n".join(error.toString() for error in canvas_component.errors())
                raise AssertionError("Failed to instantiate canvas stub QML:\\n" + errors)
            canvas_item.setProperty("payload", payload)
            menus = create_component(menus_qml_path, {"canvasItem": canvas_item})
            popup = menus.findChild(QObject, "graphCanvasNodeContextPopup")
            assert popup is not None

            visible_actions = [variant_value(action) for action in variant_list(popup.property("visibleActions"))]
            action_texts = [str(action.get("text", "")) for action in visible_actions]
            assert action_texts == ["Open Add-On Manager"], action_texts

            popup.actionTriggered.emit("open_addon_manager")
            settle_events(2)

            assert addon_bridge.requests == ["tests.addons.signal_pack"]
            assert int(canvas_item.property("closeCalls")) == 1
            assert bool(canvas_item.property("nodeContextVisible")) is False

            menus.deleteLater()
            canvas_item.deleteLater()
            engine.deleteLater()
            app.processEvents()
            """,
        )

    def test_locked_node_surface_bridge_rejects_mutating_requests(self) -> None:
        self._run_qml_probe(
            "locked-node-surface-bridge-guards",
            """
            from PyQt6.QtCore import QObject, pyqtProperty, pyqtSlot

            class SceneCommandBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.select_calls = []
                    self.property_calls = []
                    self.port_label_calls = []
                    self.property_batch_calls = []
                    self.pending_calls = []

                @pyqtSlot(str, bool)
                def select_node(self, node_id, additive):
                    self.select_calls.append((str(node_id), bool(additive)))

                @pyqtSlot(str, str, "QVariant")
                def set_node_property(self, node_id, key, value):
                    self.property_calls.append((str(node_id), str(key), variant_value(value)))

                @pyqtSlot(str, str, str)
                def set_node_port_label(self, node_id, port_key, label):
                    self.port_label_calls.append((str(node_id), str(port_key), str(label)))

                @pyqtSlot(str, "QVariantMap", result=bool)
                def set_node_properties(self, node_id, properties):
                    self.property_batch_calls.append((str(node_id), dict(properties or {})))
                    return True

                @pyqtSlot(str)
                def set_pending_surface_action(self, node_id):
                    self.pending_calls.append(str(node_id))

                @pyqtSlot(str, result=bool)
                def consume_pending_surface_action(self, _node_id):
                    return False

            class ShellCommandBridgeStub(QObject):
                def __init__(self):
                    super().__init__()
                    self.open_scope_calls = []
                    self.browse_calls = []
                    self.color_calls = []

                @pyqtSlot(str, result=bool)
                def request_open_subnode_scope(self, node_id):
                    self.open_scope_calls.append(str(node_id))
                    return True

                @pyqtSlot(str, str, str, result=str)
                def browse_node_property_path(self, node_id, key, current_path):
                    self.browse_calls.append((str(node_id), str(key), str(current_path)))
                    return "C:/tmp/example.txt"

                @pyqtSlot(str, str, str, result=str)
                def pick_node_property_color(self, node_id, key, current_value):
                    self.color_calls.append((str(node_id), str(key), str(current_value)))
                    return "#abcdef"

                @pyqtSlot(int)
                def set_graph_cursor_shape(self, _cursor_shape):
                    pass

                @pyqtSlot()
                def clear_graph_cursor_shape(self):
                    pass

                @pyqtSlot(str, "QVariant", result="QVariantMap")
                def describe_pdf_preview(self, _source, _page_number):
                    return {}

            class CanvasItemStub(QObject):
                def __init__(self, payload, scene_bridge, shell_bridge):
                    super().__init__()
                    self._payload = payload
                    self._scene_bridge = scene_bridge
                    self._shell_bridge = shell_bridge
                    self.close_calls = 0
                    self.pending_clear_calls = 0
                    self.edge_clear_calls = 0
                    self.cancel_wire_drag_calls = 0

                @pyqtProperty(QObject, constant=True)
                def _canvasSceneCommandBridgeRef(self):
                    return self._scene_bridge

                @pyqtProperty(QObject, constant=True)
                def _canvasShellCommandBridgeRef(self):
                    return self._shell_bridge

                @pyqtSlot(str, result="QVariantMap")
                def _sceneNodePayload(self, node_id):
                    if str(node_id) == "node_locked_bridge":
                        return self._payload
                    return {}

                @pyqtSlot()
                def _closeContextMenus(self):
                    self.close_calls += 1

                @pyqtSlot()
                def clearPendingConnection(self):
                    self.pending_clear_calls += 1

                @pyqtSlot()
                def clearEdgeSelection(self):
                    self.edge_clear_calls += 1

                @pyqtSlot()
                def cancelWireDrag(self):
                    self.cancel_wire_drag_calls += 1

                @pyqtSlot(result="QVariantList")
                def selectedNodeIds(self):
                    return []

            bridge_qml_path = components_dir / "graph_canvas" / "GraphCanvasNodeSurfaceBridge.qml"
            payload = node_payload()
            payload["node_id"] = "node_locked_bridge"
            payload["read_only"] = True
            payload["unresolved"] = True
            scene_bridge = SceneCommandBridgeStub()
            shell_bridge = ShellCommandBridgeStub()
            canvas_item = CanvasItemStub(payload, scene_bridge, shell_bridge)
            bridge = create_component(bridge_qml_path, {"canvasItem": canvas_item})

            assert bool(bridge.requestOpenSubnodeScope("node_locked_bridge")) is False
            assert bool(bridge.commitNodeSurfaceProperty("node_locked_bridge", "message", "blocked")) is False
            assert bool(bridge.commitNodePortLabel("node_locked_bridge", "message", "Blocked")) is False
            assert bool(bridge.requestNodeSurfaceCropEdit("node_locked_bridge")) is False
            assert bool(bridge.commitNodeSurfaceProperties("node_locked_bridge", {"message": "blocked"})) is False
            assert str(bridge.browseNodePropertyPath("node_locked_bridge", "source_path", "")) == ""
            assert str(bridge.pickNodePropertyColor("node_locked_bridge", "accent", "#000000")) == ""

            settle_events(2)

            assert scene_bridge.select_calls == []
            assert scene_bridge.property_calls == []
            assert scene_bridge.port_label_calls == []
            assert scene_bridge.property_batch_calls == []
            assert scene_bridge.pending_calls == []
            assert shell_bridge.open_scope_calls == []
            assert shell_bridge.browse_calls == []
            assert shell_bridge.color_calls == []
            assert canvas_item.close_calls == 0
            assert canvas_item.pending_clear_calls == 0
            assert canvas_item.edge_clear_calls == 0
            assert canvas_item.cancel_wire_drag_calls == 0

            bridge.deleteLater()
            engine.deleteLater()
            app.processEvents()
            """,
        )


if __name__ == "__main__":
    unittest.main()
