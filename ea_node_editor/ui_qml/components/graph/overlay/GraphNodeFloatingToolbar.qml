import QtQuick 2.15
import QtQuick.Controls 2.15
import "../surface_controls" as GraphSurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry
import "toolbar_positioning.js" as ToolbarPositioning

Item {
    id: root
    objectName: "graphNodeFloatingToolbar"

    property Item host: null
    property var canvasItem: null
    property var viewBridge: null
    property var visibleSceneRectPayload: ({})

    readonly property bool hostValid: !!root.host
    readonly property var hostNodeData: root.hostValid ? root.host.nodeData : null
    readonly property bool toolbarActive: root.hostValid && Boolean(root.host.toolbarActive)
    readonly property var toolbarMetrics: {
        if (!root.hostValid)
            return ({});
        var metrics = root.host.surfaceMetrics || {};
        return metrics.floating_toolbar ? metrics.floating_toolbar : ({});
    }
    readonly property var actionList: {
        if (!root.hostValid)
            return [];
        var actions = root.host.availableActions;
        return Array.isArray(actions) ? actions : [];
    }
    readonly property color accentColor: root.hostValid ? root.host.nodeThemeColor : "#4DA8DA"
    readonly property color chromeFillColor: {
        if (root.hostValid && root.host.headerColor !== undefined)
            return Qt.rgba(root.host.headerColor.r, root.host.headerColor.g, root.host.headerColor.b, 0.95);
        return Qt.rgba(0.10, 0.11, 0.13, 0.95);
    }

    readonly property real gapFromNode: Number(toolbarMetrics.gap_from_node || 6)
    readonly property real safetyMargin: Number(toolbarMetrics.safety_margin || 8)
    readonly property real hysteresis: Number(toolbarMetrics.hysteresis || 8)
    readonly property real internalPadding: Number(toolbarMetrics.internal_padding || 4)
    readonly property real buttonGap: Number(toolbarMetrics.button_gap || 4)
    readonly property int animationDuration: Number(toolbarMetrics.animation_duration_ms || 180)
    readonly property real toolbarHeightMetric: Number(toolbarMetrics.toolbar_height || 32)
    readonly property real buttonSizeMetric: Number(toolbarMetrics.button_size || 24)

    readonly property var embeddedInteractiveRects: root.visible
        ? SurfaceControlGeometry.rectList(SurfaceControlGeometry.rectFromItem(chromeContainer, root.host))
        : []
    readonly property rect toolbarRect: Qt.rect(root.x, root.y, root.width, root.height)

    property bool flipped: false

    readonly property var nodeLocalRect: {
        if (!root.hostValid || !root.hostNodeData)
            return ({ x: 0, y: 0, width: 0, height: 0 });
        // host.x already folds in worldOffset plus the active drag (drag.target
        // mutates host.x directly during a drag). liveDragDx/Dy contribute the
        // multi-selection translate applied to non-anchor nodes via transform.
        var dragDx = root.host.dragTranslateX !== undefined
            ? Number(root.host.dragTranslateX || 0)
            : 0.0;
        var dragDy = root.host.dragTranslateY !== undefined
            ? Number(root.host.dragTranslateY || 0)
            : 0.0;
        return {
            x: Number(root.host.x || 0) + dragDx,
            y: Number(root.host.y || 0) + dragDy,
            width: Number(root.host.width || 0),
            height: Number(root.host.height || 0)
        };
    }
    readonly property var viewportLocalRect: {
        var payload = root.visibleSceneRectPayload || {};
        var offset = root.hostValid ? Number(root.host.worldOffset || 0) : 0;
        return {
            x: Number(payload.x || 0) + offset,
            y: Number(payload.y || 0) + offset,
            width: Number(payload.width || 0),
            height: Number(payload.height || 0)
        };
    }
    readonly property size toolbarSize: Qt.size(
        Math.max(1, chromeContainer.implicitWidth),
        Math.max(1, chromeContainer.implicitHeight)
    )
    readonly property var anchor: ToolbarPositioning.computeAnchor(
        root.nodeLocalRect,
        { width: root.toolbarSize.width, height: root.toolbarSize.height },
        root.viewportLocalRect,
        {
            gap_from_node: root.gapFromNode,
            safety_margin: root.safetyMargin,
            hysteresis: root.hysteresis
        },
        root.flipped
    )

    onAnchorChanged: {
        if (Boolean(root.anchor.flipped) !== root.flipped)
            root.flipped = Boolean(root.anchor.flipped);
    }

    visible: root.toolbarActive && root.actionList.length > 0
    x: Number(root.anchor.x)
    y: Number(root.anchor.y)
    width: chromeContainer.implicitWidth
    height: chromeContainer.implicitHeight
    opacity: root.visible ? 1.0 : 0.0
    z: 40
    activeFocusOnTab: root.visible

    Behavior on opacity {
        NumberAnimation {
            duration: root.animationDuration
            easing.type: Easing.InOutCubic
        }
    }

    transform: Translate {
        id: slideTransform
        y: root.visible ? 0 : (root.flipped ? -root.gapFromNode : root.gapFromNode)
        Behavior on y {
            NumberAnimation {
                duration: root.animationDuration
                easing.type: Easing.OutCubic
            }
        }
    }

    function _iconSource(name, size, color) {
        if (typeof uiIcons === "undefined" || !uiIcons || !uiIcons.has(name))
            return "";
        return uiIcons.sourceSized(name, size, color);
    }

    // Propagate hover state back to the host so toolbarActiveSource stays true
    // while the cursor is on the chrome or in the gap bridging it to the node.
    // The gap bridge widens the effective hover target across the visible gap
    // so slow cursor movement does not race the 120 ms grace timer.
    readonly property bool pointerOnToolbar: chromeHoverHandler.hovered || bridgeHoverHandler.hovered
    onPointerOnToolbarChanged: {
        if (root.hostValid)
            root.host.toolbarPointerInside = root.pointerOnToolbar;
    }
    onHostChanged: {
        if (_previousHost && _previousHost.toolbarPointerInside !== undefined)
            _previousHost.toolbarPointerInside = false;
        _previousHost = root.host;
        if (root.hostValid)
            root.host.toolbarPointerInside = root.pointerOnToolbar;
    }
    property Item _previousHost: null

    HoverHandler {
        id: chromeHoverHandler
    }

    Item {
        id: hoverBridge
        objectName: "graphNodeFloatingToolbarHoverBridge"
        width: chromeContainer.width
        height: Math.max(1, root.gapFromNode)
        x: 0
        y: root.flipped ? -height : chromeContainer.height

        HoverHandler {
            id: bridgeHoverHandler
        }
    }

    Rectangle {
        id: ownershipCaret
        objectName: "graphNodeFloatingToolbarCaret"
        z: -1
        width: 9
        height: 9
        rotation: 45
        antialiasing: true
        color: chromeContainer.color
        border.width: 1
        border.color: chromeContainer.border.color

        readonly property real ownerCenterX: {
            if (!root.hostValid)
                return chromeContainer.width / 2;
            var rect = root.nodeLocalRect;
            return rect.x + rect.width / 2 - root.x;
        }
        readonly property real caretEdgeMargin: 6
        readonly property real clampedCenterX: Math.max(
            caretEdgeMargin + width / 2,
            Math.min(
                chromeContainer.width - caretEdgeMargin - width / 2,
                ownerCenterX
            )
        )
        x: clampedCenterX - width / 2
        y: root.flipped
            ? -height / 2 - 0.5
            : chromeContainer.height - height / 2 + 0.5
    }

    Rectangle {
        id: chromeContainer
        objectName: "graphNodeFloatingToolbarChrome"
        radius: 8
        color: root.chromeFillColor
        border.width: 1
        border.color: Qt.alpha(root.accentColor, 0.82)

        implicitWidth: Math.max(root.buttonSizeMetric, buttonRow.implicitWidth + root.internalPadding * 2)
        implicitHeight: Math.max(root.toolbarHeightMetric, buttonRow.implicitHeight + root.internalPadding * 2)

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: parent.radius - 1
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.04)
        }

        Row {
            id: buttonRow
            anchors.centerIn: parent
            spacing: root.buttonGap

            Repeater {
                id: buttonRepeater
                model: root.actionList

                GraphSurfaceControls.GraphSurfaceButton {
                    id: actionButton
                    objectName: "graphNodeFloatingToolbarAction_" + String(modelData.id || "")
                    host: root.host
                    text: String(modelData.label || "")
                    iconName: String(modelData.icon || "")
                    iconOnly: false
                    iconSize: 14
                    iconSourceResolver: function(name, size, color) {
                        return root._iconSource(name, size, color);
                    }
                    accentColor: Boolean(modelData.destructive)
                        ? "#D94F4F"
                        : (Boolean(modelData.primary) ? root.accentColor : Qt.alpha(root.accentColor, 0.85))
                    enabled: modelData.enabled !== false
                    chromeRadius: 6
                    contentHorizontalPadding: 8
                    contentVerticalPadding: 4
                    tooltipText: String(modelData.label || "")
                    baseFillColor: Qt.rgba(1, 1, 1, 0.04)
                    baseBorderColor: Qt.alpha(root.accentColor, 0.22)
                    focusPolicy: Qt.TabFocus
                    onControlStarted: {
                        if (root.host && root.host.nodeData && root.host.surfaceControlInteractionStarted)
                            root.host.surfaceControlInteractionStarted(String(root.host.nodeData.node_id || ""));
                    }
                    onClicked: {
                        if (!root.host)
                            return;
                        root.host.dispatchNodeAction(String(modelData.id || ""), null);
                    }
                    Keys.onReturnPressed: actionButton.clicked()
                    Keys.onEnterPressed: actionButton.clicked()
                }
            }
        }
    }
}
