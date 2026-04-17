import QtQuick 2.15

Item {
    id: root
    objectName: "graphCanvasInputLayers"
    property Item canvasItem: null
    property var shellCommandBridge: null
    property var sceneCommandBridge: null
    property var viewStateBridge: null
    property var viewCommandBridge: null
    property real boxZoomDragThreshold: 4
    property real boxZoomPaddingPx: 24
    readonly property var themePalette: themeBridge.palette

    function _hidePortFilterBridge() {
        if (root.canvasItem && root.canvasItem.sceneBridge && root.canvasItem.sceneBridge.set_hide_locked_ports)
            return root.canvasItem.sceneBridge;
        if (root.sceneCommandBridge && root.sceneCommandBridge.set_hide_locked_ports)
            return root.sceneCommandBridge;
        return null;
    }

    function _toggleHideLockedPorts() {
        var bridge = root._hidePortFilterBridge();
        if (!bridge || !root.canvasItem)
            return false;
        return Boolean(bridge.set_hide_locked_ports(!Boolean(root.canvasItem.hideLockedPorts)));
    }

    function _toggleHideOptionalPorts() {
        var bridge = root._hidePortFilterBridge();
        if (!bridge || !root.canvasItem || !bridge.set_hide_optional_ports)
            return false;
        return Boolean(bridge.set_hide_optional_ports(!Boolean(root.canvasItem.hideOptionalPorts)));
    }

    function _closeCommentPeekIfActive() {
        if (!root.shellCommandBridge || !root.shellCommandBridge.request_close_comment_peek)
            return false;
        return Boolean(root.shellCommandBridge.request_close_comment_peek());
    }

    function _contentFullscreenBridge() {
        if (typeof contentFullscreenBridge !== "undefined" && contentFullscreenBridge)
            return contentFullscreenBridge;
        return null;
    }

    function _showContentFullscreenHint(message) {
        var normalized = String(message || "Select one media or viewer node for fullscreen.").trim();
        if (!normalized.length)
            normalized = "Select one media or viewer node for fullscreen.";
        if (root.shellCommandBridge && root.shellCommandBridge.show_graph_hint) {
            root.shellCommandBridge.show_graph_hint(normalized, 2400);
            return true;
        }
        if (typeof shellLibraryBridge !== "undefined" && shellLibraryBridge && shellLibraryBridge.show_graph_hint) {
            shellLibraryBridge.show_graph_hint(normalized, 2400);
            return true;
        }
        return false;
    }

    function _selectedContentFullscreenNodeId() {
        if (!root.canvasItem || !root.canvasItem.selectedNodeIds)
            return "";
        var selected = root.canvasItem.selectedNodeIds() || [];
        if (selected.length !== 1)
            return "";
        return String(selected[0] || "").trim();
    }

    function _handleContentFullscreenShortcut() {
        var bridge = root._contentFullscreenBridge();
        if (!bridge)
            return false;
        if (Boolean(bridge.open)) {
            if (bridge.request_close)
                bridge.request_close();
            return true;
        }
        var nodeId = root._selectedContentFullscreenNodeId();
        if (!nodeId.length) {
            root._showContentFullscreenHint("Select one media or viewer node for fullscreen.");
            return true;
        }
        if (bridge.can_open_node && !bridge.can_open_node(nodeId)) {
            if (bridge.request_open_node)
                bridge.request_open_node(nodeId);
            root._showContentFullscreenHint(
                bridge.last_error || "The selected node does not support content fullscreen."
            );
            return true;
        }
        if (bridge.request_open_node && bridge.request_open_node(nodeId))
            return true;
        root._showContentFullscreenHint(
            bridge.last_error || "The selected node does not support content fullscreen."
        );
        return true;
    }

    function _handleHidePortChord(buttons, changedButton) {
        var normalizedButtons = Number(buttons || 0);
        if (!(normalizedButtons & Qt.MiddleButton))
            return false;
        if (changedButton === Qt.LeftButton)
            return root._toggleHideLockedPorts();
        if (changedButton === Qt.RightButton)
            return root._toggleHideOptionalPorts();
        if (changedButton === Qt.MiddleButton) {
            if (normalizedButtons & Qt.LeftButton)
                return root._toggleHideLockedPorts();
            if (normalizedButtons & Qt.RightButton)
                return root._toggleHideOptionalPorts();
        }
        return false;
    }

    function _lockToggleTargetAtScreen(screenX, screenY) {
        if (!root.canvasItem)
            return null;
        return _lockToggleTargetInItem(root.canvasItem, Number(screenX), Number(screenY));
    }

    function _lockToggleTargetInItem(item, screenX, screenY) {
        if (!item || item.visible === false)
            return null;

        var children = item.children || [];
        for (var i = children.length - 1; i >= 0; --i) {
            var child = children[i];
            if (!child || child.mapFromItem === undefined)
                continue;
            var nested = _lockToggleTargetInItem(child, screenX, screenY);
            if (nested)
                return nested;
        }

        if (
            item.objectName === "graphNodeInputPortLockToggleMouseArea"
            && item.enabled !== false
            && String(item.nodeId || "").length > 0
        ) {
            var local = item.mapFromItem(root.canvasItem, screenX, screenY);
            if (local.x >= 0 && local.x <= item.width && local.y >= 0 && local.y <= item.height)
                return item;
        }
        return null;
    }

    Keys.onDeletePressed: function(event) {
        if (root.shellCommandBridge && root.canvasItem)
            root.shellCommandBridge.request_delete_selected_graph_items(root.canvasItem.selectedEdgeIds);
        if (root.canvasItem) {
            root.canvasItem.selectedEdgeIds = [];
            root.canvasItem.clearPendingConnection();
            root.canvasItem._closeContextMenus();
        }
        event.accepted = true;
    }

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_F11) {
            if (root._handleContentFullscreenShortcut())
                event.accepted = true;
            return;
        }
        if (!root.canvasItem)
            return;
        if ((event.modifiers & Qt.AltModifier) && event.key === Qt.Key_Left) {
            if (root.shellCommandBridge && root.shellCommandBridge.request_navigate_scope_parent()) {
                root.canvasItem.clearEdgeSelection();
                root.canvasItem.clearPendingConnection();
                root.canvasItem._closeContextMenus();
            }
            event.accepted = true;
            return;
        }
        if ((event.modifiers & Qt.AltModifier) && event.key === Qt.Key_Home) {
            if (root.shellCommandBridge && root.shellCommandBridge.request_navigate_scope_root()) {
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
        if (
            root.canvasItem.edgeContextVisible
            || root.canvasItem.nodeContextVisible
            || root.canvasItem.selectionContextVisible
        ) {
            root.canvasItem._closeContextMenus();
            handled = true;
        }
        if (root._closeCommentPeekIfActive())
            handled = true;
        if (handled)
            event.accepted = true;
    }

    MouseArea {
        id: marqueeArea
        objectName: "graphCanvasMarqueeArea"
        parent: root.canvasItem
        anchors.fill: parent
        z: -9
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: false
        property bool selecting: false
        property bool additive: false
        property string marqueeMode: ""
        property real startX: 0
        property real startY: 0
        property real currentX: 0
        property real currentY: 0

        function resetGestureState() {
            selecting = false;
            additive = false;
            marqueeMode = "";
        }

        onPressed: function(mouse) {
            if (!root.canvasItem)
                return;
            root.canvasItem.forceActiveFocus();
            if (typeof viewerSessionBridge !== "undefined" && viewerSessionBridge && viewerSessionBridge.clear_viewer_focus)
                viewerSessionBridge.clear_viewer_focus();
            if (
                (mouse.button === Qt.LeftButton || mouse.button === Qt.RightButton)
                && root._closeCommentPeekIfActive()
            ) {
                resetGestureState();
                mouse.accepted = true;
                return;
            }
            if (root._handleHidePortChord(mouse.buttons, mouse.button)) {
                resetGestureState();
                panArea.cancelPanningForChord();
                mouse.accepted = true;
                return;
            }
            startX = mouse.x;
            startY = mouse.y;
            currentX = mouse.x;
            currentY = mouse.y;
            if (mouse.button === Qt.LeftButton) {
                root.canvasItem._closeContextMenus();
                root.canvasItem.clearPendingConnection();
                selecting = true;
                marqueeMode = "selection";
                additive = Boolean((mouse.modifiers & Qt.ControlModifier) || (mouse.modifiers & Qt.ShiftModifier));
                return;
            }
            if (mouse.button === Qt.RightButton) {
                root.canvasItem._closeContextMenus();
                root.canvasItem.clearPendingConnection();
                selecting = true;
                marqueeMode = "zoom";
                additive = false;
            }
        }

        onPositionChanged: function(mouse) {
            if (!selecting)
                return;
            currentX = mouse.x;
            currentY = mouse.y;
            if (
                marqueeMode === "zoom"
                && root.canvasItem
                && (Math.abs(currentX - startX) >= 2 || Math.abs(currentY - startY) >= 2)
            ) {
                if (!root.canvasItem.interactionActive)
                    root.canvasItem.beginViewportInteraction();
                root.canvasItem.noteViewportInteraction();
            }
        }

        onReleased: function(mouse) {
            var zoomGestureActive = marqueeMode === "zoom";
            if (!selecting) {
                resetGestureState();
                return;
            }
            currentX = mouse.x;
            currentY = mouse.y;
            var dx = Math.abs(currentX - startX);
            var dy = Math.abs(currentY - startY);
            if (marqueeMode === "selection" && root.sceneCommandBridge && root.canvasItem) {
                if (dx >= 4 || dy >= 4) {
                    root.sceneCommandBridge.select_nodes_in_rect(
                        root.canvasItem.screenToSceneX(startX),
                        root.canvasItem.screenToSceneY(startY),
                        root.canvasItem.screenToSceneX(currentX),
                        root.canvasItem.screenToSceneY(currentY),
                        additive
                    );
                    if (!additive)
                        root.canvasItem.clearEdgeSelection();
                } else if (!additive) {
                    root.sceneCommandBridge.clear_selection();
                    root.canvasItem.clearEdgeSelection();
                }
            } else if (zoomGestureActive && root.canvasItem) {
                var openSelectionContext = dx < root.boxZoomDragThreshold
                    && dy < root.boxZoomDragThreshold
                    && root.canvasItem.selectedNodeIds().length > 1;
                if (openSelectionContext) {
                    if (root.canvasItem.interactionActive)
                        root.canvasItem.finishViewportInteractionSoon();
                    root.canvasItem._openSelectionContext(currentX, currentY);
                } else {
                    root.canvasItem.noteViewportInteraction();
                    if (dx >= root.boxZoomDragThreshold && dy >= root.boxZoomDragThreshold) {
                        root.canvasItem.frameScreenRect(
                            startX,
                            startY,
                            currentX,
                            currentY,
                            root.boxZoomPaddingPx
                        );
                    }
                    root.canvasItem.finishViewportInteractionSoon();
                }
            }
            resetGestureState();
        }

        onCanceled: {
            var zoomGestureActive = marqueeMode === "zoom";
            resetGestureState();
            if (zoomGestureActive && root.canvasItem)
                root.canvasItem.finishViewportInteractionSoon();
        }

        onDoubleClicked: function(mouse) {
            resetGestureState();
            if (mouse.button !== Qt.LeftButton)
                return;
            if (!root.canvasItem)
                return;
            if (mouse.modifiers & Qt.ControlModifier) {
                if (root._toggleHideLockedPorts())
                    mouse.accepted = true;
                return;
            }
            if (!root.shellCommandBridge)
                return;
            var sceneX = root.canvasItem.screenToSceneX(mouse.x);
            var sceneY = root.canvasItem.screenToSceneY(mouse.y);
            var overlayHost = root.canvasItem.overlayHostItem || root.canvasItem;
            var overlayPoint = root.canvasItem.mapToItem(overlayHost, mouse.x, mouse.y);
            root.shellCommandBridge.request_open_canvas_quick_insert(
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
        color: marqueeArea.marqueeMode === "zoom"
            ? Qt.alpha(root.themePalette.accent, 0.12)
            : Qt.alpha(root.themePalette.accent, 0.2)
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
        hoverEnabled: false
        property bool panning: false
        property real lastX: 0
        property real lastY: 0

        function cancelPanningForChord() {
            if (!panning)
                return;
            panning = false;
            if (root.canvasItem)
                root.canvasItem.finishViewportInteractionSoon();
        }

        onPressed: {
            if (root._handleHidePortChord(mouse.buttons, mouse.button)) {
                marqueeArea.resetGestureState();
                panning = false;
                mouse.accepted = true;
                return;
            }
            if (!root.viewStateBridge || !root.viewCommandBridge || !root.viewCommandBridge.pan_by)
                return;
            panning = true;
            lastX = mouse.x;
            lastY = mouse.y;
            if (root.canvasItem)
                root.canvasItem.beginViewportInteraction();
        }

        onPositionChanged: {
            if (!panning || !root.viewStateBridge || !root.viewCommandBridge || !root.viewCommandBridge.pan_by)
                return;
            if (root.canvasItem)
                root.canvasItem.noteViewportInteraction();
            var dx = (mouse.x - lastX) / Math.max(0.1, root.viewStateBridge.zoom_value);
            var dy = (mouse.y - lastY) / Math.max(0.1, root.viewStateBridge.zoom_value);
            root.viewCommandBridge.pan_by(-dx, -dy);
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
