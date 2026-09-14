import QtQuick 2.15
import QtQuick.Controls 2.15
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry
import "../surface_controls/SourceStorageModeUtils.js" as SourceStorageModeUtils
import "TabularSurfaceUtils.js" as TabularUtils

Item {
    id: surface
    objectName: "graphNodeTabularSurface"
    property Item host: null
    readonly property var nodeData: host && host.nodeData ? host.nodeData : ({})
    readonly property var nodeProperties: nodeData && nodeData.properties ? nodeData.properties : ({})
    readonly property var tableViewState: nodeProperties && nodeProperties.tabular_table_view_state
        ? nodeProperties.tabular_table_view_state
        : ({})
    property var lastExportResult: ({})
    property var selectedColumns: []
    readonly property string nodeId: String(nodeData.node_id || "")
    readonly property string sourcePath: String(nodeProperties.path || "")
    readonly property bool hasSourcePath: sourcePath.trim().length > 0
    readonly property bool selectionReviewRequired: Object.keys(nodeProperties.data_view_migration_notice || ({})).length > 0
    readonly property string sourceStorageMode: SourceStorageModeUtils.sourceModeForPath(sourcePath)
    // Refreshed (not bound): cold sources answer with a transient "loading"
    // state while the managed cache builds on a worker; the retry timer below
    // re-describes until the warm payload lands.
    property var previewPayload: ({})
    property bool awaitingInlinePreviewBridge: false
    readonly property string previewState: String(previewPayload.state || "placeholder")
    readonly property string previewKind: TabularUtils.previewKind(previewPayload)
    readonly property bool previewReady: previewState === "ready"
    readonly property bool exportAvailable: previewReady
        && host
        && host.surfaceFullscreenBridgeRef
        && host.surfaceFullscreenBridgeRef.export_tabular_visible_rows_for_node
    readonly property bool fullscreenAvailable: host
        && host.surfaceFullscreenBridgeRef
        && host.surfaceFullscreenBridgeRef.request_open_node
    readonly property bool blocksHostInteraction: false
    readonly property color panelFillColor: host && host.hasPassiveFillOverride
        ? host.surfaceColor
        : Qt.darker(host ? host.surfaceColor : "#1b1f2a", 1.03)
    readonly property color panelBorderColor: host && host.isSelected
        ? host.themeSelectedOutlineColor
        : (host && host.hasPassiveBorderOverride
            ? host.outlineColor
            : (host ? Qt.lighter(host.outlineColor, 1.1) : "#3a4355"))
    readonly property color captionTextColor: host ? host.inlineInputTextColor : "#eef3ff"
    readonly property color mutedTextColor: host ? host.inlineDrivenTextColor : "#95a0b8"
    readonly property color statusOkColor: "#22B455"
    readonly property color statusInfoColor: host ? host.selectedOutlineColor : "#60CDFF"
    readonly property color statusWarnColor: host ? host.warningOutlineColor : "#E8A838"
    readonly property color statusErrorColor: "#FF6B57"
    readonly property var statusBadge: TabularUtils.nodeStatus(
        {"preview": surface.previewPayload, "properties": surface.nodeProperties},
        surface.sourcePath
    )
    readonly property string statusLabel: String(statusBadge.label || "")
    readonly property string statusTone: String(statusBadge.tone || "muted")
    readonly property color statusToneColor: statusTone === "ok"
        ? statusOkColor
        : (statusTone === "info"
            ? statusInfoColor
            : (statusTone === "warn"
                ? statusWarnColor
                : (statusTone === "error" ? statusErrorColor : mutedTextColor)))
    readonly property string statusDetail: TabularUtils.nodeDetail(
        {"preview": surface.previewPayload, "properties": surface.nodeProperties},
        surface.sourcePath
    )
    readonly property bool showStatusSummary: statusLabel.trim().length > 0
        || statusDetail.trim().length > 0
    readonly property string emptyStateHeadline: TabularUtils.nodeEmptyHeadline(
        {"preview": surface.previewPayload, "properties": surface.nodeProperties},
        surface.sourcePath
    )
    readonly property string emptyStateDescription: TabularUtils.nodeEmptyDescription(
        {"preview": surface.previewPayload, "properties": surface.nodeProperties},
        surface.sourcePath
    )
    readonly property bool bodyRegionHosted: host
        && host.surfaceLayout
        && String(host.surfaceLayout.content_region || "host") === "body"
    readonly property real minimumBodyWidth: 320.0
    readonly property real minimumBodyHeight: 154.0
    readonly property real contentLeftMargin: bodyRegionHosted ? 0 : (host ? Number(host.surfaceMetrics.body_left_margin || 10) : 10)
    readonly property real contentRightMargin: bodyRegionHosted ? 0 : (host ? Number(host.surfaceMetrics.body_right_margin || 10) : 10)
    readonly property real contentTopMargin: bodyRegionHosted ? 0 : (host ? Number(host.surfaceMetrics.body_top || 30) : 30)
    readonly property real contentBottomMargin: bodyRegionHosted ? 0 : (host ? Number(host.surfaceMetrics.body_bottom_margin || 10) : 10)
    readonly property var embeddedInteractiveRects: SurfaceControlGeometry.rectList(SurfaceControlGeometry.rectFromItem(gridPanel, host))
    readonly property var surfaceActions: [
        {
            "id": "fullscreen",
            "label": "Configure data",
            "description": "Choose a source, map arrays and set output rules.",
            "icon": "table-configure",
            "kind": "surface",
            "enabled": fullscreenAvailable,
            "primary": true
        },
        {
            "id": "editSource",
            "label": "Source",
            "icon": "search",
            "kind": "surface",
            "enabled": true,
            "primary": false,
            "popover_layout": "source_storage",
            "popoverActions": [
                {
                    "id": "editSourceExternalLink",
                    "label": "External link",
                    "icon": "external-link",
                    "kind": "surface",
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
                    "kind": "surface",
                    "toolbar_text": "Internal",
                    "source_mode": "managed_copy",
                    "checked": sourceStorageMode === "managed_copy",
                    "enabled": true,
                    "close_popover": true
                }
            ]
        },
        {
            "id": "exportVisibleRows",
            "label": "Export",
            "icon": "file-text",
            "kind": "surface",
            "enabled": exportAvailable,
            "primary": false
        }
    ]
    implicitWidth: minimumBodyWidth
    implicitHeight: Math.max(minimumBodyHeight, host ? Number(host.surfaceMetrics.body_height || 0) : 0)

    onNodeDataChanged: refreshPreview()
    onSourcePathChanged: refreshPreview()
    Component.onCompleted: refreshPreview()

    Timer {
        interval: 750
        repeat: true
        running: surface.previewState === "loading" || surface.awaitingInlinePreviewBridge
        onTriggered: surface.refreshPreview()
    }

    Connections {
        target: surface.host
        ignoreUnknownSignals: true
        function onCanvasItemChanged() {
            surface.refreshPreview();
        }
    }

    Connections {
        target: surface._canvasItem()
        ignoreUnknownSignals: true
        function onCanvasCommandBridgeChanged() {
            surface.refreshPreview();
        }
    }

    function refreshPreview() {
        var payload = _describePreview();
        awaitingInlinePreviewBridge = _shouldRetryInlinePreviewBridge(payload);
        previewPayload = payload;
    }

    function _canvasItem() {
        return host && host.canvasItem ? host.canvasItem : null;
    }

    function _fallbackPreview(message) {
        return {
            "state": sourcePath.trim().length > 0 ? "placeholder" : "placeholder",
            "message": String(message || "Choose a tabular data file to preview it here."),
            "content_kind": "tabular",
            "preview_kind": "",
            "source": {"path": sourcePath},
            "selector": {},
            "limits": {
                "inline_row_limit": 50,
                "inline_column_limit": 50
            }
        };
    }

    function _shouldRetryInlinePreviewBridge(payload) {
        if (!hasSourcePath)
            return false;
        var normalized = payload && typeof payload === "object" ? payload : ({});
        var state = String(normalized.state || "");
        if (state === "error" || state === "warning" || state === "selection_required")
            return false;
        if (state === "ready")
            return !_hasPreviewWindow(normalized);
        return true;
    }

    function _hasPreviewWindow(payload) {
        var normalized = payload && typeof payload === "object" ? payload : ({});
        var kind = String(normalized.preview_kind || "");
        var window = kind === "array" ? normalized.slice_2d : normalized.window;
        if (!window || typeof window !== "object")
            return false;
        if (kind === "array")
            return window.values && window.values.length !== undefined;
        if (kind === "table")
            return window.columns && window.columns.length !== undefined
                && window.rows && window.rows.length !== undefined;
        return false;
    }

    function _describePreview() {
        if (nodeData.preview
                && typeof nodeData.preview === "object"
                && !_shouldRetryInlinePreviewBridge(nodeData.preview))
            return nodeData.preview;
        if (nodeData.tabular_preview
                && typeof nodeData.tabular_preview === "object"
                && !_shouldRetryInlinePreviewBridge(nodeData.tabular_preview))
            return nodeData.tabular_preview;
        var canvasItem = _canvasItem();
        if (canvasItem && canvasItem.describeNodeSurfaceTabularPreview) {
            try {
                var payload = canvasItem.describeNodeSurfaceTabularPreview(
                    nodeProperties,
                    {"row_limit": 50, "column_limit": 50}
                );
                if (payload && typeof payload === "object")
                    return payload;
            } catch (error) {
                return _fallbackPreview("Tabular preview is unavailable.");
            }
        }
        return _fallbackPreview(sourcePath.trim().length > 0
            ? "Open fullscreen to resolve a bounded tabular preview window."
            : "Choose a tabular data file to preview it here.");
    }

    function _iconSource(name, size, color) {
        if (typeof uiIcons === "undefined" || !uiIcons || !uiIcons.has(name))
            return "";
        return uiIcons.sourceSized(name, size, color);
    }

    function _beginSurfaceInteraction() {
        if (host && host.nodeData)
            host.surfaceControlInteractionStarted(String(host.nodeData.node_id || ""));
    }

    function _requestContentFullscreen() {
        if (!fullscreenAvailable)
            return false;
        _beginSurfaceInteraction();
        return Boolean(host.surfaceFullscreenBridgeRef.request_open_node(nodeId));
    }

    function _copyObject(value) {
        var source = value && typeof value === "object" ? value : ({});
        var output = {};
        for (var key in source)
            output[key] = source[key];
        return output;
    }

    function _activeExportRequest() {
        var window = TabularUtils.windowPayload(previewPayload);
        var request = window && window.request && typeof window.request === "object"
            ? _copyObject(window.request)
            : {};
        return {
            "preview_kind": previewKind,
            "request": request
        };
    }

    function _exportVisibleRows() {
        if (!previewReady || !host || !host.surfaceFullscreenBridgeRef)
            return false;
        var bridge = host.surfaceFullscreenBridgeRef;
        if (!bridge.export_tabular_visible_rows_for_node)
            return false;
        _beginSurfaceInteraction();
        var result = bridge.export_tabular_visible_rows_for_node(nodeId, _activeExportRequest());
        lastExportResult = result && typeof result === "object" ? result : ({});
        return Boolean(lastExportResult.ok);
    }

    function _saveTableViewState(state) {
        var canvasItem = _canvasItem();
        if (!canvasItem || !canvasItem.commitNodeSurfaceProperty)
            return false;
        return Boolean(canvasItem.commitNodeSurfaceProperty(
            nodeId,
            "tabular_table_view_state",
            state || ({})
        ));
    }

    function _saveSelectedColumns(columns) {
        selectedColumns = columns || [];
        return true;
    }

    function _editSource(sourceMode) {
        if (!_requestContentFullscreen()) return false;
        var composer = host.surfaceFullscreenBridgeRef.tabular_composer;
        if (!composer) return false;
        var mode = SourceStorageModeUtils.normalizedSourceMode(sourceMode, sourceStorageMode);
        composer.browse_source(mode === "managed_copy");
        return true;
    }

    function dispatchSurfaceAction(actionId) {
        var normalized = String(actionId || "");
        if (normalized === "editSource")
            return _editSource();
        if (normalized === "editSourceManagedCopy")
            return _editSource("managed_copy");
        if (normalized === "editSourceExternalLink")
            return _editSource("external_link");
        if (normalized === "exportVisibleRows")
            return _exportVisibleRows();
        if (normalized === "fullscreen")
            return _requestContentFullscreen();
        return false;
    }

    Rectangle {
        anchors.fill: parent
        radius: host ? Number(host.resolvedCornerRadius || 6) : 6
        color: surface.panelFillColor
        border.width: host ? Number(host.resolvedBorderWidth || 1) : 1
        border.color: surface.panelBorderColor
    }

    Column {
        id: contentColumn
        anchors.left: parent.left
        anchors.leftMargin: surface.contentLeftMargin
        anchors.right: parent.right
        anchors.rightMargin: surface.contentRightMargin
        anchors.top: parent.top
        anchors.topMargin: surface.contentTopMargin
        anchors.bottom: parent.bottom
        anchors.bottomMargin: surface.contentBottomMargin
        spacing: surface.showStatusSummary ? 6 : 0

        Row {
            id: statusSummaryRow
            objectName: "graphNodeTabularStatusSummary"
            width: parent.width
            height: surface.showStatusSummary ? 26 : 0
            visible: surface.showStatusSummary
            spacing: 8

            Column {
                width: parent.width
                height: parent.height
                spacing: 2

                Row {
                    width: parent.width
                    spacing: 6

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 7
                        height: 7
                        radius: 3.5
                        color: surface.statusToneColor
                    }

                    Text {
                        objectName: "graphNodeTabularStatusText"
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(0, parent.width - 7 - parent.spacing)
                        text: String(surface.nodeProperties.data_view_name || surface.statusLabel)
                        visible: surface.showStatusSummary
                        color: surface.captionTextColor
                        font.pixelSize: 11
                        font.bold: true
                        elide: Text.ElideRight
                    }
                }

                Text {
                    objectName: "graphNodeTabularWindowSummary"
                    x: 8
                    width: Math.max(0, parent.width - 8)
                    text: surface.previewReady
                        ? TabularUtils.visibleSummary(surface.previewPayload)
                        : surface.statusDetail
                    visible: surface.showStatusSummary
                    color: surface.mutedTextColor
                    font.pixelSize: 9
                    elide: Text.ElideRight
                }
            }
        }

        TabularTableViewport {
            id: gridPanel
            objectName: "graphNodeTabularPreviewGrid"
            width: parent.width
            height: Math.max(44, parent.height - (surface.showStatusSummary ? 32 : 0) - (surface.selectionReviewRequired ? 22 : 0))
            host: surface.host
            compact: true
            preview: surface.previewPayload
            tableViewState: surface.tableViewState
            selectedColumns: surface.selectedColumns
            objectNamePrefix: "graphNodeTabularPreview"
            visible: surface.previewReady
            onTableViewStateEdited: function(state) {
                surface._saveTableViewState(state);
            }
            onSelectedColumnsEdited: function(columns) {
                surface._saveSelectedColumns(columns);
            }
        }

        Item {
            id: emptyStatePanel
            objectName: "graphNodeTabularPreviewPlaceholder"
            width: parent.width
            height: Math.max(44, parent.height - (surface.showStatusSummary ? 32 : 0) - (surface.selectionReviewRequired ? 22 : 0))
            visible: !surface.previewReady

            Column {
                anchors.centerIn: parent
                width: Math.min(parent.width - 16, 280)
                spacing: 6

                Text {
                    width: parent.width
                    text: surface.emptyStateHeadline
                    color: surface.captionTextColor
                    font.pixelSize: 12
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }

                Text {
                    width: parent.width
                    text: surface.emptyStateDescription
                    color: surface.mutedTextColor
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }



            }
        }
        Text {
            objectName: "graphNodeTabularSelectionReview"
            width: parent.width
            height: 16
            visible: surface.selectionReviewRequired
            text: "Selection review · Configure data in the toolbar"
            color: surface.statusWarnColor
            font.pixelSize: 10
            elide: Text.ElideRight
        }
    }
}
