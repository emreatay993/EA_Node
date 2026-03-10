import QtQuick 2.15
import QtQuick.Controls 2.15

ToolButton {
    id: control
    property bool selectedStyle: false
    implicitHeight: 24
    implicitWidth: Math.max(64, label.implicitWidth + 16)
    padding: 0
    hoverEnabled: true

    contentItem: Text {
        id: label
        text: control.text
        color: control.selectedStyle ? "#DFF2FF" : "#D8DEEA"
        font.pixelSize: 11
        font.bold: control.selectedStyle
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 2
        border.color: control.down ? "#5A606B" : "#4A4E58"
        color: control.selectedStyle
            ? "#2A4F68"
            : (control.down ? "#3A3E46" : (control.hovered ? "#343943" : "#2B2F37"))
    }
}
