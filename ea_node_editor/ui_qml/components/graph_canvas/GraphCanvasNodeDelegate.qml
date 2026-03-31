import QtQuick 2.15
import "../graph" as GraphComponents
import "GraphCanvasLogic.js" as GraphCanvasLogic

GraphComponents.GraphNodeHost {
    id: nodeCard
    property bool backdropInputOverlay: false
    readonly property bool _commentBackdropNode: canvasItem ? canvasItem._isCommentBackdropPayload(modelData) : false

    objectName: nodeCard.backdropInputOverlay ? "graphCommentBackdropInputCard" : "graphNodeCard"
    nodeData: modelData
    worldOffset: canvasItem ? canvasItem.worldOffset : 0.0
    hoveredPort: canvasItem ? canvasItem.hoveredPort : null
    previewPort: canvasItem ? canvasItem.dropPreviewPort : null
    pendingPort: canvasItem ? canvasItem.pendingConnectionPort : null
    dragSourcePort: canvasItem ? canvasItem.wireDragSourcePort() : null
    liveDragDx: canvasItem ? canvasItem.liveDragDxForNode(modelData.node_id) : 0.0
    liveDragDy: canvasItem ? canvasItem.liveDragDyForNode(modelData.node_id) : 0.0
    showShadow: nodeCard.backdropInputOverlay ? false : (canvasItem ? canvasItem.nodeShadowEnabled : false)
    shadowStrength: nodeCard._commentBackdropNode
        ? Math.max(10, Math.round(Number(canvasItem ? canvasItem.shadowStrength : 70) * 0.26))
        : Number(canvasItem ? canvasItem.shadowStrength : 70)
    shadowSoftness: nodeCard._commentBackdropNode
        ? Math.max(78, Math.round(Number(canvasItem ? canvasItem.shadowSoftness : 50) * 1.45))
        : Number(canvasItem ? canvasItem.shadowSoftness : 50)
    shadowOffset: nodeCard._commentBackdropNode
        ? Math.max(1, Math.round(Number(canvasItem ? canvasItem.shadowOffset : 4) * 0.5))
        : Number(canvasItem ? canvasItem.shadowOffset : 4)
    viewportInteractionCacheActive: canvasItem ? canvasItem.viewportInteractionWorldCacheActive : false
    snapshotReuseActive: canvasItem
        ? (canvasItem.snapshotProxyReuseActive && !canvasItem.viewportInteractionWorldCacheActive)
        : false
    shadowSimplificationActive: canvasItem ? canvasItem.shadowSimplificationActive : false
    fullFidelityMode: canvasItem ? canvasItem.fullFidelityMode : true
    renderActivationSceneRectPayload: canvasItem ? canvasItem.nodeRenderActivationSceneRectPayload : ({})
    contextTargetNodeId: canvasItem ? canvasItem.nodeContextNodeId : ""
    showPortLabelsPreference: canvasItem ? canvasItem.showPortLabels : true
    surfaceVariantOverride: nodeCard.backdropInputOverlay ? "comment_backdrop_input_overlay" : ""
    opacity: nodeCard.backdropInputOverlay
        ? (nodeCard.renderActive ? 1.0 : 0.001)
        : 1.0

    onNodeClicked: function(nodeId, additive) {
        if (!canvasItem)
            return;
        var bridge = canvasItem._canvasSceneCommandBridgeRef;
        canvasItem.forceActiveFocus();
        if (typeof viewerSessionBridge !== "undefined" && viewerSessionBridge && viewerSessionBridge.clear_viewer_focus)
            viewerSessionBridge.clear_viewer_focus();
        canvasItem._closeContextMenus();
        canvasItem.clearPendingConnection();
        if (!bridge || !bridge.select_node)
            return;
        if (!additive)
            canvasItem.clearEdgeSelection();
        bridge.select_node(nodeId, additive);
    }
    onNodeContextRequested: function(nodeId, localX, localY) {
        if (!canvasItem)
            return;
        var point = nodeCard.mapToItem(canvasItem, localX, localY);
        canvasItem._openNodeContext(nodeId, point.x, point.y);
    }
    onNodeOpenRequested: function(nodeId) {
        if (canvasItem)
            canvasItem.requestOpenSubnodeScope(nodeId);
    }
    onDragOffsetChanged: function(nodeId, dx, dy) {
        if (!canvasItem)
            return;
        canvasItem.setLiveDragOffsets(
            canvasItem.dragNodeIdsForAnchor(nodeId),
            Number(dx),
            Number(dy)
        );
    }
    onDragFinished: function(nodeId, finalX, finalY, _moved) {
        if (!canvasItem)
            return;
        var bridge = canvasItem._canvasSceneCommandBridgeRef;
        var dragNodeIds = canvasItem.dragNodeIdsForAnchor(nodeId);
        var anchorPayload = canvasItem._sceneNodePayload(nodeId);
        var anchorX = anchorPayload ? Number(anchorPayload.x) : Number(finalX);
        var anchorY = anchorPayload ? Number(anchorPayload.y) : Number(finalY);
        if (!isFinite(anchorX))
            anchorX = Number(finalX);
        if (!isFinite(anchorY))
            anchorY = Number(finalY);
        var rawDeltaX = Number(finalX) - anchorX;
        var rawDeltaY = Number(finalY) - anchorY;
        var snappedDelta = canvasItem.snappedDragDelta(nodeId, rawDeltaX, rawDeltaY);
        var deltaX = Number(snappedDelta.dx);
        var deltaY = Number(snappedDelta.dy);
        if (!isFinite(deltaX))
            deltaX = 0.0;
        if (!isFinite(deltaY))
            deltaY = 0.0;
        var finalSnappedX = anchorX + deltaX;
        var finalSnappedY = anchorY + deltaY;
        var movedByCommit = Math.abs(deltaX) >= 0.01 || Math.abs(deltaY) >= 0.01;

        canvasItem.clearLiveDragOffsets();
        if (!bridge)
            return;
        if (dragNodeIds.length > 1) {
            movedByCommit = bridge.move_nodes_by_delta ? bridge.move_nodes_by_delta(dragNodeIds, deltaX, deltaY) : false;
            if (movedByCommit)
                canvasItem.clearEdgeSelection();
            return;
        }

        if (bridge.move_node)
            bridge.move_node(nodeId, finalSnappedX, finalSnappedY);
        if (movedByCommit && bridge.select_node) {
            canvasItem.clearEdgeSelection();
            bridge.select_node(nodeId, false);
        }
    }
    onDragCanceled: function(_nodeId) {
        if (canvasItem)
            canvasItem.clearLiveDragOffsets();
    }
    onResizePreviewChanged: function(nodeId, newX, newY, newWidth, newHeight, active) {
        if (canvasItem)
            canvasItem.setLiveNodeGeometry(nodeId, newX, newY, newWidth, newHeight, active);
    }
    onResizeFinished: function(nodeId, newX, newY, newWidth, newHeight) {
        if (!canvasItem)
            return;
        var bridge = canvasItem._canvasSceneCommandBridgeRef;
        canvasItem.setLiveNodeGeometry(nodeId, newX, newY, newWidth, newHeight, false);
        if (!bridge)
            return;
        if (bridge.set_node_geometry) {
            bridge.set_node_geometry(nodeId, newX, newY, newWidth, newHeight);
            return;
        }
        if (bridge.move_node)
            bridge.move_node(nodeId, newX, newY);
        if (bridge.resize_node)
            bridge.resize_node(nodeId, newWidth, newHeight);
    }
    onPortClicked: function(nodeId, portKey, direction, sceneX, sceneY) {
        if (canvasItem)
            canvasItem.handlePortClick(nodeId, portKey, direction, sceneX, sceneY);
    }
    onPortDragStarted: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY) {
        if (canvasItem)
            canvasItem.beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY);
    }
    onPortDragMoved: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive) {
        if (canvasItem)
            canvasItem.updatePortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive);
    }
    onPortDragFinished: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive) {
        if (canvasItem)
            canvasItem.finishPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive);
    }
    onPortDragCanceled: function(_nodeId, _portKey, _direction) {
        if (canvasItem)
            canvasItem.cancelWireDrag();
    }
    onPortHoverChanged: function(nodeId, portKey, direction, sceneX, sceneY, hovered) {
        if (!canvasItem || (canvasItem.wireDragState && canvasItem.wireDragState.active))
            return;
        if (hovered) {
            var hoveredPortData = canvasItem._scenePortData(nodeId, portKey);
            var hoveredDirection = String(
                hoveredPortData && hoveredPortData.direction !== undefined
                    ? hoveredPortData.direction
                    : direction
            ).trim().toLowerCase();
            var hoveredSide = GraphCanvasLogic.normalizedPortSide(
                hoveredPortData && hoveredPortData.side !== undefined
                    ? hoveredPortData.side
                    : portKey
            );
            canvasItem.hoveredPort = {
                "node_id": nodeId,
                "port_key": portKey,
                "direction": hoveredDirection,
                "kind": hoveredPortData ? String(hoveredPortData.kind || "") : "",
                "data_type": hoveredPortData ? String(hoveredPortData.data_type || "") : "",
                "allow_multiple_connections": hoveredPortData ? Boolean(hoveredPortData.allow_multiple_connections) : false,
                "scene_x": sceneX,
                "scene_y": sceneY,
                "valid_drop": false
            };
            if (hoveredSide)
                canvasItem.hoveredPort.side = hoveredSide;
            if (canvasItem.requestEdgeRedraw)
                canvasItem.requestEdgeRedraw();
        } else if (
            canvasItem.hoveredPort
            && canvasItem.hoveredPort.node_id === nodeId
            && canvasItem.hoveredPort.port_key === portKey
        ) {
            canvasItem.hoveredPort = null;
            if (canvasItem.requestEdgeRedraw)
                canvasItem.requestEdgeRedraw();
        }
    }
    onSurfaceControlInteractionStarted: function(nodeId) {
        if (canvasItem)
            canvasItem.prepareNodeSurfaceControlInteraction(nodeId);
    }
    onInlinePropertyCommitted: function(nodeId, key, value) {
        if (canvasItem && canvasItem.commitNodeSurfaceProperty(nodeId, key, value))
            canvasItem.forceActiveFocus();
    }
    onPortLabelCommitted: function(nodeId, portKey, label) {
        if (canvasItem && canvasItem.commitNodePortLabel(nodeId, portKey, label))
            canvasItem.forceActiveFocus();
    }
}
