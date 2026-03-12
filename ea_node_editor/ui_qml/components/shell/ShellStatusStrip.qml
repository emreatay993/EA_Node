import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var statusEngineRef
    property var statusJobsRef
    property var statusMetricsRef
    property var statusNotificationsRef
    readonly property var themePalette: themeBridge.palette

    Layout.fillWidth: true
    Layout.preferredHeight: 24
    color: themePalette.status_bg
    border.color: themePalette.status_border

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 10

        Text {
            text: root.statusEngineRef.icon_value + " " + root.statusEngineRef.text_value
            color: root.themePalette.status_fg
            font.pixelSize: 11
            font.bold: true
        }
        Text {
            text: root.statusJobsRef.icon_value + " " + root.statusJobsRef.text_value
            color: root.themePalette.status_fg
            font.pixelSize: 11
        }
        Text {
            text: root.statusMetricsRef.icon_value + " " + root.statusMetricsRef.text_value
            color: root.themePalette.status_fg
            font.pixelSize: 11
        }
        Item { Layout.fillWidth: true }
        Text {
            text: root.statusNotificationsRef.icon_value + " " + root.statusNotificationsRef.text_value
            color: root.themePalette.status_fg
            font.pixelSize: 11
        }
    }
}
