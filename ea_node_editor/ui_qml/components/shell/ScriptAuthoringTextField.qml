// Purpose: Compact native property-grid fields for Python authoring.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
TextField {
    id: control
    property var pane
    implicitHeight: 28
    padding: 5
    font.pixelSize: 12
    selectByMouse: true
    color: pane.themePalette.input_fg
    placeholderTextColor: pane.themePalette.muted_fg
    selectionColor: pane.selectedSurfaceColor
    selectedTextColor: pane.themePalette.input_fg
    background: Rectangle {
        color: control.enabled ? control.pane.themePalette.input_bg : control.pane.themePalette.panel_bg
        border.color: control.activeFocus ? control.pane.themePalette.accent : control.pane.themePalette.input_border
        radius: 2
    }
}
