import QtQuick
import QtQuick.Shapes

// Two retained round-capped strokes share one renderer. Active endpoints are
// supplied in local coordinates by the owning control's actual handle centers.
Shape {
    id: root
    property color trackColor: "#4a4f5a"
    property color activeColor: "#60cdff"
    property real activeStart: 0
    property real activeEnd: 0
    property real trackThickness: 3
    readonly property real trackStart: Math.min(width * 0.5, trackThickness * 0.5)
    readonly property real trackEnd: Math.max(trackStart, width - trackThickness * 0.5)
    readonly property real clampedStart: Math.max(trackStart, Math.min(trackEnd, activeStart))
    readonly property real clampedEnd: Math.max(clampedStart, Math.min(trackEnd, activeEnd))
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
        strokeColor: root.trackColor
        strokeWidth: root.trackThickness
        fillColor: "transparent"
        capStyle: ShapePath.RoundCap
        startX: root.trackStart; startY: root.height * 0.5
        PathLine { x: root.trackEnd; y: root.height * 0.5 }
    }
    ShapePath {
        strokeColor: root.activeColor
        strokeWidth: root.trackThickness
        fillColor: "transparent"
        capStyle: ShapePath.RoundCap
        startX: root.clampedStart; startY: root.height * 0.5
        PathLine { x: root.clampedEnd; y: root.height * 0.5 }
    }
}
