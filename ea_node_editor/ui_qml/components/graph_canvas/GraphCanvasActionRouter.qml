import QtQml 2.15

QtObject {
    id: root
    property var canvasItem: null
    property var graphActionBridge: null
    property var canvasCommandBridge: null
    property var addonManagerBridge: null
    property var helpBridge: null
    property var contentFullscreenBridge: null
    property var shellLibraryBridge: null
    property var viewerSessionBridge: null

    readonly property var keyActionDescriptors: ({
        "deleteSelection": { "actionId": "delete_selection" },
        "navigateScopeParent": { "actionId": "navigate_scope_parent" },
        "navigateScopeRoot": { "actionId": "navigate_scope_root" },
        "closeCommentPeek": { "actionId": "close_comment_peek" }
    })

    readonly property var nodeDelegateActionDescriptors: ({
        "enterScope": { "actionId": "enterScope", "payload": "node" },
        "rename": { "actionId": "rename", "payload": "node", "inlineTitleEdit": true },
        "delete": { "actionId": "delete", "payload": "node", "clearEdgeSelection": true },
        "duplicate": { "actionId": "duplicate", "payload": "node" }
    })

    readonly property var edgeContextActionDescriptors: ({
        "editFlowEdge": { "actionId": "edit_flow_edge", "payload": "edge" },
        "editFlowEdgeLabel": { "actionId": "edit_edge_label", "payload": "edge" },
        "resetFlowEdgeStyle": { "actionId": "reset_flow_edge_style", "payload": "edge" },
        "copyFlowEdgeStyle": { "actionId": "copy_flow_edge_style", "payload": "edge" },
        "pasteFlowEdgeStyle": { "actionId": "paste_flow_edge_style", "payload": "edge" },
        "removeEdge": { "actionId": "remove_edge", "payload": "edge", "clearEdgeSelection": true }
    })

    readonly property var nodeContextActionDescriptors: ({
        "openAddonManager": { "actionId": "open_addon_manager", "payload": "node", "requiresSuccess": true },
        "enterSubnode": { "actionId": "enter_subnode", "payload": "node", "requiresSuccess": true },
        "addToWorkflows": { "actionId": "add_to_workflows", "payload": "node" },
        "peekComment": { "actionId": "peek_comment", "payload": "node", "requiresSuccess": true },
        "closeCommentPeek": { "actionId": "exit_comment_peek", "payload": "none", "requiresSuccess": true },
        "editNodeStyle": { "actionId": "edit_node_style", "payload": "node" },
        "resetNodeStyle": { "actionId": "reset_node_style", "payload": "node" },
        "copyNodeStyle": { "actionId": "copy_node_style", "payload": "node" },
        "pasteNodeStyle": { "actionId": "paste_node_style", "payload": "node" },
        "renameNode": {
            "actionId": "rename_node",
            "payload": "node",
            "inlineTitleEdit": true,
            "requiresSuccess": true
        },
        "showHelp": { "actionId": "show_help", "payload": "node" },
        "ungroupSubnode": { "actionId": "ungroup_subnode", "payload": "node" },
        "removeNode": { "actionId": "remove_node", "payload": "node", "clearEdgeSelection": true }
    })

    readonly property var selectionContextActionDescriptors: ({
        "wrapSelectionInCommentBackdrop": { "actionId": "wrap_into_frame", "payload": "none" }
    })

    readonly property var folderExplorerActionDescriptors: ({
        "list": { "actionId": "folder_explorer_list" },
        "navigate": { "actionId": "folder_explorer_navigate" },
        "refresh": { "actionId": "folder_explorer_refresh" },
        "setSort": { "actionId": "folder_explorer_set_sort" },
        "setSearch": { "actionId": "folder_explorer_set_search" },
        "open": { "actionId": "folder_explorer_open" },
        "openInNewWindow": { "actionId": "folder_explorer_open_in_new_window" },
        "newFolder": { "actionId": "folder_explorer_new_folder" },
        "rename": { "actionId": "folder_explorer_rename" },
        "delete": { "actionId": "folder_explorer_delete" },
        "cut": { "actionId": "folder_explorer_cut" },
        "copy": { "actionId": "folder_explorer_copy" },
        "paste": { "actionId": "folder_explorer_paste" },
        "copyPath": { "actionId": "folder_explorer_copy_path" },
        "properties": { "actionId": "folder_explorer_properties" },
        "sendToCorexPathPointer": { "actionId": "folder_explorer_send_to_corex_path_pointer" }
    })

    function descriptorActionId(descriptors, key) {
        var descriptor = descriptors ? descriptors[key] : null;
        return descriptor ? String(descriptor.actionId || "") : "";
    }

    function edgeContextActionId(key) {
        return descriptorActionId(root.edgeContextActionDescriptors, key);
    }

    function nodeContextActionId(key) {
        return descriptorActionId(root.nodeContextActionDescriptors, key);
    }

    function selectionContextActionId(key) {
        return descriptorActionId(root.selectionContextActionDescriptors, key);
    }

    function folderExplorerActionId(key) {
        return descriptorActionId(root.folderExplorerActionDescriptors, key);
    }

    function _descriptorForActionId(descriptors, actionId) {
        var normalized = String(actionId || "").trim();
        if (!normalized || !descriptors)
            return null;
        for (var key in descriptors) {
            if (!Object.prototype.hasOwnProperty.call(descriptors, key))
                continue;
            var descriptor = descriptors[key];
            if (descriptor && String(descriptor.actionId || "") === normalized)
                return descriptor;
        }
        return null;
    }

    function _graphActionBridge() {
        return root.graphActionBridge;
    }

    function triggerGraphAction(actionId, payload) {
        var bridge = root._graphActionBridge();
        if (!bridge || !bridge.trigger_graph_action)
            return false;
        return Boolean(bridge.trigger_graph_action(String(actionId || ""), payload || ({})));
    }

    function _canvasCommandBridge() {
        return root.canvasCommandBridge;
    }

    function requestFolderExplorerAction(actionId, payload) {
        var bridge = root._canvasCommandBridge();
        if (!bridge || !bridge.request_folder_explorer_action) {
            return {
                "success": false,
                "cancelled": false,
                "action_id": String(actionId || ""),
                "node_id": String((payload || ({})).node_id || ""),
                "path": String((payload || ({})).path || ""),
                "error": {
                    "code": "bridge_unavailable",
                    "message": "Folder explorer command bridge is not available.",
                    "operation": String(actionId || ""),
                    "path": String((payload || ({})).path || ""),
                    "target_path": ""
                }
            };
        }
        return bridge.request_folder_explorer_action(String(actionId || ""), payload || ({}));
    }

    function handleFolderExplorerAction(actionId, payload) {
        var result = root.requestFolderExplorerAction(actionId, payload || ({}));
        return Boolean(result && result.success);
    }

    function _nodePayload(nodeId) {
        if (!root.canvasItem || !root.canvasItem._sceneNodePayload)
            return null;
        return root.canvasItem._sceneNodePayload(String(nodeId || "").trim());
    }

    function nodeReadOnly(nodeId) {
        var payload = root._nodePayload(nodeId);
        return !!payload && Boolean(payload.read_only);
    }

    function _nodeLockedState(nodeId) {
        var payload = root._nodePayload(nodeId);
        if (!payload || !payload.locked_state)
            return ({});
        return payload.locked_state;
    }

    function nodeAddonFocusId(nodeId) {
        var payload = root._nodePayload(nodeId);
        if (!payload)
            return "";
        var lockedState = root._nodeLockedState(nodeId);
        return String(lockedState.focus_addon_id || payload.addon_id || "").trim();
    }

    function addonManagerAvailable() {
        return root.addonManagerBridge && root.addonManagerBridge.requestOpen;
    }

    function canOpenAddonManagerForNode(nodeId) {
        return root.addonManagerAvailable() && root.nodeAddonFocusId(nodeId).length > 0;
    }

    function activeCommentPeekNodeId() {
        var bridge = root._canvasCommandBridge();
        if (!bridge || !bridge.active_comment_peek_node_id)
            return "";
        return String(bridge.active_comment_peek_node_id() || "").trim();
    }

    function _isCollapsedCommentBackdrop(payload) {
        return !!payload
            && String(payload.surface_family || "").trim() === "comment_backdrop"
            && Boolean(payload.collapsed);
    }

    function nodeCanPeekInside(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized || root.activeCommentPeekNodeId() === normalized)
            return false;
        if (!root._isCollapsedCommentBackdrop(root._nodePayload(normalized)))
            return false;
        var bridge = root._canvasCommandBridge();
        if (bridge && bridge.can_open_comment_peek)
            return Boolean(bridge.can_open_comment_peek(normalized));
        return true;
    }

    function canShowHelpForNode(nodeId) {
        if (!root.helpBridge || !root.helpBridge.can_show_help_for_node || !root.canvasItem)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        return Boolean(root.helpBridge.can_show_help_for_node(normalized));
    }

    function _payloadForDescriptor(descriptor, actionId) {
        if (!descriptor)
            return null;
        var payloadKind = String(descriptor.payload || "none");
        if (payloadKind === "none")
            return ({});
        if (!root.canvasItem)
            return null;
        if (payloadKind === "edge") {
            var edgeId = String(root.canvasItem.edgeContextEdgeId || "").trim();
            return edgeId.length ? { "edge_id": edgeId } : null;
        }
        if (payloadKind === "node") {
            var nodeId = String(root.canvasItem.nodeContextNodeId || "").trim();
            if (!nodeId.length)
                return null;
            var payload = { "node_id": nodeId };
            if (descriptor.inlineTitleEdit)
                payload.inline_title_edit = true;
            return payload;
        }
        return null;
    }

    function handleEdgeContextAction(actionId) {
        var descriptor = root._descriptorForActionId(root.edgeContextActionDescriptors, actionId);
        var payload = root._payloadForDescriptor(descriptor, actionId);
        if (!payload)
            return false;
        root.triggerGraphAction(actionId, payload);
        if (descriptor.clearEdgeSelection && root.canvasItem) {
            root.canvasItem.selectedEdgeIds = root.canvasItem.selectedEdgeIds.filter(function(value) {
                return value !== payload.edge_id;
            });
        }
        if (root.canvasItem)
            root.canvasItem._closeContextMenus();
        return true;
    }

    function handleNodeContextAction(actionId) {
        var descriptor = root._descriptorForActionId(root.nodeContextActionDescriptors, actionId);
        var payload = root._payloadForDescriptor(descriptor, actionId);
        if (!descriptor || payload === null)
            return false;
        var handled = root.triggerGraphAction(actionId, payload);
        if (descriptor.requiresSuccess && !handled)
            return false;
        if (descriptor.inlineTitleEdit && root.canvasItem) {
            var renameTargetId = root.canvasItem.nodeContextNodeId;
            root.canvasItem._closeContextMenus();
            if (root.canvasItem.requestInlineRenameForNode)
                root.canvasItem.requestInlineRenameForNode(renameTargetId);
            return true;
        }
        if (descriptor.clearEdgeSelection && root.canvasItem)
            root.canvasItem.clearEdgeSelection();
        if (root.canvasItem)
            root.canvasItem._closeContextMenus();
        return true;
    }

    function handleSelectionContextAction(actionId) {
        var descriptor = root._descriptorForActionId(root.selectionContextActionDescriptors, actionId);
        var payload = root._payloadForDescriptor(descriptor, actionId);
        if (!descriptor || payload === null)
            return false;
        root.triggerGraphAction(actionId, payload);
        if (root.canvasItem)
            root.canvasItem._closeContextMenus();
        return true;
    }

    function handleNodeDelegateAction(nodeHost, nodeId, actionId) {
        var normalized = String(actionId || "").trim();
        if (!normalized)
            return false;
        var descriptor = root._descriptorForActionId(root.nodeDelegateActionDescriptors, normalized);
        if (!descriptor) {
            if (nodeHost && nodeHost.dispatchSurfaceAction)
                return Boolean(nodeHost.dispatchSurfaceAction(normalized));
            return false;
        }
        var payload = { "node_id": String(nodeId || "") };
        if (descriptor.inlineTitleEdit)
            payload.inline_title_edit = true;
        var handled = root.triggerGraphAction(descriptor.actionId, payload);
        if (!handled)
            return false;
        if (descriptor.inlineTitleEdit && nodeHost && nodeHost.beginInlineTitleEdit)
            nodeHost.beginInlineTitleEdit();
        if (descriptor.clearEdgeSelection && root.canvasItem)
            root.canvasItem.clearEdgeSelection();
        return true;
    }

    function closeCommentPeekIfActive() {
        if (root.triggerGraphAction(root.keyActionDescriptors.closeCommentPeek.actionId, ({})))
            return true;
        var bridge = root._canvasCommandBridge();
        if (!bridge || !bridge.request_close_comment_peek)
            return false;
        return Boolean(bridge.request_close_comment_peek());
    }

    function deleteSelection(edgeIds) {
        var handled = root.triggerGraphAction(
            root.keyActionDescriptors.deleteSelection.actionId,
            { "edge_ids": edgeIds || [] }
        );
        if (handled)
            return true;
        var bridge = root._canvasCommandBridge();
        if (bridge && bridge.request_delete_selected_graph_items)
            return Boolean(bridge.request_delete_selected_graph_items(edgeIds || []));
        return false;
    }

    function navigateScopeParent() {
        var handled = root.triggerGraphAction(root.keyActionDescriptors.navigateScopeParent.actionId, ({}));
        if (handled)
            return true;
        var bridge = root._canvasCommandBridge();
        return bridge && bridge.request_navigate_scope_parent
            ? Boolean(bridge.request_navigate_scope_parent())
            : false;
    }

    function navigateScopeRoot() {
        var handled = root.triggerGraphAction(root.keyActionDescriptors.navigateScopeRoot.actionId, ({}));
        if (handled)
            return true;
        var bridge = root._canvasCommandBridge();
        return bridge && bridge.request_navigate_scope_root
            ? Boolean(bridge.request_navigate_scope_root())
            : false;
    }

    function clearViewerFocus() {
        if (!root.viewerSessionBridge || !root.viewerSessionBridge.clear_viewer_focus)
            return false;
        root.viewerSessionBridge.clear_viewer_focus();
        return true;
    }

    function _showContentFullscreenHint(message) {
        var normalized = String(message || "Select one media or viewer node for fullscreen.").trim();
        if (!normalized.length)
            normalized = "Select one media or viewer node for fullscreen.";
        if (root.shellLibraryBridge && root.shellLibraryBridge.show_graph_hint) {
            root.shellLibraryBridge.show_graph_hint(normalized, 2400);
            return true;
        }
        return false;
    }

    function _selectedContentFullscreenNodeId() {
        if (!root.canvasItem || !root.canvasItem.selectedNodeIds)
            return "";
        var selected = root.canvasItem.selectedNodeIds() || [];
        if (selected.length !== 1)
            return "";
        return String(selected[0] || "").trim();
    }

    function handleContentFullscreenShortcut() {
        var bridge = root.contentFullscreenBridge;
        if (!bridge)
            return false;
        if (Boolean(bridge.open)) {
            if (bridge.request_close)
                bridge.request_close();
            return true;
        }
        var nodeId = root._selectedContentFullscreenNodeId();
        if (!nodeId.length) {
            root._showContentFullscreenHint("Select one media or viewer node for fullscreen.");
            return true;
        }
        if (bridge.can_open_node && !bridge.can_open_node(nodeId)) {
            if (bridge.request_open_node)
                bridge.request_open_node(nodeId);
            root._showContentFullscreenHint(
                bridge.last_error || "The selected node does not support content fullscreen."
            );
            return true;
        }
        if (bridge.request_open_node && bridge.request_open_node(nodeId))
            return true;
        root._showContentFullscreenHint(
            bridge.last_error || "The selected node does not support content fullscreen."
        );
        return true;
    }
}
