import QtQuick 2.15

Item {
    id: root
    objectName: "graphNodePortsLayer"
    property Item host: null
    z: 5
    visible: root.host && root.host.nodeData ? !root.host.nodeData.collapsed : false

    Repeater {
        model: root.host ? root.host.inputPorts : []

        delegate: Item {
            property int rowIndex: index
            readonly property var portPoint: root.host
                ? root.host.localPortPoint("in", rowIndex)
                : ({"x": 0.0, "y": 0.0})
            readonly property real dotDiameter: inputDot.width
            x: 0
            y: portPoint.y - height * 0.5
            width: root.host ? root.host.width : 0
            height: Math.max(dotDiameter, 18)

            Rectangle {
                id: inputDot
                objectName: "graphNodeInputPortDot"
                property bool hoveredState: root.host ? root.host.isHoveredPort("in", modelData.key) : false
                property bool pendingState: root.host ? root.host.isPendingPort("in", modelData.key) : false
                property bool dragSourceState: root.host ? root.host.isDragSourcePort("in", modelData.key) : false
                property bool selectedState: root.host ? (root.host.isFlowchartSurface && root.host.isSelected) : false
                property bool attentionState: hoveredState || pendingState || dragSourceState
                property bool interactiveState: attentionState || selectedState
                property bool connectedState: root.host ? root.host.isConnectedPort(modelData) : false
                property color portColor: root.host ? root.host.basePortColor(modelData.kind) : "#7AA8FF"
                property real restDiameter: root.host && root.host.isFlowchartSurface
                    ? (connectedState ? root.host.flowchartConnectedPortDiameter : root.host.flowchartRestPortDiameter)
                    : 8
                property real activeDiameter: root.host && root.host.isFlowchartSurface
                    ? (attentionState ? root.host.flowchartInteractivePortDiameter : root.host.flowchartSelectedPortDiameter)
                    : 14
                property real ringDiameter: root.host && root.host.isFlowchartSurface
                    ? root.host.flowchartInteractiveRingDiameter
                    : (attentionState ? 18 : 12)
                x: parent.portPoint.x - width * 0.5
                anchors.verticalCenter: parent.verticalCenter
                width: interactiveState ? activeDiameter : restDiameter
                height: width
                radius: width * 0.5
                color: root.host && root.host.isFlowchartSurface
                    ? (attentionState
                        ? root.host.portInteractiveFillColor
                        : ((selectedState || connectedState) ? root.host.flowchartConnectedPortFillColor : "transparent"))
                    : (interactiveState
                        ? (root.host ? root.host.portInteractiveFillColor : "#FFDA6B")
                        : (connectedState ? portColor : "transparent"))
                border.width: root.host && root.host.isFlowchartSurface ? (attentionState ? 1.8 : 1.1) : (interactiveState ? 2 : 1)
                border.color: attentionState
                    ? (root.host ? root.host.portInteractiveBorderColor : portColor)
                    : (root.host && root.host.isFlowchartSurface && selectedState
                        ? root.host.selectedOutlineColor
                        : portColor)

                Rectangle {
                    objectName: "graphNodeInputPortRing"
                    anchors.centerIn: parent
                    visible: !root.host || !root.host.isFlowchartSurface || inputDot.attentionState
                    width: inputDot.ringDiameter
                    height: inputDot.ringDiameter
                    radius: width * 0.5
                    z: -1
                    color: inputDot.attentionState && root.host ? root.host.portInteractiveRingFillColor : "transparent"
                    border.width: inputDot.attentionState ? 1 : 0
                    border.color: inputDot.attentionState && root.host ? root.host.portInteractiveRingBorderColor : "transparent"
                }

                MouseArea {
                    id: inputPortMouse
                    objectName: "graphNodeInputPortMouseArea"
                    enabled: root.host ? !root.host.surfaceInteractionLocked : false
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

                    onPressed: function(mouse) {
                        if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                            return;
                        pressStartX = mouse.x;
                        pressStartY = mouse.y;
                        movedState = false;
                        var scenePos = root.host.portScenePos("in", rowIndex);
                        var pointerPos = root.host._pointerInCanvas(inputPortMouse, mouse);
                        root.host.portDragStarted(
                            root.host.nodeData.node_id,
                            modelData.key,
                            "in",
                            scenePos.x,
                            scenePos.y,
                            pointerPos.x,
                            pointerPos.y
                        );
                        mouse.accepted = true;
                    }

                    onPositionChanged: function(mouse) {
                        if (!root.host || !root.host.nodeData || !pressed)
                            return;
                        if (Math.abs(mouse.x - pressStartX) >= root.host._portDragThreshold
                            || Math.abs(mouse.y - pressStartY) >= root.host._portDragThreshold) {
                            movedState = true;
                        }
                        var scenePos = root.host.portScenePos("in", rowIndex);
                        var pointerPos = root.host._pointerInCanvas(inputPortMouse, mouse);
                        root.host.portDragMoved(
                            root.host.nodeData.node_id,
                            modelData.key,
                            "in",
                            scenePos.x,
                            scenePos.y,
                            pointerPos.x,
                            pointerPos.y,
                            movedState
                        );
                    }

                    onReleased: function(mouse) {
                        if (!root.host || !root.host.nodeData)
                            return;
                        var scenePos = root.host.portScenePos("in", rowIndex);
                        var pointerPos = root.host._pointerInCanvas(inputPortMouse, mouse);
                        root.host.portDragFinished(
                            root.host.nodeData.node_id,
                            modelData.key,
                            "in",
                            scenePos.x,
                            scenePos.y,
                            pointerPos.x,
                            pointerPos.y,
                            movedState
                        );
                        if (!movedState) {
                            root.host.portClicked(root.host.nodeData.node_id, modelData.key, "in", scenePos.x, scenePos.y);
                        }
                        movedState = false;
                    }

                    onCanceled: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        root.host.portDragCanceled(root.host.nodeData.node_id, modelData.key, "in");
                        movedState = false;
                    }

                    onEntered: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        var pos = root.host.portScenePos("in", rowIndex);
                        root.host.portHoverChanged(root.host.nodeData.node_id, modelData.key, "in", pos.x, pos.y, true);
                    }

                    onExited: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        var pos = root.host.portScenePos("in", rowIndex);
                        root.host.portHoverChanged(root.host.nodeData.node_id, modelData.key, "in", pos.x, pos.y, false);
                    }
                }
            }

            Text {
                objectName: "graphNodeInputPortLabel"
                property int effectiveRenderType: renderType
                readonly property real availableWidth: Math.max(0, (root.host ? root.host.width : 0) - x - 4)
                visible: root.host ? root.host._portLabelsVisible : true
                anchors.verticalCenter: parent.verticalCenter
                x: Math.max(0, inputDot.x + inputDot.width + (root.host ? root.host._portLabelGap : 6))
                width: root.host ? root.host.portLabelWidth(implicitWidth, availableWidth) : 0
                text: modelData.label || modelData.key
                color: root.host ? root.host.portLabelColor : "#d0d5de"
                font.pixelSize: 10
                elide: Text.ElideRight
                renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
            }
        }
    }

    Repeater {
        model: root.host ? root.host.outputPorts : []

        delegate: Item {
            property int rowIndex: index
            readonly property var portPoint: root.host
                ? root.host.localPortPoint("out", rowIndex)
                : ({"x": 0.0, "y": 0.0})
            readonly property real dotDiameter: outputDot.width
            x: 0
            y: portPoint.y - height * 0.5
            width: root.host ? root.host.width : 0
            height: Math.max(dotDiameter, 18)

            Rectangle {
                id: outputDot
                objectName: "graphNodeOutputPortDot"
                property bool hoveredState: root.host ? root.host.isHoveredPort("out", modelData.key) : false
                property bool pendingState: root.host ? root.host.isPendingPort("out", modelData.key) : false
                property bool dragSourceState: root.host ? root.host.isDragSourcePort("out", modelData.key) : false
                property bool selectedState: root.host ? (root.host.isFlowchartSurface && root.host.isSelected) : false
                property bool attentionState: hoveredState || pendingState || dragSourceState
                property bool interactiveState: attentionState || selectedState
                property bool connectedState: root.host ? root.host.isConnectedPort(modelData) : false
                property color portColor: root.host ? root.host.basePortColor(modelData.kind) : "#7AA8FF"
                property real restDiameter: root.host && root.host.isFlowchartSurface
                    ? (connectedState ? root.host.flowchartConnectedPortDiameter : root.host.flowchartRestPortDiameter)
                    : 8
                property real activeDiameter: root.host && root.host.isFlowchartSurface
                    ? (attentionState ? root.host.flowchartInteractivePortDiameter : root.host.flowchartSelectedPortDiameter)
                    : 14
                property real ringDiameter: root.host && root.host.isFlowchartSurface
                    ? root.host.flowchartInteractiveRingDiameter
                    : (attentionState ? 18 : 12)
                x: parent.portPoint.x - width * 0.5
                anchors.verticalCenter: parent.verticalCenter
                width: interactiveState ? activeDiameter : restDiameter
                height: width
                radius: width * 0.5
                color: root.host && root.host.isFlowchartSurface
                    ? (attentionState
                        ? root.host.portInteractiveFillColor
                        : ((selectedState || connectedState) ? root.host.flowchartConnectedPortFillColor : "transparent"))
                    : (interactiveState
                        ? (root.host ? root.host.portInteractiveFillColor : "#FFDA6B")
                        : (connectedState ? portColor : "transparent"))
                border.width: root.host && root.host.isFlowchartSurface ? (attentionState ? 1.8 : 1.1) : (interactiveState ? 2 : 1)
                border.color: attentionState
                    ? (root.host ? root.host.portInteractiveBorderColor : portColor)
                    : (root.host && root.host.isFlowchartSurface && selectedState
                        ? root.host.selectedOutlineColor
                        : portColor)

                Rectangle {
                    objectName: "graphNodeOutputPortRing"
                    anchors.centerIn: parent
                    visible: !root.host || !root.host.isFlowchartSurface || outputDot.attentionState
                    width: outputDot.ringDiameter
                    height: outputDot.ringDiameter
                    radius: width * 0.5
                    z: -1
                    color: outputDot.attentionState && root.host ? root.host.portInteractiveRingFillColor : "transparent"
                    border.width: outputDot.attentionState ? 1 : 0
                    border.color: outputDot.attentionState && root.host ? root.host.portInteractiveRingBorderColor : "transparent"
                }

                MouseArea {
                    id: outputPortMouse
                    objectName: "graphNodeOutputPortMouseArea"
                    enabled: root.host ? !root.host.surfaceInteractionLocked : false
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
                        var nextHover = !(root.host && root.host._isResizeHandlePoint(localX, localY));
                        if (hoverActive === nextHover)
                            return;
                        hoverActive = nextHover;
                        if (!root.host || !root.host.nodeData)
                            return;
                        var pos = root.host.portScenePos("out", rowIndex);
                        root.host.portHoverChanged(root.host.nodeData.node_id, modelData.key, "out", pos.x, pos.y, nextHover);
                    }

                    onPressed: function(mouse) {
                        if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                            return;
                        var localPoint = outputPortMouse.mapToItem(root.host, mouse.x, mouse.y);
                        if (root.host._isResizeHandlePoint(localPoint.x, localPoint.y)) {
                            mouse.accepted = false;
                            return;
                        }
                        pressStartX = mouse.x;
                        pressStartY = mouse.y;
                        movedState = false;
                        var scenePos = root.host.portScenePos("out", rowIndex);
                        var pointerPos = root.host._pointerInCanvas(outputPortMouse, mouse);
                        root.host.portDragStarted(
                            root.host.nodeData.node_id,
                            modelData.key,
                            "out",
                            scenePos.x,
                            scenePos.y,
                            pointerPos.x,
                            pointerPos.y
                        );
                        mouse.accepted = true;
                    }

                    onPositionChanged: function(mouse) {
                        if (!root.host)
                            return;
                        var localPoint = outputPortMouse.mapToItem(root.host, mouse.x, mouse.y);
                        updateHoverState(localPoint.x, localPoint.y);
                        if (!root.host.nodeData || !pressed)
                            return;
                        if (Math.abs(mouse.x - pressStartX) >= root.host._portDragThreshold
                            || Math.abs(mouse.y - pressStartY) >= root.host._portDragThreshold) {
                            movedState = true;
                        }
                        var scenePos = root.host.portScenePos("out", rowIndex);
                        var pointerPos = root.host._pointerInCanvas(outputPortMouse, mouse);
                        root.host.portDragMoved(
                            root.host.nodeData.node_id,
                            modelData.key,
                            "out",
                            scenePos.x,
                            scenePos.y,
                            pointerPos.x,
                            pointerPos.y,
                            movedState
                        );
                    }

                    onReleased: function(mouse) {
                        if (!root.host || !root.host.nodeData)
                            return;
                        var scenePos = root.host.portScenePos("out", rowIndex);
                        var pointerPos = root.host._pointerInCanvas(outputPortMouse, mouse);
                        root.host.portDragFinished(
                            root.host.nodeData.node_id,
                            modelData.key,
                            "out",
                            scenePos.x,
                            scenePos.y,
                            pointerPos.x,
                            pointerPos.y,
                            movedState
                        );
                        if (!movedState) {
                            root.host.portClicked(root.host.nodeData.node_id, modelData.key, "out", scenePos.x, scenePos.y);
                        }
                        movedState = false;
                    }

                    onCanceled: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        root.host.portDragCanceled(root.host.nodeData.node_id, modelData.key, "out");
                        movedState = false;
                    }

                    onEntered: {
                        if (!root.host)
                            return;
                        var localPoint = outputPortMouse.mapToItem(root.host, outputPortMouse.mouseX, outputPortMouse.mouseY);
                        updateHoverState(localPoint.x, localPoint.y);
                    }

                    onExited: {
                        if (!hoverActive || !root.host || !root.host.nodeData)
                            return;
                        hoverActive = false;
                        var pos = root.host.portScenePos("out", rowIndex);
                        root.host.portHoverChanged(root.host.nodeData.node_id, modelData.key, "out", pos.x, pos.y, false);
                    }
                }
            }

            Text {
                objectName: "graphNodeOutputPortLabel"
                property int effectiveRenderType: renderType
                readonly property real availableWidth: Math.max(0, outputDot.x - (root.host ? root.host._portLabelGap : 6) - 4)
                visible: root.host ? root.host._portLabelsVisible : true
                anchors.verticalCenter: parent.verticalCenter
                width: root.host ? root.host.portLabelWidth(implicitWidth, availableWidth) : 0
                x: Math.max(4, outputDot.x - (root.host ? root.host._portLabelGap : 6) - width)
                text: modelData.label || modelData.key
                color: root.host ? root.host.portLabelColor : "#d0d5de"
                font.pixelSize: 10
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideLeft
                renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
            }
        }
    }
}
