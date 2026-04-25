import QtQuick 2.15
import "../shell" as ShellComponents

Item {
    id: root
    property Item canvasItem: null
    property var canvasActionRouter: null
    property var commandBridge: null
    property var graphActionBridge: null
    property var addonManagerBridge: null
    property var helpBridge: null
    property var themePalette: ({})

    anchors.fill: parent
    z: 900

    GraphCanvasActionRouter {
        id: fallbackActionRouter
        canvasItem: root.canvasItem
        graphActionBridge: root.graphActionBridge
        canvasCommandBridge: root.commandBridge
        addonManagerBridge: root.addonManagerBridge
        helpBridge: root.helpBridge
    }

    function _actionRouter() {
        return root.canvasActionRouter || fallbackActionRouter;
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

    function _triggerGraphAction(actionId, payload) {
        var actionRouter = root._actionRouter();
        if (actionRouter && actionRouter.triggerGraphAction)
            return Boolean(actionRouter.triggerGraphAction(actionId, payload || ({})));
        if (!root.graphActionBridge || !root.graphActionBridge.trigger_graph_action)
            return false;
        return Boolean(root.graphActionBridge.trigger_graph_action(actionId, payload || ({})));
    }

    function _edgeActionId(key) {
        var actionRouter = root._actionRouter();
        return actionRouter && actionRouter.edgeContextActionId
            ? actionRouter.edgeContextActionId(key)
            : "";
    }

    function _nodeActionId(key) {
        var actionRouter = root._actionRouter();
        return actionRouter && actionRouter.nodeContextActionId
            ? actionRouter.nodeContextActionId(key)
            : "";
    }

    function _selectionActionId(key) {
        var actionRouter = root._actionRouter();
        return actionRouter && actionRouter.selectionContextActionId
            ? actionRouter.selectionContextActionId(key)
            : "";
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
            { "actionId": root._edgeActionId("editFlowEdge"), "text": "Edit Flow Edge...", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": root._edgeActionId("editFlowEdgeLabel"), "text": "Edit Label...", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": root._edgeActionId("resetFlowEdgeStyle"), "text": "Reset Style", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": root._edgeActionId("copyFlowEdgeStyle"), "text": "Copy Style", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": root._edgeActionId("pasteFlowEdgeStyle"), "text": "Paste Style", "visible": edgeContextPopup.isFlowEdge },
            { "actionId": root._edgeActionId("removeEdge"), "text": "Remove Connection", "destructive": true }
        ]
        onActionTriggered: function(actionId) {
            var actionRouter = root._actionRouter();
            if (actionRouter && actionRouter.handleEdgeContextAction)
                actionRouter.handleEdgeContextAction(actionId)
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
        readonly property bool canPeekComment: root._actionRouter().nodeCanPeekInside(root.canvasItem ? root.canvasItem.nodeContextNodeId : "")
        readonly property bool isPeekedComment: root.canvasItem
            ? root._actionRouter().activeCommentPeekNodeId() === String(root.canvasItem.nodeContextNodeId || "").trim()
            : false
        readonly property bool canOpenAddonManager: nodeContextPopup.isReadOnlyNode
            && root._actionRouter().canOpenAddonManagerForNode(root.canvasItem ? root.canvasItem.nodeContextNodeId : "")
        readonly property bool canShowHelp: {
            if (!root.canvasItem)
                return false;
            var nodeId = String(root.canvasItem.nodeContextNodeId || "").trim();
            if (!nodeId.length)
                return false;
            return Boolean(root._actionRouter().canShowHelpForNode(nodeId));
        }
        actions: [
            { "actionId": root._nodeActionId("openAddonManager"), "text": "Open Add-On Manager", "visible": nodeContextPopup.canOpenAddonManager },
            { "actionId": root._nodeActionId("enterSubnode"), "text": "Enter Subnode", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canEnterScope },
            { "actionId": root._nodeActionId("addToWorkflows"), "text": "Add to Workflows", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canEnterScope },
            { "actionId": root._nodeActionId("peekComment"), "text": "Peek Inside", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canPeekComment },
            { "actionId": root._nodeActionId("closeCommentPeek"), "text": "Exit Peek", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPeekedComment },
            { "actionId": root._nodeActionId("editNodeStyle"), "text": "Edit Style...", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPassiveNode },
            { "actionId": root._nodeActionId("resetNodeStyle"), "text": "Reset Style", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPassiveNode },
            { "actionId": root._nodeActionId("copyNodeStyle"), "text": "Copy Style", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPassiveNode },
            { "actionId": root._nodeActionId("pasteNodeStyle"), "text": "Paste Style", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.isPassiveNode },
            { "actionId": root._nodeActionId("renameNode"), "text": "Rename Node", "visible": !nodeContextPopup.isReadOnlyNode },
            { "actionId": root._nodeActionId("showHelp"), "text": "Help", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canShowHelp },
            { "actionId": root._nodeActionId("ungroupSubnode"), "text": "Ungroup Subnode", "visible": !nodeContextPopup.isReadOnlyNode && nodeContextPopup.canEnterScope, "destructive": true },
            { "actionId": root._nodeActionId("removeNode"), "text": "Remove Node", "visible": !nodeContextPopup.isReadOnlyNode, "destructive": true }
        ]
        onActionTriggered: function(actionId) {
            var actionRouter = root._actionRouter();
            if (actionRouter && actionRouter.handleNodeContextAction)
                actionRouter.handleNodeContextAction(actionId)
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
            { "actionId": root._selectionActionId("wrapSelectionInCommentBackdrop"), "text": "Wrap into frame", "visible": selectionContextPopup.hasMultiNodeSelection }
        ]
        onActionTriggered: function(actionId) {
            var actionRouter = root._actionRouter();
            if (actionRouter && actionRouter.handleSelectionContextAction)
                actionRouter.handleSelectionContextAction(actionId)
        }
    }
}
