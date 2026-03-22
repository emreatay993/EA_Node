import QtQuick 2.15
import QtQuick.Controls 2.15
import "surface_controls" as SurfaceControls

Item {
    id: root
    objectName: "graphNodePortsLayer"
    property Item host: null
    property string editingPortKey: ""
    property string editingPortDirection: ""
    z: 5

    function _isEditablePort(portData) {
        return portData.kind !== "exec" && portData.kind !== "completed" && portData.kind !== "failed";
    }

    function _isFlowEdgePort(portData) {
        var kind = String(portData && portData.kind || "").trim().toLowerCase();
        return kind === "flow" || kind === "exec" || kind === "completed" || kind === "failed";
    }

    function _flowEdgePortRevealActive(portData, attentionState, selectedState) {
        if (!root._isFlowEdgePort(portData))
            return true;
        return Boolean(attentionState)
            || Boolean(selectedState)
            || (root.host ? Boolean(root.host.hoverActive) : false);
    }

    function _interactionDirection(portData, fallbackDirection) {
        var direction = String(portData && portData.direction || "").trim().toLowerCase();
        if (direction === "in" || direction === "out" || direction === "neutral")
            return direction;
        return String(fallbackDirection || "").trim().toLowerCase();
    }

    function _portLabelText(portData) {
        return String(portData && (portData.label || portData.key) || "");
    }

    function beginPortLabelEdit(portKey, direction) {
        root.editingPortKey = portKey;
        root.editingPortDirection = direction;
    }

    function cancelPortLabelEdit() {
        root.editingPortKey = "";
        root.editingPortDirection = "";
    }

    function commitPortLabelEdit(portKey, label) {
        if (root.editingPortKey !== portKey)
            return;
        root.editingPortKey = "";
        root.editingPortDirection = "";
        if (!root.host || !root.host.nodeData)
            return;
        var nodeId = root.host.nodeData.node_id;
        var hostRef = root.host;
        Qt.callLater(function() {
            if (hostRef)
                hostRef.portLabelCommitted(nodeId, portKey, label);
        });
    }
    visible: root.host && root.host.nodeData ? !root.host.nodeData.collapsed : false

    Repeater {
        model: root.host ? root.host.inputPorts : []

        delegate: Item {
            property int rowIndex: index
            readonly property string interactionDirection: root._interactionDirection(modelData, "in")
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
                readonly property string interactionDirection: parent.interactionDirection
                property bool hoveredState: root.host ? root.host.isHoveredPort(parent.interactionDirection, modelData.key) : false
                property bool pendingState: root.host ? root.host.isPendingPort(parent.interactionDirection, modelData.key) : false
                property bool dragSourceState: root.host ? root.host.isDragSourcePort(parent.interactionDirection, modelData.key) : false
                property bool selectedState: root.host ? (root.host.usesCardinalNeutralFlowHandles && root.host.isSelected) : false
                property bool attentionState: hoveredState || pendingState || dragSourceState
                property bool interactiveState: attentionState || selectedState
                property bool revealState: root._flowEdgePortRevealActive(modelData, attentionState, selectedState)
                property bool connectedState: root.host ? root.host.isConnectedPort(modelData) : false
                property color portColor: root.host ? root.host.basePortColor(modelData.kind) : "#7AA8FF"
                property real restDiameter: root.host && root.host.usesCardinalNeutralFlowHandles
                    ? (connectedState ? root.host.flowchartConnectedPortDiameter : root.host.flowchartRestPortDiameter)
                    : 8
                property real activeDiameter: root.host && root.host.usesCardinalNeutralFlowHandles
                    ? (attentionState ? root.host.flowchartInteractivePortDiameter : root.host.flowchartSelectedPortDiameter)
                    : 14
                property real ringDiameter: root.host && root.host.usesCardinalNeutralFlowHandles
                    ? root.host.flowchartInteractiveRingDiameter
                    : (attentionState ? 18 : 12)
                x: parent.portPoint.x - width * 0.5
                anchors.verticalCenter: parent.verticalCenter
                width: interactiveState ? activeDiameter : restDiameter
                height: width
                radius: width * 0.5
                opacity: revealState ? 1.0 : 0.0
                color: root.host && root.host.usesCardinalNeutralFlowHandles
                    ? (attentionState
                        ? root.host.portInteractiveFillColor
                        : ((selectedState || connectedState) ? root.host.flowchartConnectedPortFillColor : "transparent"))
                    : (interactiveState
                        ? (root.host ? root.host.portInteractiveFillColor : "#FFDA6B")
                        : (connectedState ? portColor : "transparent"))
                border.width: root.host && root.host.usesCardinalNeutralFlowHandles ? (attentionState ? 1.8 : 1.1) : (interactiveState ? 2 : 1)
                border.color: attentionState
                    ? (root.host ? root.host.portInteractiveBorderColor : portColor)
                    : (root.host && root.host.usesCardinalNeutralFlowHandles && selectedState
                        ? root.host.selectedOutlineColor
                        : portColor)

                Rectangle {
                    objectName: "graphNodeInputPortRing"
                    anchors.centerIn: parent
                    visible: !root.host || !root.host.usesCardinalNeutralFlowHandles || inputDot.attentionState
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
                    property bool tooltipOnlyPortLabelActive: root.host ? root.host._tooltipOnlyPortLabelsActive : false
                    property string portLabelTooltipText: root._portLabelText(modelData)
                    property bool tooltipVisible: tooltipOnlyPortLabelActive
                        && containsMouse
                        && portLabelTooltipText.length > 0

                    ToolTip.visible: tooltipVisible
                    ToolTip.text: portLabelTooltipText
                    ToolTip.delay: 400

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
                            inputDot.interactionDirection,
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
                            inputDot.interactionDirection,
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
                            inputDot.interactionDirection,
                            scenePos.x,
                            scenePos.y,
                            pointerPos.x,
                            pointerPos.y,
                            movedState
                        );
                        if (!movedState) {
                            root.host.portClicked(
                                root.host.nodeData.node_id,
                                modelData.key,
                                inputDot.interactionDirection,
                                scenePos.x,
                                scenePos.y
                            );
                        }
                        movedState = false;
                    }

                    onCanceled: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        root.host.portDragCanceled(root.host.nodeData.node_id, modelData.key, inputDot.interactionDirection);
                        movedState = false;
                    }

                    onEntered: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        var pos = root.host.portScenePos("in", rowIndex);
                        root.host.portHoverChanged(
                            root.host.nodeData.node_id,
                            modelData.key,
                            inputDot.interactionDirection,
                            pos.x,
                            pos.y,
                            true
                        );
                    }

                    onExited: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        var pos = root.host.portScenePos("in", rowIndex);
                        root.host.portHoverChanged(
                            root.host.nodeData.node_id,
                            modelData.key,
                            inputDot.interactionDirection,
                            pos.x,
                            pos.y,
                            false
                        );
                    }
                }
            }

            Item {
                id: inputLabelContainer
                readonly property bool isEditing: root.editingPortKey === modelData.key && root.editingPortDirection === "in"
                readonly property bool isEditable: root._isEditablePort(modelData) && (root.host ? root.host._portLabelsVisible : true)
                readonly property bool standardColumnsActive: root.host ? root.host._usesStandardPortLabelColumns : false
                readonly property real labelX: Math.max(0, inputDot.x + inputDot.width + (root.host ? root.host._portLabelGap : 6))
                readonly property real rawAvailableWidth: Math.max(0, (root.host ? root.host.width : 0) - labelX - 4)
                readonly property real standardAvailableWidth: standardColumnsActive && root.host
                    ? Math.max(
                        0,
                        Math.min(
                            root.host._standardLeftLabelWidth,
                            (root.host.width - root.host._standardPortGutter - root.host._standardCenterGap)
                                - labelX
                                - root.host._standardRightLabelWidth
                        )
                    )
                    : 0.0
                readonly property real availableWidth: standardColumnsActive ? standardAvailableWidth : rawAvailableWidth
                visible: root.host ? root.host._portLabelsVisible : true
                anchors.verticalCenter: parent.verticalCenter
                x: labelX
                width: availableWidth
                height: Math.max(inputLabelText.implicitHeight, 18)

                Text {
                    id: inputLabelText
                    objectName: "graphNodeInputPortLabel"
                    property int effectiveRenderType: renderType
                    visible: !inputLabelContainer.isEditing
                    anchors.verticalCenter: parent.verticalCenter
                    width: root.host ? root.host.portLabelWidth(implicitWidth, inputLabelContainer.availableWidth) : 0
                    text: modelData.label || modelData.key
                    color: root.host ? root.host.portLabelColor : "#d0d5de"
                    font.pixelSize: 10
                    elide: Text.ElideRight
                    renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering

                    Rectangle {
                        visible: inputLabelMouse.containsMouse && inputLabelContainer.isEditable
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: root.host ? root.host.portLabelColor : "#d0d5de"
                        opacity: 0.5
                    }
                }

                MouseArea {
                    id: inputLabelMouse
                    anchors.fill: inputLabelText
                    visible: inputLabelContainer.isEditable && !inputLabelContainer.isEditing
                    hoverEnabled: true
                    cursorShape: containsMouse ? Qt.IBeamCursor : Qt.ArrowCursor
                    acceptedButtons: Qt.LeftButton
                    onClicked: {
                        root.beginPortLabelEdit(modelData.key, "in");
                    }
                }

                SurfaceControls.GraphSurfaceTextField {
                    id: inputLabelEditor
                    visible: inputLabelContainer.isEditing
                    host: root.host
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(Math.max(60, inputLabelText.implicitWidth + 16), inputLabelContainer.availableWidth)
                    height: 20
                    font.pixelSize: 10
                    topPadding: 2
                    bottomPadding: 2
                    leftPadding: 4
                    rightPadding: 4

                    onVisibleChanged: {
                        if (visible) {
                            text = modelData.label || modelData.key;
                            forceActiveFocus();
                            selectAll();
                        }
                    }

                    onAccepted: {
                        root.commitPortLabelEdit(modelData.key, text);
                    }

                    onActiveFocusChanged: {
                        if (!activeFocus && inputLabelContainer.isEditing) {
                            root.commitPortLabelEdit(modelData.key, text);
                        }
                    }

                    Keys.onEscapePressed: {
                        root.cancelPortLabelEdit();
                    }

                    onControlStarted: {
                        if (root.host && root.host.nodeData)
                            root.host.surfaceControlInteractionStarted(root.host.nodeData.node_id);
                    }
                }
            }
        }
    }

    Repeater {
        model: root.host ? root.host.outputPorts : []

        delegate: Item {
            property int rowIndex: index
            readonly property string interactionDirection: root._interactionDirection(modelData, "out")
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
                readonly property string interactionDirection: parent.interactionDirection
                property bool hoveredState: root.host ? root.host.isHoveredPort(parent.interactionDirection, modelData.key) : false
                property bool pendingState: root.host ? root.host.isPendingPort(parent.interactionDirection, modelData.key) : false
                property bool dragSourceState: root.host ? root.host.isDragSourcePort(parent.interactionDirection, modelData.key) : false
                property bool selectedState: root.host ? (root.host.usesCardinalNeutralFlowHandles && root.host.isSelected) : false
                property bool attentionState: hoveredState || pendingState || dragSourceState
                property bool interactiveState: attentionState || selectedState
                property bool revealState: root._flowEdgePortRevealActive(modelData, attentionState, selectedState)
                property bool connectedState: root.host ? root.host.isConnectedPort(modelData) : false
                property color portColor: root.host ? root.host.basePortColor(modelData.kind) : "#7AA8FF"
                property real restDiameter: root.host && root.host.usesCardinalNeutralFlowHandles
                    ? (connectedState ? root.host.flowchartConnectedPortDiameter : root.host.flowchartRestPortDiameter)
                    : 8
                property real activeDiameter: root.host && root.host.usesCardinalNeutralFlowHandles
                    ? (attentionState ? root.host.flowchartInteractivePortDiameter : root.host.flowchartSelectedPortDiameter)
                    : 14
                property real ringDiameter: root.host && root.host.usesCardinalNeutralFlowHandles
                    ? root.host.flowchartInteractiveRingDiameter
                    : (attentionState ? 18 : 12)
                x: parent.portPoint.x - width * 0.5
                anchors.verticalCenter: parent.verticalCenter
                width: interactiveState ? activeDiameter : restDiameter
                height: width
                radius: width * 0.5
                opacity: revealState ? 1.0 : 0.0
                color: root.host && root.host.usesCardinalNeutralFlowHandles
                    ? (attentionState
                        ? root.host.portInteractiveFillColor
                        : ((selectedState || connectedState) ? root.host.flowchartConnectedPortFillColor : "transparent"))
                    : (interactiveState
                        ? (root.host ? root.host.portInteractiveFillColor : "#FFDA6B")
                        : (connectedState ? portColor : "transparent"))
                border.width: root.host && root.host.usesCardinalNeutralFlowHandles ? (attentionState ? 1.8 : 1.1) : (interactiveState ? 2 : 1)
                border.color: attentionState
                    ? (root.host ? root.host.portInteractiveBorderColor : portColor)
                    : (root.host && root.host.usesCardinalNeutralFlowHandles && selectedState
                        ? root.host.selectedOutlineColor
                        : portColor)

                Rectangle {
                    objectName: "graphNodeOutputPortRing"
                    anchors.centerIn: parent
                    visible: !root.host || !root.host.usesCardinalNeutralFlowHandles || outputDot.attentionState
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
                    property bool tooltipOnlyPortLabelActive: root.host ? root.host._tooltipOnlyPortLabelsActive : false
                    property string portLabelTooltipText: root._portLabelText(modelData)
                    property bool tooltipVisible: tooltipOnlyPortLabelActive
                        && hoverActive
                        && portLabelTooltipText.length > 0

                    ToolTip.visible: tooltipVisible
                    ToolTip.text: portLabelTooltipText
                    ToolTip.delay: 400

                    function updateHoverState(localX, localY) {
                        var nextHover = !(root.host && root.host._isResizeHandlePoint(localX, localY));
                        if (hoverActive === nextHover)
                            return;
                        hoverActive = nextHover;
                        if (!root.host || !root.host.nodeData)
                            return;
                        var pos = root.host.portScenePos("out", rowIndex);
                        root.host.portHoverChanged(
                            root.host.nodeData.node_id,
                            modelData.key,
                            outputDot.interactionDirection,
                            pos.x,
                            pos.y,
                            nextHover
                        );
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
                            outputDot.interactionDirection,
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
                            outputDot.interactionDirection,
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
                            outputDot.interactionDirection,
                            scenePos.x,
                            scenePos.y,
                            pointerPos.x,
                            pointerPos.y,
                            movedState
                        );
                        if (!movedState) {
                            root.host.portClicked(
                                root.host.nodeData.node_id,
                                modelData.key,
                                outputDot.interactionDirection,
                                scenePos.x,
                                scenePos.y
                            );
                        }
                        movedState = false;
                    }

                    onCanceled: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        root.host.portDragCanceled(root.host.nodeData.node_id, modelData.key, outputDot.interactionDirection);
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
                        root.host.portHoverChanged(
                            root.host.nodeData.node_id,
                            modelData.key,
                            outputDot.interactionDirection,
                            pos.x,
                            pos.y,
                            false
                        );
                    }
                }
            }

            Item {
                id: outputLabelContainer
                readonly property bool isEditing: root.editingPortKey === modelData.key && root.editingPortDirection === "out"
                readonly property bool isEditable: root._isEditablePort(modelData) && (root.host ? root.host._portLabelsVisible : true)
                readonly property bool standardColumnsActive: root.host ? root.host._usesStandardPortLabelColumns : false
                readonly property real rawAvailableWidth: Math.max(0, outputDot.x - (root.host ? root.host._portLabelGap : 6) - 4)
                readonly property real standardAvailableWidth: standardColumnsActive && root.host
                    ? Math.max(
                        0,
                        Math.min(
                            root.host._standardRightLabelWidth,
                            (outputDot.x - (root.host ? root.host._portLabelGap : 6))
                                - (
                                    root.host._standardPortGutter
                                    + root.host._standardLeftLabelWidth
                                    + root.host._standardCenterGap
                                )
                        )
                    )
                    : 0.0
                readonly property real availableWidth: standardColumnsActive ? standardAvailableWidth : rawAvailableWidth
                visible: root.host ? root.host._portLabelsVisible : true
                anchors.verticalCenter: parent.verticalCenter
                width: availableWidth
                height: Math.max(outputLabelText.implicitHeight, 18)
                x: standardColumnsActive && root.host
                    ? Math.max(0, outputDot.x - (root.host ? root.host._portLabelGap : 6) - availableWidth)
                    : 4

                Text {
                    id: outputLabelText
                    objectName: "graphNodeOutputPortLabel"
                    property int effectiveRenderType: renderType
                    visible: !outputLabelContainer.isEditing
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    width: root.host ? root.host.portLabelWidth(implicitWidth, outputLabelContainer.availableWidth) : 0
                    text: modelData.label || modelData.key
                    color: root.host ? root.host.portLabelColor : "#d0d5de"
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignRight
                    elide: Text.ElideLeft
                    renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering

                    Rectangle {
                        visible: outputLabelMouse.containsMouse && outputLabelContainer.isEditable
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: root.host ? root.host.portLabelColor : "#d0d5de"
                        opacity: 0.5
                    }
                }

                MouseArea {
                    id: outputLabelMouse
                    anchors.fill: outputLabelText
                    visible: outputLabelContainer.isEditable && !outputLabelContainer.isEditing
                    hoverEnabled: true
                    cursorShape: containsMouse ? Qt.IBeamCursor : Qt.ArrowCursor
                    acceptedButtons: Qt.LeftButton
                    onClicked: {
                        root.beginPortLabelEdit(modelData.key, "out");
                    }
                }

                SurfaceControls.GraphSurfaceTextField {
                    id: outputLabelEditor
                    visible: outputLabelContainer.isEditing
                    host: root.host
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.right: parent.right
                    width: Math.min(Math.max(60, outputLabelText.implicitWidth + 16), outputLabelContainer.availableWidth)
                    height: 20
                    font.pixelSize: 10
                    topPadding: 2
                    bottomPadding: 2
                    leftPadding: 4
                    rightPadding: 4
                    horizontalAlignment: TextInput.AlignRight

                    onVisibleChanged: {
                        if (visible) {
                            text = modelData.label || modelData.key;
                            forceActiveFocus();
                            selectAll();
                        }
                    }

                    onAccepted: {
                        root.commitPortLabelEdit(modelData.key, text);
                    }

                    onActiveFocusChanged: {
                        if (!activeFocus && outputLabelContainer.isEditing) {
                            root.commitPortLabelEdit(modelData.key, text);
                        }
                    }

                    Keys.onEscapePressed: {
                        root.cancelPortLabelEdit();
                    }

                    onControlStarted: {
                        if (root.host && root.host.nodeData)
                            root.host.surfaceControlInteractionStarted(root.host.nodeData.node_id);
                    }
                }
            }
        }
    }
}
