import QtQuick 2.15
import QtQuick.Controls 2.15
import "surface_controls" as SurfaceControls

Item {
    id: root
    objectName: "graphNodePortsLayer"
    property Item host: null
    property string editingPortKey: ""
    property string editingPortDirection: ""
    readonly property var graphSharedTypography: root.host ? root.host.graphSharedTypography : null
    z: 5

    function _isEditablePort(portData) {
        return portData.kind !== "exec" && portData.kind !== "completed" && portData.kind !== "failed";
    }

    function _isFlowEdgePort(portData) {
        var kind = String(portData && portData.kind || "").trim().toLowerCase();
        return kind === "flow" || kind === "exec" || kind === "completed" || kind === "failed";
    }

    function _flowEdgePortRevealActive(portData, attentionState, selectedState) {
        if (!(root.host && root.host.usesCardinalNeutralFlowHandles))
            return true;
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

    function _usesExecArrowLabel(portData) {
        var portKey = String(portData && portData.key || "").trim().toLowerCase();
        if (portKey !== "exec_in" && portKey !== "exec_out")
            return false;
        var normalizedLabel = root._portLabelText(portData).trim().toLowerCase().replace(/\s+/g, "_");
        return normalizedLabel === "exec_in" || normalizedLabel === "exec_out";
    }

    function _portDisplayText(portData) {
        if (root._usesExecArrowLabel(portData))
            return "\u27A1";
        return root._portLabelText(portData);
    }

    function _portDisplayColor(portData) {
        if (root._usesExecArrowLabel(portData))
            return root.host ? root.host.basePortColor(portData.kind) : "#67D487";
        return root.host ? root.host.portLabelColor : "#d0d5de";
    }

    function _portDisplayPixelSize(portData) {
        if (root._usesExecArrowLabel(portData))
            return root.graphSharedTypography ? root.graphSharedTypography.execArrowPortPixelSize : 18;
        return root.graphSharedTypography ? root.graphSharedTypography.portLabelPixelSize : 10;
    }

    function _portDisplayFontWeight(portData) {
        if (root._usesExecArrowLabel(portData))
            return root.graphSharedTypography ? root.graphSharedTypography.execArrowPortFontWeight : Font.Black;
        return root.graphSharedTypography ? root.graphSharedTypography.portLabelFontWeight : Font.Normal;
    }

    function _portInactive(portData) {
        return !!(portData && portData.inactive);
    }

    function _portKey(portData) {
        return String(portData && portData.key || "");
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
            id: inputPortRow
            objectName: "graphNodeInputPortRow"
            property int rowIndex: index
            property string propertyKey: root._portKey(modelData)
            readonly property string interactionDirection: root._interactionDirection(modelData, "in")
            readonly property bool lockableState: Boolean(modelData && modelData.lockable)
            readonly property bool lockedState: lockableState && Boolean(modelData && modelData.locked)
            readonly property var portPoint: root.host
                ? root.host.localPortPoint("in", rowIndex)
                : ({"x": 0.0, "y": 0.0})
            readonly property real dotDiameter: inputDot.width
            x: 0
            y: portPoint.y - height * 0.5
            width: root.host ? root.host.width : 0
            height: Math.max(dotDiameter, 18)

            Rectangle {
                objectName: "graphNodeInputPortLockedRowTint"
                property string propertyKey: inputPortRow.propertyKey
                visible: inputPortRow.lockedState
                anchors.fill: parent
                anchors.leftMargin: 1
                anchors.rightMargin: 1
                radius: Math.min(5, height * 0.5)
                color: Qt.rgba(1.0, 0.84, 0.45, 0.08)
                border.width: 1
                border.color: Qt.rgba(1.0, 0.84, 0.45, 0.22)
                z: -2
            }

            Rectangle {
                id: inputDot
                objectName: "graphNodeInputPortDot"
                property string propertyKey: inputPortRow.propertyKey
                readonly property string interactionDirection: parent.interactionDirection
                readonly property bool inactiveState: root._portInactive(modelData)
                property bool lockableState: inputPortRow.lockableState
                property bool lockedState: inputPortRow.lockedState
                property bool interactionBlockedState: inactiveState || lockedState
                property bool hoveredState: !interactionBlockedState && root.host ? root.host.isHoveredPort(parent.interactionDirection, modelData.key) : false
                property bool pendingState: !interactionBlockedState && root.host ? root.host.isPendingPort(parent.interactionDirection, modelData.key) : false
                property bool dragSourceState: !interactionBlockedState && root.host ? root.host.isDragSourcePort(parent.interactionDirection, modelData.key) : false
                property bool selectedState: root.host ? (root.host.usesCardinalNeutralFlowHandles && root.host.isSelected) : false
                property bool attentionState: hoveredState || pendingState || dragSourceState
                property bool interactiveState: !interactionBlockedState && (attentionState || selectedState)
                property bool revealState: root._flowEdgePortRevealActive(modelData, attentionState, selectedState)
                property bool connectedState: root.host ? root.host.isConnectedPort(modelData) : false
                property color portColor: root.host ? root.host.basePortColor(modelData.kind) : "#7AA8FF"
                property real lockedDiameter: 12
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
                width: lockedState ? lockedDiameter : (interactiveState ? activeDiameter : restDiameter)
                height: width
                radius: lockedState ? 0 : width * 0.5
                opacity: lockedState ? 1.0 : (revealState ? (interactionBlockedState ? 0.72 : (inactiveState ? 0.46 : 1.0)) : 0.0)
                color: lockedState
                    ? "transparent"
                    : (root.host && root.host.usesCardinalNeutralFlowHandles
                    ? (attentionState
                        ? root.host.portInteractiveFillColor
                        : ((selectedState || connectedState) ? root.host.flowchartConnectedPortFillColor : "transparent"))
                    : (interactiveState
                        ? (root.host ? root.host.portInteractiveFillColor : "#FFDA6B")
                        : (connectedState ? portColor : "transparent")))
                border.width: lockedState
                    ? 0
                    : (root.host && root.host.usesCardinalNeutralFlowHandles ? (attentionState ? 1.8 : 1.1) : (interactiveState ? 2 : 1))
                border.color: lockedState
                    ? "transparent"
                    : (attentionState
                    ? (root.host ? root.host.portInteractiveBorderColor : portColor)
                    : (root.host && root.host.usesCardinalNeutralFlowHandles && selectedState
                        ? root.host.selectedOutlineColor
                        : portColor))

                Rectangle {
                    objectName: "graphNodeInputPortRing"
                    property string propertyKey: inputPortRow.propertyKey
                    anchors.centerIn: parent
                    visible: (!root.host || !root.host.usesCardinalNeutralFlowHandles || inputDot.attentionState)
                        && !inputDot.lockedState
                    width: inputDot.ringDiameter
                    height: inputDot.ringDiameter
                    radius: width * 0.5
                    z: -1
                    color: inputDot.attentionState && root.host ? root.host.portInteractiveRingFillColor : "transparent"
                    border.width: inputDot.attentionState ? 1 : 0
                    border.color: inputDot.attentionState && root.host ? root.host.portInteractiveRingBorderColor : "transparent"
                }

                Rectangle {
                    objectName: "graphNodeInputPortInactiveSlash"
                    property string propertyKey: inputPortRow.propertyKey
                    visible: inputDot.inactiveState && inputDot.width > 0 && inputDot.height > 0
                    anchors.centerIn: parent
                    width: Math.max(6, inputDot.width + 1)
                    height: 1.6
                    radius: height * 0.5
                    rotation: -35
                    color: root.host ? root.host.outlineColor : "#95a0b8"
                    opacity: 0.9
                }

                MouseArea {
                    id: inputPortMouse
                    objectName: "graphNodeInputPortMouseArea"
                    property string propertyKey: inputPortRow.propertyKey
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
                    cursorShape: inputDot.interactionBlockedState ? Qt.ForbiddenCursor : Qt.PointingHandCursor
                    property bool tooltipOnlyPortLabelActive: root.host ? root.host._tooltipOnlyPortLabelsActive : false
                    property string portLabelTooltipText: root._portLabelText(modelData)
                    property string inactiveTooltipText: String(modelData && modelData.inactive_reason || "")
                    property bool tooltipVisible: tooltipOnlyPortLabelActive
                        && containsMouse
                        && portLabelTooltipText.length > 0
                    property bool inactiveTooltipVisible: containsMouse
                        && inputDot.inactiveState
                        && inactiveTooltipText.length > 0

                    ToolTip.visible: tooltipVisible || inactiveTooltipVisible
                    ToolTip.text: inactiveTooltipVisible ? inactiveTooltipText : portLabelTooltipText
                    ToolTip.delay: 400

                    onPressed: function(mouse) {
                        if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                            return;
                        if (inputDot.interactionBlockedState)
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
                        if (!root.host || !root.host.nodeData || !pressed || inputDot.interactionBlockedState)
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
                        if (!root.host || !root.host.nodeData || inputDot.interactionBlockedState)
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

                    onDoubleClicked: function(mouse) {
                        if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                            return;
                        if (!inputDot.lockableState || inputDot.inactiveState)
                            return;
                        root.host.portDoubleClicked(
                            root.host.nodeData.node_id,
                            modelData.key,
                            inputDot.interactionDirection,
                            inputDot.lockedState
                        );
                        mouse.accepted = true;
                    }

                    onCanceled: {
                        if (!root.host || !root.host.nodeData)
                            return;
                        root.host.portDragCanceled(root.host.nodeData.node_id, modelData.key, inputDot.interactionDirection);
                        movedState = false;
                    }

                    onEntered: {
                        if (!root.host || !root.host.nodeData || inputDot.interactionBlockedState)
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
                        if (!root.host || !root.host.nodeData || inputDot.interactionBlockedState)
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
                property string propertyKey: inputPortRow.propertyKey
                readonly property bool isEditing: root.editingPortKey === modelData.key && root.editingPortDirection === "in"
                readonly property bool isEditable: root._isEditablePort(modelData)
                    && !root._portInactive(modelData)
                    && (root.host ? root.host._portLabelsVisible : true)
                readonly property bool lockableState: inputPortRow.lockableState
                readonly property bool lockedState: inputPortRow.lockedState
                readonly property bool labelTextVisible: root.host ? root.host._portLabelsVisible : true
                readonly property real lockGlyphWidth: 0
                readonly property real lockGlyphGap: 0
                readonly property real textLeftInset: 0
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
                visible: root.host ? (root.host._portLabelsVisible || lockedState) : true
                anchors.verticalCenter: parent.verticalCenter
                x: labelX
                width: availableWidth
                height: Math.max(inputLabelText.implicitHeight, 18)

                Canvas {
                    id: lockGlyph
                    objectName: "graphNodeInputPortPadlock"
                    property string propertyKey: inputLabelContainer.propertyKey
                    readonly property bool lockedState: inputLabelContainer.lockedState
                    parent: inputLabelContainer.lockedState ? inputDot : inputLabelContainer
                    visible: inputLabelContainer.lockedState
                    x: inputLabelContainer.lockedState ? Math.round((parent.width - width) * 0.5) : 0
                    y: Math.round((parent.height - height) * 0.5)
                    width: 10
                    height: 12
                    implicitHeight: height
                    antialiasing: true
                    opacity: lockedState ? 0.96 : 0.42
                    z: 2

                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.clearRect(0, 0, width, height);
                        if (!visible || width <= 0 || height <= 0)
                            return;
                        var accentStrokeAlpha = lockedState ? 1.0 : 0.68;
                        var accentFillAlpha = lockedState ? 0.38 : 0.18;
                        var outlineAlpha = lockedState ? 0.92 : 0.58;
                        var outlineStroke = Qt.rgba(0.10, 0.07, 0.03, outlineAlpha);
                        var accentStroke = Qt.rgba(1.0, 0.82, 0.34, accentStrokeAlpha);
                        var accentFill = Qt.rgba(1.0, 0.88, 0.52, accentFillAlpha);

                        function drawShackle(strokeStyle, lineWidth) {
                            ctx.beginPath();
                            ctx.lineWidth = lineWidth;
                            ctx.strokeStyle = strokeStyle;
                            ctx.arc(width * 0.5, 4.0, 2.6, Math.PI, 0, false);
                            ctx.stroke();
                        }

                        var bodyX = Math.round((width - 8) * 0.5);
                        var bodyY = 5.0;
                        var bodyWidth = 8.0;
                        var bodyHeight = 6.0;
                        var radius = 1.8;
                        function drawBody(strokeStyle, fillStyle, lineWidth) {
                            ctx.beginPath();
                            ctx.lineWidth = lineWidth;
                            ctx.strokeStyle = strokeStyle;
                            ctx.fillStyle = fillStyle;
                            ctx.moveTo(bodyX + radius, bodyY);
                            ctx.lineTo(bodyX + bodyWidth - radius, bodyY);
                            ctx.quadraticCurveTo(bodyX + bodyWidth, bodyY, bodyX + bodyWidth, bodyY + radius);
                            ctx.lineTo(bodyX + bodyWidth, bodyY + bodyHeight - radius);
                            ctx.quadraticCurveTo(
                                bodyX + bodyWidth,
                                bodyY + bodyHeight,
                                bodyX + bodyWidth - radius,
                                bodyY + bodyHeight
                            );
                            ctx.lineTo(bodyX + radius, bodyY + bodyHeight);
                            ctx.quadraticCurveTo(bodyX, bodyY + bodyHeight, bodyX, bodyY + bodyHeight - radius);
                            ctx.lineTo(bodyX, bodyY + radius);
                            ctx.quadraticCurveTo(bodyX, bodyY, bodyX + radius, bodyY);
                            ctx.fill();
                            ctx.stroke();
                        }

                        drawShackle(outlineStroke, 2.6);
                        drawBody(outlineStroke, Qt.rgba(0.0, 0.0, 0.0, 0.0), 2.6);
                        drawShackle(accentStroke, 1.2);
                        drawBody(accentStroke, accentFill, 1.2);
                    }

                    Component.onCompleted: requestPaint()
                    onVisibleChanged: requestPaint()
                    onLockedStateChanged: requestPaint()
                }

                MouseArea {
                    id: inputLockToggleMouse
                    objectName: "graphNodeInputPortLockToggleMouseArea"
                    property string propertyKey: inputLabelContainer.propertyKey
                    property string nodeId: root.host && root.host.nodeData
                        ? String(root.host.nodeData.node_id || "")
                        : ""
                    property string portDirection: inputPortRow.interactionDirection
                    property bool lockedState: inputLabelContainer.lockedState
                    property Item hostItem: root.host
                    parent: inputLabelContainer.lockedState ? inputDot : inputLabelContainer
                    visible: inputLabelContainer.lockedState
                    x: lockGlyph.x
                    y: lockGlyph.y
                    width: lockGlyph.width
                    height: lockGlyph.height
                    acceptedButtons: Qt.LeftButton
                    hoverEnabled: true
                    preventStealing: true
                    cursorShape: Qt.PointingHandCursor
                    z: 3

                    onClicked: function(mouse) {
                        mouse.accepted = true;
                    }

                    onDoubleClicked: function(mouse) {
                        if (mouse.button !== Qt.LeftButton)
                            return;
                        if (!root.host || !root.host.nodeData)
                            return;
                        root.host.portDoubleClicked(
                            root.host.nodeData.node_id,
                            modelData.key,
                            inputPortRow.interactionDirection,
                            inputLabelContainer.lockedState
                        );
                        mouse.accepted = true;
                    }
                }

                Text {
                    id: inputLabelText
                    objectName: "graphNodeInputPortLabel"
                    property string propertyKey: inputLabelContainer.propertyKey
                    property int effectiveRenderType: renderType
                    visible: inputLabelContainer.labelTextVisible && !inputLabelContainer.isEditing
                    anchors.verticalCenter: parent.verticalCenter
                    x: inputLabelContainer.textLeftInset
                    width: root.host
                        ? root.host.portLabelWidth(
                            implicitWidth,
                            Math.max(0, inputLabelContainer.availableWidth - inputLabelContainer.textLeftInset)
                        )
                        : 0
                    text: root._portDisplayText(modelData)
                    color: root._portDisplayColor(modelData)
                    font.pixelSize: root._portDisplayPixelSize(modelData)
                    font.weight: root._portDisplayFontWeight(modelData)
                    elide: Text.ElideRight
                    renderType: root.host ? root.host.nodeTextRenderType : Text.CurveRendering
                    opacity: root._portInactive(modelData) ? 0.52 : (inputLabelContainer.lockedState ? 0.58 : 1.0)

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
                    visible: inputLabelContainer.labelTextVisible
                        && inputLabelContainer.isEditable
                        && !inputLabelContainer.isEditing
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
                    text: root._portDisplayText(modelData)
                    color: root._portDisplayColor(modelData)
                    font.pixelSize: root._portDisplayPixelSize(modelData)
                    font.weight: root._portDisplayFontWeight(modelData)
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
