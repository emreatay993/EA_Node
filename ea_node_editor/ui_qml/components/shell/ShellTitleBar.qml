import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var workspaceBridgeRef: typeof shellWorkspaceBridge !== "undefined" ? shellWorkspaceBridge : null
    property var themeBridgeRef: typeof themeBridge !== "undefined" ? themeBridge : null
    readonly property var themePalette: root.themeBridgeRef ? root.themeBridgeRef.palette : ({})

    Layout.fillWidth: true
    Layout.preferredHeight: 32
    color: themePalette.toolbar_bg
    border.color: themePalette.border

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 8
        spacing: 8

        Text {
            text: "Engineering"
            color: root.themePalette.panel_title_fg
            font.pixelSize: 13
            font.bold: true
        }

        Item { Layout.fillWidth: true }

        Text {
            text: root.workspaceBridgeRef.project_display_name
            color: root.themePalette.muted_fg
            font.pixelSize: 11
        }
    }
}
