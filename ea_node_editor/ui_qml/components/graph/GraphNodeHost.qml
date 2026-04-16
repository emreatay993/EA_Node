import QtQuick 2.15
import "GraphNodeSurfaceMetrics.js" as GraphNodeSurfaceMetrics

Item {
    id: card
    objectName: "graphNodeCard"
    property var nodeData: null
    property real worldOffset: 0
    property Item canvasItem: null
    property var renderActivationSceneRectPayload: ({})
    property string contextTargetNodeId: ""
    property var hoveredPort: null
    property var previewPort: null
    property var pendingPort: null
    property var dragSourcePort: null
    property real liveDragDx: 0
    property real liveDragDy: 0
    property bool showShadow: false
    property int shadowStrength: 70
    property int shadowSoftness: 50
    property int shadowOffset: 4
    property bool viewportInteractionCacheActive: false
    property bool snapshotReuseActive: false
    property bool shadowSimplificationActive: false
    property bool fullFidelityMode: true
    property bool showPortLabelsPreference: true
    property int graphLabelPixelSize: 10
    property string surfaceFamilyOverride: ""
    property string surfaceVariantOverride: ""
    readonly property bool highQualityRendering: card.canvasItem
        ? Boolean(card.canvasItem.highQualityRendering)
        : true
    readonly property int effectiveGraphLabelPixelSize: {
        var numeric = NaN;
        if (card.canvasItem && card.canvasItem.graphLabelPixelSize !== undefined)
            numeric = Number(card.canvasItem.graphLabelPixelSize);
        if (!isFinite(numeric) && card.canvasItem && card.canvasItem._canvasStateBridgeRef)
            numeric = Number(card.canvasItem._canvasStateBridgeRef.graphics_graph_label_pixel_size);
        if (!isFinite(numeric))
            numeric = Number(card.graphLabelPixelSize);
        if (!isFinite(numeric))
            numeric = 10;
        return Math.max(8, Math.min(18, Math.round(numeric)));
    }
    readonly property int effectiveNodeTitleIconPixelSize: {
        var numeric = NaN;
        if (card.canvasItem && card.canvasItem.nodeTitleIconPixelSize !== undefined)
            numeric = Number(card.canvasItem.nodeTitleIconPixelSize);
        if (!isFinite(numeric) && card.canvasItem && card.canvasItem._canvasStateBridgeRef)
            numeric = Number(card.canvasItem._canvasStateBridgeRef.graphics_node_title_icon_pixel_size);
        if (!isFinite(numeric))
            numeric = Number(card.effectiveGraphLabelPixelSize);
        if (!isFinite(numeric))
            numeric = Number(card.graphLabelPixelSize);
        if (!isFinite(numeric))
            numeric = 10;
        return Math.max(8, Math.min(50, Math.round(numeric)));
    }

    GraphNodeHostTheme {
        id: themeState
        host: card
    }

    GraphSharedTypography {
        id: sharedTypographyState
        graphLabelPixelSize: card.effectiveGraphLabelPixelSize
        graphNodeIconPixelSize: card.effectiveNodeTitleIconPixelSize
    }

    GraphNodeHostLayout {
        id: chromeLayout
        host: card
    }

    GraphNodeHostRenderQuality {
        id: renderQualityState
        host: card
    }

    GraphNodeHostSceneAccess {
        id: sceneAccess
        host: card
    }

    GraphNodeHostInteractionState {
        id: interactionState
        host: card
        surfaceLoader: surfaceLoader
        headerLayer: headerLayer
    }

    readonly property var nodePalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.node_palette
        : ({})
    readonly property var portKindPalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.port_kind_palette
        : ({})
    readonly property var selectedNodeLookup: canvasItem && canvasItem.sceneBridge
        ? canvasItem.sceneBridge.selected_node_lookup
        : ({})
    readonly property var failedNodeLookup: canvasItem ? canvasItem.failedNodeLookup : ({})
    readonly property var runningNodeLookup: canvasItem ? canvasItem.runningNodeLookup : ({})
    readonly property var completedNodeLookup: canvasItem ? canvasItem.completedNodeLookup : ({})
    readonly property var runningNodeStartedAtMsLookup: canvasItem ? canvasItem.runningNodeStartedAtMsLookup : ({})
    readonly property var nodeElapsedMsLookup: canvasItem ? canvasItem.nodeElapsedMsLookup : ({})
    readonly property bool isSelected: !!nodeData
        && Boolean(selectedNodeLookup[String(nodeData.node_id || "")])
    readonly property bool isFailedNode: !!nodeData
        && Boolean(failedNodeLookup[String(nodeData.node_id || "")])
    readonly property bool isRunningNode: !!nodeData
        && Boolean(runningNodeLookup[String(nodeData.node_id || "")])
    readonly property bool isCompletedNode: !!nodeData
        && Boolean(completedNodeLookup[String(nodeData.node_id || "")])
    readonly property string executionNodeId: !!nodeData ? String(nodeData.node_id || "") : ""
    readonly property int failurePulseRevision: canvasItem ? Number(canvasItem.failedNodeRevision || 0) : 0
    readonly property int executionPulseRevision: canvasItem ? Number(canvasItem.nodeExecutionRevision || 0) : 0
    readonly property double runningNodeStartedAtMs: {
        var numeric = card._lookupExecutionTimingValue(card.runningNodeStartedAtMsLookup, false);
        return isFinite(numeric) ? numeric : 0.0;
    }
    readonly property bool hasCachedExecutionElapsedMs: isFinite(
        card._lookupExecutionTimingValue(card.nodeElapsedMsLookup, true)
    )
    readonly property double cachedExecutionElapsedMs: {
        var numeric = card._lookupExecutionTimingValue(card.nodeElapsedMsLookup, true);
        return isFinite(numeric) ? numeric : 0.0;
    }
    readonly property bool liveExecutionElapsedVisible: !card.isFailedNode
        && card.isRunningNode
        && card.runningNodeStartedAtMs > 0.0
    readonly property bool cachedExecutionElapsedVisible: !card.isFailedNode
        && !card.isRunningNode
        && card.hasCachedExecutionElapsedMs
    readonly property string surfaceFamily: String(surfaceFamilyOverride || (nodeData ? nodeData.surface_family || "standard" : "standard"))
    readonly property string surfaceVariant: String(surfaceVariantOverride || (nodeData ? nodeData.surface_variant || "" : ""))
    readonly property var renderQuality: renderQualityState.renderQuality
    // Reduced/proxy surface negotiation is only worthwhile when we are reusing
    // a degraded snapshot; viewport pan/zoom already has a separate world-cache path.
    readonly property bool reducedQualityRequested: renderQualityState.reducedQualityRequested
    readonly property string requestedQualityTier: renderQualityState.requestedQualityTier
    readonly property bool proxySurfaceCapable: renderQualityState.proxySurfaceCapable
    readonly property bool proxySurfaceRequested: renderQualityState.proxySurfaceRequested
    readonly property string resolvedQualityTier: renderQualityState.resolvedQualityTier
    readonly property var surfaceQualityContext: renderQualityState.surfaceQualityContext
    readonly property bool isFlowchartSurface: surfaceFamily === "flowchart"
    readonly property bool usesCardinalNeutralFlowHandles: !!nodeData
        && GraphNodeSurfaceMetrics.nodeUsesCardinalNeutralFlowHandles(nodeData)
    readonly property bool isPassiveNode: !!nodeData && String(nodeData.runtime_behavior || "").toLowerCase() === "passive"
    readonly property var passiveStyle: themeState.passiveStyle
    readonly property string _passiveFillOverride: themeState.passiveFillOverride
    readonly property string _passiveBorderOverride: themeState.passiveBorderOverride
    readonly property string _passiveTextOverride: themeState.passiveTextOverride
    readonly property string _passiveAccentOverride: themeState.passiveAccentOverride
    readonly property string _passiveHeaderOverride: themeState.passiveHeaderOverride
    readonly property bool hasPassiveFillOverride: themeState.hasPassiveFillOverride
    readonly property bool hasPassiveBorderOverride: themeState.hasPassiveBorderOverride
    readonly property bool hasPassiveTextOverride: themeState.hasPassiveTextOverride
    readonly property bool hasPassiveAccentOverride: themeState.hasPassiveAccentOverride
    readonly property bool hasPassiveHeaderOverride: themeState.hasPassiveHeaderOverride
    readonly property color themeSurfaceColor: themeState.themeSurfaceColor
    readonly property color themeOutlineColor: themeState.themeOutlineColor
    readonly property color themeSelectedOutlineColor: themeState.themeSelectedOutlineColor
    readonly property color themeHeaderColor: themeState.themeHeaderColor
    readonly property color themeHeaderTextColor: themeState.themeHeaderTextColor
    readonly property color themeScopeBadgeColor: themeState.themeScopeBadgeColor
    readonly property color themeScopeBadgeBorderColor: themeState.themeScopeBadgeBorderColor
    readonly property color themeScopeBadgeTextColor: themeState.themeScopeBadgeTextColor
    readonly property color themeInlineRowColor: themeState.themeInlineRowColor
    readonly property color themeInlineRowBorderColor: themeState.themeInlineRowBorderColor
    readonly property color themeInlineLabelColor: themeState.themeInlineLabelColor
    readonly property color themeInlineInputTextColor: themeState.themeInlineInputTextColor
    readonly property color themeInlineInputBackgroundColor: themeState.themeInlineInputBackgroundColor
    readonly property color themeInlineInputBorderColor: themeState.themeInlineInputBorderColor
    readonly property color themeInlineDrivenTextColor: themeState.themeInlineDrivenTextColor
    readonly property color themePortLabelColor: themeState.themePortLabelColor
    readonly property color flowchartDefaultFillColor: themeState.flowchartDefaultFillColor
    readonly property color flowchartDefaultOutlineColor: themeState.flowchartDefaultOutlineColor
    readonly property color flowchartDefaultSelectedOutlineColor: themeState.flowchartDefaultSelectedOutlineColor
    readonly property color flowchartDefaultTextColor: themeState.flowchartDefaultTextColor
    readonly property color surfaceColor: themeState.surfaceColor
    readonly property color outlineColor: themeState.outlineColor
    readonly property color selectedOutlineColor: themeState.selectedOutlineColor
    readonly property color headerColor: themeState.headerColor
    readonly property color headerTextColor: themeState.headerTextColor
    readonly property color scopeBadgeColor: themeState.scopeBadgeColor
    readonly property color scopeBadgeBorderColor: themeState.scopeBadgeBorderColor
    readonly property color scopeBadgeTextColor: themeState.scopeBadgeTextColor
    readonly property color inlineRowColor: themeState.inlineRowColor
    readonly property color inlineRowBorderColor: themeState.inlineRowBorderColor
    readonly property color inlineLabelColor: themeState.inlineLabelColor
    readonly property color inlineInputTextColor: themeState.inlineInputTextColor
    readonly property color inlineInputBackgroundColor: themeState.inlineInputBackgroundColor
    readonly property color inlineInputBorderColor: themeState.inlineInputBorderColor
    readonly property color inlineDrivenTextColor: themeState.inlineDrivenTextColor
    readonly property color portLabelColor: themeState.portLabelColor
    readonly property color portInteractiveFillColor: themeState.portInteractiveFillColor
    readonly property color portInteractiveBorderColor: themeState.portInteractiveBorderColor
    readonly property color portInteractiveRingFillColor: themeState.portInteractiveRingFillColor
    readonly property color portInteractiveRingBorderColor: themeState.portInteractiveRingBorderColor
    readonly property color flowchartConnectedPortFillColor: themeState.flowchartConnectedPortFillColor
    readonly property color failureOutlineColor: themeState.failureOutlineColor
    readonly property color failureGlowColor: themeState.failureGlowColor
    readonly property color failureBadgeFillColor: themeState.failureBadgeFillColor
    readonly property color failureBadgeBorderColor: themeState.failureBadgeBorderColor
    readonly property color failureBadgeTextColor: themeState.failureBadgeTextColor
    readonly property color runningOutlineColor: themeState.runningOutlineColor
    readonly property color runningGlowColor: themeState.runningGlowColor
    readonly property color completedOutlineColor: themeState.completedOutlineColor
    readonly property color completedGlowColor: themeState.completedGlowColor
    readonly property color runningElapsedFooterColor: themeState.runningElapsedFooterColor
    readonly property color completedElapsedFooterColor: themeState.completedElapsedFooterColor
    readonly property real runningElapsedFooterOpacity: themeState.runningElapsedFooterOpacity
    readonly property real completedElapsedFooterOpacity: themeState.completedElapsedFooterOpacity
    readonly property real flowchartRestPortDiameter: themeState.flowchartRestPortDiameter
    readonly property real flowchartConnectedPortDiameter: themeState.flowchartConnectedPortDiameter
    readonly property real flowchartSelectedPortDiameter: themeState.flowchartSelectedPortDiameter
    readonly property real flowchartInteractivePortDiameter: themeState.flowchartInteractivePortDiameter
    readonly property real flowchartInteractiveRingDiameter: themeState.flowchartInteractiveRingDiameter
    readonly property real passiveBorderWidth: themeState.passiveBorderWidth
    readonly property real passiveCornerRadius: themeState.passiveCornerRadius
    readonly property real passiveFontPixelSize: themeState.passiveFontPixelSize
    readonly property int passiveFontWeight: themeState.passiveFontWeight
    readonly property bool passiveFontBold: themeState.passiveFontBold
    readonly property var graphSharedTypography: sharedTypographyState
    readonly property var surfaceMetrics: GraphNodeSurfaceMetrics.surfaceMetrics(
        nodeData,
        card._liveGeometryActive ? card._liveWidth : (card.nodeData ? card.nodeData.width : undefined),
        card._liveGeometryActive ? card._liveHeight : (card.nodeData ? card.nodeData.height : undefined)
    )
    readonly property bool surfaceInteractionLocked: Boolean(surfaceLoader.blocksHostInteraction)
    readonly property var viewerSurfaceContract: surfaceLoader.viewerSurfaceContract
    readonly property rect viewerBodyRect: surfaceLoader.viewerBodyRect
    readonly property rect viewerProxySurfaceRect: surfaceLoader.viewerProxySurfaceRect
    readonly property rect viewerLiveSurfaceRect: surfaceLoader.viewerLiveSurfaceRect
    readonly property var viewerBridgeBinding: surfaceLoader.viewerBridgeBinding
    readonly property var viewerInteractiveRects: surfaceLoader.viewerInteractiveRects
    readonly property bool isCollapsed: !!nodeData && !!nodeData.collapsed
    readonly property color color: card._useHostChrome ? card.surfaceColor : "transparent"
    readonly property real radius: card._useHostChrome ? card.resolvedCornerRadius : 0

    signal nodeClicked(string nodeId, bool additive)
    signal nodeOpenRequested(string nodeId)
    signal nodeContextRequested(string nodeId, real localX, real localY)
    signal dragOffsetChanged(string nodeId, real dx, real dy)
    signal dragFinished(string nodeId, real finalX, real finalY, bool moved)
    signal dragCanceled(string nodeId)
    signal resizePreviewChanged(string nodeId, real newX, real newY, real newWidth, real newHeight, bool active)
    signal resizeFinished(string nodeId, real newX, real newY, real newWidth, real newHeight)
    signal portClicked(string nodeId, string portKey, string direction, real sceneX, real sceneY)
    signal portDoubleClicked(string nodeId, string portKey, string direction, bool locked)
    signal portDragStarted(
        string nodeId,
        string portKey,
        string direction,
        real sceneX,
        real sceneY,
        real screenX,
        real screenY
    )
    signal portDragMoved(
        string nodeId,
        string portKey,
        string direction,
        real sceneX,
        real sceneY,
        real screenX,
        real screenY,
        bool dragActive
    )
    signal portDragFinished(
        string nodeId,
        string portKey,
        string direction,
        real sceneX,
        real sceneY,
        real screenX,
        real screenY,
        bool dragActive
    )
    signal portDragCanceled(string nodeId, string portKey, string direction)
    signal surfaceControlInteractionStarted(string nodeId)
    signal inlinePropertyCommitted(string nodeId, string key, var value)
    signal portLabelCommitted(string nodeId, string portKey, string label)
    signal portHoverChanged(
        string nodeId,
        string portKey,
        string direction,
        real sceneX,
        real sceneY,
        bool hovered
    )

    property bool _liveGeometryActive: false
    property real _liveX: 0
    property real _liveY: 0
    property real _liveWidth: 0
    property real _liveHeight: 0
    readonly property real _minNodeWidth: Number(surfaceMetrics.min_width)
    readonly property real _minNodeHeight: Number(surfaceMetrics.min_height)
    readonly property real _resizeHandleSize: Number(surfaceMetrics.resize_handle_size)
    readonly property real _resizeHandleHitSize: {
        var size = Number(card._resizeHandleSize);
        if (!isFinite(size) || size <= 0.0)
            return 10.0;
        return Math.max(6.0, Math.min(size, 10.0));
    }

    readonly property real _inlineRowHeight: {
        var numeric = Number(card.graphSharedTypography ? card.graphSharedTypography.inlineRowHeight : NaN);
        return isFinite(numeric) ? numeric : 26;
    }
    readonly property real _inlineTextareaRowHeight: {
        var numeric = Number(card.graphSharedTypography ? card.graphSharedTypography.inlineTextareaRowHeight : NaN);
        return isFinite(numeric) ? numeric : 104;
    }
    readonly property real _inlineRowSpacing: 4
    readonly property var inlineProperties: {
        if (!card.nodeData || !card.nodeData.inline_properties)
            return [];
        return card.nodeData.inline_properties;
    }
    readonly property real inlineBodyHeight: Number(surfaceMetrics.body_height)
    readonly property real _portDragThreshold: 2
    readonly property bool canEnterScope: !!card.nodeData && !!card.nodeData.can_enter_scope
    readonly property bool sharedHeaderTitleEditable: !!card.nodeData
    readonly property bool flowchartTitleEditable: card.isFlowchartSurface && card.sharedHeaderTitleEditable
    readonly property bool _useHostChrome: chromeLayout.useHostChrome
    readonly property bool _showAccentBar: chromeLayout.showAccentBar
    readonly property bool _showHeaderBackground: chromeLayout.showHeaderBackground
    readonly property real _titleTop: chromeLayout.titleTop
    readonly property real _titleHeight: chromeLayout.titleHeight
    readonly property real _titleLeftMargin: chromeLayout.titleLeftMargin
    readonly property real _titleRightMargin: chromeLayout.titleRightMargin
    readonly property bool _titleCentered: chromeLayout.titleCentered
    readonly property bool _portLabelsSuppressedBySurfaceRule: chromeLayout.portLabelsSuppressedBySurfaceRule
    readonly property bool _standardExpandedNonPassiveNode: chromeLayout.standardExpandedNonPassiveNode
    // Consume the scene-owned width contract for visible standard-node labels.
    readonly property real _standardLeftLabelMetricWidth: chromeLayout.standardLeftLabelMetricWidth
    readonly property real _standardRightLabelMetricWidth: chromeLayout.standardRightLabelMetricWidth
    readonly property real _standardPortGutterMetric: chromeLayout.standardPortGutterMetric
    readonly property real _standardCenterGapMetric: chromeLayout.standardCenterGapMetric
    readonly property real _standardPortLabelMinMetricWidth: chromeLayout.standardPortLabelMinMetricWidth
    readonly property bool _standardPortLabelMetricsReady: chromeLayout.standardPortLabelMetricsReady
    readonly property bool _usesStandardPortLabelColumns: chromeLayout.usesStandardPortLabelColumns
    readonly property int _standardVisibleLabelColumnCount: chromeLayout.standardVisibleLabelColumnCount
    readonly property real _standardExtraLabelWidthPerColumn: chromeLayout.standardExtraLabelWidthPerColumn
    readonly property real _standardLeftLabelWidth: chromeLayout.standardLeftLabelWidth
    readonly property real _standardRightLabelWidth: chromeLayout.standardRightLabelWidth
    readonly property real _standardPortGutter: chromeLayout.standardPortGutter
    readonly property real _standardCenterGap: chromeLayout.standardCenterGap
    readonly property real _portLabelGap: chromeLayout.portLabelGap
    readonly property real _portLabelMaxWidth: chromeLayout.portLabelMaxWidth
    readonly property bool _tooltipOnlyPortLabelsActive: chromeLayout.tooltipOnlyPortLabelsActive
    readonly property bool _portLabelsVisible: chromeLayout.portLabelsVisible
    readonly property bool _surfaceOwnsShadow: chromeLayout.surfaceOwnsShadow
    readonly property bool _backgroundShadowVisible: chromeLayout.backgroundShadowVisible
    readonly property bool _surfaceShadowVisible: chromeLayout.surfaceShadowVisible
    readonly property bool _shadowVisible: chromeLayout.shadowVisible
    readonly property bool effectiveTextureCacheActive: chromeLayout.effectiveTextureCacheActive
    readonly property int nodeTextRenderType: chromeLayout.nodeTextRenderType

    readonly property var inputPorts: {
        return GraphNodeSurfaceMetrics.visiblePortsForDirection(card.nodeData, "in");
    }
    readonly property var outputPorts: {
        return GraphNodeSurfaceMetrics.visiblePortsForDirection(card.nodeData, "out");
    }
    readonly property real resolvedBorderWidth: themeState.resolvedBorderWidth
    readonly property real resolvedCornerRadius: themeState.resolvedCornerRadius
    readonly property bool chromeCacheActive: chromeLayout.chromeCacheActive
    readonly property bool shadowCacheActive: chromeLayout.shadowCacheActive
    readonly property bool surfaceShadowCacheActive: chromeLayout.surfaceShadowCacheActive
    readonly property bool chromeShadowCacheActive: chromeLayout.chromeShadowCacheActive
    readonly property string chromeShadowCacheKey: [
        chromeLayout.chromeShadowCacheKey,
        card.isFailedNode ? "failed" : (card.isRunningNode ? "running" : (card.isCompletedNode ? "completed" : "idle")),
        String(card.failureOutlineColor),
        String(card.runningOutlineColor),
        String(card.completedOutlineColor)
    ].join("|")
    readonly property string surfaceShadowCacheKey: chromeLayout.surfaceShadowCacheKey

    function localPortPoint(direction, rowIndex) {
        return sceneAccess.localPortPoint(direction, rowIndex);
    }

    function portScenePos(direction, rowIndex) {
        return sceneAccess.portScenePos(direction, rowIndex);
    }

    function portLabelWidth(labelImplicitWidth, availableWidth) {
        var implicitValue = Number(labelImplicitWidth);
        if (!isFinite(implicitValue) || implicitValue < 0.0)
            implicitValue = 0.0;
        var maxWidth = Math.max(0.0, Number(card._portLabelMaxWidth));
        var clampedAvailable = Math.max(0.0, Number(availableWidth));
        return Math.max(0.0, Math.min(implicitValue, maxWidth, clampedAvailable));
    }

    function basePortColor(portKind) {
        var palette = card.portKindPalette || {};
        if (portKind === "flow")
            return card.usesCardinalNeutralFlowHandles
                ? Qt.alpha(card.outlineColor, 0.72)
                : (card.isPassiveNode ? card.scopeBadgeColor : "#60CDFF");
        if (portKind === "exec")
            return palette.exec || "#67D487";
        if (portKind === "completed")
            return palette.completed || "#E4CE7D";
        if (portKind === "failed")
            return palette.failed || "#D94F4F";
        return palette.data || "#7AA8FF";
    }

    function isHoveredPort(direction, portKey) {
        var hovered = !!card.hoveredPort
            && card.hoveredPort.node_id === card.nodeData.node_id
            && card.hoveredPort.port_key === portKey
            && card.hoveredPort.direction === direction;
        if (hovered)
            return true;
        return !!card.previewPort
            && card.previewPort.node_id === card.nodeData.node_id
            && card.previewPort.port_key === portKey
            && card.previewPort.direction === direction;
    }

    function isConnectedPort(portData) {
        return !!portData && !!portData.connected;
    }

    function isPendingPort(direction, portKey) {
        return !!card.nodeData
            && !!card.pendingPort
            && card.pendingPort.node_id === card.nodeData.node_id
            && card.pendingPort.port_key === portKey
            && card.pendingPort.direction === direction;
    }

    function isDragSourcePort(direction, portKey) {
        return !!card.nodeData
            && !!card.dragSourcePort
            && card.dragSourcePort.node_id === card.nodeData.node_id
            && card.dragSourcePort.port_key === portKey
            && card.dragSourcePort.direction === direction;
    }

    function inlineEditorText(propertyData) {
        if (!propertyData)
            return "";
        var value = propertyData.value;
        if (value === undefined || value === null)
            return "";
        return String(value);
    }

    function browseNodePropertyPath(key, currentPath) {
        return sceneAccess.browseNodePropertyPath(key, currentPath);
    }

    function pickNodePropertyColor(key, currentValue) {
        return sceneAccess.pickNodePropertyColor(key, currentValue);
    }

    function _styleString(value) {
        if (value === undefined || value === null)
            return "";
        return String(value).trim();
    }

    function _styleNumber(value, fallback, allowZero) {
        var numeric = Number(value);
        if (!isFinite(numeric))
            return fallback;
        if (allowZero ? numeric < 0.0 : numeric <= 0.0)
            return fallback;
        return numeric;
    }

    function _normalizedRenderQuality(renderQualityLike) {
        return renderQualityState.normalizedRenderQuality(renderQualityLike);
    }

    function _normalizedQualityTierList(value) {
        return renderQualityState.normalizedQualityTierList(value);
    }

    function _supportsRenderQualityTier(tier) {
        return renderQualityState.supportsRenderQualityTier(tier);
    }

    function _pointerInCanvas(mouseArea, mouse) {
        return interactionState.pointerInCanvas(mouseArea, mouse);
    }

    function _isResizeHandlePoint(localX, localY) {
        return interactionState.isResizeHandlePoint(localX, localY);
    }

    function _pointInRect(localX, localY, rectLike) {
        return interactionState.pointInRect(localX, localY, rectLike);
    }

    function _pointInEmbeddedInteractiveRect(localX, localY) {
        return interactionState.pointInEmbeddedInteractiveRect(localX, localY);
    }

    function _surfaceClaimsBodyInteractionAt(localX, localY) {
        return interactionState.surfaceClaimsBodyInteractionAt(localX, localY);
    }

    function requestInlineTitleEditAt(localX, localY) {
        return interactionState.requestInlineTitleEditAt(localX, localY);
    }

    function requestScopeOpenAt(localX, localY) {
        return interactionState.requestScopeOpenAt(localX, localY);
    }

    function commitInlineTitleEditAt(localX, localY) {
        return interactionState.commitInlineTitleEditAt(localX, localY);
    }

    function currentViewportZoom() {
        return sceneAccess.currentViewportZoom();
    }

    function _normalizedSceneRectPayload(rectLike) {
        return sceneAccess.normalizedSceneRectPayload(rectLike);
    }

    function _nodeSceneRect() {
        return sceneAccess.nodeSceneRect();
    }

    function _sceneRectsIntersect(firstRectLike, secondRectLike) {
        return sceneAccess.sceneRectsIntersect(firstRectLike, secondRectLike);
    }

    function _lookupExecutionTimingValue(lookupLike, allowZero) {
        if (!card.executionNodeId.length)
            return NaN;
        var lookup = lookupLike || {};
        var value = lookup[card.executionNodeId];
        if (value === undefined || value === null)
            return NaN;
        var numeric = Number(value);
        if (!isFinite(numeric))
            return NaN;
        if (allowZero ? numeric < 0.0 : numeric <= 0.0)
            return NaN;
        return numeric;
    }

    function formatExecutionElapsed(elapsedMilliseconds) {
        var elapsedSeconds = Math.max(0.0, Number(elapsedMilliseconds) / 1000.0);
        if (!isFinite(elapsedSeconds))
            elapsedSeconds = 0.0;
        if (elapsedSeconds < 60.0)
            return elapsedSeconds.toFixed(1) + "s";
        var minutes = Math.floor(elapsedSeconds / 60.0);
        var seconds = Math.floor(elapsedSeconds % 60.0);
        return minutes + "m " + (seconds < 10 ? "0" : "") + seconds + "s";
    }

    HoverHandler {
        id: cardHoverHandler
    }

    readonly property bool _hostHoverActive: cardHoverHandler.hovered || hostGestureLayer.containsMouse
    readonly property bool _resizeHandleContainsMouse: topLeftResizeHandle.containsMouse
        || topRightResizeHandle.containsMouse
        || bottomLeftResizeHandle.containsMouse
        || bottomRightResizeHandle.containsMouse
    readonly property bool _resizeInteractionActive: topLeftResizeHandle.dragActive
        || topRightResizeHandle.dragActive
        || bottomLeftResizeHandle.dragActive
        || bottomRightResizeHandle.dragActive
    readonly property bool _hoveredPortOnNode: !!card.nodeData
        && !!card.hoveredPort
        && card.hoveredPort.node_id === card.nodeData.node_id
    readonly property bool _previewPortOnNode: !!card.nodeData
        && !!card.previewPort
        && card.previewPort.node_id === card.nodeData.node_id
    readonly property bool _pendingPortOnNode: !!card.nodeData
        && !!card.pendingPort
        && card.pendingPort.node_id === card.nodeData.node_id
    readonly property bool _dragSourcePortOnNode: !!card.nodeData
        && !!card.dragSourcePort
        && card.dragSourcePort.node_id === card.nodeData.node_id
    readonly property bool _contextTargetActive: !!card.nodeData
        && String(card.contextTargetNodeId || "") === String(card.nodeData.node_id || "")
    readonly property bool _dragPreviewActive: Math.abs(Number(card.liveDragDx)) >= 0.01
        || Math.abs(Number(card.liveDragDy)) >= 0.01
    readonly property bool hoverActive: card._hostHoverActive
        || card._resizeHandleContainsMouse
        || card._resizeInteractionActive
    readonly property bool _forceRenderActive: card.isSelected
        || card.isFailedNode
        || card.isRunningNode
        || card.isCompletedNode
        || card.hoverActive
        || card._hoveredPortOnNode
        || card._previewPortOnNode
        || card._pendingPortOnNode
        || card._dragSourcePortOnNode
        || card._contextTargetActive
        || hostGestureLayer.dragActive
        || card._dragPreviewActive
        || card._liveGeometryActive
        || card._resizeInteractionActive
    readonly property bool renderActive: card._forceRenderActive
        || card._sceneRectsIntersect(card._nodeSceneRect(), card.renderActivationSceneRectPayload)
    readonly property bool _resizeHandlesVisible: !!card.nodeData
        && !card.isCollapsed
        && !card.surfaceInteractionLocked
        && (card._hostHoverActive || card._resizeInteractionActive)

    // Reuse a cached node texture during viewport motion and the max-performance degraded window.
    layer.enabled: card.effectiveTextureCacheActive
    layer.smooth: card.effectiveTextureCacheActive
    layer.mipmap: card.effectiveTextureCacheActive

    z: card.isFailedNode ? 32 : (card.isRunningNode ? 31 : (card.isSelected ? 30 : (card.isCompletedNode ? 29 : 20)))
    x: (card._liveGeometryActive ? card._liveX : (card.nodeData ? card.nodeData.x : 0.0)) + card.worldOffset
    y: (card._liveGeometryActive ? card._liveY : (card.nodeData ? card.nodeData.y : 0.0)) + card.worldOffset
    transform: Translate {
        x: hostGestureLayer.dragActive ? 0 : card.liveDragDx
        y: hostGestureLayer.dragActive ? 0 : card.liveDragDy
    }
    width: card._liveGeometryActive ? card._liveWidth : (card.nodeData ? card.nodeData.width : Number(surfaceMetrics.default_width))
    height: card._liveGeometryActive ? card._liveHeight : (card.nodeData ? card.nodeData.height : Number(surfaceMetrics.default_height))

    GraphNodeChromeBackground {
        anchors.fill: parent
        host: card
    }

    Text {
        id: elapsedTimerLabel
        objectName: "graphNodeElapsedTimer"
        visible: liveElapsedActive || cachedElapsedActive
        anchors.top: parent.bottom
        anchors.topMargin: 4
        anchors.horizontalCenter: parent.horizontalCenter
        z: 4
        font.pixelSize: card.graphSharedTypography ? card.graphSharedTypography.elapsedFooterPixelSize : 10
        font.bold: liveElapsedActive
        color: liveElapsedActive ? card.runningElapsedFooterColor : card.completedElapsedFooterColor
        opacity: liveElapsedActive ? card.runningElapsedFooterOpacity : card.completedElapsedFooterOpacity
        renderType: card.nodeTextRenderType
        text: card.formatExecutionElapsed(liveElapsedActive ? elapsedMilliseconds : cachedElapsedMilliseconds)

        property bool liveElapsedActive: card.liveExecutionElapsedVisible
        property bool cachedElapsedActive: card.cachedExecutionElapsedVisible
        property double elapsedMilliseconds: 0.0
        property double startedAtMs: card.runningNodeStartedAtMs
        property double cachedElapsedMilliseconds: card.cachedExecutionElapsedMs

        function _updateElapsed() {
            if (!liveElapsedActive || startedAtMs <= 0.0) {
                elapsedMilliseconds = 0.0;
                return;
            }
            elapsedMilliseconds = Math.max(0.0, Date.now() - startedAtMs);
        }

        function _syncElapsedState() {
            if (!liveElapsedActive) {
                elapsedMilliseconds = 0.0;
                return;
            }
            _updateElapsed();
        }

        Timer {
            id: elapsedTimerTicker
            interval: 100
            repeat: true
            running: elapsedTimerLabel.liveElapsedActive
            onTriggered: elapsedTimerLabel._updateElapsed()
        }

        onLiveElapsedActiveChanged: _syncElapsedState()
        onStartedAtMsChanged: _syncElapsedState()
        Component.onCompleted: _syncElapsedState()
    }

    // Keep body interactions below the loaded surface so local surface controls can own pointer input.
    GraphNodeHostGestureLayer {
        id: hostGestureLayer
        anchors.fill: parent
        host: card
    }

    Item {
        id: surfaceLayer
        z: 2
        anchors.fill: parent
        visible: card.nodeData ? !card.nodeData.collapsed : false

        GraphNodeSurfaceLoader {
            id: surfaceLoader
            anchors.fill: parent
            host: card
            nodeData: card.nodeData
            surfaceFamily: card.surfaceFamily
            surfaceVariant: card.surfaceVariant
        }
    }

    GraphNodeHeaderLayer {
        id: headerLayer
        anchors.fill: parent
        host: card
    }

    GraphNodePortsLayer {
        anchors.fill: parent
        host: card
    }

    GraphNodeResizeHandle {
        id: topLeftResizeHandle
        host: card
        cornerRole: "topLeft"
    }

    GraphNodeResizeHandle {
        id: topRightResizeHandle
        host: card
        cornerRole: "topRight"
    }

    GraphNodeResizeHandle {
        id: bottomLeftResizeHandle
        host: card
        cornerRole: "bottomLeft"
    }

    GraphNodeResizeHandle {
        id: bottomRightResizeHandle
        host: card
        cornerRole: "bottomRight"
    }
}
