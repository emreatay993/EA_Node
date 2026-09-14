// Purpose: Small theme-aware composer toggles with visible keyboard focus.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import QtQuick.Controls 2.15

CheckBox {
    id: control
    implicitHeight: 30; padding: 0; spacing: 8; hoverEnabled: true
    indicator: Rectangle {
        implicitWidth: 17; implicitHeight: 17; y: (control.height - height) / 2; radius: 4
        color: control.checked ? control.palette.highlight : control.palette.base
        border.color: control.activeFocus || control.checked ? control.palette.highlight : control.palette.mid
        border.width: control.activeFocus ? 2 : 1
        Item {
            anchors.centerIn: parent; width: 12; height: 10; visible: control.checked
            Rectangle { x: 1; y: 5; width: 5; height: 1.8; radius: 0.9; rotation: 45; color: control.palette.highlightedText }
            Rectangle { x: 4; y: 3; width: 8; height: 1.8; radius: 0.9; rotation: -45; color: control.palette.highlightedText }
        }
    }
    contentItem: Text {
        text: control.text; leftPadding: control.indicator.width + control.spacing
        color: control.enabled ? control.palette.text : control.palette.placeholderText
        verticalAlignment: Text.AlignVCenter; font.pixelSize: 12
    }
}
