// Purpose: Theme-aware navigation between authoring panes.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
TabButton {
    id: control
    property var pane
    implicitHeight: 30
    contentItem: Text {
        text: control.text
        font.pixelSize: 12; font.weight: control.checked ? Font.DemiBold : Font.Normal
        color: control.checked ? control.pane.themePalette.input_fg : control.pane.themePalette.muted_fg
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        color: control.checked ? control.pane.themePalette.panel_bg : control.pane.themePalette.toolbar_bg
        border.color: control.pane.themePalette.border
        radius: 1
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 2; color: control.checked ? control.pane.themePalette.accent : "transparent" }
    }
}
