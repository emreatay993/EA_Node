import QtQuick 2.15
import ".." as GraphShared
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import "../surface_controls" as GraphSurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry
import "../surface_controls/SourceStorageModeUtils.js" as SourceStorageModeUtils
import "GraphMediaPanelSourceUtils.js" as GraphMediaPanelSourceUtils

GraphShared.GraphSurfaceBase {
    id: surface
    chromeToggleAvailable: true
    objectName: "graphNodeVideoSurface"
    property bool resumeAfterSeek: false
    property bool initialPositionApplied: false
    property bool clipEnforcing: false
    property bool thumbnailPrimerActive: false
    property bool thumbnailPrimerComplete: false
    property bool thumbnailPrimerPauseCommitGuard: false
    property bool artifactRenameReleaseActive: false
    property var artifactRenameReleaseState: ({})
    property int artifactRenameResolveGeneration: 0
    readonly property string sourcePath: propValue("source_path")
    readonly property string sourceStorageMode: SourceStorageModeUtils.sourceModeForPath(sourcePath)
    readonly property string normalizedFitMode: _normalizedFitMode(propValue("fit_mode"))
    readonly property bool autoPlayEnabled: propBool("auto_play", false)
    readonly property bool loopEnabled: propBool("loop", false)
    readonly property bool muted: propBool("muted", false)
    readonly property real volume: _boundedNumber("volume", 1.0, 0.0, 1.0)
    readonly property real playbackRate: _boundedNumber("playback_rate", 1.0, 0.25, 4.0)
    readonly property int storedPositionMs: Math.max(0, Math.round(propNumber("position_ms", 0)))
    readonly property var timelineBookmarks: _normalizedTimelineBookmarks(propRaw("timeline_bookmarks", []))
    readonly property bool clipEnabled: propBool("clip_enabled", false)
    readonly property int clipStartMs: Math.max(0, Math.round(propNumber("clip_start_ms", 0)))
    readonly property int clipEndMs: Math.max(0, Math.round(propNumber("clip_end_ms", 0)))
    readonly property bool clipRangeActive: clipEnabled && clipEndMs > clipStartMs
    readonly property bool validSourceActive: resolvedSourceUrl.length > 0
        && !sourceRejected
    readonly property string resolvedSourceUrl: _resolvedVideoSourceUrl()
    readonly property string effectiveResolvedSourceUrl: artifactRenameReleaseActive ? "" : resolvedSourceUrl
    readonly property bool canInternalizeSource: sourceStorageMode === "external_link"
        && GraphMediaPanelSourceUtils.resolvedLocalFileSourceUrl(sourcePath).length > 0
    readonly property bool sourceRejected: sourcePath.trim().length > 0 && resolvedSourceUrl.length === 0
    readonly property bool fullscreenAvailable: host ? Boolean(host.surfaceFullscreenAvailable) : false
    readonly property var fullscreenBridgeRef: typeof contentFullscreenBridge !== "undefined" && contentFullscreenBridge
        ? contentFullscreenBridge
        : null
    readonly property bool fullscreenOwnsPlayback: fullscreenBridgeRef
        && Boolean(fullscreenBridgeRef.open)
        && String(fullscreenBridgeRef.content_kind || "") === "video"
        && host
        && host.nodeData
        && String(fullscreenBridgeRef.node_id || "") === String(host.nodeData.node_id || "")
    readonly property bool hostPlaybackAllowed: !fullscreenOwnsPlayback
    readonly property bool fileIssueActive: sourcePath.trim().length > 0
        && (sourceRejected || previewState === "error")
    readonly property real contentInset: host ? Number(host.surfaceMetrics.body_bottom_margin || 12) : 12
    readonly property real contentLeftMargin: surfaceShowFrame ? (host ? Number(host.surfaceMetrics.body_left_margin || 14) : 14) : 0
    readonly property real contentRightMargin: surfaceShowFrame ? (host ? Number(host.surfaceMetrics.body_right_margin || 14) : 14) : 0
    readonly property real contentTopMargin: {
        if (!host)
            return surfaceShowTitle ? 44 : (surfaceShowFrame ? contentInset : 0);
        if (!surfaceShowTitle)
            return surfaceShowFrame ? contentInset : 0;
        return Number(host.surfaceMetrics.body_top || 44);
    }
    readonly property real contentBottomMargin: surfaceShowFrame ? (host ? Number(host.surfaceMetrics.body_bottom_margin || 12) : 12) : 0
    readonly property string statusText: _statusText()
    readonly property string previewState: {
        if (sourcePath.trim().length === 0)
            return "placeholder";
        if (sourceRejected)
            return "error";
        if (player.error !== MediaPlayer.NoError || player.mediaStatus === MediaPlayer.InvalidMedia)
            return "error";
        if (player.mediaStatus === MediaPlayer.LoadingMedia
                || player.mediaStatus === MediaPlayer.BufferingMedia
                || player.mediaStatus === MediaPlayer.StalledMedia)
            return "loading";
        if (player.mediaStatus === MediaPlayer.LoadedMedia
                || player.mediaStatus === MediaPlayer.BufferedMedia
                || player.mediaStatus === MediaPlayer.EndOfMedia
                || player.playbackState === MediaPlayer.PlayingState
                || player.playbackState === MediaPlayer.PausedState)
            return "ready";
        return "placeholder";
    }
    readonly property bool blocksHostInteraction: seekSlider.pressed
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists(
        [
            seekRegion.embeddedInteractiveRects
        ]
    )
    readonly property var surfaceActions: {
        var actions = [
            {
                "id": "editSource",
                "label": "Source",
                "icon": "search",
                "kind": "media",
                "enabled": true,
                "primary": sourcePath.trim().length === 0,
                "popover_layout": "source_storage",
                "popoverActions": [
                    {
                        "id": "editSourceExternalLink",
                        "label": "External link",
                        "icon": "external-link",
                        "kind": "media",
                        "toolbar_text": "External",
                        "source_mode": "external_link",
                        "checked": sourceStorageMode === "external_link",
                        "enabled": true,
                        "close_popover": true
                    },
                    {
                        "id": "editSourceManagedCopy",
                        "label": "Internal copy",
                        "icon": "open-session",
                        "kind": "media",
                        "toolbar_text": "Internal",
                        "source_mode": "managed_copy",
                        "checked": sourceStorageMode === "managed_copy",
                        "enabled": true,
                        "close_popover": true
                    }
                ]
            }
        ];
        if (canInternalizeSource) {
            actions.push({
                "id": "internalizeSource",
                "label": "Copy into project",
                "icon": "internalize-source",
                "kind": "media",
                "enabled": true
            });
        }
        actions.push({
            "id": "toggle_content_only",
            "label": surfaceContentOnly ? "Show chrome" : "Content only",
            "icon": surfaceContentOnly ? "node-chrome" : "content-only",
            "kind": "media",
            "enabled": true,
            "primary": surfaceContentOnly
        });
        actions.push({
            "id": "toggle_title",
            "label": surfaceShowTitle ? "Hide title" : "Show title",
            "icon": "title-heading",
            "kind": "media",
            "enabled": true,
            "primary": false
        });
        actions.push({
            "id": "toggle_frame",
            "label": surfaceShowFrame ? "Hide frame" : "Show frame",
            "icon": "frame-corners",
            "kind": "media",
            "enabled": true,
            "primary": false
        });
        if (validSourceActive) {
            actions.push({
                "id": "playPause",
                "label": player.playbackState === MediaPlayer.PlayingState ? "Pause" : "Play",
                "icon": player.playbackState === MediaPlayer.PlayingState ? "pause" : "run",
                "kind": "media",
                "enabled": true,
                "primary": player.playbackState !== MediaPlayer.PlayingState
            });
            actions.push({
                "id": "rewindToStart",
                "label": "Rewind",
                "icon": "video-rewind",
                "kind": "media",
                "enabled": true,
                "primary": false
            });
            actions.push({
                "id": "seekBack10",
                "label": "Back 10s",
                "icon": "video-seek-back-10",
                "kind": "media",
                "enabled": true,
                "primary": false
            });
            actions.push({
                "id": "seekForward10",
                "label": "Forward 10s",
                "icon": "video-seek-forward-10",
                "kind": "media",
                "enabled": true,
                "primary": false
            });
            actions.push({
                "id": "loop",
                "label": loopEnabled ? "Disable loop" : "Loop",
                "icon": "video-loop",
                "kind": "media",
                "enabled": true,
                "primary": loopEnabled,
                "checked": loopEnabled
            });
            actions.push({
                "id": "bookmarks",
                "label": "Bookmarks",
                "icon": "video-bookmarks",
                "kind": "media",
                "enabled": true,
                "primary": timelineBookmarks.length > 0,
                "checked": timelineBookmarks.length > 0,
                "popover_layout": "video_bookmarks",
                "popoverActions": _bookmarkPopoverActions()
            });
            actions.push({
                "id": "captureFrame",
                "label": "Capture frame",
                "icon": "video-capture-frame",
                "kind": "media",
                "enabled": readyOrPlayingForAction(),
                "primary": false
            });
            actions.push({
                "id": "timestampAnnotation",
                "label": "Timestamp note",
                "icon": "video-timestamp-note",
                "kind": "media",
                "enabled": true,
                "primary": false
            });
            actions.push({
                "id": "clipRange",
                "label": clipRangeActive ? "Clip range" : "Set clip range",
                "icon": "video-clip-range",
                "kind": "media",
                "enabled": true,
                "primary": clipRangeActive,
                "checked": clipRangeActive,
                "popoverActions": _clipPopoverActions()
            });
            actions.push({
                "id": "mute",
                "label": muted ? "Unmute" : "Mute",
                "icon": muted ? "volume-muted" : "volume",
                "kind": "media",
                "enabled": true,
                "primary": muted,
                "checked": muted
            });
            actions.push({
                "id": "fitMode",
                "label": normalizedFitMode === "cover" ? "Fit video" : "Fill video",
                "icon": normalizedFitMode === "cover" ? "video-fit" : "video-fill",
                "kind": "media",
                "enabled": true,
                "primary": normalizedFitMode === "cover",
                "checked": normalizedFitMode === "cover"
            });
            var fullscreenAction = host && host.surfaceFullscreenAction
                ? host.surfaceFullscreenAction(fullscreenAvailable, false)
                : null;
            if (fullscreenAction)
                actions.push(fullscreenAction);
        }
        if (fileIssueActive) {
            actions.push({
                "id": "repair",
                "label": "Repair",
                "icon": "plug",
                "kind": "media",
                "enabled": true,
                "primary": true
            });
        }
        return actions;
    }

    implicitHeight: host ? Number(host.surfaceMetrics.body_height || 0) : 0

    onFullscreenOwnsPlaybackChanged: {
        if (fullscreenOwnsPlayback && player.playbackState === MediaPlayer.PlayingState)
            player.pause();
    }

    onHostPlaybackAllowedChanged: {
        if (!hostPlaybackAllowed && player.playbackState === MediaPlayer.PlayingState)
            player.pause();
    }

    onResolvedSourceUrlChanged: {
        initialPositionApplied = false;
        thumbnailPrimerActive = false;
        thumbnailPrimerComplete = false;
        thumbnailPrimerPauseCommitGuard = false;
        thumbnailPrimerTimer.stop();
        thumbnailPrimerPauseGuardTimer.stop();
        seekSlider.value = 0;
        if (artifactRenameReleaseActive)
            return;
        var expectedSourceUrl = resolvedSourceUrl;
        Qt.callLater(function() {
            if (surface.resolvedSourceUrl !== expectedSourceUrl)
                return;
            surface._applyInitialPosition();
            surface._maybeAutoPlay();
        });
    }

    onStoredPositionMsChanged: {
        if (seekSlider.pressed)
            return;
        if (!initialPositionApplied) {
            _applyInitialPosition();
            return;
        }
        if (Math.abs(Number(player.position || 0) - storedPositionMs) > 250)
            _seekTo(storedPositionMs);
    }

    Component.onCompleted: {
        _tryConsumePendingSurfaceAction();
        _syncSeekSlider();
    }

    Connections {
        target: host

        function onIsSelectedChanged() {
            if (host && host.isSelected) {
                surface._tryConsumePendingSurfaceAction();
                surface._maybeAutoPlay();
            }
        }

        function onNodeOpenRequested(nodeId) {
            if (!host || !host.nodeData)
                return;
            if (String(nodeId || "") !== String(host.nodeData.node_id || ""))
                return;
            surface._editSource();
        }
    }

    Connections {
        target: fullscreenBridgeRef

        function onVideoFullscreenClosed(nodeId, state) {
            if (!host || !host.nodeData)
                return;
            if (String(nodeId || "") !== String(host.nodeData.node_id || ""))
                return;
            surface._applyFullscreenReturnState(state || ({}));
        }
    }

    Connections {
        target: surface._canvasCommandBridge()

        function onManagedArtifactRenameReleaseRequested(nodeId) {
            surface._releaseForManagedArtifactRename(nodeId);
        }

        function onManagedArtifactRenameReleaseFinished(nodeId) {
            surface._restoreAfterManagedArtifactRename(nodeId);
        }
    }

    AudioOutput {
        id: audioOutput
        muted: surface.muted || surface.thumbnailPrimerActive
        volume: surface.volume
    }

    MediaPlayer {
        id: player
        objectName: "graphNodeVideoMediaPlayer"
        source: surface.effectiveResolvedSourceUrl
        audioOutput: audioOutput
        videoOutput: videoOutput
        playbackRate: surface.playbackRate
        loops: surface.loopEnabled && !surface.clipRangeActive ? MediaPlayer.Infinite : 1

        onMediaStatusChanged: {
            surface._applyInitialPosition();
            surface._maybeAutoPlay();
        }

        onDurationChanged: surface._syncSeekSlider()
        onPositionChanged: {
            surface._syncSeekSlider();
            surface._enforceClipRange();
        }
        onPlaybackStateChanged: {
            if (surface.artifactRenameReleaseActive)
                return;
            if (playbackState !== MediaPlayer.PlayingState) {
                if (surface.thumbnailPrimerActive || surface.thumbnailPrimerPauseCommitGuard) {
                    surface.thumbnailPrimerPauseCommitGuard = false;
                    thumbnailPrimerPauseGuardTimer.stop();
                    return;
                }
                surface._commitPosition(position);
            }
        }
    }

    Timer {
        id: thumbnailPrimerTimer
        interval: 500
        repeat: false
        onTriggered: surface._finishThumbnailPrimer()
    }

    Timer {
        id: thumbnailPrimerPauseGuardTimer
        interval: 350
        repeat: false
        onTriggered: surface.thumbnailPrimerPauseCommitGuard = false
    }

    Rectangle {
        visible: surface.surfaceShowFrame
        anchors.fill: parent
        radius: host ? Number(host.resolvedCornerRadius || 6) : 6
        color: host ? Qt.darker(host.surfaceColor, 1.03) : "#1b1d22"
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: host && host.isSelected
            ? host.themeSelectedOutlineColor
            : (host ? Qt.lighter(host.outlineColor, 1.1) : "#4a4f5a")
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: surface.contentLeftMargin
        anchors.rightMargin: surface.contentRightMargin
        anchors.topMargin: surface.contentTopMargin
        anchors.bottomMargin: surface.contentBottomMargin
        spacing: 6

        Rectangle {
            id: viewport
            objectName: "graphNodeVideoViewport"
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 132
            radius: 8
            color: host ? Qt.darker(host.inlineInputBackgroundColor, 1.04) : "#202228"
            border.width: 1
            border.color: host ? Qt.alpha(host.inlineInputBorderColor, 0.88) : "#4a4f5a"
            clip: true

            VideoOutput {
                id: videoOutput
                objectName: "graphNodeVideoOutput"
                anchors.fill: parent
                fillMode: surface.normalizedFitMode === "cover"
                    ? VideoOutput.PreserveAspectCrop
                    : VideoOutput.PreserveAspectFit
                visible: surface.resolvedSourceUrl.length > 0
                    && surface.previewState !== "error"
            }

            Text {
                objectName: "graphNodeVideoPlaceholder"
                anchors.centerIn: parent
                width: Math.min(parent.width - 28, 260)
                text: surface.statusText
                color: host ? host.inlineDrivenTextColor : "#bdc5d3"
                font.pixelSize: host ? Number(host.passiveFontPixelSize || 12) : 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                visible: surface.previewState !== "ready"
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }
        }

        RowLayout {
            id: controls
            objectName: "graphNodeVideoControls"
            Layout.fillWidth: true
            Layout.preferredHeight: 26
            spacing: 6

            Text {
                objectName: "graphNodeVideoElapsedLabel"
                text: surface._formatTime(seekSlider.value)
                color: host ? host.inlineInputTextColor : "#f0f2f5"
                font.pixelSize: 10
                Layout.preferredWidth: 42
                horizontalAlignment: Text.AlignRight
                verticalAlignment: Text.AlignVCenter
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }

            Slider {
                id: seekSlider
                objectName: "graphNodeVideoSeekSlider"
                Layout.fillWidth: true
                from: 0
                to: Math.max(1, Number(player.duration || 0))
                enabled: surface.validSourceActive
                live: true

                onPressedChanged: {
                    if (pressed) {
                        surface._beginInlineInteraction();
                        surface.resumeAfterSeek = player.playbackState === MediaPlayer.PlayingState;
                    } else {
                        surface._seekTo(value);
                        if (surface.resumeAfterSeek && surface.hostPlaybackAllowed)
                            player.play();
                        surface.resumeAfterSeek = false;
                        surface._commitPosition(value);
                    }
                }

                onMoved: surface._seekTo(value)

                Repeater {
                    model: surface._seekMarkers()

                    Rectangle {
                        readonly property var marker: modelData || ({})
                        readonly property real markerRatio: {
                            var duration = Math.max(1, Number(player.duration || 0));
                            return Math.max(0.0, Math.min(1.0, Number(marker.position_ms || 0) / duration));
                        }
                        objectName: "graphNodeVideoSeekMarker_" + String(marker.role || "")
                        parent: seekSlider
                        width: String(marker.role || "") === "bookmark" ? 3 : 2
                        height: String(marker.role || "") === "bookmark" ? 12 : 18
                        radius: 1
                        x: Math.round(Math.max(0, Math.min(seekSlider.width - width, 9 + (seekSlider.width - 18) * markerRatio)))
                        y: Math.round((seekSlider.height - height) / 2)
                        color: String(marker.role || "") === "bookmark"
                            ? (host ? host.nodeThemeColor : "#4DA8DA")
                            : "#F2B84B"
                        opacity: seekSlider.enabled ? 0.92 : 0.35
                        z: 10
                    }
                }
            }

            Text {
                objectName: "graphNodeVideoDurationLabel"
                text: surface._formatTime(player.duration)
                color: host ? host.inlineDrivenTextColor : "#bdc5d3"
                font.pixelSize: 10
                Layout.preferredWidth: 42
                verticalAlignment: Text.AlignVCenter
                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
            }
        }
    }

    GraphSurfaceControls.GraphSurfaceInteractiveRegion {
        id: seekRegion
        host: surface.host
        targetItem: seekSlider
        enabled: seekSlider.enabled
        onControlStarted: surface._beginInlineInteraction()
    }





    function _boundedNumber(key, fallback, minimum, maximum) {
        var numeric = propNumber(key, fallback);
        return Math.max(minimum, Math.min(maximum, numeric));
    }

    function _normalizedTimelineBookmarks(value) {
        var source = [];
        if (Array.isArray(value))
            source = value;
        else if (value && value.length !== undefined) {
            for (var sourceIndex = 0; sourceIndex < value.length; sourceIndex++)
                source.push(value[sourceIndex]);
        }
        var bookmarks = [];
        var seen = {};
        for (var index = 0; index < source.length; index++) {
            var item = source[index] || {};
            var position = Math.max(0, Math.round(Number(item.position_ms || 0)));
            var rawId = String(item.id || "").trim();
            var bookmarkId = rawId.length > 0 ? rawId : "bookmark-" + position + "-" + index;
            if (seen[bookmarkId])
                continue;
            seen[bookmarkId] = true;
            var label = String(item.label || "").trim();
            if (!label.length)
                label = _formatTime(position);
            bookmarks.push({
                "id": bookmarkId,
                "label": label.slice(0, 80),
                "position_ms": position
            });
        }
        bookmarks.sort(function(left, right) {
            var leftPosition = Number(left.position_ms || 0);
            var rightPosition = Number(right.position_ms || 0);
            if (leftPosition !== rightPosition)
                return leftPosition - rightPosition;
            return String(left.label || "").localeCompare(String(right.label || ""));
        });
        return bookmarks.slice(0, 200);
    }

    function _readyOrPlayingForAction() {
        return player.mediaStatus === MediaPlayer.LoadedMedia
            || player.mediaStatus === MediaPlayer.BufferedMedia
            || player.mediaStatus === MediaPlayer.EndOfMedia
            || player.playbackState === MediaPlayer.PlayingState
            || player.playbackState === MediaPlayer.PausedState;
    }

    function readyOrPlayingForAction() {
        return _readyOrPlayingForAction();
    }

    function _readyForInitialPosition() {
        return player.mediaStatus === MediaPlayer.LoadedMedia
            || player.mediaStatus === MediaPlayer.BufferedMedia
            || player.mediaStatus === MediaPlayer.EndOfMedia;
    }

    function _normalizedFitMode(value) {
        var normalized = String(value || "contain").trim().toLowerCase();
        return normalized === "cover" ? "cover" : "contain";
    }

    function _iconSource(name, size, color) {
        if (typeof uiIcons === "undefined" || !uiIcons || !uiIcons.has(name))
            return "";
        return uiIcons.sourceSized(name, size, color);
    }

    function _beginInlineInteraction() {
        if (host && host.nodeData)
            host.surfaceControlInteractionStarted(String(host.nodeData.node_id || ""));
    }

    function _commitInlineProperty(key, value) {
        if (host && host.nodeData)
            host.inlinePropertyCommitted(String(host.nodeData.node_id || ""), key, value);
    }

    function _commitSurfaceProperties(values) {
        if (!host || !host.nodeData)
            return false;
        var nodeId = String(host.nodeData.node_id || "");
        if (!nodeId.length)
            return false;
        var payload = values || ({});
        var canvasItem = _canvasItem();
        if (canvasItem && canvasItem.commitNodeSurfaceProperties) {
            if (canvasItem.commitNodeSurfaceProperties(nodeId, payload))
                return true;
        }
        var changed = false;
        for (var key in payload) {
            if (!Object.prototype.hasOwnProperty.call(payload, key))
                continue;
            _commitInlineProperty(key, payload[key]);
            changed = true;
        }
        return changed;
    }

    function _commitChromeAppearance(showTitle, showFrame) {
        return _commitSurfaceProperties({
            "show_title": Boolean(showTitle),
            "show_frame": Boolean(showFrame)
        });
    }

    // Position saves can be triggered by blur-pausing playback; avoid the inline
    // property path because it reselects the node as a control interaction.
    function _persistPlaybackPosition(position) {
        if (!host || !host.nodeData)
            return false;
        if (host.graphReadOnly !== undefined && Boolean(host.graphReadOnly))
            return false;
        var nodeId = String(host.nodeData.node_id || "");
        if (!nodeId.length)
            return false;
        var canvasItem = _canvasItem();
        var bridge = canvasItem && canvasItem.sceneCommandBridge
            ? canvasItem.sceneCommandBridge
            : null;
        if (bridge) {
            try {
                if (bridge.set_node_properties)
                    return Boolean(bridge.set_node_properties(nodeId, { "position_ms": position }));
            } catch (error) {
                // Fall back to the single-property slot below.
            }
            try {
                if (bridge.set_node_property) {
                    bridge.set_node_property(nodeId, "position_ms", position);
                    return true;
                }
            } catch (error) {
                return false;
            }
        }
        _commitInlineProperty("position_ms", position);
        return true;
    }

    function _canvasItem() {
        return host && host.canvasItem ? host.canvasItem : null;
    }

    function _canvasCommandBridge() {
        var canvasItem = _canvasItem();
        return canvasItem && canvasItem.canvasCommandBridgeRef
            ? canvasItem.canvasCommandBridgeRef
            : null;
    }

    function _currentPositionMs() {
        return Math.max(0, Math.round(seekSlider.pressed ? seekSlider.value : Number(player.position || 0)));
    }

    function _sidecarScenePoint(verticalOffset) {
        var nodeX = 0;
        var nodeY = 0;
        if (host && host.nodeData) {
            nodeX = Number(host.nodeData.x || 0);
            nodeY = Number(host.nodeData.y || 0);
        }
        var width = host ? Number(host.width || 0) : 0;
        return {
            "x": nodeX + Math.max(width + 28, 260),
            "y": nodeY + Number(verticalOffset || 0)
        };
    }

    function _capturedFrameImageNodeSize() {
        var width = host ? Number(host.width || 0) : 0;
        var height = host ? Number(host.height || 0) : 0;
        return {
            "width": isFinite(width) && width > 0 ? width : 0,
            "height": isFinite(height) && height > 0 ? height : 0
        };
    }

    function _browseInlinePropertyPath(key, currentPath, sourceMode) {
        if (!host || !host.browseNodePropertyPath)
            return "";
        var normalizedSourceMode = String(sourceMode || "").trim();
        if (normalizedSourceMode.length > 0)
            return String(host.browseNodePropertyPath(key, currentPath, normalizedSourceMode) || "");
        return String(host.browseNodePropertyPath(key, currentPath) || "");
    }

    function _resolvedVideoSourceUrl() {
        artifactRenameResolveGeneration;
        var fileSourceUrl = GraphMediaPanelSourceUtils.resolvedLocalFileSourceUrl(sourcePath);
        if (fileSourceUrl.length > 0)
            return fileSourceUrl;
        if (!GraphMediaPanelSourceUtils.isProjectArtifactRef(sourcePath))
            return "";
        if (!host || !host.resolveLocalFileSourceUrl)
            return "";
        return String(host.resolveLocalFileSourceUrl(sourcePath) || "");
    }

    function _internalizeSource() {
        if (!canInternalizeSource || !host || !host.internalizeNodePropertyPath)
            return false;
        var managedPath = String(host.internalizeNodePropertyPath("source_path", sourcePath) || "");
        if (!managedPath.length || managedPath === sourcePath)
            return false;
        _commitInlineProperty("source_path", managedPath);
        return true;
    }

    function _repairRequestValue(currentPath) {
        return "ea-file-repair:" + encodeURIComponent(String(currentPath || ""));
    }

    function repairFile() {
        var repairedPath = _browseInlinePropertyPath("source_path", _repairRequestValue(sourcePath));
        if (!repairedPath.length)
            return;
        _commitInlineProperty("source_path", repairedPath);
    }

    function _editSource(sourceMode) {
        var selectedPath = _browseInlinePropertyPath(
            "source_path",
            sourcePath,
            SourceStorageModeUtils.normalizedSourceMode(sourceMode, sourceStorageMode)
        );
        if (!selectedPath.length || selectedPath === sourcePath)
            return false;
        _commitInlineProperty("source_path", selectedPath);
        return true;
    }

    function _commitTimelineBookmarks(bookmarks) {
        return _commitSurfaceProperties({
            "timeline_bookmarks": _normalizedTimelineBookmarks(bookmarks)
        });
    }

    function _bookmarkPopoverActions() {
        var actions = [
            {
                "id": "videoBookmarkAdd",
                "label": "Add " + _formatTime(_currentPositionMs()),
                "icon": "video-bookmark-add",
                "kind": "media",
                "role": "add",
                "enabled": true,
                "close_popover": false
            }
        ];
        for (var index = 0; index < timelineBookmarks.length; index++) {
            var bookmark = timelineBookmarks[index] || {};
            var encodedId = encodeURIComponent(String(bookmark.id || ""));
            actions.push({
                "id": "videoBookmarkJump:" + encodedId,
                "label": String(bookmark.label || ""),
                "icon": "video-bookmark-jump",
                "kind": "media",
                "role": "bookmark",
                "bookmark_id": String(bookmark.id || ""),
                "position_ms": Math.max(0, Math.round(Number(bookmark.position_ms || 0))),
                "time_text": _formatTime(bookmark.position_ms || 0),
                "rename_action_prefix": "videoBookmarkRename:" + encodedId + ":",
                "delete_action_id": "videoBookmarkDelete:" + encodedId,
                "enabled": true,
                "close_popover": false
            });
        }
        return actions;
    }

    function _clipPopoverActions() {
        return [
            {
                "id": "videoClipToggle",
                "label": clipRangeActive ? "Disable range" : "Enable range",
                "icon": "video-clip-range",
                "kind": "media",
                "toolbar_text": clipRangeActive ? "Disable" : "Enable",
                "enabled": clipEndMs > clipStartMs,
                "checked": clipRangeActive,
                "close_popover": false
            },
            {
                "id": "videoClipSetIn",
                "label": "Set in " + _formatTime(_currentPositionMs()),
                "icon": "video-clip-in",
                "kind": "media",
                "toolbar_text": "Set in",
                "enabled": true,
                "close_popover": false
            },
            {
                "id": "videoClipSetOut",
                "label": "Set out " + _formatTime(_currentPositionMs()),
                "icon": "video-clip-out",
                "kind": "media",
                "toolbar_text": "Set out",
                "enabled": true,
                "close_popover": false
            },
            {
                "id": "videoClipReplaceTrimmed",
                "label": "Replace with trimmed video",
                "icon": "video-trim-save",
                "kind": "media",
                "toolbar_text": "Replace",
                "enabled": validSourceActive && clipRangeActive,
                "close_popover": true
            },
            {
                "id": "videoClipSaveTrimmedCopy",
                "label": "Save trimmed copy",
                "icon": "video-trim-save",
                "kind": "media",
                "toolbar_text": "Copy",
                "enabled": validSourceActive && clipRangeActive,
                "close_popover": true
            },
            {
                "id": "videoClipClear",
                "label": "Clear range",
                "icon": "x",
                "kind": "media",
                "toolbar_text": "Clear",
                "enabled": clipStartMs > 0 || clipEndMs > 0 || clipEnabled,
                "close_popover": true
            }
        ];
    }

    function _addBookmarkAtCurrentPosition() {
        var position = _currentPositionMs();
        var bookmarks = timelineBookmarks.slice(0);
        bookmarks.push({
            "id": "bookmark-" + Date.now() + "-" + position,
            "label": _formatTime(position),
            "position_ms": position
        });
        return _commitTimelineBookmarks(bookmarks);
    }

    function _bookmarkIndex(bookmarkId) {
        var normalizedId = String(bookmarkId || "");
        for (var index = 0; index < timelineBookmarks.length; index++) {
            if (String((timelineBookmarks[index] || {}).id || "") === normalizedId)
                return index;
        }
        return -1;
    }

    function _jumpToBookmark(bookmarkId) {
        var index = _bookmarkIndex(bookmarkId);
        if (index < 0)
            return false;
        _seekTo(timelineBookmarks[index].position_ms || 0);
        _commitPosition(player.position);
        return true;
    }

    function _deleteBookmark(bookmarkId) {
        var normalizedId = String(bookmarkId || "");
        var next = [];
        for (var index = 0; index < timelineBookmarks.length; index++) {
            var bookmark = timelineBookmarks[index] || {};
            if (String(bookmark.id || "") !== normalizedId)
                next.push(bookmark);
        }
        return _commitTimelineBookmarks(next);
    }

    function _renameBookmark(bookmarkId, label) {
        var normalizedId = String(bookmarkId || "");
        var nextLabel = String(label || "").trim().slice(0, 80);
        if (!nextLabel.length)
            return false;
        var next = [];
        for (var index = 0; index < timelineBookmarks.length; index++) {
            var bookmark = timelineBookmarks[index] || {};
            if (String(bookmark.id || "") === normalizedId) {
                next.push({
                    "id": String(bookmark.id || ""),
                    "label": nextLabel,
                    "position_ms": Math.max(0, Math.round(Number(bookmark.position_ms || 0)))
                });
            } else {
                next.push(bookmark);
            }
        }
        return _commitTimelineBookmarks(next);
    }

    function _commitClipProperties(values) {
        return _commitSurfaceProperties(values || ({}));
    }

    function _setClipStartAtCurrentPosition() {
        var position = _currentPositionMs();
        var end = Math.max(0, Math.round(Number(clipEndMs || 0)));
        if (end <= position)
            end = Math.max(position + 1000, Math.round(Number(player.duration || 0)));
        return _commitClipProperties({
            "clip_enabled": true,
            "clip_start_ms": position,
            "clip_end_ms": end
        });
    }

    function _setClipEndAtCurrentPosition() {
        var position = _currentPositionMs();
        var start = Math.max(0, Math.round(Number(clipStartMs || 0)));
        if (position <= start)
            start = Math.max(0, position - 1000);
        return _commitClipProperties({
            "clip_enabled": true,
            "clip_start_ms": start,
            "clip_end_ms": Math.max(start + 1, position)
        });
    }

    function _toggleClipRange() {
        if (clipEndMs <= clipStartMs)
            return false;
        return _commitClipProperties({ "clip_enabled": !clipRangeActive });
    }

    function _clearClipRange() {
        return _commitClipProperties({
            "clip_enabled": false,
            "clip_start_ms": 0,
            "clip_end_ms": 0
        });
    }

    function _trimStatePayload() {
        return {
            "source_path": sourcePath,
            "fit_mode": normalizedFitMode,
            "muted": muted,
            "loop": loopEnabled,
            "volume": volume,
            "playback_rate": playbackRate,
            "timeline_bookmarks": timelineBookmarks,
            "clip_enabled": clipRangeActive,
            "clip_start_ms": clipStartMs,
            "clip_end_ms": clipEndMs
        };
    }

    function _replaceWithTrimmedClip() {
        if (!validSourceActive || !clipRangeActive || !host || !host.nodeData)
            return false;
        var bridge = _canvasCommandBridge();
        if (!bridge || !bridge.request_trim_video_clip_replace)
            return false;
        var nodeId = String(host.nodeData.node_id || "");
        if (!nodeId.length)
            return false;
        var result = bridge.request_trim_video_clip_replace(
            nodeId,
            clipStartMs,
            clipEndMs,
            _trimStatePayload()
        );
        return Boolean(result && result.success);
    }

    function _saveTrimmedClipCopy() {
        if (!validSourceActive || !clipRangeActive || !host || !host.nodeData)
            return false;
        var bridge = _canvasCommandBridge();
        if (!bridge || !bridge.request_trim_video_clip_copy)
            return false;
        var nodeId = String(host.nodeData.node_id || "");
        if (!nodeId.length)
            return false;
        var point = _sidecarScenePoint(96);
        var result = bridge.request_trim_video_clip_copy(
            nodeId,
            clipStartMs,
            clipEndMs,
            point.x,
            point.y,
            _trimStatePayload()
        );
        return Boolean(result && result.success);
    }

    function _captureFrameToImageNode() {
        if (!validSourceActive || !_readyOrPlayingForAction())
            return false;
        if (!videoOutput || !videoOutput.grabToImage)
            return false;
        var bridge = _canvasCommandBridge();
        if (!bridge || !bridge.video_frame_capture_path || !bridge.request_create_video_frame_image_node)
            return false;
        if (!host || !host.nodeData)
            return false;
        var nodeId = String(host.nodeData.node_id || "");
        if (!nodeId.length)
            return false;
        var position = _currentPositionMs();
        var capturePath = String(bridge.video_frame_capture_path(nodeId, position) || "");
        if (!capturePath.length)
            return false;
        var point = _sidecarScenePoint(0);
        var size = _capturedFrameImageNodeSize();
        videoOutput.grabToImage(function(result) {
            if (!result || !result.saveToFile || !result.saveToFile(capturePath))
                return;
            bridge.request_create_video_frame_image_node(
                nodeId,
                capturePath,
                position,
                point.x,
                point.y,
                size.width,
                size.height
            );
        });
        return true;
    }

    function _createTimestampAnnotation() {
        if (!validSourceActive || !host || !host.nodeData)
            return false;
        var bridge = _canvasCommandBridge();
        if (!bridge || !bridge.request_create_video_timestamp_annotation)
            return false;
        var nodeId = String(host.nodeData.node_id || "");
        if (!nodeId.length)
            return false;
        var point = _sidecarScenePoint(72);
        var result = bridge.request_create_video_timestamp_annotation(nodeId, _currentPositionMs(), point.x, point.y);
        return Boolean(result && result.success);
    }

    function _tryConsumePendingSurfaceAction() {
        if (!host || !host.nodeData)
            return;
        var canvasItem = _canvasItem();
        var nodeId = String(host.nodeData.node_id || "");
        if (nodeId.length > 0
                && canvasItem
                && canvasItem.consumePendingNodeSurfaceAction
                && canvasItem.consumePendingNodeSurfaceAction(nodeId)) {
            _editSource();
        }
    }

    function _statusText() {
        if (sourcePath.trim().length === 0)
            return "Choose a local video file to preview it here.";
        if (sourceRejected)
            return "Video source must be an absolute local path or file URL.";
        if (player.error !== MediaPlayer.NoError)
            return player.errorString && player.errorString.length > 0
                ? player.errorString
                : "Video could not be loaded.";
        if (player.mediaStatus === MediaPlayer.InvalidMedia)
            return "Video could not be loaded.";
        if (previewState === "loading")
            return "Loading video...";
        return "";
    }

    function _applyInitialPosition() {
        if (initialPositionApplied)
            return;
        if (!_readyForInitialPosition())
            return;
        if (storedPositionMs <= 0) {
            _seekTo(_initialThumbnailPositionMs());
            _primeThumbnailFrame();
            initialPositionApplied = true;
            _syncSeekSlider();
            return;
        }
        _seekTo(storedPositionMs);
        _primeThumbnailFrame();
        initialPositionApplied = true;
    }

    function _initialThumbnailPositionMs() {
        if (clipRangeActive && clipStartMs > 0)
            return clipStartMs;
        return 1;
    }

    function _primeThumbnailFrame() {
        if (artifactRenameReleaseActive)
            return;
        if (thumbnailPrimerComplete || thumbnailPrimerActive)
            return;
        if (!validSourceActive || sourceRejected || autoPlayEnabled || fullscreenOwnsPlayback)
            return;
        if (player.playbackState === MediaPlayer.PlayingState)
            return;
        thumbnailPrimerComplete = true;
        thumbnailPrimerActive = true;
        thumbnailPrimerTimer.restart();
        player.play();
    }

    function _finishThumbnailPrimer() {
        if (!thumbnailPrimerActive)
            return;
        thumbnailPrimerPauseCommitGuard = true;
        thumbnailPrimerPauseGuardTimer.restart();
        player.pause();
        thumbnailPrimerActive = false;
        _syncSeekSlider();
    }

    function _maybeAutoPlay() {
        if (artifactRenameReleaseActive)
            return;
        if (!autoPlayEnabled || !hostPlaybackAllowed)
            return;
        if (resolvedSourceUrl.length === 0 || sourceRejected)
            return;
        if (player.playbackState === MediaPlayer.PlayingState)
            return;
        player.play();
    }

    // A play-button click selects the node, but host.isSelected can lag until
    // after this action handler returns.
    function _explicitPlaybackStartAllowed() {
        if (fullscreenOwnsPlayback)
            return false;
        if (hostPlaybackAllowed)
            return true;
        return !!(host && host.nodeData);
    }

    function togglePlayback() {
        if (!validSourceActive || artifactRenameReleaseActive)
            return false;
        _beginInlineInteraction();
        if (player.playbackState === MediaPlayer.PlayingState) {
            player.pause();
            _commitPosition(player.position);
            return true;
        }
        if (!_explicitPlaybackStartAllowed())
            return false;
        player.play();
        return true;
    }

    function _seekTo(positionMs) {
        var duration = Math.max(0, Number(player.duration || 0));
        var target = _clampedPlaybackPosition(positionMs);
        if (duration > 0)
            target = Math.min(target, duration);
        player.position = target;
        seekSlider.value = target;
    }

    function seekBy(deltaMs) {
        if (!validSourceActive)
            return false;
        _beginInlineInteraction();
        _seekTo(Number(player.position || 0) + Number(deltaMs || 0));
        _commitPosition(player.position);
        return true;
    }

    function rewindToStart() {
        if (!validSourceActive)
            return false;
        _beginInlineInteraction();
        _seekTo(0);
        _commitPosition(player.position);
        return true;
    }

    function _syncSeekSlider() {
        if (seekSlider.pressed)
            return;
        seekSlider.to = Math.max(1, Number(player.duration || 0));
        seekSlider.value = Math.max(0, Number(player.position || 0));
    }

    function _clampedPlaybackPosition(positionMs) {
        var target = Math.max(0, Math.round(Number(positionMs || 0)));
        var duration = Math.max(0, Math.round(Number(player.duration || 0)));
        if (duration > 0)
            target = Math.min(target, duration);
        if (!clipRangeActive)
            return target;
        var start = Math.max(0, Math.round(Number(clipStartMs || 0)));
        var end = Math.max(start + 1, Math.round(Number(clipEndMs || 0)));
        if (duration > 0)
            end = Math.min(end, duration);
        if (target < start)
            return start;
        if (target > end)
            return end;
        return target;
    }

    function _enforceClipRange() {
        if (!clipRangeActive || clipEnforcing)
            return;
        var position = Math.max(0, Math.round(Number(player.position || 0)));
        var start = Math.max(0, Math.round(Number(clipStartMs || 0)));
        var end = Math.max(start + 1, Math.round(Number(clipEndMs || 0)));
        var duration = Math.max(0, Math.round(Number(player.duration || 0)));
        if (duration > 0)
            end = Math.min(end, duration);
        if (position < start) {
            clipEnforcing = true;
            _seekTo(start);
            clipEnforcing = false;
            return;
        }
        if (position >= end) {
            clipEnforcing = true;
            if (loopEnabled && hostPlaybackAllowed) {
                _seekTo(start);
                player.play();
            } else {
                _seekTo(end);
                player.pause();
                _commitPosition(end);
            }
            clipEnforcing = false;
        }
    }

    function _seekMarkers() {
        var markers = [];
        if (clipEndMs > clipStartMs) {
            markers.push({ "role": "clip_start", "position_ms": clipStartMs });
            markers.push({ "role": "clip_end", "position_ms": clipEndMs });
        }
        for (var index = 0; index < timelineBookmarks.length; index++) {
            var bookmark = timelineBookmarks[index] || {};
            markers.push({
                "role": "bookmark",
                "position_ms": Math.max(0, Math.round(Number(bookmark.position_ms || 0))),
                "label": String(bookmark.label || "")
            });
        }
        return markers;
    }

    function _commitPosition(positionMs) {
        var position = Math.max(0, Math.round(Number(positionMs || 0)));
        if (position !== storedPositionMs)
            return _persistPlaybackPosition(position);
        return false;
    }

    function _runtimeState() {
        return {
            "position_ms": Math.max(0, Math.round(seekSlider.pressed ? seekSlider.value : player.position)),
            "playing": player.playbackState === MediaPlayer.PlayingState,
            "muted": surface.muted,
            "volume": surface.volume,
            "playback_rate": surface.playbackRate,
            "loop": surface.loopEnabled,
            "fit_mode": surface.normalizedFitMode,
            "timeline_bookmarks": surface.timelineBookmarks,
            "clip_enabled": surface.clipRangeActive,
            "clip_start_ms": surface.clipStartMs,
            "clip_end_ms": surface.clipEndMs
        };
    }

    function _isManagedArtifactRenameTarget(nodeId) {
        return !!(host && host.nodeData)
            && String(nodeId || "") === String(host.nodeData.node_id || "");
    }

    function _releaseForManagedArtifactRename(nodeId) {
        if (!_isManagedArtifactRenameTarget(nodeId))
            return;
        artifactRenameReleaseState = _runtimeState();
        thumbnailPrimerTimer.stop();
        thumbnailPrimerPauseGuardTimer.stop();
        thumbnailPrimerActive = false;
        thumbnailPrimerPauseCommitGuard = false;
        if (player.playbackState === MediaPlayer.PlayingState)
            player.pause();
        artifactRenameReleaseActive = true;
    }

    function _restoreAfterManagedArtifactRename(nodeId) {
        if (!_isManagedArtifactRenameTarget(nodeId) || !artifactRenameReleaseActive)
            return;
        var state = artifactRenameReleaseState || ({});
        artifactRenameResolveGeneration += 1;
        artifactRenameReleaseActive = false;
        initialPositionApplied = false;
        Qt.callLater(function() {
            if (!surface.artifactRenameReleaseActive)
                surface._applyFullscreenReturnState(state);
        });
    }

    function _requestContentFullscreen() {
        if (!fullscreenAvailable || !validSourceActive || !host || !host.requestSurfaceContentFullscreen)
            return false;
        var state = _runtimeState();
        var opened = Boolean(host.requestSurfaceContentFullscreen(state));
        if (opened)
            player.pause();
        return opened;
    }

    function _applyFullscreenReturnState(state) {
        var payload = state || ({});
        if (artifactRenameReleaseActive) {
            artifactRenameReleaseState = payload;
            return;
        }
        if (payload.position_ms !== undefined)
            _seekTo(payload.position_ms);
        if (Boolean(payload.playing) && hostPlaybackAllowed) {
            player.play();
        } else {
            player.pause();
            _primeThumbnailFrame();
        }
    }

    function _rateIndex(rate) {
        var value = Number(rate || 1.0);
        if (value <= 0.75)
            return 0;
        if (value <= 1.125)
            return 1;
        if (value <= 1.375)
            return 2;
        if (value <= 1.75)
            return 3;
        return 4;
    }

    function _rateForIndex(index) {
        var rates = [0.5, 1.0, 1.25, 1.5, 2.0];
        var normalized = Math.max(0, Math.min(rates.length - 1, Number(index || 0)));
        return rates[normalized];
    }

    function _formatTime(positionMs) {
        var totalSeconds = Math.max(0, Math.floor(Number(positionMs || 0) / 1000));
        var hours = Math.floor(totalSeconds / 3600);
        var minutes = Math.floor((totalSeconds % 3600) / 60);
        var seconds = totalSeconds % 60;
        var secondText = seconds < 10 ? "0" + seconds : "" + seconds;
        if (hours > 0) {
            var minuteText = minutes < 10 ? "0" + minutes : "" + minutes;
            return hours + ":" + minuteText + ":" + secondText;
        }
        return minutes + ":" + secondText;
    }

    function dispatchSurfaceAction(actionId) {
        var normalized = String(actionId || "");
        _beginInlineInteraction();
        if (normalized === "editSource")
            return _editSource();
        if (normalized === "editSourceManagedCopy")
            return _editSource("managed_copy");
        if (normalized === "editSourceExternalLink")
            return _editSource("external_link");
        if (normalized === "internalizeSource")
            return _internalizeSource();
        if (normalized === "toggle_content_only") {
            return surfaceContentOnly
                ? _commitChromeAppearance(true, true)
                : _commitChromeAppearance(false, false);
        }
        if (normalized === "toggle_title")
            return _commitChromeAppearance(!surfaceShowTitle, surfaceShowFrame);
        if (normalized === "toggle_frame")
            return _commitChromeAppearance(surfaceShowTitle, !surfaceShowFrame);
        if (normalized === "playPause")
            return togglePlayback();
        if (normalized === "rewindToStart")
            return rewindToStart();
        if (normalized === "seekBack10")
            return seekBy(-10000);
        if (normalized === "seekForward10")
            return seekBy(10000);
        if (normalized === "videoBookmarkAdd")
            return _addBookmarkAtCurrentPosition();
        if (normalized.indexOf("videoBookmarkJump:") === 0)
            return _jumpToBookmark(decodeURIComponent(normalized.slice("videoBookmarkJump:".length)));
        if (normalized.indexOf("videoBookmarkDelete:") === 0)
            return _deleteBookmark(decodeURIComponent(normalized.slice("videoBookmarkDelete:".length)));
        if (normalized.indexOf("videoBookmarkRename:") === 0) {
            var renamePayload = normalized.slice("videoBookmarkRename:".length);
            var splitAt = renamePayload.indexOf(":");
            if (splitAt < 0)
                return false;
            return _renameBookmark(
                decodeURIComponent(renamePayload.slice(0, splitAt)),
                decodeURIComponent(renamePayload.slice(splitAt + 1))
            );
        }
        if (normalized === "videoClipToggle")
            return _toggleClipRange();
        if (normalized === "videoClipSetIn")
            return _setClipStartAtCurrentPosition();
        if (normalized === "videoClipSetOut")
            return _setClipEndAtCurrentPosition();
        if (normalized === "videoClipReplaceTrimmed")
            return _replaceWithTrimmedClip();
        if (normalized === "videoClipSaveTrimmedCopy")
            return _saveTrimmedClipCopy();
        if (normalized === "videoClipClear")
            return _clearClipRange();
        if (normalized === "captureFrame")
            return _captureFrameToImageNode();
        if (normalized === "timestampAnnotation")
            return _createTimestampAnnotation();
        if (normalized === "mute") {
            if (!validSourceActive)
                return false;
            _commitInlineProperty("muted", !muted);
            return true;
        }
        if (normalized === "loop") {
            if (!validSourceActive)
                return false;
            _commitInlineProperty("loop", !loopEnabled);
            return true;
        }
        if (normalized === "fitMode") {
            if (!validSourceActive)
                return false;
            _commitInlineProperty(
                "fit_mode",
                normalizedFitMode === "cover" ? "contain" : "cover"
            );
            return true;
        }
        if (normalized === "fullscreen")
            return _requestContentFullscreen();
        if (normalized === "repair") {
            if (!fileIssueActive)
                return false;
            repairFile();
            return true;
        }
        return false;
    }
}
