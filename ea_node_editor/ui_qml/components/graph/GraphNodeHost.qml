import QtQuick 2.15
import "GraphNodeSurfaceMetrics.js" as GraphNodeSurfaceMetrics
import "GraphNodeHostHitTesting.js" as GraphNodeHostHitTesting

Item {
    id: card
    objectName: "graphNodeCard"
    property var nodeData: null
    property real worldOffset: 0
    property Item canvasItem: null
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
    property real zoom: 1.0
    property bool viewportInteractionCacheActive: false
    property string surfaceFamilyOverride: ""
    property string surfaceVariantOverride: ""
    readonly property var nodePalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.node_palette
        : ({})
    readonly property var portKindPalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.port_kind_palette
        : ({})
    readonly property var selectedNodeLookup: canvasItem && canvasItem.sceneBridge
        ? canvasItem.sceneBridge.selected_node_lookup
        : ({})
    readonly property bool isSelected: !!nodeData
        && Boolean(selectedNodeLookup[String(nodeData.node_id || "")])
    readonly property string surfaceFamily: String(surfaceFamilyOverride || (nodeData ? nodeData.surface_family || "standard" : "standard"))
    readonly property string surfaceVariant: String(surfaceVariantOverride || (nodeData ? nodeData.surface_variant || "" : ""))
    readonly property bool isFlowchartSurface: surfaceFamily === "flowchart"
    readonly property bool isPassiveNode: !!nodeData && String(nodeData.runtime_behavior || "").toLowerCase() === "passive"
    readonly property var passiveStyle: isPassiveNode && nodeData && nodeData.visual_style ? nodeData.visual_style : ({})
    readonly property string _passiveFillOverride: card._styleString(passiveStyle.fill_color)
    readonly property string _passiveBorderOverride: card._styleString(passiveStyle.border_color)
    readonly property string _passiveTextOverride: card._styleString(passiveStyle.text_color)
    readonly property string _passiveAccentOverride: card._styleString(passiveStyle.accent_color)
    readonly property string _passiveHeaderOverride: card._styleString(passiveStyle.header_color)
    readonly property bool hasPassiveFillOverride: isPassiveNode && _passiveFillOverride.length > 0
    readonly property bool hasPassiveBorderOverride: isPassiveNode && _passiveBorderOverride.length > 0
    readonly property bool hasPassiveTextOverride: isPassiveNode && _passiveTextOverride.length > 0
    readonly property bool hasPassiveAccentOverride: isPassiveNode && _passiveAccentOverride.length > 0
    readonly property bool hasPassiveHeaderOverride: isPassiveNode && _passiveHeaderOverride.length > 0
    readonly property color themeSurfaceColor: nodePalette.card_bg || "#1b1d22"
    readonly property color themeOutlineColor: nodePalette.card_border || "#3a3d45"
    readonly property color themeSelectedOutlineColor: nodePalette.card_selected_border || "#60CDFF"
    readonly property color themeHeaderColor: nodePalette.header_bg || "#2a2b30"
    readonly property color themeHeaderTextColor: nodePalette.header_fg || "#f0f4fb"
    readonly property color themeScopeBadgeColor: nodePalette.scope_badge_bg || "#1D8CE0"
    readonly property color themeScopeBadgeBorderColor: nodePalette.scope_badge_border || "#60CDFF"
    readonly property color themeScopeBadgeTextColor: nodePalette.scope_badge_fg || "#f2f4f8"
    readonly property color themeInlineRowColor: nodePalette.inline_row_bg || "#24262c"
    readonly property color themeInlineRowBorderColor: nodePalette.inline_row_border || "#4a4f5a"
    readonly property color themeInlineLabelColor: nodePalette.inline_label_fg || "#d0d5de"
    readonly property color themeInlineInputTextColor: nodePalette.inline_input_fg || "#f0f2f5"
    readonly property color themeInlineInputBackgroundColor: nodePalette.inline_input_bg || "#22242a"
    readonly property color themeInlineInputBorderColor: nodePalette.inline_input_border || "#4a4f5a"
    readonly property color themeInlineDrivenTextColor: nodePalette.inline_driven_fg || "#bdc5d3"
    readonly property color themePortLabelColor: nodePalette.port_label_fg || "#d0d5de"
    readonly property color flowchartDefaultFillColor: "#F5FAFD"
    readonly property color flowchartDefaultOutlineColor: "#61798B"
    readonly property color flowchartDefaultSelectedOutlineColor: "#2C85BF"
    readonly property color flowchartDefaultTextColor: "#173247"
    readonly property color surfaceColor: isPassiveNode
        ? (_passiveFillOverride || (isFlowchartSurface ? flowchartDefaultFillColor : themeSurfaceColor))
        : themeSurfaceColor
    readonly property color outlineColor: isPassiveNode
        ? (_passiveBorderOverride || (isFlowchartSurface ? flowchartDefaultOutlineColor : themeOutlineColor))
        : themeOutlineColor
    readonly property color selectedOutlineColor: isPassiveNode
        ? (isFlowchartSurface
            ? (hasPassiveBorderOverride ? Qt.lighter(outlineColor, 1.18) : flowchartDefaultSelectedOutlineColor)
            : Qt.lighter(outlineColor, 1.25))
        : themeSelectedOutlineColor
    readonly property color headerColor: isPassiveNode
        ? (_passiveHeaderOverride || (isFlowchartSurface ? surfaceColor : themeHeaderColor))
        : themeHeaderColor
    readonly property color headerTextColor: isPassiveNode
        ? (_passiveTextOverride || (isFlowchartSurface ? flowchartDefaultTextColor : themeHeaderTextColor))
        : themeHeaderTextColor
    readonly property color scopeBadgeColor: isPassiveNode
        ? (_passiveAccentOverride || (isFlowchartSurface ? selectedOutlineColor : themeScopeBadgeColor))
        : themeScopeBadgeColor
    readonly property color scopeBadgeBorderColor: isPassiveNode
        ? Qt.lighter(scopeBadgeColor, 1.16)
        : themeScopeBadgeBorderColor
    readonly property color scopeBadgeTextColor: isPassiveNode ? "#f2f4f8" : themeScopeBadgeTextColor
    readonly property color inlineRowColor: isPassiveNode ? Qt.darker(surfaceColor, 1.04) : themeInlineRowColor
    readonly property color inlineRowBorderColor: isPassiveNode ? Qt.alpha(outlineColor, 0.85) : themeInlineRowBorderColor
    readonly property color inlineLabelColor: isPassiveNode ? Qt.alpha(headerTextColor, 0.82) : themeInlineLabelColor
    readonly property color inlineInputTextColor: isPassiveNode ? headerTextColor : themeInlineInputTextColor
    readonly property color inlineInputBackgroundColor: isPassiveNode
        ? Qt.darker(surfaceColor, 1.08)
        : themeInlineInputBackgroundColor
    readonly property color inlineInputBorderColor: isPassiveNode ? Qt.alpha(outlineColor, 0.9) : themeInlineInputBorderColor
    readonly property color inlineDrivenTextColor: isPassiveNode ? Qt.alpha(headerTextColor, 0.72) : themeInlineDrivenTextColor
    readonly property color portLabelColor: isPassiveNode
        ? Qt.alpha(headerTextColor, isFlowchartSurface ? 0.74 : 0.84)
        : themePortLabelColor
    readonly property color portInteractiveFillColor: isFlowchartSurface
        ? Qt.alpha(selectedOutlineColor, 0.18)
        : (nodePalette.port_interactive_fill || "#FFDA6B")
    readonly property color portInteractiveBorderColor: isFlowchartSurface
        ? selectedOutlineColor
        : (nodePalette.port_interactive_border || "#FFE48B")
    readonly property color portInteractiveRingFillColor: isFlowchartSurface
        ? Qt.alpha(selectedOutlineColor, 0.1)
        : (nodePalette.port_interactive_ring_fill || "#44FFC857")
    readonly property color portInteractiveRingBorderColor: isFlowchartSurface
        ? Qt.alpha(selectedOutlineColor, 0.38)
        : (nodePalette.port_interactive_ring_border || "#66FFE29A")
    readonly property color flowchartConnectedPortFillColor: Qt.alpha(outlineColor, 0.18)
    readonly property real flowchartRestPortDiameter: 6.0
    readonly property real flowchartConnectedPortDiameter: 7.0
    readonly property real flowchartSelectedPortDiameter: 8.0
    readonly property real flowchartInteractivePortDiameter: 11.0
    readonly property real flowchartInteractiveRingDiameter: 15.0
    readonly property real passiveBorderWidth: card._styleNumber(passiveStyle.border_width, 1.0, false)
    readonly property real passiveCornerRadius: card._styleNumber(passiveStyle.corner_radius, 6.0, true)
    readonly property real passiveFontPixelSize: card._styleNumber(passiveStyle.font_size, 12.0, false)
    readonly property bool passiveFontBold: card._styleString(passiveStyle.font_weight).toLowerCase() === "bold"
    readonly property var surfaceMetrics: GraphNodeSurfaceMetrics.surfaceMetrics(nodeData)
    readonly property bool surfaceInteractionLocked: Boolean(surfaceLoader.blocksHostInteraction)
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

    readonly property real _inlineRowHeight: 26
    readonly property real _inlineRowSpacing: 4
    readonly property var inlineProperties: {
        if (!card.nodeData || !card.nodeData.inline_properties)
            return [];
        return card.nodeData.inline_properties;
    }
    readonly property real inlineBodyHeight: Number(surfaceMetrics.body_height)
    readonly property real _portDragThreshold: 2
    readonly property bool canEnterScope: !!card.nodeData && !!card.nodeData.can_enter_scope
    readonly property bool _useHostChrome: card.isCollapsed || Boolean(surfaceMetrics.use_host_chrome)
    readonly property bool _showAccentBar: card.isCollapsed || Boolean(surfaceMetrics.show_accent_bar)
    readonly property bool _showHeaderBackground: card.isCollapsed
        || Boolean(surfaceMetrics.show_header_background)
        || (card.isPassiveNode && card._useHostChrome && card.hasPassiveHeaderOverride)
    readonly property real _titleTop: card.isCollapsed ? 4.0 : Number(surfaceMetrics.title_top)
    readonly property real _titleHeight: card.isCollapsed ? 24.0 : Number(surfaceMetrics.title_height)
    readonly property real _titleLeftMargin: card.isCollapsed ? 10.0 : Number(surfaceMetrics.title_left_margin)
    readonly property real _titleRightMargin: card.isCollapsed ? 10.0 : Number(surfaceMetrics.title_right_margin)
    readonly property bool _titleCentered: !card.isCollapsed && Boolean(surfaceMetrics.title_centered)
    readonly property real _portLabelGap: 6.0
    readonly property real _portLabelMaxWidth: Math.max(40.0, card.width * 0.46)
    readonly property bool _portLabelsVisible: !card.isFlowchartSurface
    readonly property bool _suppressShadow: card.isFlowchartSurface && !card.isCollapsed
    readonly property bool _shadowVisible: card.showShadow
        && !card._suppressShadow
        && card._useHostChrome
    readonly property int nodeTextRenderType: Text.CurveRendering

    readonly property var inputPorts: {
        if (!card.nodeData || !card.nodeData.ports)
            return [];
        return card.nodeData.ports.filter(function(port) { return port.direction === "in"; });
    }
    readonly property var outputPorts: {
        if (!card.nodeData || !card.nodeData.ports)
            return [];
        return card.nodeData.ports.filter(function(port) { return port.direction === "out"; });
    }
    readonly property real resolvedBorderWidth: card.isPassiveNode
        ? (card.isSelected ? Math.max(2.0, card.passiveBorderWidth) : card.passiveBorderWidth)
        : (card.isSelected ? 2.0 : 1.0)
    readonly property real resolvedCornerRadius: card.isPassiveNode ? card.passiveCornerRadius : 6.0

    function localPortPoint(direction, rowIndex) {
        if (!card.nodeData)
            return {"x": 0.0, "y": 0.0};
        var widthValue = Number(card.width);
        if (!isFinite(widthValue) || widthValue <= 0.0)
            widthValue = Number(card.nodeData.width);
        if (!isFinite(widthValue) || widthValue <= 0.0)
            widthValue = Number(surfaceMetrics.default_width);
        var heightValue = Number(card.height);
        if (!isFinite(heightValue) || heightValue <= 0.0)
            heightValue = Number(card.nodeData.height);
        if (!isFinite(heightValue) || heightValue <= 0.0)
            heightValue = Number(surfaceMetrics.default_height);
        return GraphNodeSurfaceMetrics.localPortPoint(card.nodeData, direction, rowIndex, widthValue, heightValue);
    }

    function portScenePos(direction, rowIndex) {
        if (!card.nodeData)
            return {"x": 0.0, "y": 0.0};
        var point = card.localPortPoint(direction, rowIndex);
        var nodeX = card._liveGeometryActive ? Number(card._liveX) : Number(card.nodeData.x);
        var nodeY = card._liveGeometryActive ? Number(card._liveY) : Number(card.nodeData.y);
        return {
            "x": nodeX + point.x,
            "y": nodeY + point.y
        };
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
            return card.isFlowchartSurface ? Qt.alpha(card.outlineColor, 0.72) : (card.isPassiveNode ? card.scopeBadgeColor : "#60CDFF");
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
        if (!card.nodeData || !card.canvasItem || !card.canvasItem.browseNodePropertyPath)
            return "";
        return String(card.canvasItem.browseNodePropertyPath(card.nodeData.node_id, key, currentPath) || "");
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

    function _pointerInCanvas(mouseArea, mouse) {
        if (!card.canvasItem)
            return {"x": 0.0, "y": 0.0};
        return mouseArea.mapToItem(card.canvasItem, mouse.x, mouse.y);
    }

    function _isResizeHandlePoint(localX, localY) {
        return GraphNodeHostHitTesting.resizeHandleContainsPoint(
            localX,
            localY,
            card.width,
            card.height,
            card._resizeHandleSize,
            card.nodeData ? Boolean(card.nodeData.collapsed) : true
        );
    }

    function _pointInRect(localX, localY, rectLike) {
        return GraphNodeHostHitTesting.pointInRect(localX, localY, rectLike);
    }

    function _pointInEmbeddedInteractiveRect(localX, localY) {
        return GraphNodeHostHitTesting.pointInAnyRect(localX, localY, surfaceLoader.embeddedInteractiveRects);
    }

    function _surfaceClaimsBodyInteractionAt(localX, localY) {
        return GraphNodeHostHitTesting.claimsBodyInteraction(localX, localY, surfaceLoader.embeddedInteractiveRects);
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
    readonly property bool hoverActive: card._hostHoverActive
        || card._resizeHandleContainsMouse
        || card._resizeInteractionActive
    readonly property bool _resizeHandlesVisible: !!card.nodeData
        && !card.isCollapsed
        && !card.surfaceInteractionLocked
        && (card._hostHoverActive || card._resizeInteractionActive)

    // Cache each node as a texture only while the viewport is moving so pan/zoom can reuse node content.
    layer.enabled: card.viewportInteractionCacheActive
    layer.smooth: card.viewportInteractionCacheActive
    layer.mipmap: card.viewportInteractionCacheActive

    z: card.isSelected ? 30 : 20
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
