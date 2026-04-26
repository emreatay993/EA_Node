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
        if (root.nodeData && String(root.nodeData.type_id || "") === "io.folder_explorer")
            return "classic_explorer";
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
            if (root.loadedSurfaceKey === "classic_explorer")
                return classicExplorerSurfaceComponent;
            return standardSurfaceComponent;
        }
    }

    Component {
        id: lockedPlaceholderComponent

        Item {
            id: lockedPlaceholderSurface
            objectName: "graphNodeLockedPlaceholderSurface"
            anchors.fill: parent
            property Item host: root.host
            readonly property var metrics: host && host.surfaceMetrics ? host.surfaceMetrics : ({})
            readonly property real bodyLeftMargin: Math.max(0.0, Number(metrics.body_left_margin || 0.0))
            readonly property real bodyRightMargin: Math.max(0.0, Number(metrics.body_right_margin || 0.0))
            readonly property real bodyTop: Math.max(0.0, Number(metrics.body_top || 0.0))
            readonly property real bodyBottomMargin: Math.max(0.0, Number(metrics.body_bottom_margin || 0.0))
            readonly property real bodyInnerPadding: 8.0
            readonly property real loadRowHeight: 14.0
            readonly property real loadRowSpacing: 6.0
            readonly property real ribbonNaturalHeight: 38.0
            readonly property bool loadRowVisible: host ? Boolean(host.lockedPlaceholderManagerAvailable) : false
            readonly property real ribbonHeight: ribbonNaturalHeight
            readonly property real ribbonWidth: Math.max(0.0, width - bodyLeftMargin - bodyRightMargin)
            readonly property real ribbonY: bodyTop + bodyInnerPadding
            readonly property rect lockedPlaceholderActionRect: loadLinkRow.visible
                ? Qt.rect(
                    loadLinkRow.x + loadLink.x,
                    loadLinkRow.y + loadLink.y,
                    loadLink.width,
                    loadLink.height
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
                radius: 4
                color: host ? host.lockedPlaceholderRibbonFillColor : "#1a1c21"
                border.width: 1
                border.color: host ? host.lockedPlaceholderRibbonBorderColor : "#4a4f5a"

                Canvas {
                    id: ribbonDashedBorder
                    objectName: "graphNodeLockedPlaceholderRibbonDashedBorder"
                    anchors.fill: parent
                    antialiasing: false

                    property color dashColor: host
                        ? host.lockedPlaceholderRibbonBorderColor
                        : "#4a4f5a"

                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.clearRect(0, 0, width, height);
                        if (width <= 2 || height <= 2)
                            return;
                        ctx.strokeStyle = String(dashColor);
                        ctx.lineWidth = 1;
                        ctx.setLineDash([3, 3]);
                        ctx.strokeRect(0.5, 0.5, width - 1, height - 1);
                    }

                    Component.onCompleted: requestPaint()
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    onDashColorChanged: requestPaint()
                }

                Image {
                    id: ribbonPlugIcon
                    objectName: "graphNodeLockedPlaceholderPlugIcon"
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    width: 11
                    height: 11
                    sourceSize.width: 11
                    sourceSize.height: 11
                    fillMode: Image.PreserveAspectFit
                    smooth: host ? host.highQualityRendering : true
                    mipmap: host ? host.highQualityRendering : true
                    source: (typeof uiIcons !== "undefined" && uiIcons && uiIcons.has && uiIcons.has("plug"))
                        ? uiIcons.sourceSized("plug", 11, String(host ? host.lockedPlaceholderLabelColor : "#8a93a3"))
                        : ""
                }

                Column {
                    anchors.left: ribbonPlugIcon.right
                    anchors.leftMargin: 8
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    Text {
                        id: lockedLabel
                        objectName: "graphNodeLockedPlaceholderLabel"
                        width: parent.width
                        text: host ? host.lockedPlaceholderLabel : "Requires add-on"
                        color: host ? host.lockedPlaceholderLabelColor : "#8a93a3"
                        font.pixelSize: 9
                        font.letterSpacing: 0.3
                        font.capitalization: Font.AllUppercase
                        elide: Text.ElideRight
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    Text {
                        id: packageLabel
                        objectName: "graphNodeLockedPlaceholderPackage"
                        width: parent.width
                        text: host ? host.lockedPlaceholderPackageText : ""
                        color: host ? host.lockedPlaceholderPackageTextColor : "#d0d5de"
                        font.family: "Cascadia Mono, Cascadia Code, Consolas, monospace"
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }
                }
            }

            Item {
                id: loadLinkRow
                objectName: "graphNodeLockedPlaceholderButton"
                visible: lockedPlaceholderSurface.loadRowVisible
                x: lockedPlaceholderSurface.bodyLeftMargin
                y: ribbon.y + ribbon.height + lockedPlaceholderSurface.loadRowSpacing
                width: lockedPlaceholderSurface.ribbonWidth
                height: lockedPlaceholderSurface.loadRowHeight

                Text {
                    id: loadLink
                    objectName: "graphNodeLockedPlaceholderButtonText"
                    anchors.right: parent.right
                    anchors.rightMargin: 2
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Load..."
                    color: host ? host.lockedPlaceholderLinkColor : "#60cdff"
                    font.pixelSize: 10
                    font.bold: true
                    renderType: host ? host.nodeTextRenderType : Text.CurveRendering
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

    Component {
        id: classicExplorerSurfaceComponent

        GraphPassiveComponents.GraphClassicExplorerSurface {
            host: root.host
        }
    }
}
