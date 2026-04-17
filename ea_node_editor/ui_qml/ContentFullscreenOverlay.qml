import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components/shell"
import "components/graph/passive/GraphMediaPanelGeometry.js" as GraphMediaPanelGeometry

FocusScope {
    id: root
    objectName: "contentFullscreenOverlay"
    property var bridgeRef: null
    readonly property var themePalette: themeBridge.palette
    readonly property bool bridgeOpen: !!root.bridgeRef && Boolean(root.bridgeRef.open)
    readonly property string activeNodeId: root.bridgeRef ? String(root.bridgeRef.node_id || "") : ""
    readonly property string contentKind: root.bridgeRef ? String(root.bridgeRef.content_kind || "") : ""
    readonly property string titleText: root.bridgeRef ? String(root.bridgeRef.title || "") : ""
    readonly property var mediaPayload: root.bridgeRef && root.bridgeRef.media_payload ? root.bridgeRef.media_payload : ({})
    readonly property var viewerPayload: root.bridgeRef && root.bridgeRef.viewer_payload ? root.bridgeRef.viewer_payload : ({})
    readonly property string mediaKind: String(root.mediaPayload.media_kind || root.contentKind || "")
    readonly property string previewSourceUrl: String(root.mediaPayload.preview_url || "")
    readonly property string captionText: String(root.mediaPayload.caption || "")
    readonly property string sourcePath: String(root.mediaPayload.source_path || "")
    readonly property int sourcePixelWidth: Math.max(0, Number(root.mediaPayload.source_pixel_width || 0))
    readonly property int sourcePixelHeight: Math.max(0, Number(root.mediaPayload.source_pixel_height || 0))
    readonly property var mediaCrop: root._normalizedMediaCrop()
    readonly property string payloadFitMode: root._normalizedPayloadFitMode()
    readonly property string effectiveDisplayMode: root.localDisplayMode.length > 0
        ? root.localDisplayMode
        : root._displayModeFromPayload()
    property string localDisplayMode: ""

    visible: root.bridgeOpen
    enabled: visible
    focus: visible
    activeFocusOnTab: visible
    z: 2000

    onVisibleChanged: {
        if (visible) {
            Qt.callLater(function() {
                if (root.visible)
                    root.forceActiveFocus();
            });
        } else {
            root.localDisplayMode = "";
        }
    }

    onActiveNodeIdChanged: root.localDisplayMode = ""

    Keys.priority: Keys.BeforeItem
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Escape || event.key === Qt.Key_F11) {
            root.requestClose();
            event.accepted = true;
        }
    }

    function requestClose() {
        if (root.bridgeRef && root.bridgeRef.request_close)
            root.bridgeRef.request_close();
    }

    function _normalizedPayloadFitMode() {
        var value = String(root.mediaPayload.fit_mode || "contain").trim().toLowerCase();
        if (value === "cover" || value === "original")
            return value;
        return "contain";
    }

    function _displayModeFromPayload() {
        if (root.payloadFitMode === "cover")
            return "fill";
        if (root.payloadFitMode === "original")
            return "actual";
        return "fit";
    }

    function _normalizedMediaCrop() {
        var crop = root.mediaPayload.crop || ({});
        return GraphMediaPanelGeometry.normalizedCropRect(
            Number(crop.x || 0.0),
            Number(crop.y || 0.0),
            Number(crop.width || 1.0),
            Number(crop.height || 1.0)
        );
    }

    function _sourceClipRect() {
        if (root.mediaKind === "pdf")
            return Qt.rect(0, 0, mediaImage.sourceSize.width, mediaImage.sourceSize.height);
        if (!(root.sourcePixelWidth > 0) || !(root.sourcePixelHeight > 0))
            return Qt.rect(0, 0, 0, 0);
        return GraphMediaPanelGeometry.sourceClipRectFromNormalized(
            root.mediaCrop,
            root.sourcePixelWidth,
            root.sourcePixelHeight
        );
    }

    function _viewerStatusText() {
        var phase = String(root.viewerPayload.phase || "closed");
        var cacheState = String(root.viewerPayload.cache_state || "");
        var liveMode = String(root.viewerPayload.live_mode || "");
        var details = [];
        if (phase.length > 0)
            details.push("Session " + phase);
        if (cacheState.length > 0)
            details.push("Cache " + cacheState);
        if (liveMode.length > 0)
            details.push("Mode " + liveMode);
        return details.length > 0
            ? details.join("  |  ")
            : "Viewer surface is waiting for live retargeting.";
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.alpha(root.themePalette.app_bg, 0.97)
    }

    MouseArea {
        id: interactionBlocker
        objectName: "contentFullscreenInteractionBlocker"
        anchors.fill: parent
        z: 1
        acceptedButtons: Qt.AllButtons
        hoverEnabled: true
        preventStealing: true
        onPressed: function(mouse) { mouse.accepted = true; }
        onReleased: function(mouse) { mouse.accepted = true; }
        onWheel: function(wheel) { wheel.accepted = true; }
    }

    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12
        z: 2

        Rectangle {
            id: topBar
            objectName: "contentFullscreenTopBar"
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            radius: 6
            color: root.themePalette.toolbar_bg
            border.width: 1
            border.color: root.themePalette.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8
                spacing: 8

                Text {
                    id: titleLabel
                    objectName: "contentFullscreenTitleText"
                    Layout.fillWidth: true
                    text: root.titleText.length > 0 ? root.titleText : "Fullscreen content"
                    color: root.themePalette.panel_title_fg
                    font.pixelSize: 14
                    font.bold: true
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }

                Text {
                    id: shortcutHint
                    objectName: "contentFullscreenShortcutHint"
                    text: "Esc / F11"
                    color: root.themePalette.muted_fg
                    font.pixelSize: 11
                    verticalAlignment: Text.AlignVCenter
                }

                ShellButton {
                    id: closeButton
                    objectName: "contentFullscreenCloseButton"
                    text: "Close"
                    tooltipText: "Close fullscreen"
                    onClicked: root.requestClose()
                }
            }
        }

        Rectangle {
            id: contentFrame
            objectName: "contentFullscreenContentFrame"
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 8
            color: Qt.darker(root.themePalette.panel_bg, 1.08)
            border.width: 1
            border.color: root.themePalette.border
            clip: true

            ColumnLayout {
                id: mediaLayout
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10
                visible: root.contentKind === "image" || root.contentKind === "pdf"

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 28
                    spacing: 6

                    Text {
                        objectName: "contentFullscreenMediaSummary"
                        Layout.fillWidth: true
                        text: root.mediaKind === "pdf"
                            ? "PDF page " + Number(root.mediaPayload.resolved_page_number || root.mediaPayload.page_number || 1)
                            : (root.sourcePixelWidth > 0 && root.sourcePixelHeight > 0
                                ? root.sourcePixelWidth + " x " + root.sourcePixelHeight
                                : "Image preview")
                        color: root.themePalette.muted_fg
                        font.pixelSize: 11
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    ShellButton {
                        objectName: "contentFullscreenDisplayModeFitButton"
                        text: "Fit"
                        selectedStyle: root.effectiveDisplayMode === "fit"
                        onClicked: root.localDisplayMode = "fit"
                    }

                    ShellButton {
                        objectName: "contentFullscreenDisplayModeFillButton"
                        text: "Fill"
                        selectedStyle: root.effectiveDisplayMode === "fill"
                        onClicked: root.localDisplayMode = "fill"
                    }

                    ShellButton {
                        objectName: "contentFullscreenDisplayModeActualButton"
                        text: "100%"
                        selectedStyle: root.effectiveDisplayMode === "actual"
                        onClicked: root.localDisplayMode = "actual"
                    }
                }

                Rectangle {
                    id: mediaViewport
                    objectName: "contentFullscreenMediaViewport"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 6
                    color: root.themePalette.input_bg
                    border.width: 1
                    border.color: root.themePalette.input_border
                    clip: true

                    Image {
                        id: mediaImage
                        objectName: "contentFullscreenMediaImage"
                        anchors.centerIn: parent
                        asynchronous: false
                        cache: root.mediaKind === "pdf"
                        mipmap: true
                        smooth: true
                        source: root.previewSourceUrl
                        sourceClipRect: root._sourceClipRect()
                        sourceSize.width: root.mediaKind === "pdf" ? Math.max(1, Math.round(mediaViewport.width)) : 0
                        sourceSize.height: root.mediaKind === "pdf" ? Math.max(1, Math.round(mediaViewport.height)) : 0
                        fillMode: root.effectiveDisplayMode === "fill"
                            ? Image.PreserveAspectCrop
                            : Image.PreserveAspectFit
                        width: root.effectiveDisplayMode === "actual"
                            ? Math.max(1, implicitWidth)
                            : parent.width
                        height: root.effectiveDisplayMode === "actual"
                            ? Math.max(1, implicitHeight)
                            : parent.height
                        visible: root.previewSourceUrl.length > 0
                    }

                    Text {
                        objectName: "contentFullscreenMediaPlaceholder"
                        anchors.centerIn: parent
                        width: Math.min(parent.width - 48, 420)
                        visible: !mediaImage.visible || mediaImage.status === Image.Error
                        text: root.mediaKind === "pdf"
                            ? String(root.mediaPayload.pdf_preview && root.mediaPayload.pdf_preview.message
                                ? root.mediaPayload.pdf_preview.message
                                : "PDF preview is unavailable.")
                            : "Image preview is unavailable."
                        color: root.themePalette.muted_fg
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }

                Text {
                    id: captionLabel
                    objectName: "contentFullscreenCaptionText"
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? Math.min(64, implicitHeight) : 0
                    visible: root.captionText.length > 0
                    text: root.captionText
                    color: root.themePalette.panel_fg
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    maximumLineCount: 3
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                id: viewerViewport
                objectName: "contentFullscreenViewerViewport"
                anchors.fill: parent
                anchors.margins: 12
                visible: root.contentKind === "viewer"
                radius: 6
                color: root.themePalette.input_bg
                border.width: 1
                border.color: root.themePalette.accent

                Column {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 48, 520)
                    spacing: 10

                    Text {
                        objectName: "contentFullscreenViewerPlaceholderTitle"
                        width: parent.width
                        text: String(root.viewerPayload.title || root.titleText || "Viewer")
                        color: root.themePalette.panel_title_fg
                        font.pixelSize: 15
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        elide: Text.ElideRight
                    }

                    Text {
                        objectName: "contentFullscreenViewerStatusText"
                        width: parent.width
                        text: root._viewerStatusText()
                        color: root.themePalette.muted_fg
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        objectName: "contentFullscreenViewerRetargetHint"
                        width: parent.width
                        text: "Live viewer retargeting will attach here."
                        color: root.themePalette.muted_fg
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
