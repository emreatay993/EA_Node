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
    readonly property var bridgeSessionProjectionSeed: viewerBridgeAvailable
        ? viewerSessionBridgeRef.sessions_model
        : []
    readonly property string viewerNodeId: host && host.nodeData
        ? String(host.nodeData.node_id || "")
        : ""
    readonly property var viewerSessionState: {
        var projectionSeed = surface.bridgeSessionProjectionSeed;
        void(projectionSeed);
        if (!surface.viewerBridgeAvailable || surface.viewerNodeId.length === 0)
            return ({});
        return viewerSessionBridgeRef.session_state(surface.viewerNodeId);
    }
    readonly property var viewerSessionModel: viewerSessionState
    readonly property var viewerSummary: viewerSessionModel.summary ? viewerSessionModel.summary : ({})
    readonly property var viewerOptions: viewerSessionModel.options ? viewerSessionModel.options : ({})
    readonly property var viewerDataRefs: viewerSessionModel.data_refs ? viewerSessionModel.data_refs : ({})
    readonly property var viewerPreviewRefPayload: viewerDataRefs.png
        ? viewerDataRefs.png
        : (viewerDataRefs.preview ? viewerDataRefs.preview : null)
    readonly property string viewerPreviewSourceRef: _artifactSource(viewerPreviewRefPayload)
    readonly property string viewerPreviewImageSource: _previewImageSource(viewerPreviewSourceRef)
    readonly property bool viewerPreviewAvailable: viewerPreviewImageSource.length > 0
    readonly property bool proxySurfaceSupported: viewerPayload.proxy_surface_supported === undefined
        ? true
        : Boolean(viewerPayload.proxy_surface_supported)
    readonly property bool liveSurfaceSupported: viewerPayload.live_surface_supported === undefined
        ? true
        : Boolean(viewerPayload.live_surface_supported)
    readonly property string overlayTarget: String(viewerPayload.overlay_target || "body")
    readonly property bool liveGeometryRectSizingActive: host ? Boolean(host._liveGeometryActive) : false
    readonly property rect surfaceBodyRect: _resolvedBodyRect()
    readonly property rect proxySurfaceRect: _resolvedRect(
        viewerPayload.proxy_rect,
        surfaceBodyRect,
        liveGeometryRectSizingActive
    )
    readonly property rect liveSurfaceRect: _resolvedLiveRect()
    readonly property bool proxySurfaceRequested: host
        ? Boolean(host.proxySurfaceRequested || String(host.resolvedQualityTier || "") === "proxy")
        : false
    readonly property string viewerSessionId: String(viewerSessionModel.session_id || "")
    readonly property string viewerPhase: String(viewerSessionModel.phase || "closed")
    readonly property string viewerPlaybackState: String(viewerSessionModel.playback_state || "paused")
    readonly property int viewerStepIndex: Math.max(0, Math.floor(_number(viewerSessionModel.step_index, 0)))
    readonly property string viewerLivePolicy: String(viewerSessionModel.live_policy || "focus_only")
    readonly property bool viewerKeepLive: Boolean(viewerSessionModel.keep_live)
    readonly property string viewerCacheState: String(viewerSessionModel.cache_state || "empty")
    readonly property string viewerBackendId: String(
        viewerSessionModel.backend_id || ""
    )
    readonly property var viewerTransport: viewerSessionModel.transport
        ? viewerSessionModel.transport
        : ({})
    readonly property string viewerTransportKind: String(viewerTransport.kind || "")
    readonly property int viewerTransportRevision: Math.max(
        0,
        Math.floor(
            _number(viewerSessionModel.transport_revision, 0)
        )
    )
    readonly property string viewerLiveOpenStatus: String(
        viewerSessionModel.live_open_status || ""
    )
    readonly property var viewerLiveOpenBlocker: viewerSessionModel.live_open_blocker
        ? viewerSessionModel.live_open_blocker
        : ({})
    readonly property string viewerTransportReleaseReason: String(
        viewerSummary.live_transport_release_reason || ""
    )
    readonly property bool viewerRunRequired: viewerPhase === "blocked"
        || viewerLiveOpenStatus === "blocked"
        || Boolean(viewerLiveOpenBlocker.rerun_required)
    readonly property string viewerLiveMode: {
        var liveMode = String(surface.viewerSessionModel.live_mode || "");
        if (liveMode.length > 0)
            return liveMode;
        if (surface.viewerPhase === "open")
            return surface.proxySurfaceRequested ? "proxy" : "full";
        if (surface.viewerPhase === "opening" || surface.viewerPhase === "closing")
            return "proxy";
        return surface.proxySurfaceRequested ? "proxy" : "reserved";
    }
    readonly property string viewerLastError: {
        var sessionError = String(surface.viewerSessionModel.last_error || "");
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
        viewerSessionModel.invalidated_reason
        || viewerSummary.invalidated_reason
        || ""
    )
    readonly property string viewerCloseReason: String(
        viewerSessionModel.close_reason
        || viewerSummary.close_reason
        || ""
    )
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
            return "open-session";
        if (surface.viewerPhase === "closing")
            return "stop";
        return surface.viewerCanOpen ? "open-session" : "stop";
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
    readonly property var viewerInteractiveRects: []
    readonly property var embeddedInteractiveRects: viewerInteractiveRects
    readonly property var surfaceActions: {
        var actions = [];
        var nodeIdLength = surface.viewerNodeId ? String(surface.viewerNodeId).length : 0;
        var fullscreenAvailable = nodeIdLength > 0
            && typeof contentFullscreenBridge !== "undefined"
            && contentFullscreenBridge;
        actions.push({
            "id": "openSession",
            "label": surface.sessionButtonText,
            "icon": surface.viewerSessionIconName,
            "kind": "viewer",
            "enabled": surface.viewerBridgeAvailable
                && nodeIdLength > 0
                && !surface.viewerSessionBusy
                && !surface.viewerRunRequired,
            "primary": surface.viewerCanOpen
        });
        actions.push({
            "id": "playPause",
            "label": surface.playbackButtonText,
            "icon": surface.viewerPlayPauseIconName,
            "kind": "viewer",
            "enabled": surface.viewerCanControlPlayback,
            "primary": false
        });
        actions.push({
            "id": "step",
            "label": "Step",
            "icon": "step",
            "kind": "viewer",
            "enabled": surface.viewerCanControlPlayback,
            "primary": false
        });
        actions.push({
            "id": "keepLive",
            "label": "Keep Live",
            "icon": "pin",
            "kind": "viewer",
            "enabled": surface.viewerCanControlPlayback,
            "primary": surface.viewerKeepLive
        });
        actions.push({
            "id": "fullscreen",
            "label": "Fullscreen",
            "icon": "fullscreen",
            "kind": "viewer",
            "enabled": fullscreenAvailable,
            "primary": false
        });
        return actions;
    }

    function dispatchSurfaceAction(actionId) {
        var normalized = String(actionId || "");
        surface._beginSurfaceControl();
        if (normalized === "openSession")
            return Boolean(surface.requestSessionToggle());
        if (normalized === "playPause")
            return Boolean(surface.requestPlayPause());
        if (normalized === "step")
            return Boolean(surface.requestStep());
        if (normalized === "keepLive")
            return Boolean(surface.requestKeepLiveToggle());
        if (normalized === "fullscreen")
            return Boolean(surface.requestContentFullscreen());
        return false;
    }

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
    readonly property var viewerFooterMetaModel: []
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
        var height = Math.max(0.0, _number(metrics.body_height, 0.0));
        return Qt.rect(x, y, width, height);
    }

    function _resolvedBodyRect() {
        var fallback = _defaultBodyRect();
        var resolved = _resolvedRect(
            viewerPayload.body_rect,
            fallback,
            liveGeometryRectSizingActive
        );
        if (liveGeometryRectSizingActive)
            return resolved;
        var payloadHeight = _number(
            viewerPayload && viewerPayload.body_rect ? viewerPayload.body_rect.height : NaN,
            NaN
        );
        var fallbackHeight = Math.max(0.0, _number(fallback.height, 0.0));
        if (!isFinite(payloadHeight) || !isFinite(fallbackHeight) || fallbackHeight <= 0.0)
            return resolved;
        if (Math.abs(payloadHeight - fallbackHeight) <= 1.0)
            return resolved;
        return Qt.rect(
            Math.max(0.0, _number(resolved.x, fallback.x)),
            Math.max(0.0, _number(resolved.y, fallback.y)),
            Math.max(0.0, _number(resolved.width, fallback.width)),
            fallbackHeight
        );
    }

    function _resolvedRect(value, fallbackRect, preferFallbackSize) {
        var fallback = fallbackRect || Qt.rect(0.0, 0.0, 0.0, 0.0);
        var x = Math.max(0.0, _number(value && value.x, fallback.x));
        var y = Math.max(0.0, _number(value && value.y, fallback.y));
        var width = preferFallbackSize
            ? Math.max(0.0, fallback.width)
            : Math.max(0.0, _number(value && value.width, fallback.width));
        var height = preferFallbackSize
            ? Math.max(0.0, fallback.height)
            : Math.max(0.0, _number(value && value.height, fallback.height));
        return Qt.rect(x, y, width, height);
    }

    function _resolvedLiveRect() {
        var fallback = _resolvedRect(
            viewerPayload.live_rect,
            surfaceBodyRect,
            liveGeometryRectSizingActive
        );
        var viewportWidth = _number(viewportFrame ? viewportFrame.width : NaN, NaN);
        var viewportHeight = _number(viewportFrame ? viewportFrame.height : NaN, NaN);
        if (!isFinite(viewportWidth) || !isFinite(viewportHeight) || viewportWidth <= 0.0 || viewportHeight <= 0.0)
            return fallback;
        var viewportX = _number(bodyFrame ? bodyFrame.x : fallback.x, fallback.x)
            + _number(viewportContainer ? viewportContainer.x : 0.0, 0.0)
            + _number(viewportFrame ? viewportFrame.x : 0.0, 0.0);
        var viewportY = _number(bodyFrame ? bodyFrame.y : fallback.y, fallback.y)
            + _number(viewportContainer ? viewportContainer.y : 0.0, 0.0)
            + _number(viewportFrame ? viewportFrame.y : 0.0, 0.0);
        return Qt.rect(
            Math.max(0.0, viewportX),
            Math.max(0.0, viewportY),
            Math.max(0.0, viewportWidth),
            Math.max(0.0, viewportHeight)
        );
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
        _focusViewerSession();
    }

    function _focusViewerSession() {
        if (!viewerBridgeAvailable || !viewerNodeId.length || !viewerSessionBridgeRef.focus_session)
            return false;
        return Boolean(viewerSessionBridgeRef.focus_session(viewerNodeId));
    }

    function _artifactSource(value) {
        if (value === undefined || value === null)
            return "";
        if (typeof value === "string")
            return String(value);
        if (value.ref !== undefined && value.ref !== null)
            return String(value.ref);
        if (value.source !== undefined && value.source !== null)
            return String(value.source);
        return "";
    }

    function _previewImageSource(sourceRef) {
        var normalized = String(sourceRef || "");
        if (!normalized.length)
            return "";
        return "image://local-media-preview/preview?source=" + encodeURIComponent(normalized);
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

    function requestKeepLiveToggle() {
        if (!viewerCanControlPlayback || !viewerSessionBridgeRef.set_keep_live)
            return false;
        return Boolean(viewerSessionBridgeRef.set_keep_live(viewerNodeId, !viewerKeepLive));
    }

    function _contentFullscreenBridge() {
        if (typeof contentFullscreenBridge !== "undefined" && contentFullscreenBridge)
            return contentFullscreenBridge;
        return null;
    }

    function requestContentFullscreen() {
        var bridge = _contentFullscreenBridge();
        if (!bridge || !viewerNodeId.length)
            return false;
        if (bridge.request_toggle_for_node)
            return Boolean(bridge.request_toggle_for_node(viewerNodeId));
        if (bridge.request_open_node)
            return Boolean(bridge.request_open_node(viewerNodeId));
        return false;
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
                height: Math.max(60, bodyFrame.height - statusStrip.height)

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

                    TapHandler {
                        objectName: "graphNodeViewerViewportTapHandler"
                        acceptedButtons: Qt.LeftButton
                        onTapped: surface._beginSurfaceControl()
                    }

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
                    id: proxyPane
                    objectName: "graphNodeViewerProxyPane"
                    visible: surface.proxySurfaceActive
                    anchors.fill: viewportFrame
                    radius: viewportFrame.radius
                    color: host ? Qt.alpha(host.surfaceColor, 0.16) : "#22304a"
                    border.width: 1
                    border.color: host ? Qt.alpha(host.scopeBadgeBorderColor, 0.7) : "#4c7bc0"

                    Image {
                        id: proxyPreviewImage
                        objectName: "graphNodeViewerProxyImage"
                        visible: surface.viewerPreviewAvailable
                        anchors.fill: parent
                        anchors.margins: 1
                        source: surface.viewerPreviewImageSource
                        fillMode: Image.PreserveAspectFit
                        asynchronous: false
                        cache: false
                        smooth: true
                        mipmap: true
                    }
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
