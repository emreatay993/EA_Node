import QtQuick 2.15
import "../shell" as ShellComponents

Item {
    id: root
    property Item canvasItem: null
    property var commandBridge: null
    readonly property var themePalette: themeBridge.palette

    anchors.fill: parent
    z: 900

    function _activeCommentPeekNodeId() {
        if (!root.commandBridge || !root.commandBridge.active_comment_peek_node_id)
            return "";
        return String(root.commandBridge.active_comment_peek_node_id() || "").trim();
    }

    function _nodePayload(nodeId) {
        if (!root.canvasItem || !root.canvasItem._sceneNodePayload)
            return null;
        return root.canvasItem._sceneNodePayload(nodeId);
    }

    function _isCollapsedCommentBackdrop(payload) {
        return !!payload
            && String(payload.surface_family || "").trim() === "comment_backdrop"
            && Boolean(payload.collapsed);
    }

    function _nodeCanPeekInside(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized || root._activeCommentPeekNodeId() === normalized)
            return false;
        if (!root._isCollapsedCommentBackdrop(root._nodePayload(normalized)))
            return false;
        if (root.commandBridge && root.commandBridge.can_open_comment_peek)
            return Boolean(root.commandBridge.can_open_comment_peek(normalized));
        return true;
    }

    ShellComponents.ShellContextMenu {
        id: edgeContextPopup
        objectName: "graphCanvasEdgeContextPopup"
        visible: root.canvasItem ? root.canvasItem.edgeContextVisible : false
        x: root.canvasItem ? root.canvasItem.contextMenuX : 0
        y: root.canvasItem ? root.canvasItem.contextMenuY : 0
        minimumWidth: 198
        readonly property var edgePayload: root.canvasItem
            ? root.canvasItem._sceneEdgePayload(root.canvasItem.edgeContextEdgeId)
            : null
        readonly property bool isFlowEdge: edgePayload
            ? String(edgePayload.edge_family || "").toLowerCase() === "flow"
            : false
        actions: [
            { "actionId": "edit_flow_edge", "text": "Edit Flow Edge...", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": "edit_edge_label", "text": "Edit Label...", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": "reset_flow_edge_style", "text": "Reset Style", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": "copy_flow_edge_style", "text": "Copy Style", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": "paste_flow_edge_style", "text": "Paste Style", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": "remove_edge", "text": "Remove Connection", "destructive": true }
        ]
        onActionTriggered: function(actionId) {
            if (!root.commandBridge || !root.canvasItem || !root.canvasItem.edgeContextEdgeId)
                return
            if (actionId === "edit_flow_edge") {
                root.commandBridge.request_edit_flow_edge_style(root.canvasItem.edgeContextEdgeId)
            } else if (actionId === "edit_edge_label") {
                root.commandBridge.request_edit_flow_edge_label(root.canvasItem.edgeContextEdgeId)
            } else if (actionId === "reset_flow_edge_style") {
                root.commandBridge.request_reset_flow_edge_style(root.canvasItem.edgeContextEdgeId)
            } else if (actionId === "copy_flow_edge_style") {
                root.commandBridge.request_copy_flow_edge_style(root.canvasItem.edgeContextEdgeId)
            } else if (actionId === "paste_flow_edge_style") {
                root.commandBridge.request_paste_flow_edge_style(root.canvasItem.edgeContextEdgeId)
            } else if (actionId === "remove_edge") {
                root.commandBridge.request_remove_edge(root.canvasItem.edgeContextEdgeId)
                root.canvasItem.selectedEdgeIds = root.canvasItem.selectedEdgeIds.filter(function(value) {
                    return value !== root.canvasItem.edgeContextEdgeId
                })
            } else {
                return
            }
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
        readonly property bool isPassiveNode: root.canvasItem
            ? root.canvasItem._nodeSupportsPassiveStyle(root.canvasItem.nodeContextNodeId)
            : false
        readonly property bool canPeekComment: root._nodeCanPeekInside(root.canvasItem ? root.canvasItem.nodeContextNodeId : "")
        readonly property bool isPeekedComment: root.canvasItem
            ? root._activeCommentPeekNodeId() === String(root.canvasItem.nodeContextNodeId || "").trim()
            : false
        actions: [
            { "actionId": "enter_subnode", "text": "Enter Subnode", "visible": nodeContextPopup.canEnterScope },
            { "actionId": "add_to_workflows", "text": "Add to Workflows", "visible": nodeContextPopup.canEnterScope },
            { "actionId": "peek_comment", "text": "Peek Inside", "visible": nodeContextPopup.canPeekComment },
            { "actionId": "exit_comment_peek", "text": "Exit Peek", "visible": nodeContextPopup.isPeekedComment },
            { "actionId": "edit_node_style", "text": "Edit Style...", "visible": nodeContextPopup.isPassiveNode },
            { "actionId": "reset_node_style", "text": "Reset Style", "visible": nodeContextPopup.isPassiveNode },
            { "actionId": "copy_node_style", "text": "Copy Style", "visible": nodeContextPopup.isPassiveNode },
            { "actionId": "paste_node_style", "text": "Paste Style", "visible": nodeContextPopup.isPassiveNode },
            { "actionId": "rename_node", "text": "Rename Node" },
            { "actionId": "ungroup_subnode", "text": "Ungroup Subnode", "visible": nodeContextPopup.canEnterScope, "destructive": true },
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
            if (!root.commandBridge || !root.canvasItem.nodeContextNodeId)
                return
            if (actionId === "add_to_workflows") {
                root.commandBridge.request_publish_custom_workflow_from_node(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "peek_comment") {
                if (!root.commandBridge.request_open_comment_peek(root.canvasItem.nodeContextNodeId))
                    return
            } else if (actionId === "exit_comment_peek") {
                if (!root.commandBridge.request_close_comment_peek())
                    return
            } else if (actionId === "edit_node_style") {
                root.commandBridge.request_edit_passive_node_style(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "reset_node_style") {
                root.commandBridge.request_reset_passive_node_style(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "copy_node_style") {
                root.commandBridge.request_copy_passive_node_style(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "paste_node_style") {
                root.commandBridge.request_paste_passive_node_style(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "rename_node") {
                root.commandBridge.request_rename_node(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "ungroup_subnode") {
                root.commandBridge.request_ungroup_node(root.canvasItem.nodeContextNodeId)
            } else if (actionId === "remove_node") {
                root.commandBridge.request_remove_node(root.canvasItem.nodeContextNodeId)
                root.canvasItem.clearEdgeSelection()
            } else {
                return
            }
            root.canvasItem._closeContextMenus()
        }
    }

    ShellComponents.ShellContextMenu {
        id: selectionContextPopup
        objectName: "graphCanvasSelectionContextPopup"
        visible: root.canvasItem ? root.canvasItem.selectionContextVisible : false
        x: root.canvasItem ? root.canvasItem.contextMenuX : 0
        y: root.canvasItem ? root.canvasItem.contextMenuY : 0
        minimumWidth: 188
        readonly property bool hasMultiNodeSelection: root.canvasItem
            ? root.canvasItem.selectedNodeIds().length > 1
            : false
        actions: [
            { "actionId": "wrap_into_frame", "text": "Wrap into frame", "visible": selectionContextPopup.hasMultiNodeSelection }
        ]
        onActionTriggered: function(actionId) {
            if (!root.commandBridge || !root.canvasItem)
                return
            if (actionId === "wrap_into_frame") {
                root.commandBridge.request_wrap_selected_nodes_in_comment_backdrop()
            } else {
                return
            }
            root.canvasItem._closeContextMenus()
        }
    }
}
