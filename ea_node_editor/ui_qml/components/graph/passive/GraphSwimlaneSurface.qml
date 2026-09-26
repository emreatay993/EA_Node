import QtQuick 2.15
import ".." as GraphShared
import "../surface_controls" as SurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry

// Swimlane pools and lanes (Group backdrops): a pool draws the Group's glass body, frame and title band; a lane its
// role band and the divider it shares with the lane before it. A lane no pool holds draws the glass body and frame
// itself. The title in either band is the shared header title (rotated into the band of a horizontal pool), so
// double-click editing is the Group's. The input-overlay copy draws nothing but a lane's "+" buttons. Both copies
// offer the floating toolbar's orientation switch, since either can be the toolbar's host.
GraphShared.GraphSurfaceBase {
    id: surface
    objectName: "graphNodeSwimlaneSurface"
    readonly property bool inputOverlayMode: host
        ? String(host.surfaceVariant || "") === "group_backdrop_input_overlay"
        : false
    readonly property string swimlaneVariant: host && host.nodeData
        ? String(host.nodeData.surface_variant || "")
        : ""
    readonly property string nodeId: host && host.nodeData ? String(host.nodeData.node_id || "") : ""
    readonly property var canvasItem: host ? host.canvasItem : null
    readonly property bool isPool: surface.swimlaneVariant === "swimlane_pool"
    // A lane in no pool (its owner is not a pool) stands on its own and draws its own sheet and frame.
    readonly property bool standaloneLane: !surface.isPool && !surface._heldByPool
    readonly property bool framed: surface.isPool || surface.standaloneLane
    readonly property bool _heldByPool: {
        if (!host || !host.nodeData || !surface.canvasItem || !surface.canvasItem._sceneNodePayload)
            return false;
        var ownerId = String(host.nodeData.owner_backdrop_id || "");
        if (!ownerId.length)
            return false;
        var owner = surface.canvasItem._sceneNodePayload(ownerId);
        return !!owner && String(owner.surface_variant || "") === "swimlane_pool";
    }
    readonly property bool horizontal: surface.propString("orientation", "horizontal") !== "vertical"
    readonly property bool visualsVisible: !surface.inputOverlayMode
    // The band the title sits in: the header metrics describe a top band; a horizontal pool turns it to the left.
    readonly property real bandThickness: host && host.surfaceMetrics
        ? Math.max(0.0, Number(host.surfaceMetrics.body_top || 40.0))
        : 40.0
    readonly property bool selected: host ? Boolean(host.isSelected) : false
    readonly property real frameRadius: host ? Math.max(6, Number(host.resolvedCornerRadius || 10)) : 8
    readonly property real frameWidth: host ? Math.max(1, Number(host.resolvedBorderWidth || 1)) : 1
    readonly property var themePalette: typeof themeBridge !== "undefined" && themeBridge ? themeBridge.palette : ({})
    readonly property color accentColor: host ? host.selectedOutlineColor : "#4d9fff"
    readonly property color frameColor: surface.selected
        ? surface.accentColor
        : (host
            ? (host.hasPassiveBorderOverride ? Qt.alpha(host.outlineColor, 0.96) : Qt.alpha(host.headerTextColor, 0.34))
            : "#4a4f5a")
    // Lines inside a pool follow the title colour, so they read on light and dark canvases alike.
    readonly property color dividerColor: host
        ? (host.hasPassiveBorderOverride ? Qt.alpha(host.outlineColor, 0.9) : Qt.alpha(host.headerTextColor, 0.2))
        : Qt.rgba(1.0, 1.0, 1.0, 0.2)
    readonly property color bandEdgeColor: host
        ? (host.hasPassiveBorderOverride ? Qt.alpha(host.outlineColor, 0.9) : Qt.alpha(host.headerTextColor, 0.24))
        : Qt.rgba(1.0, 1.0, 1.0, 0.24)
    // A pool is a sheet lifted off the canvas (the theme's raised panel colour), so the grid recedes behind its lanes;
    // a style fill replaces it.
    readonly property color sheetColor: host && host.hasPassiveFillOverride
        ? host.surfaceColor
        : String(surface.themePalette.panel_alt_bg || "#24262c")
    readonly property color glassTopColor: Qt.alpha(Qt.lighter(surface.sheetColor, 1.04), 0.8)
    readonly property color glassFillColor: Qt.alpha(surface.sheetColor, 0.74)
    readonly property color glassBottomColor: Qt.alpha(Qt.darker(surface.sheetColor, 1.02), 0.74)
    readonly property color innerBorderColor: Qt.rgba(1.0, 1.0, 1.0, surface.selected ? 0.18 : 0.11)
    // Hairlines stay antialiased and a little wider than a pixel, so zoomed-out lanes keep their dividers.
    readonly property real lineWidth: 1.5
    readonly property color poolBandColor: host
        ? Qt.alpha(host.scopeBadgeColor, surface.selected ? 0.34 : 0.24)
        : Qt.rgba(0.3, 0.62, 1.0, 0.24)
    // A lane's own colour ("#rrggbb", from its Color property) tints its band and, lightly, the lane.
    readonly property string laneColorText: surface.isPool ? "" : surface.propString("color", "").trim()
    readonly property bool hasLaneColor: /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(surface.laneColorText)
    readonly property color laneBandColor: surface.hasLaneColor
        ? Qt.alpha(surface.laneColorText, surface.selected ? 0.52 : 0.38)
        : (host
            ? Qt.alpha(host.scopeBadgeColor, surface.selected ? 0.24 : 0.13)
            : Qt.rgba(0.3, 0.62, 1.0, 0.13))
    readonly property color laneFillColor: surface.hasLaneColor
        ? Qt.alpha(surface.laneColorText, 0.08)
        : (host && host.hasPassiveFillOverride ? Qt.alpha(host.surfaceColor, 0.24) : "transparent")
    // While a drag would drop nodes (or a lane) here, the lane (or pool) lights up.
    readonly property bool dropTarget: surface.visualsVisible
        && surface.nodeId.length > 0
        && !!surface.canvasItem
        && !!surface.canvasItem.swimlaneDropTargetLookup
        && !!surface.canvasItem.swimlaneDropTargetLookup[surface.nodeId]
    readonly property real _inset: surface.framed ? surface.frameWidth : 0.0
    readonly property real _innerRadius: surface.framed ? Math.max(0, surface.frameRadius - surface.frameWidth) : 0

    // "+" buttons: add a lane before or after this one (next to a standalone lane, that forms a pool). Only the
    // input-overlay copy takes the pointer, so only it shows them.
    readonly property real _viewZoom: {
        var bridge = surface.canvasItem ? surface.canvasItem.viewBridge : null;
        var zoom = bridge && bridge.zoom_value !== undefined ? Number(bridge.zoom_value) : 1.0;
        return isFinite(zoom) && zoom > 0 ? zoom : 1.0;
    }
    readonly property bool laneInsertAllowed: surface.inputOverlayMode
        && !surface.isPool
        && !!host
        && !host.surfaceInteractionLocked
        && !host.isCollapsed
        && !host.hostDragActive
        && !host.wireDragInProgress
        && surface._viewZoom >= 0.45
        && !(surface.canvasItem && String(surface.canvasItem.liveDragAnchorNodeId || "").length > 0)
    readonly property bool _insertRevealed: !!host && Boolean(host.hoverActive)
    readonly property real insertButtonSize: 24
    // The "+" reads as an action on any lane colour: an accent disc with a white plus.
    readonly property color insertFillColor: surface.accentColor
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists([
        insertBeforeButton.embeddedInteractiveRects,
        insertAfterButton.embeddedInteractiveRects
    ])

    // Floating-toolbar button: the context menu's "Switch to ... Lanes". Its label and glyph name the orientation it
    // switches to; a lane in a pool turns the whole pool. A collapsed pool keeps its orientation (as in the menu).
    readonly property bool orientationSwitchAvailable: !!host && !host.isCollapsed && surface.nodeId.length > 0
    readonly property var surfaceActions: surface.orientationSwitchAvailable ? [surface._orientationSwitchAction()] : []

    function _orientationSwitchAction() {
        var action = {
            "id": "swimlane_switch_orientation",
            "label": surface.horizontal ? "Switch to vertical lanes" : "Switch to horizontal lanes",
            "icon": surface.horizontal ? "swimlane-vertical" : "swimlane-horizontal",
            "kind": "surface"
        };
        if (surface._heldByPool)
            action.description = "Turns the whole pool";
        return action;
    }

    function dispatchSurfaceAction(actionId) {
        if (String(actionId || "") !== "swimlane_switch_orientation" || !surface.orientationSwitchAvailable)
            return false;
        // Like the menu row, an orientation property edit: the scene turns it into one undo step that re-lays the
        // lanes out and keeps every node in its lane.
        host.inlinePropertyCommitted(surface.nodeId, "orientation", surface.horizontal ? "vertical" : "horizontal");
        return true;
    }

    function _insertLane(after) {
        var bridge = surface.canvasItem ? surface.canvasItem.sceneCommandBridge : null;
        if (!surface.laneInsertAllowed || !surface.nodeId.length || !bridge || !bridge.insert_swimlane_lane)
            return;
        bridge.insert_swimlane_lane(surface.nodeId, Boolean(after));
    }

    function _iconSource(name, size, color) {
        return typeof uiIcons !== "undefined" && uiIcons && uiIcons.has(name) ? uiIcons.sourceSized(name, size, color) : "";
    }

    // Pool, or a standalone lane: the Group's glass body and frame.
    Rectangle {
        id: poolGlass
        objectName: "graphNodeSwimlanePoolFrame"
        visible: surface.visualsVisible && surface.framed
        anchors.fill: parent
        radius: surface.frameRadius
        gradient: Gradient {
            GradientStop { position: 0.0; color: surface.glassTopColor }
            GradientStop { position: 0.32; color: surface.glassFillColor }
            GradientStop { position: 1.0; color: surface.glassBottomColor }
        }
        border.width: surface.frameWidth
        border.color: surface.frameColor
    }

    Rectangle {
        visible: surface.visualsVisible && surface.framed
        anchors.fill: parent
        anchors.margins: surface.frameWidth
        radius: Math.max(0, surface.frameRadius - surface.frameWidth)
        color: "transparent"
        border.width: 1
        border.color: surface.innerBorderColor
    }

    // Pool title band: along the left edge of a horizontal pool, along the top of a vertical one.
    Rectangle {
        objectName: "graphNodeSwimlanePoolBand"
        visible: surface.visualsVisible && surface.isPool
        x: surface.frameWidth
        y: surface.frameWidth
        width: surface.horizontal ? surface.bandThickness - surface.frameWidth : parent.width - 2 * surface.frameWidth
        height: surface.horizontal ? parent.height - 2 * surface.frameWidth : surface.bandThickness - surface.frameWidth
        radius: Math.max(0, surface.frameRadius - surface.frameWidth)
        color: surface.poolBandColor
    }

    Rectangle {
        objectName: "graphNodeSwimlanePoolBandEdge"
        visible: surface.visualsVisible && surface.isPool
        antialiasing: true
        x: surface.horizontal ? surface.bandThickness - surface.lineWidth : surface.frameWidth
        y: surface.horizontal ? surface.frameWidth : surface.bandThickness - surface.lineWidth
        width: surface.horizontal ? surface.lineWidth : parent.width - 2 * surface.frameWidth
        height: surface.horizontal ? parent.height - 2 * surface.frameWidth : surface.lineWidth
        color: surface.bandEdgeColor
    }

    // Lane: its tint (a colour or a style fill), its role band, and the divider it shares with the lane before it.
    Rectangle {
        objectName: "graphNodeSwimlaneLaneFill"
        visible: surface.visualsVisible && !surface.isPool
        anchors.fill: parent
        anchors.margins: surface._inset
        radius: surface._innerRadius
        color: surface.laneFillColor
    }

    Rectangle {
        objectName: "graphNodeSwimlaneLaneBand"
        visible: surface.visualsVisible && !surface.isPool
        x: surface._inset
        y: surface._inset
        width: surface.horizontal ? surface.bandThickness - surface._inset : parent.width - 2 * surface._inset
        height: surface.horizontal ? parent.height - 2 * surface._inset : surface.bandThickness - surface._inset
        radius: surface._innerRadius
        color: surface.laneBandColor
    }

    Rectangle {
        objectName: "graphNodeSwimlaneLaneBandEdge"
        visible: surface.visualsVisible && !surface.isPool
        antialiasing: true
        x: surface.horizontal ? surface.bandThickness - surface.lineWidth : surface._inset
        y: surface.horizontal ? surface._inset : surface.bandThickness - surface.lineWidth
        width: surface.horizontal ? surface.lineWidth : parent.width - 2 * surface._inset
        height: surface.horizontal ? parent.height - 2 * surface._inset : surface.lineWidth
        color: surface.bandEdgeColor
    }

    Rectangle {
        objectName: "graphNodeSwimlaneLaneDivider"
        visible: surface.visualsVisible && !surface.isPool && !surface.standaloneLane
        antialiasing: true
        x: 0
        y: 0
        width: surface.horizontal ? parent.width : surface.lineWidth
        height: surface.horizontal ? surface.lineWidth : parent.height
        color: surface.dividerColor
    }

    // A selected lane in a pool shows its whole outline above its neighbours' dividers (a standalone lane's frame
    // already turns the selection colour).
    Rectangle {
        objectName: "graphNodeSwimlaneLaneSelection"
        visible: surface.visualsVisible && !surface.isPool && !surface.standaloneLane && surface.selected
        anchors.fill: parent
        color: "transparent"
        border.width: Math.max(1.5, surface.frameWidth)
        border.color: surface.frameColor
    }

    // The lane (or pool) a drag would drop into.
    Rectangle {
        objectName: "graphNodeSwimlaneDropTarget"
        visible: surface.dropTarget
        anchors.fill: parent
        radius: surface.framed ? surface.frameRadius : 0
        color: Qt.alpha(surface.accentColor, 0.1)
        border.width: 2
        border.color: Qt.alpha(surface.accentColor, 0.9)
    }

    SurfaceControls.GraphSurfaceButton {
        id: insertBeforeButton
        objectName: "graphNodeSwimlaneInsertBeforeButton"
        host: surface.host
        visible: surface.laneInsertAllowed && (surface._insertRevealed || hovered || down)
        width: surface.insertButtonSize
        height: surface.insertButtonSize
        controlHeight: surface.insertButtonSize
        chromeRadius: surface.insertButtonSize / 2
        iconOnly: true
        iconName: "plus"
        iconSize: 14
        text: ""
        accentColor: "#ffffff"
        foregroundColor: "#ffffff"
        baseFillColor: Qt.alpha(surface.insertFillColor, 0.9)
        baseBorderColor: Qt.lighter(surface.insertFillColor, 1.3)
        hoverFillColor: Qt.lighter(surface.insertFillColor, 1.15)
        hoverBorderColor: "#ffffff"
        pressedFillColor: Qt.darker(surface.insertFillColor, 1.15)
        pressedBorderColor: "#ffffff"
        iconSourceResolver: surface._iconSource
        x: surface.horizontal ? surface.bandThickness + (surface.width - surface.bandThickness - width) / 2 : 4
        y: surface.horizontal ? 4 : surface.bandThickness + (surface.height - surface.bandThickness - height) / 2
        tooltipText: surface.horizontal ? "Add a lane above" : "Add a lane to the left"
        onControlStarted: {
            if (surface.host)
                surface.host.surfaceControlInteractionStarted(surface.nodeId);
        }
        onClicked: surface._insertLane(false)

        HoverHandler {
            cursorShape: Qt.PointingHandCursor
        }
    }

    SurfaceControls.GraphSurfaceButton {
        id: insertAfterButton
        objectName: "graphNodeSwimlaneInsertAfterButton"
        host: surface.host
        visible: surface.laneInsertAllowed && (surface._insertRevealed || hovered || down)
        width: surface.insertButtonSize
        height: surface.insertButtonSize
        controlHeight: surface.insertButtonSize
        chromeRadius: surface.insertButtonSize / 2
        iconOnly: true
        iconName: "plus"
        iconSize: 14
        text: ""
        accentColor: "#ffffff"
        foregroundColor: "#ffffff"
        baseFillColor: Qt.alpha(surface.insertFillColor, 0.9)
        baseBorderColor: Qt.lighter(surface.insertFillColor, 1.3)
        hoverFillColor: Qt.lighter(surface.insertFillColor, 1.15)
        hoverBorderColor: "#ffffff"
        pressedFillColor: Qt.darker(surface.insertFillColor, 1.15)
        pressedBorderColor: "#ffffff"
        iconSourceResolver: surface._iconSource
        x: surface.horizontal
            ? surface.bandThickness + (surface.width - surface.bandThickness - width) / 2
            : surface.width - width - 4
        y: surface.horizontal
            ? surface.height - height - 4
            : surface.bandThickness + (surface.height - surface.bandThickness - height) / 2
        tooltipText: surface.horizontal ? "Add a lane below" : "Add a lane to the right"
        onControlStarted: {
            if (surface.host)
                surface.host.surfaceControlInteractionStarted(surface.nodeId);
        }
        onClicked: surface._insertLane(true)

        HoverHandler {
            cursorShape: Qt.PointingHandCursor
        }
    }
}
