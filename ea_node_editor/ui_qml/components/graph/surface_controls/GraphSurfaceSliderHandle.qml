import QtQuick
import QtQuick.Shapes

// Light macOS-inspired thumb. Both the subtle lower rim and the disk are
// retained curves; no blur, offscreen layer, or scale-dependent image is used.
Shape {
    id: root
    property color fillColor: "#fafafa"
    property color borderColor: "#b6b8bc"
    property color depthColor: "#24000000"
    readonly property real diskRadius: Math.max(0, Math.min(width, height) * 0.5 - 0.6)
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
        strokeWidth: 0
        strokeColor: "transparent"
        fillColor: root.depthColor
        PathAngleArc {
            centerX: root.width * 0.5; centerY: root.height * 0.5 + 0.6
            radiusX: root.diskRadius; radiusY: root.diskRadius
            startAngle: 0; sweepAngle: 360
        }
    }
    ShapePath {
        strokeWidth: 0.8
        strokeColor: root.borderColor
        fillColor: root.fillColor
        PathAngleArc {
            centerX: root.width * 0.5; centerY: root.height * 0.5
            radiusX: root.diskRadius; radiusY: root.diskRadius
            startAngle: 0; sweepAngle: 360
        }
    }
}
