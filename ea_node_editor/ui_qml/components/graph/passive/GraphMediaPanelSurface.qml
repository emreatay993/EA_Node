import QtQuick 2.15
import QtQuick.Controls 2.15
import "../surface_controls" as GraphSurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry
import "GraphMediaPanelGeometry.js" as GraphMediaPanelGeometry
import "GraphMediaPanelSourceUtils.js" as GraphMediaPanelSourceUtils

Item {
    id: surface
    objectName: "graphNodeMediaSurface"
    property Item host: null
    property bool cropModeActive: false
    property bool inlineEditorsOpened: false
    property real draftCropX: 0.0
    property real draftCropY: 0.0
    property real draftCropW: 1.0
    property real draftCropH: 1.0
    property string hoveredCropHandle: ""
    property string activeCropHandle: ""
    readonly property bool blocksHostInteraction: cropModeActive
    readonly property var nodeProperties: host && host.nodeData && host.nodeData.properties
        ? host.nodeData.properties
        : ({})
    readonly property string mediaVariant: host ? String(host.surfaceVariant || "") : ""
    readonly property var renderQuality: host && host.renderQuality
        ? host.renderQuality
        : ({
            "weight_class": "standard",
            "max_performance_strategy": "generic_fallback",
            "supported_quality_tiers": ["full"]
        })
    readonly property string requestedQualityTier: host ? String(host.requestedQualityTier || "full") : "full"
    readonly property string resolvedQualityTier: host ? String(host.resolvedQualityTier || "full") : "full"
    readonly property bool proxySurfaceRequested: host ? Boolean(host.proxySurfaceRequested) : false
    readonly property bool isPdfPanel: mediaVariant === "pdf_panel"
    readonly property string sourcePath: _value("source_path")
    readonly property var rawPageNumber: _rawValue("page_number", 1)
    readonly property string captionText: _value("caption")
    readonly property string normalizedFitMode: _normalizedFitMode()
    readonly property bool captionVisible: captionText.length > 0
    readonly property var pdfPreviewInfo: isPdfPanel ? _describePdfPreview(sourcePath, rawPageNumber) : ({})
    readonly property string resolvedSourceUrl: isPdfPanel
        ? String(pdfPreviewInfo.resolved_source_url || "")
        : GraphMediaPanelSourceUtils.resolvedLocalSourceUrl(sourcePath)
    readonly property string previewSourceUrl: isPdfPanel
        ? String(pdfPreviewInfo.preview_url || "")
        : GraphMediaPanelSourceUtils.previewSourceUrl(resolvedSourceUrl)
    readonly property int pdfPageCount: isPdfPanel ? Number(pdfPreviewInfo.page_count || 0) : 0
    readonly property int pdfRequestedPageNumber: isPdfPanel ? Number(pdfPreviewInfo.requested_page_number || 1) : 1
    readonly property int pdfResolvedPageNumber: isPdfPanel ? Number(pdfPreviewInfo.resolved_page_number || 1) : 1
    readonly property string pdfPreviewMessage: isPdfPanel ? String(pdfPreviewInfo.message || "") : ""
    readonly property bool sourceRejected: sourcePath.trim().length > 0 && resolvedSourceUrl.length === 0
    readonly property bool fileIssueActive: sourcePath.trim().length > 0 && previewState === "error"
    readonly property string fileIssueMessage: {
        if (!fileIssueActive)
            return "";
        if (isPdfPanel)
            return pdfPreviewMessage.length > 0
                ? pdfPreviewMessage
                : "The PDF source is missing or can no longer be loaded.";
        return sourceRejected
            ? "The image source is missing or can no longer be loaded."
            : "The image preview could not be loaded from the current source.";
    }
    readonly property string previewState: {
        if (isPdfPanel) {
            var state = String(pdfPreviewInfo.state || "placeholder");
            if (state === "error")
                return "error";
            if (state === "ready") {
                if (proxySurfaceRequested)
                    return "ready";
                if (previewViewport.previewImageStatus === Image.Ready)
                    return "ready";
            }
            if (!proxySurfaceRequested && previewViewport.previewImageStatus === Image.Error)
                return "error";
            return "placeholder";
        }
        if (sourcePath.trim().length === 0)
            return "placeholder";
        if (sourceRejected)
            return "error";
        if (previewViewport.previewImageStatus === Image.Error)
            return "error";
        if (previewViewport.previewImageStatus === Image.Ready)
            return "ready";
        return "placeholder";
    }
    readonly property bool proxySurfaceActive: proxySurfaceRequested
        && previewState === "ready"
        && !cropModeActive
    readonly property string appliedFitMode: isPdfPanel ? "contain" : normalizedFitMode
    readonly property bool originalModeActive: !isPdfPanel && normalizedFitMode === "original"
    readonly property real sourcePixelWidth: Number(previewViewport.sourcePixelWidth || 0)
    readonly property real sourcePixelHeight: Number(previewViewport.sourcePixelHeight || 0)
    readonly property var normalizedStoredCropRect: _normalizedStoredCropRect()
    readonly property bool hasEffectiveCrop: !GraphMediaPanelGeometry.isFullCropRect(normalizedStoredCropRect)
    readonly property rect appliedSourceClipRect: _sourceClipRectFromNormalized(normalizedStoredCropRect)
    readonly property real appliedClipX: Number(appliedSourceClipRect.x || 0)
    readonly property real appliedClipY: Number(appliedSourceClipRect.y || 0)
    readonly property real appliedClipWidth: Number(appliedSourceClipRect.width || 0)
    readonly property real appliedClipHeight: Number(appliedSourceClipRect.height || 0)
    readonly property bool cropToolAvailable: !isPdfPanel
        && !proxySurfaceActive
        && previewState === "ready"
        && sourcePixelWidth > 0
        && sourcePixelHeight > 0
    readonly property bool cropButtonVisible: cropToolAvailable
        && !cropModeActive
        && (host ? host.hoverActive : false)
    readonly property bool inlineEditorsVisible: !!(host && host.isSelected) && inlineEditorsOpened && !cropModeActive
    readonly property var cropDisplayRect: previewViewport.cropDisplayRect
    readonly property var draftDisplayCropRect: previewViewport.draftDisplayCropRect
    readonly property real effectivePreviewSourceWidth: Number(previewViewport.effectivePreviewSourceWidth || 0)
    readonly property real effectivePreviewSourceHeight: Number(previewViewport.effectivePreviewSourceHeight || 0)
    readonly property var appliedPreviewRect: previewViewport.appliedPreviewRect
    readonly property real appliedPreviewScale: Number(previewViewport.appliedPreviewScale || 0)
    readonly property real appliedFullImageWidth: Number(previewViewport.appliedFullImageWidth || 0)
    readonly property real appliedFullImageHeight: Number(previewViewport.appliedFullImageHeight || 0)
    readonly property real appliedImageOffsetX: Number(previewViewport.appliedImageOffsetX || 0)
    readonly property real appliedImageOffsetY: Number(previewViewport.appliedImageOffsetY || 0)
    readonly property string previewHintText: {
        if (isPdfPanel) {
            if (previewState === "error")
                return pdfPreviewMessage.length > 0
                    ? pdfPreviewMessage
                    : "Unable to load the current PDF preview. Use Repair file... to relink it.";
            return "Choose a local PDF file to preview it here.";
        }
        return previewState === "error"
            ? "Unable to load the current image preview. Use Repair file... to relink it."
            : "Choose a local image file to preview it here.";
    }
    readonly property color panelFillColor: host && host.hasPassiveFillOverride
        ? host.surfaceColor
        : Qt.darker(host ? host.surfaceColor : "#1b1d22", 1.03)
    readonly property color panelBorderColor: host && host.isSelected
        ? host.themeSelectedOutlineColor
        : (host && host.hasPassiveBorderOverride
            ? host.outlineColor
            : (host ? Qt.lighter(host.outlineColor, 1.1) : "#4a4f5a"))
    readonly property color viewportFillColor: host
        ? Qt.darker(host.inlineInputBackgroundColor, 1.02)
        : "#202228"
    readonly property color hintTextColor: host ? host.inlineDrivenTextColor : "#bdc5d3"
    readonly property color captionTextColor: host ? host.inlineInputTextColor : "#f0f2f5"
    readonly property color pdfBadgeFillColor: host ? Qt.alpha(host.scopeBadgeColor, 0.92) : "#2C85BF"
    readonly property color pdfBadgeBorderColor: host ? Qt.alpha(host.scopeBadgeBorderColor, 0.96) : "#7FC7FF"
    readonly property color pdfBadgeTextColor: host ? host.scopeBadgeTextColor : "#F4F8FC"
    readonly property color cropOverlayShadeColor: Qt.alpha("#11151A", 0.44)
    readonly property color cropFrameColor: host ? host.selectedOutlineColor : "#60CDFF"
    readonly property color cropHandleFillColor: host ? host.surfaceColor : "#1b1d22"
    readonly property color cropHandleBorderColor: host ? host.selectedOutlineColor : "#60CDFF"
    readonly property color cropButtonIconColor: host ? host.headerTextColor : "#f0f2f5"
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists(
        [
            headerControls.embeddedInteractiveRects,
            previewViewport.embeddedInteractiveRects
        ]
    )
    readonly property real cropHandleSize: 12
    readonly property real cropHandleHitSlop: 8
    implicitHeight: host ? Number(host.surfaceMetrics.body_height || 0) : 0

    onCropToolAvailableChanged: {
        if (!cropToolAvailable && cropModeActive) {
            _cancelCropEdit();
            return;
        }
        if (cropToolAvailable)
            _tryConsumePendingSurfaceAction();
        _syncCropCursor();
    }

    onCropModeActiveChanged: _syncCropCursor()
    onHoveredCropHandleChanged: _syncCropCursor()
    onActiveCropHandleChanged: _syncCropCursor()

    onSourcePathChanged: {
        if (cropModeActive)
            _cancelCropEdit();
        _syncCropCursor();
    }

    Component.onCompleted: {
        _tryConsumePendingSurfaceAction();
        _syncCropCursor();
    }

    Component.onDestruction: _clearGraphCursorShape()

    Connections {
        target: host

        function onIsSelectedChanged() {
            if (host && host.isSelected) {
                surface._tryConsumePendingSurfaceAction();
            } else {
                surface.inlineEditorsOpened = false;
            }
        }

        function onNodeOpenRequested(nodeId) {
            if (!host || !host.nodeData)
                return;
            if (String(nodeId || "") !== String(host.nodeData.node_id || ""))
                return;
            surface.inlineEditorsOpened = !surface.inlineEditorsOpened;
        }
    }

    function _tryConsumePendingSurfaceAction() {
        if (!cropToolAvailable || cropModeActive)
            return;
        var nodeId = host && host.nodeData ? String(host.nodeData.node_id || "") : "";
        var canvasItem = _canvasItem();
        if (nodeId.length > 0
                && canvasItem
                && canvasItem.consumePendingNodeSurfaceAction
                && canvasItem.consumePendingNodeSurfaceAction(nodeId)) {
            _loadDraftFromStoredCrop();
            cropModeActive = true;
        }
    }

    function _canvasItem() {
        return host && host.canvasItem ? host.canvasItem : null;
    }

    function _rawValue(key, fallback) {
        var value = nodeProperties[key];
        return value === undefined || value === null ? fallback : value;
    }

    function _value(key) {
        var value = nodeProperties[key];
        if (value === undefined || value === null)
            return "";
        return String(value);
    }

    function _beginInlineInteraction() {
        if (host && host.nodeData)
            host.surfaceControlInteractionStarted(String(host.nodeData.node_id || ""));
    }

    function _commitInlineProperty(key, value) {
        if (host && host.nodeData)
            host.inlinePropertyCommitted(String(host.nodeData.node_id || ""), key, value);
    }

    function _browseInlinePropertyPath(key, currentPath) {
        if (!host || !host.browseNodePropertyPath)
            return "";
        return String(host.browseNodePropertyPath(key, currentPath) || "");
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

    function _numberValue(key, fallback) {
        var numeric = Number(_rawValue(key, fallback));
        return isFinite(numeric) ? numeric : fallback;
    }

    function _normalizedFitMode() {
        var value = _value("fit_mode").trim().toLowerCase();
        if (value === "cover" || value === "original")
            return value;
        return "contain";
    }

    function _normalizedStoredCropRect() {
        return GraphMediaPanelGeometry.normalizedCropRect(
            _numberValue("crop_x", 0.0),
            _numberValue("crop_y", 0.0),
            _numberValue("crop_w", 1.0),
            _numberValue("crop_h", 1.0)
        );
    }

    function _sourceClipRectFromNormalized(rect) {
        return GraphMediaPanelGeometry.sourceClipRectFromNormalized(
            rect,
            sourcePixelWidth,
            sourcePixelHeight
        );
    }

    function _iconSource(name, size, color) {
        if (typeof uiIcons === "undefined" || !uiIcons || !uiIcons.has(name))
            return "";
        return uiIcons.sourceSized(name, size, color);
    }

    function _setDraftCropRect(rect) {
        draftCropX = Number(rect.x || 0);
        draftCropY = Number(rect.y || 0);
        draftCropW = Number(rect.width || 1);
        draftCropH = Number(rect.height || 1);
    }

    function _setGraphCursorShape(cursorShape) {
        var canvasItem = _canvasItem();
        if (!canvasItem || !canvasItem.setNodeSurfaceCursorShape)
            return false;
        return Boolean(canvasItem.setNodeSurfaceCursorShape(cursorShape));
    }

    function _clearGraphCursorShape() {
        var canvasItem = _canvasItem();
        if (!canvasItem || !canvasItem.clearNodeSurfaceCursorShape)
            return false;
        return Boolean(canvasItem.clearNodeSurfaceCursorShape());
    }

    function _loadDraftFromStoredCrop() {
        _setDraftCropRect(normalizedStoredCropRect);
    }

    function _beginCropEdit() {
        if (!cropToolAvailable)
            return;
        var nodeId = host && host.nodeData ? String(host.nodeData.node_id || "") : "";
        var canvasItem = _canvasItem();
        if (canvasItem && canvasItem.requestNodeSurfaceCropEdit && nodeId.length > 0) {
            if (!canvasItem.requestNodeSurfaceCropEdit(nodeId))
                return;
        } else if (host && !host.isSelected) {
            return;
        }
        _loadDraftFromStoredCrop();
        cropModeActive = true;
    }

    function _cancelCropEdit() {
        cropModeActive = false;
        hoveredCropHandle = "";
        activeCropHandle = "";
        _loadDraftFromStoredCrop();
    }

    function _applyCropEdit() {
        var rect = GraphMediaPanelGeometry.normalizedCropRect(
            draftCropX,
            draftCropY,
            draftCropW,
            draftCropH
        );
        var canvasItem = _canvasItem();
        if (canvasItem && canvasItem.commitNodeSurfaceProperties && host && host.nodeData) {
            var applied = canvasItem.commitNodeSurfaceProperties(
                String(host.nodeData.node_id || ""),
                {
                    "crop_x": rect.x,
                    "crop_y": rect.y,
                    "crop_w": rect.width,
                    "crop_h": rect.height
                }
            );
            if (!applied && !GraphMediaPanelGeometry.cropRectsEqual(rect, normalizedStoredCropRect))
                return;
        }
        cropModeActive = false;
        hoveredCropHandle = "";
        activeCropHandle = "";
        _setDraftCropRect(rect);
    }

    function triggerHoverAction() {
        _beginCropEdit();
    }

    function _updateDraftFromHandle(handle, deltaPixelsX, deltaPixelsY, startX, startY, startW, startH) {
        _setDraftCropRect(
            GraphMediaPanelGeometry.updatedDraftCropRect(
                handle,
                deltaPixelsX,
                deltaPixelsY,
                startX,
                startY,
                startW,
                startH,
                cropDisplayRect,
                sourcePixelWidth,
                sourcePixelHeight
            )
        );
    }

    function _handleCursorShape(handle) {
        return GraphMediaPanelGeometry.handleCursorShape(handle);
    }

    function _resolvedCropCursorShape() {
        var handle = activeCropHandle.length > 0 ? activeCropHandle : hoveredCropHandle;
        if (handle.length > 0)
            return _handleCursorShape(handle);
        return Qt.ArrowCursor;
    }

    function _syncCropCursor() {
        if (!cropModeActive || !cropToolAvailable) {
            _clearGraphCursorShape();
            return;
        }
        _setGraphCursorShape(_resolvedCropCursorShape());
    }

    function _handleX(handle, frameRect, handleSize) {
        return GraphMediaPanelGeometry.handleX(handle, frameRect, handleSize);
    }

    function _handleY(handle, frameRect, handleSize) {
        return GraphMediaPanelGeometry.handleY(handle, frameRect, handleSize);
    }

    function _describePdfPreview(source, pageNumber) {
        var canvasItem = _canvasItem();
        if (canvasItem && canvasItem.describeNodeSurfacePdfPreview) {
            try {
                return canvasItem.describeNodeSurfacePdfPreview(String(source || ""), pageNumber);
            } catch (error) {
            }
        }
        if (String(source || "").trim().length === 0) {
            return {
                "state": "placeholder",
                "message": "Choose a local PDF file to preview it here.",
                "resolved_source_url": "",
                "preview_url": "",
                "page_count": 0,
                "requested_page_number": 1,
                "resolved_page_number": 1,
                "file_stamp_token": ""
            };
        }
        return {
            "state": "error",
            "message": "PDF preview service unavailable.",
            "resolved_source_url": "",
            "preview_url": "",
            "page_count": 0,
            "requested_page_number": Number(pageNumber || 1),
            "resolved_page_number": Number(pageNumber || 1),
            "file_stamp_token": ""
        };
    }

    Rectangle {
        anchors.fill: parent
        radius: host ? Number(host.resolvedCornerRadius || 6) : 6
        color: surface.panelFillColor
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: surface.panelBorderColor
    }

    GraphMediaPanelHeaderControls {
        id: headerControls
        surface: surface
        anchors.fill: parent
    }

    Column {
        anchors.left: parent.left
        anchors.leftMargin: host ? Number(host.surfaceMetrics.body_left_margin || 14) : 14
        anchors.right: parent.right
        anchors.rightMargin: host ? Number(host.surfaceMetrics.body_right_margin || 14) : 14
        anchors.top: parent.top
        anchors.topMargin: host ? Number(host.surfaceMetrics.body_top || 44) : 44
        anchors.bottom: parent.bottom
        anchors.bottomMargin: host ? Number(host.surfaceMetrics.body_bottom_margin || 12) : 12
        spacing: surface.captionVisible ? 10 : 0

        GraphMediaPanelPreviewViewport {
            id: previewViewport
            width: parent.width
            height: surface.captionVisible
                ? Math.max(64, parent.height - captionBlock.implicitHeight - parent.spacing)
                : parent.height
            surface: surface
            overlayInteractiveRects: cropOverlay.embeddedInteractiveRects

            overlayData: [
                Item {
                    id: cropOverlay
                    objectName: "graphNodeMediaCropOverlay"
                    property var handleEmbeddedInteractiveRects: {
                        var frameWidth = Number(surface.draftDisplayCropRect.width || 0);
                        var frameHeight = Number(surface.draftDisplayCropRect.height || 0);
                        if (!(surface.cropModeActive && surface.cropToolAvailable)
                                || !(frameWidth > 0)
                                || !(frameHeight > 0)) {
                            return [];
                        }
                        var rectLists = [];
                        for (var index = 0; index < cropHandleRepeater.count; index++) {
                            var handleItem = cropHandleRepeater.itemAt(index);
                            if (!handleItem || handleItem.embeddedInteractiveRects === undefined || handleItem.embeddedInteractiveRects === null)
                                continue;
                            rectLists.push(handleItem.embeddedInteractiveRects);
                        }
                        return SurfaceControlGeometry.combineRectLists(rectLists);
                    }
                    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.combineRectLists(
                        [
                            cropApplyButton.embeddedInteractiveRects,
                            cropCancelButton.embeddedInteractiveRects,
                            cropOverlay.handleEmbeddedInteractiveRects
                        ]
                    )
                    anchors.fill: parent
                    visible: surface.cropModeActive && surface.cropToolAvailable
                    z: 3

                    HoverHandler {
                        id: cropCursorArea
                        objectName: "graphNodeMediaCropCursorArea"
                        cursorShape: surface._resolvedCropCursorShape()
                    }

                    Image {
                        id: cropEditImage
                        objectName: "graphNodeMediaCropEditImage"
                        x: Number(surface.cropDisplayRect.x || 0)
                        y: Number(surface.cropDisplayRect.y || 0)
                        width: Number(surface.cropDisplayRect.width || 0)
                        height: Number(surface.cropDisplayRect.height || 0)
                        asynchronous: false
                        cache: true
                        mipmap: true
                        fillMode: Image.PreserveAspectFit
                        source: surface.previewSourceUrl
                        visible: parent.visible
                        smooth: true
                    }

                    Rectangle {
                        color: surface.cropOverlayShadeColor
                        x: 0
                        y: 0
                        width: parent.width
                        height: Number(surface.draftDisplayCropRect.y || 0)
                    }

                    Rectangle {
                        color: surface.cropOverlayShadeColor
                        x: 0
                        y: Number(surface.draftDisplayCropRect.y || 0)
                            + Number(surface.draftDisplayCropRect.height || 0)
                        width: parent.width
                        height: Math.max(0, parent.height - y)
                    }

                    Rectangle {
                        color: surface.cropOverlayShadeColor
                        x: 0
                        y: Number(surface.draftDisplayCropRect.y || 0)
                        width: Number(surface.draftDisplayCropRect.x || 0)
                        height: Number(surface.draftDisplayCropRect.height || 0)
                    }

                    Rectangle {
                        color: surface.cropOverlayShadeColor
                        x: Number(surface.draftDisplayCropRect.x || 0)
                            + Number(surface.draftDisplayCropRect.width || 0)
                        y: Number(surface.draftDisplayCropRect.y || 0)
                        width: Math.max(0, parent.width - x)
                        height: Number(surface.draftDisplayCropRect.height || 0)
                    }

                    Rectangle {
                        id: cropFrame
                        objectName: "graphNodeMediaCropFrame"
                        x: Number(surface.draftDisplayCropRect.x || 0)
                        y: Number(surface.draftDisplayCropRect.y || 0)
                        width: Number(surface.draftDisplayCropRect.width || 0)
                        height: Number(surface.draftDisplayCropRect.height || 0)
                        color: "transparent"
                        border.width: 2
                        border.color: surface.cropFrameColor
                    }

                    Repeater {
                        id: cropHandleRepeater
                        model: [
                            "top_left",
                            "top",
                            "top_right",
                            "left",
                            "right",
                            "bottom_left",
                            "bottom",
                            "bottom_right"
                        ]

                        delegate: Rectangle {
                            objectName: "graphNodeMediaCropHandle"
                            property string handleId: String(modelData || "")
                            property real pressGlobalX: 0
                            property real pressGlobalY: 0
                            property real startCropX: 0
                            property real startCropY: 0
                            property real startCropW: 1
                            property real startCropH: 1
                            readonly property var embeddedInteractiveRects: handleInteractiveRegion.embeddedInteractiveRects
                            width: surface.cropHandleSize
                            height: surface.cropHandleSize
                            radius: 3
                            z: 4
                            visible: surface.cropModeActive && surface.cropToolAvailable
                            color: surface.cropHandleFillColor
                            border.width: 2
                            border.color: surface.cropHandleBorderColor
                            x: surface._handleX(handleId, surface.draftDisplayCropRect, width)
                            y: surface._handleY(handleId, surface.draftDisplayCropRect, height)

                            GraphSurfaceControls.GraphSurfaceInteractiveRegion {
                                id: handleInteractiveRegion
                                host: surface.host
                                targetItem: handleMouseArea
                                enabled: parent.visible
                                onControlStarted: surface._beginInlineInteraction()
                            }

                            MouseArea {
                                id: handleMouseArea
                                objectName: "graphNodeMediaCropHandleMouseArea"
                                property string handleId: parent.handleId
                                x: -surface.cropHandleHitSlop
                                y: -surface.cropHandleHitSlop
                                width: parent.width + surface.cropHandleHitSlop * 2
                                height: parent.height + surface.cropHandleHitSlop * 2
                                acceptedButtons: Qt.LeftButton
                                cursorShape: surface._handleCursorShape(handleId)
                                hoverEnabled: true
                                preventStealing: true

                                onEntered: {
                                    surface.hoveredCropHandle = handleId;
                                }

                                onExited: {
                                    if (surface.hoveredCropHandle === handleId)
                                        surface.hoveredCropHandle = "";
                                }

                                onPressed: function(mouse) {
                                    handleInteractiveRegion.beginControl();
                                    surface.activeCropHandle = handleId;
                                    surface.hoveredCropHandle = handleId;
                                    var gp = mapToGlobal(mouse.x, mouse.y);
                                    parent.pressGlobalX = gp.x;
                                    parent.pressGlobalY = gp.y;
                                    parent.startCropX = surface.draftCropX;
                                    parent.startCropY = surface.draftCropY;
                                    parent.startCropW = surface.draftCropW;
                                    parent.startCropH = surface.draftCropH;
                                    mouse.accepted = true;
                                }

                                onPositionChanged: function(mouse) {
                                    if (!pressed)
                                        return;
                                    var gp = mapToGlobal(mouse.x, mouse.y);
                                    surface._updateDraftFromHandle(
                                        handleId,
                                        gp.x - parent.pressGlobalX,
                                        gp.y - parent.pressGlobalY,
                                        parent.startCropX,
                                        parent.startCropY,
                                        parent.startCropW,
                                        parent.startCropH
                                    );
                                }

                                onReleased: function(_mouse) {
                                    if (surface.activeCropHandle === handleId)
                                        surface.activeCropHandle = "";
                                }

                                onCanceled: {
                                    if (surface.activeCropHandle === handleId)
                                        surface.activeCropHandle = "";
                                }
                            }
                        }
                    }

                    Row {
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.topMargin: 8
                        anchors.rightMargin: 8
                        spacing: 6
                        z: 5

                        GraphSurfaceControls.GraphSurfaceButton {
                            id: cropApplyButton
                            objectName: "graphNodeMediaCropApplyButton"
                            host: surface.host
                            visible: surface.cropModeActive && surface.cropToolAvailable
                            enabled: visible
                            text: "Apply"
                            foregroundColor: surface.cropButtonIconColor
                            baseFillColor: Qt.alpha(surface.panelFillColor, 0.82)
                            baseBorderColor: Qt.alpha(surface.panelBorderColor, 0.82)
                            onControlStarted: surface._beginInlineInteraction()
                            onClicked: surface._applyCropEdit()
                        }

                        GraphSurfaceControls.GraphSurfaceButton {
                            id: cropCancelButton
                            objectName: "graphNodeMediaCropCancelButton"
                            host: surface.host
                            visible: surface.cropModeActive && surface.cropToolAvailable
                            enabled: visible
                            text: "Cancel"
                            foregroundColor: surface.cropButtonIconColor
                            baseFillColor: Qt.alpha(surface.panelFillColor, 0.82)
                            baseBorderColor: Qt.alpha(surface.panelBorderColor, 0.82)
                            onControlStarted: surface._beginInlineInteraction()
                            onClicked: surface._cancelCropEdit()
                        }
                    }
                }
            ]
        }

        Text {
            id: captionBlock
            objectName: "graphNodeMediaCaption"
            property int effectiveRenderType: renderType
            visible: surface.captionVisible && !surface.inlineEditorsVisible
            width: parent.width
            text: surface.captionText
            color: surface.captionTextColor
            font.pixelSize: host ? Number(host.passiveFontPixelSize || 12) : 12
            font.bold: host ? Boolean(host.passiveFontBold) : false
            wrapMode: Text.WordWrap
            maximumLineCount: 4
            elide: Text.ElideRight
            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
        }
    }
}
