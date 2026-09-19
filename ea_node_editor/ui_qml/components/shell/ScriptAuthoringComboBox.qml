// Purpose: Compact native property-grid choices for Python authoring.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
InspectorComboBox {
    id: control
    implicitHeight: 28
    background: Rectangle { radius: 2; color: control.pane.themePalette.input_bg; border.color: control.activeFocus ? control.pane.themePalette.accent : control.pane.themePalette.input_border }
    popup.background: Rectangle { radius: 2; color: control.pane.themePalette.input_bg; border.color: control.pane.themePalette.input_border }
}
