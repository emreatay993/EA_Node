import QtQml 2.15

QtObject {
    id: root
    property var canvasItem: null

    function _sceneSelectionBridge() {
        var bridge = root.canvasItem ? root.canvasItem._canvasSceneCommandBridgeRef : null;
        if (bridge && bridge.select_node)
            return bridge;
        return null;
    }

    function _pendingActionBridge() {
        var bridge = root.canvasItem ? root.canvasItem._canvasSceneCommandBridgeRef : null;
        if (bridge && bridge.set_pending_surface_action && bridge.consume_pending_surface_action)
            return bridge;
        return null;
    }

    function _propertyBridge() {
        var bridge = root.canvasItem ? root.canvasItem._canvasSceneCommandBridgeRef : null;
        if (bridge && bridge.set_node_properties)
            return bridge;
        return null;
    }

    function _cursorBridge() {
        var bridge = root.canvasItem ? root.canvasItem._canvasShellCommandBridgeRef : null;
        if (bridge && bridge.set_graph_cursor_shape && bridge.clear_graph_cursor_shape)
            return bridge;
        return null;
    }

    function _pdfPreviewBridge() {
        var bridge = root.canvasItem ? root.canvasItem._canvasShellCommandBridgeRef : null;
        if (bridge && bridge.describe_pdf_preview)
            return bridge;
        return null;
    }

    function requestOpenSubnodeScope(nodeId) {
        if (!root.canvasItem)
            return false;
        var bridge = root.canvasItem._canvasShellCommandBridgeRef;
        if (!bridge || !bridge.request_open_subnode_scope)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        var opened = bridge.request_open_subnode_scope(normalized);
        if (!opened)
            return false;
        root.canvasItem.clearEdgeSelection();
        root.canvasItem.clearPendingConnection();
        root.canvasItem._closeContextMenus();
        return true;
    }

    function prepareNodeSurfaceControlInteraction(nodeId) {
        if (!root.canvasItem)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        root.canvasItem._closeContextMenus();
        root.canvasItem.cancelWireDrag();
        root.canvasItem.clearPendingConnection();
        root.canvasItem.clearEdgeSelection();
        var bridge = root.canvasItem._canvasSceneCommandBridgeRef;
        if (bridge && bridge.select_node)
            bridge.select_node(normalized, false);
        return true;
    }

    function commitNodeSurfaceProperty(nodeId, key, value) {
        if (!root.canvasItem)
            return false;
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedKey = String(key || "").trim();
        if (!normalizedNodeId || !normalizedKey)
            return false;
        root.prepareNodeSurfaceControlInteraction(normalizedNodeId);
        var bridge = root.canvasItem._canvasSceneCommandBridgeRef;
        if (!bridge || !bridge.set_node_property)
            return false;
        bridge.set_node_property(normalizedNodeId, normalizedKey, value);
        return true;
    }

    function commitNodePortLabel(nodeId, portKey, label) {
        if (!root.canvasItem)
            return false;
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedPortKey = String(portKey || "").trim();
        if (!normalizedNodeId || !normalizedPortKey)
            return false;
        root.prepareNodeSurfaceControlInteraction(normalizedNodeId);
        var bridge = root.canvasItem._canvasSceneCommandBridgeRef;
        if (!bridge || !bridge.set_node_port_label)
            return false;
        bridge.set_node_port_label(normalizedNodeId, normalizedPortKey, String(label || ""));
        return true;
    }

    function requestNodeSurfaceCropEdit(nodeId) {
        if (!root.canvasItem)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        var selectionBridge = root._sceneSelectionBridge();
        var needsSelection = root.canvasItem.selectedNodeIds().indexOf(normalized) < 0;
        if (needsSelection) {
            var pendingBridge = root._pendingActionBridge();
            if (!selectionBridge || !pendingBridge)
                return false;
            root.canvasItem._closeContextMenus();
            root.canvasItem.cancelWireDrag();
            root.canvasItem.clearPendingConnection();
            root.canvasItem.clearEdgeSelection();
            pendingBridge.set_pending_surface_action(normalized);
            selectionBridge.select_node(normalized, false);
            return false;
        }
        root.prepareNodeSurfaceControlInteraction(normalized);
        return true;
    }

    function consumePendingNodeSurfaceAction(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        var bridge = root._pendingActionBridge();
        if (!bridge)
            return false;
        return Boolean(bridge.consume_pending_surface_action(normalized));
    }

    function commitNodeSurfaceProperties(nodeId, properties) {
        if (!root.canvasItem)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        root.prepareNodeSurfaceControlInteraction(normalized);
        var bridge = root._propertyBridge();
        if (bridge)
            return Boolean(bridge.set_node_properties(normalized, properties || ({})));
        bridge = root.canvasItem._canvasSceneCommandBridgeRef;
        if (!bridge || !bridge.set_node_property)
            return false;
        var changed = false;
        var payload = properties || ({});
        for (var key in payload) {
            if (!Object.prototype.hasOwnProperty.call(payload, key))
                continue;
            bridge.set_node_property(normalized, key, payload[key]);
            changed = true;
        }
        return changed;
    }

    function setNodeSurfaceCursorShape(cursorShape) {
        var bridge = root._cursorBridge();
        if (!bridge)
            return false;
        bridge.set_graph_cursor_shape(cursorShape);
        return true;
    }

    function clearNodeSurfaceCursorShape() {
        var bridge = root._cursorBridge();
        if (!bridge)
            return false;
        bridge.clear_graph_cursor_shape();
        return true;
    }

    function describeNodeSurfacePdfPreview(source, pageNumber) {
        var bridge = root._pdfPreviewBridge();
        if (!bridge)
            return ({});
        return bridge.describe_pdf_preview(String(source || ""), pageNumber);
    }

    function browseNodePropertyPath(nodeId, key, currentPath) {
        if (!root.canvasItem)
            return "";
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedKey = String(key || "").trim();
        var bridge = root.canvasItem._canvasShellCommandBridgeRef;
        if (!normalizedNodeId || !normalizedKey || !bridge || !bridge.browse_node_property_path)
            return "";
        root.prepareNodeSurfaceControlInteraction(normalizedNodeId);
        return String(bridge.browse_node_property_path(
            normalizedNodeId,
            normalizedKey,
            String(currentPath || "")
        ) || "");
    }
}
