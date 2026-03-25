import QtQuick 2.15
import "passive" as GraphPassiveComponents
import "viewer" as GraphViewerComponents

Item {
    id: root
    objectName: "graphNodeSurfaceLoader"
    property Item host: null
    property var nodeData: host ? host.nodeData : null
    property string surfaceFamily: host ? host.surfaceFamily : "standard"
    property string surfaceVariant: host ? host.surfaceVariant : ""
    readonly property var renderQuality: host ? host.renderQuality : ({
        "weight_class": "standard",
        "max_performance_strategy": "generic_fallback",
        "supported_quality_tiers": ["full"]
    })
    readonly property string requestedQualityTier: host ? host.requestedQualityTier : "full"
    readonly property string resolvedQualityTier: host ? host.resolvedQualityTier : "full"
    readonly property bool proxySurfaceRequested: host ? Boolean(host.proxySurfaceRequested) : false
    readonly property bool renderActive: host ? Boolean(host.renderActive) : true
    readonly property bool surfaceLoaded: !!loader.item
    readonly property bool proxySurfaceActive: proxySurfaceRequested && loader.item
        ? Boolean(loader.item.proxySurfaceActive)
        : false
    readonly property var viewerSurfaceContract: {
        if (loader.item && loader.item.viewerSurfaceContract !== undefined && loader.item.viewerSurfaceContract !== null)
            return loader.item.viewerSurfaceContract;
        if (root.nodeData && root.nodeData.viewer_surface)
            return root.nodeData.viewer_surface;
        return ({});
    }
    readonly property rect viewerBodyRect: {
        if (root.loadedSurfaceKey !== "viewer")
            return Qt.rect(0.0, 0.0, 0.0, 0.0);
        return _rectValue(root.viewerSurfaceContract.body_rect);
    }
    readonly property rect viewerProxySurfaceRect: {
        if (root.loadedSurfaceKey !== "viewer")
            return Qt.rect(0.0, 0.0, 0.0, 0.0);
        var contract = root.viewerSurfaceContract;
        return _rectValue(contract.proxy_rect !== undefined ? contract.proxy_rect : contract.body_rect);
    }
    readonly property rect viewerLiveSurfaceRect: {
        if (root.loadedSurfaceKey !== "viewer")
            return Qt.rect(0.0, 0.0, 0.0, 0.0);
        var contract = root.viewerSurfaceContract;
        return _rectValue(contract.live_rect !== undefined ? contract.live_rect : contract.body_rect);
    }
    readonly property var viewerBridgeBinding: {
        if (root.loadedSurfaceKey !== "viewer")
            return ({});
        if (loader.item && loader.item.viewerBridgeBinding !== undefined && loader.item.viewerBridgeBinding !== null)
            return loader.item.viewerBridgeBinding;
        var contract = root.viewerSurfaceContract;
        if (contract && contract.bridge_binding !== undefined && contract.bridge_binding !== null)
            return contract.bridge_binding;
        return ({});
    }
    readonly property var viewerInteractiveRects: {
        if (root.loadedSurfaceKey !== "viewer")
            return [];
        if (loader.item && loader.item.viewerInteractiveRects !== undefined && loader.item.viewerInteractiveRects !== null)
            return loader.item.viewerInteractiveRects;
        var contract = root.viewerSurfaceContract;
        if (contract && contract.interactive_rects !== undefined && contract.interactive_rects !== null)
            return contract.interactive_rects;
        return [];
    }
    readonly property var surfaceQualityContext: host ? host.surfaceQualityContext : ({
        "requested_quality_tier": root.requestedQualityTier,
        "resolved_quality_tier": root.resolvedQualityTier,
        "render_quality": root.renderQuality,
        "proxy_surface_requested": root.proxySurfaceRequested
    })
    readonly property string loadedSurfaceKey: _loadedSurfaceKey(surfaceFamily, surfaceVariant)
    readonly property real contentHeight: {
        if (!host || !nodeData)
            return 0.0;
        if (loader.item && Number(loader.item.implicitHeight) > 0.0)
            return Number(loader.item.implicitHeight);
        if (host.surfaceMetrics)
            return Number(host.surfaceMetrics.body_height || 0.0);
        return 0.0;
    }
    readonly property bool blocksHostInteraction: loader.item ? Boolean(loader.item.blocksHostInteraction) : false
    readonly property var embeddedInteractiveRects: {
        if (!loader.item || loader.item.embeddedInteractiveRects === undefined || loader.item.embeddedInteractiveRects === null)
            return [];
        return loader.item.embeddedInteractiveRects;
    }

    function _loadedSurfaceKey(family, _variant) {
        var normalizedFamily = String(family || "standard");
        if (normalizedFamily === "flowchart")
            return "flowchart";
        if (normalizedFamily === "planning")
            return "planning";
        if (normalizedFamily === "annotation")
            return "annotation";
        if (normalizedFamily === "comment_backdrop")
            return "comment_backdrop";
        if (normalizedFamily === "media")
            return "media";
        if (normalizedFamily === "viewer")
            return "viewer";
        return "standard";
    }

    function _rectValue(value) {
        var x = value !== undefined && value !== null ? Number(value.x) : NaN;
        var y = value !== undefined && value !== null ? Number(value.y) : NaN;
        var width = value !== undefined && value !== null ? Number(value.width) : NaN;
        var height = value !== undefined && value !== null ? Number(value.height) : NaN;
        if (!isFinite(x))
            x = 0.0;
        if (!isFinite(y))
            y = 0.0;
        if (!isFinite(width))
            width = 0.0;
        if (!isFinite(height))
            height = 0.0;
        return Qt.rect(x, y, Math.max(0.0, width), Math.max(0.0, height));
    }

    function triggerHoverAction() {
        if (loader.item && loader.item.triggerHoverAction)
            loader.item.triggerHoverAction();
    }

    function requestInlineEditAt(localX, localY) {
        if (loader.item && loader.item.requestInlineEditAt)
            return Boolean(loader.item.requestInlineEditAt(localX, localY));
        return false;
    }

    function commitInlineEditFromExternalInteraction(localX, localY) {
        if (loader.item && loader.item.commitInlineEditFromExternalInteraction)
            return Boolean(loader.item.commitInlineEditFromExternalInteraction(localX, localY));
        return false;
    }

    Loader {
        id: loader
        anchors.fill: parent
        active: !!root.host && !!root.nodeData && !Boolean(root.nodeData.collapsed) && root.renderActive
        sourceComponent: {
            if (root.loadedSurfaceKey === "flowchart")
                return flowchartSurfaceComponent;
            if (root.loadedSurfaceKey === "planning")
                return planningSurfaceComponent;
            if (root.loadedSurfaceKey === "annotation")
                return annotationSurfaceComponent;
            if (root.loadedSurfaceKey === "comment_backdrop")
                return commentBackdropSurfaceComponent;
            if (root.loadedSurfaceKey === "media")
                return mediaSurfaceComponent;
            if (root.loadedSurfaceKey === "viewer")
                return viewerSurfaceComponent;
            return standardSurfaceComponent;
        }
    }

    Component {
        id: standardSurfaceComponent

        GraphStandardNodeSurface {
            host: root.host
        }
    }

    Component {
        id: flowchartSurfaceComponent

        GraphPassiveComponents.GraphFlowchartNodeSurface {
            host: root.host
        }
    }

    Component {
        id: planningSurfaceComponent

        GraphPassiveComponents.GraphPlanningCardSurface {
            host: root.host
        }
    }

    Component {
        id: annotationSurfaceComponent

        GraphPassiveComponents.GraphAnnotationNoteSurface {
            host: root.host
        }
    }

    Component {
        id: mediaSurfaceComponent

        GraphPassiveComponents.GraphMediaPanelSurface {
            host: root.host
        }
    }

    Component {
        id: commentBackdropSurfaceComponent

        GraphPassiveComponents.GraphCommentBackdropSurface {
            host: root.host
        }
    }

    Component {
        id: viewerSurfaceComponent

        GraphViewerComponents.GraphViewerSurface {
            host: root.host
        }
    }
}
