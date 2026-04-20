import QtQuick 2.15
import QtQuick.Effects

Item {
    id: root
    objectName: "graphNodeChromeBackgroundLayer"
    property Item host: null
    property real failurePulseProgress: 0.0
    property real runningPulseProgress: 0.0
    property real completedFlashProgress: 0.0
    readonly property bool cacheActive: !!root.host && root.host.chromeShadowCacheActive
    readonly property string cacheKey: root.host ? root.host.chromeShadowCacheKey : ""
    readonly property bool chromeCacheActive: root.host ? root.host.chromeCacheActive : false
    readonly property bool shadowCacheActive: root.host ? root.host.shadowCacheActive : false
    readonly property real effectiveBorderWidth: !root.host
        ? 0.0
        : (root.host.isFailedNode
            ? Math.max(root.host.resolvedBorderWidth, 2.4)
            : ((root.host.isRunningNode || root.host.isCompletedNode)
                ? Math.max(root.host.resolvedBorderWidth, 2.0)
                : root.host.resolvedBorderWidth))
    readonly property color effectiveOutlineColor: !root.host
        ? "transparent"
        : (root.host.isFailedNode
            ? root.host.failureOutlineColor
            : (root.host.isRunningNode
                ? root.host.runningOutlineColor
                : (root.host.isCompletedNode
                    ? root.host.completedOutlineColor
                    : (root.host.isSelected
                        ? root.host.selectedOutlineColor
                        : root.host.outlineColor))))
    readonly property string effectiveBorderState: !root.host
        ? "idle"
        : (root.host.isFailedNode
            ? "failed"
            : (root.host.isRunningNode
                ? "running"
                : (root.host.isCompletedNode
                    ? "completed"
                    : (root.host.isSelected ? "selected" : "idle"))))
    z: 0

    onHostChanged: {
        if (!root.host || !root.host.isFailedNode)
            root.failurePulseProgress = 0.0;
        if (!root.host || !root.host.isRunningNode)
            root.runningPulseProgress = 0.0;
        if (!root.host || !root.host.isCompletedNode)
            root.completedFlashProgress = 0.0;
    }

    SequentialAnimation {
        id: failurePulseAnimation
        loops: Animation.Infinite
        running: root.host ? root.host.isFailedNode : false

        NumberAnimation {
            target: root
            property: "failurePulseProgress"
            from: 0.0
            to: 1.0
            duration: 920
            easing.type: Easing.OutCubic
        }

        PauseAnimation {
            duration: 160
        }

        onRunningChanged: {
            if (!running)
                root.failurePulseProgress = 0.0;
        }
    }

    SequentialAnimation {
        id: runningPulseAnimation
        loops: Animation.Infinite
        running: root.host ? (root.host.isRunningNode && !root.host.isFailedNode) : false

        NumberAnimation {
            target: root
            property: "runningPulseProgress"
            from: 0.0
            to: 1.0
            duration: 1400
            easing.type: Easing.InOutSine
        }

        NumberAnimation {
            target: root
            property: "runningPulseProgress"
            from: 1.0
            to: 0.0
            duration: 1400
            easing.type: Easing.InOutSine
        }

        onRunningChanged: {
            if (!running)
                root.runningPulseProgress = 0.0;
        }
    }

    SequentialAnimation {
        id: completedFlashAnimation
        loops: 1
        running: false

        NumberAnimation {
            target: root
            property: "completedFlashProgress"
            from: 0.0
            to: 1.0
            duration: 300
            easing.type: Easing.OutCubic
        }

        PauseAnimation {
            duration: 600
        }

        NumberAnimation {
            target: root
            property: "completedFlashProgress"
            from: 1.0
            to: 0.0
            duration: 500
            easing.type: Easing.InCubic
        }

        onStopped: {
            if (!running)
                root.completedFlashProgress = 0.0;
        }
    }

    Connections {
        target: root.host

        function onFailurePulseRevisionChanged() {
            if (!root.host || !root.host.isFailedNode)
                return;
            root.failurePulseProgress = 0.0;
            failurePulseAnimation.restart();
        }

        function onIsCompletedNodeChanged() {
            if (!root.host || root.host.isFailedNode) {
                completedFlashAnimation.stop();
                root.completedFlashProgress = 0.0;
                return;
            }
            if (!root.host.isCompletedNode) {
                completedFlashAnimation.stop();
                root.completedFlashProgress = 0.0;
                return;
            }
            root.completedFlashProgress = 0.0;
            completedFlashAnimation.restart();
        }
    }

    RectangularShadow {
        id: cardShadow
        objectName: "graphNodeShadow"
        visible: root.host ? root.host._backgroundShadowVisible : false
        anchors.fill: parent
        z: 0
        offset.x: 0
        offset.y: root.host ? root.host.shadowOffset : 4
        // RectangularShadow blur is specified in pixels, not a normalized 0..1 range.
        blur: Math.max(0.0, (root.host ? root.host.shadowSoftness : 50) * 0.4)
        spread: Math.max(0.0, Math.min(1.0, (root.host ? root.host.shadowStrength : 70) / 100.0))
        radius: root.host ? root.host.resolvedCornerRadius : 0
        color: Qt.rgba(0, 0, 0, (root.host ? root.host.shadowStrength : 70) / 100.0)
        cached: root.shadowCacheActive
    }

    Rectangle {
        id: failureHalo
        objectName: "graphNodeFailureHalo"
        visible: root.host ? root.host.isFailedNode : false
        anchors.fill: parent
        anchors.margins: -7
        z: 1
        color: root.host ? Qt.alpha(root.host.failureGlowColor, 0.09) : "transparent"
        border.width: 2
        border.color: root.host ? Qt.alpha(root.host.failureOutlineColor, 0.88) : "transparent"
        radius: root.host ? root.host.resolvedCornerRadius + 7 : 0
    }

    Rectangle {
        id: failurePulseHalo
        objectName: "graphNodeFailurePulseHalo"
        visible: root.host ? root.host.isFailedNode : false
        anchors.fill: parent
        anchors.margins: -10
        z: 2
        color: "transparent"
        border.width: 2
        border.color: root.host
            ? Qt.alpha(root.host.failureGlowColor, Math.max(0.0, 0.82 - (root.failurePulseProgress * 0.62)))
            : "transparent"
        radius: root.host ? root.host.resolvedCornerRadius + 10 : 0
        opacity: root.host ? Math.max(0.0, 0.7 - (root.failurePulseProgress * 0.55)) : 0.0
        scale: 1.0 + (root.failurePulseProgress * 0.1)
        transformOrigin: Item.Center
    }

    Rectangle {
        id: runningHalo
        objectName: "graphNodeRunningHalo"
        visible: root.host ? (root.host.isRunningNode && !root.host.isFailedNode) : false
        anchors.fill: parent
        anchors.margins: -6
        z: 1
        color: root.host ? Qt.alpha(root.host.runningGlowColor, 0.06) : "transparent"
        border.width: 2
        border.color: root.host
            ? Qt.alpha(root.host.runningOutlineColor, 0.5 + (root.runningPulseProgress * 0.4))
            : "transparent"
        radius: root.host ? root.host.resolvedCornerRadius + 6 : 0
        opacity: 0.6 + (root.runningPulseProgress * 0.4)
    }

    Rectangle {
        id: runningPulseHalo
        objectName: "graphNodeRunningPulseHalo"
        visible: root.host ? (root.host.isRunningNode && !root.host.isFailedNode) : false
        anchors.fill: parent
        anchors.margins: -9
        z: 2
        color: "transparent"
        border.width: 1.5
        border.color: root.host
            ? Qt.alpha(root.host.runningGlowColor, Math.max(0.0, 0.5 * root.runningPulseProgress))
            : "transparent"
        radius: root.host ? root.host.resolvedCornerRadius + 9 : 0
        opacity: root.runningPulseProgress * 0.6
        scale: 1.0 + (root.runningPulseProgress * 0.06)
        transformOrigin: Item.Center
    }

    Rectangle {
        id: completedFlashHalo
        objectName: "graphNodeCompletedFlashHalo"
        visible: root.completedFlashProgress > 0.01 && (root.host ? !root.host.isFailedNode : true)
        anchors.fill: parent
        anchors.margins: -6
        z: 1
        color: "transparent"
        border.width: 2
        border.color: root.host
            ? Qt.alpha(root.host.completedGlowColor, root.completedFlashProgress * 0.7)
            : "transparent"
        radius: root.host ? root.host.resolvedCornerRadius + 6 : 0
        opacity: root.completedFlashProgress
        scale: 1.0 + ((1.0 - root.completedFlashProgress) * 0.04)
        transformOrigin: Item.Center
    }

    Rectangle {
        id: cardChrome
        objectName: "graphNodeChrome"
        anchors.fill: parent
        z: 3
        visible: root.host ? root.host._useHostChrome : false
        color: root.host ? root.host.surfaceColor : "transparent"
        border.width: root.effectiveBorderWidth
        border.color: root.effectiveOutlineColor
        radius: root.host ? root.host.resolvedCornerRadius : 0
        layer.enabled: root.chromeCacheActive

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
}
