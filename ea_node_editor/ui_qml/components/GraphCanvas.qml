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
    readonly property var canvasStateBridgeRef: root.canvasStateBridge
        ? root.canvasStateBridge
        : null
    readonly property var canvasCommandBridgeRef: root.canvasCommandBridge
        ? root.canvasCommandBridge
        : null
    property var mainWindowBridge: root.canvasCommandBridgeRef
        ? root.canvasCommandBridgeRef
        : null
    property var sceneBridge: root.canvasStateBridgeRef
        ? root.canvasStateBridgeRef
        : null
    property var viewBridge: root.canvasStateBridgeRef
        ? root.canvasStateBridgeRef
        : null
    readonly property var _canvasStateBridgeRef: root.canvasStateBridgeRef
        ? root.canvasStateBridgeRef
        : root.mainWindowBridge
    readonly property var _canvasSceneStateBridgeRef: root.canvasStateBridgeRef
        ? root.canvasStateBridgeRef
        : root.sceneBridge
    readonly property var _canvasStateViewportBridgeRef: root.canvasStateBridgeRef
        && root.canvasStateBridgeRef.viewport_bridge
        ? root.canvasStateBridgeRef.viewport_bridge
        : null
    readonly property var _canvasCommandViewportBridgeRef: root.canvasCommandBridgeRef
        && root.canvasCommandBridgeRef.viewport_bridge
        ? root.canvasCommandBridgeRef.viewport_bridge
        : null
    readonly property var _canvasRawViewBridgeRef: root._canvasStateViewportBridgeRef
        ? root._canvasStateViewportBridgeRef
        : (root._canvasCommandViewportBridgeRef
            ? root._canvasCommandViewportBridgeRef
            : root.viewBridge)
    readonly property var _canvasViewStateBridgeRef: root._canvasRawViewBridgeRef
        ? root._canvasRawViewBridgeRef
        : (root.canvasStateBridgeRef
            ? root.canvasStateBridgeRef
            : root.viewBridge)
    readonly property var _canvasShellCommandBridgeRef: root.canvasCommandBridgeRef
        ? root.canvasCommandBridgeRef
        : root.mainWindowBridge
    readonly property var _canvasSceneCommandBridgeRef: root.canvasCommandBridgeRef
        ? root.canvasCommandBridgeRef
        : root.sceneBridge
    readonly property var _canvasViewCommandBridgeRef: root.canvasCommandBridgeRef
        ? root.canvasCommandBridgeRef
        : root._canvasRawViewBridgeRef
    readonly property var _canvasCompatBridgeRef: typeof graphCanvasBridge !== "undefined"
        ? graphCanvasBridge
        : null
    property var overlayHostItem: null
    property var edgePayload: []
    property var liveDragOffsets: ({})
    property var liveNodeGeometry: ({})
    property var selectedEdgeIds: []
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
        return GraphCanvasLogic.normalizeEdgeIds(values);
    }

    function _availableEdgeIdSet() {
        return GraphCanvasLogic.availableEdgeIdSet(root.edgePayload);
    }

    function pruneSelectedEdges() {
        root.selectedEdgeIds = GraphCanvasLogic.pruneSelectedEdgeIds(root.selectedEdgeIds, _availableEdgeIdSet());
    }

    function clearEdgeSelection() {
        if (!root.selectedEdgeIds.length)
            return;
        root.selectedEdgeIds = [];
    }

    function toggleEdgeSelection(edgeId) {
        var next = _normalizeEdgeIds(root.selectedEdgeIds);
        var index = next.indexOf(edgeId);
        if (index >= 0)
            next.splice(index, 1);
        else
            next.push(edgeId);
        root.selectedEdgeIds = next;
    }

    function setExclusiveEdgeSelection(edgeId) {
        root.selectedEdgeIds = edgeId ? [edgeId] : [];
    }

    function _sceneNodePayload(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return null;
        var nodes = root._sceneAllNodesModel();
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (node && node.node_id === normalized)
                return node;
        }
        return null;
    }

    function _sceneBackdropNodesModel() {
        var compatBridge = root._canvasCompatBridgeRef;
        if (compatBridge && compatBridge.backdrop_nodes_model !== undefined)
            return compatBridge.backdrop_nodes_model || [];
        var stateBridge = root._canvasSceneStateBridgeRef;
        if (stateBridge && stateBridge.backdrop_nodes_model !== undefined)
            return stateBridge.backdrop_nodes_model || [];
        return [];
    }

    function _sceneAllNodesModel() {
        var nodes = root._canvasSceneStateBridgeRef ? root._canvasSceneStateBridgeRef.nodes_model : [];
        var backdrops = root._sceneBackdropNodesModel();
        if (!backdrops.length)
            return nodes;
        return nodes.concat(backdrops);
    }

    function _sceneEdgePayload(edgeId) {
        var normalized = String(edgeId || "").trim();
        if (!normalized)
            return null;
        var edges = root.edgePayload || [];
        for (var i = 0; i < edges.length; i++) {
            var edge = edges[i];
            if (edge && edge.edge_id === normalized)
                return edge;
        }
        return null;
    }

    function _nodeSupportsPassiveStyle(nodeId) {
        var payload = _sceneNodePayload(nodeId);
        if (!payload)
            return false;
        return String(payload.runtime_behavior || "").toLowerCase() === "passive";
    }

    function _edgeSupportsFlowStyle(edgeId) {
        var payload = _sceneEdgePayload(edgeId);
        if (!payload)
            return false;
        return String(payload.edge_family || "").toLowerCase() === "flow";
    }

    function _nodeCanEnterScope(nodeId) {
        var payload = _sceneNodePayload(nodeId);
        if (!payload)
            return false;
        if (payload.can_enter_scope !== undefined)
            return Boolean(payload.can_enter_scope);
        return String(payload.type_id || "") === "core.subnode";
    }

    function requestOpenSubnodeScope(nodeId) {
        var bridge = root._canvasShellCommandBridgeRef;
        if (!bridge || !bridge.request_open_subnode_scope)
            return false;
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        var opened = bridge.request_open_subnode_scope(normalized);
        if (!opened)
            return false;
        root.clearEdgeSelection();
        root.clearPendingConnection();
        root._closeContextMenus();
        return true;
    }

    function _nodeSurfaceSelectionBridge() {
        var bridge = root._canvasSceneCommandBridgeRef;
        if (bridge && bridge.select_node)
            return bridge;
        return null;
    }

    function _nodeSurfacePendingActionBridge() {
        var bridge = root._canvasSceneCommandBridgeRef;
        if (bridge && bridge.set_pending_surface_action && bridge.consume_pending_surface_action)
            return bridge;
        return null;
    }

    function _nodeSurfacePropertyBridge() {
        var bridge = root._canvasSceneCommandBridgeRef;
        if (bridge && bridge.set_node_properties)
            return bridge;
        return null;
    }

    function _nodeSurfaceCursorBridge() {
        var bridge = root._canvasShellCommandBridgeRef;
        if (bridge && bridge.set_graph_cursor_shape && bridge.clear_graph_cursor_shape)
            return bridge;
        return null;
    }

    function _nodeSurfacePdfPreviewBridge() {
        var bridge = root._canvasShellCommandBridgeRef;
        if (bridge && bridge.describe_pdf_preview)
            return bridge;
        return null;
    }

    function prepareNodeSurfaceControlInteraction(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        root._closeContextMenus();
        root.cancelWireDrag();
        root.clearPendingConnection();
        root.clearEdgeSelection();
        var bridge = root._canvasSceneCommandBridgeRef;
        if (bridge && bridge.select_node)
            bridge.select_node(normalized, false);
        return true;
    }

    function commitNodeSurfaceProperty(nodeId, key, value) {
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedKey = String(key || "").trim();
        if (!normalizedNodeId || !normalizedKey)
            return false;
        root.prepareNodeSurfaceControlInteraction(normalizedNodeId);
        var bridge = root._canvasSceneCommandBridgeRef;
        if (!bridge || !bridge.set_node_property)
            return false;
        bridge.set_node_property(normalizedNodeId, normalizedKey, value);
        return true;
    }

    function commitNodePortLabel(nodeId, portKey, label) {
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedPortKey = String(portKey || "").trim();
        if (!normalizedNodeId || !normalizedPortKey)
            return false;
        root.prepareNodeSurfaceControlInteraction(normalizedNodeId);
        var bridge = root._canvasSceneCommandBridgeRef;
        if (!bridge || !bridge.set_node_port_label)
            return false;
        bridge.set_node_port_label(normalizedNodeId, normalizedPortKey, String(label || ""));
        return true;
    }

    function requestNodeSurfaceCropEdit(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        var selectionBridge = root._nodeSurfaceSelectionBridge();
        var needsSelection = root.selectedNodeIds().indexOf(normalized) < 0;
        if (needsSelection) {
            var pendingBridge = root._nodeSurfacePendingActionBridge();
            if (!selectionBridge || !pendingBridge)
                return false;
            root._closeContextMenus();
            root.cancelWireDrag();
            root.clearPendingConnection();
            root.clearEdgeSelection();
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
        var bridge = root._nodeSurfacePendingActionBridge();
        if (!bridge)
            return false;
        return Boolean(bridge.consume_pending_surface_action(normalized));
    }

    function commitNodeSurfaceProperties(nodeId, properties) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return false;
        root.prepareNodeSurfaceControlInteraction(normalized);
        var bridge = root._nodeSurfacePropertyBridge();
        if (bridge)
            return Boolean(bridge.set_node_properties(normalized, properties || ({})));
        bridge = root._canvasSceneCommandBridgeRef;
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
        var bridge = root._nodeSurfaceCursorBridge();
        if (!bridge)
            return false;
        bridge.set_graph_cursor_shape(cursorShape);
        return true;
    }

    function clearNodeSurfaceCursorShape() {
        var bridge = root._nodeSurfaceCursorBridge();
        if (!bridge)
            return false;
        bridge.clear_graph_cursor_shape();
        return true;
    }

    function describeNodeSurfacePdfPreview(source, pageNumber) {
        var bridge = root._nodeSurfacePdfPreviewBridge();
        if (!bridge)
            return ({});
        return bridge.describe_pdf_preview(String(source || ""), pageNumber);
    }

    function browseNodePropertyPath(nodeId, key, currentPath) {
        var normalizedNodeId = String(nodeId || "").trim();
        var normalizedKey = String(key || "").trim();
        var bridge = root._canvasShellCommandBridgeRef;
        if (!normalizedNodeId || !normalizedKey || !bridge || !bridge.browse_node_property_path)
            return "";
        root.prepareNodeSurfaceControlInteraction(normalizedNodeId);
        return String(bridge.browse_node_property_path(
            normalizedNodeId,
            normalizedKey,
            String(currentPath || "")
        ) || "");
    }

    function selectedNodeIds() {
        var bridge = root._canvasSceneStateBridgeRef;
        var nodes = root._sceneAllNodesModel();
        var selectedLookup = null;
        if (bridge && typeof bridge.selected_node_lookup !== "undefined")
            selectedLookup = bridge.selected_node_lookup || ({});
        var selected = [];
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            var nodeId = node ? String(node.node_id || "").trim() : "";
            if (!nodeId)
                continue;
            if (selectedLookup !== null) {
                if (Boolean(selectedLookup[nodeId]))
                    selected.push(nodeId);
                continue;
            }
            if (node.selected)
                selected.push(nodeId);
        }
        return selected;
    }

    function _appendUniqueDragNodeId(nodeIds, seenNodeIds, nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized || Boolean(seenNodeIds[normalized]))
            return;
        seenNodeIds[normalized] = true;
        nodeIds.push(normalized);
    }

    function _payloadNodeIdList(payload, key) {
        if (!payload || payload[key] === undefined || payload[key] === null)
            return [];
        if (payload[key].length === undefined)
            return [payload[key]];
        return payload[key];
    }

    function _isCommentBackdropPayload(payload) {
        return !!payload && String(payload.surface_family || "").trim() === "comment_backdrop";
    }

    function _appendBackdropDragDescendants(nodeIds, seenNodeIds, backdropNodeId) {
        var payload = root._sceneNodePayload(backdropNodeId);
        if (!root._isCommentBackdropPayload(payload))
            return;

        var memberNodeIds = root._payloadNodeIdList(payload, "member_node_ids");
        for (var i = 0; i < memberNodeIds.length; i++)
            root._appendUniqueDragNodeId(nodeIds, seenNodeIds, memberNodeIds[i]);

        var memberBackdropIds = root._payloadNodeIdList(payload, "member_backdrop_ids");
        for (var j = 0; j < memberBackdropIds.length; j++)
            root._appendUniqueDragNodeId(nodeIds, seenNodeIds, memberBackdropIds[j]);
        for (var k = 0; k < memberBackdropIds.length; k++)
            root._appendBackdropDragDescendants(nodeIds, seenNodeIds, memberBackdropIds[k]);
    }

    function _appendBackdropAwareDragNodeIds(nodeIds, seenNodeIds, nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return;
        root._appendUniqueDragNodeId(nodeIds, seenNodeIds, normalized);
        root._appendBackdropDragDescendants(nodeIds, seenNodeIds, normalized);
    }

    function dragNodeIdsForAnchor(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return [];
        var selected = root.selectedNodeIds();
        var baseNodeIds = [];
        if (selected.length > 1 && selected.indexOf(normalized) >= 0) {
            baseNodeIds.push(normalized);
            for (var i = 0; i < selected.length; i++) {
                if (selected[i] !== normalized)
                    baseNodeIds.push(selected[i]);
            }
        } else {
            baseNodeIds.push(normalized);
        }

        var ordered = [];
        var seenNodeIds = {};
        for (var index = 0; index < baseNodeIds.length; index++)
            root._appendBackdropAwareDragNodeIds(ordered, seenNodeIds, baseNodeIds[index]);
        return ordered;
    }

    function setLiveDragOffsets(nodeIds, dx, dy) {
        var next = {};
        if (Math.abs(dx) >= 0.01 || Math.abs(dy) >= 0.01) {
            var source = nodeIds || [];
            for (var i = 0; i < source.length; i++) {
                var nodeId = String(source[i] || "").trim();
                if (!nodeId)
                    continue;
                next[nodeId] = {"dx": dx, "dy": dy};
            }
        }
        root.liveDragOffsets = next;
        edgeLayer.requestRedraw();
    }

    function clearLiveDragOffsets() {
        if (!root.liveDragOffsets || Object.keys(root.liveDragOffsets).length === 0)
            return;
        root.liveDragOffsets = ({});
        edgeLayer.requestRedraw();
    }

    function liveDragDxForNode(nodeId) {
        var entry = root.liveDragOffsets ? root.liveDragOffsets[String(nodeId || "").trim()] : null;
        var value = entry ? Number(entry.dx) : 0.0;
        return isFinite(value) ? value : 0.0;
    }

    function liveDragDyForNode(nodeId) {
        var entry = root.liveDragOffsets ? root.liveDragOffsets[String(nodeId || "").trim()] : null;
        var value = entry ? Number(entry.dy) : 0.0;
        return isFinite(value) ? value : 0.0;
    }

    function setLiveNodeGeometry(nodeId, x, y, width, height, active) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return;
        var next = {};
        var source = root.liveNodeGeometry || {};
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key))
                next[key] = source[key];
        }
        if (active) {
            next[normalized] = {
                "x": Number(x),
                "y": Number(y),
                "width": Math.max(1.0, Number(width)),
                "height": Math.max(1.0, Number(height))
            };
        } else {
            delete next[normalized];
        }
        root.liveNodeGeometry = next;
        edgeLayer.requestRedraw();
    }

    function clearLiveNodeGeometry() {
        if (!root.liveNodeGeometry || Object.keys(root.liveNodeGeometry).length === 0)
            return;
        root.liveNodeGeometry = ({});
        edgeLayer.requestRedraw();
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
        root.edgePayload = root._canvasSceneStateBridgeRef ? root._canvasSceneStateBridgeRef.edges_model : [];
        pruneSelectedEdges();
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

    Component {
        id: graphNodeHostDelegate

        GraphComponents.GraphNodeHost {
            id: nodeCard
            readonly property bool _backdropInputOverlay: parent && parent.objectName === "graphCanvasBackdropInputLayer"
            readonly property bool _commentBackdropNode: root._isCommentBackdropPayload(modelData)
            objectName: nodeCard._backdropInputOverlay ? "graphCommentBackdropInputCard" : "graphNodeCard"
            nodeData: modelData
            worldOffset: root.worldOffset
            canvasItem: root
            hoveredPort: root.hoveredPort
            previewPort: root.dropPreviewPort
            pendingPort: root.pendingConnectionPort
            dragSourcePort: root.wireDragSourcePort()
            liveDragDx: root.liveDragDxForNode(modelData.node_id)
            liveDragDy: root.liveDragDyForNode(modelData.node_id)
            showShadow: nodeCard._backdropInputOverlay ? false : root.nodeShadowEnabled
            shadowStrength: nodeCard._commentBackdropNode
                ? Math.max(10, Math.round(Number(root.shadowStrength) * 0.26))
                : root.shadowStrength
            shadowSoftness: nodeCard._commentBackdropNode
                ? Math.max(78, Math.round(Number(root.shadowSoftness) * 1.45))
                : root.shadowSoftness
            shadowOffset: nodeCard._commentBackdropNode
                ? Math.max(1, Math.round(Number(root.shadowOffset) * 0.5))
                : root.shadowOffset
            viewportInteractionCacheActive: root.viewportInteractionWorldCacheActive
            snapshotReuseActive: root.snapshotProxyReuseActive && !root.viewportInteractionWorldCacheActive
            shadowSimplificationActive: root.shadowSimplificationActive
            fullFidelityMode: canvasPerformancePolicy.fullFidelityMode
            renderActivationSceneRectPayload: root.nodeRenderActivationSceneRectPayload
            contextTargetNodeId: root.nodeContextNodeId
            showPortLabelsPreference: root.showPortLabels
            surfaceVariantOverride: nodeCard._backdropInputOverlay ? "comment_backdrop_input_overlay" : ""
            opacity: nodeCard._backdropInputOverlay
                ? (nodeCard.renderActive ? 1.0 : 0.001)
                : 1.0

            onNodeClicked: function(nodeId, additive) {
                var bridge = root._canvasSceneCommandBridgeRef;
                root.forceActiveFocus();
                root._closeContextMenus();
                root.clearPendingConnection();
                if (!bridge || !bridge.select_node)
                    return;
                if (!additive)
                    root.clearEdgeSelection();
                bridge.select_node(nodeId, additive);
            }
            onNodeContextRequested: function(nodeId, localX, localY) {
                var point = nodeCard.mapToItem(root, localX, localY);
                root._openNodeContext(nodeId, point.x, point.y);
            }
            onNodeOpenRequested: function(nodeId) {
                root.requestOpenSubnodeScope(nodeId);
            }
            onDragOffsetChanged: function(nodeId, dx, dy) {
                root.setLiveDragOffsets(
                    root.dragNodeIdsForAnchor(nodeId),
                    Number(dx),
                    Number(dy)
                );
            }
            onDragFinished: function(nodeId, finalX, finalY, _moved) {
                var bridge = root._canvasSceneCommandBridgeRef;
                var dragNodeIds = root.dragNodeIdsForAnchor(nodeId);
                var anchorPayload = root._sceneNodePayload(nodeId);
                var anchorX = anchorPayload ? Number(anchorPayload.x) : Number(finalX);
                var anchorY = anchorPayload ? Number(anchorPayload.y) : Number(finalY);
                if (!isFinite(anchorX))
                    anchorX = Number(finalX);
                if (!isFinite(anchorY))
                    anchorY = Number(finalY);
                var rawDeltaX = Number(finalX) - anchorX;
                var rawDeltaY = Number(finalY) - anchorY;
                var snappedDelta = root.snappedDragDelta(nodeId, rawDeltaX, rawDeltaY);
                var deltaX = Number(snappedDelta.dx);
                var deltaY = Number(snappedDelta.dy);
                if (!isFinite(deltaX))
                    deltaX = 0.0;
                if (!isFinite(deltaY))
                    deltaY = 0.0;
                var finalSnappedX = anchorX + deltaX;
                var finalSnappedY = anchorY + deltaY;
                var movedByCommit = Math.abs(deltaX) >= 0.01 || Math.abs(deltaY) >= 0.01;

                root.clearLiveDragOffsets();
                if (!bridge)
                    return;
                if (dragNodeIds.length > 1) {
                    movedByCommit = bridge.move_nodes_by_delta ? bridge.move_nodes_by_delta(dragNodeIds, deltaX, deltaY) : false;
                    if (movedByCommit)
                        root.clearEdgeSelection();
                    return;
                }

                if (bridge.move_node)
                    bridge.move_node(nodeId, finalSnappedX, finalSnappedY);
                if (movedByCommit && bridge.select_node) {
                    root.clearEdgeSelection();
                    bridge.select_node(nodeId, false);
                }
            }
            onDragCanceled: function(_nodeId) {
                root.clearLiveDragOffsets();
            }
            onResizePreviewChanged: function(nodeId, newX, newY, newWidth, newHeight, active) {
                root.setLiveNodeGeometry(nodeId, newX, newY, newWidth, newHeight, active);
            }
            onResizeFinished: function(nodeId, newX, newY, newWidth, newHeight) {
                var bridge = root._canvasSceneCommandBridgeRef;
                root.setLiveNodeGeometry(nodeId, newX, newY, newWidth, newHeight, false);
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
                root.handlePortClick(nodeId, portKey, direction, sceneX, sceneY);
            }
            onPortDragStarted: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY) {
                root.beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY);
            }
            onPortDragMoved: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive) {
                root.updatePortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive);
            }
            onPortDragFinished: function(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive) {
                root.finishPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY, dragActive);
            }
            onPortDragCanceled: function(_nodeId, _portKey, _direction) {
                root.cancelWireDrag();
            }
            onPortHoverChanged: function(nodeId, portKey, direction, sceneX, sceneY, hovered) {
                if (root.wireDragState && root.wireDragState.active)
                    return;
                if (hovered) {
                    var hoveredPortData = root._scenePortData(nodeId, portKey);
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
                    root.hoveredPort = {
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
                        root.hoveredPort.side = hoveredSide;
                    edgeLayer.requestRedraw();
                } else if (
                    root.hoveredPort
                    && root.hoveredPort.node_id === nodeId
                    && root.hoveredPort.port_key === portKey
                ) {
                    root.hoveredPort = null;
                    edgeLayer.requestRedraw();
                }
            }
            onSurfaceControlInteractionStarted: function(nodeId) {
                root.prepareNodeSurfaceControlInteraction(nodeId);
            }
            onInlinePropertyCommitted: function(nodeId, key, value) {
                if (root.commitNodeSurfaceProperty(nodeId, key, value))
                    root.forceActiveFocus();
            }
            onPortLabelCommitted: function(nodeId, portKey, label) {
                if (root.commitNodePortLabel(nodeId, portKey, label))
                    root.forceActiveFocus();
            }
        }
    }

    Item {
        id: backdropWorld
        objectName: "graphCanvasBackdropLayer"
        width: root.worldSize
        height: root.worldSize
        transformOrigin: Item.TopLeft
        scale: root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.zoom_value : 1.0
        x: root.width * 0.5 - ((root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.center_x : 0) + root.worldOffset) * scale
        y: root.height * 0.5 - ((root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.center_y : 0) + root.worldOffset) * scale

        Repeater {
            model: root._sceneBackdropNodesModel()
            delegate: graphNodeHostDelegate
        }
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

    Item {
        id: backdropInputWorld
        objectName: "graphCanvasBackdropInputLayer"
        width: root.worldSize
        height: root.worldSize
        transformOrigin: Item.TopLeft
        scale: root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.zoom_value : 1.0
        x: root.width * 0.5 - ((root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.center_x : 0) + root.worldOffset) * scale
        y: root.height * 0.5 - ((root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.center_y : 0) + root.worldOffset) * scale

        Repeater {
            model: root._sceneBackdropNodesModel()
            delegate: graphNodeHostDelegate
        }
    }

    GraphCanvasComponents.GraphCanvasDropPreview {
        id: dragNodePreview
        objectName: "graphCanvasDropPreview"
        canvasItem: root
        viewBridge: root._canvasViewStateBridgeRef
    }

    Item {
        id: world
        objectName: "graphCanvasWorld"
        width: root.worldSize
        height: root.worldSize
        transformOrigin: Item.TopLeft
        scale: root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.zoom_value : 1.0
        x: root.width * 0.5 - ((root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.center_x : 0) + root.worldOffset) * scale
        y: root.height * 0.5 - ((root._canvasViewStateBridgeRef ? root._canvasViewStateBridgeRef.center_y : 0) + root.worldOffset) * scale

        Repeater {
            model: root._canvasSceneStateBridgeRef ? root._canvasSceneStateBridgeRef.nodes_model : []
            delegate: graphNodeHostDelegate
        }
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
