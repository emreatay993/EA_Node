import QtQuick 2.15
import QtQuick.Effects

Item {
    id: root
    objectName: "graphNodeChromeBackgroundLayer"
    property Item host: null
    property real failurePulseProgress: 0.0
    readonly property bool cacheActive: !!root.host && root.host.chromeShadowCacheActive
    readonly property string cacheKey: root.host ? root.host.chromeShadowCacheKey : ""
    readonly property bool chromeCacheActive: root.host ? root.host.chromeCacheActive : false
    readonly property bool shadowCacheActive: root.host ? root.host.shadowCacheActive : false
    z: 0

    onHostChanged: {
        if (!root.host || !root.host.isFailedNode)
            root.failurePulseProgress = 0.0;
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

    Connections {
        target: root.host

        function onFailurePulseRevisionChanged() {
            if (!root.host || !root.host.isFailedNode)
                return;
            root.failurePulseProgress = 0.0;
            failurePulseAnimation.restart();
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
        id: cardChrome
        objectName: "graphNodeChrome"
        anchors.fill: parent
        z: 3
        visible: root.host ? root.host._useHostChrome : false
        color: root.host ? root.host.surfaceColor : "transparent"
        border.width: root.host
            ? (root.host.isFailedNode ? Math.max(root.host.resolvedBorderWidth, 2.4) : root.host.resolvedBorderWidth)
            : 0
        border.color: root.host
            ? (root.host.isFailedNode
                ? root.host.failureOutlineColor
                : (root.host.isSelected ? root.host.selectedOutlineColor : root.host.outlineColor))
            : "transparent"
        radius: root.host ? root.host.resolvedCornerRadius : 0
        layer.enabled: root.chromeCacheActive
    }
}
