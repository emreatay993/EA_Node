import QtQuick 2.15
import QtQuick.Effects

Item {
    id: root
    objectName: "graphNodeChromeBackgroundLayer"
    property Item host: null
    property var notchCutoutCenters: ({"left": [], "right": []})
    readonly property bool notchMaskActive: !!root.host
        && root.host._notchedPortsEffective
        && ((root.notchCutoutCenters.left || []).length > 0
            || (root.notchCutoutCenters.right || []).length > 0)
    readonly property url notchMaskSvgSource: root._notchMaskSvgSource()
    readonly property bool cacheActive: !!root.host && root.host.chromeShadowCacheActive
    readonly property string cacheKey: root.host ? root.host.chromeShadowCacheKey : ""
    readonly property bool chromeCacheActive: root.host ? root.host.chromeCacheActive : false
    readonly property bool shadowCacheActive: root.host ? root.host.shadowCacheActive : false
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

    function _svgNumber(value) {
        return Number(value).toFixed(3).replace(/\.?0+$/, "");
    }

    function _notchMaskSvgSource() {
        if (!root.notchMaskActive)
            return "";
        var resolvedWidth = Math.max(1.0, Number(root.width));
        var resolvedHeight = Math.max(1.0, Number(root.height));
        var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + root._svgNumber(resolvedWidth)
            + '" height="' + root._svgNumber(resolvedHeight) + '" viewBox="0 0 '
            + root._svgNumber(resolvedWidth) + ' ' + root._svgNumber(resolvedHeight) + '">'
            + '<mask id="port-notches" maskUnits="userSpaceOnUse">'
            + '<rect width="100%" height="100%" fill="white"/>';
        var left = root.notchCutoutCenters.left || [];
        var right = root.notchCutoutCenters.right || [];
        for (var leftIndex = 0; leftIndex < left.length; ++leftIndex)
            svg += '<circle cx="0" cy="' + root._svgNumber(left[leftIndex]) + '" r="9" fill="black"/>';
        for (var rightIndex = 0; rightIndex < right.length; ++rightIndex)
            svg += '<circle cx="' + root._svgNumber(resolvedWidth) + '" cy="'
                + root._svgNumber(right[rightIndex]) + '" r="9" fill="black"/>';
        svg += '</mask><rect width="100%" height="100%" fill="white" mask="url(#port-notches)"/></svg>';
        return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    }

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

    Rectangle {
        id: cardChrome
        objectName: "graphNodeChrome"
        anchors.fill: parent
        z: 3
        visible: root.host ? (root.host._useHostChrome || root.selectedChromeFreeOutlineOnly) : false
        color: root.host && (root.host.bodyGradientActive || root.selectedChromeFreeOutlineOnly)
            ? "transparent"
            : (root.host ? root.host.surfaceColor : "transparent")
        border.width: root.effectiveBorderWidth
        border.color: root.effectiveOutlineColor
        radius: root.host ? root.host.resolvedCornerRadius : 0
        layer.enabled: root.chromeCacheActive
        layer.effect: MultiEffect {
            maskEnabled: root.notchMaskActive && notchMask.status === Image.Ready
            maskSource: notchMask
        }

        GraphNodeGradientFill {
            objectName: "graphNodeBodyGradientFill"
            visible: root.host ? root.host.bodyGradientActive : false
            anchors.fill: parent
            anchors.margins: Math.max(0, root.effectiveBorderWidth)
            startColor: root.host ? root.host.bodyGradientStartColor : "transparent"
            endColor: root.host ? root.host.bodyGradientEndColor : "transparent"
            direction: root.host ? root.host.bodyGradientDirection : "south"
            cornerRadius: root.host
                ? Math.max(0, root.host.resolvedCornerRadius - Math.max(0, root.effectiveBorderWidth))
                : 0
        }

        Loader {
            id: lockedHatchLoader
            anchors.fill: parent
            active: root.host ? root.host.lockedPlaceholderActive : false
            asynchronous: true
            visible: active

            sourceComponent: Canvas {
                objectName: "graphNodeLockedHatchOverlay"
                antialiasing: true
                opacity: 0.22
                renderTarget: Canvas.FramebufferObject
                renderStrategy: Canvas.Cooperative
                layer.enabled: true
                layer.smooth: true

                readonly property real cornerRadius: root.host ? Number(root.host.resolvedCornerRadius) : 8
                readonly property color hatchColor: "#e8a838"
                readonly property real hatchSpacing: 8.0

                onPaint: {
                    var ctx = getContext("2d");
                    ctx.reset();
                    if (width <= 2 || height <= 2)
                        return;

                    var r = Math.max(0, Math.min(cornerRadius, Math.min(width, height) / 2));
                    ctx.beginPath();
                    ctx.moveTo(r, 0);
                    ctx.lineTo(width - r, 0);
                    ctx.quadraticCurveTo(width, 0, width, r);
                    ctx.lineTo(width, height - r);
                    ctx.quadraticCurveTo(width, height, width - r, height);
                    ctx.lineTo(r, height);
                    ctx.quadraticCurveTo(0, height, 0, height - r);
                    ctx.lineTo(0, r);
                    ctx.quadraticCurveTo(0, 0, r, 0);
                    ctx.closePath();
                    ctx.clip();

                    ctx.strokeStyle = String(hatchColor);
                    ctx.lineWidth = 1;

                    ctx.translate(width / 2, height / 2);
                    ctx.rotate(Math.PI / 4);
                    ctx.translate(-width / 2, -height / 2);

                    var diag = Math.ceil(Math.sqrt(width * width + height * height)) + 16;
                    ctx.beginPath();
                    for (var x = -diag; x <= width + diag; x += hatchSpacing) {
                        ctx.moveTo(x + 0.5, -diag);
                        ctx.lineTo(x + 0.5, height + diag);
                    }
                    ctx.stroke();
                }

                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onCornerRadiusChanged: requestPaint()
                Component.onCompleted: requestPaint()
            }
        }
    }

    Image {
        id: notchMask
        objectName: "graphNodeChromeNotchMask"
        visible: false
        width: root.width
        height: root.height
        sourceSize: Qt.size(Math.max(1, Math.ceil(width)), Math.max(1, Math.ceil(height)))
        source: root.notchMaskSvgSource
        cache: true
        asynchronous: false
        smooth: true
        mipmap: false
        fillMode: Image.Stretch
    }
}
