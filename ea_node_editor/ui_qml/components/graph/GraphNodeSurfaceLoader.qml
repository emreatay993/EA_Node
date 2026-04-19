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
    readonly property bool hostReadOnly: host ? Boolean(host.graphReadOnly) : false
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
    readonly property bool blocksHostInteraction: hostReadOnly || (loader.item ? Boolean(loader.item.blocksHostInteraction) : false)
    readonly property rect lockedPlaceholderActionRect: {
        if (!loader.item || loader.item.lockedPlaceholderActionRect === undefined || loader.item.lockedPlaceholderActionRect === null)
            return Qt.rect(0.0, 0.0, 0.0, 0.0);
        return _rectValue(loader.item.lockedPlaceholderActionRect);
    }
    readonly property var embeddedInteractiveRects: {
        if (hostReadOnly)
            return [];
        if (!loader.item || loader.item.embeddedInteractiveRects === undefined || loader.item.embeddedInteractiveRects === null)
            return [];
        return loader.item.embeddedInteractiveRects;
    }
    readonly property var surfaceActions: {
        if (hostReadOnly)
            return [];
        if (!loader.item || loader.item.surfaceActions === undefined || loader.item.surfaceActions === null)
            return [];
        return loader.item.surfaceActions;
    }

    function dispatchSurfaceAction(actionId) {
        if (hostReadOnly)
            return false;
        if (loader.item && loader.item.dispatchSurfaceAction)
            return Boolean(loader.item.dispatchSurfaceAction(actionId));
        return false;
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
            if (root.host && root.host.lockedPlaceholderActive)
                return lockedPlaceholderComponent;
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
        id: lockedPlaceholderComponent

        Item {
            id: lockedPlaceholderSurface
            objectName: "graphNodeLockedPlaceholderSurface"
            property Item host: root.host
            readonly property var metrics: host && host.surfaceMetrics ? host.surfaceMetrics : ({})
            readonly property real bodyLeftMargin: Math.max(0.0, Number(metrics.body_left_margin || 0.0))
            readonly property real bodyRightMargin: Math.max(0.0, Number(metrics.body_right_margin || 0.0))
            readonly property real bodyTop: Math.max(0.0, Number(metrics.body_top || 0.0))
            readonly property real bodyHeight: Math.max(0.0, Number(metrics.body_height || 0.0))
            readonly property real ribbonHeight: Math.max(24.0, Math.min(32.0, bodyHeight > 0.0 ? bodyHeight - 2.0 : 28.0))
            readonly property real ribbonWidth: Math.max(0.0, width - bodyLeftMargin - bodyRightMargin)
            readonly property real ribbonY: bodyTop + Math.max(0.0, (bodyHeight - ribbonHeight) * 0.5)
            readonly property rect lockedPlaceholderActionRect: openManagerButton.visible
                ? Qt.rect(
                    ribbon.x + openManagerButton.x,
                    ribbon.y + openManagerButton.y,
                    openManagerButton.width,
                    openManagerButton.height
                )
                : Qt.rect(0.0, 0.0, 0.0, 0.0)
            readonly property bool blocksHostInteraction: true
            readonly property var embeddedInteractiveRects: []
            readonly property var surfaceActions: []

            Rectangle {
                id: ribbon
                objectName: "graphNodeLockedPlaceholderRibbon"
                x: lockedPlaceholderSurface.bodyLeftMargin
                y: lockedPlaceholderSurface.ribbonY
                width: lockedPlaceholderSurface.ribbonWidth
                height: lockedPlaceholderSurface.ribbonHeight
                radius: 6
                color: "#1d2430"
                border.width: 1
                border.color: "#4e596d"

                Text {
                    id: lockedLabel
                    objectName: "graphNodeLockedPlaceholderLabel"
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: host ? host.lockedPlaceholderLabel : "Requires add-on"
                    color: host ? host.headerTextColor : "#e7edf8"
                    font.pixelSize: 10
                    font.bold: true
                    renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                }

                Text {
                    id: packageLabel
                    objectName: "graphNodeLockedPlaceholderPackage"
                    anchors.left: lockedLabel.right
                    anchors.leftMargin: 8
                    anchors.right: openManagerButton.visible ? openManagerButton.left : parent.right
                    anchors.rightMargin: openManagerButton.visible ? 8 : 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: host ? host.lockedPlaceholderPackageText : ""
                    color: host ? host.portLabelColor : "#b0bacb"
                    font.pixelSize: 10
                    elide: Text.ElideRight
                    renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                }

                Rectangle {
                    id: openManagerButton
                    objectName: "graphNodeLockedPlaceholderButton"
                    visible: host ? host.lockedPlaceholderManagerAvailable : false
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    width: 70
                    height: Math.max(20, parent.height - 8)
                    radius: 5
                    color: "#253349"
                    border.width: 1
                    border.color: "#5d86c6"

                    Text {
                        anchors.centerIn: parent
                        text: "Manager"
                        color: "#eef3ff"
                        font.pixelSize: 10
                        font.bold: true
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }
                }
            }
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
