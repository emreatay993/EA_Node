import QtQuick 2.15
import QtQuick.Controls 2.15
import "GraphCanvasLogic.js" as GraphCanvasLogic

Rectangle {
    id: root
    objectName: "graphCanvasMinimapOverlayRoot"
    property Item canvasItem: null
    property var sceneBridge: null
    property var viewBridge: null
    readonly property var themePalette: themeBridge.palette
    readonly property bool isExpanded: root.canvasItem ? root.canvasItem.minimapExpanded : false
    readonly property color chromeColor: Qt.alpha(themePalette.panel_bg, 0.64)
    readonly property color chromeBorderColor: themePalette.border
    readonly property color titleColor: themePalette.group_title_fg
    readonly property color toggleHoverColor: themePalette.hover
    readonly property color togglePressedColor: themePalette.pressed
    readonly property color toggleBorderColor: themePalette.border
    readonly property color toggleCollapsedColor: themePalette.toolbar_bg
    readonly property color toggleIconColor: themePalette.panel_title_fg
    readonly property color viewportBackdropColor: Qt.alpha(themePalette.canvas_bg, 0.72)
    readonly property color viewportBackdropBorderColor: themePalette.border
    readonly property color minimapNodeSelectedColor: Qt.alpha(themePalette.accent, 0.28)
    readonly property color minimapNodeColor: Qt.alpha(themePalette.border, 0.45)
    readonly property color minimapNodeSelectedBorderColor: themePalette.accent
    readonly property color minimapNodeBorderColor: themePalette.muted_fg
    readonly property color viewportRectFillColor: Qt.alpha(themePalette.accent, 0.18)
    readonly property color viewportRectBorderColor: themePalette.accent
    readonly property var selectedNodeLookup: root.sceneBridge ? root.sceneBridge.selected_node_lookup : ({})

    z: 140
    visible: root.canvasItem ? root.canvasItem.minimapVisible : true
    enabled: visible
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.rightMargin: 12
    anchors.bottomMargin: 12
    width: root.canvasItem && root.isExpanded
        ? root.canvasItem.minimapExpandedWidth
        : (root.canvasItem ? root.canvasItem.minimapCollapsedWidth : 28)
    height: root.canvasItem && root.isExpanded
        ? root.canvasItem.minimapExpandedHeight
        : (root.canvasItem ? root.canvasItem.minimapCollapsedHeight : 28)
    radius: 6
    color: root.chromeColor
    border.width: 1
    border.color: root.isExpanded ? root.chromeBorderColor : (minimapToggleMouse.containsMouse || minimapToggleMouse.pressed ? root.chromeBorderColor : "transparent")
    clip: true

    Behavior on width {
        NumberAnimation { duration: 200; easing.type: Easing.InOutCubic }
    }
    Behavior on height {
        NumberAnimation { duration: 200; easing.type: Easing.InOutCubic }
    }
    Behavior on border.color {
        ColorAnimation { duration: 120 }
    }

    // Expanded header: label + collapse toggle
    Text {
        visible: root.isExpanded
        anchors.left: parent.left
        anchors.leftMargin: 8
        anchors.top: parent.top
        anchors.topMargin: 6
        text: "MINIMAP"
        color: root.titleColor
        font.pixelSize: 9
        font.bold: true
    }

    // Toggle button — ghost icon-only style.
    // Collapsed: fills the entire root and shows "expand" chevron.
    // Expanded: small button in top-right shows "collapse" chevron.
    Rectangle {
        id: minimapToggle
        objectName: "graphCanvasMinimapToggle"
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.topMargin: root.isExpanded ? 3 : 0
        anchors.rightMargin: root.isExpanded ? 3 : 0
        width: root.isExpanded ? 22 : parent.width
        height: root.isExpanded ? 22 : parent.height
        radius: root.isExpanded ? 4 : root.radius
        color: minimapToggleMouse.pressed
            ? root.togglePressedColor
            : (minimapToggleMouse.containsMouse ? root.toggleHoverColor : root.toggleCollapsedColor)
        border.width: (minimapToggleMouse.containsMouse || minimapToggleMouse.pressed) ? 1 : 0
        border.color: root.toggleBorderColor

        Image {
            anchors.centerIn: parent
            source: root.isExpanded
                ? uiIcons.sourceSized("chevron-down", 12, String(root.toggleIconColor))
                : uiIcons.sourceSized("chevron-up", 14, String(root.toggleIconColor))
            width: root.isExpanded ? 12 : 14
            height: root.isExpanded ? 12 : 14
            fillMode: Image.PreserveAspectFit
            smooth: true
            mipmap: true
        }

        ToolTip.visible: minimapToggleMouse.containsMouse
        ToolTip.text: root.isExpanded ? "Collapse minimap" : "Expand minimap"
        ToolTip.delay: 400

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
        objectName: "graphCanvasMinimapViewport"
        visible: root.isExpanded
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
            color: root.viewportBackdropColor
            border.width: 1
            border.color: root.viewportBackdropBorderColor
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
                readonly property bool selectedState: Boolean(
                    root.selectedNodeLookup[String(modelData.node_id || "")]
                )
                x: minimapViewport.sceneToMinimapX(modelData.x)
                y: minimapViewport.sceneToMinimapY(modelData.y)
                width: Math.max(2, modelData.width * minimapViewport.scaleValue())
                height: Math.max(2, modelData.height * minimapViewport.scaleValue())
                color: selectedState ? root.minimapNodeSelectedColor : root.minimapNodeColor
                border.width: selectedState ? 1.2 : 1
                border.color: selectedState
                    ? root.minimapNodeSelectedBorderColor
                    : root.minimapNodeBorderColor
                radius: 1
            }
        }

        Rectangle {
            id: minimapViewportRect
            objectName: "graphCanvasMinimapViewportRect"
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
            color: root.viewportRectFillColor
            border.width: 1
            border.color: root.viewportRectBorderColor
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
