from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

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
                from PyQt6.QtGui import QColor
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

            field_rects = variant_list(field.property("embeddedInteractiveRects"))
            assert len(field_rects) == 1
            assert abs(rect_field(field_rects[0], "x") - 22.0) < 0.5
            assert abs(rect_field(field_rects[0], "y") - 56.0) < 0.5
            assert color_name(field.property("resolvedBackgroundColor")) == "#223344"
            assert color_name(field.property("resolvedBorderColor")) == "#556677"

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

            assert color_name(combo.property("resolvedTextColor")) == "#ddeeff"
            assert color_name(combo.property("resolvedBackgroundColor")) == "#223344"
            assert color_name(check.property("resolvedIndicatorBorderColor")) == "#66ccff"
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


if __name__ == "__main__":
    unittest.main()
