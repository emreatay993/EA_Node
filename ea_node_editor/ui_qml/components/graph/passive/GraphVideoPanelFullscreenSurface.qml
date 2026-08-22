import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtMultimedia
import "../../shell" as ShellComponents
import "../../common/TooltipCopy.js" as TooltipCopy

FocusScope {
    id: root
    objectName: "contentFullscreenVideoSurface"
    property var payload: ({})
    property var bridgeRef: null
    property var themePalette: ({})
    property bool initialPositionApplied: false
    property bool resumeAfterSeek: false
    property bool clipEnforcing: false
    property bool thumbnailPrimerActive: false
    property bool thumbnailPrimerComplete: false
    property bool mutedValue: false
    property real volumeValue: 1.0
    property real playbackRateValue: 1.0
    property bool loopValue: false
    property string fitModeValue: "contain"
    property var timelineBookmarksValue: []
    property bool clipEnabledValue: false
    property int clipStartValue: 0
    property int clipEndValue: 0
    readonly property var transientState: payload && payload.transient_state ? payload.transient_state : ({})
    readonly property bool videoPayloadActive: String(payload && payload.media_kind || "") === "video"
    readonly property string sourceUrl: videoPayloadActive ? String(payload && payload.resolved_source_url || "") : ""
    readonly property int initialPositionMs: Math.max(
        0,
        Math.round(Number(transientState.position_ms !== undefined
            ? transientState.position_ms
            : (payload ? payload.position_ms || 0 : 0)))
    )
    readonly property bool shouldResumePlaying: transientState.playing !== undefined
        ? Boolean(transientState.playing)
        : Boolean(payload && payload.auto_play)
    readonly property bool readyOrPlaying: player.mediaStatus === MediaPlayer.LoadedMedia
        || player.mediaStatus === MediaPlayer.BufferedMedia
        || player.mediaStatus === MediaPlayer.EndOfMedia
        || player.playbackState === MediaPlayer.PlayingState
        || player.playbackState === MediaPlayer.PausedState
    readonly property bool errorActive: player.error !== MediaPlayer.NoError
        || player.mediaStatus === MediaPlayer.InvalidMedia
        || sourceUrl.length === 0
    readonly property bool clipRangeActive: clipEnabledValue && clipEndValue > clipStartValue
    readonly property string statusText: _statusText()

    focus: visible
    activeFocusOnTab: visible

    onVisibleChanged: {
        if (visible) {
            _syncFromPayload();
            Qt.callLater(function() {
                if (root.visible)
                    root.forceActiveFocus();
            });
        }
    }

    onPayloadChanged: _syncFromPayload()
    onSourceUrlChanged: {
        initialPositionApplied = false;
        thumbnailPrimerActive = false;
        thumbnailPrimerComplete = false;
        thumbnailPrimerTimer.stop();
        seekSlider.value = 0;
    }

    Keys.priority: Keys.BeforeItem
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Space) {
            togglePlayback();
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_Left) {
            seekBy(-10000);
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_Right) {
            seekBy(10000);
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_M) {
            mutedValue = !mutedValue;
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_Escape || event.key === Qt.Key_F11) {
            requestCloseWithState();
            event.accepted = true;
        }
    }

    AudioOutput {
        id: audioOutput
        muted: root.mutedValue || root.thumbnailPrimerActive
        volume: volumeSlider.pressed ? volumeSlider.value : root.volumeValue
    }

    MediaPlayer {
        id: player
        objectName: "contentFullscreenVideoMediaPlayer"
        source: root.visible ? root.sourceUrl : ""
        audioOutput: audioOutput
        videoOutput: videoOutput
        playbackRate: root.playbackRateValue
        loops: root.loopValue && !root.clipRangeActive ? MediaPlayer.Infinite : 1

        onMediaStatusChanged: {
            root._applyInitialPosition();
            root._maybeResumePlaying();
            root._primeThumbnailFrame();
        }
        onDurationChanged: root._syncSeekSlider()
        onPositionChanged: {
            root._syncSeekSlider();
            root._enforceClipRange();
        }
    }

    Timer {
        id: thumbnailPrimerTimer
        interval: 500
        repeat: false
        onTriggered: root._finishThumbnailPrimer()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            id: viewport
            objectName: "contentFullscreenVideoViewport"
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 6
            color: root.themePalette.input_bg || "#111418"
            border.width: 1
            border.color: root.themePalette.input_border || "#4a4f5a"
            clip: true

            VideoOutput {
                id: videoOutput
                objectName: "contentFullscreenVideoOutput"
                anchors.fill: parent
                fillMode: root.fitModeValue === "cover"
                    ? VideoOutput.PreserveAspectCrop
                    : VideoOutput.PreserveAspectFit
                visible: root.sourceUrl.length > 0 && !root.errorActive
            }

            Text {
                objectName: "contentFullscreenVideoPlaceholder"
                anchors.centerIn: parent
                width: Math.min(parent.width - 48, 520)
                text: root.statusText
                visible: root.errorActive || !root.readyOrPlaying
                color: root.themePalette.muted_fg || "#bdc5d3"
                font.pixelSize: 13
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }

        ColumnLayout {
            id: controls
            objectName: "contentFullscreenVideoControls"
            Layout.fillWidth: true
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    objectName: "contentFullscreenVideoElapsedLabel"
                    text: root._formatTime(seekSlider.value)
                    color: root.themePalette.panel_fg || "#f0f2f5"
                    font.pixelSize: 11
                    Layout.preferredWidth: 54
                    horizontalAlignment: Text.AlignRight
                    verticalAlignment: Text.AlignVCenter
                }

                Slider {
                    id: seekSlider
                    objectName: "contentFullscreenVideoSeekSlider"
                    Layout.fillWidth: true
                    from: 0
                    to: Math.max(1, Number(player.duration || 0))
                    enabled: root.sourceUrl.length > 0 && !root.errorActive
                    live: true
                    onPressedChanged: {
                        if (pressed) {
                            root.resumeAfterSeek = player.playbackState === MediaPlayer.PlayingState;
                        } else {
                            root._seekTo(value);
                            if (root.resumeAfterSeek)
                                player.play();
                            root.resumeAfterSeek = false;
                        }
                    }
                    onMoved: root._seekTo(value)

                    Repeater {
                        model: root._seekMarkers()

                        Rectangle {
                            readonly property var marker: modelData || ({})
                            readonly property real markerRatio: {
                                var duration = Math.max(1, Number(player.duration || 0));
                                return Math.max(0.0, Math.min(1.0, Number(marker.position_ms || 0) / duration));
                            }
                            objectName: "contentFullscreenVideoSeekMarker_" + String(marker.role || "")
                            parent: seekSlider
                            width: String(marker.role || "") === "bookmark" ? 3 : 2
                            height: String(marker.role || "") === "bookmark" ? 12 : 18
                            radius: 1
                            x: Math.round(Math.max(0, Math.min(seekSlider.width - width, 9 + (seekSlider.width - 18) * markerRatio)))
                            y: Math.round((seekSlider.height - height) / 2)
                            color: String(marker.role || "") === "bookmark"
                                ? (root.themePalette.accent || "#4DA8DA")
                                : "#F2B84B"
                            opacity: seekSlider.enabled ? 0.92 : 0.35
                            z: 10
                        }
                    }
                }

                Text {
                    objectName: "contentFullscreenVideoDurationLabel"
                    text: root._formatTime(player.duration)
                    color: root.themePalette.muted_fg || "#bdc5d3"
                    font.pixelSize: 11
                    Layout.preferredWidth: 54
                    verticalAlignment: Text.AlignVCenter
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                ShellComponents.ShellButton {
                    id: playButton
                    objectName: "contentFullscreenVideoPlayButton"
                    iconName: player.playbackState === MediaPlayer.PlayingState ? "pause" : "run"
                    tooltipText: player.playbackState === MediaPlayer.PlayingState
                        ? TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.pause")
                        : TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.play")
                    enabled: root.sourceUrl.length > 0 && !root.errorActive
                    onClicked: root.togglePlayback()
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoRewindButton"
                    iconName: "video-rewind"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.rewind_start")
                    enabled: playButton.enabled
                    onClicked: root.rewindToStart()
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoBackButton"
                    iconName: "video-seek-back-10"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.seek_back_10")
                    enabled: playButton.enabled
                    onClicked: root.seekBy(-10000)
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoForwardButton"
                    iconName: "video-seek-forward-10"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.seek_forward_10")
                    enabled: playButton.enabled
                    onClicked: root.seekBy(10000)
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoLoopButton"
                    iconName: "video-loop"
                    tooltipText: root.loopValue
                        ? TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.disable_loop")
                        : TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.loop")
                    selectedStyle: root.loopValue
                    enabled: playButton.enabled
                    onClicked: root.loopValue = !root.loopValue
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoMuteButton"
                    iconName: root.mutedValue ? "volume-muted" : "volume"
                    tooltipText: root.mutedValue
                        ? TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.unmute")
                        : TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.mute")
                    enabled: playButton.enabled
                    onClicked: root.mutedValue = !root.mutedValue
                }

                Slider {
                    id: volumeSlider
                    objectName: "contentFullscreenVideoVolumeSlider"
                    Layout.preferredWidth: 96
                    from: 0
                    to: 1
                    stepSize: 0.05
                    value: root.volumeValue
                    enabled: playButton.enabled
                    onPressedChanged: {
                        if (!pressed)
                            root.volumeValue = Math.max(0, Math.min(1, value));
                    }
                }

                ComboBox {
                    id: rateCombo
                    objectName: "contentFullscreenVideoRateCombo"
                    Layout.preferredWidth: 82
                    model: ["0.5x", "1x", "1.25x", "1.5x", "2x"]
                    currentIndex: root._rateIndex(root.playbackRateValue)
                    enabled: playButton.enabled
                    onActivated: root.playbackRateValue = root._rateForIndex(index)
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoFitButton"
                    iconName: root.fitModeValue === "cover" ? "video-fit" : "video-fill"
                    tooltipText: root.fitModeValue === "cover"
                        ? TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.fit_video")
                        : TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.fill_video")
                    selectedStyle: root.fitModeValue === "cover"
                    onClicked: root.fitModeValue = root.fitModeValue === "cover" ? "contain" : "cover"
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoAddBookmarkButton"
                    iconName: "video-bookmark-add"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.add_bookmark")
                    enabled: playButton.enabled
                    selectedStyle: root.timelineBookmarksValue.length > 0
                    onClicked: root._addBookmarkAtCurrentPosition()
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoClipInButton"
                    iconName: "video-clip-in"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.set_clip_in")
                    enabled: playButton.enabled
                    selectedStyle: root.clipRangeActive
                    onClicked: root._setClipStartAtCurrentPosition()
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoClipOutButton"
                    iconName: "video-clip-out"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.set_clip_out")
                    enabled: playButton.enabled
                    selectedStyle: root.clipRangeActive
                    onClicked: root._setClipEndAtCurrentPosition()
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoTrimReplaceButton"
                    iconName: "video-trim-save"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.replace_trimmed_video")
                    enabled: playButton.enabled && root.clipRangeActive
                    selectedStyle: false
                    onClicked: root._replaceWithTrimmedClip()
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoTrimCopyButton"
                    iconName: "video-trim-save"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.save_trimmed_copy")
                    enabled: playButton.enabled && root.clipRangeActive
                    selectedStyle: false
                    onClicked: root._saveTrimmedClipCopy()
                }

                ShellComponents.ShellButton {
                    objectName: "contentFullscreenVideoClipClearButton"
                    iconName: "x"
                    tooltipText: TooltipCopy.text(tooltipCopyBridge, "fullscreen.video.clear_clip_range")
                    enabled: playButton.enabled && (root.clipStartValue > 0 || root.clipEndValue > 0 || root.clipEnabledValue)
                    onClicked: root._clearClipRange()
                }

                Item { Layout.fillWidth: true }
            }
        }
    }

    function _syncFromPayload() {
        var source = payload || ({});
        var state = source.transient_state || ({});
        mutedValue = _boolValue(state.muted !== undefined ? state.muted : source.muted, false);
        volumeValue = _boundedNumber(state.volume !== undefined ? state.volume : source.volume, 1.0, 0.0, 1.0);
        playbackRateValue = _boundedNumber(
            state.playback_rate !== undefined ? state.playback_rate : source.playback_rate,
            1.0,
            0.25,
            4.0
        );
        loopValue = _boolValue(state.loop !== undefined ? state.loop : source.loop, false);
        fitModeValue = _normalizedFitMode(state.fit_mode !== undefined ? state.fit_mode : source.fit_mode);
        timelineBookmarksValue = _normalizedTimelineBookmarks(
            state.timeline_bookmarks !== undefined ? state.timeline_bookmarks : source.timeline_bookmarks
        );
        clipEnabledValue = _boolValue(state.clip_enabled !== undefined ? state.clip_enabled : source.clip_enabled, false);
        clipStartValue = Math.max(
            0,
            Math.round(Number(state.clip_start_ms !== undefined ? state.clip_start_ms : source.clip_start_ms || 0))
        );
        clipEndValue = Math.max(
            0,
            Math.round(Number(state.clip_end_ms !== undefined ? state.clip_end_ms : source.clip_end_ms || 0))
        );
    }

    function _boolValue(value, fallback) {
        if (typeof value === "boolean")
            return value;
        if (value === undefined || value === null)
            return Boolean(fallback);
        if (typeof value === "string") {
            var normalized = value.trim().toLowerCase();
            if (normalized === "true" || normalized === "1" || normalized === "yes")
                return true;
            if (normalized === "false" || normalized === "0" || normalized === "no")
                return false;
        }
        return Boolean(value);
    }

    function _boundedNumber(value, fallback, minimum, maximum) {
        var numeric = Number(value);
        if (!isFinite(numeric))
            numeric = Number(fallback);
        return Math.max(minimum, Math.min(maximum, numeric));
    }

    function _normalizedFitMode(value) {
        var normalized = String(value || "contain").trim().toLowerCase();
        return normalized === "cover" ? "cover" : "contain";
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
            var bookmarkId = String(item.id || "").trim() || "bookmark-" + position + "-" + index;
            if (seen[bookmarkId])
                continue;
            seen[bookmarkId] = true;
            var label = String(item.label || "").trim() || _formatTime(position);
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

    function _statusText() {
        if (sourceUrl.length === 0)
            return "Video source is unavailable.";
        if (player.error !== MediaPlayer.NoError)
            return player.errorString && player.errorString.length > 0
                ? player.errorString
                : "Video could not be loaded.";
        if (player.mediaStatus === MediaPlayer.InvalidMedia)
            return "Video could not be loaded.";
        return "Loading video...";
    }

    function _applyInitialPosition() {
        if (initialPositionApplied)
            return;
        if (player.mediaStatus !== MediaPlayer.LoadedMedia
                && player.mediaStatus !== MediaPlayer.BufferedMedia
                && player.mediaStatus !== MediaPlayer.EndOfMedia)
            return;
        _seekTo(_initialThumbnailPositionMs());
        _primeThumbnailFrame();
        initialPositionApplied = true;
    }

    function _initialThumbnailPositionMs() {
        if (initialPositionMs > 0)
            return initialPositionMs;
        if (clipRangeActive && clipStartValue > 0)
            return clipStartValue;
        return 1;
    }

    function _primeThumbnailFrame() {
        if (thumbnailPrimerComplete || thumbnailPrimerActive)
            return;
        if (initialPositionMs > 0 || shouldResumePlaying || errorActive)
            return;
        if (!readyOrPlaying || player.playbackState === MediaPlayer.PlayingState)
            return;
        thumbnailPrimerComplete = true;
        thumbnailPrimerActive = true;
        thumbnailPrimerTimer.restart();
        player.play();
    }

    function _finishThumbnailPrimer() {
        if (!thumbnailPrimerActive)
            return;
        player.pause();
        thumbnailPrimerActive = false;
        _syncSeekSlider();
    }

    function _maybeResumePlaying() {
        if (!shouldResumePlaying)
            return;
        if (!readyOrPlaying || errorActive)
            return;
        if (player.playbackState !== MediaPlayer.PlayingState)
            player.play();
    }

    function togglePlayback() {
        if (sourceUrl.length === 0 || errorActive)
            return;
        if (player.playbackState === MediaPlayer.PlayingState) {
            player.pause();
            return;
        }
        player.play();
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
        _seekTo(Number(player.position || 0) + Number(deltaMs || 0));
    }

    function rewindToStart() {
        _seekTo(0);
    }

    function _syncSeekSlider() {
        if (seekSlider.pressed)
            return;
        seekSlider.to = Math.max(1, Number(player.duration || 0));
        seekSlider.value = Math.max(0, Number(player.position || 0));
    }

    function _currentPositionMs() {
        return Math.max(0, Math.round(seekSlider.pressed ? seekSlider.value : Number(player.position || 0)));
    }

    function _clampedPlaybackPosition(positionMs) {
        var target = Math.max(0, Math.round(Number(positionMs || 0)));
        var duration = Math.max(0, Math.round(Number(player.duration || 0)));
        if (duration > 0)
            target = Math.min(target, duration);
        if (!clipRangeActive)
            return target;
        var start = Math.max(0, Math.round(Number(clipStartValue || 0)));
        var end = Math.max(start + 1, Math.round(Number(clipEndValue || 0)));
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
        var start = Math.max(0, Math.round(Number(clipStartValue || 0)));
        var end = Math.max(start + 1, Math.round(Number(clipEndValue || 0)));
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
            if (loopValue) {
                _seekTo(start);
                player.play();
            } else {
                _seekTo(end);
                player.pause();
            }
            clipEnforcing = false;
        }
    }

    function _seekMarkers() {
        var markers = [];
        if (clipEndValue > clipStartValue) {
            markers.push({ "role": "clip_start", "position_ms": clipStartValue });
            markers.push({ "role": "clip_end", "position_ms": clipEndValue });
        }
        for (var index = 0; index < timelineBookmarksValue.length; index++) {
            var bookmark = timelineBookmarksValue[index] || {};
            markers.push({
                "role": "bookmark",
                "position_ms": Math.max(0, Math.round(Number(bookmark.position_ms || 0))),
                "label": String(bookmark.label || "")
            });
        }
        return markers;
    }

    function _addBookmarkAtCurrentPosition() {
        var position = _currentPositionMs();
        var bookmarks = timelineBookmarksValue.slice(0);
        bookmarks.push({
            "id": "bookmark-" + Date.now() + "-" + position,
            "label": _formatTime(position),
            "position_ms": position
        });
        timelineBookmarksValue = _normalizedTimelineBookmarks(bookmarks);
    }

    function _setClipStartAtCurrentPosition() {
        var position = _currentPositionMs();
        var end = Math.max(0, Math.round(Number(clipEndValue || 0)));
        if (end <= position)
            end = Math.max(position + 1000, Math.round(Number(player.duration || 0)));
        clipStartValue = position;
        clipEndValue = end;
        clipEnabledValue = true;
    }

    function _setClipEndAtCurrentPosition() {
        var position = _currentPositionMs();
        var start = Math.max(0, Math.round(Number(clipStartValue || 0)));
        if (position <= start)
            start = Math.max(0, position - 1000);
        clipStartValue = start;
        clipEndValue = Math.max(start + 1, position);
        clipEnabledValue = true;
    }

    function _clearClipRange() {
        clipEnabledValue = false;
        clipStartValue = 0;
        clipEndValue = 0;
    }

    function _replaceWithTrimmedClip() {
        if (!bridgeRef || !bridgeRef.request_trim_video_clip_replace || !clipRangeActive)
            return false;
        var result = bridgeRef.request_trim_video_clip_replace(currentState());
        return Boolean(result && result.success);
    }

    function _saveTrimmedClipCopy() {
        if (!bridgeRef || !bridgeRef.request_trim_video_clip_copy || !clipRangeActive)
            return false;
        var result = bridgeRef.request_trim_video_clip_copy(currentState());
        return Boolean(result && result.success);
    }

    function currentState() {
        return {
            "position_ms": Math.max(0, Math.round(seekSlider.pressed ? seekSlider.value : player.position)),
            "playing": player.playbackState === MediaPlayer.PlayingState,
            "muted": mutedValue,
            "volume": volumeSlider.pressed ? volumeSlider.value : volumeValue,
            "playback_rate": playbackRateValue,
            "loop": loopValue,
            "fit_mode": fitModeValue,
            "timeline_bookmarks": timelineBookmarksValue,
            "clip_enabled": clipRangeActive,
            "clip_start_ms": clipStartValue,
            "clip_end_ms": clipEndValue
        };
    }

    function requestCloseWithState() {
        if (bridgeRef && bridgeRef.request_close_with_state)
            return Boolean(bridgeRef.request_close_with_state(currentState()));
        if (bridgeRef && bridgeRef.request_close) {
            bridgeRef.request_close();
            return true;
        }
        return false;
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
}
