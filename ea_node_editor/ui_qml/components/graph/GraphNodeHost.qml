import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Effects
import "GraphNodeSurfaceMetrics.js" as GraphNodeSurfaceMetrics

Rectangle {
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
    property string surfaceFamilyOverride: ""
    property string surfaceVariantOverride: ""
    readonly property var nodePalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.node_palette
        : ({})
    readonly property var portKindPalette: typeof graphThemeBridge !== "undefined"
        ? graphThemeBridge.port_kind_palette
        : ({})
    readonly property color surfaceColor: nodePalette.card_bg || "#1b1d22"
    readonly property color outlineColor: nodePalette.card_border || "#3a3d45"
    readonly property color selectedOutlineColor: nodePalette.card_selected_border || "#60CDFF"
    readonly property color headerColor: nodePalette.header_bg || "#2a2b30"
    readonly property color headerTextColor: nodePalette.header_fg || "#f0f4fb"
    readonly property color scopeBadgeColor: nodePalette.scope_badge_bg || "#1D8CE0"
    readonly property color scopeBadgeBorderColor: nodePalette.scope_badge_border || "#60CDFF"
    readonly property color scopeBadgeTextColor: nodePalette.scope_badge_fg || "#f2f4f8"
    readonly property color inlineRowColor: nodePalette.inline_row_bg || "#24262c"
    readonly property color inlineRowBorderColor: nodePalette.inline_row_border || "#4a4f5a"
    readonly property color inlineLabelColor: nodePalette.inline_label_fg || "#d0d5de"
    readonly property color inlineInputTextColor: nodePalette.inline_input_fg || "#f0f2f5"
    readonly property color inlineInputBackgroundColor: nodePalette.inline_input_bg || "#22242a"
    readonly property color inlineInputBorderColor: nodePalette.inline_input_border || "#4a4f5a"
    readonly property color inlineDrivenTextColor: nodePalette.inline_driven_fg || "#bdc5d3"
    readonly property color portLabelColor: nodePalette.port_label_fg || "#d0d5de"
    readonly property color portInteractiveFillColor: nodePalette.port_interactive_fill || "#FFDA6B"
    readonly property color portInteractiveBorderColor: nodePalette.port_interactive_border || "#FFE48B"
    readonly property color portInteractiveRingFillColor: nodePalette.port_interactive_ring_fill || "#44FFC857"
    readonly property color portInteractiveRingBorderColor: nodePalette.port_interactive_ring_border || "#66FFE29A"
    readonly property string surfaceFamily: String(surfaceFamilyOverride || (nodeData ? nodeData.surface_family || "standard" : "standard"))
    readonly property string surfaceVariant: String(surfaceVariantOverride || (nodeData ? nodeData.surface_variant || "" : ""))
    readonly property var surfaceMetrics: GraphNodeSurfaceMetrics.surfaceMetrics(nodeData)
    readonly property bool isCollapsed: !!nodeData && !!nodeData.collapsed

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
    readonly property bool _showHeaderBackground: card.isCollapsed || Boolean(surfaceMetrics.show_header_background)
    readonly property real _titleTop: card.isCollapsed ? 4.0 : Number(surfaceMetrics.title_top)
    readonly property real _titleHeight: card.isCollapsed ? 24.0 : Number(surfaceMetrics.title_height)
    readonly property real _titleLeftMargin: card.isCollapsed ? 10.0 : Number(surfaceMetrics.title_left_margin)
    readonly property real _titleRightMargin: card.isCollapsed ? 10.0 : Number(surfaceMetrics.title_right_margin)
    readonly property bool _titleCentered: !card.isCollapsed && Boolean(surfaceMetrics.title_centered)
    readonly property real _portLabelGap: 6.0
    readonly property real _portLabelMaxWidth: Math.max(40.0, card.width * 0.46)

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

    function basePortColor(portKind) {
        var palette = card.portKindPalette || {};
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

    z: card.nodeData && card.nodeData.selected ? 30 : 20
    x: (card.nodeData ? card.nodeData.x : 0.0) + card.worldOffset
    y: (card.nodeData ? card.nodeData.y : 0.0) + card.worldOffset
    transform: Translate {
        x: nodeDragArea.drag.active ? 0 : card.liveDragDx
        y: nodeDragArea.drag.active ? 0 : card.liveDragDy
    }
    width: card._liveWidth > 0 ? card._liveWidth : (card.nodeData ? card.nodeData.width : Number(surfaceMetrics.default_width))
    height: card._liveHeight > 0 ? card._liveHeight : (card.nodeData ? card.nodeData.height : Number(surfaceMetrics.default_height))
    color: card._useHostChrome ? card.surfaceColor : "transparent"
    border.width: card._useHostChrome ? (card.nodeData && card.nodeData.selected ? 2 : 1) : 0
    border.color: card.nodeData && card.nodeData.selected ? card.selectedOutlineColor : card.outlineColor
    radius: card._useHostChrome ? 6 : 0

    layer.enabled: card.showShadow
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowBlur: card.shadowSoftness / 100.0
        shadowColor: Qt.rgba(0, 0, 0, card.shadowStrength / 100.0)
        shadowVerticalOffset: card.shadowOffset
        shadowHorizontalOffset: 0
        autoPaddingEnabled: true
    }

    Item {
        id: surfaceLayer
        z: 1
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
        z: 4
        anchors.left: parent.left
        anchors.leftMargin: card._titleLeftMargin
        anchors.right: parent.right
        anchors.rightMargin: card._titleRightMargin + (card.canEnterScope ? 56 : 0)
        y: card._titleTop
        height: card._titleHeight
        text: card.nodeData ? card.nodeData.title : ""
        color: card.headerTextColor
        font.pixelSize: 12
        font.bold: true
        horizontalAlignment: card._titleCentered ? Text.AlignHCenter : Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
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
                readonly property real dotDiameter: inputDot.interactiveState ? 14 : 8
                x: 0
                y: portPoint.y - height * 0.5
                width: card.width
                height: Math.max(dotDiameter, 18)

                Rectangle {
                    id: inputDot
                    property bool hoveredState: card.isHoveredPort("in", modelData.key)
                    property bool pendingState: card.isPendingPort("in", modelData.key)
                    property bool dragSourceState: card.isDragSourcePort("in", modelData.key)
                    property bool interactiveState: hoveredState || pendingState || dragSourceState
                    property bool connectedState: card.isConnectedPort(modelData)
                    property color portColor: card.basePortColor(modelData.kind)
                    x: parent.portPoint.x - width * 0.5
                    anchors.verticalCenter: parent.verticalCenter
                    width: interactiveState ? 14 : 8
                    height: interactiveState ? 14 : 8
                    radius: width * 0.5
                    color: interactiveState ? card.portInteractiveFillColor : (connectedState ? portColor : "transparent")
                    border.width: interactiveState ? 2 : 1
                    border.color: interactiveState
                        ? card.portInteractiveBorderColor
                        : portColor

                    Rectangle {
                        anchors.centerIn: parent
                        width: inputDot.interactiveState ? 18 : 12
                        height: inputDot.interactiveState ? 18 : 12
                        radius: width * 0.5
                        z: -1
                        color: inputDot.interactiveState ? card.portInteractiveRingFillColor : "transparent"
                        border.width: inputDot.interactiveState ? 1 : 0
                        border.color: inputDot.interactiveState ? card.portInteractiveRingBorderColor : "transparent"
                    }

                    MouseArea {
                        id: inputPortMouse
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
                    anchors.verticalCenter: parent.verticalCenter
                    x: Math.max(0, inputDot.x + inputDot.width + card._portLabelGap)
                    width: Math.max(0, Math.min(card._portLabelMaxWidth, card.width - x - 4))
                    text: modelData.label || modelData.key
                    color: card.portLabelColor
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }
            }
        }

        Repeater {
            model: card.outputPorts
            delegate: Item {
                property int rowIndex: index
                readonly property var portPoint: card.localPortPoint("out", rowIndex)
                readonly property real dotDiameter: outputDot.interactiveState ? 14 : 8
                x: 0
                y: portPoint.y - height * 0.5
                width: card.width
                height: Math.max(dotDiameter, 18)

                Rectangle {
                    id: outputDot
                    property bool hoveredState: card.isHoveredPort("out", modelData.key)
                    property bool pendingState: card.isPendingPort("out", modelData.key)
                    property bool dragSourceState: card.isDragSourcePort("out", modelData.key)
                    property bool interactiveState: hoveredState || pendingState || dragSourceState
                    property bool connectedState: card.isConnectedPort(modelData)
                    property color portColor: card.basePortColor(modelData.kind)
                    x: parent.portPoint.x - width * 0.5
                    anchors.verticalCenter: parent.verticalCenter
                    width: interactiveState ? 14 : 8
                    height: interactiveState ? 14 : 8
                    radius: width * 0.5
                    color: interactiveState ? card.portInteractiveFillColor : (connectedState ? portColor : "transparent")
                    border.width: interactiveState ? 2 : 1
                    border.color: interactiveState
                        ? card.portInteractiveBorderColor
                        : portColor

                    Rectangle {
                        anchors.centerIn: parent
                        width: outputDot.interactiveState ? 18 : 12
                        height: outputDot.interactiveState ? 18 : 12
                        radius: width * 0.5
                        z: -1
                        color: outputDot.interactiveState ? card.portInteractiveRingFillColor : "transparent"
                        border.width: outputDot.interactiveState ? 1 : 0
                        border.color: outputDot.interactiveState ? card.portInteractiveRingBorderColor : "transparent"
                    }

                    MouseArea {
                        id: outputPortMouse
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
                    anchors.verticalCenter: parent.verticalCenter
                    x: 4
                    width: Math.max(0, Math.min(card._portLabelMaxWidth, outputDot.x - card._portLabelGap - x))
                    text: modelData.label || modelData.key
                    color: card.portLabelColor
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideLeft
                }
            }
        }
    }

    MouseArea {
        id: nodeDragArea
        z: 2
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true
        cursorShape: drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        drag.target: card
        drag.axis: Drag.XAndYAxis
        propagateComposedEvents: true
        property bool dragMoved: false

        onPressed: {
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
            var additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            card.nodeClicked(card.nodeData.node_id, additive);
        }
        onDoubleClicked: {
            if (mouse.button !== Qt.LeftButton)
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

    Canvas {
        id: resizeGrip
        z: 6
        width: card._resizeHandleSize
        height: card._resizeHandleSize
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: card.nodeData ? !card.nodeData.collapsed : false
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
        z: 5
        width: card._resizeHandleSize
        height: card._resizeHandleSize
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: card.nodeData ? !card.nodeData.collapsed : false
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
