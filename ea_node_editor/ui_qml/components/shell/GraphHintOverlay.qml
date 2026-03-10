import QtQuick 2.15

Rectangle {
    id: root
    objectName: "graphHintOverlay"
    property var mainWindowRef
    property bool graphSearchVisible: false

    visible: root.mainWindowRef.graph_hint_visible && !root.graphSearchVisible
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: 32
    width: Math.min(parent.width * 0.68, Math.max(260, graphHintText.implicitWidth + 28))
    height: graphHintText.implicitHeight + 14
    radius: 5
    color: "#CC212A35"
    border.width: 1
    border.color: "#5C8CAF"
    z: 1080

    Text {
        id: graphHintText
        anchors.centerIn: parent
        width: parent.width - 24
        text: root.mainWindowRef.graph_hint_message
        color: "#E6F2FF"
        font.pixelSize: 12
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.Wrap
    }
}
