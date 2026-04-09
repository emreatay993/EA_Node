import QtQuick 2.15
import QtQml 2.15
import "GraphCanvasPerformancePolicy.js" as GraphCanvasPerformancePolicyLogic

QtObject {
    id: root
    property var canvasStateBridge: null
    property var canvasCommandBridge: null
    property var canvasViewBridge: null
    property var viewportController: null
    property var canvasPerformancePolicy: null
    property real nodeRenderActivationPaddingPx: 240.0

    readonly property var canvasStateBridgeRef: root.canvasStateBridge || null
    readonly property var canvasCommandBridgeRef: root.canvasCommandBridge || null
    readonly property var canvasViewBridgeRef: root.canvasViewBridge || null
    readonly property var _canvasStateBridgeRef: root.canvasStateBridgeRef
    readonly property var _canvasSceneStateBridgeRef: root.canvasStateBridgeRef
    readonly property var _legacyCanvasViewBridgeRef: root.canvasStateBridgeRef
        && root.canvasStateBridgeRef.viewport_bridge
        ? root.canvasStateBridgeRef.viewport_bridge
        : (root.canvasCommandBridgeRef
            && root.canvasCommandBridgeRef.viewport_bridge
            ? root.canvasCommandBridgeRef.viewport_bridge
            : null)
    readonly property var _canvasViewStateBridgeRef: root.canvasViewBridgeRef || root._legacyCanvasViewBridgeRef
    readonly property var _canvasShellCommandBridgeRef: root.canvasCommandBridgeRef
    readonly property var _canvasSceneCommandBridgeRef: root.canvasCommandBridgeRef
    readonly property var _canvasViewCommandBridgeRef: root._canvasViewStateBridgeRef
    readonly property var sceneStateBridge: root._canvasSceneStateBridgeRef
    readonly property var sceneCommandBridge: root._canvasSceneCommandBridgeRef
    readonly property var sceneBridge: root._canvasSceneStateBridgeRef
    readonly property var viewBridge: root._canvasViewStateBridgeRef
    readonly property var visibleSceneRectPayload: root._canvasViewStateBridgeRef
        ? (root._canvasViewStateBridgeRef.visible_scene_rect_payload_cached !== undefined
            ? root._canvasViewStateBridgeRef.visible_scene_rect_payload_cached
            : root._canvasViewStateBridgeRef.visible_scene_rect_payload)
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
    readonly property int graphLabelPixelSize: {
        if (!root._canvasStateBridgeRef)
            return 10;
        var numeric = Math.round(Number(root._canvasStateBridgeRef.graphics_graph_label_pixel_size));
        if (!isFinite(numeric))
            return 10;
        return Math.max(8, Math.min(18, numeric));
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
}
