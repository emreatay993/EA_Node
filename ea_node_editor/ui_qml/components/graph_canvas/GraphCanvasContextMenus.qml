import QtQuick 2.15

Item {
    id: root
    property Item canvasItem: null
    property var mainWindowBridge: null

    anchors.fill: parent
    z: 900

    Rectangle {
        id: edgeContextPopup
        visible: root.canvasItem ? root.canvasItem.edgeContextVisible : false
        x: root.canvasItem ? root.canvasItem.contextMenuX : 0
        y: root.canvasItem ? root.canvasItem.contextMenuY : 0
        width: 170
        height: 36
        radius: 4
        color: "#2B2F37"
        border.width: 1
        border.color: "#4A4E58"

        Rectangle {
            anchors.fill: parent
            color: removeEdgeMouse.containsMouse ? "#39404C" : "transparent"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Remove Connection"
                color: "#D8DEEA"
                font.pixelSize: 12
            }

            MouseArea {
                id: removeEdgeMouse
                anchors.fill: parent
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                onPressed: {
                    if (!root.mainWindowBridge || !root.canvasItem || !root.canvasItem.edgeContextEdgeId)
                        return;
                    root.mainWindowBridge.request_remove_edge(root.canvasItem.edgeContextEdgeId);
                    root.canvasItem.selectedEdgeIds = root.canvasItem.selectedEdgeIds.filter(function(value) {
                        return value !== root.canvasItem.edgeContextEdgeId;
                    });
                    root.canvasItem._closeContextMenus();
                    mouse.accepted = true;
                }
            }
        }
    }

    Rectangle {
        id: nodeContextPopup
        visible: root.canvasItem ? root.canvasItem.nodeContextVisible : false
        x: root.canvasItem ? root.canvasItem.contextMenuX : 0
        y: root.canvasItem ? root.canvasItem.contextMenuY : 0
        width: 170
        property bool canEnterScope: root.canvasItem
            ? root.canvasItem._nodeCanEnterScope(root.canvasItem.nodeContextNodeId)
            : false
        property int rowHeight: 36
        property int rowCount: canEnterScope ? 4 : 2
        height: rowHeight * rowCount
        radius: 4
        color: "#2B2F37"
        border.width: 1
        border.color: "#4A4E58"

        Rectangle {
            visible: nodeContextPopup.canEnterScope
            x: 0
            y: 0
            width: parent.width
            height: nodeContextPopup.rowHeight
            color: openSubnodeMouse.containsMouse ? "#39404C" : "transparent"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Enter Subnode"
                color: "#D8DEEA"
                font.pixelSize: 12
            }

            MouseArea {
                id: openSubnodeMouse
                anchors.fill: parent
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                onPressed: {
                    if (!root.canvasItem || !root.canvasItem.nodeContextNodeId)
                        return;
                    if (root.canvasItem.requestOpenSubnodeScope(root.canvasItem.nodeContextNodeId))
                        mouse.accepted = true;
                }
            }
        }

        Rectangle {
            visible: nodeContextPopup.canEnterScope
            x: 0
            y: nodeContextPopup.rowHeight
            width: parent.width
            height: nodeContextPopup.rowHeight
            color: addToWorkflowsMouse.containsMouse ? "#39404C" : "transparent"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Add to Workflows"
                color: "#D8DEEA"
                font.pixelSize: 12
            }

            MouseArea {
                id: addToWorkflowsMouse
                anchors.fill: parent
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                onPressed: {
                    if (!root.mainWindowBridge || !root.canvasItem || !root.canvasItem.nodeContextNodeId)
                        return;
                    root.mainWindowBridge.request_publish_custom_workflow_from_node(root.canvasItem.nodeContextNodeId);
                    root.canvasItem._closeContextMenus();
                    mouse.accepted = true;
                }
            }
        }

        Rectangle {
            x: 0
            y: nodeContextPopup.canEnterScope ? nodeContextPopup.rowHeight * 2 : 0
            width: parent.width
            height: nodeContextPopup.rowHeight
            color: renameNodeMouse.containsMouse ? "#39404C" : "transparent"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Rename Node"
                color: "#D8DEEA"
                font.pixelSize: 12
            }

            MouseArea {
                id: renameNodeMouse
                anchors.fill: parent
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                onPressed: {
                    if (!root.mainWindowBridge || !root.canvasItem || !root.canvasItem.nodeContextNodeId)
                        return;
                    root.mainWindowBridge.request_rename_node(root.canvasItem.nodeContextNodeId);
                    root.canvasItem._closeContextMenus();
                    mouse.accepted = true;
                }
            }
        }

        Rectangle {
            x: 0
            y: nodeContextPopup.canEnterScope ? nodeContextPopup.rowHeight * 3 : nodeContextPopup.rowHeight
            width: parent.width
            height: nodeContextPopup.rowHeight
            color: removeNodeMouse.containsMouse ? "#39404C" : "transparent"

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: "Remove Node"
                color: "#D8DEEA"
                font.pixelSize: 12
            }

            MouseArea {
                id: removeNodeMouse
                anchors.fill: parent
                hoverEnabled: true
                preventStealing: true
                acceptedButtons: Qt.LeftButton
                onPressed: {
                    if (!root.mainWindowBridge || !root.canvasItem || !root.canvasItem.nodeContextNodeId)
                        return;
                    root.mainWindowBridge.request_remove_node(root.canvasItem.nodeContextNodeId);
                    root.canvasItem.clearEdgeSelection();
                    root.canvasItem._closeContextMenus();
                    mouse.accepted = true;
                }
            }
        }
    }
}
