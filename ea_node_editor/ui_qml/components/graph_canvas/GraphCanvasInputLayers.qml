import QtQuick 2.15

Item {
    id: root
    objectName: "graphCanvasInputLayers"
    property Item canvasItem: null
    property var mainWindowBridge: null
    property var sceneBridge: null
    property var viewBridge: null
    readonly property var themePalette: themeBridge.palette

    Keys.onDeletePressed: function(event) {
        if (root.mainWindowBridge && root.canvasItem)
            root.mainWindowBridge.request_delete_selected_graph_items(root.canvasItem.selectedEdgeIds);
        if (root.canvasItem) {
            root.canvasItem.selectedEdgeIds = [];
            root.canvasItem.clearPendingConnection();
            root.canvasItem._closeContextMenus();
        }
        event.accepted = true;
    }

    Keys.onPressed: function(event) {
        if (!root.canvasItem)
            return;
        if ((event.modifiers & Qt.AltModifier) && event.key === Qt.Key_Left) {
            if (root.mainWindowBridge && root.mainWindowBridge.request_navigate_scope_parent()) {
                root.canvasItem.clearEdgeSelection();
                root.canvasItem.clearPendingConnection();
                root.canvasItem._closeContextMenus();
            }
            event.accepted = true;
            return;
        }
        if ((event.modifiers & Qt.AltModifier) && event.key === Qt.Key_Home) {
            if (root.mainWindowBridge && root.mainWindowBridge.request_navigate_scope_root()) {
                root.canvasItem.clearEdgeSelection();
                root.canvasItem.clearPendingConnection();
                root.canvasItem._closeContextMenus();
            }
            event.accepted = true;
        }
    }

    Keys.onEscapePressed: function(event) {
        if (!root.canvasItem)
            return;
        var handled = false;
        if (root.canvasItem.cancelWireDrag())
            handled = true;
        if (root.canvasItem.pendingConnectionPort) {
            root.canvasItem.clearPendingConnection();
            handled = true;
        }
        if (root.canvasItem.edgeContextVisible || root.canvasItem.nodeContextVisible) {
            root.canvasItem._closeContextMenus();
            handled = true;
        }
        if (handled)
            event.accepted = true;
    }

    MouseArea {
        id: marqueeArea
        parent: root.canvasItem
        anchors.fill: parent
        z: -9
        acceptedButtons: Qt.LeftButton
        hoverEnabled: true
        property bool selecting: false
        property bool additive: false
        property real startX: 0
        property real startY: 0
        property real currentX: 0
        property real currentY: 0

        onPressed: {
            if (!root.canvasItem)
                return;
            root.canvasItem.forceActiveFocus();
            root.canvasItem._closeContextMenus();
            root.canvasItem.clearPendingConnection();
            selecting = true;
            additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
            startX = mouse.x;
            startY = mouse.y;
            currentX = mouse.x;
            currentY = mouse.y;
        }

        onPositionChanged: {
            if (!selecting)
                return;
            currentX = mouse.x;
            currentY = mouse.y;
        }

        onReleased: {
            if (!selecting)
                return;
            currentX = mouse.x;
            currentY = mouse.y;
            var dx = Math.abs(currentX - startX);
            var dy = Math.abs(currentY - startY);
            if (root.sceneBridge && root.canvasItem) {
                if (dx >= 4 || dy >= 4) {
                    root.sceneBridge.select_nodes_in_rect(
                        root.canvasItem.screenToSceneX(startX),
                        root.canvasItem.screenToSceneY(startY),
                        root.canvasItem.screenToSceneX(currentX),
                        root.canvasItem.screenToSceneY(currentY),
                        additive
                    );
                    if (!additive)
                        root.canvasItem.clearEdgeSelection();
                } else if (!additive) {
                    root.sceneBridge.clear_selection();
                    root.canvasItem.clearEdgeSelection();
                }
            }
            selecting = false;
        }

        onCanceled: {
            selecting = false;
        }

        onDoubleClicked: {
            selecting = false;
            if (!root.canvasItem || !root.mainWindowBridge)
                return;
            var sceneX = root.canvasItem.screenToSceneX(mouse.x);
            var sceneY = root.canvasItem.screenToSceneY(mouse.y);
            var overlayHost = root.canvasItem.overlayHostItem || root.canvasItem;
            var overlayPoint = root.canvasItem.mapToItem(overlayHost, mouse.x, mouse.y);
            root.mainWindowBridge.request_open_canvas_quick_insert(
                sceneX, sceneY, overlayPoint.x, overlayPoint.y
            );
            mouse.accepted = true;
        }

        onWheel: function(wheel) {
            if (root.canvasItem && root.canvasItem.applyWheelZoom(wheel))
                wheel.accepted = true;
        }
    }

    Rectangle {
        objectName: "graphCanvasMarqueeRect"
        parent: root.canvasItem
        visible: marqueeArea.selecting
            && (Math.abs(marqueeArea.currentX - marqueeArea.startX) >= 2
                || Math.abs(marqueeArea.currentY - marqueeArea.startY) >= 2)
        z: 60
        x: Math.min(marqueeArea.startX, marqueeArea.currentX)
        y: Math.min(marqueeArea.startY, marqueeArea.currentY)
        width: Math.abs(marqueeArea.currentX - marqueeArea.startX)
        height: Math.abs(marqueeArea.currentY - marqueeArea.startY)
        color: Qt.alpha(root.themePalette.accent, 0.2)
        border.width: 1
        border.color: root.themePalette.accent
    }

    MouseArea {
        id: panArea
        objectName: "graphCanvasPanArea"
        parent: root.canvasItem
        anchors.fill: parent
        z: -10
        acceptedButtons: Qt.MiddleButton
        hoverEnabled: true
        property bool panning: false
        property real lastX: 0
        property real lastY: 0

        onPressed: {
            if (!root.viewBridge)
                return;
            panning = true;
            lastX = mouse.x;
            lastY = mouse.y;
            if (root.canvasItem)
                root.canvasItem.beginViewportInteraction();
        }

        onPositionChanged: {
            if (!panning || !root.viewBridge)
                return;
            if (root.canvasItem)
                root.canvasItem.noteViewportInteraction();
            var dx = (mouse.x - lastX) / Math.max(0.1, root.viewBridge.zoom_value);
            var dy = (mouse.y - lastY) / Math.max(0.1, root.viewBridge.zoom_value);
            root.viewBridge.pan_by(-dx, -dy);
            lastX = mouse.x;
            lastY = mouse.y;
        }

        onReleased: {
            panning = false;
            if (root.canvasItem)
                root.canvasItem.finishViewportInteractionSoon();
        }

        onCanceled: {
            panning = false;
            if (root.canvasItem)
                root.canvasItem.finishViewportInteractionSoon();
        }
    }
}
