// Purpose: Comfortable authoring actions using the shared shell palette and tooltip policy.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15

ShellButton {
    id: control
    tooltipCategory: "general"
    implicitHeight: 28
    implicitWidth: Math.max(control.iconName && !control.text ? 28 : 58, contents.implicitWidth + 14)
    contentItem: Item {
        implicitWidth: contents.implicitWidth
        implicitHeight: 20
        Row {
            id: contents
            anchors.centerIn: parent
            spacing: 5
            Image { visible: control.resolvedIconSource !== ""; source: control.resolvedIconSource; width: 16; height: 16; anchors.verticalCenter: parent.verticalCenter; opacity: control.enabled ? 1 : 0.4 }
            Text {
                text: control.text || (control.iconName && !control.resolvedIconSource ? control.tooltipText : "")
                visible: text.length > 0
                color: control.foregroundColor
                font.family: "Segoe UI"; font.pixelSize: 12
                font.weight: control.selectedStyle ? Font.DemiBold : Font.Normal
                opacity: control.enabled ? 1 : 0.55
            }
        }
    }
    background: Rectangle {
        radius: 2
        color: control.selectedStyle && control.enabled ? control.themePalette.accent_strong
            : control.hovered && control.enabled ? control.themePalette.hover : "transparent"
        border.color: control.selectedStyle && control.enabled ? control.themePalette.accent : control.hovered ? control.themePalette.input_border : "transparent"
        border.width: 1
        opacity: control.enabled ? 1 : 0.5
    }
}
