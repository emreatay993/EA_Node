import QtQuick 2.15

Item {
    id: root
    objectName: "graphNodeHostGestureLayer"
    property Item host: null
    readonly property bool dragActive: nodeDragArea.manualDragActive
    readonly property string dragAxisLock: nodeDragArea.dragAxisLock
    readonly property bool dragSnapBypass: nodeDragArea.dragSnapBypass
    readonly property bool containsMouse: nodeDragArea.containsMouse
    readonly property bool pointerInteractionActive: nodeDragArea.pressed || nodeDragArea.manualDragActive
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
            : (manualDragActive ? Qt.ClosedHandCursor : (hostDragCursorSuppressed ? Qt.ArrowCursor : Qt.OpenHandCursor))
        drag.target: null
        drag.axis: Drag.XAndYAxis
        propagateComposedEvents: true
        property bool dragMoved: false
        property bool manualDragActive: false
        property bool suppressNextClick: false
        property real pressPointerX: 0.0
        property real pressPointerY: 0.0
        property real lastDragDx: 0.0
        property real lastDragDy: 0.0
        // Shift+drag constrains the move to the dominant axis: "", "horizontal", or "vertical".
        property string dragAxisLock: ""
        // Alt+drag moves without snapping to smart guides or the grid.
        property bool dragSnapBypass: false
        // Set by a right press while this area holds a left press: the rest of that left press stays inert.
        property bool leftPressInert: false
        property bool edgePressHandled: false
        readonly property bool edgeHoverActive: containsMouse && _edgeAtLocalPosition(mouseX, mouseY).length > 0
        readonly property bool surfaceClaimHoverActive: containsMouse
            && !!root.host
            && !!root.host._surfaceClaimsBodyInteractionAt
            && root.host._surfaceClaimsBodyInteractionAt(mouseX, mouseY)
        readonly property bool hostDragCursorSuppressed: edgeHoverActive || surfaceClaimHoverActive

        function _resetDragMotionState() {
            dragMoved = false;
            manualDragActive = false;
            lastDragDx = 0.0;
            lastDragDy = 0.0;
            dragAxisLock = "";
            dragSnapBypass = false;
        }

        function _dragThreshold() {
            var threshold = Number(drag.threshold);
            return isFinite(threshold) && threshold > 0.0 ? threshold : 4.0;
        }

        function _pointerPoint(mouse) {
            var coordinateItem = root.host ? root.host.parent : null;
            if (coordinateItem && nodeDragArea.mapToItem) {
                var mapped = nodeDragArea.mapToItem(coordinateItem, mouse.x, mouse.y);
                return {"x": Number(mapped.x), "y": Number(mapped.y)};
            }
            return {"x": Number(mouse.x), "y": Number(mouse.y)};
        }

        function _pointerInCanvasAt(localX, localY) {
            if (!root.host || !root.host.edgeHitPassthroughEnabled || !root.host.canvasItem)
                return null;
            if (root.host._pointerInCanvas)
                return root.host._pointerInCanvas(nodeDragArea, {"x": localX, "y": localY});
            if (nodeDragArea.mapToItem)
                return nodeDragArea.mapToItem(root.host.canvasItem, localX, localY);
            return {"x": Number(localX), "y": Number(localY)};
        }

        function _edgeAtLocalPosition(localX, localY) {
            if (!root.host || !root.host.edgeHitPassthroughEnabled || !root.host.canvasItem)
                return "";
            if (!root.host.canvasItem.edgeAtScreen)
                return "";
            var pointerPos = _pointerInCanvasAt(localX, localY);
            if (!pointerPos)
                return "";
            return String(root.host.canvasItem.edgeAtScreen(pointerPos.x, pointerPos.y) || "");
        }

        function _handleEdgePress(mouse) {
            if (!mouse || (mouse.button !== Qt.LeftButton && mouse.button !== Qt.RightButton))
                return false;
            if (!root.host || !root.host.canvasItem || !root.host.canvasItem.handleEdgePressAtScreen)
                return false;
            var pointerPos = _pointerInCanvasAt(mouse.x, mouse.y);
            if (!pointerPos)
                return false;
            return Boolean(root.host.canvasItem.handleEdgePressAtScreen(
                pointerPos.x,
                pointerPos.y,
                mouse.button,
                mouse.modifiers
            ));
        }

        function _emitDragOffset(mouse, force) {
            var pointerPoint = _pointerPoint(mouse);
            var dx = Number(pointerPoint.x) - pressPointerX;
            var dy = Number(pointerPoint.y) - pressPointerY;
            if (!isFinite(dx))
                dx = 0.0;
            if (!isFinite(dy))
                dy = 0.0;
            if (!force && !dragMoved && Math.max(Math.abs(dx), Math.abs(dy)) < _dragThreshold())
                return false;
            // Re-evaluated on every move so pressing or releasing Shift or Alt mid-drag applies.
            if (mouse.modifiers & Qt.ShiftModifier) {
                dragAxisLock = Math.abs(dx) >= Math.abs(dy) ? "horizontal" : "vertical";
                if (dragAxisLock === "horizontal")
                    dy = 0.0;
                else
                    dx = 0.0;
            } else {
                dragAxisLock = "";
            }
            dragSnapBypass = Boolean(mouse.modifiers & Qt.AltModifier);
            dragMoved = true;
            manualDragActive = true;
            lastDragDx = dx;
            lastDragDy = dy;
            root.host.dragOffsetChanged(root.host.nodeData.node_id, dx, dy, dragAxisLock, dragSnapBypass);
            return true;
        }

        onPressed: function(mouse) {
            if (!root.host || !root.host.nodeData)
                return;
            // mouse.x/y is where the press met the node as drawn (the node-relative surface-claim and
            // title-edit checks use it); pressX/Y is where it lands in this area once a canceled drag has
            // moved the host back (the edge hit and the context menu use it).
            var pressX = mouse.x;
            var pressY = mouse.y;
            if (mouse.button === Qt.LeftButton) {
                leftPressInert = false;
            } else if (pressedButtons & Qt.LeftButton) {
                // A right press while this area holds a left press ends that left press: moving on starts
                // no drag and its release neither commits nor clicks. A live drag is canceled first, so
                // its offset and smart guides do not linger under the context menu; that moves the host
                // back to where the drag started, so the press is mapped again from its window position.
                leftPressInert = true;
                if (manualDragActive) {
                    var pointer = nodeDragArea.mapToItem(null, mouse.x, mouse.y);
                    root.host.dragCanceled(root.host.nodeData.node_id);
                    var restored = nodeDragArea.mapFromItem(null, pointer.x, pointer.y);
                    pressX = restored.x;
                    pressY = restored.y;
                }
            }
            _resetDragMotionState();
            suppressNextClick = false;
            edgePressHandled = false;
            if (root.host.commitInlineTitleEditAt)
                root.host.commitInlineTitleEditAt(mouse.x, mouse.y);
            if (root.host._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y)) {
                mouse.accepted = true;
                return;
            }
            if (_handleEdgePress({"x": pressX, "y": pressY, "button": mouse.button, "modifiers": mouse.modifiers})) {
                edgePressHandled = true;
                suppressNextClick = true;
                mouse.accepted = true;
                return;
            }
            if (mouse.button === Qt.RightButton) {
                root.host.nodeContextRequested(root.host.nodeData.node_id, pressX, pressY);
                mouse.accepted = true;
                return;
            }
            if (mouse.button !== Qt.LeftButton)
                return;
            var pointerPoint = _pointerPoint(mouse);
            pressPointerX = Number(pointerPoint.x);
            pressPointerY = Number(pointerPoint.y);
        }

        onClicked: function(mouse) {
            if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                return;
            if (suppressNextClick) {
                suppressNextClick = false;
                mouse.accepted = true;
                return;
            }
            if (root.host._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y)) {
                mouse.accepted = true;
                return;
            }
            var additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            root.host.nodeClicked(root.host.nodeData.node_id, additive);
        }

        onDoubleClicked: function(mouse) {
            if (!root.host || !root.host.nodeData || mouse.button !== Qt.LeftButton)
                return;
            if (root.host._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y)) {
                mouse.accepted = true;
                return;
            }
            if (root.host.requestInlineTitleEditAt && root.host.requestInlineTitleEditAt(mouse.x, mouse.y)) {
                mouse.accepted = true;
                return;
            }
            root.host.nodeOpenRequested(root.host.nodeData.node_id);
        }

        onPositionChanged: {
            if (!root.host || !root.host.nodeData || !pressed)
                return;
            if (edgePressHandled || leftPressInert)
                return;
            if ((pressedButtons & Qt.LeftButton) === 0)
                return;
            _emitDragOffset(mouse, false);
        }

        onReleased: function(mouse) {
            if (!root.host || !root.host.nodeData)
                return;
            if (mouse.button === Qt.LeftButton && leftPressInert) {
                // A right press ended this left press: its release neither commits nor clicks.
                leftPressInert = false;
                suppressNextClick = true;
                _resetDragMotionState();
                mouse.accepted = true;
                return;
            }
            if (edgePressHandled) {
                edgePressHandled = false;
                suppressNextClick = true;
                _resetDragMotionState();
                mouse.accepted = true;
                return;
            }
            if (mouse.button !== Qt.LeftButton)
                return;
            var moved = dragMoved;
            if (!moved && root.host._surfaceClaimsBodyInteractionAt(mouse.x, mouse.y)) {
                _resetDragMotionState();
                mouse.accepted = true;
                return;
            }
            if (moved)
                _emitDragOffset(mouse, true);
            var baseX = Number(root.host.nodeData.x);
            var baseY = Number(root.host.nodeData.y);
            if (!isFinite(baseX))
                baseX = 0.0;
            if (!isFinite(baseY))
                baseY = 0.0;
            root.host.dragFinished(
                root.host.nodeData.node_id,
                baseX + (moved ? lastDragDx : 0.0),
                baseY + (moved ? lastDragDy : 0.0),
                moved,
                moved ? dragAxisLock : "",
                moved ? dragSnapBypass : false
            );
            suppressNextClick = moved;
            _resetDragMotionState();
        }

        onCanceled: {
            if (!root.host || !root.host.nodeData)
                return;
            edgePressHandled = false;
            leftPressInert = false;
            root.host.dragCanceled(root.host.nodeData.node_id);
            suppressNextClick = false;
            _resetDragMotionState();
        }
    }
}
