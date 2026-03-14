import QtQuick 2.15
import "../shell" as ShellComponents

Item {
    id: root
    property Item canvasItem: null
    property var mainWindowBridge: null
    readonly property var themePalette: themeBridge.palette

    anchors.fill: parent
    z: 900

    ShellComponents.ShellContextMenu {
        id: edgeContextPopup
        objectName: "graphCanvasEdgeContextPopup"
        visible: root.canvasItem ? root.canvasItem.edgeContextVisible : false
        x: root.canvasItem ? root.canvasItem.contextMenuX : 0
        y: root.canvasItem ? root.canvasItem.contextMenuY : 0
        minimumWidth: 198
        actions: [
            { "actionId": "remove_edge", "text": "Remove Connection", "destructive": true }
        ]
        onActionTriggered: function(actionId) {
            if (actionId !== "remove_edge" || !root.mainWindowBridge || !root.canvasItem || !root.canvasItem.edgeContextEdgeId)
                return
            root.mainWindowBridge.request_remove_edge(root.canvasItem.edgeContextEdgeId)
            root.canvasItem.selectedEdgeIds = root.canvasItem.selectedEdgeIds.filter(function(value) {
                return value !== root.canvasItem.edgeContextEdgeId
            })
            root.canvasItem._closeContextMenus()
        }
    }

    ShellComponents.ShellContextMenu {
        id: nodeContextPopup
        objectName: "graphCanvasNodeContextPopup"
        visible: root.canvasItem ? root.canvasItem.nodeContextVisible : false
        x: root.canvasItem ? root.canvasItem.contextMenuX : 0
        y: root.canvasItem ? root.canvasItem.contextMenuY : 0
        minimumWidth: 188
        property bool canEnterScope: root.canvasItem
            ? root.canvasItem._nodeCanEnterScope(root.canvasItem.nodeContextNodeId)
            : false
        actions: nodeContextPopup.canEnterScope
            ? [
                { "actionId": "enter_subnode", "text": "Enter Subnode" },
                { "actionId": "add_to_workflows", "text": "Add to Workflows" },
                { "actionId": "rename_node", "text": "Rename Node" },
                { "actionId": "remove_node", "text": "Remove Node", "destructive": true }
            ]
            : [
                { "actionId": "rename_node", "text": "Rename Node" },
                { "actionId": "remove_node", "text": "Remove Node", "destructive": true }
            ]
        onActionTriggered: function(actionId) {
            if (!root.canvasItem)
                return
            if (actionId === "enter_subnode") {
                if (!root.canvasItem.nodeContextNodeId)
                    return
                if (root.canvasItem.requestOpenSubnodeScope(root.canvasItem.nodeContextNodeId))
                    root.canvasItem._closeContextMenus()
                return
            }
            if (!root.mainWindowBridge || !root.canvasItem.nodeContextNodeId)
                return
            if (actionId === "add_to_workflows") {
                root.mainWindowBridge.request_publish_custom_workflow_from_node(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "rename_node") {
                root.mainWindowBridge.request_rename_node(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "remove_node") {
                root.mainWindowBridge.request_remove_node(root.canvasItem.nodeContextNodeId)
                root.canvasItem.clearEdgeSelection()
            } else {
                return
            }
            root.canvasItem._closeContextMenus()
        }
    }
}
