// Purpose: Compact composer section navigation with a clear active underline.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import QtQuick.Controls 2.15

TabButton {
    id: control
    implicitWidth: Math.max(100, label.implicitWidth + 30); implicitHeight: 40
    contentItem: Text {
        id: label
        text: control.text; font.pixelSize: 12; font.weight: control.checked ? Font.DemiBold : Font.Normal
        color: control.checked ? control.palette.text : control.palette.placeholderText
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        color: control.hovered ? Qt.alpha(control.palette.highlight, 0.06) : "transparent"
        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 2; color: control.checked ? control.palette.highlight : "transparent" }
        border.width: control.activeFocus ? 1 : 0; border.color: control.palette.highlight
    }
}
