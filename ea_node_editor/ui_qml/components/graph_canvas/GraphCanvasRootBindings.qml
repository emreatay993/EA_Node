import QtQuick 2.15
import QtQml 2.15
import "GraphCanvasPerformancePolicy.js" as GraphCanvasPerformancePolicyLogic

QtObject {
    id: root
    property var graphActionBridge: null
    property var canvasStateBridge: null
    property var canvasCommandBridge: null
    property var canvasViewBridge: null
    property var viewportController: null
    property var canvasPerformancePolicy: null
    property real nodeRenderActivationPaddingPx: 240.0

    readonly property var graphActionBridgeRef: root.graphActionBridge || null
    readonly property var canvasStateBridgeRef: root.canvasStateBridge || null
    readonly property var canvasCommandBridgeRef: root.canvasCommandBridge || null
    readonly property var canvasViewBridgeRef: root.canvasViewBridge
        || root._viewportBridgeFrom(root.canvasStateBridgeRef)
        || root._viewportBridgeFrom(root.canvasCommandBridgeRef)
    readonly property var _canvasStateBridgeRef: root.canvasStateBridgeRef
    readonly property var _canvasViewStateBridgeRef: root.canvasViewBridgeRef
    readonly property var sceneStateBridge: root.canvasStateBridgeRef
    readonly property var sceneCommandBridge: root.canvasCommandBridgeRef
    readonly property var sceneBridge: root.canvasStateBridgeRef
    readonly property var viewBridge: root.canvasViewBridgeRef
    readonly property var visibleSceneRectPayload: root.canvasViewBridgeRef
        ? (root.canvasViewBridgeRef.visible_scene_rect_payload_cached !== undefined
            ? root.canvasViewBridgeRef.visible_scene_rect_payload_cached
            : root.canvasViewBridgeRef.visible_scene_rect_payload)
        : ({})
    readonly property var failedNodeLookup: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.failed_node_lookup
        : ({})
    readonly property int failedNodeRevision: root._canvasStateBridgeRef
        ? Number(root._canvasStateBridgeRef.failed_node_revision)
        : 0
    readonly property string failedNodeTitle: root._canvasStateBridgeRef
        ? String(root._canvasStateBridgeRef.failed_node_title || "")
        : ""
    readonly property var runningNodeLookup: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.running_node_lookup
        : ({})
    readonly property var completedNodeLookup: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.completed_node_lookup
        : ({})
    readonly property bool hideLockedPorts: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.hide_locked_ports)
        : false
    readonly property bool hideOptionalPorts: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.hide_optional_ports)
        : false
    readonly property var runningNodeStartedAtMsLookup: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.running_node_started_at_ms_lookup
        : ({})
    readonly property var nodeElapsedMsLookup: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.node_elapsed_ms_lookup
        : ({})
    readonly property var progressedExecutionEdgeLookup: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.progressed_execution_edge_lookup
        : ({})
    readonly property int nodeExecutionRevision: root._canvasStateBridgeRef
        ? Number(root._canvasStateBridgeRef.node_execution_revision)
        : 0
    readonly property var nodeRenderActivationSceneRectPayload: root.viewportController
        ? root.viewportController.inflateSceneRectPayload(
            root.visibleSceneRectPayload,
            root.viewportController.scenePaddingForViewportPixels(root.nodeRenderActivationPaddingPx)
        )
        : ({})
    readonly property bool minimapExpanded: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.graphics_minimap_expanded)
        : true
    readonly property bool showGrid: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.graphics_show_grid)
        : true
    readonly property bool minimapVisible: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.graphics_show_minimap)
        : true
    readonly property bool showPortLabels: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.graphics_show_port_labels)
        : true
    readonly property bool showTooltips: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.graphics_show_tooltips)
        : true
    readonly property int graphLabelPixelSize: {
        if (!root._canvasStateBridgeRef)
            return 10;
        return root._normalizePixelSize(root._canvasStateBridgeRef.graphics_graph_label_pixel_size, 10, 18);
    }
    readonly property var graphNodeIconPixelSizeOverride: root._canvasStateBridgeRef
        ? root._normalizeNullablePixelSize(root._canvasStateBridgeRef.graphics_graph_node_icon_pixel_size_override, 50)
        : null
    readonly property int nodeTitleIconPixelSize: {
        if (!root._canvasStateBridgeRef)
            return root.graphLabelPixelSize;
        return root._normalizePixelSize(
            root._canvasStateBridgeRef.graphics_node_title_icon_pixel_size,
            root.graphLabelPixelSize,
            50
        );
    }
    readonly property string edgeCrossingStyle: root._canvasStateBridgeRef
        ? String(root._canvasStateBridgeRef.graphics_edge_crossing_style || "none")
        : "none"
    readonly property bool nodeShadowEnabled: root._canvasStateBridgeRef
        ? Boolean(root._canvasStateBridgeRef.graphics_node_shadow)
        : true
    readonly property int shadowStrength: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.graphics_shadow_strength
        : 70
    readonly property int shadowSoftness: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.graphics_shadow_softness
        : 50
    readonly property int shadowOffset: root._canvasStateBridgeRef
        ? root._canvasStateBridgeRef.graphics_shadow_offset
        : 4
    readonly property string graphicsPerformanceMode: root._canvasStateBridgeRef
        ? GraphCanvasPerformancePolicyLogic.normalizePerformanceMode(
            root._canvasStateBridgeRef.graphics_performance_mode
        )
        : "full_fidelity"
    readonly property string resolvedGraphicsPerformanceMode: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.resolvedMode
        : "full_fidelity"
    readonly property bool mutationBurstActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.mutationBurstActive
        : false
    readonly property bool transientPerformanceActivityActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.transientActivityActive
        : false
    readonly property bool transientDegradedWindowActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.transientDegradedWindowActive
        : false
    readonly property bool edgeLabelSimplificationActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.edgeLabelSimplificationActive
            || root.transientDegradedWindowActive
        : false
    readonly property bool gridSimplificationActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.gridSimplificationActive
            || root.transientDegradedWindowActive
        : false
    readonly property bool minimapSimplificationActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.minimapSimplificationActive
            || root.transientDegradedWindowActive
        : false
    readonly property bool shadowSimplificationActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.shadowSimplificationActive
            || (root.canvasPerformancePolicy.maxPerformanceMode && root.mutationBurstActive)
        : false
    readonly property bool snapshotProxyReuseActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.snapshotProxyReuseActive
            || root.transientDegradedWindowActive
        : false
    readonly property bool fullFidelityMode: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.fullFidelityMode
        : true
    readonly property bool viewportInteractionWorldCacheActive: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.viewportWorldCacheActive
        : false
    readonly property bool highQualityRendering: root.canvasPerformancePolicy
        ? root.canvasPerformancePolicy.highQualityRendering
            && !root.transientDegradedWindowActive
        : true
    readonly property string gridStyle: root._canvasStateBridgeRef
        ? String(root._canvasStateBridgeRef.graphics_grid_style || "lines")
        : "lines"

    function _normalizePixelSize(value, fallback, maxValue) {
        if (typeof value === "boolean")
            return fallback;
        var numeric = Math.round(Number(value));
        if (!isFinite(numeric))
            return fallback;
        return Math.max(8, Math.min(maxValue, numeric));
    }

    function _normalizeNullablePixelSize(value, maxValue) {
        if (value === null || value === undefined || typeof value === "boolean")
            return null;
        var numeric = Math.round(Number(value));
        if (!isFinite(numeric))
            return null;
        return Math.max(8, Math.min(maxValue, numeric));
    }

    function _viewportBridgeFrom(bridge) {
        if (bridge && bridge.viewport_bridge)
            return bridge.viewport_bridge;
        return null;
    }
}
