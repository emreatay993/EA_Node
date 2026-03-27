import QtQuick 2.15
import QtQml 2.15
import "graph" as GraphComponents
import "graph_canvas" as GraphCanvasComponents
import "graph_canvas/GraphCanvasLogic.js" as GraphCanvasLogic
import "graph_canvas/GraphCanvasPerformancePolicy.js" as GraphCanvasPerformancePolicyLogic

Item {
    id: root
    objectName: "graphCanvas"
    property var canvasStateBridge: null
    property var canvasCommandBridge: null
    readonly property var canvasStateBridgeRef: root.canvasStateBridge || null
    readonly property var canvasCommandBridgeRef: root.canvasCommandBridge || null
    readonly property var _canvasStateBridgeRef: root.canvasStateBridgeRef
    readonly property var _canvasSceneStateBridgeRef: root.canvasStateBridgeRef
    readonly property var _canvasViewStateBridgeRef: root.canvasStateBridgeRef
        && root.canvasStateBridgeRef.viewport_bridge
        ? root.canvasStateBridgeRef.viewport_bridge
        : null
    readonly property var _canvasShellCommandBridgeRef: root.canvasCommandBridgeRef
    readonly property var _canvasSceneCommandBridgeRef: root.canvasCommandBridgeRef
    readonly property var _canvasViewCommandBridgeRef: root.canvasCommandBridgeRef
        && root.canvasCommandBridgeRef.viewport_bridge
        ? root.canvasCommandBridgeRef.viewport_bridge
        : null
    readonly property var sceneBridge: root._canvasSceneStateBridgeRef
    readonly property var viewBridge: root._canvasViewStateBridgeRef
    property var overlayHostItem: null
    property var edgePayload: []
    readonly property var visibleSceneRectPayload: root._canvasViewStateBridgeRef
        ? (root._canvasViewStateBridgeRef.visible_scene_rect_payload_cached !== undefined
            ? root._canvasViewStateBridgeRef.visible_scene_rect_payload_cached
            : root._canvasViewStateBridgeRef.visible_scene_rect_payload)
        : ({})
    readonly property real nodeRenderActivationPaddingPx: 240.0
    readonly property var nodeRenderActivationSceneRectPayload: root._inflateSceneRectPayload(
        root.visibleSceneRectPayload,
        root._scenePaddingForViewportPixels(root.nodeRenderActivationPaddingPx)
    )
    property bool minimapExpanded: root._canvasStateBridgeRef ? Boolean(root._canvasStateBridgeRef.graphics_minimap_expanded) : true
    readonly property bool showGrid: root._canvasStateBridgeRef ? Boolean(root._canvasStateBridgeRef.graphics_show_grid) : true
    readonly property bool minimapVisible: root._canvasStateBridgeRef ? Boolean(root._canvasStateBridgeRef.graphics_show_minimap) : true
    readonly property bool showPortLabels: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.graphics_show_port_labels)
        : true
    readonly property bool nodeShadowEnabled: root._canvasStateBridgeRef ? Boolean(root._canvasStateBridgeRef.graphics_node_shadow) : true
    readonly property int shadowStrength: root._canvasStateBridgeRef ? root._canvasStateBridgeRef.graphics_shadow_strength : 70
    readonly property int shadowSoftness: root._canvasStateBridgeRef ? root._canvasStateBridgeRef.graphics_shadow_softness : 50
    readonly property int shadowOffset: root._canvasStateBridgeRef ? root._canvasStateBridgeRef.graphics_shadow_offset : 4
    readonly property string graphicsPerformanceMode: root._canvasStateBridgeRef
        ? GraphCanvasPerformancePolicyLogic.normalizePerformanceMode(
            root._canvasStateBridgeRef.graphics_performance_mode
        )
        : "full_fidelity"
    readonly property string resolvedGraphicsPerformanceMode: canvasPerformancePolicy.resolvedMode
    readonly property bool mutationBurstActive: canvasPerformancePolicy.mutationBurstActive
    readonly property bool transientPerformanceActivityActive: canvasPerformancePolicy.transientActivityActive
    readonly property bool transientDegradedWindowActive: canvasPerformancePolicy.transientDegradedWindowActive
    readonly property bool edgeLabelSimplificationActive: canvasPerformancePolicy.edgeLabelSimplificationActive
        || root.transientDegradedWindowActive
    readonly property bool gridSimplificationActive: canvasPerformancePolicy.gridSimplificationActive
        || root.transientDegradedWindowActive
    readonly property bool minimapSimplificationActive: canvasPerformancePolicy.minimapSimplificationActive
        || root.transientDegradedWindowActive
    readonly property bool shadowSimplificationActive: canvasPerformancePolicy.shadowSimplificationActive
        || (canvasPerformancePolicy.maxPerformanceMode && root.mutationBurstActive)
    readonly property bool snapshotProxyReuseActive: canvasPerformancePolicy.snapshotProxyReuseActive
        || root.transientDegradedWindowActive
    readonly property bool fullFidelityMode: canvasPerformancePolicy.fullFidelityMode
    readonly property bool viewportInteractionWorldCacheActive: canvasPerformancePolicy.viewportWorldCacheActive
    readonly property bool highQualityRendering: canvasPerformancePolicy.highQualityRendering
        && !root.transientDegradedWindowActive
    readonly property int interactionIdleDelayMs: 150
    readonly property real wireDragThreshold: 2
    readonly property real worldSize: 12000
    readonly property real worldOffset: worldSize / 2
    readonly property real minimapExpandedWidth: 238
    readonly property real minimapExpandedHeight: 162
    readonly property real minimapCollapsedWidth: 28
    readonly property real minimapCollapsedHeight: 28

    GraphCanvasComponents.GraphCanvasInteractionState {
        id: interactionState
        canvasItem: root
        shellBridge: root._canvasShellCommandBridgeRef
        sceneBridge: root._canvasSceneStateBridgeRef
        edgeLayerItem: edgeLayer
        interactionIdleTimer: interactionIdleTimer
        interactionIdleDelayMs: root.interactionIdleDelayMs
        wireDragThreshold: root.wireDragThreshold
    }

    GraphCanvasComponents.GraphCanvasSceneState {
        id: sceneState
        canvasItem: root
        edgeLayerItem: edgeLayer
    }

    GraphCanvasComponents.GraphCanvasNodeSurfaceBridge {
        id: nodeSurfaceBridge
        canvasItem: root
    }

    QtObject {
        id: canvasPerformancePolicy
        objectName: "graphCanvasPerformancePolicy"
        property bool mutationBurstActive: false
        readonly property var resolvedPolicy: GraphCanvasPerformancePolicyLogic.resolvePerformancePolicy(
            root.graphicsPerformanceMode,
            interactionState.interactionActive,
            mutationBurstActive
        )
        readonly property string resolvedMode: resolvedPolicy.resolvedMode
        readonly property bool fullFidelityMode: resolvedPolicy.fullFidelityMode
        readonly property bool maxPerformanceMode: resolvedPolicy.maxPerformanceMode
        readonly property bool viewportInteractionActive: resolvedPolicy.viewportInteractionActive
        readonly property bool transientActivityActive: resolvedPolicy.transientActivityActive
        readonly property bool transientDegradedWindowActive: resolvedPolicy.transientDegradedWindowActive
        readonly property bool viewportWorldCacheActive: resolvedPolicy.viewportWorldCacheActive
        readonly property bool highQualityRendering: resolvedPolicy.highQualityRendering
        readonly property bool gridSimplificationActive: resolvedPolicy.gridSimplificationActive
        readonly property bool minimapSimplificationActive: resolvedPolicy.minimapSimplificationActive
        readonly property bool edgeLabelSimplificationActive: resolvedPolicy.edgeLabelSimplificationActive
        readonly property bool shadowSimplificationActive: resolvedPolicy.shadowSimplificationActive
        readonly property bool snapshotProxyReuseActive: resolvedPolicy.snapshotProxyReuseActive

        function noteStructuralMutation() {
            if (!mutationBurstActive)
                mutationBurstActive = true;
            structuralMutationIdleTimer.restart();
        }

        function clearStructuralMutation() {
            structuralMutationIdleTimer.stop();
            mutationBurstActive = false;
        }
    }

    Timer {
        id: structuralMutationIdleTimer
        interval: root.interactionIdleDelayMs
        repeat: false
        onTriggered: canvasPerformancePolicy.mutationBurstActive = false
    }

    property alias hoveredPort: interactionState.hoveredPort
    property alias dropPreviewPort: interactionState.dropPreviewPort
    property alias dropPreviewEdgeId: interactionState.dropPreviewEdgeId
    property alias dropPreviewNodePayload: interactionState.dropPreviewNodePayload
    property alias dropPreviewScreenX: interactionState.dropPreviewScreenX
    property alias dropPreviewScreenY: interactionState.dropPreviewScreenY
    property alias pendingConnectionPort: interactionState.pendingConnectionPort
    property alias wireDragState: interactionState.wireDragState
    property alias wireDropCandidate: interactionState.wireDropCandidate
    property alias edgeContextVisible: interactionState.edgeContextVisible
    property alias nodeContextVisible: interactionState.nodeContextVisible
    property alias edgeContextEdgeId: interactionState.edgeContextEdgeId
    property alias nodeContextNodeId: interactionState.nodeContextNodeId
    property alias contextMenuX: interactionState.contextMenuX
    property alias contextMenuY: interactionState.contextMenuY
    property alias interactionActive: interactionState.interactionActive
    property alias liveDragOffsets: sceneState.liveDragOffsets
    property alias liveNodeGeometry: sceneState.liveNodeGeometry
    property alias selectedEdgeIds: sceneState.selectedEdgeIds

    focus: true
    activeFocusOnTab: true
    Keys.forwardTo: [inputLayers]
    clip: true

    function toggleMinimapExpanded() {
        var nextExpanded = !root.minimapExpanded;
        var bridge = root._canvasShellCommandBridgeRef;
        if (bridge && bridge.set_graphics_minimap_expanded) {
            bridge.set_graphics_minimap_expanded(nextExpanded);
            return;
        }
        root.minimapExpanded = nextExpanded;
    }

    function beginViewportInteraction() {
        interactionState.beginViewportInteraction();
    }

    function finishViewportInteractionSoon() {
        interactionState.finishViewportInteractionSoon();
    }

    function noteViewportInteraction() {
        interactionState.noteViewportInteraction();
    }

    Timer {
        id: interactionIdleTimer
        interval: root.interactionIdleDelayMs
        repeat: false
        onTriggered: interactionState.endViewportInteraction()
    }

    Timer {
        id: viewStateRedrawFlushTimer
        interval: 0
        repeat: false
        onTriggered: root.flushViewStateRedraw()
    }

    function screenToSceneX(screenX) {
        var view = root._canvasViewStateBridgeRef;
        return GraphCanvasLogic.screenToSceneX(
            screenX,
            (view ? view.center_x : 0.0),
            root.width,
            (view ? view.zoom_value : 1.0)
        );
    }

    function screenToSceneY(screenY) {
        var view = root._canvasViewStateBridgeRef;
        return GraphCanvasLogic.screenToSceneY(
            screenY,
            (view ? view.center_y : 0.0),
            root.height,
            (view ? view.zoom_value : 1.0)
        );
    }

    function _wheelDeltaY(eventObj) {
        return GraphCanvasLogic.wheelDeltaY(eventObj);
    }

    function applyWheelZoom(eventObj) {
        var viewCommand = root._canvasViewCommandBridgeRef;
        if (!viewCommand)
            return false;
        var deltaY = _wheelDeltaY(eventObj);
        if (Math.abs(deltaY) < 0.001)
            return false;
        root.noteViewportInteraction();

        var cursorX = Number(eventObj && eventObj.x);
        var cursorY = Number(eventObj && eventObj.y);
        var hasCursor = isFinite(cursorX) && isFinite(cursorY);
        var sceneBeforeX = 0.0;
        var sceneBeforeY = 0.0;
        if (hasCursor) {
            sceneBeforeX = screenToSceneX(cursorX);
            sceneBeforeY = screenToSceneY(cursorY);
        }

        var steps = deltaY / 120.0;
        if (Math.abs(steps) < 0.01)
            steps = deltaY > 0 ? 1.0 : -1.0;
        steps = Math.max(-1.0, Math.min(1.0, steps));
        var factor = Math.pow(1.15, steps);
        if (hasCursor && viewCommand.adjust_zoom_at_viewport_point) {
            viewCommand.adjust_zoom_at_viewport_point(factor, cursorX, cursorY);
            return true;
        }

        if (viewCommand.adjust_zoom)
            viewCommand.adjust_zoom(factor);

        if (hasCursor) {
            var sceneAfterX = screenToSceneX(cursorX);
            var sceneAfterY = screenToSceneY(cursorY);
            if (viewCommand.pan_by)
                viewCommand.pan_by(sceneBeforeX - sceneAfterX, sceneBeforeY - sceneAfterY);
        }
        return true;
    }

    function sceneToScreenX(sceneX) {
        var view = root._canvasViewStateBridgeRef;
        return GraphCanvasLogic.sceneToScreenX(
            sceneX,
            (view ? view.center_x : 0.0),
            root.width,
            (view ? view.zoom_value : 1.0)
        );
    }

    function sceneToScreenY(sceneY) {
        var view = root._canvasViewStateBridgeRef;
        return GraphCanvasLogic.sceneToScreenY(
            sceneY,
            (view ? view.center_y : 0.0),
            root.height,
            (view ? view.zoom_value : 1.0)
        );
    }

    function _normalizedSceneRectPayload(rectLike) {
        if (rectLike === undefined || rectLike === null)
            return null;

        var x = Number(rectLike.x);
        var y = Number(rectLike.y);
        var width = Number(rectLike.width);
        var height = Number(rectLike.height);
        if (!isFinite(x) || !isFinite(y) || !isFinite(width) || !isFinite(height))
            return null;

        if (width < 0.0) {
            x += width;
            width = Math.abs(width);
        }
        if (height < 0.0) {
            y += height;
            height = Math.abs(height);
        }

        return {
            "x": x,
            "y": y,
            "width": width,
            "height": height
        };
    }

    function _scenePaddingForViewportPixels(paddingPx) {
        var zoom = root._canvasViewStateBridgeRef ? Number(root._canvasViewStateBridgeRef.zoom_value) : 1.0;
        if (!isFinite(zoom) || zoom <= 0.0001)
            zoom = 1.0;

        var padding = Number(paddingPx);
        if (!isFinite(padding) || padding < 0.0)
            padding = 0.0;
        return padding / zoom;
    }

    function _inflateSceneRectPayload(rectLike, padding) {
        var normalized = root._normalizedSceneRectPayload(rectLike);
        if (!normalized)
            return ({});

        var resolvedPadding = Number(padding);
        if (!isFinite(resolvedPadding) || resolvedPadding < 0.0)
            resolvedPadding = 0.0;

        return {
            "x": normalized.x - resolvedPadding,
            "y": normalized.y - resolvedPadding,
            "width": normalized.width + (resolvedPadding * 2.0),
            "height": normalized.height + (resolvedPadding * 2.0)
        };
    }

    function snapToGridEnabled() {
        return root._canvasStateBridgeRef ? Boolean(root._canvasStateBridgeRef.snap_to_grid_enabled) : false;
    }

    function snapGridSize() {
        return GraphCanvasLogic.normalizeSnapGridSize(root._canvasStateBridgeRef ? root._canvasStateBridgeRef.snap_grid_size : 20.0);
    }

    function snapToGridValue(value) {
        return GraphCanvasLogic.snapToGridValue(value, root.snapGridSize());
    }

    function snappedDragDelta(nodeId, rawDx, rawDy) {
        return GraphCanvasLogic.snappedDragDelta(
            rawDx,
            rawDy,
            root.snapToGridEnabled(),
            root._sceneNodePayload(nodeId),
            root.snapGridSize()
        );
    }

    function _normalizeEdgeIds(values) {
        return sceneState.normalizeEdgeIds(values);
    }

    function _availableEdgeIdSet() {
        return sceneState.availableEdgeIdSet();
    }

    function pruneSelectedEdges() {
        sceneState.pruneSelectedEdges();
    }

    function clearEdgeSelection() {
        sceneState.clearEdgeSelection();
    }

    function toggleEdgeSelection(edgeId) {
        sceneState.toggleEdgeSelection(edgeId);
    }

    function setExclusiveEdgeSelection(edgeId) {
        sceneState.setExclusiveEdgeSelection(edgeId);
    }

    function _sceneNodePayload(nodeId) {
        return sceneState.sceneNodePayload(nodeId);
    }

    function _sceneBackdropNodesModel() {
        return sceneState.sceneBackdropNodesModel();
    }

    function _sceneAllNodesModel() {
        return sceneState.sceneAllNodesModel();
    }

    function _sceneEdgePayload(edgeId) {
        return sceneState.sceneEdgePayload(edgeId);
    }

    function _nodeSupportsPassiveStyle(nodeId) {
        return sceneState.nodeSupportsPassiveStyle(nodeId);
    }

    function _edgeSupportsFlowStyle(edgeId) {
        return sceneState.edgeSupportsFlowStyle(edgeId);
    }

    function _nodeCanEnterScope(nodeId) {
        return sceneState.nodeCanEnterScope(nodeId);
    }

    function requestOpenSubnodeScope(nodeId) {
        return nodeSurfaceBridge.requestOpenSubnodeScope(nodeId);
    }

    function _nodeSurfaceSelectionBridge() {
        return nodeSurfaceBridge._sceneSelectionBridge();
    }

    function _nodeSurfacePendingActionBridge() {
        return nodeSurfaceBridge._pendingActionBridge();
    }

    function _nodeSurfacePropertyBridge() {
        return nodeSurfaceBridge._propertyBridge();
    }

    function _nodeSurfaceCursorBridge() {
        return nodeSurfaceBridge._cursorBridge();
    }

    function _nodeSurfacePdfPreviewBridge() {
        return nodeSurfaceBridge._pdfPreviewBridge();
    }

    function prepareNodeSurfaceControlInteraction(nodeId) {
        return nodeSurfaceBridge.prepareNodeSurfaceControlInteraction(nodeId);
    }

    function commitNodeSurfaceProperty(nodeId, key, value) {
        return nodeSurfaceBridge.commitNodeSurfaceProperty(nodeId, key, value);
    }

    function commitNodePortLabel(nodeId, portKey, label) {
        return nodeSurfaceBridge.commitNodePortLabel(nodeId, portKey, label);
    }

    function requestNodeSurfaceCropEdit(nodeId) {
        return nodeSurfaceBridge.requestNodeSurfaceCropEdit(nodeId);
    }

    function consumePendingNodeSurfaceAction(nodeId) {
        return nodeSurfaceBridge.consumePendingNodeSurfaceAction(nodeId);
    }

    function commitNodeSurfaceProperties(nodeId, properties) {
        return nodeSurfaceBridge.commitNodeSurfaceProperties(nodeId, properties);
    }

    function setNodeSurfaceCursorShape(cursorShape) {
        return nodeSurfaceBridge.setNodeSurfaceCursorShape(cursorShape);
    }

    function clearNodeSurfaceCursorShape() {
        return nodeSurfaceBridge.clearNodeSurfaceCursorShape();
    }

    function describeNodeSurfacePdfPreview(source, pageNumber) {
        return nodeSurfaceBridge.describeNodeSurfacePdfPreview(source, pageNumber);
    }

    function browseNodePropertyPath(nodeId, key, currentPath) {
        return nodeSurfaceBridge.browseNodePropertyPath(nodeId, key, currentPath);
    }

    function selectedNodeIds() {
        return sceneState.selectedNodeIds();
    }

    function _appendUniqueDragNodeId(nodeIds, seenNodeIds, nodeId) {
        sceneState._appendUniqueDragNodeId(nodeIds, seenNodeIds, nodeId);
    }

    function _payloadNodeIdList(payload, key) {
        return sceneState._payloadNodeIdList(payload, key);
    }

    function _isCommentBackdropPayload(payload) {
        return sceneState.isCommentBackdropPayload(payload);
    }

    function _appendBackdropDragDescendants(nodeIds, seenNodeIds, backdropNodeId) {
        sceneState._appendBackdropDragDescendants(nodeIds, seenNodeIds, backdropNodeId);
    }

    function _appendBackdropAwareDragNodeIds(nodeIds, seenNodeIds, nodeId) {
        sceneState._appendBackdropAwareDragNodeIds(nodeIds, seenNodeIds, nodeId);
    }

    function dragNodeIdsForAnchor(nodeId) {
        return sceneState.dragNodeIdsForAnchor(nodeId);
    }

    function setLiveDragOffsets(nodeIds, dx, dy) {
        sceneState.setLiveDragOffsets(nodeIds, dx, dy);
    }

    function clearLiveDragOffsets() {
        sceneState.clearLiveDragOffsets();
    }

    function liveDragDxForNode(nodeId) {
        return sceneState.liveDragDxForNode(nodeId);
    }

    function liveDragDyForNode(nodeId) {
        return sceneState.liveDragDyForNode(nodeId);
    }

    function setLiveNodeGeometry(nodeId, x, y, width, height, active) {
        sceneState.setLiveNodeGeometry(nodeId, x, y, width, height, active);
    }

    function clearLiveNodeGeometry() {
        sceneState.clearLiveNodeGeometry();
    }

    function _dropTargetInput(sourceDrag, candidate) {
        return interactionState._dropTargetInput(sourceDrag, candidate);
    }

    function _isExactDuplicate(sourceDrag, candidate, edge) {
        return interactionState._isExactDuplicate(sourceDrag, candidate, edge);
    }

    function _portKind(nodeId, portKey) {
        return interactionState._portKind(nodeId, portKey);
    }

    function _portDataType(nodeId, portKey) {
        return interactionState._portDataType(nodeId, portKey);
    }

    function _arePortKindsCompatible(sourceKind, targetKind) {
        return interactionState._arePortKindsCompatible(sourceKind, targetKind);
    }

    function _isDropAllowed(sourceDrag, candidate) {
        return interactionState._isDropAllowed(sourceDrag, candidate);
    }

    function _nearestDropCandidateForWireDrag(screenX, screenY, sourceDrag, thresholdOverride) {
        return interactionState._nearestDropCandidateForWireDrag(
            screenX,
            screenY,
            sourceDrag,
            thresholdOverride
        );
    }

    function _areDataTypesCompatible(sourceType, targetType) {
        return interactionState._areDataTypesCompatible(sourceType, targetType);
    }

    function _portsCompatibleForAuto(sourcePort, targetPort) {
        return interactionState._portsCompatibleForAuto(sourcePort, targetPort);
    }

    function _libraryPorts(payload) {
        return interactionState._libraryPorts(payload);
    }

    function _scenePortData(nodeId, portKey) {
        return interactionState._scenePortData(nodeId, portKey);
    }

    function _scenePortPoint(node, port, inputRow, outputRow) {
        return interactionState._scenePortPoint(node, port, inputRow, outputRow);
    }

    function _hasCompatiblePortForTarget(targetPort, nodePorts) {
        return interactionState._hasCompatiblePortForTarget(targetPort, nodePorts);
    }

    function _portDropTargetAtScreen(screenX, screenY, payload) {
        return interactionState._portDropTargetAtScreen(screenX, screenY, payload);
    }

    function _edgeSupportsDrop(edgeId, payload) {
        return interactionState._edgeSupportsDrop(edgeId, payload);
    }

    function _computeLibraryDropTarget(screenX, screenY, payload) {
        return interactionState._computeLibraryDropTarget(screenX, screenY, payload);
    }

    function _previewNodeMetrics(payload) {
        return interactionState._previewNodeMetrics(payload);
    }

    function previewNodeMetrics() {
        return interactionState.previewNodeMetrics();
    }

    function _previewVisiblePorts(payload, direction) {
        return interactionState._previewVisiblePorts(payload, direction);
    }

    function previewInputPorts() {
        return interactionState.previewInputPorts();
    }

    function previewOutputPorts() {
        return interactionState.previewOutputPorts();
    }

    function previewPortColor(kind) {
        return interactionState.previewPortColor(kind);
    }

    function previewNodeScreenWidth() {
        return interactionState.previewNodeScreenWidth();
    }

    function previewNodeScreenHeight() {
        return interactionState.previewNodeScreenHeight();
    }

    function previewPortLabelsVisible() {
        return interactionState.previewPortLabelsVisible();
    }

    function clearLibraryDropPreview() {
        interactionState.clearLibraryDropPreview();
    }

    function updateLibraryDropPreview(screenX, screenY, payload) {
        interactionState.updateLibraryDropPreview(screenX, screenY, payload);
    }

    function isPointInCanvas(screenX, screenY) {
        return GraphCanvasLogic.pointInCanvas(screenX, screenY, root.width, root.height);
    }

    function performLibraryDrop(screenX, screenY, payload) {
        interactionState.performLibraryDrop(screenX, screenY, payload);
    }

    function _samePort(a, b) {
        return interactionState._samePort(a, b);
    }

    function clearPendingConnection() {
        interactionState.clearPendingConnection();
    }

    function _wireDragSourceData(state) {
        return interactionState._wireDragSourceData(state);
    }

    function wireDragSourcePort() {
        return interactionState.wireDragSourcePort();
    }

    function wireDragPreviewConnection() {
        return interactionState.wireDragPreviewConnection();
    }

    function _updateWireDropCandidate(screenX, screenY, state) {
        interactionState._updateWireDropCandidate(screenX, screenY, state);
    }

    function _clearWireDragState() {
        interactionState._clearWireDragState();
    }

    function beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY) {
        interactionState.beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY);
    }

    function updatePortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) {
        interactionState.updatePortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive);
    }

    function finishPortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) {
        interactionState.finishPortWireDrag(
            nodeId,
            portKey,
            direction,
            _sceneX,
            _sceneY,
            screenX,
            screenY,
            dragActive
        );
    }

    function cancelWireDrag() {
        return interactionState.cancelWireDrag();
    }

    function handlePortClick(nodeId, portKey, direction, sceneX, sceneY) {
        interactionState.handlePortClick(nodeId, portKey, direction, sceneX, sceneY);
    }

    function _syncEdgePayload() {
        sceneState.syncEdgePayload();
    }

    function requestEdgeRedraw() {
        if (edgeLayer && edgeLayer.requestRedraw)
            edgeLayer.requestRedraw();
    }

    function requestViewStateRedraw() {
        if (backgroundLayer && backgroundLayer.markViewStateRedrawDirty)
            backgroundLayer.markViewStateRedrawDirty();
        if (edgeLayer && edgeLayer.markViewStateRedrawDirty)
            edgeLayer.markViewStateRedrawDirty();
        if (!viewStateRedrawFlushTimer.running)
            viewStateRedrawFlushTimer.start();
    }

    function flushViewStateRedraw() {
        if (backgroundLayer && backgroundLayer.flushViewStateRedraw)
            backgroundLayer.flushViewStateRedraw();
        if (edgeLayer && edgeLayer.flushViewStateRedraw)
            edgeLayer.flushViewStateRedraw();
    }

    function _closeContextMenus() {
        interactionState._closeContextMenus();
    }

    function _clampMenuPosition(x, y, menuWidth, menuHeight) {
        return GraphCanvasLogic.clampMenuPosition(
            x,
            y,
            menuWidth,
            menuHeight,
            root.width,
            root.height,
            4
        );
    }

    function _openEdgeContext(edgeId, x, y) {
        interactionState._openEdgeContext(edgeId, x, y);
    }

    function _openNodeContext(nodeId, x, y) {
        interactionState._openNodeContext(nodeId, x, y);
    }

    GraphCanvasComponents.GraphCanvasBackground {
        id: backgroundLayer
        objectName: "graphCanvasBackground"
        anchors.fill: parent
        viewBridge: root._canvasViewStateBridgeRef
        showGrid: root.showGrid
        degradedWindowActive: root.gridSimplificationActive
    }

    GraphCanvasComponents.GraphCanvasWorldLayer {
        id: backdropWorld
        objectName: "graphCanvasBackdropLayer"
        canvasItem: root
        viewBridge: root._canvasViewStateBridgeRef
        sceneModel: root._sceneBackdropNodesModel()
    }

    GraphComponents.EdgeLayer {
        id: edgeLayer
        objectName: "graphCanvasEdgeLayer"
        anchors.fill: parent
        viewBridge: root._canvasViewStateBridgeRef
        sceneBridge: root._canvasSceneStateBridgeRef
        edges: root.edgePayload
        nodes: root._canvasSceneStateBridgeRef ? root._canvasSceneStateBridgeRef.nodes_model : []
        dragOffsets: root.liveDragOffsets
        liveNodeGeometry: root.liveNodeGeometry
        selectedEdgeIds: root.selectedEdgeIds
        visibleSceneRectPayload: root.visibleSceneRectPayload
        previewEdgeId: root.dropPreviewEdgeId
        dragConnection: root.wireDragPreviewConnection()
        performanceMode: root.resolvedGraphicsPerformanceMode
        transientPerformanceActivityActive: root.transientPerformanceActivityActive
        transientDegradedWindowActive: root.transientDegradedWindowActive
        edgeLabelSimplificationActive: root.edgeLabelSimplificationActive
        inputEnabled: !(root.edgeContextVisible || root.nodeContextVisible)

        onEdgeClicked: function(edgeId, additive) {
            root.forceActiveFocus();
            root._closeContextMenus();
            root.clearPendingConnection();
            if (additive)
                root.toggleEdgeSelection(edgeId);
            else
                root.setExclusiveEdgeSelection(edgeId);
        }
        onEdgeContextRequested: function(edgeId, screenX, screenY) {
            root._openEdgeContext(edgeId, screenX, screenY);
        }
    }

    GraphCanvasComponents.GraphCanvasWorldLayer {
        id: backdropInputWorld
        objectName: "graphCanvasBackdropInputLayer"
        canvasItem: root
        viewBridge: root._canvasViewStateBridgeRef
        sceneModel: root._sceneBackdropNodesModel()
        backdropInputOverlay: true
    }

    GraphCanvasComponents.GraphCanvasDropPreview {
        id: dragNodePreview
        objectName: "graphCanvasDropPreview"
        canvasItem: root
        viewBridge: root._canvasViewStateBridgeRef
    }

    GraphCanvasComponents.GraphCanvasWorldLayer {
        id: world
        objectName: "graphCanvasWorld"
        canvasItem: root
        viewBridge: root._canvasViewStateBridgeRef
        sceneModel: root._canvasSceneStateBridgeRef ? root._canvasSceneStateBridgeRef.nodes_model : []
    }

    GraphCanvasComponents.GraphCanvasMinimapOverlay {
        id: minimapOverlay
        objectName: "graphCanvasMinimapOverlay"
        canvasItem: root
        sceneStateBridge: root._canvasSceneStateBridgeRef
        viewStateBridge: root._canvasViewStateBridgeRef
        viewCommandBridge: root._canvasViewCommandBridgeRef
        degradedWindowActive: root.minimapSimplificationActive
    }

    GraphCanvasComponents.GraphCanvasInputLayers {
        id: inputLayers
        objectName: "graphCanvasInputLayers"
        canvasItem: root
        shellCommandBridge: root._canvasShellCommandBridgeRef
        sceneCommandBridge: root._canvasSceneCommandBridgeRef
        viewStateBridge: root._canvasViewStateBridgeRef
        viewCommandBridge: root._canvasViewCommandBridgeRef
    }

    GraphCanvasComponents.GraphCanvasContextMenus {
        id: contextMenus
        objectName: "graphCanvasContextMenus"
        canvasItem: root
        commandBridge: root._canvasShellCommandBridgeRef
    }

    Connections {
        target: root._canvasSceneStateBridgeRef
        ignoreUnknownSignals: true
        function _handleSceneMutation() {
            canvasPerformancePolicy.noteStructuralMutation();
            root.liveDragOffsets = ({});
            root.liveNodeGeometry = ({});
            root._clearWireDragState();
            root._syncEdgePayload();
        }
        function onScene_edges_changed() {
            _handleSceneMutation();
        }
        function onScene_nodes_changed() {
            _handleSceneMutation();
        }
        function onEdges_changed() {
            _handleSceneMutation();
        }
        function onNodes_changed() {
            _handleSceneMutation();
        }
    }

    Connections {
        target: root._canvasViewStateBridgeRef
        ignoreUnknownSignals: true
        function onView_state_changed() {
            root.requestViewStateRedraw();
        }
    }

    function _resetCanvasSceneState() {
        canvasPerformancePolicy.clearStructuralMutation();
        root.liveDragOffsets = ({});
        root.liveNodeGeometry = ({});
        interactionState.resetSceneBridgeState();
        root._syncEdgePayload();
    }

    onCanvasStateBridgeChanged: root._resetCanvasSceneState()
    onCanvasCommandBridgeChanged: root._resetCanvasSceneState()
    onSceneBridgeChanged: root._resetCanvasSceneState()

    onWidthChanged: {
        var view = root._canvasViewCommandBridgeRef;
        if (view && view.set_viewport_size)
            view.set_viewport_size(width, height);
    }

    onHeightChanged: {
        var view = root._canvasViewCommandBridgeRef;
        if (view && view.set_viewport_size)
            view.set_viewport_size(width, height);
    }

    Component.onDestruction: {
        canvasPerformancePolicy.clearStructuralMutation();
        viewStateRedrawFlushTimer.stop();
        interactionIdleTimer.stop();
        interactionState.releaseHostReferences();
    }
}
