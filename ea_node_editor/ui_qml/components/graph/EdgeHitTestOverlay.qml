import QtQuick 2.15
import QtQuick.Controls 2.15
import "../common" as Common

Item {
    id: root
    property Item edgeLayer: null
    property bool inputEnabled: true
    property bool wireSelectionModeHeld: false
    property string hoveredEdgeId: ""
    property string hoveredLabelEdgeId: ""
    property real hoverX: 0.0
    property real hoverY: 0.0
    property string labelPressEdgeId: ""
    property real labelPressX: 0.0
    property real labelPressY: 0.0
    property bool labelDragActive: false
    readonly property real labelDragThresholdPx: 4.0
    readonly property string hoveredEdgeTooltipText: root.edgeLayer && root.edgeLayer.edgeTooltipText
        ? root.edgeLayer.edgeTooltipText(root.hoveredEdgeId)
        : ""

    onWireSelectionModeHeldChanged: {
        if (root.wireSelectionModeHeld) {
            root.hoveredEdgeId = "";
            root.hoveredLabelEdgeId = "";
        }
    }

    signal edgeClicked(string edgeId, bool additive)
    signal edgeDoubleClicked(string edgeId)
    signal edgeContextRequested(string edgeId, real screenX, real screenY)
    signal flowLabelDragFinished(string edgeId, real fraction)

    function _labelEdgeAt(screenX, screenY) {
        return root.edgeLayer && root.edgeLayer.flowLabelEdgeAtScreen
            ? String(root.edgeLayer.flowLabelEdgeAtScreen(screenX, screenY) || "")
            : "";
    }

    // Flow labels sit on top of their wires, so a label hit wins over the path pick.
    function _edgeAt(screenX, screenY) {
        var labelEdgeId = root._labelEdgeAt(screenX, screenY);
        if (labelEdgeId.length)
            return labelEdgeId;
        return root.edgeLayer && root.edgeLayer.edgeAtScreen
            ? String(root.edgeLayer.edgeAtScreen(screenX, screenY) || "")
            : "";
    }

    function _resetLabelDrag(clearPreview) {
        var wasActive = root.labelDragActive;
        root.labelPressEdgeId = "";
        root.labelDragActive = false;
        if (clearPreview && wasActive && root.edgeLayer && root.edgeLayer.clearFlowLabelDragPreview)
            root.edgeLayer.clearFlowLabelDragPreview();
    }

    MouseArea {
        id: edgeHitMouse
        anchors.fill: parent
        enabled: root.inputEnabled && !root.wireSelectionModeHeld
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        propagateComposedEvents: true
        // Unset away from labels so layers underneath keep their own cursors.
        cursorShape: root.labelDragActive
            ? Qt.ClosedHandCursor
            : (root.hoveredLabelEdgeId.length ? Qt.OpenHandCursor : undefined)

        onPositionChanged: function(mouse) {
            root.hoverX = mouse.x;
            root.hoverY = mouse.y;
            if (root.labelPressEdgeId.length && (mouse.buttons & Qt.LeftButton)) {
                if (!root.labelDragActive) {
                    var dx = mouse.x - root.labelPressX;
                    var dy = mouse.y - root.labelPressY;
                    if (Math.sqrt(dx * dx + dy * dy) < root.labelDragThresholdPx)
                        return;
                    root.labelDragActive = true;
                }
                var fraction = root.edgeLayer.flowLabelFractionAtScreen(root.labelPressEdgeId, mouse.x, mouse.y);
                if (isFinite(fraction))
                    root.edgeLayer.setFlowLabelDragPreview(root.labelPressEdgeId, fraction);
                return;
            }
            root.hoveredLabelEdgeId = root._labelEdgeAt(mouse.x, mouse.y);
            root.hoveredEdgeId = root.hoveredLabelEdgeId.length
                ? root.hoveredLabelEdgeId
                : (root.edgeLayer && root.edgeLayer.edgeAtScreen
                    ? root.edgeLayer.edgeAtScreen(mouse.x, mouse.y)
                    : "");
        }

        onExited: {
            root.hoveredEdgeId = "";
            root.hoveredLabelEdgeId = "";
        }

        onPressed: function(mouse) {
            root._resetLabelDrag(true);
            var labelEdgeId = root._labelEdgeAt(mouse.x, mouse.y);
            var edgeId = labelEdgeId.length ? labelEdgeId : root._edgeAt(mouse.x, mouse.y);
            if (!edgeId) {
                mouse.accepted = false;
                return;
            }
            var additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            if (mouse.button === Qt.LeftButton) {
                root.edgeClicked(edgeId, additive);
                if (labelEdgeId.length && !additive && root.edgeLayer && root.edgeLayer.flowLabelFractionAtScreen) {
                    root.labelPressEdgeId = labelEdgeId;
                    root.labelPressX = mouse.x;
                    root.labelPressY = mouse.y;
                }
            } else if (mouse.button === Qt.RightButton) {
                root.edgeContextRequested(edgeId, mouse.x, mouse.y);
            }
            mouse.accepted = true;
        }

        onReleased: function(mouse) {
            if (root.labelDragActive && mouse.button === Qt.LeftButton) {
                var edgeId = root.labelPressEdgeId;
                var fraction = Number(root.edgeLayer ? root.edgeLayer.labelDragFraction : NaN);
                root.labelPressEdgeId = "";
                root.labelDragActive = false;
                if (edgeId.length && isFinite(fraction))
                    root.flowLabelDragFinished(edgeId, fraction);
                else if (root.edgeLayer && root.edgeLayer.clearFlowLabelDragPreview)
                    root.edgeLayer.clearFlowLabelDragPreview();
                return;
            }
            root._resetLabelDrag(true);
        }

        onCanceled: root._resetLabelDrag(true)

        onDoubleClicked: function(mouse) {
            if (mouse.button !== Qt.LeftButton) {
                mouse.accepted = false;
                return;
            }
            var edgeId = root._edgeAt(mouse.x, mouse.y);
            if (!edgeId) {
                mouse.accepted = false;
                return;
            }
            root._resetLabelDrag(true);
            root.edgeDoubleClicked(edgeId);
            mouse.accepted = true;
        }
    }

    Item {
        id: edgePreviewAnchor
        x: root.hoverX
        y: root.hoverY
        width: 1
        height: 1

        Common.ManagedToolTip {
            objectName: "graphEdgeValuePreviewToolTip"
            popupType: Popup.Item
            policyBridge: root.edgeLayer ? root.edgeLayer.sceneBridge : null
            category: "general"
            active: root.hoveredEdgeId.length > 0 && !root.labelDragActive
            text: root.hoveredEdgeTooltipText
            maximumTextWidth: 360
            font.family: "monospace"
            font.pixelSize: 12
            screenStablePositioning: true
            screenStablePlacement: "below"
            screenGap: 6
        }
    }
}
