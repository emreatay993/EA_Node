import QtQuick 2.15

Item {
    id: surface
    objectName: "graphNodeMediaSurface"
    property Item host: null
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
    readonly property color panelBorderColor: host && host.nodeData && host.nodeData.selected
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
    implicitHeight: host ? Number(host.surfaceMetrics.body_height || 0) : 0

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

    function _normalizedFitMode() {
        var value = _value("fit_mode").trim().toLowerCase();
        if (value === "cover" || value === "original")
            return value;
        return "contain";
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

    Rectangle {
        anchors.fill: parent
        radius: host ? Number(host.resolvedCornerRadius || 6) : 6
        color: surface.panelFillColor
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: surface.panelBorderColor
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
                    id: previewImage
                    objectName: "graphNodeMediaPreviewImage"
                    anchors.centerIn: parent
                    asynchronous: false
                    cache: false
                    mipmap: true
                    fillMode: surface.isPdfPanel
                        ? Image.PreserveAspectFit
                        : (surface.normalizedFitMode === "cover"
                            ? Image.PreserveAspectCrop
                            : Image.PreserveAspectFit)
                    source: surface.previewSourceUrl
                    sourceSize.width: surface.isPdfPanel ? Math.max(1, Math.round(previewViewport.width)) : 0
                    sourceSize.height: surface.isPdfPanel ? Math.max(1, Math.round(previewViewport.height)) : 0
                    width: surface.originalModeActive
                        ? Math.max(1, implicitWidth)
                        : parent.width
                    height: surface.originalModeActive
                        ? Math.max(1, implicitHeight)
                        : parent.height
                    visible: surface.previewState === "ready"
                    smooth: true
                }

                Rectangle {
                    id: pdfPageBadge
                    objectName: "graphNodeMediaPageBadge"
                    visible: surface.isPdfPanel && surface.previewState === "ready" && surface.pdfPageCount > 0
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: 10
                    anchors.rightMargin: 10
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
                    }
                }
            }
        }

        Text {
            id: captionBlock
            objectName: "graphNodeMediaCaption"
            visible: surface.captionVisible
            width: parent.width
            text: surface.captionText
            color: surface.captionTextColor
            font.pixelSize: host ? Number(host.passiveFontPixelSize || 12) : 12
            font.bold: host ? Boolean(host.passiveFontBold) : false
            wrapMode: Text.WordWrap
            maximumLineCount: 4
            elide: Text.ElideRight
        }
    }
}
