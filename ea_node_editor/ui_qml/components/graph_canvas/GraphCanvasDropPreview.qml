import QtQuick 2.15

Rectangle {
    id: root
    property Item canvasItem: null
    property var viewBridge: null

    visible: !!root.canvasItem && !!root.canvasItem.dropPreviewNodePayload
    z: 34
    x: root.canvasItem ? root.canvasItem.dropPreviewScreenX : -1
    y: root.canvasItem ? root.canvasItem.dropPreviewScreenY : -1
    width: root.canvasItem ? root.canvasItem.previewNodeScreenWidth() : 0
    height: root.canvasItem ? root.canvasItem.previewNodeScreenHeight() : 0
    radius: Math.max(4, 6 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
    color: "#AA2A3340"
    border.width: 1
    border.color: "#80CFF5"
    clip: true

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: Math.max(8, 4 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
        color: "#66A4D8"
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Math.max(8, 4 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
        height: Math.max(14, 24 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
        color: "#7A2F3948"
    }

    Text {
        anchors.left: parent.left
        anchors.leftMargin: Math.max(4, 10 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
        anchors.right: parent.right
        anchors.rightMargin: Math.max(4, 8 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
        anchors.top: parent.top
        anchors.topMargin: Math.max(10, 8 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
        text: root.canvasItem && root.canvasItem.dropPreviewNodePayload
            ? String(root.canvasItem.dropPreviewNodePayload.display_name || root.canvasItem.dropPreviewNodePayload.type_id || "")
            : ""
        color: "#EAF3FF"
        font.bold: true
        font.pixelSize: Math.max(10, Math.min(16, 12 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0)))
        elide: Text.ElideRight
    }

    Item {
        id: previewPortsLayer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Math.max(10, 30 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Math.max(2, 6 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))

        Column {
            id: previewInputColumn
            anchors.left: parent.left
            anchors.leftMargin: Math.max(4, 8 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
            anchors.top: parent.top
            spacing: 0

            Repeater {
                model: root.canvasItem ? root.canvasItem.previewInputPorts() : []
                delegate: Item {
                    width: Math.max(40, previewPortsLayer.width * 0.45)
                    height: Math.max(8, 18 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))

                    Rectangle {
                        anchors.left: parent.left
                        anchors.leftMargin: 0
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(5, Math.min(10, 8 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0)))
                        height: width
                        radius: width * 0.5
                        color: "transparent"
                        border.width: 1
                        border.color: root.canvasItem ? root.canvasItem.previewPortColor(modelData.kind) : "#C6D1E1"
                    }

                    Text {
                        visible: root.canvasItem ? root.canvasItem.previewPortLabelsVisible() : false
                        anchors.left: parent.left
                        anchors.leftMargin: Math.max(7, 12 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: String(modelData.label || modelData.key || "")
                        color: "#C6D1E1"
                        font.pixelSize: Math.max(7, Math.min(11, 10 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0)))
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Column {
            id: previewOutputColumn
            anchors.right: parent.right
            anchors.rightMargin: Math.max(4, 8 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
            anchors.top: parent.top
            spacing: 0

            Repeater {
                model: root.canvasItem ? root.canvasItem.previewOutputPorts() : []
                delegate: Item {
                    width: Math.max(40, previewPortsLayer.width * 0.45)
                    height: Math.max(8, 18 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))

                    Rectangle {
                        anchors.right: parent.right
                        anchors.rightMargin: 0
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(5, Math.min(10, 8 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0)))
                        height: width
                        radius: width * 0.5
                        color: "transparent"
                        border.width: 1
                        border.color: root.canvasItem ? root.canvasItem.previewPortColor(modelData.kind) : "#C6D1E1"
                    }

                    Text {
                        visible: root.canvasItem ? root.canvasItem.previewPortLabelsVisible() : false
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.rightMargin: Math.max(7, 12 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0))
                        anchors.verticalCenter: parent.verticalCenter
                        text: String(modelData.label || modelData.key || "")
                        color: "#C6D1E1"
                        font.pixelSize: Math.max(7, Math.min(11, 10 * (root.viewBridge ? root.viewBridge.zoom_value : 1.0)))
                        horizontalAlignment: Text.AlignRight
                        elide: Text.ElideLeft
                    }
                }
            }
        }
    }
}
