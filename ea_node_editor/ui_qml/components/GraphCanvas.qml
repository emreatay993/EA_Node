import QtQuick 2.15
import QtQml 2.15
import "graph_canvas" as GraphCanvasComponents
import "graph_canvas/GraphCanvasRootApi.js" as GraphCanvasRootApi
import "graph_canvas/GraphCanvasPerformancePolicy.js" as GraphCanvasPerformancePolicyLogic

Item {
    id: root
    objectName: "graphCanvas"
    property var graphActionBridge: null
    property var canvasStateBridge: null
    property var canvasCommandBridge: null
    property var canvasViewBridge: canvasStateBridge && canvasStateBridge.viewport_bridge
        ? canvasStateBridge.viewport_bridge
        : (canvasCommandBridge && canvasCommandBridge.viewport_bridge ? canvasCommandBridge.viewport_bridge : null)
    readonly property var shellContextRef: typeof shellContext !== "undefined" ? shellContext : null
    readonly property var graphActionBridgeRef: rootBindings.graphActionBridgeRef
    readonly property var canvasStateBridgeRef: rootBindings.canvasStateBridgeRef
    readonly property var canvasCommandBridgeRef: rootBindings.canvasCommandBridgeRef
    readonly property var canvasViewBridgeRef: rootBindings.canvasViewBridgeRef
    readonly property var _canvasStateBridgeRef: rootBindings._canvasStateBridgeRef
    readonly property var _canvasViewStateBridgeRef: rootBindings._canvasViewStateBridgeRef
    readonly property var sceneStateBridge: rootBindings.sceneStateBridge
    readonly property var sceneCommandBridge: rootBindings.sceneCommandBridge
    readonly property var sceneBridge: rootBindings.sceneBridge
    readonly property var viewBridge: rootBindings.viewBridge
    readonly property var themeBridgeRef: root.shellContextRef
        ? root.shellContextRef.themeBridge
        : (typeof themeBridge !== "undefined" ? themeBridge : null)
    readonly property var addonManagerBridgeRef: root.shellContextRef
        ? root.shellContextRef.addonManagerBridge
        : null
    readonly property var helpBridgeRef: root.shellContextRef
        ? root.shellContextRef.helpBridge
        : null
    readonly property var contentFullscreenBridgeRef: root.shellContextRef
        ? root.shellContextRef.contentFullscreenBridge
        : null
    readonly property var shellLibraryBridgeRef: root.shellContextRef
        ? root.shellContextRef.shellLibraryBridge
        : null
    readonly property var viewerSessionBridgeRef: root.shellContextRef
        ? root.shellContextRef.viewerSessionBridge
        : (typeof viewerSessionBridge !== "undefined" ? viewerSessionBridge : null)
    readonly property var themePalette: root.themeBridgeRef ? root.themeBridgeRef.palette : ({})
    readonly property var canvasActionRouter: actionRouter
    property var overlayHostItem: null
    property Item activeToolbarHost: null
    property var edgePayload: []
    readonly property var visibleSceneRectPayload: rootBindings.visibleSceneRectPayload
    readonly property var failedNodeLookup: rootBindings.failedNodeLookup
    readonly property int failedNodeRevision: rootBindings.failedNodeRevision
    readonly property string failedNodeTitle: rootBindings.failedNodeTitle
    readonly property var runningNodeLookup: rootBindings.runningNodeLookup
    readonly property var completedNodeLookup: rootBindings.completedNodeLookup
    readonly property bool hideLockedPorts: rootBindings.hideLockedPorts
    readonly property bool hideOptionalPorts: rootBindings.hideOptionalPorts
    readonly property var sceneNodesModel: root.sceneStateBridge ? root.sceneStateBridge.nodes_model : []
    readonly property var runningNodeStartedAtMsLookup: rootBindings.runningNodeStartedAtMsLookup
    readonly property var nodeElapsedMsLookup: rootBindings.nodeElapsedMsLookup
    readonly property var progressedExecutionEdgeLookup: rootBindings.progressedExecutionEdgeLookup
    readonly property int nodeExecutionRevision: rootBindings.nodeExecutionRevision
    readonly property var canvasViewportController: viewportController
    readonly property var canvasSceneLifecycle: sceneLifecycle
    readonly property real nodeRenderActivationPaddingPx: rootBindings.nodeRenderActivationPaddingPx
    readonly property var nodeRenderActivationSceneRectPayload: rootBindings.nodeRenderActivationSceneRectPayload
    property bool minimapExpanded: rootBindings.minimapExpanded
    readonly property bool showGrid: rootBindings.showGrid
    readonly property bool minimapVisible: rootBindings.minimapVisible
    readonly property bool showPortLabels: rootBindings.showPortLabels
    readonly property string edgeCrossingStyle: rootBindings.edgeCrossingStyle
    readonly property bool nodeShadowEnabled: rootBindings.nodeShadowEnabled
    readonly property int shadowStrength: rootBindings.shadowStrength
    readonly property int shadowSoftness: rootBindings.shadowSoftness
    readonly property int shadowOffset: rootBindings.shadowOffset
    readonly property string graphicsPerformanceMode: rootBindings.graphicsPerformanceMode
    readonly property string resolvedGraphicsPerformanceMode: rootBindings.resolvedGraphicsPerformanceMode
    readonly property bool mutationBurstActive: rootBindings.mutationBurstActive
    readonly property bool transientPerformanceActivityActive: rootBindings.transientPerformanceActivityActive
    readonly property bool transientDegradedWindowActive: rootBindings.transientDegradedWindowActive
    readonly property bool edgeLabelSimplificationActive: rootBindings.edgeLabelSimplificationActive
    readonly property bool gridSimplificationActive: rootBindings.gridSimplificationActive
    readonly property bool minimapSimplificationActive: rootBindings.minimapSimplificationActive
    readonly property bool shadowSimplificationActive: rootBindings.shadowSimplificationActive
    readonly property bool snapshotProxyReuseActive: rootBindings.snapshotProxyReuseActive
    readonly property bool fullFidelityMode: rootBindings.fullFidelityMode
    readonly property bool viewportInteractionWorldCacheActive: rootBindings.viewportInteractionWorldCacheActive
    readonly property bool highQualityRendering: rootBindings.highQualityRendering
    readonly property int interactionIdleDelayMs: 2000
    readonly property int transientRecoveryDelayMs: 150
    readonly property real wireDragThreshold: 2
    readonly property real boxZoomDragThreshold: 4
    readonly property real boxZoomPaddingPx: 24
    readonly property real worldSize: 12000
    readonly property real worldOffset: root.worldSize / 2
    readonly property real minimapExpandedWidth: 238
    readonly property real minimapExpandedHeight: 162
    readonly property real minimapCollapsedWidth: 28
    readonly property real minimapCollapsedHeight: 28
    readonly property string gridStyle: rootBindings.gridStyle
    readonly property var lockedNodeStatusSummary: {
        var payloads = root.sceneNodesModel || [];
        var lockedNodeCount = 0;
        var focusAddonIds = [];
        var seenFocusAddonIds = ({});
        for (var index = 0; index < payloads.length; ++index) {
            var payload = payloads[index];
            if (!payload || !Boolean(payload.read_only) || !Boolean(payload.unresolved))
                continue;
            lockedNodeCount += 1;
            var lockedState = payload.locked_state || ({});
            var focusAddonId = String(lockedState.focus_addon_id || payload.addon_id || "").trim();
            if (!focusAddonId.length || seenFocusAddonIds[focusAddonId])
                continue;
            seenFocusAddonIds[focusAddonId] = true;
            focusAddonIds.push(focusAddonId);
        }
        return {
            "lockedNodeCount": lockedNodeCount,
            "missingAddonCount": focusAddonIds.length,
            "focusAddonIds": focusAddonIds,
            "focusAddonId": focusAddonIds.length === 1 ? focusAddonIds[0] : "",
        };
    }
    readonly property int lockedNodeCount: Math.max(0, Number(lockedNodeStatusSummary.lockedNodeCount || 0))
    readonly property int missingAddonCount: Math.max(0, Number(lockedNodeStatusSummary.missingAddonCount || 0))
    readonly property string lockedNodeStatusFocusAddonId: String(lockedNodeStatusSummary.focusAddonId || "")
    readonly property bool lockedNodeStatusVisible: lockedNodeCount > 0
    readonly property bool lockedNodeStatusActionVisible: false
    readonly property string lockedNodeStatusText: {
        if (root.lockedNodeCount <= 0)
            return "";
        var lockedNodeText = root.lockedNodeCount === 1
            ? "1 locked node"
            : root.lockedNodeCount + " locked nodes";
        if (root.missingAddonCount <= 0)
            return lockedNodeText;
        var missingAddonText = root.missingAddonCount === 1
            ? "1 add-on missing"
            : root.missingAddonCount + " add-ons missing";
        return lockedNodeText + ", " + missingAddonText;
    }
    readonly property color lockedNodeStatusMutedTextColor: typeof themeBridge !== "undefined"
        && themeBridge
        && themeBridge.palette
        && themeBridge.palette.muted_fg
        ? themeBridge.palette.muted_fg
        : "#95a0b8"
    readonly property color lockedNodeStatusActionColor: typeof themeBridge !== "undefined"
        && themeBridge
        && themeBridge.palette
        && themeBridge.palette.accent
        ? themeBridge.palette.accent
        : "#2F89FF"

    GraphCanvasComponents.GraphCanvasRootBindings {
        id: rootBindings
        graphActionBridge: root.graphActionBridge
        canvasStateBridge: root.canvasStateBridge
        canvasCommandBridge: root.canvasCommandBridge
        canvasViewBridge: root.canvasViewBridge
        viewportController: viewportController
        canvasPerformancePolicy: canvasPerformancePolicy
    }

    GraphCanvasComponents.GraphCanvasActionRouter {
        id: actionRouter
        canvasItem: root
        graphActionBridge: root.graphActionBridgeRef
        canvasCommandBridge: root.canvasCommandBridgeRef
        addonManagerBridge: root.addonManagerBridgeRef
        helpBridge: root.helpBridgeRef
        contentFullscreenBridge: root.contentFullscreenBridgeRef
        shellLibraryBridge: root.shellLibraryBridgeRef
        viewerSessionBridge: root.viewerSessionBridgeRef
    }

    GraphCanvasComponents.GraphCanvasInteractionState {
        id: interactionState
        canvasItem: root
        shellBridge: root.canvasCommandBridgeRef
        sceneBridge: root.sceneStateBridge
        edgeLayerItem: rootLayers.edgeLayerItem
        interactionIdleTimer: interactionIdleTimer
        interactionIdleDelayMs: root.transientRecoveryDelayMs
        wireDragThreshold: root.wireDragThreshold
    }

    GraphCanvasComponents.GraphCanvasSceneState {
        id: sceneState
        canvasItem: root
        edgeLayerItem: rootLayers.edgeLayerItem
    }

    GraphCanvasComponents.GraphCanvasNodeSurfaceBridge {
        id: nodeSurfaceBridge
        canvasItem: root
    }

    GraphCanvasComponents.GraphCanvasViewportController {
        id: viewportController
        canvasItem: root
        shellCommandBridge: root.canvasCommandBridgeRef
        viewStateBridge: root.viewBridge
        viewCommandBridge: root.viewBridge
        interactionState: interactionState
        backgroundLayer: rootLayers.backgroundLayerItem
        edgeLayer: rootLayers.edgeLayerItem
        redrawFlushTimer: viewStateRedrawFlushTimer
    }

    GraphCanvasComponents.GraphCanvasSceneLifecycle {
        id: sceneLifecycle
        canvasItem: root
        sceneStateBridge: root.sceneStateBridge
        viewStateBridge: root.viewBridge
        sceneState: sceneState
        interactionState: interactionState
        canvasPerformancePolicy: canvasPerformancePolicy
        viewportController: viewportController
        edgeLayerItem: rootLayers.edgeLayerItem
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
        interval: root.transientRecoveryDelayMs
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
    property alias selectionContextVisible: interactionState.selectionContextVisible
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

    Timer {
        id: interactionIdleTimer
        interval: root.transientRecoveryDelayMs
        repeat: false
        onTriggered: interactionState.endViewportInteraction()
    }

    Timer {
        id: viewStateRedrawFlushTimer
        interval: 0
        repeat: false
        onTriggered: root.flushViewStateRedraw()
    }

    function toggleMinimapExpanded() { GraphCanvasRootApi.invoke(viewportController, "toggleMinimapExpanded"); }
    function beginViewportInteraction() { GraphCanvasRootApi.invoke(viewportController, "beginViewportInteraction"); }
    function finishViewportInteractionSoon() { GraphCanvasRootApi.invoke(viewportController, "finishViewportInteractionSoon"); }
    function noteViewportInteraction() { GraphCanvasRootApi.invoke(viewportController, "noteViewportInteraction"); }
    function screenToSceneX(screenX) { return GraphCanvasRootApi.invoke(viewportController, "screenToSceneX", [screenX], 0.0); }
    function screenToSceneY(screenY) { return GraphCanvasRootApi.invoke(viewportController, "screenToSceneY", [screenY], 0.0); }
    function _wheelDeltaY(eventObj) { return GraphCanvasRootApi.invoke(viewportController, "wheelDeltaY", [eventObj], 0.0); }
    function applyWheelZoom(eventObj) { return GraphCanvasRootApi.invoke(viewportController, "applyWheelZoom", [eventObj], false); }
    function sceneToScreenX(sceneX) { return GraphCanvasRootApi.invoke(viewportController, "sceneToScreenX", [sceneX], 0.0); }
    function sceneToScreenY(sceneY) { return GraphCanvasRootApi.invoke(viewportController, "sceneToScreenY", [sceneY], 0.0); }
    function _normalizedSceneRectPayload(rectLike) { return GraphCanvasRootApi.invoke(viewportController, "normalizedSceneRectPayload", [rectLike], null); }
    function _scenePaddingForViewportPixels(paddingPx) { return GraphCanvasRootApi.invoke(viewportController, "scenePaddingForViewportPixels", [paddingPx], 0.0); }
    function _inflateSceneRectPayload(rectLike, padding) { return GraphCanvasRootApi.invoke(viewportController, "inflateSceneRectPayload", [rectLike, padding], ({})); }
    function frameScreenRect(screenX1, screenY1, screenX2, screenY2, paddingPx) { return GraphCanvasRootApi.invoke(viewportController, "frameScreenRect", [screenX1, screenY1, screenX2, screenY2, paddingPx], false); }
    function snapToGridEnabled() { return GraphCanvasRootApi.snapToGridEnabled(root.canvasStateBridgeRef); }
    function snapGridSize() { return GraphCanvasRootApi.snapGridSize(root.canvasStateBridgeRef); }
    function snapToGridValue(value) { return GraphCanvasRootApi.snapToGridValue(root.canvasStateBridgeRef, value); }
    function snappedDragDelta(nodeId, rawDx, rawDy) { return GraphCanvasRootApi.snappedDragDelta(sceneState, root.canvasStateBridgeRef, nodeId, rawDx, rawDy); }
    function _normalizeEdgeIds(values) { return GraphCanvasRootApi.invoke(sceneState, "normalizeEdgeIds", [values], []); }
    function _availableEdgeIdSet() { return GraphCanvasRootApi.invoke(sceneState, "availableEdgeIdSet", [], ({})); }
    function pruneSelectedEdges() { GraphCanvasRootApi.invoke(sceneState, "pruneSelectedEdges"); }
    function clearEdgeSelection() { GraphCanvasRootApi.invoke(sceneState, "clearEdgeSelection"); }
    function toggleEdgeSelection(edgeId) { GraphCanvasRootApi.invoke(sceneState, "toggleEdgeSelection", [edgeId]); }
    function setExclusiveEdgeSelection(edgeId) { GraphCanvasRootApi.invoke(sceneState, "setExclusiveEdgeSelection", [edgeId]); }
    function _sceneNodePayload(nodeId) { return GraphCanvasRootApi.invoke(sceneState, "sceneNodePayload", [nodeId], null); }
    function _sceneBackdropNodesModel() { return GraphCanvasRootApi.invoke(sceneState, "sceneBackdropNodesModel", [], []); }
    function _sceneAllNodesModel() { return GraphCanvasRootApi.invoke(sceneState, "sceneAllNodesModel", [], []); }
    function _sceneEdgePayload(edgeId) { return GraphCanvasRootApi.invoke(sceneState, "sceneEdgePayload", [edgeId], null); }
    function _nodeSupportsPassiveStyle(nodeId) { return GraphCanvasRootApi.invoke(sceneState, "nodeSupportsPassiveStyle", [nodeId], false); }
    function _edgeSupportsFlowStyle(edgeId) { return GraphCanvasRootApi.invoke(sceneState, "edgeSupportsFlowStyle", [edgeId], false); }
    function _nodeCanEnterScope(nodeId) { return GraphCanvasRootApi.invoke(sceneState, "nodeCanEnterScope", [nodeId], false); }
    function requestOpenSubnodeScope(nodeId) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "requestOpenSubnodeScope", [nodeId], false); }
    function _nodeSurfaceSelectionBridge() { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "_sceneSelectionBridge", [], null); }
    function _nodeSurfacePendingActionBridge() { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "_pendingActionBridge", [], null); }
    function _nodeSurfacePropertyBridge() { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "_propertyBridge", [], null); }
    function _nodeSurfaceCursorBridge() { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "_cursorBridge", [], null); }
    function _nodeSurfacePdfPreviewBridge() { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "_pdfPreviewBridge", [], null); }
    function prepareNodeSurfaceControlInteraction(nodeId) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "prepareNodeSurfaceControlInteraction", [nodeId], false); }
    function commitNodeSurfaceProperty(nodeId, key, value) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "commitNodeSurfaceProperty", [nodeId, key, value], false); }
    function commitNodePortLabel(nodeId, portKey, label) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "commitNodePortLabel", [nodeId, portKey, label], false); }
    function requestNodeSurfaceCropEdit(nodeId) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "requestNodeSurfaceCropEdit", [nodeId], false); }
    function consumePendingNodeSurfaceAction(nodeId) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "consumePendingNodeSurfaceAction", [nodeId], false); }
    function commitNodeSurfaceProperties(nodeId, properties) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "commitNodeSurfaceProperties", [nodeId, properties], false); }
    function setNodeSurfaceCursorShape(cursorShape) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "setNodeSurfaceCursorShape", [cursorShape], false); }
    function clearNodeSurfaceCursorShape() { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "clearNodeSurfaceCursorShape", [], false); }
    function describeNodeSurfacePdfPreview(source, pageNumber) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "describeNodeSurfacePdfPreview", [source, pageNumber], ({})); }
    function browseNodePropertyPath(nodeId, key, currentPath) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "browseNodePropertyPath", [nodeId, key, currentPath], ""); }
    function pickNodePropertyColor(nodeId, key, currentValue) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "pickNodePropertyColor", [nodeId, key, currentValue], ""); }
    function selectedNodeIds() { return GraphCanvasRootApi.invoke(sceneState, "selectedNodeIds", [], []); }
    function _appendUniqueDragNodeId(nodeIds, seenNodeIds, nodeId) { GraphCanvasRootApi.invoke(sceneState, "_appendUniqueDragNodeId", [nodeIds, seenNodeIds, nodeId]); }
    function _payloadNodeIdList(payload, key) { return GraphCanvasRootApi.invoke(sceneState, "_payloadNodeIdList", [payload, key], []); }
    function _isCommentBackdropPayload(payload) { return GraphCanvasRootApi.invoke(sceneState, "isCommentBackdropPayload", [payload], false); }
    function _appendBackdropDragDescendants(nodeIds, seenNodeIds, backdropNodeId) { GraphCanvasRootApi.invoke(sceneState, "_appendBackdropDragDescendants", [nodeIds, seenNodeIds, backdropNodeId]); }
    function _appendBackdropAwareDragNodeIds(nodeIds, seenNodeIds, nodeId) { GraphCanvasRootApi.invoke(sceneState, "_appendBackdropAwareDragNodeIds", [nodeIds, seenNodeIds, nodeId]); }
    function dragNodeIdsForAnchor(nodeId) { return GraphCanvasRootApi.invoke(sceneState, "dragNodeIdsForAnchor", [nodeId], []); }
    function setLiveDragOffsets(nodeIds, dx, dy) { GraphCanvasRootApi.invoke(sceneState, "setLiveDragOffsets", [nodeIds, dx, dy]); }
    function clearLiveDragOffsets() { GraphCanvasRootApi.invoke(sceneState, "clearLiveDragOffsets"); }
    function liveDragDxForNode(nodeId) { return GraphCanvasRootApi.invoke(sceneState, "liveDragDxForNode", [nodeId], 0.0); }
    function liveDragDyForNode(nodeId) { return GraphCanvasRootApi.invoke(sceneState, "liveDragDyForNode", [nodeId], 0.0); }
    function setLiveNodeGeometry(nodeId, x, y, width, height, active) { GraphCanvasRootApi.invoke(sceneState, "setLiveNodeGeometry", [nodeId, x, y, width, height, active]); }
    function clearLiveNodeGeometry() { GraphCanvasRootApi.invoke(sceneState, "clearLiveNodeGeometry"); }
    function _dropTargetInput(sourceDrag, candidate) { return GraphCanvasRootApi.invoke(interactionState, "_dropTargetInput", [sourceDrag, candidate], null); }
    function _isExactDuplicate(sourceDrag, candidate, edge) { return GraphCanvasRootApi.invoke(interactionState, "_isExactDuplicate", [sourceDrag, candidate, edge], false); }
    function _portKind(nodeId, portKey) { return GraphCanvasRootApi.invoke(interactionState, "_portKind", [nodeId, portKey], ""); }
    function _portDataType(nodeId, portKey) { return GraphCanvasRootApi.invoke(interactionState, "_portDataType", [nodeId, portKey], "any"); }
    function _arePortKindsCompatible(sourceKind, targetKind) { return GraphCanvasRootApi.invoke(interactionState, "_arePortKindsCompatible", [sourceKind, targetKind], false); }
    function _isDropAllowed(sourceDrag, candidate) { return GraphCanvasRootApi.invoke(interactionState, "_isDropAllowed", [sourceDrag, candidate], false); }
    function _nearestDropCandidateForWireDrag(screenX, screenY, sourceDrag, thresholdOverride) { return GraphCanvasRootApi.invoke(interactionState, "_nearestDropCandidateForWireDrag", [screenX, screenY, sourceDrag, thresholdOverride], null); }
    function _areDataTypesCompatible(sourceType, targetType) { return GraphCanvasRootApi.invoke(interactionState, "_areDataTypesCompatible", [sourceType, targetType], false); }
    function _portsCompatibleForAuto(sourcePort, targetPort) { return GraphCanvasRootApi.invoke(interactionState, "_portsCompatibleForAuto", [sourcePort, targetPort], false); }
    function _libraryPorts(payload) { return GraphCanvasRootApi.invoke(interactionState, "_libraryPorts", [payload], []); }
    function _scenePortData(nodeId, portKey) { return GraphCanvasRootApi.invoke(interactionState, "_scenePortData", [nodeId, portKey], null); }
    function _scenePortPoint(node, port, inputRow, outputRow) { return GraphCanvasRootApi.invoke(interactionState, "_scenePortPoint", [node, port, inputRow, outputRow], ({})); }
    function _hasCompatiblePortForTarget(targetPort, nodePorts) { return GraphCanvasRootApi.invoke(interactionState, "_hasCompatiblePortForTarget", [targetPort, nodePorts], false); }
    function _portDropTargetAtScreen(screenX, screenY, payload) { return GraphCanvasRootApi.invoke(interactionState, "_portDropTargetAtScreen", [screenX, screenY, payload], null); }
    function _edgeSupportsDrop(edgeId, payload) { return GraphCanvasRootApi.invoke(interactionState, "_edgeSupportsDrop", [edgeId, payload], false); }
    function _computeLibraryDropTarget(screenX, screenY, payload) { return GraphCanvasRootApi.invoke(interactionState, "_computeLibraryDropTarget", [screenX, screenY, payload], ({})); }
    function _previewNodeMetrics(payload) { return GraphCanvasRootApi.invoke(interactionState, "_previewNodeMetrics", [payload], ({})); }
    function previewNodeMetrics() { return GraphCanvasRootApi.invoke(interactionState, "previewNodeMetrics", [], ({})); }
    function _previewVisiblePorts(payload, direction) { return GraphCanvasRootApi.invoke(interactionState, "_previewVisiblePorts", [payload, direction], []); }
    function previewInputPorts() { return GraphCanvasRootApi.invoke(interactionState, "previewInputPorts", [], []); }
    function previewOutputPorts() { return GraphCanvasRootApi.invoke(interactionState, "previewOutputPorts", [], []); }
    function previewPortColor(kind) { return GraphCanvasRootApi.invoke(interactionState, "previewPortColor", [kind], "transparent"); }
    function previewNodeScreenWidth() { return GraphCanvasRootApi.invoke(interactionState, "previewNodeScreenWidth", [], 0.0); }
    function previewNodeScreenHeight() { return GraphCanvasRootApi.invoke(interactionState, "previewNodeScreenHeight", [], 0.0); }
    function previewPortLabelsVisible() { return GraphCanvasRootApi.invoke(interactionState, "previewPortLabelsVisible", [], false); }
    function clearLibraryDropPreview() { GraphCanvasRootApi.invoke(interactionState, "clearLibraryDropPreview"); }
    function updateLibraryDropPreview(screenX, screenY, payload) { GraphCanvasRootApi.invoke(interactionState, "updateLibraryDropPreview", [screenX, screenY, payload]); }
    function isPointInCanvas(screenX, screenY) { return GraphCanvasRootApi.isPointInCanvas(root, screenX, screenY); }
    function performLibraryDrop(screenX, screenY, payload) { GraphCanvasRootApi.invoke(interactionState, "performLibraryDrop", [screenX, screenY, payload]); }
    function folderExplorerDragPayload(path, isFolder) { return GraphCanvasRootApi.invoke(nodeSurfaceBridge, "folderExplorerDragPayload", [path, isFolder], ({})); }
    function _pathPointerPayload(path, isFolder) {
        return folderExplorerDragPayload(path, isFolder);
    }
    function _pathFromDropEvent(eventObj) {
        if (!eventObj)
            return "";
        if (eventObj.urls && eventObj.urls.length > 0)
            return String(eventObj.urls[0] || "");
        if (eventObj.text !== undefined && String(eventObj.text || "").trim().length > 0)
            return String(eventObj.text || "").trim();
        if (eventObj.getDataAsString) {
            var pointerData = String(eventObj.getDataAsString("application/x-corex-path-pointer") || "").trim();
            if (pointerData.length > 0) {
                try {
                    var payload = JSON.parse(pointerData);
                    var pointerPath = String(payload && payload.properties ? payload.properties.path || "" : "").trim();
                    if (pointerPath.length > 0)
                        return pointerPath;
                } catch (error) {
                }
            }
            var uriList = String(eventObj.getDataAsString("text/uri-list") || "").trim();
            if (uriList.length > 0)
                return uriList.split(/\r?\n/)[0];
            var plainText = String(eventObj.getDataAsString("text/plain") || "").trim();
            if (plainText.length > 0)
                return plainText;
        }
        return "";
    }
    function updatePathPointerDropPreview(screenX, screenY, path, isFolder) {
        var payload = _pathPointerPayload(path, isFolder);
        if (!payload || !payload.type_id) {
            clearLibraryDropPreview();
            return;
        }
        updateLibraryDropPreview(screenX, screenY, payload);
    }
    function performPathPointerDrop(screenX, screenY, path, isFolder) {
        var bridge = root.canvasCommandBridgeRef;
        if (!bridge || !bridge.request_create_path_pointer_node) {
            clearLibraryDropPreview();
            return false;
        }
        var normalizedPath = String(path || "").trim();
        if (!normalizedPath.length) {
            clearLibraryDropPreview();
            return false;
        }
        root.forceActiveFocus();
        root._closeContextMenus();
        root.clearPendingConnection();
        var result = bridge.request_create_path_pointer_node(
            normalizedPath,
            Boolean(isFolder),
            root.screenToSceneX(screenX),
            root.screenToSceneY(screenY)
        );
        root.clearEdgeSelection();
        root.clearLibraryDropPreview();
        return !!result && Boolean(result.success);
    }
    function _samePort(a, b) { return GraphCanvasRootApi.invoke(interactionState, "_samePort", [a, b], false); }
    function clearPendingConnection() { GraphCanvasRootApi.invoke(interactionState, "clearPendingConnection"); }
    function _wireDragSourceData(state) { return GraphCanvasRootApi.invoke(interactionState, "_wireDragSourceData", [state], null); }
    function wireDragSourcePort() { return GraphCanvasRootApi.invoke(interactionState, "wireDragSourcePort", [], null); }
    function wireDragPreviewConnection() { return GraphCanvasRootApi.invoke(interactionState, "wireDragPreviewConnection", [], null); }
    function _updateWireDropCandidate(screenX, screenY, state) { GraphCanvasRootApi.invoke(interactionState, "_updateWireDropCandidate", [screenX, screenY, state]); }
    function _clearWireDragState() { GraphCanvasRootApi.invoke(interactionState, "_clearWireDragState"); }
    function beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY) { GraphCanvasRootApi.invoke(interactionState, "beginPortWireDrag", [nodeId, portKey, direction, sceneX, sceneY, screenX, screenY]); }
    function updatePortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) { GraphCanvasRootApi.invoke(interactionState, "updatePortWireDrag", [nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive]); }
    function finishPortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) { GraphCanvasRootApi.invoke(interactionState, "finishPortWireDrag", [nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive]); }
    function cancelWireDrag() { return GraphCanvasRootApi.invoke(interactionState, "cancelWireDrag", [], false); }
    function handlePortClick(nodeId, portKey, direction, sceneX, sceneY) { GraphCanvasRootApi.invoke(interactionState, "handlePortClick", [nodeId, portKey, direction, sceneX, sceneY]); }
    function _portLockBridge() {
        if (root.canvasCommandBridge && root.canvasCommandBridge.set_port_locked)
            return root.canvasCommandBridge;
        if (root.sceneCommandBridge && root.sceneCommandBridge.set_port_locked)
            return root.sceneCommandBridge;
        return null;
    }
    function togglePortLock(nodeId, portKey, locked) {
        var bridge = _portLockBridge();
        if (!bridge || !bridge.set_port_locked)
            return false;
        if (!bridge.set_port_locked(nodeId, portKey, !Boolean(locked)))
            return false;
        clearPendingConnection();
        cancelWireDrag();
        hoveredPort = null;
        if (requestEdgeRedraw)
            requestEdgeRedraw();
        forceActiveFocus();
        return true;
    }
    function _syncEdgePayload() { GraphCanvasRootApi.invoke(sceneState, "syncEdgePayload"); }
    function requestEdgeRedraw() { GraphCanvasRootApi.invoke(sceneLifecycle, "requestEdgeRedraw"); }
    function requestViewStateRedraw() { GraphCanvasRootApi.invoke(viewportController, "requestViewStateRedraw"); }
    function flushViewStateRedraw() { GraphCanvasRootApi.invoke(viewportController, "flushViewStateRedraw"); }
    function _closeContextMenus() { GraphCanvasRootApi.invoke(interactionState, "_closeContextMenus"); }
    function _clampMenuPosition(x, y, menuWidth, menuHeight) { return GraphCanvasRootApi.clampMenuPosition(root, x, y, menuWidth, menuHeight); }
    function _openEdgeContext(edgeId, x, y) { GraphCanvasRootApi.invoke(interactionState, "_openEdgeContext", [edgeId, x, y]); }
    function _openNodeContext(nodeId, x, y) { GraphCanvasRootApi.invoke(interactionState, "_openNodeContext", [nodeId, x, y]); }
    function _openSelectionContext(x, y) { GraphCanvasRootApi.invoke(interactionState, "_openSelectionContext", [x, y]); }
    function requestOpenLockedNodeStatusAction() {
        if (!root.lockedNodeStatusActionVisible)
            return false;
        return true;
    }

    function clearViewerFocus() { return GraphCanvasRootApi.invoke(actionRouter, "clearViewerFocus", [], false); }

    GraphCanvasComponents.GraphCanvasRootLayers {
        id: rootLayers
        canvasItem: root
        sceneStateBridge: root.sceneStateBridge
        viewStateBridge: root.viewBridge
        viewCommandBridge: root.viewBridge
        minimapSimplificationActive: root.minimapSimplificationActive
    }

    DropArea {
        id: osPathDropArea
        objectName: "graphCanvasOsPathDropArea"
        anchors.fill: parent
        keys: ["text/uri-list", "text/plain", "application/x-corex-path-pointer"]
        z: 5

        onEntered: function(drag) {
            var path = root._pathFromDropEvent(drag);
            if (!path.length)
                return;
            drag.accept(Qt.CopyAction);
            root.updatePathPointerDropPreview(drag.x, drag.y, path, false);
        }

        onPositionChanged: function(drag) {
            var path = root._pathFromDropEvent(drag);
            if (!path.length) {
                root.clearLibraryDropPreview();
                return;
            }
            drag.accept(Qt.CopyAction);
            root.updatePathPointerDropPreview(drag.x, drag.y, path, false);
        }

        onExited: root.clearLibraryDropPreview()

        onDropped: function(drop) {
            var path = root._pathFromDropEvent(drop);
            if (!path.length) {
                root.clearLibraryDropPreview();
                return;
            }
            drop.accept(Qt.CopyAction);
            root.performPathPointerDrop(drop.x, drop.y, path, false);
        }
    }

    Item {
        id: lockedNodeStatusRibbon
        objectName: "graphCanvasLockedNodeStatusRibbon"
        visible: root.lockedNodeStatusVisible
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        anchors.topMargin: 12
        height: 28
        z: 7

        Rectangle {
            id: lockedNodeStatusPill
            objectName: "graphCanvasLockedNodeStatusPill"
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: Math.ceil(lockedNodeStatusTextItem.implicitWidth) + 20
            height: 24
            radius: 4
            color: "#151b26"
            opacity: 0.84
            border.width: 1
            border.color: "#2d3442"

            Text {
                id: lockedNodeStatusTextItem
                objectName: "graphCanvasLockedNodeStatusText"
                anchors.centerIn: parent
                text: root.lockedNodeStatusText
                color: root.lockedNodeStatusMutedTextColor
                font.pixelSize: 11
                font.weight: Font.Medium
                renderType: Text.CurveRendering
            }
        }

        Rectangle {
            id: lockedNodeStatusAction
            objectName: "graphCanvasLockedNodeStatusAction"
            visible: root.lockedNodeStatusActionVisible
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            width: Math.ceil(lockedNodeStatusActionText.implicitWidth) + 22
            height: 24
            radius: 4
            color: root.lockedNodeStatusActionColor
            border.width: 1
            border.color: Qt.lighter(root.lockedNodeStatusActionColor, 1.12)

            Text {
                id: lockedNodeStatusActionText
                objectName: "graphCanvasLockedNodeStatusActionText"
                anchors.centerIn: parent
                text: "Load missing add-ons"
                color: "#f7fbff"
                font.pixelSize: 11
                font.weight: Font.DemiBold
                renderType: Text.CurveRendering
            }

            MouseArea {
                objectName: "graphCanvasLockedNodeStatusActionMouseArea"
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.requestOpenLockedNodeStatusAction()
            }
        }
    }

    function hostForNodeId(nodeId) {
        return rootLayers.hostForNodeId(nodeId);
    }

    function requestInlineRenameForNode(nodeId) {
        var host = rootLayers.hostForNodeId(nodeId);
        if (host && host.beginInlineTitleEdit)
            return host.beginInlineTitleEdit();
        return false;
    }

    GraphCanvasComponents.GraphCanvasInputLayers {
        id: inputLayers
        objectName: "graphCanvasInputLayers"
        canvasItem: root
        canvasActionRouter: root.canvasActionRouter
        graphActionBridge: root.graphActionBridgeRef
        canvasCommandBridge: root.canvasCommandBridgeRef
        sceneCommandBridge: root.sceneCommandBridge
        viewStateBridge: root.viewBridge
        viewCommandBridge: root.viewBridge
        themePalette: root.themePalette
        boxZoomDragThreshold: root.boxZoomDragThreshold
        boxZoomPaddingPx: root.boxZoomPaddingPx
    }

    GraphCanvasComponents.GraphCanvasContextMenus {
        id: contextMenus
        objectName: "graphCanvasContextMenus"
        canvasItem: root
        canvasActionRouter: root.canvasActionRouter
        commandBridge: root.canvasCommandBridgeRef
        graphActionBridge: root.graphActionBridgeRef
        themePalette: root.themePalette
    }

    function _resetCanvasSceneState() { GraphCanvasRootApi.invoke(sceneLifecycle, "resetCanvasSceneState"); }

    onCanvasStateBridgeChanged: root._resetCanvasSceneState()
    onCanvasCommandBridgeChanged: root._resetCanvasSceneState()
    onCanvasViewBridgeChanged: root._resetCanvasSceneState()
    onSceneBridgeChanged: root._resetCanvasSceneState()
    onWidthChanged: viewportController.updateViewportSize()
    onHeightChanged: viewportController.updateViewportSize()

    Component.onDestruction: {
        canvasPerformancePolicy.clearStructuralMutation();
        viewStateRedrawFlushTimer.stop();
        interactionIdleTimer.stop();
        interactionState.releaseHostReferences();
    }
}
