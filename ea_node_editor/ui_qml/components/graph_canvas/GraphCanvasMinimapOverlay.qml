import QtQuick 2.15
import "GraphCanvasLogic.js" as GraphCanvasLogic

Rectangle {
    id: root
    property Item canvasItem: null
    property var sceneBridge: null
    property var viewBridge: null

    z: 140
    visible: root.canvasItem ? root.canvasItem.minimapVisible : true
    enabled: visible
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.rightMargin: 12
    anchors.bottomMargin: 12
    width: root.canvasItem && root.canvasItem.minimapExpanded
        ? root.canvasItem.minimapExpandedWidth
        : (root.canvasItem ? root.canvasItem.minimapCollapsedWidth : 36)
    height: root.canvasItem && root.canvasItem.minimapExpanded
        ? root.canvasItem.minimapExpandedHeight
        : (root.canvasItem ? root.canvasItem.minimapCollapsedHeight : 28)
    radius: 4
    color: "#A21C2028"
    border.width: 1
    border.color: "#4B5567"
    clip: true

    Text {
        visible: root.canvasItem ? root.canvasItem.minimapExpanded : false
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.top: parent.top
        anchors.topMargin: 5
        text: "MINIMAP"
        color: "#AAB4C9"
        font.pixelSize: 9
        font.bold: true
    }

    Rectangle {
        id: minimapToggle
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: 4
        anchors.rightMargin: 4
        width: 22
        height: 18
        radius: 3
        color: minimapToggleMouse.pressed ? "#4A5365" : (minimapToggleMouse.containsMouse ? "#3F4857" : "#37404F")
        border.width: 1
        border.color: "#5B667A"

        Text {
            anchors.centerIn: parent
            text: (root.canvasItem && root.canvasItem.minimapExpanded) ? "-" : "+"
            color: "#E2E9F7"
            font.pixelSize: 12
            font.bold: true
        }

        MouseArea {
            id: minimapToggleMouse
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            hoverEnabled: true
            preventStealing: true
            onClicked: {
                if (!root.canvasItem)
                    return;
                root.canvasItem.forceActiveFocus();
                root.canvasItem.toggleMinimapExpanded();
                mouse.accepted = true;
            }
        }
    }

    Item {
        id: minimapViewport
        visible: root.canvasItem ? root.canvasItem.minimapExpanded : false
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        anchors.topMargin: 24
        anchors.bottomMargin: 4
        property real contentPadding: 7

        function _normalizeRectPayload(payload, fallbackX, fallbackY, fallbackWidth, fallbackHeight) {
            return GraphCanvasLogic.normalizeRectPayload(
                payload,
                fallbackX,
                fallbackY,
                fallbackWidth,
                fallbackHeight
            );
        }

        function sceneRect() {
            var payload = root.sceneBridge ? root.sceneBridge.workspace_scene_bounds_payload : null;
            return _normalizeRectPayload(payload, -1600.0, -900.0, 3200.0, 1800.0);
        }

        function visibleRect() {
            var scene = sceneRect();
            var payload = root.viewBridge ? root.viewBridge.visible_scene_rect_payload : null;
            return _normalizeRectPayload(payload, scene.x, scene.y, scene.width, scene.height);
        }

        function scaleValue() {
            var scene = sceneRect();
            var availableWidth = Math.max(1.0, width - contentPadding * 2.0);
            var availableHeight = Math.max(1.0, height - contentPadding * 2.0);
            return Math.min(availableWidth / scene.width, availableHeight / scene.height);
        }

        function usedWidth() {
            return sceneRect().width * scaleValue();
        }

        function usedHeight() {
            return sceneRect().height * scaleValue();
        }

        function contentOffsetX() {
            return (width - usedWidth()) * 0.5;
        }

        function contentOffsetY() {
            return (height - usedHeight()) * 0.5;
        }

        function sceneToMinimapX(sceneX) {
            var scene = sceneRect();
            return contentOffsetX() + (Number(sceneX) - scene.x) * scaleValue();
        }

        function sceneToMinimapY(sceneY) {
            var scene = sceneRect();
            return contentOffsetY() + (Number(sceneY) - scene.y) * scaleValue();
        }

        function minimapToSceneX(minimapX) {
            var scene = sceneRect();
            return scene.x + (Number(minimapX) - contentOffsetX()) / Math.max(1e-6, scaleValue());
        }

        function minimapToSceneY(minimapY) {
            var scene = sceneRect();
            return scene.y + (Number(minimapY) - contentOffsetY()) / Math.max(1e-6, scaleValue());
        }

        Rectangle {
            anchors.fill: parent
            radius: 2
            color: "#AA171A22"
            border.width: 1
            border.color: "#41495B"
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            preventStealing: true
            onPressed: {
                if (!root.canvasItem)
                    return;
                root.canvasItem.forceActiveFocus();
                root.canvasItem._closeContextMenus();
            }
            onClicked: {
                if (!root.viewBridge)
                    return;
                root.viewBridge.center_on_scene_point(
                    minimapViewport.minimapToSceneX(mouse.x),
                    minimapViewport.minimapToSceneY(mouse.y)
                );
                mouse.accepted = true;
            }
        }

        Repeater {
            model: root.sceneBridge ? root.sceneBridge.minimap_nodes_model : []
            delegate: Rectangle {
                x: minimapViewport.sceneToMinimapX(modelData.x)
                y: minimapViewport.sceneToMinimapY(modelData.y)
                width: Math.max(2, modelData.width * minimapViewport.scaleValue())
                height: Math.max(2, modelData.height * minimapViewport.scaleValue())
                color: modelData.selected ? "#A4457FC6" : "#6C5A6273"
                border.width: modelData.selected ? 1.2 : 1
                border.color: modelData.selected ? "#D0EAFF" : "#909DB4"
                radius: 1
            }
        }

        Rectangle {
            id: minimapViewportRect
            property var visibleRectPayload: minimapViewport.visibleRect()
            property real contentWidth: minimapViewport.usedWidth()
            property real contentHeight: minimapViewport.usedHeight()
            width: Math.max(10, Math.min(contentWidth, visibleRectPayload.width * minimapViewport.scaleValue()))
            height: Math.max(10, Math.min(contentHeight, visibleRectPayload.height * minimapViewport.scaleValue()))
            x: {
                var raw = minimapViewport.sceneToMinimapX(visibleRectPayload.x);
                var minX = minimapViewport.contentOffsetX();
                return Math.max(minX, Math.min(raw, minX + contentWidth - width));
            }
            y: {
                var raw = minimapViewport.sceneToMinimapY(visibleRectPayload.y);
                var minY = minimapViewport.contentOffsetY();
                return Math.max(minY, Math.min(raw, minY + contentHeight - height));
            }
            color: "#2A7EC7FF"
            border.width: 1
            border.color: "#E0F3FF"
            radius: 2

            MouseArea {
                id: minimapViewportDragArea
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                hoverEnabled: true
                cursorShape: Qt.SizeAllCursor
                preventStealing: true
                onPressed: {
                    if (!root.canvasItem)
                        return;
                    root.canvasItem.forceActiveFocus();
                    root.canvasItem._closeContextMenus();
                    if (root.viewBridge) {
                        root.viewBridge.center_on_scene_point(
                            minimapViewport.minimapToSceneX(minimapViewportRect.x + mouse.x),
                            minimapViewport.minimapToSceneY(minimapViewportRect.y + mouse.y)
                        );
                    }
                    mouse.accepted = true;
                }
                onPositionChanged: {
                    if (!pressed || !root.viewBridge)
                        return;
                    root.viewBridge.center_on_scene_point(
                        minimapViewport.minimapToSceneX(minimapViewportRect.x + mouse.x),
                        minimapViewport.minimapToSceneY(minimapViewportRect.y + mouse.y)
                    );
                    mouse.accepted = true;
                }
            }
        }
    }
}
