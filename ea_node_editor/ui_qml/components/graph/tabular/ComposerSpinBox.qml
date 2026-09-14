// Purpose: Compact explicit axis/index stepping with keyboard and focus support.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import QtQuick.Controls 2.15

SpinBox {
    id: control
    implicitWidth: 112; implicitHeight: 36
    leftPadding: 30; rightPadding: 30
    font.pixelSize: 12
    contentItem: TextInput {
        text: control.displayText; font: control.font; color: control.palette.text
        horizontalAlignment: Qt.AlignHCenter; verticalAlignment: Qt.AlignVCenter
        readOnly: !control.editable; validator: control.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        selectionColor: control.palette.highlight; selectedTextColor: control.palette.highlightedText
    }
    background: Rectangle {
        radius: 7; color: control.palette.base
        border.color: control.activeFocus ? control.palette.highlight : control.palette.mid
        border.width: control.activeFocus ? 2 : 1
    }
    up.indicator: Rectangle {
        x: control.width - width; width: 28; height: control.height; radius: 7
        color: control.up.pressed || control.up.hovered ? control.palette.alternateBase : "transparent"
        Text { anchors.centerIn: parent; text: "+"; font.pixelSize: 17; color: control.palette.text }
    }
    down.indicator: Rectangle {
        width: 28; height: control.height; radius: 7
        color: control.down.pressed || control.down.hovered ? control.palette.alternateBase : "transparent"
        Text { anchors.centerIn: parent; text: "−"; font.pixelSize: 17; color: control.palette.text }
    }
}
