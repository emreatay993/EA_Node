import QtQuick 2.15
import "../graph" as GraphComponents
import "../graph/overlay" as GraphOverlay

Item {
    id: root
    property Item canvasItem: null
    property var sceneStateBridge: null
    property var viewStateBridge: null
    property var viewCommandBridge: null
    property bool minimapSimplificationActive: false
    property alias backgroundLayerItem: backgroundLayer
    property alias edgeLayerItem: edgeLayer

    anchors.fill: parent

    GraphCanvasBackground {
        id: backgroundLayer
        objectName: "graphCanvasBackground"
        anchors.fill: parent
        viewBridge: root.viewStateBridge
        showGrid: root.canvasItem ? root.canvasItem.showGrid : true
        gridStyle: root.canvasItem ? root.canvasItem.gridStyle : "lines"
        degradedWindowActive: root.canvasItem ? root.canvasItem.gridSimplificationActive : false
    }

    GraphCanvasWorldLayer {
        objectName: "graphCanvasBackdropLayer"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
        sceneModel: root.canvasItem ? root.canvasItem._sceneBackdropNodesModel() : []
    }

    GraphComponents.EdgeLayer {
        id: edgeLayer
        objectName: "graphCanvasEdgeLayer"
        anchors.fill: parent
        viewBridge: root.viewStateBridge
        sceneBridge: root.sceneStateBridge
        edges: root.canvasItem ? root.canvasItem.edgePayload : []
        nodes: root.sceneStateBridge ? root.sceneStateBridge.nodes_model : []
        progressedExecutionEdgeLookup: root.canvasItem ? root.canvasItem.progressedExecutionEdgeLookup : ({})
        nodeExecutionRevision: root.canvasItem ? Number(root.canvasItem.nodeExecutionRevision || 0) : 0
        dragOffsets: root.canvasItem ? root.canvasItem.liveDragOffsets : ({})
        liveNodeGeometry: root.canvasItem ? root.canvasItem.liveNodeGeometry : ({})
        selectedEdgeIds: root.canvasItem ? root.canvasItem.selectedEdgeIds : []
        visibleSceneRectPayload: root.canvasItem ? root.canvasItem.visibleSceneRectPayload : ({})
        previewEdgeId: root.canvasItem ? root.canvasItem.dropPreviewEdgeId : ""
        dragConnection: root.canvasItem ? root.canvasItem.wireDragPreviewConnection() : null
        edgeCrossingStyle: root.canvasItem ? root.canvasItem.edgeCrossingStyle : "none"
        performanceMode: root.canvasItem ? root.canvasItem.resolvedGraphicsPerformanceMode : "full_fidelity"
        transientPerformanceActivityActive: root.canvasItem
            ? root.canvasItem.transientPerformanceActivityActive
            : false
        viewportInteractionActive: root.canvasItem
            ? root.canvasItem.viewportInteractionWorldCacheActive
            : false
        transientDegradedWindowActive: root.canvasItem
            ? root.canvasItem.transientDegradedWindowActive
            : false
        edgeLabelSimplificationActive: root.canvasItem ? root.canvasItem.edgeLabelSimplificationActive : false
        inputEnabled: !(root.canvasItem && (
            root.canvasItem.edgeContextVisible
            || root.canvasItem.nodeContextVisible
            || root.canvasItem.selectionContextVisible
        ))

        onEdgeClicked: function(edgeId, additive) {
            if (!root.canvasItem)
                return;
            root.canvasItem.forceActiveFocus();
            if (typeof viewerSessionBridge !== "undefined" && viewerSessionBridge && viewerSessionBridge.clear_viewer_focus)
                viewerSessionBridge.clear_viewer_focus();
            root.canvasItem._closeContextMenus();
            root.canvasItem.clearPendingConnection();
            if (additive)
                root.canvasItem.toggleEdgeSelection(edgeId);
            else
                root.canvasItem.setExclusiveEdgeSelection(edgeId);
        }

        onEdgeContextRequested: function(edgeId, screenX, screenY) {
            if (!root.canvasItem)
                return;
            if (typeof viewerSessionBridge !== "undefined" && viewerSessionBridge && viewerSessionBridge.clear_viewer_focus)
                viewerSessionBridge.clear_viewer_focus();
            root.canvasItem._openEdgeContext(edgeId, screenX, screenY);
        }
    }

    GraphCanvasWorldLayer {
        objectName: "graphCanvasBackdropInputLayer"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
        sceneModel: root.canvasItem ? root.canvasItem._sceneBackdropNodesModel() : []
        backdropInputOverlay: true
    }

    GraphCanvasDropPreview {
        objectName: "graphCanvasDropPreview"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
    }

    GraphCanvasWorldLayer {
        objectName: "graphCanvasWorld"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
        sceneModel: root.sceneStateBridge ? root.sceneStateBridge.nodes_model : []
    }

    GraphOverlay.GraphNodeOverlayToolbarLayer {
        objectName: "graphNodeOverlayToolbarLayer"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
        sceneStateBridge: root.sceneStateBridge
        visibleSceneRectPayload: root.canvasItem ? root.canvasItem.visibleSceneRectPayload : ({})
    }

    GraphCanvasMinimapOverlay {
        objectName: "graphCanvasMinimapOverlay"
        canvasItem: root.canvasItem
        sceneStateBridge: root.sceneStateBridge
        viewStateBridge: root.viewStateBridge
        viewCommandBridge: root.viewCommandBridge
        degradedWindowActive: root.minimapSimplificationActive
    }
}
