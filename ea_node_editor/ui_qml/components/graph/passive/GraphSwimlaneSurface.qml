import QtQuick 2.15
import ".." as GraphShared

// Swimlane pools and lanes (Group backdrops): a pool draws the Group's glass body, frame and title band; a lane its
// role band and the divider it shares with the lane before it. The title in either band is the shared header title
// (rotated into the band of a horizontal pool), so double-click editing is the Group's.
GraphShared.GraphSurfaceBase {
    id: surface
    objectName: "graphNodeSwimlaneSurface"
    readonly property bool inputOverlayMode: host
        ? String(host.surfaceVariant || "") === "group_backdrop_input_overlay"
        : false
    readonly property string swimlaneVariant: host && host.nodeData
        ? String(host.nodeData.surface_variant || "")
        : ""
    readonly property bool isPool: surface.swimlaneVariant === "swimlane_pool"
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
    readonly property color frameColor: surface.selected
        ? (host ? host.selectedOutlineColor : "#4d9fff")
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
    readonly property color laneBandColor: host
        ? Qt.alpha(host.scopeBadgeColor, surface.selected ? 0.24 : 0.13)
        : Qt.rgba(0.3, 0.62, 1.0, 0.13)
    readonly property color laneFillColor: host && host.hasPassiveFillOverride
        ? Qt.alpha(host.surfaceColor, 0.24)
        : "transparent"

    // Pool: the Group's glass body and frame.
    Rectangle {
        id: poolGlass
        objectName: "graphNodeSwimlanePoolFrame"
        visible: surface.visualsVisible && surface.isPool
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
        visible: surface.visualsVisible && surface.isPool
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

    // Lane: optional style fill, its role band, and the divider it shares with the lane before it.
    Rectangle {
        objectName: "graphNodeSwimlaneLaneFill"
        visible: surface.visualsVisible && !surface.isPool
        anchors.fill: parent
        color: surface.laneFillColor
    }

    Rectangle {
        objectName: "graphNodeSwimlaneLaneBand"
        visible: surface.visualsVisible && !surface.isPool
        x: 0
        y: 0
        width: surface.horizontal ? surface.bandThickness : parent.width
        height: surface.horizontal ? parent.height : surface.bandThickness
        color: surface.laneBandColor
    }

    Rectangle {
        objectName: "graphNodeSwimlaneLaneBandEdge"
        visible: surface.visualsVisible && !surface.isPool
        antialiasing: true
        x: surface.horizontal ? surface.bandThickness - surface.lineWidth : 0
        y: surface.horizontal ? 0 : surface.bandThickness - surface.lineWidth
        width: surface.horizontal ? surface.lineWidth : parent.width
        height: surface.horizontal ? parent.height : surface.lineWidth
        color: surface.bandEdgeColor
    }

    Rectangle {
        objectName: "graphNodeSwimlaneLaneDivider"
        visible: surface.visualsVisible && !surface.isPool
        antialiasing: true
        x: 0
        y: 0
        width: surface.horizontal ? parent.width : surface.lineWidth
        height: surface.horizontal ? surface.lineWidth : parent.height
        color: surface.dividerColor
    }

    // A selected lane shows its whole outline above its neighbours' dividers.
    Rectangle {
        objectName: "graphNodeSwimlaneLaneSelection"
        visible: surface.visualsVisible && !surface.isPool && surface.selected
        anchors.fill: parent
        color: "transparent"
        border.width: Math.max(1.5, surface.frameWidth)
        border.color: surface.frameColor
    }
}
