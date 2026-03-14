import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

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

    signal nodeClicked(string nodeId, bool additive)
    signal nodeOpenRequested(string nodeId)
    signal nodeContextRequested(string nodeId, real localX, real localY)
    signal dragOffsetChanged(string nodeId, real dx, real dy)
    signal dragFinished(string nodeId, real finalX, real finalY, bool moved)
    signal dragCanceled(string nodeId)
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

    readonly property real _portHeight: 18
    readonly property real _inlineRowHeight: 26
    readonly property real _inlineRowSpacing: 4
    readonly property real _inlineSectionPadding: 8
    readonly property var inlineProperties: {
        if (!card.nodeData || !card.nodeData.inline_properties)
            return [];
        return card.nodeData.inline_properties;
    }
    readonly property real inlineBodyHeight: {
        if (!card.inlineProperties.length)
            return 0;
        return card._inlineSectionPadding
            + card.inlineProperties.length * card._inlineRowHeight
            + Math.max(0, card.inlineProperties.length - 1) * card._inlineRowSpacing;
    }
    readonly property real _portTop: 30 + inlineBodyHeight
    readonly property real _portCenterOffset: 6
    readonly property real _portSideMargin: 8
    readonly property real _portDotRadius: 3.5
    readonly property real _portDragThreshold: 2
    readonly property bool canEnterScope: !!card.nodeData && !!card.nodeData.can_enter_scope

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

    function portScenePos(direction, rowIndex) {
        if (!card.nodeData)
            return {"x": 0.0, "y": 0.0};
        var xValue = direction === "in"
            ? card.nodeData.x + card._portSideMargin + card._portDotRadius
            : card.nodeData.x + card.nodeData.width - card._portSideMargin - card._portDotRadius;
        var yValue = card.nodeData.y + card._portTop + card._portCenterOffset + card._portHeight * rowIndex;
        return {"x": xValue, "y": yValue};
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

    z: card.nodeData && card.nodeData.selected ? 30 : 20
    x: (card.nodeData ? card.nodeData.x : 0.0) + card.worldOffset
    y: (card.nodeData ? card.nodeData.y : 0.0) + card.worldOffset
    transform: Translate {
        x: nodeDragArea.drag.active ? 0 : card.liveDragDx
        y: nodeDragArea.drag.active ? 0 : card.liveDragDy
    }
    width: card.nodeData ? card.nodeData.width : 0.0
    height: card.nodeData ? card.nodeData.height : 0.0
    color: card.surfaceColor
    border.width: card.nodeData && card.nodeData.selected ? 2 : 1
    border.color: card.nodeData && card.nodeData.selected ? card.selectedOutlineColor : card.outlineColor
    radius: 6

    Rectangle {
        id: shadowOuter
        visible: card.showShadow
        x: -4
        y: 2
        z: -3
        width: card.width + 8
        height: card.height + 8
        radius: card.radius + 4
        color: "#18000000"
    }
    Rectangle {
        id: shadowMid
        visible: card.showShadow
        x: -2
        y: 2
        z: -2
        width: card.width + 4
        height: card.height + 5
        radius: card.radius + 2
        color: "#28000000"
    }
    Rectangle {
        id: shadowInner
        visible: card.showShadow
        x: 0
        y: 2
        z: -1
        width: card.width
        height: card.height + 2
        radius: card.radius
        color: "#38000000"
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 4
        radius: 4
        color: card.nodeData ? card.nodeData.accent : "#4AA9D6"
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 4
        height: 24
        color: card.headerColor
        border.color: card.outlineColor

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.right: parent.right
            anchors.rightMargin: card.canEnterScope ? 66 : 10
            anchors.verticalCenter: parent.verticalCenter
            text: card.nodeData ? card.nodeData.title : ""
            color: card.headerTextColor
            font.pixelSize: 12
            font.bold: true
            elide: Text.ElideRight
        }

        Rectangle {
            visible: card.canEnterScope
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
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
    }

    Item {
        z: 3
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 30
        anchors.bottom: parent.bottom
        anchors.margins: 8
        visible: card.nodeData ? !card.nodeData.collapsed : false

        Column {
            id: inlineControlsColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: card._inlineRowSpacing
            visible: card.inlineProperties.length > 0

            Repeater {
                model: card.inlineProperties
                delegate: Rectangle {
                    width: inlineControlsColumn.width
                    height: card._inlineRowHeight
                    radius: 4
                    color: card.inlineRowColor
                    border.color: card.inlineRowBorderColor

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 6
                        spacing: 6

                        Text {
                            Layout.preferredWidth: 78
                            text: String(modelData.label || modelData.key || "")
                            color: card.inlineLabelColor
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }

                        CheckBox {
                            visible: modelData.inline_editor === "toggle"
                            enabled: !modelData.overridden_by_input
                            checked: !!modelData.value
                            onClicked: card.inlinePropertyCommitted(card.nodeData.node_id, modelData.key, checked)
                        }

                        ComboBox {
                            visible: modelData.inline_editor === "enum"
                            Layout.fillWidth: true
                            enabled: !modelData.overridden_by_input
                            model: modelData.enum_values || []
                            currentIndex: {
                                var values = modelData.enum_values || [];
                                var value = String(modelData.value || "");
                                var matchIndex = values.indexOf(value);
                                return matchIndex >= 0 ? matchIndex : 0;
                            }
                            onActivated: {
                                var values = modelData.enum_values || [];
                                if (currentIndex < 0 || currentIndex >= values.length)
                                    return;
                                card.inlinePropertyCommitted(card.nodeData.node_id, modelData.key, String(values[currentIndex]));
                            }
                        }

                        TextField {
                            visible: modelData.inline_editor === "text" || modelData.inline_editor === "number"
                            Layout.fillWidth: true
                            enabled: !modelData.overridden_by_input
                            text: card.inlineEditorText(modelData)
                            selectByMouse: true
                            color: card.inlineInputTextColor
                            background: Rectangle {
                                color: card.inlineInputBackgroundColor
                                border.color: card.inlineInputBorderColor
                                radius: 3
                            }
                            onAccepted: card.inlinePropertyCommitted(card.nodeData.node_id, modelData.key, text)
                            onEditingFinished: card.inlinePropertyCommitted(card.nodeData.node_id, modelData.key, text)
                        }

                        Text {
                            visible: modelData.overridden_by_input
                            Layout.fillWidth: true
                            text: "Driven by " + String(modelData.input_port_label || "input")
                            color: card.inlineDrivenTextColor
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }

        Column {
            anchors.left: parent.left
            anchors.top: inlineControlsColumn.visible ? inlineControlsColumn.bottom : parent.top
            anchors.topMargin: inlineControlsColumn.visible ? card._inlineSectionPadding : 0
            spacing: 4

            Repeater {
                model: card.inputPorts
                delegate: Row {
                    property int rowIndex: index
                    spacing: 6

                    Rectangle {
                        id: inputDot
                        property bool hoveredState: card.isHoveredPort("in", modelData.key)
                        property bool pendingState: card.isPendingPort("in", modelData.key)
                        property bool dragSourceState: card.isDragSourcePort("in", modelData.key)
                        property bool interactiveState: hoveredState || pendingState || dragSourceState
                        property bool connectedState: card.isConnectedPort(modelData)
                        property color portColor: card.basePortColor(modelData.kind)
                        width: interactiveState ? 14 : 8
                        height: interactiveState ? 14 : 8
                        radius: width * 0.5
                        anchors.verticalCenter: parent.verticalCenter
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
                        text: modelData.label || modelData.key
                        color: card.portLabelColor
                        font.pixelSize: 10
                    }
                }
            }
        }

        Column {
            id: outputPortsColumn
            anchors.right: parent.right
            anchors.top: inlineControlsColumn.visible ? inlineControlsColumn.bottom : parent.top
            anchors.topMargin: inlineControlsColumn.visible ? card._inlineSectionPadding : 0
            spacing: 4

            Repeater {
                model: card.outputPorts
                delegate: Row {
                    property int rowIndex: index
                    anchors.right: outputPortsColumn.right
                    spacing: 6

                    Text {
                        text: modelData.label || modelData.key
                        color: card.portLabelColor
                        font.pixelSize: 10
                    }

                    Rectangle {
                        id: outputDot
                        property bool hoveredState: card.isHoveredPort("out", modelData.key)
                        property bool pendingState: card.isPendingPort("out", modelData.key)
                        property bool dragSourceState: card.isDragSourcePort("out", modelData.key)
                        property bool interactiveState: hoveredState || pendingState || dragSourceState
                        property bool connectedState: card.isConnectedPort(modelData)
                        property color portColor: card.basePortColor(modelData.kind)
                        width: interactiveState ? 14 : 8
                        height: interactiveState ? 14 : 8
                        radius: width * 0.5
                        anchors.verticalCenter: parent.verticalCenter
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
                                var pos = card.portScenePos("out", rowIndex);
                                card.portHoverChanged(card.nodeData.node_id, modelData.key, "out", pos.x, pos.y, true);
                            }
                            onExited: {
                                var pos = card.portScenePos("out", rowIndex);
                                card.portHoverChanged(card.nodeData.node_id, modelData.key, "out", pos.x, pos.y, false);
                            }
                        }
                    }
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
}
