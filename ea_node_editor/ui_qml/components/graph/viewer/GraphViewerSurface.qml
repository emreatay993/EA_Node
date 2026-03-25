import QtQuick 2.15
import QtQuick.Controls 2.15
import "../surface_controls" as GraphSurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry

Item {
    id: surface
    objectName: "graphNodeViewerSurface"
    property Item host: null
    readonly property var viewerPayload: host && host.nodeData && host.nodeData.viewer_surface
        ? host.nodeData.viewer_surface
        : ({})
    readonly property var viewerSessionBridgeRef: typeof viewerSessionBridge !== "undefined"
        ? viewerSessionBridge
        : null
    readonly property bool viewerBridgeAvailable: viewerSessionBridgeRef !== null
    readonly property var bridgeSessionsModel: viewerBridgeAvailable
        ? viewerSessionBridgeRef.sessions_model
        : []
    readonly property string viewerNodeId: host && host.nodeData
        ? String(host.nodeData.node_id || "")
        : ""
    readonly property var viewerSessionState: {
        var sessions = surface.bridgeSessionsModel;
        for (var index = 0; index < sessions.length; index++) {
            var session = sessions[index];
            if (String(session && session.node_id || "") === surface.viewerNodeId)
                return session;
        }
        return ({});
    }
    readonly property var viewerSummary: viewerSessionState.summary ? viewerSessionState.summary : ({})
    readonly property var viewerOptions: viewerSessionState.options ? viewerSessionState.options : ({})
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
    readonly property bool proxySurfaceRequested: host
        ? Boolean(host.proxySurfaceRequested || String(host.resolvedQualityTier || "") === "proxy")
        : false
    readonly property string viewerSessionId: String(viewerSessionState.session_id || "")
    readonly property string viewerPhase: String(viewerSessionState.phase || "closed")
    readonly property string viewerPlaybackState: String(viewerSessionState.playback_state || "paused")
    readonly property int viewerStepIndex: Math.max(0, Math.floor(_number(viewerSessionState.step_index, 0)))
    readonly property string viewerLivePolicy: String(viewerSessionState.live_policy || "focus_only")
    readonly property bool viewerKeepLive: Boolean(viewerSessionState.keep_live)
    readonly property string viewerCacheState: String(viewerSessionState.cache_state || "empty")
    readonly property string viewerLiveMode: {
        var liveMode = String(surface.viewerOptions.live_mode || surface.viewerSessionState.live_mode || "");
        if (liveMode.length > 0)
            return liveMode;
        if (surface.viewerPhase === "open")
            return surface.proxySurfaceRequested ? "proxy" : "full";
        if (surface.viewerPhase === "opening" || surface.viewerPhase === "closing")
            return "proxy";
        return surface.proxySurfaceRequested ? "proxy" : "reserved";
    }
    readonly property string viewerLastError: {
        var sessionError = String(surface.viewerSessionState.last_error || "");
        if (sessionError.length > 0)
            return sessionError;
        if (surface.viewerBridgeAvailable)
            return String(surface.viewerSessionBridgeRef.last_error || "");
        return "";
    }
    readonly property string viewerResultLabel: String(
        viewerSummary.result_name
        || viewerSummary.result_label
        || (host && host.nodeData ? host.nodeData.title || "" : "")
    )
    readonly property string viewerSetLabel: String(viewerSummary.set_label || viewerSummary.time_label || "")
    readonly property string viewerInvalidatedReason: String(
        viewerSessionState.invalidated_reason
        || viewerSummary.invalidated_reason
        || ""
    )
    readonly property string viewerCloseReason: String(
        viewerSessionState.close_reason
        || viewerSummary.close_reason
        || ""
    )
    readonly property string viewerDemotedReason: String(viewerSummary.demoted_reason || "")
    readonly property bool viewerSessionOpen: viewerPhase === "open"
    readonly property bool viewerSessionBusy: viewerPhase === "opening" || viewerPhase === "closing"
    readonly property bool viewerCanOpen: viewerBridgeAvailable
        && viewerNodeId.length > 0
        && (viewerPhase === "closed" || viewerPhase === "invalidated" || viewerPhase === "error")
    readonly property bool viewerCanClose: viewerBridgeAvailable
        && viewerNodeId.length > 0
        && !viewerCanOpen
        && viewerPhase !== "closed"
        && viewerPhase !== "invalidated"
    readonly property bool viewerCanControlPlayback: viewerBridgeAvailable && viewerSessionOpen
    readonly property bool viewerPlaying: viewerPlaybackState === "playing"
    readonly property string sessionButtonText: viewerPhase === "opening"
        ? "Opening"
        : (viewerPhase === "closing"
            ? "Closing"
            : (viewerCanOpen ? "Open" : "Close"))
    readonly property string playbackButtonText: viewerPlaying ? "Pause" : "Play"
    readonly property string viewerStatusLabel: {
        if (!surface.viewerBridgeAvailable)
            return "Viewer bridge unavailable";
        if (surface.viewerPhase === "opening")
            return "Opening viewer session";
        if (surface.viewerPhase === "closing")
            return "Closing viewer session";
        if (surface.viewerPhase === "invalidated")
            return "Viewer session invalidated";
        if (surface.viewerPhase === "error")
            return surface.viewerLastError.length > 0 ? surface.viewerLastError : "Viewer session failed";
        if (surface.viewerSessionOpen && surface.viewerLiveMode === "full")
            return "Live overlay active";
        if (surface.viewerSessionOpen)
            return "Proxy viewer ready";
        return "Ready to open viewer session";
    }
    readonly property string viewerHintText: {
        if (surface.viewerPhase === "invalidated") {
            if (surface.viewerInvalidatedReason.length > 0)
                return "Invalidated: " + surface.viewerInvalidatedReason;
            return "The existing viewer session was invalidated and must be reopened.";
        }
        if (surface.viewerPhase === "error") {
            if (surface.viewerLastError.length > 0)
                return surface.viewerLastError;
            return "The last viewer action failed and the proxy surface remains active.";
        }
        if (surface.viewerCloseReason.length > 0 && surface.viewerPhase === "closed")
            return "Closed: " + surface.viewerCloseReason;
        if (surface.viewerDemotedReason.length > 0)
            return "Demoted to proxy: " + surface.viewerDemotedReason;
        if (surface.viewerSessionOpen && surface.viewerLiveMode === "full")
            return "The node body stays reserved for a native viewer overlay handoff.";
        if (surface.viewerSessionOpen)
            return "QML owns the proxy pane while the bridge tracks the active session.";
        return "Use the quick actions to open the viewer session or inspect the proxy surface.";
    }
    readonly property string viewerModeBadgeText: {
        if (surface.viewerPhase === "opening")
            return "Opening";
        if (surface.viewerPhase === "closing")
            return "Closing";
        if (surface.viewerSessionOpen && surface.viewerLiveMode === "full")
            return "Live";
        if (surface.proxySurfaceActive)
            return "Proxy";
        return "Overlay";
    }
    readonly property color viewerAccentColor: {
        if (surface.viewerPhase === "error" || surface.viewerPhase === "invalidated")
            return "#D94F4F";
        if (surface.viewerPhase === "opening" || surface.viewerPhase === "closing")
            return "#D98B4B";
        if (surface.viewerSessionOpen && surface.viewerLiveMode === "full")
            return "#67D487";
        return "#5DA9FF";
    }
    readonly property bool proxySurfaceActive: {
        if (!surface.proxySurfaceSupported)
            return false;
        if (surface.viewerPhase === "opening" || surface.viewerPhase === "closing")
            return true;
        if (surface.viewerSessionOpen)
            return surface.viewerLiveMode !== "full";
        if (surface.viewerPhase === "invalidated" || surface.viewerPhase === "error")
            return true;
        return surface.proxySurfaceRequested;
    }
    readonly property bool liveSurfaceActive: {
        if (!surface.liveSurfaceSupported)
            return false;
        if (surface.viewerSessionOpen)
            return surface.viewerLiveMode === "full";
        if (surface.viewerPhase === "opening" || surface.viewerPhase === "closing")
            return false;
        return !surface.proxySurfaceActive;
    }
    readonly property bool blocksHostInteraction: false
    readonly property var viewerInteractiveRects: SurfaceControlGeometry.combineRectLists(
        [
            sessionButton.embeddedInteractiveRects,
            playPauseButton.embeddedInteractiveRects,
            stepButton.embeddedInteractiveRects,
            keepLiveButton.embeddedInteractiveRects,
            focusPolicyChip.embeddedInteractiveRects,
            keepPolicyChip.embeddedInteractiveRects
        ]
    )
    readonly property var embeddedInteractiveRects: viewerInteractiveRects
    readonly property var viewerBridgeBinding: ({
        "node_id": viewerNodeId,
        "bridge_available": viewerBridgeAvailable,
        "session_id": viewerSessionId,
        "phase": viewerPhase,
        "playback_state": viewerPlaybackState,
        "step_index": viewerStepIndex,
        "live_policy": viewerLivePolicy,
        "keep_live": viewerKeepLive,
        "cache_state": viewerCacheState,
        "live_mode": viewerLiveMode,
        "last_error": viewerLastError
    })
    readonly property var viewerSurfaceContract: ({
        "body_rect": _rectPayload(surfaceBodyRect),
        "proxy_rect": _rectPayload(proxySurfaceRect),
        "live_rect": _rectPayload(liveSurfaceRect),
        "overlay_target": overlayTarget,
        "proxy_surface_supported": proxySurfaceSupported,
        "live_surface_supported": liveSurfaceSupported,
        "interactive_rects": _rectListPayload(viewerInteractiveRects),
        "bridge_binding": viewerBridgeBinding
    })
    readonly property var viewerBadgeModel: [
        {
            "object_name": "graphNodeViewerPhaseBadge",
            "text": "Phase " + String(surface.viewerPhase || "closed")
        },
        {
            "object_name": "graphNodeViewerCacheBadge",
            "text": "Cache " + String(surface.viewerCacheState || "empty")
        },
        {
            "object_name": "graphNodeViewerLiveModeBadge",
            "text": "Mode " + String(surface.viewerLiveMode || "proxy")
        }
    ]
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

    function _rectListPayload(rects) {
        var normalized = [];
        if (!rects)
            return normalized;
        for (var index = 0; index < rects.length; index++)
            normalized.push(_rectPayload(rects[index]));
        return normalized;
    }

    function _beginSurfaceControl() {
        if (host && host.nodeData)
            host.surfaceControlInteractionStarted(String(host.nodeData.node_id || ""));
    }

    function requestSessionToggle() {
        if (!viewerBridgeAvailable || !viewerNodeId.length || viewerSessionBusy)
            return false;
        if (viewerCanOpen) {
            if (!viewerSessionBridgeRef.open)
                return false;
            return String(viewerSessionBridgeRef.open(viewerNodeId) || "").length > 0;
        }
        if (!viewerSessionBridgeRef.close)
            return false;
        return Boolean(viewerSessionBridgeRef.close(viewerNodeId));
    }

    function requestPlayPause() {
        if (!viewerCanControlPlayback)
            return false;
        if (viewerPlaying) {
            if (!viewerSessionBridgeRef.pause)
                return false;
            return Boolean(viewerSessionBridgeRef.pause(viewerNodeId));
        }
        if (!viewerSessionBridgeRef.play)
            return false;
        return Boolean(viewerSessionBridgeRef.play(viewerNodeId));
    }

    function requestStep() {
        if (!viewerCanControlPlayback || !viewerSessionBridgeRef.step)
            return false;
        return Boolean(viewerSessionBridgeRef.step(viewerNodeId));
    }

    function requestLivePolicy(policyName) {
        if (!viewerCanControlPlayback || !viewerSessionBridgeRef.set_live_policy)
            return false;
        return Boolean(viewerSessionBridgeRef.set_live_policy(viewerNodeId, String(policyName || "focus_only")));
    }

    function requestKeepLiveToggle() {
        if (!viewerCanControlPlayback || !viewerSessionBridgeRef.set_keep_live)
            return false;
        return Boolean(viewerSessionBridgeRef.set_keep_live(viewerNodeId, !viewerKeepLive));
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
                ? (surface.proxySurfaceActive
                    ? Qt.alpha(host.outlineColor, 0.92)
                    : Qt.alpha(host.selectedOutlineColor, 0.9))
                : "#5da9ff"
        }

        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            Row {
                id: quickActionsRow
                objectName: "graphNodeViewerQuickActions"
                spacing: 6

                GraphSurfaceControls.GraphSurfaceButton {
                    id: sessionButton
                    objectName: "graphNodeViewerSessionButton"
                    host: surface.host
                    text: surface.sessionButtonText
                    enabled: surface.viewerBridgeAvailable
                        && surface.viewerNodeId.length > 0
                        && !surface.viewerSessionBusy
                    accentColor: surface.viewerCanOpen ? "#67D487" : "#D98B4B"
                    baseFillColor: Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.96)
                    baseBorderColor: Qt.alpha(surface.viewerAccentColor, 0.55)
                    onControlStarted: surface._beginSurfaceControl()
                    onClicked: surface.requestSessionToggle()
                }

                GraphSurfaceControls.GraphSurfaceButton {
                    id: playPauseButton
                    objectName: "graphNodeViewerPlayPauseButton"
                    host: surface.host
                    text: surface.playbackButtonText
                    enabled: surface.viewerCanControlPlayback
                    accentColor: surface.viewerPlaying ? "#D98B4B" : "#5DA9FF"
                    baseFillColor: Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.96)
                    baseBorderColor: Qt.alpha(surface.viewerPlaying ? "#D98B4B" : "#5DA9FF", 0.45)
                    onControlStarted: surface._beginSurfaceControl()
                    onClicked: surface.requestPlayPause()
                }

                GraphSurfaceControls.GraphSurfaceButton {
                    id: stepButton
                    objectName: "graphNodeViewerStepButton"
                    host: surface.host
                    text: "Step"
                    enabled: surface.viewerCanControlPlayback
                    accentColor: "#7AA8FF"
                    baseFillColor: Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.96)
                    baseBorderColor: Qt.alpha("#7AA8FF", 0.5)
                    onControlStarted: surface._beginSurfaceControl()
                    onClicked: surface.requestStep()
                }

                GraphSurfaceControls.GraphSurfaceButton {
                    id: keepLiveButton
                    objectName: "graphNodeViewerKeepLiveButton"
                    host: surface.host
                    text: surface.viewerKeepLive ? "Pinned" : "Pin"
                    enabled: surface.viewerCanControlPlayback
                    accentColor: surface.viewerKeepLive ? "#67D487" : "#A0A8C0"
                    baseFillColor: surface.viewerKeepLive
                        ? Qt.alpha("#67D487", 0.22)
                        : Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.96)
                    baseBorderColor: surface.viewerKeepLive
                        ? Qt.alpha("#67D487", 0.75)
                        : Qt.alpha("#A0A8C0", 0.38)
                    onControlStarted: surface._beginSurfaceControl()
                    onClicked: surface.requestKeepLiveToggle()
                }
            }

            Row {
                id: policyRow
                objectName: "graphNodeViewerPolicyRow"
                spacing: 6

                GraphSurfaceControls.GraphSurfaceButton {
                    id: focusPolicyChip
                    objectName: "graphNodeViewerFocusPolicyChip"
                    host: surface.host
                    text: "Focus"
                    enabled: surface.viewerCanControlPlayback
                    accentColor: "#5DA9FF"
                    baseFillColor: surface.viewerLivePolicy === "focus_only"
                        ? Qt.alpha("#5DA9FF", 0.24)
                        : Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.92)
                    baseBorderColor: surface.viewerLivePolicy === "focus_only"
                        ? Qt.alpha("#5DA9FF", 0.82)
                        : Qt.alpha("#5DA9FF", 0.3)
                    onControlStarted: surface._beginSurfaceControl()
                    onClicked: surface.requestLivePolicy("focus_only")
                }

                GraphSurfaceControls.GraphSurfaceButton {
                    id: keepPolicyChip
                    objectName: "graphNodeViewerKeepPolicyChip"
                    host: surface.host
                    text: "Keep"
                    enabled: surface.viewerCanControlPlayback
                    accentColor: "#67D487"
                    baseFillColor: surface.viewerLivePolicy === "keep_live"
                        ? Qt.alpha("#67D487", 0.24)
                        : Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.92)
                    baseBorderColor: surface.viewerLivePolicy === "keep_live"
                        ? Qt.alpha("#67D487", 0.82)
                        : Qt.alpha("#67D487", 0.3)
                    onControlStarted: surface._beginSurfaceControl()
                    onClicked: surface.requestLivePolicy("keep_live")
                }

                Rectangle {
                    id: modePill
                    objectName: "graphNodeViewerModePill"
                    radius: height * 0.5
                    height: modeLabel.implicitHeight + 8
                    width: modeLabel.implicitWidth + 18
                    color: Qt.alpha(surface.viewerAccentColor, 0.22)
                    border.width: 1
                    border.color: Qt.alpha(surface.viewerAccentColor, 0.82)

                    Text {
                        id: modeLabel
                        objectName: "graphNodeViewerSurfaceModeLabel"
                        anchors.centerIn: parent
                        text: surface.viewerModeBadgeText
                        color: host ? host.headerTextColor : "#eef3ff"
                        font.pixelSize: 11
                        font.bold: true
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }
                }
            }

            Item {
                id: contentPane
                width: parent.width
                height: Math.max(72, bodyFrame.height - quickActionsRow.height - policyRow.height - 40)

                Rectangle {
                    objectName: "graphNodeViewerProxyPane"
                    visible: surface.proxySurfaceActive
                    anchors.fill: parent
                    radius: 6
                    color: host ? Qt.alpha(host.surfaceColor, 0.16) : "#22304a"
                    border.width: 1
                    border.color: host ? Qt.alpha(host.scopeBadgeBorderColor, 0.88) : "#4c7bc0"
                }

                Rectangle {
                    objectName: "graphNodeViewerLivePane"
                    visible: surface.liveSurfaceActive
                    anchors.fill: parent
                    radius: 6
                    color: host ? Qt.alpha(host.selectedOutlineColor, 0.08) : "#11243d"
                    border.width: 1
                    border.color: host ? Qt.alpha(host.selectedOutlineColor, 0.92) : "#5da9ff"
                }

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text {
                        objectName: "graphNodeViewerSurfaceHeadline"
                        width: parent.width
                        text: surface.viewerStatusLabel
                        color: host ? host.inlineInputTextColor : "#eef3ff"
                        font.pixelSize: 14
                        font.bold: true
                        wrapMode: Text.WordWrap
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    Text {
                        objectName: "graphNodeViewerSurfaceHint"
                        width: parent.width
                        text: surface.viewerHintText
                        color: host ? host.inlineDrivenTextColor : "#bdc5d3"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    Flow {
                        width: parent.width
                        spacing: 6

                        Repeater {
                            model: surface.viewerBadgeModel

                            Rectangle {
                                objectName: modelData.object_name
                                radius: 10
                                color: Qt.alpha(surface.viewerAccentColor, 0.18)
                                border.width: 1
                                border.color: Qt.alpha(surface.viewerAccentColor, 0.58)
                                height: badgeLabel.implicitHeight + 8
                                width: badgeLabel.implicitWidth + 12

                                Text {
                                    id: badgeLabel
                                    anchors.centerIn: parent
                                    text: modelData.text
                                    color: host ? host.headerTextColor : "#eef3ff"
                                    font.pixelSize: 10
                                    font.bold: true
                                    renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                                }
                            }
                        }
                    }

                    Text {
                        visible: surface.viewerResultLabel.length > 0
                        width: parent.width
                        text: "Result: " + surface.viewerResultLabel
                        color: host ? host.inlineLabelColor : "#d5dbea"
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    Text {
                        visible: surface.viewerSetLabel.length > 0
                        width: parent.width
                        text: "Selection: " + surface.viewerSetLabel
                        color: host ? host.inlineLabelColor : "#d5dbea"
                        font.pixelSize: 10
                        elide: Text.ElideRight
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    Text {
                        objectName: "graphNodeViewerSurfaceTarget"
                        width: parent.width
                        text: "Overlay target: " + surface.overlayTarget + " | Step " + surface.viewerStepIndex
                        color: host ? host.inlineLabelColor : "#d5dbea"
                        font.pixelSize: 10
                        font.bold: true
                        wrapMode: Text.WordWrap
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }
                }
            }
        }
    }
}
