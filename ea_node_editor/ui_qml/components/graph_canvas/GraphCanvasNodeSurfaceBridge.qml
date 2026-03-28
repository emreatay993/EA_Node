import QtQuick 2.15

Item {
    id: root
    property var canvasItem: null
    visible: false
    width: 0
    height: 0

    GraphCanvasSurfaceInteractionHost {
        id: hostInteraction
        canvasItem: root.canvasItem
    }

    function _sceneSelectionBridge() {
        return hostInteraction.sceneSelectionBridge();
    }

    function _pendingActionBridge() {
        return hostInteraction.pendingActionBridge();
    }

    function _propertyBridge() {
        return hostInteraction.propertyBridge();
    }

    function _cursorBridge() {
        return hostInteraction.cursorBridge();
    }

    function _pdfPreviewBridge() {
        return hostInteraction.pdfPreviewBridge();
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
        hostInteraction.clearCanvasSelectionState();
        return true;
    }

    function prepareNodeSurfaceControlInteraction(nodeId) {
        if (!root.canvasItem)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        hostInteraction.resetSurfaceInteractionState();
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
        var needsSelection = hostInteraction.selectedNodeIds().indexOf(normalized) < 0;
        if (needsSelection) {
            var pendingBridge = root._pendingActionBridge();
            if (!selectionBridge || !pendingBridge)
                return false;
            hostInteraction.resetSurfaceInteractionState();
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
