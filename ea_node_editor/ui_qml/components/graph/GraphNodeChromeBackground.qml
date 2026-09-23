import QtQuick 2.15
import QtQuick.Effects
import QtQuick.Shapes
import "GraphNodeChromeGeometry.js" as ChromeGeometry

Item {
    id: root
    objectName: "graphNodeChromeBackgroundLayer"
    property Item host: null
    property var notchCutoutCenters: ({"left": [], "right": []})
    readonly property bool notchesEnabled: !!root.host && root.host._notchedPortsEffective
    readonly property bool shadowCacheActive: !!root.host && root.host.shadowCacheActive
    readonly property var silhouette: ChromeGeometry.build(
        root.width, root.height, root.host ? root.host.resolvedCornerRadius : 0,
        root.effectiveBorderWidth, root.notchesEnabled ? root.notchCutoutCenters : {}, 9)
    readonly property string fillPath: root.silhouette.fillPath
    readonly property string borderPath: root.silhouette.borderPath
    readonly property string hatchPath: root.host && root.host.lockedPlaceholderActive
        ? ChromeGeometry.hatch(root.width, root.height, root.host.resolvedCornerRadius,
            root.notchesEnabled ? root.notchCutoutCenters : {}, 9, 8) : ""
    readonly property string gradientDirection: root.host
        ? String(root.host.bodyGradientDirection || "south").toLowerCase() : "south"
    readonly property bool horizontalGradient: gradientDirection === "east" || gradientDirection === "west"
    readonly property bool reverseGradient: gradientDirection === "north" || gradientDirection === "west"
    readonly property color firstGradientColor: !root.host ? "transparent"
        : (root.reverseGradient ? root.host.bodyGradientEndColor : root.host.bodyGradientStartColor)
    readonly property color lastGradientColor: !root.host ? "transparent"
        : (root.reverseGradient ? root.host.bodyGradientStartColor : root.host.bodyGradientEndColor)
    readonly property bool selectedChromeFreeOutlineOnly: !!root.host
        && root.host.isSelected
        && !root.host._useHostChrome
        && !root.host.isFlowchartSurface
    readonly property bool suppressHorizontalGlowSpill: !!root.host
        && root.host._notchedPortsEffective

    readonly property real effectiveBorderWidth: !root.host
        ? 0.0
        : (root.host.isPassiveNode
            ? root.host.resolvedBorderWidth
            : (root.host.semanticChromeState === "error"
                ? Math.max(root.host.resolvedBorderWidth, 2.4)
                : (root.host.semanticChromeState === "warning"
                    ? Math.max(root.host.resolvedBorderWidth, 2.0)
                    : root.host.resolvedBorderWidth)))
    readonly property color effectiveOutlineColor: !root.host
        ? "transparent"
        : (root.host.isPassiveNode && root.host.isSelected
            ? root.host.selectedOutlineColor
            : root.host.outlineColor)
    readonly property string effectiveBorderState: !root.host
        ? "idle"
        : (root.host.isPassiveNode
            ? (root.host.isSelected ? "selected" : "idle")
            : (root.host.semanticChromeState === "error"
                ? "failed"
                : (root.host.semanticChromeState === "default"
                    ? "idle"
                    : root.host.semanticChromeState)))
    z: 0

    RectangularShadow {
        id: cardShadow
        objectName: "graphNodeShadow"
        readonly property real effectiveBlur: Math.max(0.0, (root.host ? root.host.shadowSoftness : 50) * 0.4)
        readonly property real horizontalInset: {
            if (!(root.host && root.host._notchedPortsEffective))
                return 0.0;
            var cornerRadius = Math.max(0.0, Number(root.host.resolvedCornerRadius));
            var maximumInset = Math.max(0.0, (Number(root.width) - (cornerRadius * 2.0) - 1.0) * 0.5);
            return Math.min(cardShadow.effectiveBlur, maximumInset);
        }
        visible: root.host ? root.host._backgroundShadowVisible : false
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: cardShadow.horizontalInset
        anchors.rightMargin: cardShadow.horizontalInset
        z: 0
        offset.x: 0
        offset.y: root.host ? root.host.shadowOffset : 4
        // RectangularShadow blur is specified in pixels, not a normalized 0..1 range.
        blur: cardShadow.effectiveBlur
        spread: Math.max(0.0, Math.min(1.0, (root.host ? root.host.shadowStrength : 70) / 100.0))
        radius: root.host ? root.host.resolvedCornerRadius : 0
        color: Qt.rgba(0, 0, 0, (root.host ? root.host.shadowStrength : 70) / 100.0)
        cached: root.shadowCacheActive
    }

    // Passive nodes retain their customizable selection aura. Active nodes use
    // the fixed selected fill and outline with no glow.
    Rectangle {
        id: selectedGlowSource
        objectName: "graphNodeSelectedGlowSource"
        anchors.fill: parent
        radius: root.host ? root.host.resolvedCornerRadius : 0
        color: root.host ? root.host.selectedGlowColor : "transparent"
        visible: false
    }
    MultiEffect {
        id: selectedHalo
        objectName: "graphNodeSelectedHalo"
        source: selectedGlowSource
        anchors.fill: selectedGlowSource
        z: 1
        autoPaddingEnabled: !root.suppressHorizontalGlowSpill
        paddingRect: root.suppressHorizontalGlowSpill
            ? Qt.rect(0, -blurMax, 0, blurMax * 2)
            : Qt.rect(0, 0, 0, 0)
        blurEnabled: true
        blur: 1.0
        blurMax: 40
        saturation: 0.35
        visible: opacity > 0.01
        opacity: (root.host
            && root.host.isSelected
            && root.host.isPassiveNode
            && !root.host.isFlowchartSurface
            && !root.selectedChromeFreeOutlineOnly) ? 0.85 : 0.0
        // Selection is direct click feedback: the glow must land with the click,
        // so only the fade-out gets the slow ease. A symmetric 160 ms ramp reads
        // as input lag.
        Behavior on opacity {
            NumberAnimation {
                duration: root.host && root.host.isSelected ? 50 : 160
                easing.type: Easing.InOutCubic
            }
        }
    }

    LinearGradient {
        id: bodyLinearGradient
        objectName: "graphNodeChromeLinearGradient"
        x1: root.effectiveBorderWidth
        y1: root.effectiveBorderWidth
        x2: root.horizontalGradient ? root.width - root.effectiveBorderWidth : x1
        y2: root.horizontalGradient ? y1 : root.height - root.effectiveBorderWidth
        GradientStop { position: 0; color: root.firstGradientColor }
        GradientStop { position: 1; color: root.lastGradientColor }
    }
    RadialGradient {
        id: bodyRadialGradient
        objectName: "graphNodeChromeRadialGradient"
        centerX: root.width / 2
        centerY: root.height / 2
        focalX: centerX
        focalY: centerY
        centerRadius: Math.max(0, Math.max(root.width, root.height) / 2 - root.effectiveBorderWidth)
        GradientStop { position: 0; color: root.host ? root.host.bodyGradientStartColor : "transparent" }
        GradientStop { position: 1; color: root.host ? root.host.bodyGradientEndColor : "transparent" }
    }

    Shape {
        id: cardChrome
        objectName: "graphNodeChrome"
        anchors.fill: parent
        z: 3
        visible: root.host ? (root.host._useHostChrome || root.selectedChromeFreeOutlineOnly) : false
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            objectName: "graphNodeChromeFill"
            fillRule: ShapePath.OddEvenFill
            strokeWidth: -1
            fillColor: root.selectedChromeFreeOutlineOnly ? "transparent"
                : (root.host ? root.host.surfaceColor : "transparent")
            fillGradient: root.host && root.host.bodyGradientActive && !root.selectedChromeFreeOutlineOnly
                ? (root.gradientDirection === "radial" ? bodyRadialGradient : bodyLinearGradient) : null
            PathSvg { path: root.fillPath }
        }
        ShapePath {
            objectName: "graphNodeChromeBorder"
            fillRule: ShapePath.OddEvenFill
            strokeWidth: -1
            fillColor: root.effectiveOutlineColor
            PathSvg { path: root.borderPath }
        }
        ShapePath {
            objectName: "graphNodeLockedHatchOverlay"
            fillColor: "transparent"
            strokeColor: Qt.rgba(232 / 255, 168 / 255, 56 / 255, 0.22)
            strokeWidth: 1
            capStyle: ShapePath.FlatCap
            PathSvg { path: root.hatchPath }
        }
    }
}
