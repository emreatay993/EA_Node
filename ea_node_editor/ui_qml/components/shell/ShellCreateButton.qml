import QtQuick 2.15
import QtQuick.Controls 2.15

ToolButton {
    id: control
    readonly property var themePalette: themeBridge.palette
    property string tooltipText: text
    property bool accentOutline: false

    implicitHeight: 30
    implicitWidth: Math.max(108, contentRow.implicitWidth + 20)
    padding: 0
    hoverEnabled: true

    ToolTip.visible: hovered && tooltipText.length > 0
    ToolTip.text: tooltipText
    ToolTip.delay: 300

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: 8

            Rectangle {
                width: 18
                height: 18
                radius: 9
                color: control.themePalette.accent

                Rectangle {
                    anchors.centerIn: parent
                    width: 10
                    height: 2
                    radius: 1
                    color: "#ffffff"
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: 2
                    height: 10
                    radius: 1
                    color: "#ffffff"
                }
            }

            Text {
                text: control.text
                color: control.themePalette.panel_title_fg
                font.pixelSize: 11
                font.bold: true
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    background: Rectangle {
        radius: 9
        border.width: 1
        border.color: control.down
            ? control.themePalette.accent
            : ((control.hovered || control.accentOutline)
                ? control.themePalette.accent
                : control.themePalette.border)
        color: control.down
            ? control.themePalette.pressed
            : (control.hovered ? control.themePalette.hover : control.themePalette.panel_alt_bg)
    }
}
