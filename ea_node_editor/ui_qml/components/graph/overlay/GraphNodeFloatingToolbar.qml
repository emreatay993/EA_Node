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
    // compact_pill / minimal_ghost group surface-specific buttons on the left
    // and common (rename/duplicate/delete/...) buttons on the right so the two
    // families read as distinct groups separated by a thin divider. Other styles
    // keep the source order.
    readonly property bool _groupBySurfaceFamily:
        root.style === "compact_pill" || root.style === "minimal_ghost"
    readonly property var _orderedActions: {
        var all = root.actionList;
        if (!Array.isArray(all) || all.length === 0)
            return [];
        if (!root._groupBySurfaceFamily)
            return all;
        var surface = [];
        var common = [];
        for (var i = 0; i < all.length; i++) {
            var item = all[i] || {};
            if (String(item.kind || "") === "common")
                common.push(item);
            else
                surface.push(item);
        }
        return surface.concat(common);
    }
    readonly property color accentColor: root.hostValid ? root.host.nodeThemeColor : "#4DA8DA"
    // Chrome colors track the host's theme / shell palette so the toolbar
    // follows both graph-theme switches (dark/light) and per-node passive
    // overrides (shell colors) instead of staying hardcoded-dark.
    readonly property color _chromeBaseFill: root.hostValid ? root.host.headerColor : "#1b1d22"
    readonly property color _chromeBaseBorder: root.hostValid ? root.host.outlineColor : "#3a3d45"
    readonly property color _chromeForeground: root.hostValid ? root.host.headerTextColor : "#f0f4fb"

    function _canvasStateBridge() {
        if (root.canvasItem) {
            if (root.canvasItem.canvasStateBridgeRef)
                return root.canvasItem.canvasStateBridgeRef;
            if (root.canvasItem._canvasStateBridgeRef)
                return root.canvasItem._canvasStateBridgeRef;
        }
        if (typeof graphCanvasStateBridge !== "undefined" && graphCanvasStateBridge)
            return graphCanvasStateBridge;
        return null;
    }

    readonly property string style: {
        var bridge = root._canvasStateBridge();
        if (bridge && bridge.graphics_floating_toolbar_style !== undefined) {
            var value = String(bridge.graphics_floating_toolbar_style || "").toLowerCase();
            if (value === "compact_pill" || value === "segmented_bar" || value === "minimal_ghost")
                return value;
        }
        return "compact_pill";
    }

    readonly property string size: {
        var bridge = root._canvasStateBridge();
        if (bridge && bridge.graphics_floating_toolbar_size !== undefined) {
            var value = String(bridge.graphics_floating_toolbar_size || "").toLowerCase();
            if (value === "small" || value === "medium" || value === "large")
                return value;
        }
        return "small";
    }

    readonly property real _sizeScale: {
        if (root.size === "large") return 1.5;
        if (root.size === "medium") return 1.25;
        return 1.0;
    }

    readonly property bool _hasChrome: root.style !== "minimal_ghost"
    readonly property real _chromeRadius: {
        if (root.style === "compact_pill") return 999;
        if (root.style === "segmented_bar") return 7;
        return 0;
    }
    readonly property color _chromeFillColor: {
        if (root.style === "compact_pill")
            return Qt.rgba(root._chromeBaseFill.r, root._chromeBaseFill.g, root._chromeBaseFill.b, 0.96);
        if (root.style === "segmented_bar") return root._chromeBaseFill;
        return "transparent";
    }
    readonly property color _chromeBorderColor: {
        if (root.style === "compact_pill") return Qt.alpha(root._chromeBaseBorder, 0.55);
        if (root.style === "segmented_bar") return root._chromeBaseBorder;
        return "transparent";
    }
    readonly property real _chromeBorderWidth: root._hasChrome ? 1 : 0
    readonly property real _chromeInternalPadding: {
        var base;
        if (root.style === "compact_pill") base = 3;
        else if (root.style === "segmented_bar") base = 0;
        else base = 2;
        return base * root._sizeScale;
    }
    readonly property real _chromeButtonGap: {
        var base;
        if (root.style === "compact_pill") base = 2;
        else if (root.style === "segmented_bar") base = 0;
        else base = 2;
        return base * root._sizeScale;
    }
    readonly property bool _chromeClip: root.style === "segmented_bar"
    readonly property real _buttonChromeRadius: {
        if (root.style === "compact_pill") return 999;
        if (root.style === "segmented_bar") return 0;
        return 5;
    }
    readonly property int _buttonHPadding: {
        var base;
        if (root.style === "compact_pill") base = 7;
        else if (root.style === "segmented_bar") base = 12;
        else base = 6;
        return Math.round(base * root._sizeScale);
    }
    readonly property int _buttonVPadding: {
        var base;
        if (root.style === "compact_pill") base = 7;
        else if (root.style === "segmented_bar") base = 6;
        else base = 6;
        return Math.round(base * root._sizeScale);
    }
    readonly property int _buttonIconSize: {
        var base;
        if (root.style === "compact_pill") base = 15;
        else if (root.style === "segmented_bar") base = 14;
        else base = 14;
        return Math.round(base * root._sizeScale);
    }
    readonly property color _buttonHoverFillColor: {
        if (root.style === "minimal_ghost") return Qt.alpha(root._chromeForeground, 0.10);
        return Qt.alpha(root.accentColor, 0.18);
    }
    readonly property color _segmentedDividerColor: Qt.alpha(root._chromeBaseBorder, 0.75)
    readonly property color _minimalSeparatorColor: Qt.alpha(root._chromeForeground, 0.18)
    readonly property color _caretFillColor: root._hasChrome ? root._chromeFillColor : Qt.alpha(root.accentColor, 0.55)
    readonly property color _caretBorderColor: root._hasChrome ? root._chromeBorderColor : Qt.alpha(root.accentColor, 0.55)

    readonly property real gapFromNode: Number(toolbarMetrics.gap_from_node || 6)
    readonly property real safetyMargin: Number(toolbarMetrics.safety_margin || 8)
    readonly property real hysteresis: Number(toolbarMetrics.hysteresis || 8)
    readonly property int animationDuration: Number(toolbarMetrics.animation_duration_ms || 180)
    readonly property real toolbarHeightMetric: Number(toolbarMetrics.toolbar_height || 32)

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

    readonly property bool _nodeDragActive: root.hostValid && Boolean(root.host.hostDragActive)

    visible: root.toolbarActive && root.actionList.length > 0 && !root._nodeDragActive
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

    readonly property real _ownerCenterX: {
        if (!root.hostValid)
            return chromeContainer.width / 2;
        var rect = root.nodeLocalRect;
        return rect.x + rect.width / 2 - root.x;
    }

    Rectangle {
        id: ownershipCaret
        objectName: "graphNodeFloatingToolbarCaret"
        visible: root._hasChrome
        z: -1
        width: 9
        height: 9
        rotation: 45
        antialiasing: true
        color: root._caretFillColor
        border.width: 1
        border.color: root._caretBorderColor

        readonly property real caretEdgeMargin: 6
        readonly property real clampedCenterX: Math.max(
            caretEdgeMargin + width / 2,
            Math.min(
                chromeContainer.width - caretEdgeMargin - width / 2,
                root._ownerCenterX
            )
        )
        x: clampedCenterX - width / 2
        y: root.flipped
            ? -height / 2 - 0.5
            : chromeContainer.height - height / 2 + 0.5
    }

    Image {
        id: ownershipChevron
        objectName: "graphNodeFloatingToolbarChevron"
        visible: !root._hasChrome
        z: -1
        width: 24
        height: 24
        smooth: true
        antialiasing: true
        source: root._iconSource(
            root.flipped ? "chevron-down" : "chevron-up",
            24,
            root._chromeForeground
        )
        sourceSize: Qt.size(24, 24)

        readonly property real clampedCenterX: Math.max(
            width / 2,
            Math.min(
                chromeContainer.width - width / 2,
                root._ownerCenterX
            )
        )
        x: clampedCenterX - width / 2
        y: root.flipped ? -height + 8 : chromeContainer.height - 9
    }

    Rectangle {
        id: chromeContainer
        objectName: "graphNodeFloatingToolbarChrome"
        radius: root._chromeRadius
        color: root._chromeFillColor
        border.width: root._chromeBorderWidth
        border.color: root._chromeBorderColor
        clip: root._chromeClip

        implicitWidth: buttonRow.implicitWidth + root._chromeInternalPadding * 2
        implicitHeight: Math.max(root.toolbarHeightMetric, buttonRow.implicitHeight + root._chromeInternalPadding * 2)

        Row {
            id: buttonRow
            anchors.centerIn: parent
            spacing: root._chromeButtonGap

            Repeater {
                id: buttonRepeater
                model: root._orderedActions

                Row {
                    id: buttonCell
                    spacing: 0
                    height: actionButton.implicitHeight

                    readonly property bool _isFirst: index === 0
                    readonly property bool _isLast: index === buttonRepeater.count - 1
                    readonly property bool _isDestructive: Boolean(modelData.destructive)
                    readonly property bool _isCommon: String((modelData || {}).kind || "") === "common"
                    readonly property bool _startsCommonGroup: {
                        if (!root._groupBySurfaceFamily || !buttonCell._isCommon || buttonCell._isFirst)
                            return false;
                        var prev = root._orderedActions[index - 1] || {};
                        return String(prev.kind || "") !== "common";
                    }
                    readonly property bool _showLeadingSeparator:
                        buttonCell._startsCommonGroup
                        || (root.style === "minimal_ghost" && buttonCell._isDestructive && !buttonCell._isFirst)

                    Item {
                        id: leadingSeparatorSlot
                        visible: buttonCell._showLeadingSeparator
                        width: visible ? 9 : 0
                        height: buttonCell.height
                        Rectangle {
                            anchors.centerIn: parent
                            width: 1
                            height: parent.height - 8
                            color: root._minimalSeparatorColor
                        }
                    }

                    GraphSurfaceControls.GraphSurfaceButton {
                        id: actionButton
                        objectName: "graphNodeFloatingToolbarAction_" + String(modelData.id || "")
                        host: root.host
                        text: String(modelData.label || "")
                        iconName: String(modelData.icon || "")
                        iconOnly: true
                        iconSize: root._buttonIconSize
                        iconSourceResolver: function(name, size, color) {
                            return root._iconSource(name, size, color);
                        }
                        accentColor: buttonCell._isDestructive
                            ? "#D94F4F"
                            : root.accentColor
                        enabled: modelData.enabled !== false
                        chromeRadius: root._buttonChromeRadius
                        contentHorizontalPadding: root._buttonHPadding
                        contentVerticalPadding: root._buttonVPadding
                        tooltipText: String(modelData.label || "")
                        baseFillColor: "transparent"
                        baseBorderColor: "transparent"
                        hoverFillColor: root._buttonHoverFillColor
                        hoverBorderColor: root._buttonHoverFillColor
                        hoverBorderWidth: 1
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

                    Rectangle {
                        id: trailingDivider
                        visible: root.style === "segmented_bar" && !buttonCell._isLast
                        width: visible ? 1 : 0
                        height: buttonCell.height
                        color: root._segmentedDividerColor
                    }
                }
            }
        }
    }
}
