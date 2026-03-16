import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Effects
import "GraphNodeSurfaceMetrics.js" as GraphNodeSurfaceMetrics

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
    property bool renderQualitySimplified: false
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
    signal resizePreviewChanged(string nodeId, real newWidth, real newHeight, bool active)
    signal resizeFinished(string nodeId, real newWidth, real newHeight)
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
        && !card.renderQualitySimplified
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
        return {
            "x": Number(card.nodeData.x) + point.x,
            "y": Number(card.nodeData.y) + point.y
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
        if (!card.nodeData || card.nodeData.collapsed)
            return false;
        return localX >= card.width - card._resizeHandleSize && localY >= card.height - card._resizeHandleSize;
    }

    function _pointInRect(localX, localY, rectLike) {
        if (!rectLike)
            return false;
        var rectX = Number(rectLike.x || 0);
        var rectY = Number(rectLike.y || 0);
        var rectWidth = Number(rectLike.width || 0);
        var rectHeight = Number(rectLike.height || 0);
        return rectWidth > 0
            && rectHeight > 0
            && localX >= rectX
            && localX <= rectX + rectWidth
            && localY >= rectY
            && localY <= rectY + rectHeight;
    }

    function _pointInEmbeddedInteractiveRect(localX, localY) {
        var rects = surfaceLoader.embeddedInteractiveRects;
        if (!rects || rects.length <= 0)
            return false;
        for (var index = 0; index < rects.length; index++) {
            if (card._pointInRect(localX, localY, rects[index]))
                return true;
        }
        return false;
    }

    function _pointInHoverAction(localX, localY) {
        return card._pointInRect(localX, localY, surfaceLoader.hoverActionHitRect);
    }

    function _surfaceClaimsBodyInteractionAt(localX, localY) {
        return card._pointInEmbeddedInteractiveRect(localX, localY)
            || card._pointInHoverAction(localX, localY);
    }

    HoverHandler {
        id: cardHoverHandler
    }

    readonly property bool hoverActive: cardHoverHandler.hovered || nodeDragArea.containsMouse || resizeDragArea.containsMouse
    readonly property bool surfaceHoverActionHovered: surfaceHoverActionArea.visible && Boolean(surfaceHoverActionArea.hovered)

    z: card.isSelected ? 30 : 20
    x: (card.nodeData ? card.nodeData.x : 0.0) + card.worldOffset
    y: (card.nodeData ? card.nodeData.y : 0.0) + card.worldOffset
    transform: Translate {
        x: nodeDragArea.drag.active ? 0 : card.liveDragDx
        y: nodeDragArea.drag.active ? 0 : card.liveDragDy
    }
    width: card._liveWidth > 0 ? card._liveWidth : (card.nodeData ? card.nodeData.width : Number(surfaceMetrics.default_width))
    height: card._liveHeight > 0 ? card._liveHeight : (card.nodeData ? card.nodeData.height : Number(surfaceMetrics.default_height))

    RectangularShadow {
        id: cardShadow
        objectName: "graphNodeShadow"
        visible: card._shadowVisible
        anchors.fill: cardChrome
        z: 0
        offset.y: card.shadowOffset
        blur: Math.max(0.0, Math.min(1.0, card.shadowSoftness / 100.0))
        spread: Math.max(0.0, Math.min(1.0, card.shadowStrength / 150.0))
        radius: card.resolvedCornerRadius
        color: Qt.rgba(0, 0, 0, card.shadowStrength / 100.0)
        cached: true
    }

    Rectangle {
        id: cardChrome
        objectName: "graphNodeChrome"
        anchors.fill: parent
        z: 1
        visible: card._useHostChrome
        color: card.surfaceColor
        border.width: card.resolvedBorderWidth
        border.color: card.isSelected ? card.selectedOutlineColor : card.outlineColor
        radius: card.resolvedCornerRadius
    }

    // Keep body interactions below the loaded surface so local surface controls can own pointer input.
    MouseArea {
        id: nodeDragArea
        objectName: "graphNodeDragArea"
        z: 1.5
        anchors.fill: parent
        enabled: !card.surfaceInteractionLocked
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true
        cursorShape: card.surfaceInteractionLocked
            ? Qt.ArrowCursor
            : (drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
        drag.target: enabled ? card : null
        drag.axis: Drag.XAndYAxis
        propagateComposedEvents: true
        property bool dragMoved: false

        onPressed: {
            if (card._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y)) {
                mouse.accepted = false;
                return;
            }
            if (mouse.button === Qt.RightButton) {
                card.nodeContextRequested(card.nodeData.node_id, mouse.x, mouse.y);
                mouse.accepted = true;
                return;
            }
            dragMoved = false;
        }
        onClicked: {
            if (mouse.button !== Qt.LeftButton)
                return;
            if (card._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y))
                return;
            var additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            card.nodeClicked(card.nodeData.node_id, additive);
        }
        onDoubleClicked: {
            if (mouse.button !== Qt.LeftButton)
                return;
            if (card._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y))
                return;
            card.nodeOpenRequested(card.nodeData.node_id);
        }
        onPositionChanged: {
            if (!drag.active)
                return;
            dragMoved = true;
            card.dragOffsetChanged(
                card.nodeData.node_id,
                card.x - card.worldOffset - card.nodeData.x,
                card.y - card.worldOffset - card.nodeData.y
            );
        }
        onReleased: {
            if (mouse.button !== Qt.LeftButton)
                return;
            card.dragFinished(
                card.nodeData.node_id,
                card.x - card.worldOffset,
                card.y - card.worldOffset,
                dragMoved
            );
        }
        onCanceled: {
            card.dragCanceled(card.nodeData.node_id);
        }
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

    Rectangle {
        z: 3
        visible: card._showAccentBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 4
        radius: 4
        color: card.nodeData ? card.nodeData.accent : "#4AA9D6"
    }

    Rectangle {
        z: 3
        visible: card._showHeaderBackground
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: Number(surfaceMetrics.header_top_margin)
        height: Number(surfaceMetrics.header_height)
        color: card.headerColor
        border.color: card.outlineColor
    }

    Text {
        objectName: "graphNodeTitle"
        property int effectiveRenderType: renderType
        z: 4
        anchors.left: parent.left
        anchors.leftMargin: card._titleLeftMargin
        anchors.right: parent.right
        anchors.rightMargin: card._titleRightMargin + (card.canEnterScope ? 56 : 0)
        y: card._titleTop
        height: card._titleHeight
        text: card.nodeData ? card.nodeData.title : ""
        color: card.headerTextColor
        font.pixelSize: card.isPassiveNode ? card.passiveFontPixelSize : 12
        font.bold: card.isPassiveNode ? card.passiveFontBold : true
        horizontalAlignment: card._titleCentered ? Text.AlignHCenter : Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        renderType: card.nodeTextRenderType
    }

    Rectangle {
        z: 4
        visible: card.canEnterScope
        anchors.right: parent.right
        anchors.rightMargin: 8
        y: card._titleTop + Math.max(0, (card._titleHeight - height) * 0.5)
        width: 48
        height: 16
        radius: 8
        color: card.scopeBadgeColor
        border.color: card.scopeBadgeBorderColor

        Text {
            anchors.centerIn: parent
            text: "OPEN"
            color: card.scopeBadgeTextColor
            font.pixelSize: 9
            font.bold: true
            renderType: card.nodeTextRenderType
        }
    }

    Button {
        id: surfaceHoverActionArea
        objectName: "graphNodeSurfaceHoverActionButton"
        z: 6
        visible: !card.surfaceInteractionLocked
            && Number(surfaceLoader.hoverActionHitRect.width || 0) > 0
            && Number(surfaceLoader.hoverActionHitRect.height || 0) > 0
        enabled: visible
        x: Number(surfaceLoader.hoverActionHitRect.x || 0)
        y: Number(surfaceLoader.hoverActionHitRect.y || 0)
        width: Number(surfaceLoader.hoverActionHitRect.width || 0)
        height: Number(surfaceLoader.hoverActionHitRect.height || 0)
        opacity: 0.0
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        padding: 0

        contentItem: Item {
        }

        background: Item {
        }

        onClicked: {
            surfaceLoader.triggerHoverAction();
        }
    }

    Item {
        id: portLayer
        z: 5
        anchors.fill: parent
        visible: card.nodeData ? !card.nodeData.collapsed : false

        Repeater {
            model: card.inputPorts
            delegate: Item {
                property int rowIndex: index
                readonly property var portPoint: card.localPortPoint("in", rowIndex)
                readonly property real dotDiameter: inputDot.width
                x: 0
                y: portPoint.y - height * 0.5
                width: card.width
                height: Math.max(dotDiameter, 18)

                Rectangle {
                    id: inputDot
                    objectName: "graphNodeInputPortDot"
                    property bool hoveredState: card.isHoveredPort("in", modelData.key)
                    property bool pendingState: card.isPendingPort("in", modelData.key)
                    property bool dragSourceState: card.isDragSourcePort("in", modelData.key)
                    property bool selectedState: card.isFlowchartSurface && card.isSelected
                    property bool attentionState: hoveredState || pendingState || dragSourceState
                    property bool interactiveState: attentionState || selectedState
                    property bool connectedState: card.isConnectedPort(modelData)
                    property color portColor: card.basePortColor(modelData.kind)
                    property real restDiameter: card.isFlowchartSurface
                        ? (connectedState ? card.flowchartConnectedPortDiameter : card.flowchartRestPortDiameter)
                        : 8
                    property real activeDiameter: card.isFlowchartSurface
                        ? (attentionState ? card.flowchartInteractivePortDiameter : card.flowchartSelectedPortDiameter)
                        : 14
                    property real ringDiameter: card.isFlowchartSurface ? card.flowchartInteractiveRingDiameter : (attentionState ? 18 : 12)
                    x: parent.portPoint.x - width * 0.5
                    anchors.verticalCenter: parent.verticalCenter
                    width: interactiveState ? activeDiameter : restDiameter
                    height: width
                    radius: width * 0.5
                    color: card.isFlowchartSurface
                        ? (attentionState
                            ? card.portInteractiveFillColor
                            : ((selectedState || connectedState) ? card.flowchartConnectedPortFillColor : "transparent"))
                        : (interactiveState ? card.portInteractiveFillColor : (connectedState ? portColor : "transparent"))
                    border.width: card.isFlowchartSurface ? (attentionState ? 1.8 : 1.1) : (interactiveState ? 2 : 1)
                    border.color: attentionState
                        ? card.portInteractiveBorderColor
                        : (card.isFlowchartSurface && selectedState ? card.selectedOutlineColor : portColor)

                    Rectangle {
                        objectName: "graphNodeInputPortRing"
                        anchors.centerIn: parent
                        visible: !card.isFlowchartSurface || inputDot.attentionState
                        width: inputDot.ringDiameter
                        height: inputDot.ringDiameter
                        radius: width * 0.5
                        z: -1
                        color: inputDot.attentionState ? card.portInteractiveRingFillColor : "transparent"
                        border.width: inputDot.attentionState ? 1 : 0
                        border.color: inputDot.attentionState ? card.portInteractiveRingBorderColor : "transparent"
                    }

                    MouseArea {
                        id: inputPortMouse
                        objectName: "graphNodeInputPortMouseArea"
                        enabled: !card.surfaceInteractionLocked
                        property real pressStartX: 0
                        property real pressStartY: 0
                        property bool movedState: false
                        x: -9
                        y: -9
                        width: parent.width + 18
                        height: parent.height + 18
                        acceptedButtons: Qt.LeftButton
                        hoverEnabled: true
                        preventStealing: true
                        cursorShape: Qt.PointingHandCursor
                        onPressed: {
                            if (mouse.button !== Qt.LeftButton)
                                return;
                            pressStartX = mouse.x;
                            pressStartY = mouse.y;
                            movedState = false;
                            var scenePos = card.portScenePos("in", rowIndex);
                            var pointerPos = card._pointerInCanvas(inputPortMouse, mouse);
                            card.portDragStarted(
                                card.nodeData.node_id,
                                modelData.key,
                                "in",
                                scenePos.x,
                                scenePos.y,
                                pointerPos.x,
                                pointerPos.y
                            );
                            mouse.accepted = true;
                        }
                        onPositionChanged: {
                            if (!pressed)
                                return;
                            if (Math.abs(mouse.x - pressStartX) >= card._portDragThreshold
                                || Math.abs(mouse.y - pressStartY) >= card._portDragThreshold) {
                                movedState = true;
                            }
                            var scenePos = card.portScenePos("in", rowIndex);
                            var pointerPos = card._pointerInCanvas(inputPortMouse, mouse);
                            card.portDragMoved(
                                card.nodeData.node_id,
                                modelData.key,
                                "in",
                                scenePos.x,
                                scenePos.y,
                                pointerPos.x,
                                pointerPos.y,
                                movedState
                            );
                        }
                        onReleased: {
                            var scenePos = card.portScenePos("in", rowIndex);
                            var pointerPos = card._pointerInCanvas(inputPortMouse, mouse);
                            card.portDragFinished(
                                card.nodeData.node_id,
                                modelData.key,
                                "in",
                                scenePos.x,
                                scenePos.y,
                                pointerPos.x,
                                pointerPos.y,
                                movedState
                            );
                            if (!movedState) {
                                card.portClicked(card.nodeData.node_id, modelData.key, "in", scenePos.x, scenePos.y);
                            }
                            movedState = false;
                        }
                        onCanceled: {
                            card.portDragCanceled(card.nodeData.node_id, modelData.key, "in");
                            movedState = false;
                        }
                        onEntered: {
                            var pos = card.portScenePos("in", rowIndex);
                            card.portHoverChanged(card.nodeData.node_id, modelData.key, "in", pos.x, pos.y, true);
                        }
                        onExited: {
                            var pos = card.portScenePos("in", rowIndex);
                            card.portHoverChanged(card.nodeData.node_id, modelData.key, "in", pos.x, pos.y, false);
                        }
                    }
                }

                Text {
                    objectName: "graphNodeInputPortLabel"
                    property int effectiveRenderType: renderType
                    readonly property real availableWidth: Math.max(0, card.width - x - 4)
                    visible: card._portLabelsVisible
                    anchors.verticalCenter: parent.verticalCenter
                    x: Math.max(0, inputDot.x + inputDot.width + card._portLabelGap)
                    width: card.portLabelWidth(implicitWidth, availableWidth)
                    text: modelData.label || modelData.key
                    color: card.portLabelColor
                    font.pixelSize: 10
                    elide: Text.ElideRight
                    renderType: card.nodeTextRenderType
                }
            }
        }

        Repeater {
            model: card.outputPorts
            delegate: Item {
                property int rowIndex: index
                readonly property var portPoint: card.localPortPoint("out", rowIndex)
                readonly property real dotDiameter: outputDot.width
                x: 0
                y: portPoint.y - height * 0.5
                width: card.width
                height: Math.max(dotDiameter, 18)

                Rectangle {
                    id: outputDot
                    objectName: "graphNodeOutputPortDot"
                    property bool hoveredState: card.isHoveredPort("out", modelData.key)
                    property bool pendingState: card.isPendingPort("out", modelData.key)
                    property bool dragSourceState: card.isDragSourcePort("out", modelData.key)
                    property bool selectedState: card.isFlowchartSurface && card.isSelected
                    property bool attentionState: hoveredState || pendingState || dragSourceState
                    property bool interactiveState: attentionState || selectedState
                    property bool connectedState: card.isConnectedPort(modelData)
                    property color portColor: card.basePortColor(modelData.kind)
                    property real restDiameter: card.isFlowchartSurface
                        ? (connectedState ? card.flowchartConnectedPortDiameter : card.flowchartRestPortDiameter)
                        : 8
                    property real activeDiameter: card.isFlowchartSurface
                        ? (attentionState ? card.flowchartInteractivePortDiameter : card.flowchartSelectedPortDiameter)
                        : 14
                    property real ringDiameter: card.isFlowchartSurface ? card.flowchartInteractiveRingDiameter : (attentionState ? 18 : 12)
                    x: parent.portPoint.x - width * 0.5
                    anchors.verticalCenter: parent.verticalCenter
                    width: interactiveState ? activeDiameter : restDiameter
                    height: width
                    radius: width * 0.5
                    color: card.isFlowchartSurface
                        ? (attentionState
                            ? card.portInteractiveFillColor
                            : ((selectedState || connectedState) ? card.flowchartConnectedPortFillColor : "transparent"))
                        : (interactiveState ? card.portInteractiveFillColor : (connectedState ? portColor : "transparent"))
                    border.width: card.isFlowchartSurface ? (attentionState ? 1.8 : 1.1) : (interactiveState ? 2 : 1)
                    border.color: attentionState
                        ? card.portInteractiveBorderColor
                        : (card.isFlowchartSurface && selectedState ? card.selectedOutlineColor : portColor)

                    Rectangle {
                        objectName: "graphNodeOutputPortRing"
                        anchors.centerIn: parent
                        visible: !card.isFlowchartSurface || outputDot.attentionState
                        width: outputDot.ringDiameter
                        height: outputDot.ringDiameter
                        radius: width * 0.5
                        z: -1
                        color: outputDot.attentionState ? card.portInteractiveRingFillColor : "transparent"
                        border.width: outputDot.attentionState ? 1 : 0
                        border.color: outputDot.attentionState ? card.portInteractiveRingBorderColor : "transparent"
                    }

                    MouseArea {
                        id: outputPortMouse
                        objectName: "graphNodeOutputPortMouseArea"
                        enabled: !card.surfaceInteractionLocked
                        property real pressStartX: 0
                        property real pressStartY: 0
                        property bool movedState: false
                        property bool hoverActive: false
                        x: -9
                        y: -9
                        width: parent.width + 18
                        height: parent.height + 18
                        acceptedButtons: Qt.LeftButton
                        hoverEnabled: true
                        preventStealing: true
                        cursorShape: Qt.PointingHandCursor
                        function updateHoverState(localX, localY) {
                            var nextHover = !card._isResizeHandlePoint(localX, localY);
                            if (hoverActive === nextHover)
                                return;
                            hoverActive = nextHover;
                            var pos = card.portScenePos("out", rowIndex);
                            card.portHoverChanged(card.nodeData.node_id, modelData.key, "out", pos.x, pos.y, nextHover);
                        }
                        onPressed: {
                            if (mouse.button !== Qt.LeftButton)
                                return;
                            var localPoint = outputPortMouse.mapToItem(card, mouse.x, mouse.y);
                            if (card._isResizeHandlePoint(localPoint.x, localPoint.y)) {
                                mouse.accepted = false;
                                return;
                            }
                            pressStartX = mouse.x;
                            pressStartY = mouse.y;
                            movedState = false;
                            var scenePos = card.portScenePos("out", rowIndex);
                            var pointerPos = card._pointerInCanvas(outputPortMouse, mouse);
                            card.portDragStarted(
                                card.nodeData.node_id,
                                modelData.key,
                                "out",
                                scenePos.x,
                                scenePos.y,
                                pointerPos.x,
                                pointerPos.y
                            );
                            mouse.accepted = true;
                        }
                        onPositionChanged: {
                            var localPoint = outputPortMouse.mapToItem(card, mouse.x, mouse.y);
                            updateHoverState(localPoint.x, localPoint.y);
                            if (!pressed)
                                return;
                            if (Math.abs(mouse.x - pressStartX) >= card._portDragThreshold
                                || Math.abs(mouse.y - pressStartY) >= card._portDragThreshold) {
                                movedState = true;
                            }
                            var scenePos = card.portScenePos("out", rowIndex);
                            var pointerPos = card._pointerInCanvas(outputPortMouse, mouse);
                            card.portDragMoved(
                                card.nodeData.node_id,
                                modelData.key,
                                "out",
                                scenePos.x,
                                scenePos.y,
                                pointerPos.x,
                                pointerPos.y,
                                movedState
                            );
                        }
                        onReleased: {
                            var scenePos = card.portScenePos("out", rowIndex);
                            var pointerPos = card._pointerInCanvas(outputPortMouse, mouse);
                            card.portDragFinished(
                                card.nodeData.node_id,
                                modelData.key,
                                "out",
                                scenePos.x,
                                scenePos.y,
                                pointerPos.x,
                                pointerPos.y,
                                movedState
                            );
                            if (!movedState) {
                                card.portClicked(card.nodeData.node_id, modelData.key, "out", scenePos.x, scenePos.y);
                            }
                            movedState = false;
                        }
                        onCanceled: {
                            card.portDragCanceled(card.nodeData.node_id, modelData.key, "out");
                            movedState = false;
                        }
                        onEntered: {
                            var localPoint = outputPortMouse.mapToItem(card, outputPortMouse.mouseX, outputPortMouse.mouseY);
                            updateHoverState(localPoint.x, localPoint.y);
                        }
                        onExited: {
                            if (!hoverActive)
                                return;
                            hoverActive = false;
                            var pos = card.portScenePos("out", rowIndex);
                            card.portHoverChanged(card.nodeData.node_id, modelData.key, "out", pos.x, pos.y, false);
                        }
                    }
                }

                Text {
                    objectName: "graphNodeOutputPortLabel"
                    property int effectiveRenderType: renderType
                    readonly property real availableWidth: Math.max(0, outputDot.x - card._portLabelGap - 4)
                    visible: card._portLabelsVisible
                    anchors.verticalCenter: parent.verticalCenter
                    width: card.portLabelWidth(implicitWidth, availableWidth)
                    x: Math.max(4, outputDot.x - card._portLabelGap - width)
                    text: modelData.label || modelData.key
                    color: card.portLabelColor
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideLeft
                    renderType: card.nodeTextRenderType
                }
            }
        }
    }

    Canvas {
        id: resizeGrip
        z: 6
        width: card._resizeHandleSize
        height: card._resizeHandleSize
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: card.nodeData ? (!card.nodeData.collapsed && !card.surfaceInteractionLocked) : false
        onPaint: {
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            ctx.strokeStyle = card.outlineColor;
            ctx.lineWidth = 1.2;
            ctx.lineCap = "round";
            for (var i = 1; i <= 3; i++) {
                var off = i * 3.5;
                ctx.beginPath();
                ctx.moveTo(width - off, height - 1);
                ctx.lineTo(width - 1, height - off);
                ctx.stroke();
            }
        }
    }

    MouseArea {
        id: resizeDragArea
        objectName: "graphNodeResizeDragArea"
        z: 5
        width: card._resizeHandleSize
        height: card._resizeHandleSize
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: card.nodeData ? (!card.nodeData.collapsed && !card.surfaceInteractionLocked) : false
        enabled: !card.surfaceInteractionLocked
        hoverEnabled: true
        cursorShape: Qt.SizeFDiagCursor
        preventStealing: true
        property real pressGlobalX: 0
        property real pressGlobalY: 0
        property real pressWidth: 0
        property real pressHeight: 0

        onPressed: function(mouse) {
            var gp = mapToGlobal(mouse.x, mouse.y);
            pressGlobalX = gp.x;
            pressGlobalY = gp.y;
            pressWidth = card.width;
            pressHeight = card.height;
            card._liveWidth = pressWidth;
            card._liveHeight = pressHeight;
            card.resizePreviewChanged(card.nodeData.node_id, pressWidth, pressHeight, true);
            mouse.accepted = true;
        }
        onPositionChanged: function(mouse) {
            if (!pressed)
                return;
            var gp = mapToGlobal(mouse.x, mouse.y);
            var dw = (gp.x - pressGlobalX) / card.zoom;
            var dh = (gp.y - pressGlobalY) / card.zoom;
            card._liveWidth = Math.max(card._minNodeWidth, pressWidth + dw);
            card._liveHeight = Math.max(card._minNodeHeight, pressHeight + dh);
            card.resizePreviewChanged(card.nodeData.node_id, card._liveWidth, card._liveHeight, true);
        }
        onReleased: function(_mouse) {
            if (card._liveWidth <= 0)
                return;
            var finalWidth = card._liveWidth;
            var finalHeight = card._liveHeight;
            card._liveWidth = 0;
            card._liveHeight = 0;
            card.resizePreviewChanged(card.nodeData.node_id, finalWidth, finalHeight, false);
            card.resizeFinished(card.nodeData.node_id, finalWidth, finalHeight);
        }
        onCanceled: {
            var fallbackWidth = card._liveWidth > 0 ? card._liveWidth : card.width;
            var fallbackHeight = card._liveHeight > 0 ? card._liveHeight : card.height;
            card._liveWidth = 0;
            card._liveHeight = 0;
            card.resizePreviewChanged(card.nodeData.node_id, fallbackWidth, fallbackHeight, false);
        }
    }
}
