import QtQuick 2.15

Rectangle {
    id: card
    property var nodeData: null
    property real worldOffset: 0
    property var hoveredPort: null
    property var pendingPort: null

    signal nodeClicked(string nodeId, bool additive)
    signal nodeContextRequested(string nodeId, real localX, real localY)
    signal dragOffsetChanged(string nodeId, real dx, real dy)
    signal dragFinished(string nodeId, real finalX, real finalY, bool moved)
    signal dragCanceled(string nodeId)
    signal portClicked(string nodeId, string portKey, string direction, real sceneX, real sceneY)
    signal portHoverChanged(
        string nodeId,
        string portKey,
        string direction,
        real sceneX,
        real sceneY,
        bool hovered
    )

    readonly property real _portHeight: 18
    readonly property real _portTop: 30
    readonly property real _portCenterOffset: 6
    readonly property real _portSideMargin: 8
    readonly property real _portDotRadius: 3.5

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
        if (portKind === "exec")
            return "#67D487";
        if (portKind === "completed")
            return "#E4CE7D";
        return "#7AA8FF";
    }

    function isHoveredPort(direction, portKey) {
        return !!card.hoveredPort
            && card.hoveredPort.node_id === card.nodeData.node_id
            && card.hoveredPort.port_key === portKey
            && card.hoveredPort.direction === direction;
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

    z: card.nodeData && card.nodeData.selected ? 30 : 20
    x: (card.nodeData ? card.nodeData.x : 0.0) + card.worldOffset
    y: (card.nodeData ? card.nodeData.y : 0.0) + card.worldOffset
    width: card.nodeData ? card.nodeData.width : 0.0
    height: card.nodeData ? card.nodeData.height : 0.0
    color: "#262A31"
    border.width: card.nodeData && card.nodeData.selected ? 2 : 1
    border.color: card.nodeData && card.nodeData.selected ? "#60CDFF" : "#4A4F59"
    radius: 6

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
        color: "#2F333B"
        border.color: "#3A404B"

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            text: card.nodeData ? card.nodeData.title : ""
            color: "#F5F8FF"
            font.pixelSize: 12
            font.bold: true
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
            anchors.left: parent.left
            anchors.top: parent.top
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
                        property bool interactiveState: hoveredState || pendingState
                        property bool connectedState: card.isConnectedPort(modelData)
                        width: interactiveState ? 14 : 8
                        height: interactiveState ? 14 : 8
                        radius: width * 0.5
                        anchors.verticalCenter: parent.verticalCenter
                        color: interactiveState ? "#FFDA6B" : (connectedState ? "#67D487" : "transparent")
                        border.width: interactiveState ? 2 : 1
                        border.color: interactiveState
                            ? "#FFF4CB"
                            : (connectedState ? "#67D487" : card.basePortColor(modelData.kind))

                        Rectangle {
                            anchors.centerIn: parent
                            width: inputDot.interactiveState ? 18 : 12
                            height: inputDot.interactiveState ? 18 : 12
                            radius: width * 0.5
                            z: -1
                            color: inputDot.interactiveState ? "#44FFC857" : "transparent"
                            border.width: inputDot.interactiveState ? 1 : 0
                            border.color: inputDot.interactiveState ? "#66FFE29A" : "transparent"
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
                                mouse.accepted = true;
                            }
                            onPositionChanged: {
                                if (!pressed)
                                    return;
                                if (Math.abs(mouse.x - pressStartX) >= 2 || Math.abs(mouse.y - pressStartY) >= 2)
                                    movedState = true;
                            }
                            onReleased: {
                                if (!movedState) {
                                    var clickPos = card.portScenePos("in", rowIndex);
                                    card.portClicked(card.nodeData.node_id, modelData.key, "in", clickPos.x, clickPos.y);
                                }
                                movedState = false;
                            }
                            onCanceled: {
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
                        text: modelData.key
                        color: "#CAD1DF"
                        font.pixelSize: 10
                    }
                }
            }
        }

        Column {
            id: outputPortsColumn
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: 4

            Repeater {
                model: card.outputPorts
                delegate: Row {
                    property int rowIndex: index
                    anchors.right: outputPortsColumn.right
                    spacing: 6

                    Text {
                        text: modelData.key
                        color: "#CAD1DF"
                        font.pixelSize: 10
                    }

                    Rectangle {
                        id: outputDot
                        property bool hoveredState: card.isHoveredPort("out", modelData.key)
                        property bool pendingState: card.isPendingPort("out", modelData.key)
                        property bool interactiveState: hoveredState || pendingState
                        property bool connectedState: card.isConnectedPort(modelData)
                        width: interactiveState ? 14 : 8
                        height: interactiveState ? 14 : 8
                        radius: width * 0.5
                        anchors.verticalCenter: parent.verticalCenter
                        color: interactiveState ? "#FFDA6B" : (connectedState ? "#67D487" : "transparent")
                        border.width: interactiveState ? 2 : 1
                        border.color: interactiveState
                            ? "#FFF4CB"
                            : (connectedState ? "#67D487" : card.basePortColor(modelData.kind))

                        Rectangle {
                            anchors.centerIn: parent
                            width: outputDot.interactiveState ? 18 : 12
                            height: outputDot.interactiveState ? 18 : 12
                            radius: width * 0.5
                            z: -1
                            color: outputDot.interactiveState ? "#44FFC857" : "transparent"
                            border.width: outputDot.interactiveState ? 1 : 0
                            border.color: outputDot.interactiveState ? "#66FFE29A" : "transparent"
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
                                mouse.accepted = true;
                            }
                            onPositionChanged: {
                                if (!pressed)
                                    return;
                                if (Math.abs(mouse.x - pressStartX) >= 2 || Math.abs(mouse.y - pressStartY) >= 2)
                                    movedState = true;
                            }
                            onReleased: {
                                if (!movedState) {
                                    var clickPos = card.portScenePos("out", rowIndex);
                                    card.portClicked(card.nodeData.node_id, modelData.key, "out", clickPos.x, clickPos.y);
                                }
                                movedState = false;
                            }
                            onCanceled: {
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
