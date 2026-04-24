import QtQuick 2.15
import "../shell" as ShellComponents

Item {
    id: root
    property Item canvasItem: null
    property var commandBridge: null
    property var graphActionBridge: null
    readonly property var shellContextRef: typeof shellContext !== "undefined" ? shellContext : null
    readonly property var themeBridgeRef: root.shellContextRef ? root.shellContextRef.themeBridge : null
    readonly property var addonManagerBridgeRef: root.shellContextRef ? root.shellContextRef.addonManagerBridge : null
    readonly property var helpBridgeRef: root.shellContextRef ? root.shellContextRef.helpBridge : null
    readonly property var themePalette: root.themeBridgeRef ? root.themeBridgeRef.palette : ({})

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

    function _nodeReadOnly(nodeId) {
        var payload = root._nodePayload(nodeId);
        return !!payload && Boolean(payload.read_only);
    }

    function _nodeLockedState(nodeId) {
        var payload = root._nodePayload(nodeId);
        if (!payload || !payload.locked_state)
            return ({});
        return payload.locked_state;
    }

    function _nodeAddonFocusId(nodeId) {
        var payload = root._nodePayload(nodeId);
        if (!payload)
            return "";
        var lockedState = root._nodeLockedState(nodeId);
        return String(lockedState.focus_addon_id || payload.addon_id || "").trim();
    }

    function _addonManagerAvailable() {
        return root.addonManagerBridgeRef
            && root.addonManagerBridgeRef.requestOpen;
    }

    function _triggerGraphAction(actionId, payload) {
        if (!root.graphActionBridge || !root.graphActionBridge.trigger_graph_action)
            return false;
        return Boolean(root.graphActionBridge.trigger_graph_action(actionId, payload || ({})));
    }

    function _edgeActionPayload(actionId) {
        var edgeId = root.canvasItem ? String(root.canvasItem.edgeContextEdgeId || "").trim() : "";
        if (!edgeId.length)
            return null;
        if ([
            "edit_flow_edge",
            "edit_edge_label",
            "reset_flow_edge_style",
            "copy_flow_edge_style",
            "paste_flow_edge_style",
            "remove_edge"
        ].indexOf(actionId) < 0) {
            return null;
        }
        return { "edge_id": edgeId };
    }

    function _nodeActionPayload(actionId) {
        var nodeId = root.canvasItem ? String(root.canvasItem.nodeContextNodeId || "").trim() : "";
        if (!nodeId.length)
            return null;
        if ([
            "open_addon_manager",
            "enter_subnode",
            "add_to_workflows",
            "peek_comment",
            "edit_node_style",
            "reset_node_style",
            "copy_node_style",
            "paste_node_style",
            "rename_node",
            "show_help",
            "ungroup_subnode",
            "remove_node"
        ].indexOf(actionId) < 0) {
            return null;
        }
        return { "node_id": nodeId };
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
            if (!root.canvasItem)
                return
            var payload = root._edgeActionPayload(actionId)
            if (!payload)
                return
            root._triggerGraphAction(actionId, payload)
            if (actionId === "remove_edge") {
                root.canvasItem.selectedEdgeIds = root.canvasItem.selectedEdgeIds.filter(function(value) {
                    return value !== payload.edge_id
                })
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
        minimumWidth: nodeContextPopup.isReadOnlyNode ? 210 : 188
        property bool canEnterScope: root.canvasItem
            ? root.canvasItem._nodeCanEnterScope(root.canvasItem.nodeContextNodeId)
            : false
        readonly property bool isReadOnlyNode: root.canvasItem
            ? root._nodeReadOnly(root.canvasItem.nodeContextNodeId)
            : false
        readonly property bool isPassiveNode: root.canvasItem
            ? root.canvasItem._nodeSupportsPassiveStyle(root.canvasItem.nodeContextNodeId)
            : false
        readonly property bool canPeekComment: root._nodeCanPeekInside(root.canvasItem ? root.canvasItem.nodeContextNodeId : "")
        readonly property bool isPeekedComment: root.canvasItem
            ? root._activeCommentPeekNodeId() === String(root.canvasItem.nodeContextNodeId || "").trim()
            : false
        readonly property bool canOpenAddonManager: nodeContextPopup.isReadOnlyNode
            && root._addonManagerAvailable()
            && root._nodeAddonFocusId(root.canvasItem ? root.canvasItem.nodeContextNodeId : "").length > 0
        readonly property bool canShowHelp: {
            if (!root.helpBridgeRef)
                return false;
            if (!root.canvasItem)
                return false;
            var nodeId = String(root.canvasItem.nodeContextNodeId || "").trim();
            if (!nodeId.length)
                return false;
            return Boolean(root.helpBridgeRef.can_show_help_for_node(nodeId));
        }
        actions: [
            { "actionId": "open_addon_manager", "text": "Open Add-On Manager", "visible": nodeContextPopup.canOpenAddonManager },
            { "actionId": "enter_subnode", "text": "Enter Subnode", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canEnterScope },
            { "actionId": "add_to_workflows", "text": "Add to Workflows", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canEnterScope },
            { "actionId": "peek_comment", "text": "Peek Inside", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canPeekComment },
            { "actionId": "exit_comment_peek", "text": "Exit Peek", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPeekedComment },
            { "actionId": "edit_node_style", "text": "Edit Style...", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPassiveNode },
            { "actionId": "reset_node_style", "text": "Reset Style", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPassiveNode },
            { "actionId": "copy_node_style", "text": "Copy Style", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPassiveNode },
            { "actionId": "paste_node_style", "text": "Paste Style", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPassiveNode },
            { "actionId": "rename_node", "text": "Rename Node", "visible": !nodeContextPopup.isReadOnlyNode },
            { "actionId": "show_help", "text": "Help", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canShowHelp },
            { "actionId": "ungroup_subnode", "text": "Ungroup Subnode", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canEnterScope, "destructive": true },
            { "actionId": "remove_node", "text": "Remove Node", "visible": !nodeContextPopup.isReadOnlyNode, "destructive": true }
        ]
        onActionTriggered: function(actionId) {
            if (!root.canvasItem)
                return
            var payload = root._nodeActionPayload(actionId)
            if (actionId === "add_to_workflows") {
                if (!payload)
                    return
                root._triggerGraphAction(actionId, payload)
            } else if (actionId === "peek_comment") {
                if (!payload || !root._triggerGraphAction(actionId, payload))
                    return
            } else if (actionId === "exit_comment_peek") {
                if (!root._triggerGraphAction(actionId, ({})))
                    return
            } else if (actionId === "open_addon_manager" || actionId === "enter_subnode") {
                if (!payload || !root._triggerGraphAction(actionId, payload))
                    return
            } else if (actionId === "edit_node_style") {
                if (!payload)
                    return
                root._triggerGraphAction(actionId, payload)
            } else if (actionId === "reset_node_style") {
                if (!payload)
                    return
                root._triggerGraphAction(actionId, payload)
            } else if (actionId === "copy_node_style") {
                if (!payload)
                    return
                root._triggerGraphAction(actionId, payload)
            } else if (actionId === "paste_node_style") {
                if (!payload)
                    return
                root._triggerGraphAction(actionId, payload)
            } else if (actionId === "rename_node") {
                if (!payload)
                    return
                payload.inline_title_edit = true
                if (!root._triggerGraphAction(actionId, payload))
                    return
                // Close the menu first so the node host regains focus cleanly,
                // then begin inline title editing in the header (same gesture
                // as double-clicking the node name). Return early to skip the
                // trailing _closeContextMenus() since we already closed it.
                var renameTargetId = root.canvasItem.nodeContextNodeId
                root.canvasItem._closeContextMenus()
                if (root.canvasItem.requestInlineRenameForNode)
                    root.canvasItem.requestInlineRenameForNode(renameTargetId)
                return
            } else if (actionId === "show_help") {
                if (root.helpBridgeRef)
                    root._triggerGraphAction(actionId, payload)
            } else if (actionId === "ungroup_subnode") {
                if (!payload)
                    return
                root._triggerGraphAction(actionId, payload)
            } else if (actionId === "remove_node") {
                if (!payload)
                    return
                root._triggerGraphAction(actionId, payload)
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
            if (!root.canvasItem)
                return
            if (actionId === "wrap_into_frame") {
                root._triggerGraphAction(actionId, ({}))
            } else {
                return
            }
            root.canvasItem._closeContextMenus()
        }
    }
}
