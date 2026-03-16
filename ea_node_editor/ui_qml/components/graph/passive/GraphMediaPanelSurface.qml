import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: surface
    objectName: "graphNodeMediaSurface"
    property Item host: null
    property bool cropModeActive: false
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
    readonly property bool isPdfPanel: mediaVariant === "pdf_panel"
    readonly property string sourcePath: _value("source_path")
    readonly property var rawPageNumber: _rawValue("page_number", 1)
    readonly property string captionText: _value("caption")
    readonly property string normalizedFitMode: _normalizedFitMode()
    readonly property bool captionVisible: captionText.length > 0
    readonly property var pdfPreviewInfo: isPdfPanel ? _describePdfPreview(sourcePath, rawPageNumber) : ({})
    readonly property string resolvedSourceUrl: isPdfPanel
        ? String(pdfPreviewInfo.resolved_source_url || "")
        : _resolvedLocalSourceUrl(sourcePath)
    readonly property string previewSourceUrl: isPdfPanel
        ? String(pdfPreviewInfo.preview_url || "")
        : _previewSourceUrl(resolvedSourceUrl)
    readonly property int pdfPageCount: isPdfPanel ? Number(pdfPreviewInfo.page_count || 0) : 0
    readonly property int pdfRequestedPageNumber: isPdfPanel ? Number(pdfPreviewInfo.requested_page_number || 1) : 1
    readonly property int pdfResolvedPageNumber: isPdfPanel ? Number(pdfPreviewInfo.resolved_page_number || 1) : 1
    readonly property string pdfPreviewMessage: isPdfPanel ? String(pdfPreviewInfo.message || "") : ""
    readonly property bool sourceRejected: sourcePath.trim().length > 0 && resolvedSourceUrl.length === 0
    readonly property string previewState: {
        if (isPdfPanel) {
            var state = String(pdfPreviewInfo.state || "placeholder");
            if (state === "error")
                return "error";
            if (state === "ready" && previewImage.status === Image.Ready)
                return "ready";
            if (previewImage.status === Image.Error)
                return "error";
            return "placeholder";
        }
        if (sourcePath.trim().length === 0)
            return "placeholder";
        if (sourceRejected)
            return "error";
        if (previewImage.status === Image.Error)
            return "error";
        if (previewImage.status === Image.Ready)
            return "ready";
        return "placeholder";
    }
    readonly property string appliedFitMode: isPdfPanel ? "contain" : normalizedFitMode
    readonly property bool originalModeActive: !isPdfPanel && normalizedFitMode === "original"
    readonly property real sourcePixelWidth: !isPdfPanel && sourceImageProbe.status === Image.Ready
        ? Number(sourceImageProbe.implicitWidth || 0)
        : 0
    readonly property real sourcePixelHeight: !isPdfPanel && sourceImageProbe.status === Image.Ready
        ? Number(sourceImageProbe.implicitHeight || 0)
        : 0
    readonly property var normalizedStoredCropRect: _normalizedStoredCropRect()
    readonly property bool hasEffectiveCrop: !_isFullCropRect(normalizedStoredCropRect)
    readonly property rect appliedSourceClipRect: _sourceClipRectFromNormalized(normalizedStoredCropRect)
    readonly property real appliedClipX: Number(appliedSourceClipRect.x || 0)
    readonly property real appliedClipY: Number(appliedSourceClipRect.y || 0)
    readonly property real appliedClipWidth: Number(appliedSourceClipRect.width || 0)
    readonly property real appliedClipHeight: Number(appliedSourceClipRect.height || 0)
    readonly property bool cropToolAvailable: !isPdfPanel
        && previewState === "ready"
        && sourcePixelWidth > 0
        && sourcePixelHeight > 0
    readonly property bool cropButtonVisible: cropToolAvailable
        && !cropModeActive
        && (host ? host.hoverActive : false)
    readonly property rect hoverActionHitRect: cropButton.visible
        ? Qt.rect(cropButton.x, cropButton.y, cropButton.width, cropButton.height)
        : Qt.rect(0, 0, 0, 0)
    readonly property real cropHandleSize: 12
    readonly property real cropHandleHitSlop: 8
    readonly property var cropDisplayRect: _containRect(
        previewViewport.width,
        previewViewport.height,
        sourcePixelWidth,
        sourcePixelHeight
    )
    readonly property var draftDisplayCropRect: _displayCropRect(
        draftCropX,
        draftCropY,
        draftCropW,
        draftCropH,
        cropDisplayRect
    )
    readonly property real effectivePreviewSourceWidth: sourcePixelWidth > 0
        ? sourcePixelWidth * Number(normalizedStoredCropRect.width || 0)
        : 0
    readonly property real effectivePreviewSourceHeight: sourcePixelHeight > 0
        ? sourcePixelHeight * Number(normalizedStoredCropRect.height || 0)
        : 0
    readonly property var appliedPreviewRect: _fitRect(
        previewViewport.width,
        previewViewport.height,
        effectivePreviewSourceWidth,
        effectivePreviewSourceHeight,
        appliedFitMode
    )
    readonly property real appliedPreviewScale: {
        if (!(effectivePreviewSourceWidth > 0) || !(effectivePreviewSourceHeight > 0))
            return 0.0;
        if (appliedFitMode === "original")
            return 1.0;
        return Number(appliedPreviewRect.width || 0) / effectivePreviewSourceWidth;
    }
    readonly property real appliedFullImageWidth: sourcePixelWidth > 0
        ? sourcePixelWidth * appliedPreviewScale
        : 0
    readonly property real appliedFullImageHeight: sourcePixelHeight > 0
        ? sourcePixelHeight * appliedPreviewScale
        : 0
    readonly property real appliedImageOffsetX: -Number(normalizedStoredCropRect.x || 0) * appliedFullImageWidth
    readonly property real appliedImageOffsetY: -Number(normalizedStoredCropRect.y || 0) * appliedFullImageHeight
    readonly property string previewHintText: {
        if (isPdfPanel) {
            if (previewState === "error")
                return pdfPreviewMessage.length > 0 ? pdfPreviewMessage : "Unable to load a local PDF preview.";
            return "Choose a local PDF file to preview it here.";
        }
        return previewState === "error"
            ? "Unable to load a local image preview."
            : "Choose a local image file to preview it here.";
    }
    readonly property color panelFillColor: host && host.hasPassiveFillOverride
        ? host.surfaceColor
        : Qt.darker(host ? host.surfaceColor : "#1b1d22", 1.03)
    readonly property color panelBorderColor: host && host.isSelected
        ? host.selectedOutlineColor
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

    Component.onDestruction: {
        if (typeof mainWindow !== "undefined" && mainWindow)
            mainWindow.clear_graph_cursor_shape();
    }

    Connections {
        target: host

        function onIsSelectedChanged() {
            if (host && host.isSelected)
                surface._tryConsumePendingSurfaceAction();
        }
    }

    function _tryConsumePendingSurfaceAction() {
        if (!cropToolAvailable || cropModeActive)
            return;
        var nodeId = host && host.nodeData ? String(host.nodeData.node_id || "") : "";
        if (nodeId.length > 0 && typeof sceneBridge !== "undefined" && sceneBridge) {
            if (sceneBridge.consume_pending_surface_action(nodeId)) {
                _loadDraftFromStoredCrop();
                cropModeActive = true;
            }
        }
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

    function _clamp(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value));
    }

    function _approxEqual(a, b) {
        return Math.abs(Number(a) - Number(b)) <= 0.0001;
    }

    function _minimumCropWidth() {
        return sourcePixelWidth > 0 ? (1.0 / sourcePixelWidth) : 0.001;
    }

    function _minimumCropHeight() {
        return sourcePixelHeight > 0 ? (1.0 / sourcePixelHeight) : 0.001;
    }

    function _fullCropRect() {
        return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0};
    }

    function _normalizedCropRect(x, y, w, h) {
        var left = Number(x);
        var top = Number(y);
        var widthValue = Number(w);
        var heightValue = Number(h);
        if (!isFinite(left) || !isFinite(top) || !isFinite(widthValue) || !isFinite(heightValue))
            return _fullCropRect();
        if (!(widthValue > 0.0) || !(heightValue > 0.0))
            return _fullCropRect();
        left = _clamp(left, 0.0, 1.0);
        top = _clamp(top, 0.0, 1.0);
        var right = _clamp(left + widthValue, left, 1.0);
        var bottom = _clamp(top + heightValue, top, 1.0);
        if (!(right > left) || !(bottom > top))
            return _fullCropRect();
        return {
            "x": left,
            "y": top,
            "width": right - left,
            "height": bottom - top
        };
    }

    function _normalizedStoredCropRect() {
        return _normalizedCropRect(
            _numberValue("crop_x", 0.0),
            _numberValue("crop_y", 0.0),
            _numberValue("crop_w", 1.0),
            _numberValue("crop_h", 1.0)
        );
    }

    function _isFullCropRect(rect) {
        return _approxEqual(rect.x, 0.0)
            && _approxEqual(rect.y, 0.0)
            && _approxEqual(rect.width, 1.0)
            && _approxEqual(rect.height, 1.0);
    }

    function _cropRectsEqual(a, b) {
        return _approxEqual(Number(a.x || 0), Number(b.x || 0))
            && _approxEqual(Number(a.y || 0), Number(b.y || 0))
            && _approxEqual(Number(a.width || 0), Number(b.width || 0))
            && _approxEqual(Number(a.height || 0), Number(b.height || 0));
    }

    function _sourceClipRectFromNormalized(rect) {
        if (sourcePixelWidth <= 0 || sourcePixelHeight <= 0)
            return Qt.rect(0, 0, 0, 0);
        return Qt.rect(
            rect.x * sourcePixelWidth,
            rect.y * sourcePixelHeight,
            rect.width * sourcePixelWidth,
            rect.height * sourcePixelHeight
        );
    }

    function _fitRect(containerWidth, containerHeight, sourceWidth, sourceHeight, fitMode) {
        var cw = Math.max(0.0, Number(containerWidth || 0));
        var ch = Math.max(0.0, Number(containerHeight || 0));
        var sw = Math.max(0.0, Number(sourceWidth || 0));
        var sh = Math.max(0.0, Number(sourceHeight || 0));
        if (!(cw > 0.0) || !(ch > 0.0) || !(sw > 0.0) || !(sh > 0.0))
            return {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0};
        var normalizedMode = String(fitMode || "contain").trim().toLowerCase();
        if (normalizedMode === "original") {
            return {
                "x": (cw - sw) * 0.5,
                "y": (ch - sh) * 0.5,
                "width": sw,
                "height": sh
            };
        }
        var scale = normalizedMode === "cover"
            ? Math.max(cw / sw, ch / sh)
            : Math.min(cw / sw, ch / sh);
        var widthValue = sw * scale;
        var heightValue = sh * scale;
        return {
            "x": (cw - widthValue) * 0.5,
            "y": (ch - heightValue) * 0.5,
            "width": widthValue,
            "height": heightValue
        };
    }

    function _containRect(containerWidth, containerHeight, sourceWidth, sourceHeight) {
        return _fitRect(containerWidth, containerHeight, sourceWidth, sourceHeight, "contain");
    }

    function _displayCropRect(x, y, w, h, imageRect) {
        var rect = _normalizedCropRect(x, y, w, h);
        var widthValue = Number(imageRect.width || 0);
        var heightValue = Number(imageRect.height || 0);
        return {
            "x": Number(imageRect.x || 0) + rect.x * widthValue,
            "y": Number(imageRect.y || 0) + rect.y * heightValue,
            "width": rect.width * widthValue,
            "height": rect.height * heightValue
        };
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

    function _loadDraftFromStoredCrop() {
        _setDraftCropRect(normalizedStoredCropRect);
    }

    function _beginCropEdit() {
        if (!cropToolAvailable)
            return;
        var nodeId = host && host.nodeData ? String(host.nodeData.node_id || "") : "";
        var needsSelection = nodeId.length > 0
            && host && !host.isSelected;
        if (needsSelection && typeof sceneBridge !== "undefined" && sceneBridge) {
            sceneBridge.set_pending_surface_action(nodeId);
            sceneBridge.select_node(nodeId, false);
            return;
        }
        if (typeof sceneBridge !== "undefined" && sceneBridge && nodeId.length > 0) {
            sceneBridge.select_node(nodeId, false);
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
        var rect = _normalizedCropRect(draftCropX, draftCropY, draftCropW, draftCropH);
        if (typeof sceneBridge !== "undefined" && sceneBridge && host && host.nodeData) {
            var applied = sceneBridge.set_node_properties(
                String(host.nodeData.node_id || ""),
                {
                    "crop_x": rect.x,
                    "crop_y": rect.y,
                    "crop_w": rect.width,
                    "crop_h": rect.height
                }
            );
            if (!applied && !_cropRectsEqual(rect, normalizedStoredCropRect))
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
        var imageWidth = Number(cropDisplayRect.width || 0);
        var imageHeight = Number(cropDisplayRect.height || 0);
        if (!(imageWidth > 0.0) || !(imageHeight > 0.0))
            return;
        var deltaX = deltaPixelsX / imageWidth;
        var deltaY = deltaPixelsY / imageHeight;
        var left = Number(startX);
        var top = Number(startY);
        var right = Number(startX) + Number(startW);
        var bottom = Number(startY) + Number(startH);
        var minWidth = _minimumCropWidth();
        var minHeight = _minimumCropHeight();

        if (handle.indexOf("left") >= 0)
            left = _clamp(left + deltaX, 0.0, right - minWidth);
        if (handle.indexOf("right") >= 0)
            right = _clamp(right + deltaX, left + minWidth, 1.0);
        if (handle.indexOf("top") >= 0)
            top = _clamp(top + deltaY, 0.0, bottom - minHeight);
        if (handle.indexOf("bottom") >= 0)
            bottom = _clamp(bottom + deltaY, top + minHeight, 1.0);

        _setDraftCropRect({
            "x": left,
            "y": top,
            "width": right - left,
            "height": bottom - top
        });
    }

    function _handleCursorShape(handle) {
        if (handle === "top_left" || handle === "bottom_right")
            return Qt.SizeFDiagCursor;
        if (handle === "top_right" || handle === "bottom_left")
            return Qt.SizeBDiagCursor;
        if (handle === "top" || handle === "bottom")
            return Qt.SizeVerCursor;
        return Qt.SizeHorCursor;
    }

    function _resolvedCropCursorShape() {
        var handle = activeCropHandle.length > 0 ? activeCropHandle : hoveredCropHandle;
        if (handle.length > 0)
            return _handleCursorShape(handle);
        return Qt.ArrowCursor;
    }

    function _syncCropCursor() {
        if (typeof mainWindow === "undefined" || !mainWindow)
            return;
        if (!cropModeActive || !cropToolAvailable) {
            mainWindow.clear_graph_cursor_shape();
            return;
        }
        mainWindow.set_graph_cursor_shape(_resolvedCropCursorShape());
    }

    function _handleX(handle, frameRect, handleSize) {
        var half = handleSize * 0.5;
        if (handle === "top_left" || handle === "left" || handle === "bottom_left")
            return frameRect.x - half;
        if (handle === "top_right" || handle === "right" || handle === "bottom_right")
            return frameRect.x + frameRect.width - half;
        return frameRect.x + frameRect.width * 0.5 - half;
    }

    function _handleY(handle, frameRect, handleSize) {
        var half = handleSize * 0.5;
        if (handle === "top_left" || handle === "top" || handle === "top_right")
            return frameRect.y - half;
        if (handle === "bottom_left" || handle === "bottom" || handle === "bottom_right")
            return frameRect.y + frameRect.height - half;
        return frameRect.y + frameRect.height * 0.5 - half;
    }

    function _isWindowsDrivePath(value) {
        return /^[A-Za-z]:[\\/]/.test(value);
    }

    function _isAbsolutePosixPath(value) {
        return value.length > 0 && value.charAt(0) === "/";
    }

    function _isUncPath(value) {
        return /^[/\\]{2}[^/\\]/.test(value);
    }

    function _normalizedFileUrlFromRemainder(remainder) {
        var normalized = String(remainder || "").replace(/\\/g, "/");
        if (!normalized.length)
            return "";
        if (normalized.indexOf("///") === 0)
            return "file://" + encodeURI(normalized.substring(2));
        if (normalized.indexOf("//") === 0)
            return "file://" + encodeURI(normalized.substring(2));
        if (_isWindowsDrivePath(normalized))
            return "file:///" + encodeURI(normalized);
        if (_isUncPath(normalized))
            return "file:" + encodeURI(normalized);
        if (_isAbsolutePosixPath(normalized))
            return "file://" + encodeURI(normalized);
        return "";
    }

    function _resolvedLocalSourceUrl(rawValue) {
        var trimmed = String(rawValue || "").trim();
        if (!trimmed.length)
            return "";
        var normalized = trimmed.replace(/\\/g, "/");
        var lower = normalized.toLowerCase();
        if (lower.indexOf("file:") === 0)
            return _normalizedFileUrlFromRemainder(normalized.substring(5));
        if (_isWindowsDrivePath(trimmed))
            return "file:///" + encodeURI(trimmed.replace(/\\/g, "/"));
        if (_isUncPath(trimmed))
            return "file:" + encodeURI(trimmed.replace(/\\/g, "/"));
        if (_isAbsolutePosixPath(trimmed))
            return "file://" + encodeURI(trimmed);
        return "";
    }

    function _previewSourceUrl(localSourceUrl) {
        var normalized = String(localSourceUrl || "").trim();
        if (!normalized.length)
            return "";
        return "image://local-media-preview/preview?source=" + encodeURIComponent(normalized);
    }

    function _describePdfPreview(source, pageNumber) {
        if (typeof mainWindow !== "undefined" && mainWindow) {
            try {
                return mainWindow.describe_pdf_preview(String(source || ""), pageNumber);
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

    component SurfaceButton : Button {
        id: control
        property string iconName: ""
        property int iconSize: 14
        property bool externalHover: false
        readonly property bool hoverVisualActive: hovered || externalHover
        readonly property color resolvedForegroundColor: hoverVisualActive
            ? "#4DA8DA"
            : surface.cropButtonIconColor
        property color iconColor: resolvedForegroundColor
        property color labelColor: resolvedForegroundColor
        readonly property string resolvedIconSource: surface._iconSource(iconName, iconSize, String(iconColor))
        implicitHeight: 24
        implicitWidth: Math.max(28, contentRow.implicitWidth + 14)
        padding: 0
        hoverEnabled: true

        contentItem: Item {
            implicitWidth: contentRow.implicitWidth
            implicitHeight: contentRow.implicitHeight

            Row {
                id: contentRow
                anchors.centerIn: parent
                spacing: control.text.length > 0 && control.resolvedIconSource.length > 0 ? 6 : 0

                Image {
                    visible: control.resolvedIconSource.length > 0
                    source: control.resolvedIconSource
                    width: control.iconSize
                    height: control.iconSize
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    mipmap: true
                    sourceSize.width: control.iconSize
                    sourceSize.height: control.iconSize
                }

                Text {
                    visible: control.text.length > 0
                    text: control.text
                    color: control.labelColor
                    font.pixelSize: 10
                    font.bold: true
                    verticalAlignment: Text.AlignVCenter
                    renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                }
            }
        }

        background: Rectangle {
            radius: 6
            color: control.down
                ? Qt.alpha("#4DA8DA", 0.35)
                : (control.hoverVisualActive
                    ? Qt.alpha("#4DA8DA", 0.22)
                    : Qt.alpha(surface.panelFillColor, 0.82))
            border.width: control.hoverVisualActive ? 1.5 : 1
            border.color: control.down
                ? Qt.alpha("#4DA8DA", 0.95)
                : (control.hoverVisualActive
                    ? Qt.alpha("#4DA8DA", 0.85)
                    : Qt.alpha(surface.panelBorderColor, 0.82))
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: host ? Number(host.resolvedCornerRadius || 6) : 6
        color: surface.panelFillColor
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: surface.panelBorderColor
    }

    SurfaceButton {
        id: cropButton
        objectName: "graphNodeMediaCropButton"
        z: 6
        visible: surface.cropButtonVisible
        enabled: visible
        iconName: "crop"
        iconSize: 14
        externalHover: host ? Boolean(host.surfaceHoverActionHovered) : false
        anchors.right: parent.right
        anchors.rightMargin: 10
        y: host
            ? Number(host.surfaceMetrics.title_top || 0)
                + Math.max(0, (Number(host.surfaceMetrics.title_height || 24) - height) * 0.5)
            : 6
        implicitWidth: 28
        text: ""
        onClicked: surface.triggerHoverAction()
    }

    Rectangle {
        id: pdfPageBadge
        objectName: "graphNodeMediaPageBadge"
        z: 5
        visible: surface.isPdfPanel && surface.previewState === "ready" && surface.pdfPageCount > 0
        anchors.right: parent.right
        anchors.rightMargin: host ? Number(host.surfaceMetrics.title_right_margin || 10) : 10
        y: host
            ? Number(host.surfaceMetrics.title_top || 0)
                + Math.max(0, (Number(host.surfaceMetrics.title_height || 28) - height) * 0.5)
            : 6
        radius: 10
        color: surface.pdfBadgeFillColor
        border.width: 1
        border.color: surface.pdfBadgeBorderColor
        height: pageBadgeLabel.implicitHeight + 10
        width: pageBadgeLabel.implicitWidth + 16

        Text {
            id: pageBadgeLabel
            anchors.centerIn: parent
            text: "Page " + surface.pdfResolvedPageNumber + " / " + surface.pdfPageCount
            color: surface.pdfBadgeTextColor
            font.pixelSize: 10
            font.bold: true
            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
        }
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

        Rectangle {
            id: previewViewport
            objectName: "graphNodeMediaPreviewViewport"
            width: parent.width
            height: surface.captionVisible
                ? Math.max(64, parent.height - captionBlock.implicitHeight - parent.spacing)
                : parent.height
            radius: 8
            color: surface.viewportFillColor
            border.width: 1
            border.color: Qt.alpha(surface.panelBorderColor, 0.82)
            clip: true

            Item {
                anchors.fill: parent

                Image {
                    id: sourceImageProbe
                    visible: false
                    asynchronous: false
                    cache: true
                    source: surface.isPdfPanel ? "" : surface.previewSourceUrl
                }

                Image {
                    id: previewImage
                    objectName: "graphNodeMediaPreviewImage"
                    anchors.centerIn: parent
                    asynchronous: false
                    cache: surface.isPdfPanel
                    mipmap: true
                    fillMode: surface.isPdfPanel
                        ? Image.PreserveAspectFit
                        : (surface.normalizedFitMode === "cover"
                            ? Image.PreserveAspectCrop
                            : Image.PreserveAspectFit)
                    source: surface.previewSourceUrl
                    sourceClipRect: surface.isPdfPanel
                        ? Qt.rect(0, 0, sourceSize.width, sourceSize.height)
                        : surface.appliedSourceClipRect
                    sourceSize.width: surface.isPdfPanel ? Math.max(1, Math.round(previewViewport.width)) : 0
                    sourceSize.height: surface.isPdfPanel ? Math.max(1, Math.round(previewViewport.height)) : 0
                    width: surface.originalModeActive
                        ? Math.max(1, implicitWidth)
                        : parent.width
                    height: surface.originalModeActive
                        ? Math.max(1, implicitHeight)
                        : parent.height
                    visible: surface.isPdfPanel && surface.previewState === "ready" && !surface.cropModeActive
                    smooth: true
                }

                Item {
                    id: appliedImageViewport
                    objectName: "graphNodeMediaAppliedImageViewport"
                    x: Number(surface.appliedPreviewRect.x || 0)
                    y: Number(surface.appliedPreviewRect.y || 0)
                    width: Math.max(0, Number(surface.appliedPreviewRect.width || 0))
                    height: Math.max(0, Number(surface.appliedPreviewRect.height || 0))
                    visible: !surface.isPdfPanel && surface.previewState === "ready" && !surface.cropModeActive
                    clip: true

                    Image {
                        id: appliedImage
                        objectName: "graphNodeMediaAppliedImage"
                        x: Number(surface.appliedImageOffsetX || 0)
                        y: Number(surface.appliedImageOffsetY || 0)
                        width: Math.max(0, Number(surface.appliedFullImageWidth || 0))
                        height: Math.max(0, Number(surface.appliedFullImageHeight || 0))
                        asynchronous: false
                        cache: true
                        mipmap: true
                        fillMode: Image.Stretch
                        source: surface.previewSourceUrl
                        smooth: true
                    }
                }

                Item {
                    id: cropOverlay
                    objectName: "graphNodeMediaCropOverlay"
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
                        y: Number(surface.draftDisplayCropRect.y || 0) + Number(surface.draftDisplayCropRect.height || 0)
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
                        x: Number(surface.draftDisplayCropRect.x || 0) + Number(surface.draftDisplayCropRect.width || 0)
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
                            width: surface.cropHandleSize
                            height: surface.cropHandleSize
                            radius: 3
                            z: 4
                            color: surface.cropHandleFillColor
                            border.width: 2
                            border.color: surface.cropHandleBorderColor
                            x: surface._handleX(handleId, surface.draftDisplayCropRect, width)
                            y: surface._handleY(handleId, surface.draftDisplayCropRect, height)

                            MouseArea {
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

                        SurfaceButton {
                            objectName: "graphNodeMediaCropApplyButton"
                            text: "Apply"
                            onClicked: surface._applyCropEdit()
                        }

                        SurfaceButton {
                            objectName: "graphNodeMediaCropCancelButton"
                            text: "Cancel"
                            onClicked: surface._cancelCropEdit()
                        }
                    }
                }

                Column {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 24, surface.isPdfPanel ? 208 : 180)
                    spacing: 8
                    visible: surface.previewState !== "ready"

                    Item {
                        width: 42
                        height: 42
                        anchors.horizontalCenter: parent.horizontalCenter

                        Rectangle {
                            visible: !surface.isPdfPanel
                            width: 42
                            height: 42
                            radius: 8
                            color: Qt.alpha(surface.panelBorderColor, 0.1)
                            border.width: 1
                            border.color: Qt.alpha(surface.panelBorderColor, 0.55)

                            Rectangle {
                                anchors.centerIn: parent
                                width: 22
                                height: 16
                                radius: 3
                                color: "transparent"
                                border.width: 1
                                border.color: Qt.alpha(surface.hintTextColor, 0.9)
                            }
                        }

                        Item {
                            visible: surface.isPdfPanel
                            anchors.fill: parent

                            Rectangle {
                                x: 8
                                y: 2
                                width: 26
                                height: 34
                                radius: 4
                                color: "#F5F7FA"
                                border.width: 1
                                border.color: Qt.alpha(surface.hintTextColor, 0.75)
                            }

                            Rectangle {
                                x: 13
                                y: 8
                                width: 16
                                height: 8
                                radius: 2
                                color: surface.previewState === "error"
                                    ? Qt.alpha("#B55454", 0.92)
                                    : Qt.alpha("#3A7CA5", 0.92)
                            }

                            Rectangle {
                                x: 28
                                y: 2
                                width: 6
                                height: 6
                                color: "#E8EDF3"
                                rotation: 45
                                transformOrigin: Item.TopLeft
                            }
                        }
                    }

                    Text {
                        objectName: "graphNodeMediaPreviewHint"
                        visible: parent.visible
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        color: surface.hintTextColor
                        font.pixelSize: 11
                        text: surface.previewHintText
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }
                }
            }
        }

        Text {
            id: captionBlock
            objectName: "graphNodeMediaCaption"
            property int effectiveRenderType: renderType
            visible: surface.captionVisible
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
