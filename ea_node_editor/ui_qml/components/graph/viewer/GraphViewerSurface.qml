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
    readonly property string viewerBackendId: String(
        viewerSessionState.backend_id
        || viewerSummary.backend_id
        || viewerOptions.backend_id
        || ""
    )
    readonly property var viewerTransport: viewerSessionState.transport
        ? viewerSessionState.transport
        : ({})
    readonly property string viewerTransportKind: String(viewerTransport.kind || "")
    readonly property int viewerTransportRevision: Math.max(
        0,
        Math.floor(
            _number(
                viewerSessionState.transport_revision !== undefined
                    ? viewerSessionState.transport_revision
                    : (
                        viewerSummary.transport_revision !== undefined
                            ? viewerSummary.transport_revision
                            : viewerOptions.transport_revision
                    ),
                0
            )
        )
    )
    readonly property string viewerLiveOpenStatus: String(
        viewerSessionState.live_open_status
        || viewerSummary.live_open_status
        || viewerOptions.live_open_status
        || ""
    )
    readonly property var viewerLiveOpenBlocker: viewerSessionState.live_open_blocker
        ? viewerSessionState.live_open_blocker
        : (
            viewerSummary.live_open_blocker
            ? viewerSummary.live_open_blocker
            : (viewerOptions.live_open_blocker ? viewerOptions.live_open_blocker : ({}))
        )
    readonly property string viewerTransportReleaseReason: String(
        viewerSummary.live_transport_release_reason
        || viewerOptions.live_transport_release_reason
        || ""
    )
    readonly property bool viewerRunRequired: viewerPhase === "blocked"
        || viewerLiveOpenStatus === "blocked"
        || Boolean(viewerSummary.rerun_required)
        || Boolean(viewerOptions.rerun_required)
        || Boolean(viewerLiveOpenBlocker.rerun_required)
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
        && !viewerRunRequired
        && (viewerPhase === "closed" || viewerPhase === "invalidated" || viewerPhase === "error")
    readonly property bool viewerCanClose: viewerBridgeAvailable
        && viewerNodeId.length > 0
        && viewerSessionOpen
    readonly property bool viewerCanControlPlayback: viewerBridgeAvailable && viewerSessionOpen
    readonly property bool viewerPlaying: viewerPlaybackState === "playing"
    readonly property string sessionButtonText: viewerPhase === "opening"
        ? "Opening"
        : (viewerPhase === "closing"
            ? "Closing"
            : (viewerRunRequired ? "Blocked" : (viewerCanOpen ? "Open" : "Close")))
    readonly property string playbackButtonText: viewerPlaying ? "Pause" : "Play"
    readonly property string viewerStatusLabel: {
        if (!surface.viewerBridgeAvailable)
            return "Viewer bridge unavailable";
        if (surface.viewerPhase === "opening")
            return "Opening viewer session";
        if (surface.viewerPhase === "closing")
            return "Closing viewer session";
        if (surface.viewerRunRequired)
            return "Rerun required before live open";
        if (surface.viewerPhase === "invalidated")
            return "Viewer session invalidated";
        if (surface.viewerPhase === "error")
            return surface.viewerLastError.length > 0 ? surface.viewerLastError : "Viewer session failed";
        if (
            surface.viewerSessionOpen
            && surface.viewerLiveMode === "full"
            && surface.viewerLiveOpenStatus === "ready"
        ) {
            return "Live overlay active";
        }
        if (surface.viewerSessionOpen)
            return "Proxy viewer ready";
        return "Ready to open viewer session";
    }
    readonly property string viewerHintText: {
        if (surface.viewerRunRequired) {
            var blockerReason = String(surface.viewerLiveOpenBlocker.reason || "");
            var transportReleaseDetail = "";
            if (surface.viewerTransportReleaseReason === "project_reload")
                transportReleaseDetail = "Project reload cleared the live transport.";
            else if (surface.viewerTransportReleaseReason === "workspace_rerun")
                transportReleaseDetail = "The last workspace run replaced the live transport.";
            else if (surface.viewerTransportReleaseReason === "worker_reset")
                transportReleaseDetail = "The execution worker reset cleared the live transport.";
            if (blockerReason.length > 0 && transportReleaseDetail.length > 0)
                return blockerReason + " " + transportReleaseDetail;
            if (blockerReason.length > 0)
                return blockerReason;
            if (transportReleaseDetail.length > 0)
                return transportReleaseDetail;
            return "The saved viewer summary is available, but rerun is required before the live viewer can reopen.";
        }
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
        if (surface.viewerRunRequired)
            return "Blocked";
        if (
            surface.viewerSessionOpen
            && surface.viewerLiveMode === "full"
            && surface.viewerLiveOpenStatus === "ready"
        ) {
            return "Live";
        }
        if (surface.proxySurfaceActive)
            return "Proxy";
        return "Overlay";
    }
    readonly property color viewerAccentColor: {
        if (surface.viewerRunRequired || surface.viewerPhase === "error" || surface.viewerPhase === "invalidated")
            return "#D94F4F";
        if (surface.viewerPhase === "opening" || surface.viewerPhase === "closing")
            return "#D98B4B";
        if (
            surface.viewerSessionOpen
            && surface.viewerLiveMode === "full"
            && surface.viewerLiveOpenStatus === "ready"
        ) {
            return "#67D487";
        }
        return "#5DA9FF";
    }
    readonly property bool proxySurfaceActive: {
        if (!surface.proxySurfaceSupported)
            return false;
        if (surface.viewerPhase === "opening" || surface.viewerPhase === "closing")
            return true;
        if (surface.viewerRunRequired)
            return true;
        if (surface.viewerSessionOpen) {
            return surface.viewerLiveMode !== "full"
                || surface.viewerLiveOpenStatus.length > 0 && surface.viewerLiveOpenStatus !== "ready";
        }
        if (surface.viewerPhase === "invalidated" || surface.viewerPhase === "error")
            return true;
        return surface.proxySurfaceRequested;
    }
    readonly property bool liveSurfaceActive: {
        if (!surface.liveSurfaceSupported)
            return false;
        return surface.viewerSessionOpen
            && surface.viewerLiveMode === "full"
            && surface.viewerLiveOpenStatus === "ready";
    }
    readonly property bool viewerShowsPlaceholder: !surface.viewerSessionOpen || surface.viewerRunRequired
    readonly property string viewerSessionIconName: {
        if (surface.viewerPhase === "opening")
            return "run";
        if (surface.viewerPhase === "closing")
            return "stop";
        return surface.viewerCanOpen ? "run" : "stop";
    }
    readonly property string viewerPlayPauseIconName: surface.viewerPlaying ? "pause" : "run"
    readonly property string viewerPlaceholderIconName: {
        if (
            surface.viewerRunRequired
            || surface.viewerPhase === "error"
            || surface.viewerPhase === "invalidated"
            || surface.viewerPhase === "closing"
        ) {
            return "stop";
        }
        if (surface.viewerPhase === "opening")
            return "run";
        return surface.proxySurfaceActive ? "focus" : "run";
    }
    readonly property color viewerViewportBorderColor: surface.host
        ? Qt.alpha(
            surface.proxySurfaceActive
                ? surface.host.outlineColor
                : (surface.liveSurfaceActive ? surface.host.selectedOutlineColor : surface.viewerAccentColor),
            0.4
        )
        : Qt.alpha(surface.viewerAccentColor, 0.4)
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
        "last_error": viewerLastError,
        "backend_id": viewerBackendId,
        "transport": viewerTransport,
        "transport_kind": viewerTransportKind,
        "transport_revision": viewerTransportRevision,
        "live_open_status": viewerLiveOpenStatus,
        "live_open_blocker": viewerLiveOpenBlocker,
        "run_required": viewerRunRequired
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
    readonly property var viewerFooterMetaModel: _buildFooterMetaModel()
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

    function _iconSource(name, size, color) {
        if (typeof uiIcons === "undefined" || !uiIcons || !uiIcons.has(name))
            return "";
        return uiIcons.sourceSized(name, size, color);
    }

    function _appendFooterMeta(items, objectName, label, value) {
        var text = String(value || "");
        if (!text.length)
            return;
        items.push({
            "object_name": objectName,
            "label": label,
            "value": text
        });
    }

    function _buildFooterMetaModel() {
        var items = [];
        if (surface.viewerSessionOpen || surface.viewerRunRequired) {
            _appendFooterMeta(items, "graphNodeViewerResultMeta", "Result", surface.viewerResultLabel);
            _appendFooterMeta(items, "graphNodeViewerSelectionMeta", "Selection", surface.viewerSetLabel);
            _appendFooterMeta(items, "graphNodeViewerStepMeta", "Step", String(surface.viewerStepIndex));
        }
        if (surface.viewerRunRequired)
            _appendFooterMeta(items, "graphNodeViewerStatusMeta", "Status", "Rerun required");
        return items;
    }

    function requestSessionToggle() {
        if (!viewerBridgeAvailable || !viewerNodeId.length || viewerSessionBusy)
            return false;
        if (viewerRunRequired)
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
            color: host ? Qt.darker(host.inlineInputBackgroundColor, 1.05) : "#1a202b"
            border.width: 1
            border.color: host
                ? Qt.alpha(
                    surface.proxySurfaceActive
                        ? host.outlineColor
                        : (surface.liveSurfaceActive ? host.selectedOutlineColor : surface.viewerAccentColor),
                    0.82
                )
                : "#5da9ff"
        }

        Column {
            anchors.fill: parent
            spacing: 0

            Item {
                id: toolbarFrame
                width: parent.width
                height: toolbarFlow.implicitHeight + 10

                Rectangle {
                    anchors.fill: parent
                    color: host ? Qt.alpha(host.inlineRowColor, 0.18) : "#1d2431"
                    border.width: 0
                }

                Flow {
                    id: toolbarFlow
                    objectName: "graphNodeViewerQuickActions"
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 6
                    spacing: 4

                    GraphSurfaceControls.GraphSurfaceButton {
                        id: sessionButton
                        objectName: "graphNodeViewerSessionButton"
                        host: surface.host
                        text: surface.sessionButtonText
                        tooltipText: surface.sessionButtonText
                        iconName: surface.viewerSessionIconName
                        iconOnly: true
                        iconSize: 14
                        iconSourceResolver: function(name, size, color) {
                            return surface._iconSource(name, size, color);
                        }
                        enabled: surface.viewerBridgeAvailable
                            && surface.viewerNodeId.length > 0
                            && !surface.viewerSessionBusy
                            && !surface.viewerRunRequired
                        accentColor: surface.viewerCanOpen ? "#67D487" : "#D98B4B"
                        foregroundColor: surface.viewerCanOpen ? "#80E89A" : (host ? host.headerTextColor : "#eef3ff")
                        baseFillColor: surface.viewerCanOpen
                            ? Qt.alpha("#67D487", 0.14)
                            : Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.92)
                        baseBorderColor: surface.viewerCanOpen
                            ? Qt.alpha("#67D487", 0.52)
                            : Qt.alpha(surface.viewerAccentColor, 0.42)
                        chromeRadius: 6
                        contentHorizontalPadding: 7
                        contentVerticalPadding: 4
                        onControlStarted: surface._beginSurfaceControl()
                        onClicked: surface.requestSessionToggle()
                    }

                    Item {
                        width: 1
                        height: 30

                        Rectangle {
                            width: 1
                            height: 20
                            radius: 0.5
                            color: host ? Qt.alpha(host.inlineInputBorderColor, 0.45) : "#3b465b"
                            anchors.centerIn: parent
                        }
                    }

                    GraphSurfaceControls.GraphSurfaceButton {
                        id: playPauseButton
                        objectName: "graphNodeViewerPlayPauseButton"
                        host: surface.host
                        text: surface.playbackButtonText
                        tooltipText: surface.playbackButtonText
                        iconName: surface.viewerPlayPauseIconName
                        iconOnly: true
                        iconSize: 14
                        iconSourceResolver: function(name, size, color) {
                            return surface._iconSource(name, size, color);
                        }
                        enabled: surface.viewerCanControlPlayback
                        accentColor: surface.viewerPlaying ? "#D98B4B" : "#5DA9FF"
                        foregroundColor: host ? host.headerTextColor : "#eef3ff"
                        baseFillColor: Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.92)
                        baseBorderColor: Qt.alpha(surface.viewerPlaying ? "#D98B4B" : "#5DA9FF", 0.42)
                        chromeRadius: 6
                        contentHorizontalPadding: 7
                        contentVerticalPadding: 4
                        onControlStarted: surface._beginSurfaceControl()
                        onClicked: surface.requestPlayPause()
                    }

                    GraphSurfaceControls.GraphSurfaceButton {
                        id: stepButton
                        objectName: "graphNodeViewerStepButton"
                        host: surface.host
                        text: "Step"
                        tooltipText: "Step"
                        iconName: "step"
                        iconOnly: true
                        iconSize: 14
                        iconSourceResolver: function(name, size, color) {
                            return surface._iconSource(name, size, color);
                        }
                        enabled: surface.viewerCanControlPlayback
                        accentColor: "#7AA8FF"
                        foregroundColor: host ? host.headerTextColor : "#eef3ff"
                        baseFillColor: Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.92)
                        baseBorderColor: Qt.alpha("#7AA8FF", 0.46)
                        chromeRadius: 6
                        contentHorizontalPadding: 7
                        contentVerticalPadding: 4
                        onControlStarted: surface._beginSurfaceControl()
                        onClicked: surface.requestStep()
                    }

                    Item {
                        width: 1
                        height: 30

                        Rectangle {
                            width: 1
                            height: 20
                            radius: 0.5
                            color: host ? Qt.alpha(host.inlineInputBorderColor, 0.45) : "#3b465b"
                            anchors.centerIn: parent
                        }
                    }

                    Rectangle {
                        id: policyGroup
                        objectName: "graphNodeViewerPolicyRow"
                        radius: 6
                        clip: true
                        color: host ? Qt.alpha(host.inlineInputBackgroundColor, 0.86) : "#202635"
                        border.width: 1
                        border.color: host ? Qt.alpha(host.inlineInputBorderColor, 0.52) : "#465066"
                        width: policyRow.implicitWidth
                        height: 30
                        opacity: surface.viewerCanControlPlayback ? 1.0 : 0.78

                        Row {
                            id: policyRow
                            anchors.fill: parent
                            spacing: 0

                            GraphSurfaceControls.GraphSurfaceButton {
                                id: focusPolicyChip
                                objectName: "graphNodeViewerFocusPolicyChip"
                                host: surface.host
                                text: "Focus"
                                tooltipText: "Focus only"
                                iconName: "focus"
                                iconSize: 11
                                iconSourceResolver: function(name, size, color) {
                                    return surface._iconSource(name, size, color);
                                }
                                enabled: surface.viewerCanControlPlayback
                                accentColor: "#5DA9FF"
                                foregroundColor: surface.viewerLivePolicy === "focus_only"
                                    ? (host ? host.headerTextColor : "#eef3ff")
                                    : (host ? host.inlineDrivenTextColor : "#7a8eae")
                                baseFillColor: surface.viewerLivePolicy === "focus_only"
                                    ? Qt.alpha("#5DA9FF", 0.22)
                                    : "transparent"
                                baseBorderColor: "transparent"
                                hoverBorderColor: "transparent"
                                pressedBorderColor: "transparent"
                                chromeRadius: 0
                                idleBorderWidth: 0
                                hoverBorderWidth: 0
                                contentHorizontalPadding: 8
                                contentVerticalPadding: 3
                                onControlStarted: surface._beginSurfaceControl()
                                onClicked: surface.requestLivePolicy("focus_only")
                            }

                            Rectangle {
                                width: 1
                                height: parent.height
                                color: host ? Qt.alpha(host.inlineInputBorderColor, 0.48) : "#465066"
                            }

                            GraphSurfaceControls.GraphSurfaceButton {
                                id: keepPolicyChip
                                objectName: "graphNodeViewerKeepPolicyChip"
                                host: surface.host
                                text: "Keep"
                                tooltipText: "Keep live policy"
                                iconName: "keep-live"
                                iconSize: 11
                                iconSourceResolver: function(name, size, color) {
                                    return surface._iconSource(name, size, color);
                                }
                                enabled: surface.viewerCanControlPlayback
                                accentColor: "#67D487"
                                foregroundColor: surface.viewerLivePolicy === "keep_live"
                                    ? (host ? host.headerTextColor : "#eef3ff")
                                    : (host ? host.inlineDrivenTextColor : "#7a8eae")
                                baseFillColor: surface.viewerLivePolicy === "keep_live"
                                    ? Qt.alpha("#67D487", 0.22)
                                    : "transparent"
                                baseBorderColor: "transparent"
                                hoverBorderColor: "transparent"
                                pressedBorderColor: "transparent"
                                chromeRadius: 0
                                idleBorderWidth: 0
                                hoverBorderWidth: 0
                                contentHorizontalPadding: 8
                                contentVerticalPadding: 3
                                onControlStarted: surface._beginSurfaceControl()
                                onClicked: surface.requestLivePolicy("keep_live")
                            }
                        }
                    }

                    GraphSurfaceControls.GraphSurfaceButton {
                        id: keepLiveButton
                        objectName: "graphNodeViewerKeepLiveButton"
                        host: surface.host
                        text: surface.viewerKeepLive ? "Pinned" : "Pin"
                        tooltipText: surface.viewerKeepLive ? "Pinned" : "Pin session"
                        iconName: "pin"
                        iconOnly: true
                        iconSize: 14
                        iconSourceResolver: function(name, size, color) {
                            return surface._iconSource(name, size, color);
                        }
                        enabled: surface.viewerCanControlPlayback
                        accentColor: surface.viewerKeepLive ? "#67D487" : "#A0A8C0"
                        foregroundColor: surface.viewerKeepLive
                            ? "#80E89A"
                            : (host ? host.headerTextColor : "#eef3ff")
                        baseFillColor: surface.viewerKeepLive
                            ? Qt.alpha("#67D487", 0.2)
                            : Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.92)
                        baseBorderColor: surface.viewerKeepLive
                            ? Qt.alpha("#67D487", 0.72)
                            : Qt.alpha("#A0A8C0", 0.34)
                        chromeRadius: 6
                        contentHorizontalPadding: 7
                        contentVerticalPadding: 4
                        onControlStarted: surface._beginSurfaceControl()
                        onClicked: surface.requestKeepLiveToggle()
                    }

                    Rectangle {
                        id: moreButton
                        objectName: "graphNodeViewerMoreButton"
                        width: 30
                        height: 30
                        radius: 6
                        color: Qt.alpha(surface.host ? surface.host.inlineInputBackgroundColor : "#202635", 0.48)
                        border.width: 1
                        border.color: Qt.alpha(surface.host ? surface.host.inlineInputBorderColor : "#465066", 0.28)

                        Image {
                            anchors.centerIn: parent
                            source: surface._iconSource(
                                "more",
                                14,
                                String(surface.host ? surface.host.inlineDrivenTextColor : "#7a8eae")
                            )
                            width: 14
                            height: 14
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                            opacity: 0.66
                            sourceSize.width: 14
                            sourceSize.height: 14
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: host ? Qt.alpha(host.inlineInputBorderColor, 0.2) : "#2a3248"
            }

            Rectangle {
                id: statusStrip
                objectName: "graphNodeViewerStatusStrip"
                width: parent.width
                height: Math.max(24, statusText.implicitHeight + 10)
                color: "transparent"
                border.width: 0

                Item {
                    anchors.fill: parent

                    Rectangle {
                        id: statusDot
                        objectName: "graphNodeViewerStatusDot"
                        width: 6
                        height: 6
                        radius: 3
                        anchors.left: parent.left
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        color: surface.viewerAccentColor
                        border.width: 0
                    }

                    Text {
                        id: statusText
                        objectName: "graphNodeViewerStatusText"
                        anchors.left: statusDot.right
                        anchors.leftMargin: 6
                        anchors.right: modeBadge.left
                        anchors.rightMargin: 6
                        anchors.verticalCenter: parent.verticalCenter
                        text: surface.viewerStatusLabel
                        color: host ? host.inlineDrivenTextColor : "#b5c0d4"
                        font.pixelSize: 10
                        font.bold: true
                        wrapMode: Text.WordWrap
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    Rectangle {
                        id: modeBadge
                        objectName: "graphNodeViewerModeBadge"
                        anchors.right: parent.right
                        anchors.rightMargin: 10
                        radius: 4
                        anchors.verticalCenter: parent.verticalCenter
                        color: Qt.alpha(surface.viewerAccentColor, 0.16)
                        border.width: 1
                        border.color: Qt.alpha(surface.viewerAccentColor, 0.46)
                        height: modeLabel.implicitHeight + 6
                        width: modeLabel.implicitWidth + 12

                        Text {
                            id: modeLabel
                            objectName: "graphNodeViewerSurfaceModeLabel"
                            anchors.centerIn: parent
                            text: surface.viewerModeBadgeText
                            color: host ? host.headerTextColor : "#eef3ff"
                            font.pixelSize: 9
                            font.bold: true
                            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                        }
                    }
                }
            }

            Item {
                id: viewportContainer
                width: parent.width
                height: Math.max(60, bodyFrame.height - toolbarFrame.height - statusStrip.height)

                Rectangle {
                    id: viewportFrame
                    objectName: "graphNodeViewerViewport"
                    anchors.fill: parent
                    anchors.margins: 8
                    radius: 6
                    color: host ? Qt.alpha(host.surfaceColor, 0.12) : "#101724"
                    border.width: surface.viewerShowsPlaceholder ? 0 : 1
                    border.color: surface.viewerViewportBorderColor
                    clip: true

                    Canvas {
                        id: crosshatchCanvas
                        anchors.fill: parent
                        visible: surface.viewerShowsPlaceholder
                        opacity: 0.08

                        onPaint: {
                            var ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            ctx.strokeStyle = host
                                ? String(host.inlineDrivenTextColor || "#aaa")
                                : "#aaa";
                            ctx.lineWidth = 0.5;
                            var step = 14;
                            var diag = Math.max(width, height) * 2;
                            ctx.beginPath();
                            for (var i = -diag; i < diag; i += step) {
                                ctx.moveTo(i, 0);
                                ctx.lineTo(i + height, height);
                            }
                            ctx.stroke();
                        }

                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                    }
                }

                Rectangle {
                    objectName: "graphNodeViewerProxyPane"
                    visible: surface.proxySurfaceActive
                    anchors.fill: viewportFrame
                    radius: viewportFrame.radius
                    color: host ? Qt.alpha(host.surfaceColor, 0.16) : "#22304a"
                    border.width: 1
                    border.color: host ? Qt.alpha(host.scopeBadgeBorderColor, 0.7) : "#4c7bc0"
                }

                Rectangle {
                    objectName: "graphNodeViewerLivePane"
                    visible: surface.liveSurfaceActive
                    anchors.fill: viewportFrame
                    radius: viewportFrame.radius
                    color: host ? Qt.alpha(host.selectedOutlineColor, 0.08) : "#11243d"
                    border.width: 1
                    border.color: host ? Qt.alpha(host.selectedOutlineColor, 0.76) : "#5da9ff"
                }

                Item {
                    id: viewportInner
                    anchors.fill: viewportFrame

                    Column {
                        id: placeholderColumn
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 24, 180)
                        spacing: 8
                        visible: surface.viewerShowsPlaceholder

                        Image {
                            id: placeholderIcon
                            objectName: "graphNodeViewerPlaceholderIcon"
                            anchors.horizontalCenter: parent.horizontalCenter
                            source: surface._iconSource(surface.viewerPlaceholderIconName, 24, String(Qt.alpha(surface.viewerAccentColor, 0.35)))
                            width: 24
                            height: 24
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            mipmap: true
                            sourceSize.width: 24
                            sourceSize.height: 24
                            opacity: 0.5
                        }

                        Text {
                            objectName: "graphNodeViewerSurfaceHeadline"
                            width: parent.width
                            text: surface.viewerPhase === "error"
                                ? surface.viewerStatusLabel
                                : (surface.viewerRunRequired || surface.viewerPhase === "invalidated"
                                    ? surface.viewerStatusLabel
                                    : "Open session to view")
                            color: (
                                surface.viewerRunRequired
                                || surface.viewerPhase === "error"
                                || surface.viewerPhase === "invalidated"
                            )
                                ? (host ? host.inlineInputTextColor : "#eef3ff")
                                : (host ? Qt.alpha(host.inlineDrivenTextColor, 0.5) : "#4a5578")
                            font.pixelSize: (
                                surface.viewerRunRequired
                                || surface.viewerPhase === "error"
                                || surface.viewerPhase === "invalidated"
                            ) ? 11 : 10
                            font.weight: Font.DemiBold
                            font.capitalization: (
                                surface.viewerRunRequired
                                || surface.viewerPhase === "error"
                                || surface.viewerPhase === "invalidated"
                            )
                                ? Font.MixedCase
                                : Font.AllUppercase
                            font.letterSpacing: (
                                surface.viewerRunRequired
                                || surface.viewerPhase === "error"
                                || surface.viewerPhase === "invalidated"
                            ) ? 0 : 0.5
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                        }

                        Text {
                            objectName: "graphNodeViewerSurfaceHint"
                            width: parent.width
                            visible: surface.viewerRunRequired
                                || surface.viewerPhase === "error"
                                || surface.viewerPhase === "invalidated"
                            text: surface.viewerHintText
                            color: host ? host.inlineDrivenTextColor : "#bdc5d3"
                            font.pixelSize: 10
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                        }
                    }

                    Rectangle {
                        id: footerFrame
                        visible: surface.viewerFooterMetaModel.length > 0
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 8
                        radius: 5
                        color: host ? Qt.alpha(host.inlineInputBackgroundColor, 0.72) : "#19202d"
                        border.width: 1
                        border.color: host ? Qt.alpha(host.inlineInputBorderColor, 0.34) : "#465066"
                        height: footerFlow.implicitHeight + 8

                        Flow {
                            id: footerFlow
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            anchors.topMargin: 4
                            anchors.bottomMargin: 4
                            spacing: 6

                            Repeater {
                                model: surface.viewerFooterMetaModel

                                Rectangle {
                                    objectName: modelData.object_name
                                    readonly property real maxChipWidth: Math.max(72, footerFlow.width * 0.52)
                                    radius: 9
                                    color: Qt.alpha(surface.viewerAccentColor, 0.1)
                                    border.width: 1
                                    border.color: Qt.alpha(surface.viewerAccentColor, 0.22)
                                    height: footerMetaRow.implicitHeight + 6
                                    width: Math.min(maxChipWidth, footerMetaRow.implicitWidth + 10)

                                    Row {
                                        id: footerMetaRow
                                        anchors.fill: parent
                                        anchors.leftMargin: 5
                                        anchors.rightMargin: 5
                                        spacing: 4

                                        Text {
                                            text: modelData.label
                                            color: host ? host.inlineDrivenTextColor : "#8ea0bd"
                                            font.pixelSize: 9
                                            font.bold: true
                                            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                                        }

                                        Text {
                                            width: Math.max(20, parent.width - x - 2)
                                            text: modelData.value
                                            color: host ? host.inlineLabelColor : "#d5dbea"
                                            font.pixelSize: 9
                                            elide: Text.ElideRight
                                            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
