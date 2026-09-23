import QtQuick
import QtQuick.Shapes

// Retained pill/rounded-frame geometry. The outline stays inside the item's bounds;
// its curves are rendered at the current scene scale without a texture layer.
Shape {
    id: root
    property color fillColor: "transparent"
    property color borderColor: "transparent"
    property real borderWidth: 0
    property real cornerRadius: Math.min(width, height) * 0.5
    readonly property real resolvedBorderWidth: Math.max(0, Math.min(borderWidth, width, height))
    readonly property real inset: resolvedBorderWidth * 0.5
    readonly property real curveRadius: Math.max(0, Math.min(cornerRadius, Math.min(width, height) * 0.5) - inset)

    preferredRendererType: Shape.CurveRenderer
    visible: width > 0 && height > 0

    ShapePath {
        fillColor: root.fillColor
        strokeColor: root.borderColor
        strokeWidth: root.resolvedBorderWidth
        startX: root.width * 0.5
        startY: root.inset
        PathLine { x: root.width - root.inset - root.curveRadius; y: root.inset }
        PathAngleArc {
            moveToStart: false
            centerX: root.width - root.inset - root.curveRadius
            centerY: root.inset + root.curveRadius
            radiusX: root.curveRadius; radiusY: root.curveRadius
            startAngle: 270; sweepAngle: 90
        }
        PathLine { x: root.width - root.inset; y: root.height - root.inset - root.curveRadius }
        PathAngleArc {
            moveToStart: false
            centerX: root.width - root.inset - root.curveRadius
            centerY: root.height - root.inset - root.curveRadius
            radiusX: root.curveRadius; radiusY: root.curveRadius
            startAngle: 0; sweepAngle: 90
        }
        PathLine { x: root.inset + root.curveRadius; y: root.height - root.inset }
        PathAngleArc {
            moveToStart: false
            centerX: root.inset + root.curveRadius
            centerY: root.height - root.inset - root.curveRadius
            radiusX: root.curveRadius; radiusY: root.curveRadius
            startAngle: 90; sweepAngle: 90
        }
        PathLine { x: root.inset; y: root.inset + root.curveRadius }
        PathAngleArc {
            moveToStart: false
            centerX: root.inset + root.curveRadius
            centerY: root.inset + root.curveRadius
            radiusX: root.curveRadius; radiusY: root.curveRadius
            startAngle: 180; sweepAngle: 90
        }
        PathLine { x: root.width * 0.5; y: root.inset }
    }
}
