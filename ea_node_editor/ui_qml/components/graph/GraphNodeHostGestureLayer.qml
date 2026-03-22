import QtQuick 2.15

Item {
    id: root
    objectName: "graphNodeHostGestureLayer"
    property Item host: null
    readonly property bool dragActive: nodeDragArea.drag.active
    readonly property bool containsMouse: nodeDragArea.containsMouse
    z: 1.5

    MouseArea {
        id: nodeDragArea
        objectName: "graphNodeDragArea"
        anchors.fill: parent
        enabled: root.host ? !root.host.surfaceInteractionLocked : false
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: true
        cursorShape: root.host && root.host.surfaceInteractionLocked
            ? Qt.ArrowCursor
            : (drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
        drag.target: enabled && root.host ? root.host : null
        drag.axis: Drag.XAndYAxis
        propagateComposedEvents: true
        property bool dragMoved: false

        onPressed: function(mouse) {
            if (!root.host || !root.host.nodeData)
                return;
            if (root.host.commitInlineTitleEditAt)
                root.host.commitInlineTitleEditAt(mouse.x, mouse.y);
            if (root.host._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y)) {
                mouse.accepted = false;
                return;
            }
            if (mouse.button === Qt.RightButton) {
                root.host.nodeContextRequested(root.host.nodeData.node_id, mouse.x, mouse.y);
                mouse.accepted = true;
                return;
            }
            dragMoved = false;
        }

        onClicked: function(mouse) {
            if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                return;
            if (root.host._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y))
                return;
            var additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            root.host.nodeClicked(root.host.nodeData.node_id, additive);
        }

        onDoubleClicked: function(mouse) {
            if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                return;
            if (root.host._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y))
                return;
            if (root.host.requestInlineTitleEditAt && root.host.requestInlineTitleEditAt(mouse.x, mouse.y)) {
                mouse.accepted = true;
                return;
            }
            root.host.nodeOpenRequested(root.host.nodeData.node_id);
        }

        onPositionChanged: {
            if (!root.host || !root.host.nodeData || !drag.active)
                return;
            dragMoved = true;
            root.host.dragOffsetChanged(
                root.host.nodeData.node_id,
                root.host.x - root.host.worldOffset - root.host.nodeData.x,
                root.host.y - root.host.worldOffset - root.host.nodeData.y
            );
        }

        onReleased: function(mouse) {
            if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                return;
            root.host.dragFinished(
                root.host.nodeData.node_id,
                root.host.x - root.host.worldOffset,
                root.host.y - root.host.worldOffset,
                dragMoved
            );
        }

        onCanceled: {
            if (!root.host || !root.host.nodeData)
                return;
            root.host.dragCanceled(root.host.nodeData.node_id);
        }
    }
}
