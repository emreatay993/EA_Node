import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var mainWindowRef

    Layout.fillWidth: true
    Layout.preferredHeight: 32
    color: "#1F2024"
    border.color: "#383838"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 8
        spacing: 8

        Text {
            text: "Engineering"
            color: "#C7D2E2"
            font.pixelSize: 13
            font.bold: true
        }

        Item { Layout.fillWidth: true }

        Text {
            text: root.mainWindowRef.project_display_name
            color: "#9AA1B0"
            font.pixelSize: 11
        }
    }
}
