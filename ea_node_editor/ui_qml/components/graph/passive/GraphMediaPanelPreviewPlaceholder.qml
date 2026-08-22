import QtQuick 2.15

Column {
    id: root
    property var surface: null
    anchors.centerIn: parent
    width: Math.min(parent.width - 24, root.surface && root.surface.isPdfPanel ? 208 : 180)
    spacing: 8
    visible: root.surface ? root.surface.previewState !== "ready" : true

    Item {
        width: 42
        height: 42
        anchors.horizontalCenter: parent.horizontalCenter

        Rectangle {
            visible: !(root.surface && root.surface.isPdfPanel)
            width: 42
            height: 42
            radius: 8
            color: Qt.alpha(root.surface ? root.surface.panelBorderColor : "#4a4f5a", 0.1)
            border.width: 1
            border.color: Qt.alpha(root.surface ? root.surface.panelBorderColor : "#4a4f5a", 0.55)

            Rectangle {
                anchors.centerIn: parent
                width: 22
                height: 16
                radius: 3
                color: "transparent"
                border.width: 1
                border.color: Qt.alpha(root.surface ? root.surface.hintTextColor : "#bdc5d3", 0.9)
            }
        }

        Item {
            visible: root.surface && root.surface.isPdfPanel
            anchors.fill: parent

            Rectangle {
                x: 8
                y: 2
                width: 26
                height: 34
                radius: 4
                color: "#F5F7FA"
                border.width: 1
                border.color: Qt.alpha(root.surface ? root.surface.hintTextColor : "#bdc5d3", 0.75)
            }

            Rectangle {
                x: 13
                y: 8
                width: 16
                height: 8
                radius: 2
                color: root.surface && root.surface.previewState === "error"
                    ? Qt.alpha("#B55454", 0.92)
                    : Qt.alpha("#3A7CA5", 0.92)
            }

            Rectangle {
                x: 28
                y: 2
                width: 6
                height: 6
                color: "#E8EDF3"
                rotation: 45
                transformOrigin: Item.TopLeft
            }
        }
    }

    Text {
        objectName: "graphNodeMediaPreviewHint"
        visible: parent.visible
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        wrapMode: Text.WordWrap
        color: root.surface ? root.surface.hintTextColor : "#bdc5d3"
        font.pixelSize: 11
        text: root.surface ? root.surface.previewHintText : ""
        renderType: root.surface && root.surface.host
            ? root.surface.host.nodeTextRenderType
            : Text.CurveRendering
    }
}
