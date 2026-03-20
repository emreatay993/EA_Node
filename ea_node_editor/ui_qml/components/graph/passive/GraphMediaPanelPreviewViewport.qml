import QtQuick 2.15
import "../surface_controls" as GraphSurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry
import "GraphMediaPanelGeometry.js" as GraphMediaPanelGeometry

Rectangle {
    id: root
    property var surface: null
    property var overlayInteractiveRects: []
    default property alias overlayData: overlayLayer.data
    readonly property int previewImageStatus: previewImage.status
    readonly property real sourcePixelWidth: !!root.surface
        && !root.surface.isPdfPanel
        && sourceImageProbe.status === Image.Ready
        ? Number(sourceImageProbe.implicitWidth || 0)
        : 0
    readonly property real sourcePixelHeight: !!root.surface
        && !root.surface.isPdfPanel
        && sourceImageProbe.status === Image.Ready
        ? Number(sourceImageProbe.implicitHeight || 0)
        : 0
    readonly property var cropDisplayRect: GraphMediaPanelGeometry.containRect(
        root.width,
        root.height,
        root.sourcePixelWidth,
        root.sourcePixelHeight
    )
    readonly property var draftDisplayCropRect: GraphMediaPanelGeometry.displayCropRect(
        root.surface ? root.surface.draftCropX : 0.0,
        root.surface ? root.surface.draftCropY : 0.0,
        root.surface ? root.surface.draftCropW : 1.0,
        root.surface ? root.surface.draftCropH : 1.0,
        root.cropDisplayRect
    )
    readonly property real effectivePreviewSourceWidth: root.sourcePixelWidth > 0
        ? root.sourcePixelWidth * Number(root.surface ? root.surface.normalizedStoredCropRect.width || 0 : 0)
        : 0
    readonly property real effectivePreviewSourceHeight: root.sourcePixelHeight > 0
        ? root.sourcePixelHeight * Number(root.surface ? root.surface.normalizedStoredCropRect.height || 0 : 0)
        : 0
    readonly property var appliedPreviewRect: GraphMediaPanelGeometry.fitRect(
        root.width,
        root.height,
        root.effectivePreviewSourceWidth,
        root.effectivePreviewSourceHeight,
        root.surface ? root.surface.appliedFitMode : "contain"
    )
    readonly property real appliedPreviewScale: {
        if (!(root.effectivePreviewSourceWidth > 0) || !(root.effectivePreviewSourceHeight > 0))
            return 0.0;
        if (root.surface && root.surface.appliedFitMode === "original")
            return 1.0;
        return Number(root.appliedPreviewRect.width || 0) / root.effectivePreviewSourceWidth;
    }
    readonly property real appliedFullImageWidth: root.sourcePixelWidth > 0
        ? root.sourcePixelWidth * root.appliedPreviewScale
        : 0
    readonly property real appliedFullImageHeight: root.sourcePixelHeight > 0
        ? root.sourcePixelHeight * root.appliedPreviewScale
        : 0
    readonly property real appliedImageOffsetX: -Number(
        root.surface ? root.surface.normalizedStoredCropRect.x || 0 : 0
    ) * root.appliedFullImageWidth
    readonly property real appliedImageOffsetY: -Number(
        root.surface ? root.surface.normalizedStoredCropRect.y || 0 : 0
    ) * root.appliedFullImageHeight
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists(
        [
            inlinePathEditor.embeddedInteractiveRects,
            inlineCaptionEditor.embeddedInteractiveRects,
            root.overlayInteractiveRects
        ]
    )
    readonly property bool proxyPreviewVisible: !!root.surface && Boolean(root.surface.proxySurfaceActive)

    objectName: "graphNodeMediaPreviewViewport"
    radius: 8
    color: root.surface ? root.surface.viewportFillColor : "#202228"
    border.width: 1
    border.color: Qt.alpha(root.surface ? root.surface.panelBorderColor : "#4a4f5a", 0.82)
    clip: true

    Item {
        anchors.fill: parent

        GraphSurfaceControls.GraphSurfacePathEditor {
            id: inlinePathEditor
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 8
            z: 4
            visible: root.surface ? root.surface.inlineEditorsVisible : false
            enabled: visible
            host: root.surface ? root.surface.host : null
            propertyKey: "source_path"
            committedText: root.surface ? root.surface.sourcePath : ""
            fieldObjectName: "graphNodeInlinePathEditor"
            browseButtonObjectName: "graphNodeInlinePathBrowseButton"
            browsePathResolver: function(currentPath) {
                return root.surface ? root.surface._browseInlinePropertyPath("source_path", currentPath) : "";
            }
            onControlStarted: root.surface._beginInlineInteraction()
            onCommitRequested: function(value) {
                root.surface._commitInlineProperty("source_path", value);
            }
        }

        Image {
            id: sourceImageProbe
            visible: false
            asynchronous: false
            cache: true
            source: root.surface && root.surface.isPdfPanel ? "" : (root.surface ? root.surface.previewSourceUrl : "")
        }

        Image {
            id: previewImage
            objectName: "graphNodeMediaPreviewImage"
            anchors.centerIn: parent
            asynchronous: false
            cache: root.surface ? root.surface.isPdfPanel : false
            mipmap: true
            fillMode: root.surface && root.surface.isPdfPanel
                ? Image.PreserveAspectFit
                : (root.surface && root.surface.normalizedFitMode === "cover"
                    ? Image.PreserveAspectCrop
                    : Image.PreserveAspectFit)
            source: root.surface ? root.surface.previewSourceUrl : ""
            sourceClipRect: root.surface && root.surface.isPdfPanel
                ? Qt.rect(0, 0, sourceSize.width, sourceSize.height)
                : (root.surface ? root.surface.appliedSourceClipRect : Qt.rect(0, 0, 0, 0))
            sourceSize.width: root.surface && root.surface.isPdfPanel ? Math.max(1, Math.round(root.width)) : 0
            sourceSize.height: root.surface && root.surface.isPdfPanel ? Math.max(1, Math.round(root.height)) : 0
            width: root.surface && root.surface.originalModeActive
                ? Math.max(1, implicitWidth)
                : parent.width
            height: root.surface && root.surface.originalModeActive
                ? Math.max(1, implicitHeight)
                : parent.height
            visible: root.surface
                && root.surface.isPdfPanel
                && root.surface.previewState === "ready"
                && !root.proxyPreviewVisible
                && !root.surface.cropModeActive
            smooth: true
        }

        Item {
            id: appliedImageViewport
            objectName: "graphNodeMediaAppliedImageViewport"
            x: Number(root.appliedPreviewRect.x || 0)
            y: Number(root.appliedPreviewRect.y || 0)
            width: Math.max(0, Number(root.appliedPreviewRect.width || 0))
            height: Math.max(0, Number(root.appliedPreviewRect.height || 0))
            visible: root.surface
                && !root.surface.isPdfPanel
                && root.surface.previewState === "ready"
                && !root.proxyPreviewVisible
                && !root.surface.cropModeActive
            clip: true

            Image {
                id: appliedImage
                objectName: "graphNodeMediaAppliedImage"
                x: Number(root.appliedImageOffsetX || 0)
                y: Number(root.appliedImageOffsetY || 0)
                width: Math.max(0, Number(root.appliedFullImageWidth || 0))
                height: Math.max(0, Number(root.appliedFullImageHeight || 0))
                asynchronous: false
                cache: true
                mipmap: true
                fillMode: Image.Stretch
                source: root.surface ? root.surface.previewSourceUrl : ""
                smooth: true
            }
        }

        Item {
            id: proxyPreview
            objectName: "graphNodeMediaProxyPreview"
            anchors.fill: parent
            visible: root.proxyPreviewVisible

            Rectangle {
                anchors.fill: parent
                radius: 6
                color: Qt.alpha(root.surface ? root.surface.panelBorderColor : "#4a4f5a", 0.08)
                border.width: 1
                border.color: Qt.alpha(root.surface ? root.surface.panelBorderColor : "#4a4f5a", 0.38)
            }

            Column {
                anchors.centerIn: parent
                width: Math.min(parent.width - 24, root.surface && root.surface.isPdfPanel ? 224 : 208)
                spacing: 8

                Item {
                    width: 44
                    height: 44
                    anchors.horizontalCenter: parent.horizontalCenter

                    Rectangle {
                        anchors.fill: parent
                        radius: 10
                        color: Qt.alpha(root.surface ? root.surface.panelFillColor : "#1b1d22", 0.82)
                        border.width: 1
                        border.color: Qt.alpha(root.surface ? root.surface.panelBorderColor : "#4a4f5a", 0.68)
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: root.surface && root.surface.isPdfPanel ? 18 : 20
                        height: root.surface && root.surface.isPdfPanel ? 24 : 16
                        radius: 3
                        color: "transparent"
                        border.width: 1
                        border.color: Qt.alpha(root.surface ? root.surface.hintTextColor : "#bdc5d3", 0.9)
                    }

                    Rectangle {
                        visible: !(root.surface && root.surface.isPdfPanel)
                        anchors.centerIn: parent
                        width: 10
                        height: 6
                        radius: 2
                        color: Qt.alpha(root.surface ? root.surface.hintTextColor : "#bdc5d3", 0.65)
                    }

                    Rectangle {
                        visible: root.surface && root.surface.isPdfPanel
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 12
                        width: 12
                        height: 6
                        radius: 2
                        color: Qt.alpha(root.surface ? root.surface.pdfBadgeFillColor : "#2C85BF", 0.92)
                    }
                }

                Text {
                    objectName: "graphNodeMediaProxyPreviewTitle"
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    color: root.surface ? root.surface.captionTextColor : "#f0f2f5"
                    font.pixelSize: 12
                    font.bold: true
                    text: root.surface && root.surface.isPdfPanel ? "PDF proxy preview" : "Image proxy preview"
                    renderType: root.surface && root.surface.host
                        ? root.surface.host.nodeTextRenderType
                        : Text.CurveRendering
                }

                Text {
                    objectName: "graphNodeMediaProxyPreviewDetail"
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    color: root.surface ? root.surface.hintTextColor : "#bdc5d3"
                    font.pixelSize: 11
                    text: root.surface && root.surface.isPdfPanel && root.surface.pdfPageCount > 0
                        ? "Page " + root.surface.pdfResolvedPageNumber + " of " + root.surface.pdfPageCount
                            + " paused during max performance interaction."
                        : "Full preview returns automatically after the interaction settles."
                    renderType: root.surface && root.surface.host
                        ? root.surface.host.nodeTextRenderType
                        : Text.CurveRendering
                }
            }
        }

        GraphMediaPanelPreviewPlaceholder {
            surface: root.surface
        }

        Item {
            id: overlayLayer
            anchors.fill: parent
            z: 3
        }

        GraphSurfaceControls.GraphSurfaceTextareaEditor {
            id: inlineCaptionEditor
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 8
            z: 4
            visible: root.surface ? root.surface.inlineEditorsVisible : false
            enabled: visible
            host: root.surface ? root.surface.host : null
            propertyKey: "caption"
            committedText: root.surface ? root.surface.captionText : ""
            fieldObjectName: "graphNodeInlineTextareaEditor"
            applyButtonObjectName: "graphNodeInlineTextareaApplyButton"
            resetButtonObjectName: "graphNodeInlineTextareaResetButton"
            onControlStarted: root.surface._beginInlineInteraction()
            onCommitRequested: function(value) {
                root.surface._commitInlineProperty("caption", value);
            }
        }
    }
}
