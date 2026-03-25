import QtQuick 2.15

Item {
    id: surface
    objectName: "graphNodeViewerSurface"
    property Item host: null
    readonly property var viewerPayload: host && host.nodeData && host.nodeData.viewer_surface
        ? host.nodeData.viewer_surface
        : ({})
    readonly property bool proxySurfaceSupported: viewerPayload.proxy_surface_supported === undefined
        ? true
        : Boolean(viewerPayload.proxy_surface_supported)
    readonly property bool liveSurfaceSupported: viewerPayload.live_surface_supported === undefined
        ? true
        : Boolean(viewerPayload.live_surface_supported)
    readonly property string overlayTarget: String(viewerPayload.overlay_target || "body")
    readonly property rect surfaceBodyRect: _resolvedRect(viewerPayload.body_rect, _defaultBodyRect())
    readonly property rect proxySurfaceRect: _resolvedRect(viewerPayload.proxy_rect, surfaceBodyRect)
    readonly property rect liveSurfaceRect: _resolvedRect(viewerPayload.live_rect, surfaceBodyRect)
    readonly property bool proxySurfaceActive: proxySurfaceSupported && host
        ? Boolean(host.proxySurfaceRequested || String(host.resolvedQualityTier || "") === "proxy")
        : false
    readonly property bool liveSurfaceActive: liveSurfaceSupported && !proxySurfaceActive
    readonly property bool blocksHostInteraction: false
    readonly property var embeddedInteractiveRects: []
    readonly property var viewerSurfaceContract: ({
        "body_rect": _rectPayload(surfaceBodyRect),
        "proxy_rect": _rectPayload(proxySurfaceRect),
        "live_rect": _rectPayload(liveSurfaceRect),
        "overlay_target": overlayTarget,
        "proxy_surface_supported": proxySurfaceSupported,
        "live_surface_supported": liveSurfaceSupported
    })
    implicitHeight: host ? Number(host.surfaceMetrics.body_height || 0) : 0

    function _number(value, fallback) {
        var numeric = Number(value);
        return isFinite(numeric) ? numeric : fallback;
    }

    function _defaultBodyRect() {
        if (!host || !host.surfaceMetrics)
            return Qt.rect(0.0, 0.0, 0.0, 0.0);
        var metrics = host.surfaceMetrics;
        var x = Math.max(0.0, _number(metrics.body_left_margin, 0.0));
        var y = Math.max(0.0, _number(metrics.body_top, 0.0));
        var width = Math.max(
            0.0,
            _number(host.width, 0.0)
            - x
            - Math.max(0.0, _number(metrics.body_right_margin, 0.0))
        );
        var height = Math.max(
            0.0,
            Math.min(
                Math.max(0.0, _number(metrics.body_height, 0.0)),
                Math.max(0.0, _number(host.height, 0.0) - y)
            )
        );
        return Qt.rect(x, y, width, height);
    }

    function _resolvedRect(value, fallbackRect) {
        var fallback = fallbackRect || Qt.rect(0.0, 0.0, 0.0, 0.0);
        var x = Math.max(0.0, _number(value && value.x, fallback.x));
        var y = Math.max(0.0, _number(value && value.y, fallback.y));
        var width = Math.max(0.0, _number(value && value.width, fallback.width));
        var height = Math.max(0.0, _number(value && value.height, fallback.height));
        return Qt.rect(x, y, width, height);
    }

    function _rectPayload(rectLike) {
        return {
            "x": Math.max(0.0, _number(rectLike && rectLike.x, 0.0)),
            "y": Math.max(0.0, _number(rectLike && rectLike.y, 0.0)),
            "width": Math.max(0.0, _number(rectLike && rectLike.width, 0.0)),
            "height": Math.max(0.0, _number(rectLike && rectLike.height, 0.0))
        };
    }

    Item {
        id: bodyFrame
        objectName: "graphNodeViewerBodyFrame"
        x: surface.surfaceBodyRect.x
        y: surface.surfaceBodyRect.y
        width: surface.surfaceBodyRect.width
        height: surface.surfaceBodyRect.height
        clip: true

        Rectangle {
            anchors.fill: parent
            radius: host ? Math.max(8, Number(host.resolvedCornerRadius || 6) - 1) : 8
            color: host ? Qt.darker(host.inlineInputBackgroundColor, 1.04) : "#1a202b"
            border.width: 1
            border.color: host
                ? (surface.proxySurfaceActive ? Qt.alpha(host.outlineColor, 0.92) : Qt.alpha(host.selectedOutlineColor, 0.9))
                : "#5da9ff"
        }

        Rectangle {
            id: modePill
            objectName: "graphNodeViewerModePill"
            anchors.top: parent.top
            anchors.topMargin: 10
            anchors.right: parent.right
            anchors.rightMargin: 10
            radius: height * 0.5
            width: modeLabel.implicitWidth + 18
            height: modeLabel.implicitHeight + 8
            color: surface.proxySurfaceActive
                ? (host ? Qt.alpha(host.scopeBadgeColor, 0.24) : "#1f3657")
                : (host ? Qt.alpha(host.selectedOutlineColor, 0.2) : "#244770")
            border.width: 1
            border.color: surface.proxySurfaceActive
                ? (host ? Qt.alpha(host.scopeBadgeBorderColor, 0.92) : "#4c7bc0")
                : (host ? Qt.alpha(host.selectedOutlineColor, 0.95) : "#5da9ff")

            Text {
                id: modeLabel
                objectName: "graphNodeViewerSurfaceModeLabel"
                anchors.centerIn: parent
                text: surface.proxySurfaceActive ? "Proxy Surface" : "Live Surface"
                color: host ? host.headerTextColor : "#eef3ff"
                font.pixelSize: 11
                font.bold: true
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }
        }

        Rectangle {
            objectName: "graphNodeViewerProxyPane"
            visible: surface.proxySurfaceActive
            anchors.fill: parent
            anchors.margins: 12
            radius: 6
            color: host ? Qt.alpha(host.surfaceColor, 0.16) : "#22304a"
            border.width: 1
            border.color: host ? Qt.alpha(host.scopeBadgeBorderColor, 0.88) : "#4c7bc0"
        }

        Rectangle {
            objectName: "graphNodeViewerLivePane"
            visible: surface.liveSurfaceActive
            anchors.fill: parent
            anchors.margins: 12
            radius: 6
            color: "transparent"
            border.width: 1
            border.color: host ? Qt.alpha(host.selectedOutlineColor, 0.92) : "#5da9ff"
        }

        Column {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6

            Text {
                objectName: "graphNodeViewerSurfaceHeadline"
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: surface.proxySurfaceActive
                    ? "Proxy contract active"
                    : "Live overlay contract ready"
                color: host ? host.inlineInputTextColor : "#eef3ff"
                font.pixelSize: 15
                font.bold: true
                wrapMode: Text.WordWrap
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }

            Text {
                objectName: "graphNodeViewerSurfaceHint"
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: surface.proxySurfaceActive
                    ? "QML owns the proxy pane until a live viewer session takes over."
                    : "The node body stays reserved for a native viewer overlay handoff."
                color: host ? host.inlineDrivenTextColor : "#bdc5d3"
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }

            Text {
                objectName: "graphNodeViewerSurfaceTarget"
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: "Overlay target: " + surface.overlayTarget
                color: host ? host.inlineLabelColor : "#d5dbea"
                font.pixelSize: 10
                font.bold: true
                wrapMode: Text.WordWrap
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }
        }
    }
}
