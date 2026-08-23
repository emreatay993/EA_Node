import QtQuick 2.15
import "../graph" as GraphComponents
import "../graph/overlay" as GraphOverlay
import "../graph/passive" as GraphPassive
import "../web" as WebComponents
import "../common/TooltipCopy.js" as TooltipCopy

Item {
    id: root
    objectName: "graphCanvasRootLayers"
    property Item canvasItem: null
    property var sceneStateBridge: null
    property var viewStateBridge: null
    property var viewCommandBridge: null
    property var canvasActionRouter: null
    property var themePalette: ({})
    property var graphNodePalette: ({})
    property alias backgroundLayerItem: backgroundLayer
    property alias edgeLayerItem: edgeLayer
    property alias webPageRetentionStore: webPageRetentionStore
    property var _appliedLiveDragNodeIds: []
    property Item webPageAddressEditorHost: null
    property bool webPageAddressOverlayOpen: false
    property Item timestampEditorHost: null
    property bool timestampOverlayOpen: false
    property Item numberSliderEditorHost: null
    property bool numberSliderOverlayOpen: false
    property Item selectEditorHost: null
    property bool selectOverlayOpen: false
    property Item panelEditorHost: null
    property bool panelOverlayOpen: false
    readonly property var visibleNodesModel: root.sceneStateBridge
        && root.sceneStateBridge.visible_nodes_model !== undefined
        ? root.sceneStateBridge.visible_nodes_model
        : (root.sceneStateBridge ? root.sceneStateBridge.nodes_model : [])
    readonly property var visibleBackdropNodesModel: root.sceneStateBridge
        && root.sceneStateBridge.visible_backdrop_nodes_model !== undefined
        ? root.sceneStateBridge.visible_backdrop_nodes_model
        : (root.canvasItem ? root.canvasItem._sceneBackdropNodesModel() : [])
    readonly property var visibleBadgeNodesModel: root.sceneStateBridge
        && root.sceneStateBridge.visible_badge_nodes_model !== undefined
        ? root.sceneStateBridge.visible_badge_nodes_model
        : []
    readonly property var visibleModelDiagnostics: root.sceneStateBridge
        ? root.sceneStateBridge.visible_scene_model_diagnostics
        : ({})
    readonly property var activeVirtualizedNodeIds: root._activeVirtualizedNodeIds()
    readonly property int visibleNodeDelegateCount: nodeWorldLayer.visibleDelegateCount
    readonly property int visibleBackdropDelegateCount: backdropLayer.visibleDelegateCount
    readonly property int profileTotalNodeCount: root._profileTotalNodeCount()
    readonly property int profileVisibleNodeDelegateCount: root.visibleNodeDelegateCount
    readonly property int profileVisibleBackdropDelegateCount: root.visibleBackdropDelegateCount
    readonly property real profileLastVisibleModelQueryMs: Math.max(
        0.0,
        Number((root.visibleModelDiagnostics || {}).query_ms || 0.0)
    )
    readonly property int profileVisibleModelQueryCount: Math.max(
        0,
        Math.round(Number((root.visibleModelDiagnostics || {}).query_count || 0))
    )
    readonly property int profileDelegateCreateCount: root._delegateCreateCount
    readonly property int profileDelegateDestroyCount: root._delegateDestroyCount
    readonly property int profileVisibleModelExactRefreshCount: root._visibleModelExactRefreshCount
    readonly property int profileVisibleModelIdleRefreshRequestCount: root._visibleModelIdleRefreshRequestCount
    readonly property int visibleModelExactRefreshDelayMs: root.canvasItem
        ? Math.max(80, Math.round(Number(root.canvasItem.transientRecoveryDelayMs || 150)))
        : 150
    property bool _delegateChurnInitialized: false
    property int _lastDelegateTotalCount: 0
    property int _delegateCreateCount: 0
    property int _delegateDestroyCount: 0
    property int _visibleModelExactRefreshCount: 0
    property int _visibleModelIdleRefreshRequestCount: 0
    property string _lastActiveVirtualizedNodeIdsSignature: ""
    readonly property var activeToolbarSurfaceItem: root._loadedSurfaceItem(
        root.canvasItem ? root.canvasItem.activeToolbarHost : null
    )
    readonly property bool activeToolbarAddressEditorOpen: root._surfaceAddressEditorOpen(
        root.activeToolbarSurfaceItem
    )
    readonly property bool activeToolbarTimestampEditorOpen: root._surfaceTimestampEditorOpen(
        root.activeToolbarSurfaceItem
    )
    readonly property var webPageAddressEditorSurface: root._loadedSurfaceItem(root.webPageAddressEditorHost)
    readonly property var timestampEditorSurface: root._loadedSurfaceItem(root.timestampEditorHost)
    readonly property var numberSliderEditorSurface: root._loadedSurfaceItem(root.numberSliderEditorHost)
    readonly property var selectEditorSurface: root._loadedSurfaceItem(root.selectEditorHost)
    readonly property var panelEditorSurface: root._loadedSurfaceItem(root.panelEditorHost)

    anchors.fill: parent

    WebComponents.WebPageRetentionStore {
        id: webPageRetentionStore
        objectName: "graphCanvasWebPageRetentionStore"
    }

    Component.onDestruction: root.clearRetainedWebPages()

    Connections {
        target: root.sceneStateBridge
        ignoreUnknownSignals: true

        function onScene_workspace_changing(workspaceId) {
            root._beginWebPageWorkspaceSwitch(workspaceId);
        }

        function onScene_workspace_changed(workspaceId) {
            root._beginWebPageWorkspaceSwitch(workspaceId);
        }

        function onWorkspace_changed(workspaceId) {
            root._beginWebPageWorkspaceSwitch(workspaceId);
        }
    }

    readonly property var nodeLinkHoverPalette: ({
        "accent": root._graphNodeToken("card_selected_border", root._shellToken("accent", "#60CDFF")),
        "app_fg": root._graphNodeToken("header_fg", root._shellToken("app_fg", "#ffffff")),
        "border": root._graphNodeToken("card_border", root._shellToken("border", "#3a3d45")),
        "hover": root._graphNodeToken("inline_row_bg", root._shellToken("hover", "#33373f")),
        "input_bg": root._graphNodeToken("inline_input_bg", root._shellToken("input_bg", "#24262c")),
        "input_border": root._graphNodeToken("card_border", root._shellToken("input_border", "#4a4f5a")),
        "input_fg": root._graphNodeToken("header_fg", root._shellToken("input_fg", "#f0f2f5")),
        "muted_fg": root._graphNodeToken("inline_label_fg", root._shellToken("muted_fg", "#9aa3af")),
        "on_accent": root._graphNodeToken("scope_badge_fg", root._shellToken("on_accent", "#0c2230")),
        "panel_bg": root._graphNodeToken("card_bg", root._shellToken("panel_bg", "#1b1d22")),
        "panel_alt_bg": root._graphNodeToken("card_bg", root._shellToken("panel_alt_bg", "#24262c")),
        "panel_title_fg": root._graphNodeToken("header_fg", root._shellToken("panel_title_fg", "#f0f4fb")),
        "pressed": root._graphNodeToken("inline_input_bg", root._shellToken("pressed", "#2d3139")),
        "tab_bg": root._graphNodeToken("card_bg", root._shellToken("tab_bg", "#24262c")),
        "tab_fg": root._graphNodeToken("header_fg", root._shellToken("tab_fg", "#f0f4fb"))
    })
    readonly property bool nodeCommentPaletteDark: root._hostSurfaceIsDark()
    readonly property var nodeCommentPalette: ({
        "isDark": root.nodeCommentPaletteDark,
        "appFg": root.nodeCommentPaletteDark ? "#e8e8e8" : "#17212b",
        "border": root.nodeCommentPaletteDark ? "#3a3d45" : "#b7c2ce",
        "comment": root.nodeCommentPaletteDark ? "#F2B84B" : "#D58E1E",
        "commentBorder": root.nodeCommentPaletteDark ? "#765f2b" : "#E3B660",
        "commentSoft": root.nodeCommentPaletteDark ? "#3c321f" : "#FFF4DA",
        "danger": root.nodeCommentPaletteDark ? "#ff7a7a" : "#B34B55",
        "hover": root.nodeCommentPaletteDark ? "#33373f" : "#dbe4ee",
        "inputBg": root.nodeCommentPaletteDark ? "#22242a" : "#ffffff",
        "inputBorder": root.nodeCommentPaletteDark ? "#4a4f5a" : "#96a6ba",
        "inputFg": root.nodeCommentPaletteDark ? "#f0f2f5" : "#17212b",
        "mutedFg": root.nodeCommentPaletteDark ? "#9aa3af" : "#5b6b7b",
        "onComment": root.nodeCommentPaletteDark ? "#241a08" : "#ffffff",
        "panelAltBg": root.nodeCommentPaletteDark ? "#24262c" : "#ffffff",
        "success": root.nodeCommentPaletteDark ? "#64C88A" : "#247B4F",
        "successSoft": root.nodeCommentPaletteDark ? "#20372a" : "#DDF3E8"
    })

    function _graphNodeToken(name, fallback) {
        var palette = root.graphNodePalette || {};
        return palette && palette[name] !== undefined ? palette[name] : fallback;
    }

    function _shellToken(name, fallback) {
        var palette = root.themePalette || {};
        return palette && palette[name] !== undefined ? palette[name] : fallback;
    }

    function _hostSurfaceIsDark() {
        var raw = root._graphNodeToken("card_bg", root._shellToken("panel_bg", "#1b1d22"));
        var color = Qt.color(String(raw || "#1b1d22"));
        return (0.2126 * color.r + 0.7152 * color.g + 0.0722 * color.b) < 0.5;
    }

    function _modelLength(model) {
        if (!model || model.length === undefined)
            return 0;
        var length = Number(model.length);
        return isFinite(length) ? Math.max(0, length) : 0;
    }

    function _appendVirtualizedNodeId(lookup, nodeId) {
        var normalized = String(nodeId || "").trim();
        if (normalized.length)
            lookup[normalized] = true;
    }

    function _appendVirtualizedLookupKeys(target, source) {
        if (!source)
            return;
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key) && Boolean(source[key]))
                root._appendVirtualizedNodeId(target, key);
        }
    }

    function _appendVirtualizedPortNodeId(lookup, portPayload) {
        if (portPayload)
            root._appendVirtualizedNodeId(lookup, portPayload.node_id);
    }

    function _activeVirtualizedNodeLookup() {
        var lookup = {};
        if (!root.canvasItem)
            return lookup;
        var executionFacts = root.canvasItem.executionFacts;
        if (executionFacts) {
            root._appendVirtualizedLookupKeys(lookup, executionFacts.failedNodeLookup);
            root._appendVirtualizedLookupKeys(lookup, executionFacts.runningNodeLookup);
            root._appendVirtualizedLookupKeys(lookup, executionFacts.completedNodeLookup);
            root._appendVirtualizedLookupKeys(lookup, executionFacts.warningNodeLookup);
            root._appendVirtualizedLookupKeys(lookup, executionFacts.freshRunNodeLookup);
        }
        root._appendVirtualizedLookupKeys(lookup, root.canvasItem.liveDragNodeLookup);
        root._appendVirtualizedLookupKeys(lookup, root.canvasItem.liveNodeGeometry);
        root._appendVirtualizedPortNodeId(lookup, root.canvasItem.hoveredPort);
        root._appendVirtualizedPortNodeId(lookup, root.canvasItem.dropPreviewPort);
        root._appendVirtualizedPortNodeId(lookup, root.canvasItem.pendingConnectionPort);
        root._appendVirtualizedPortNodeId(lookup, root.canvasItem.wireDropCandidate);
        if (root.canvasItem.nodeContextVisible)
            root._appendVirtualizedNodeId(lookup, root.canvasItem.nodeContextNodeId);
        if (root.canvasItem.wireDragState)
            root._appendVirtualizedNodeId(lookup, root.canvasItem.wireDragState.node_id);
        return lookup;
    }

    function _profileTotalNodeCount() {
        var diagnostics = root.visibleModelDiagnostics || ({});
        var fullCount = Number(diagnostics.full_count);
        if (isFinite(fullCount) && fullCount >= 0)
            return Math.round(fullCount);
        return root._modelLength(root.visibleNodesModel) + root._modelLength(root.visibleBackdropNodesModel);
    }

    function _currentDelegateTotalCount() {
        return Math.max(0, Number(root.visibleNodeDelegateCount || 0))
            + Math.max(0, Number(root.visibleBackdropDelegateCount || 0))
            + Math.max(0, Number(backdropInputLayer.visibleDelegateCount || 0));
    }

    function _recordDelegateChurn() {
        var nextCount = root._currentDelegateTotalCount();
        if (!root._delegateChurnInitialized) {
            root._delegateChurnInitialized = true;
            root._lastDelegateTotalCount = nextCount;
            root._delegateCreateCount += nextCount;
            return;
        }
        var delta = nextCount - root._lastDelegateTotalCount;
        if (delta > 0)
            root._delegateCreateCount += delta;
        else if (delta < 0)
            root._delegateDestroyCount += -delta;
        root._lastDelegateTotalCount = nextCount;
    }

    function _activeVirtualizedNodeIds() {
        var lookup = root._activeVirtualizedNodeLookup();
        var ids = [];
        for (var key in lookup) {
            if (Object.prototype.hasOwnProperty.call(lookup, key) && Boolean(lookup[key]))
                ids.push(key);
        }
        ids.sort();
        return ids;
    }

    function _nodeIdSignature(nodeIds) {
        return nodeIds && nodeIds.length ? nodeIds.join("\u001f") : "";
    }

    function _syncVisibleModelActiveNodeIds() {
        if (!root.sceneStateBridge || !root.sceneStateBridge.set_visible_model_active_node_ids)
            return;
        var nodeIds = root.activeVirtualizedNodeIds;
        var signature = root._nodeIdSignature(nodeIds);
        if (signature === root._lastActiveVirtualizedNodeIdsSignature)
            return;
        root._lastActiveVirtualizedNodeIdsSignature = signature;
        root.sceneStateBridge.set_visible_model_active_node_ids(nodeIds);
    }

    function _beginWebPageWorkspaceSwitch(workspaceId) {
        webPageRetentionStore.beginWorkspaceSwitch(String(workspaceId || ""));
    }

    function clearRetainedWebPages() {
        webPageRetentionStore.clearAll();
    }

    function _allVisibleNodeHosts() {
        var hosts = [];
        if (nodeWorldLayer && nodeWorldLayer.allHosts)
            hosts = hosts.concat(nodeWorldLayer.allHosts());
        if (backdropLayer && backdropLayer.allHosts)
            hosts = hosts.concat(backdropLayer.allHosts());
        return hosts;
    }

    function _webPageSurfaceForHost(host) {
        var surface = root._loadedSurfaceItem(host);
        if (!surface || !surface.prepareForCanvasExport || !surface.finishCanvasExport)
            return null;
        if (String(surface.objectName || "") !== "graphNodeWebPageHost")
            return null;
        return surface;
    }

    function _prepareWebPageHostsForCanvasExport() {
        var surfaces = [];
        var hosts = root._allVisibleNodeHosts();
        for (var index = 0; index < hosts.length; index++) {
            var surface = root._webPageSurfaceForHost(hosts[index]);
            if (!surface)
                continue;
            surface.prepareForCanvasExport();
            surfaces.push(surface);
        }
        return surfaces;
    }

    function _finishWebPageHostsForCanvasExport(surfaces) {
        var items = surfaces || [];
        for (var index = 0; index < items.length; index++) {
            var surface = items[index];
            if (surface && surface.finishCanvasExport)
                surface.finishCanvasExport();
        }
    }

    function _canvasExportWebSettleDelayMs(request, surfaces) {
        if (!surfaces || surfaces.length <= 0)
            return 0;
        var requested = Number((request || {}).web_settle_ms);
        if (!isFinite(requested))
            requested = 260;
        return Math.max(0, Math.min(2000, Math.round(requested)));
    }

    function _hostNodeId(host) {
        if (!host || !host.nodeData)
            return "";
        return String(host.nodeData.node_id || "").trim();
    }

    function _visibleHostForNodeId(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return null;
        var host = nodeWorldLayer.hostForNodeId(normalized);
        if (host)
            return host;
        return backdropLayer.hostForNodeId(normalized);
    }

    function _visibleHostsForNodeId(nodeId) {
        var normalized = String(nodeId || "").trim();
        if (!normalized)
            return [];
        var hosts = [];
        var host = nodeWorldLayer.hostForNodeId(normalized);
        if (host)
            hosts.push(host);
        host = backdropLayer.hostForNodeId(normalized);
        if (host)
            hosts.push(host);
        host = backdropInputLayer.hostForNodeId(normalized);
        if (host)
            hosts.push(host);
        return hosts;
    }

    function _setHostLiveDragOffset(nodeId, dx, dy) {
        var hosts = root._visibleHostsForNodeId(nodeId);
        if (!hosts.length)
            return false;
        for (var i = 0; i < hosts.length; i++) {
            var host = hosts[i];
            host.liveDragDx = dx;
            host.liveDragDy = dy;
        }
        return true;
    }

    function exportCanvasBasePng(request, finished) {
        var payload = request || {};
        var requestId = String(payload.request_id || "");
        var outputPath = String(payload.path || "").trim();
        var scale = Math.min(4, Math.max(1, Math.round(Number(payload.scale) || 1)));
        var devicePixelRatio = Number(payload.device_pixel_ratio);
        if (!isFinite(devicePixelRatio) || devicePixelRatio <= 0.0)
            devicePixelRatio = 1.0;
        var baseLogicalWidth = Math.max(0.0, Number(graphCanvasBaseContent.width) || 0.0);
        var baseLogicalHeight = Math.max(0.0, Number(graphCanvasBaseContent.height) || 0.0);
        var targetWidth = Math.round(baseLogicalWidth * devicePixelRatio * scale);
        var targetHeight = Math.round(baseLogicalHeight * devicePixelRatio * scale);
        function finish(result) {
            if (typeof finished === "function")
                finished(result || {});
        }
        function finishFailure(message) {
            finish({
                "success": false,
                "request_id": requestId,
                "path": outputPath,
                "scale": scale,
                "device_pixel_ratio": devicePixelRatio,
                "base_logical_width": baseLogicalWidth,
                "base_logical_height": baseLogicalHeight,
                "output_pixel_width": targetWidth,
                "output_pixel_height": targetHeight,
                "width": targetWidth,
                "height": targetHeight,
                "error": message,
                "message": message
            });
        }
        if (!outputPath.length) {
            finishFailure("Export path is required.");
            return;
        }
        if (baseLogicalWidth <= 0.0 || baseLogicalHeight <= 0.0 || targetWidth <= 0 || targetHeight <= 0) {
            finishFailure("Canvas base size is not ready for export.");
            return;
        }
        if (!graphCanvasBaseContent || !graphCanvasBaseContent.grabToImage) {
            finishFailure("Canvas base capture is not available.");
            return;
        }
        root._forceExactVisibleSceneModels();
        if (root.canvasItem && root.canvasItem.flushViewStateRedraw)
            root.canvasItem.flushViewStateRedraw();
        var webPageExportSurfaces = root._prepareWebPageHostsForCanvasExport();
        function grabCanvasBaseContent() {
            graphCanvasBaseContent.grabToImage(function(result) {
                var saved = false;
                if (result && result.saveToFile)
                    saved = result.saveToFile(outputPath);
                var message = saved ? "" : "Could not save canvas base PNG.";
                root._finishWebPageHostsForCanvasExport(webPageExportSurfaces);
                finish({
                    "success": saved,
                    "request_id": requestId,
                    "path": outputPath,
                    "scale": scale,
                    "device_pixel_ratio": devicePixelRatio,
                    "base_logical_width": baseLogicalWidth,
                    "base_logical_height": baseLogicalHeight,
                    "output_pixel_width": targetWidth,
                    "output_pixel_height": targetHeight,
                    "width": targetWidth,
                    "height": targetHeight,
                    "error": message,
                    "message": message
                });
            }, Qt.size(targetWidth, targetHeight));
        }
        var webSettleDelayMs = root._canvasExportWebSettleDelayMs(payload, webPageExportSurfaces);
        if (webSettleDelayMs > 0) {
            canvasExportWebSettleTimer.startWithDelay(webSettleDelayMs, grabCanvasBaseContent);
        } else {
            Qt.callLater(grabCanvasBaseContent);
        }
    }

    function applyLiveDragOffsetToHost(host) {
        var nodeId = root._hostNodeId(host);
        if (!nodeId)
            return false;
        var dragged = root.canvasItem && root.canvasItem.liveDragNodeLookup
            ? Boolean(root.canvasItem.liveDragNodeLookup[nodeId])
            : false;
        host.liveDragDx = dragged ? Number(root.canvasItem.liveDragDx || 0.0) : 0.0;
        host.liveDragDy = dragged ? Number(root.canvasItem.liveDragDy || 0.0) : 0.0;
        return true;
    }

    function applyLiveDragOffsetToHosts() {
        var nodeIds = root.canvasItem ? root.canvasItem.liveDragNodeIds || [] : [];
        if (root._appliedLiveDragNodeIds !== nodeIds) {
            var previous = root._appliedLiveDragNodeIds || [];
            for (var previousIndex = 0; previousIndex < previous.length; previousIndex++)
                root._setHostLiveDragOffset(previous[previousIndex], 0.0, 0.0);
            root._appliedLiveDragNodeIds = nodeIds;
        }
        var dx = root.canvasItem ? Number(root.canvasItem.liveDragDx || 0.0) : 0.0;
        var dy = root.canvasItem ? Number(root.canvasItem.liveDragDy || 0.0) : 0.0;
        for (var index = 0; index < nodeIds.length; index++)
            root._setHostLiveDragOffset(nodeIds[index], dx, dy);
        return true;
    }

    function _forceExactVisibleSceneModels() {
        if (!root.sceneStateBridge || !root.sceneStateBridge.force_visible_scene_models_exact)
            return false;
        var refreshed = Boolean(root.sceneStateBridge.force_visible_scene_models_exact());
        if (refreshed)
            root._visibleModelExactRefreshCount += 1;
        return refreshed;
    }

    function forceExactVisibleSceneModels() {
        return root._forceExactVisibleSceneModels();
    }

    function _scheduleExactVisibleSceneModels() {
        if (!root.sceneStateBridge || !root.sceneStateBridge.force_visible_scene_models_exact)
            return;
        root._visibleModelIdleRefreshRequestCount += 1;
        visibleModelIdleRefreshTimer.restart();
    }

    onCanvasItemChanged: {
        root._lastActiveVirtualizedNodeIdsSignature = "";
        root._syncVisibleModelActiveNodeIds();
    }
    onSceneStateBridgeChanged: {
        root._lastActiveVirtualizedNodeIdsSignature = "";
        root._syncVisibleModelActiveNodeIds();
    }
    onActiveVirtualizedNodeIdsChanged: root._syncVisibleModelActiveNodeIds()
    onActiveToolbarAddressEditorOpenChanged: {
        if (root.activeToolbarAddressEditorOpen && root.canvasItem && root.canvasItem.activeToolbarHost)
            root._openWebPageAddressOverlay(root.canvasItem.activeToolbarHost, root.activeToolbarSurfaceItem);
    }
    onActiveToolbarTimestampEditorOpenChanged: {
        if (root.activeToolbarTimestampEditorOpen && root.canvasItem && root.canvasItem.activeToolbarHost)
            root._openTimestampOverlay(root.canvasItem.activeToolbarHost, root.activeToolbarSurfaceItem);
    }
    Component.onCompleted: {
        root._syncVisibleModelActiveNodeIds();
        root._forceExactVisibleSceneModels();
        root._recordDelegateChurn();
    }

    Connections {
        target: root.viewStateBridge
        function onView_state_changed() {
            root._scheduleExactVisibleSceneModels();
        }
    }

    Timer {
        id: visibleModelIdleRefreshTimer
        interval: root.visibleModelExactRefreshDelayMs
        repeat: false
        onTriggered: root._forceExactVisibleSceneModels()
    }

    Timer {
        id: canvasExportWebSettleTimer
        interval: 260
        repeat: false
        property var callback: null
        function startWithDelay(delayMs, nextCallback) {
            canvasExportWebSettleTimer.stop();
            canvasExportWebSettleTimer.interval = Math.max(0, Math.round(Number(delayMs || 0)));
            canvasExportWebSettleTimer.callback = nextCallback;
            canvasExportWebSettleTimer.start();
        }
        onTriggered: {
            var nextCallback = canvasExportWebSettleTimer.callback;
            canvasExportWebSettleTimer.callback = null;
            if (typeof nextCallback === "function")
                nextCallback();
        }
    }

    function _loadedSurfaceItem(host) {
        if (!host || host.loadedSurfaceItem === undefined || host.loadedSurfaceItem === null)
            return null;
        return host.loadedSurfaceItem;
    }

    function _surfaceAddressEditorOpen(surface) {
        return !!surface
            && surface.addressEditorOpen !== undefined
            && Boolean(surface.addressEditorOpen);
    }

    function _surfaceTimestampEditorOpen(surface) {
        return !!surface
            && surface.timestampManualEditorOpen !== undefined
            && Boolean(surface.timestampManualEditorOpen);
    }

    function _openWebPageAddressOverlay(host, surface) {
        if (!host || !root._surfaceAddressEditorOpen(surface))
            return false;
        root.webPageAddressEditorHost = host;
        root.webPageAddressOverlayOpen = true;
        webPageAddressPopover.openWithAddress(String(surface.addressEditorText || ""));
        return true;
    }

    function openWebPageAddressEditorForHost(host, surface) {
        return root._openWebPageAddressOverlay(host, surface || root._loadedSurfaceItem(host));
    }

    function _openTimestampOverlay(host, surface) {
        if (!host || !root._surfaceTimestampEditorOpen(surface))
            return false;
        root.timestampEditorHost = host;
        root.timestampOverlayOpen = true;
        timestampDateTimePopover.openWithTimestamp(String(surface.timestampManualEditorText || ""));
        return true;
    }

    function openTimestampEditorForHost(host, surface) {
        return root._openTimestampOverlay(host, surface || root._loadedSurfaceItem(host));
    }

    function _surfaceNumberSliderEditorOpen(surface) {
        return !!surface
            && surface.sliderSettingsEditorOpen !== undefined
            && Boolean(surface.sliderSettingsEditorOpen);
    }

    function _openNumberSliderOverlay(host, surface) {
        if (!host || !root._surfaceNumberSliderEditorOpen(surface))
            return false;
        root.numberSliderEditorHost = host;
        root.numberSliderOverlayOpen = true;
        numberSliderSettingsPopover.openWithSettings(surface.sliderSettingsPayload || ({}));
        return true;
    }

    function openNumberSliderEditorForHost(host, surface) {
        return root._openNumberSliderOverlay(host, surface || root._loadedSurfaceItem(host));
    }

    function _surfaceSelectEditorOpen(surface) {
        return !!surface
            && surface.selectSettingsEditorOpen !== undefined
            && Boolean(surface.selectSettingsEditorOpen);
    }

    function _openSelectOverlay(host, surface) {
        if (!host || !root._surfaceSelectEditorOpen(surface))
            return false;
        root.selectEditorHost = host;
        root.selectOverlayOpen = true;
        selectSettingsPopover.openWithSettings(surface.selectSettingsPayload || ({}));
        return true;
    }

    function openSelectEditorForHost(host, surface) {
        return root._openSelectOverlay(host, surface || root._loadedSurfaceItem(host));
    }

    function _surfacePanelEditorOpen(surface) {
        return !!surface
            && surface.panelEditorOpen !== undefined
            && Boolean(surface.panelEditorOpen);
    }

    function _openPanelOverlay(host, surface) {
        if (!host || !root._surfacePanelEditorOpen(surface))
            return false;
        root.panelEditorHost = host;
        root.panelOverlayOpen = true;
        panelEditorPopover.openWithSettings(surface.panelEditorPayload || ({}));
        return true;
    }

    function openPanelEditorForHost(host, surface) {
        return root._openPanelOverlay(host, surface || root._loadedSurfaceItem(host));
    }

    function openSurfaceActionOverlayForHost(host, actionId, surface) {
        if (String(actionId || "") === "web_page_edit_address")
            return root.openWebPageAddressEditorForHost(host, surface);
        if (String(actionId || "") === "timestamp_edit_manual")
            return root.openTimestampEditorForHost(host, surface);
        if (String(actionId || "") === "number_slider_edit_settings")
            return root.openNumberSliderEditorForHost(host, surface);
        if (String(actionId || "") === "select_edit_settings")
            return root.openSelectEditorForHost(host, surface);
        if (String(actionId || "") === "panel_edit")
            return root.openPanelEditorForHost(host, surface);
        return false;
    }

    function _cancelWebPageAddressOverlay() {
        if (root.webPageAddressOverlayOpen)
            webPageAddressPopover.cancelEdit();
    }

    function _cancelTimestampOverlay() {
        if (root.timestampOverlayOpen)
            timestampDateTimePopover.cancelEdit();
    }

    function _cancelNumberSliderOverlay() {
        if (root.numberSliderOverlayOpen)
            numberSliderSettingsPopover.cancelEdit();
    }

    function _cancelSelectOverlay() {
        if (root.selectOverlayOpen)
            selectSettingsPopover.cancelEdit();
    }

    function _cancelPanelOverlay() {
        if (root.panelOverlayOpen)
            panelEditorPopover.cancelEdit();
    }

    function _clampAddressOverlayX(preferred, overlayWidth) {
        return Math.max(8, Math.min(root.width - overlayWidth - 8, preferred));
    }

    function _quickWindowAddressOverlayY(overlayHeight) {
        var preferred = Math.max(24, Math.min(72, root.height * 0.12));
        return Math.max(8, Math.min(root.height - overlayHeight - 8, preferred));
    }

    function _itemRectInOverlayLayer(item, layer) {
        if (!item || !layer)
            return {"x": 0, "y": 0, "width": 0, "height": 0};
        var width = Math.max(0, Number(item.width || 0));
        var height = Math.max(0, Number(item.height || 0));
        var p1 = item.mapToItem(layer, 0, 0);
        var p2 = item.mapToItem(layer, width, 0);
        var p3 = item.mapToItem(layer, width, height);
        var p4 = item.mapToItem(layer, 0, height);
        var minX = Math.min(p1.x, p2.x, p3.x, p4.x);
        var maxX = Math.max(p1.x, p2.x, p3.x, p4.x);
        var minY = Math.min(p1.y, p2.y, p3.y, p4.y);
        var maxY = Math.max(p1.y, p2.y, p3.y, p4.y);
        return {
            "x": minX,
            "y": minY,
            "width": Math.max(0, maxX - minX),
            "height": Math.max(0, maxY - minY)
        };
    }

    function _timestampSheetWidth() {
        return Math.min(360, Math.max(300, timestampOverlayLayer.width - 32));
    }

    function _timestampSheetX(sheetWidth) {
        var rect = root._itemRectInOverlayLayer(root.timestampEditorHost, timestampOverlayLayer);
        if (rect.width > 0)
            return root._clampAddressOverlayX(rect.x + rect.width * 0.5 - sheetWidth * 0.5, sheetWidth);
        return root._clampAddressOverlayX(timestampOverlayLayer.width * 0.5 - sheetWidth * 0.5, sheetWidth);
    }

    function _timestampSheetY(sheetHeight) {
        var host = root.timestampEditorHost;
        var layer = timestampOverlayLayer;
        if (host && layer) {
            var preferredPoint = host.mapToItem(layer, 0, -sheetHeight - 10);
            if (preferredPoint.y >= 8)
                return preferredPoint.y;
            preferredPoint = host.mapToItem(layer, 0, Number(host.height || 0) + 10);
            return Math.max(8, Math.min(layer.height - sheetHeight - 8, preferredPoint.y));
        }
        return root._quickWindowAddressOverlayY(sheetHeight);
    }

    function _numberSliderSheetWidth() {
        return Math.min(400, Math.max(320, numberSliderOverlayLayer.width - 48));
    }

    function _numberSliderSheetX(sheetWidth) {
        var rect = root._itemRectInOverlayLayer(root.numberSliderEditorHost, numberSliderOverlayLayer);
        if (rect.width > 0)
            return root._clampAddressOverlayX(rect.x + rect.width * 0.5 - sheetWidth * 0.5, sheetWidth);
        return root._clampAddressOverlayX(numberSliderOverlayLayer.width * 0.5 - sheetWidth * 0.5, sheetWidth);
    }

    function _numberSliderSheetY(sheetHeight) {
        var host = root.numberSliderEditorHost;
        var layer = numberSliderOverlayLayer;
        if (host && layer) {
            var preferredPoint = host.mapToItem(layer, 0, Number(host.height || 0) + 16);
            if (preferredPoint.y + sheetHeight <= layer.height - 8)
                return preferredPoint.y;
            preferredPoint = host.mapToItem(layer, 0, -sheetHeight - 16);
            return Math.max(8, Math.min(layer.height - sheetHeight - 8, preferredPoint.y));
        }
        return root._quickWindowAddressOverlayY(sheetHeight);
    }

    function _selectSheetWidth() {
        return Math.min(480, Math.max(360, selectOverlayLayer.width - 48));
    }

    function _selectSheetX(sheetWidth) {
        var rect = root._itemRectInOverlayLayer(root.selectEditorHost, selectOverlayLayer);
        if (rect.width > 0)
            return root._clampAddressOverlayX(rect.x + rect.width * 0.5 - sheetWidth * 0.5, sheetWidth);
        return root._clampAddressOverlayX(selectOverlayLayer.width * 0.5 - sheetWidth * 0.5, sheetWidth);
    }

    function _selectSheetY(sheetHeight) {
        var host = root.selectEditorHost;
        var layer = selectOverlayLayer;
        if (host && layer) {
            var preferredPoint = host.mapToItem(layer, 0, Number(host.height || 0) + 16);
            if (preferredPoint.y + sheetHeight <= layer.height - 8)
                return preferredPoint.y;
            preferredPoint = host.mapToItem(layer, 0, -sheetHeight - 16);
            return Math.max(8, Math.min(layer.height - sheetHeight - 8, preferredPoint.y));
        }
        return root._quickWindowAddressOverlayY(sheetHeight);
    }

    function _panelSheetWidth() {
        return Math.min(320, Math.max(288, panelOverlayLayer.width - 32));
    }

    function _panelSheetX(sheetWidth) {
        var rect = root._itemRectInOverlayLayer(root.panelEditorHost, panelOverlayLayer);
        if (rect.width > 0)
            return root._clampAddressOverlayX(rect.x + rect.width * 0.5 - sheetWidth * 0.5, sheetWidth);
        return root._clampAddressOverlayX(panelOverlayLayer.width * 0.5 - sheetWidth * 0.5, sheetWidth);
    }

    function _panelSheetY(sheetHeight) {
        var host = root.panelEditorHost;
        var layer = panelOverlayLayer;
        if (host && layer) {
            var preferredPoint = host.mapToItem(layer, 0, Number(host.height || 0) + 16);
            if (preferredPoint.y + sheetHeight <= layer.height - 8)
                return preferredPoint.y;
            preferredPoint = host.mapToItem(layer, 0, -sheetHeight - 16);
            return Math.max(8, Math.min(layer.height - sheetHeight - 8, preferredPoint.y));
        }
        return root._quickWindowAddressOverlayY(sheetHeight);
    }

    Connections {
        target: root.webPageAddressEditorSurface

        function onAddressEditorOpenChanged() {
            var surface = root.webPageAddressEditorSurface;
            if (root._surfaceAddressEditorOpen(surface)) {
                webPageAddressPopover.openWithAddress(String(surface.addressEditorText || ""));
            } else {
                webPageAddressPopover.closeSilently();
                root.webPageAddressOverlayOpen = false;
                root.webPageAddressEditorHost = null;
            }
        }

        function onAddressEditorTextChanged() {
            var surface = root.webPageAddressEditorSurface;
            if (root._surfaceAddressEditorOpen(surface) && !webPageAddressPopover.visible)
                webPageAddressPopover.openWithAddress(String(surface.addressEditorText || ""));
        }
    }

    Connections {
        target: root.timestampEditorSurface

        function onTimestampManualEditorOpenChanged() {
            var surface = root.timestampEditorSurface;
            if (root._surfaceTimestampEditorOpen(surface)) {
                timestampDateTimePopover.openWithTimestamp(String(surface.timestampManualEditorText || ""));
            } else {
                timestampDateTimePopover.closeSilently();
                root.timestampOverlayOpen = false;
                root.timestampEditorHost = null;
            }
        }

        function onTimestampManualEditorTextChanged() {
            var surface = root.timestampEditorSurface;
            if (root._surfaceTimestampEditorOpen(surface) && !timestampDateTimePopover.visible)
                timestampDateTimePopover.openWithTimestamp(String(surface.timestampManualEditorText || ""));
        }
    }

    Connections {
        target: root.numberSliderEditorSurface

        function onSliderSettingsEditorOpenChanged() {
            var surface = root.numberSliderEditorSurface;
            if (root._surfaceNumberSliderEditorOpen(surface)) {
                numberSliderSettingsPopover.openWithSettings(surface.sliderSettingsPayload || ({}));
            } else {
                numberSliderSettingsPopover.closeSilently();
                root.numberSliderOverlayOpen = false;
                root.numberSliderEditorHost = null;
            }
        }
    }

    Connections {
        target: root.selectEditorSurface

        function onSelectSettingsEditorOpenChanged() {
            var surface = root.selectEditorSurface;
            if (root._surfaceSelectEditorOpen(surface)) {
                selectSettingsPopover.openWithSettings(surface.selectSettingsPayload || ({}));
            } else {
                selectSettingsPopover.closeSilently();
                root.selectOverlayOpen = false;
                root.selectEditorHost = null;
            }
        }
    }

    Connections {
        target: root.panelEditorSurface

        function onPanelEditorOpenChanged() {
            var surface = root.panelEditorSurface;
            if (root._surfacePanelEditorOpen(surface)) {
                panelEditorPopover.openWithSettings(surface.panelEditorPayload || ({}));
            } else {
                panelEditorPopover.closeSilently();
                root.panelOverlayOpen = false;
                root.panelEditorHost = null;
            }
        }
    }

    Item {
        id: graphCanvasBaseContent
        objectName: "graphCanvasBaseContent"
        anchors.fill: parent

        GraphCanvasBackground {
            id: backgroundLayer
            objectName: "graphCanvasBackground"
            anchors.fill: parent
            viewBridge: root.viewStateBridge
            canvasBackgroundVariant: root.canvasItem && root.canvasItem.prefs
                ? root.canvasItem.prefs.canvasBackgroundVariant
                : "theme"
            showGrid: root.canvasItem && root.canvasItem.prefs ? root.canvasItem.prefs.showGrid : true
            gridStyle: root.canvasItem && root.canvasItem.prefs ? root.canvasItem.prefs.gridStyle : "lines"
        }

        GraphCanvasWorldLayer {
            id: backdropLayer
            objectName: "graphCanvasBackdropLayer"
            canvasItem: root.canvasItem
            viewBridge: root.viewStateBridge
            sceneModel: root.visibleBackdropNodesModel
            onVisibleDelegateCountChanged: root._recordDelegateChurn()
        }

        GraphComponents.EdgeLayer {
            id: edgeLayer
            objectName: "graphCanvasEdgeLayer"
            anchors.fill: parent
            viewBridge: root.viewStateBridge
            sceneBridge: root.sceneStateBridge
            edges: root.canvasItem ? root.canvasItem.edgePayload : []
            nodeDeltaPayload: root.sceneStateBridge
                ? (root.sceneStateBridge.node_delta_payload || ({}))
                : ({})
            nodes: root.sceneStateBridge
                ? (
                    root.sceneStateBridge.stable_edge_endpoint_nodes_model !== undefined
                    ? root.sceneStateBridge.stable_edge_endpoint_nodes_model
                    : (root.sceneStateBridge.edge_endpoint_nodes_model || root.sceneStateBridge.nodes_model)
                )
                : []
            dragNodeLookup: root.canvasItem ? root.canvasItem.liveDragNodeLookup : ({})
            dragDx: root.canvasItem ? root.canvasItem.liveDragDx : 0.0
            dragDy: root.canvasItem ? root.canvasItem.liveDragDy : 0.0
            dragRevision: root.canvasItem ? root.canvasItem.liveDragRevision : 0
            liveNodeGeometry: root.canvasItem ? root.canvasItem.liveNodeGeometry : ({})
            selectedEdgeIds: root.canvasItem ? root.canvasItem.selectedEdgeIds : []
            visibleSceneRectPayload: root.canvasItem ? root.canvasItem.visibleSceneRectPayload : ({})
            previewEdgeId: root.canvasItem ? root.canvasItem.dropPreviewEdgeId : ""
            dragConnection: root.canvasItem ? root.canvasItem.wireDragPreviewConnection() : null
            replacementPreviewEdgeIds: dragConnection && dragConnection.replacement_edge_ids
                ? dragConnection.replacement_edge_ids
                : []
            wireSelectionModeHeld: root.canvasItem ? Boolean(root.canvasItem.wireSelectionModeHeld) : false
            outputPreviewLookup: root.canvasItem && root.canvasItem.executionFacts
                ? root.canvasItem.executionFacts.portValuePreviewLookup
                : ({})
            edgeCrossingStyle: root.canvasItem && root.canvasItem.prefs
                ? root.canvasItem.prefs.edgeCrossingStyle
                : "none"
            viewportInteractionActive: root.canvasItem
                ? root.canvasItem.viewportInteractionWorldCacheActive
                : false
            inputEnabled: !(root.canvasItem && (
                root.canvasItem.edgeContextVisible
                || root.canvasItem.nodeContextVisible
                || root.canvasItem.selectionContextVisible
                || root.canvasItem.canvasOptionsVisible
            ))

            onEdgeClicked: function(edgeId, additive) {
                if (!root.canvasItem)
                    return;
                root.canvasItem.forceActiveFocus();
                if (root.canvasItem.clearViewerFocus)
                    root.canvasItem.clearViewerFocus();
                root.canvasItem._closeContextMenus();
                root.canvasItem.clearPendingConnection();
                if (additive)
                    root.canvasItem.toggleEdgeSelection(edgeId);
                else
                    root.canvasItem.setExclusiveEdgeSelection(edgeId);
            }

            onEdgeDoubleClicked: function(edgeId) {
                if (!root.canvasItem)
                    return;
                root.canvasItem.forceActiveFocus();
                if (root.canvasItem.clearViewerFocus)
                    root.canvasItem.clearViewerFocus();
                root.canvasItem._closeContextMenus();
                root.canvasItem.clearPendingConnection();
                root.canvasItem.setExclusiveEdgeSelection(edgeId);
                if (root.canvasItem._edgeSupportsFlowStyle(edgeId)
                        && edgeFloatingToolbar
                        && edgeFloatingToolbar.beginLabelEdit
                        && edgeFloatingToolbar.beginLabelEdit(edgeId)) {
                    return;
                }
                var actionRouter = root.canvasActionRouter
                    || (root.canvasItem && root.canvasItem.canvasActionRouter ? root.canvasItem.canvasActionRouter : null);
                if (actionRouter && actionRouter.handleEdgeToolbarAction && actionRouter.edgeContextActionId) {
                    actionRouter.handleEdgeToolbarAction(
                        actionRouter.edgeContextActionId("edit_flow_edge_label"),
                        edgeId
                    );
                }
            }

            onEdgeContextRequested: function(edgeId, screenX, screenY) {
                if (!root.canvasItem)
                    return;
                if (root.canvasItem.clearViewerFocus)
                    root.canvasItem.clearViewerFocus();
                root.canvasItem._openEdgeContext(edgeId, screenX, screenY);
            }
        }

        GraphCanvasWorldLayer {
            id: backdropInputLayer
            objectName: "graphCanvasBackdropInputLayer"
            canvasItem: root.canvasItem
            viewBridge: root.viewStateBridge
            sceneModel: root.visibleBackdropNodesModel
            backdropInputOverlay: true
            onVisibleDelegateCountChanged: root._recordDelegateChurn()
        }

        GraphCanvasDropPreview {
            objectName: "graphCanvasDropPreview"
            canvasItem: root.canvasItem
            viewBridge: root.viewStateBridge
        }

        GraphCanvasWorldLayer {
            id: nodeWorldLayer
            objectName: "graphCanvasWorld"
            canvasItem: root.canvasItem
            viewBridge: root.viewStateBridge
            sceneModel: root.visibleNodesModel
            onVisibleDelegateCountChanged: root._recordDelegateChurn()
        }
    }

    function hostForNodeId(nodeId) {
        root._forceExactVisibleSceneModels();
        var host = nodeWorldLayer.hostForNodeId(nodeId);
        if (host)
            return host;
        return backdropLayer.hostForNodeId(nodeId);
    }

    function showNodeLinkHoverCard(nodeId, linkId, sceneX, sceneY) {
        return nodeLinkHoverLayer.showNodeLinkCard(nodeId, linkId, sceneX, sceneY);
    }

    function openNodeLinkEditor(nodeData, workspaceId) {
        return nodeLinkHoverLayer.openEditor(nodeData, workspaceId);
    }

    function applyNodeLinkTargetPick(kind, workspaceId, nodeId, label, subtitle) {
        return nodeLinkHoverLayer.applyPickedTarget(kind, workspaceId, nodeId, label, subtitle);
    }

    function resumeNodeLinkEditorAfterPickCancel() {
        return nodeLinkHoverLayer.resumeAfterPickCancel();
    }

    function abortNodeLinkEditorAfterSourceLoss() {
        return nodeLinkHoverLayer.abortEditor();
    }

    function scheduleNodeLinkHoverDismiss() {
        nodeLinkHoverLayer.scheduleDismiss();
    }

    function openNodeCommentEditor(nodeData, compose) {
        return nodeCommentPopoverLayer.handleBadgeClick(nodeData, Boolean(compose));
    }

    GraphOverlay.GraphSelectionEnvelopeOverlay {
        objectName: "graphSelectionEnvelopeOverlay"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
        sceneStateBridge: root.sceneStateBridge
        canvasActionRouter: root.canvasActionRouter
            || (root.canvasItem && root.canvasItem.canvasActionRouter ? root.canvasItem.canvasActionRouter : null)
        visibleSceneRectPayload: root.canvasItem ? root.canvasItem.visibleSceneRectPayload : ({})
        hostResolver: root.hostForNodeId
        themePalette: root.themePalette
    }

    GraphOverlay.GraphNodeOverlayToolbarLayer {
        objectName: "graphNodeOverlayToolbarLayer"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
        sceneStateBridge: root.sceneStateBridge
        visibleSceneRectPayload: root.canvasItem ? root.canvasItem.visibleSceneRectPayload : ({})
    }

    GraphOverlay.GraphNodeLinkHoverLayer {
        id: nodeLinkHoverLayer
        objectName: "graphNodeLinkHoverLayer"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
        sceneStateBridge: root.sceneStateBridge
        sceneModel: root.visibleNodesModel
        badgeModel: root.visibleBadgeNodesModel
        visibleSceneRectPayload: root.canvasItem ? root.canvasItem.visibleSceneRectPayload : ({})
        hostResolver: root.hostForNodeId
        themePalette: root.nodeLinkHoverPalette
    }

    GraphOverlay.GraphNodeCommentPopoverLayer {
        id: nodeCommentPopoverLayer
        objectName: "graphNodeCommentPopoverLayer"
        canvasItem: root.canvasItem
        viewBridge: root.viewStateBridge
        sceneStateBridge: root.sceneStateBridge
        sceneModel: root.visibleNodesModel
        badgeModel: root.visibleBadgeNodesModel
        visibleSceneRectPayload: root.canvasItem ? root.canvasItem.visibleSceneRectPayload : ({})
        hostResolver: root.hostForNodeId
        themePalette: root.nodeCommentPalette
    }

    GraphOverlay.GraphEdgeFloatingToolbar {
        id: edgeFloatingToolbar
        objectName: "graphEdgeFloatingToolbar"
        anchors.fill: parent
        canvasItem: root.canvasItem
        edgeLayer: edgeLayer
        canvasActionRouter: root.canvasActionRouter
            || (root.canvasItem && root.canvasItem.canvasActionRouter ? root.canvasItem.canvasActionRouter : null)
        viewBridge: root.viewStateBridge
        themePalette: root.themePalette
    }

    Item {
        id: selectedRunPreviewOverlay
        objectName: "selectedRunPreviewOverlay"
        readonly property var executionFactsRef: root.canvasItem ? root.canvasItem.executionFacts : null
        visible: executionFactsRef ? Boolean(executionFactsRef.selectedRunPreviewVisible) : false
        z: 1090
        width: Math.min(maxPanelWidth, Math.max(minPanelWidth, Math.ceil(panelWidthHint)))
        height: selectedRunPreviewPanel.height
        x: Math.max(16, parent.width - width - 16)
        y: 16

        readonly property var rows: executionFactsRef ? executionFactsRef.selectedRunPreviewRows : []
        readonly property int revision: executionFactsRef ? Number(executionFactsRef.selectedRunPreviewRevision || 0) : 0
        property bool expanded: false
        readonly property int previewRowLimit: 8
        readonly property int hiddenRowCount: Math.max(0, rows.length - previewRowLimit)
        readonly property int visibleRowCount: expanded ? rows.length : Math.min(rows.length, previewRowLimit)
        readonly property var visibleRows: rows.slice(0, visibleRowCount)
        readonly property int minPanelWidth: 236
        readonly property int maxPanelWidth: Math.max(minPanelWidth, parent ? parent.width - 32 : minPanelWidth)
        readonly property int maxRowListHeight: 220
        readonly property string titleText: "Selected run preview"
        readonly property string longestRowLabel: _longestRowLabel(rows)
        readonly property string longestSectionLabel: _longestSectionLabel(rows)
        readonly property real actionWidthHint: (78 + 78 + 8 + 20)
        readonly property real panelWidthHint: Math.max(
            selectedRunPreviewTitleMetrics.advanceWidth + 48,
            selectedRunPreviewSectionMetrics.advanceWidth + 20,
            selectedRunPreviewRowMetrics.advanceWidth + 54,
            actionWidthHint
        )

        onVisibleChanged: {
            if (!visible)
                _resetExpanded();
        }

        onRevisionChanged: _resetExpanded()
        onExpandedChanged: {
            if (!expanded && typeof selectedRunPreviewList !== "undefined" && selectedRunPreviewList)
                selectedRunPreviewList.contentY = 0;
        }

        function _token(name, fallback) {
            var palette = root.themePalette || ({});
            if (palette && palette[name] !== undefined)
                return palette[name];
            var bridgePalette = (typeof themeBridge !== "undefined" && themeBridge) ? themeBridge.palette : ({});
            return bridgePalette && bridgePalette[name] !== undefined ? bridgePalette[name] : fallback;
        }

        function _trigger(actionId) {
            var router = root.canvasActionRouter
                || (root.canvasItem && root.canvasItem.canvasActionRouter ? root.canvasItem.canvasActionRouter : null);
            if (router && router.triggerGraphAction)
                router.triggerGraphAction(actionId, {});
        }

        function _rowToneColor(tone) {
            return selectedRunPreviewOverlay._token("accent", "#60CDFF");
        }

        function _wheelDeltaY(wheel) {
            if (!wheel)
                return 0;
            var delta = 0;
            if (wheel.angleDelta && Number(wheel.angleDelta.y) !== 0)
                delta = Number(wheel.angleDelta.y);
            else if (wheel.pixelDelta && Number(wheel.pixelDelta.y) !== 0)
                delta = Number(wheel.pixelDelta.y);
            if (wheel.inverted)
                delta = -delta;
            return delta;
        }

        function _scrollPreviewListByWheel(wheel) {
            if (typeof selectedRunPreviewList === "undefined" || !selectedRunPreviewList)
                return;
            var deltaY = _wheelDeltaY(wheel);
            if (Math.abs(deltaY) < 0.001)
                return;
            var step = (-deltaY / 120.0) * 40.0;
            if (Math.abs(step) < 1.0)
                step = deltaY > 0 ? -24.0 : 24.0;
            var maxContentY = Math.max(0, selectedRunPreviewList.contentHeight - selectedRunPreviewList.height);
            selectedRunPreviewList.contentY = Math.max(
                0,
                Math.min(maxContentY, selectedRunPreviewList.contentY + step)
            );
        }

        function _rowLabel(row) {
            if (!row)
                return "";
            var label = String(row.title || row.node_id || "");
            var detail = String(row.detail || "");
            return detail.length > 0 ? label + " (" + detail + ")" : label;
        }

        function _longestSectionLabel(sourceRows) {
            var longest = "";
            for (var index = 0; index < sourceRows.length; ++index) {
                var section = String(sourceRows[index].section || "");
                if (section.length > longest.length)
                    longest = section;
            }
            return longest;
        }

        function _longestRowLabel(sourceRows) {
            var longest = "";
            for (var index = 0; index < sourceRows.length; ++index) {
                var label = _rowLabel(sourceRows[index]);
                if (label.length > longest.length)
                    longest = label;
            }
            return longest;
        }

        function _resetExpanded() {
            expanded = false;
            if (typeof selectedRunPreviewList !== "undefined" && selectedRunPreviewList)
                selectedRunPreviewList.contentY = 0;
        }

        TextMetrics {
            id: selectedRunPreviewTitleMetrics
            text: selectedRunPreviewOverlay.titleText
            font.pixelSize: 13
            font.bold: true
        }

        TextMetrics {
            id: selectedRunPreviewSectionMetrics
            text: selectedRunPreviewOverlay.longestSectionLabel
            font.pixelSize: 10
            font.bold: true
        }

        TextMetrics {
            id: selectedRunPreviewRowMetrics
            text: selectedRunPreviewOverlay.longestRowLabel
            font.pixelSize: 11
        }

        Rectangle {
            id: selectedRunPreviewPanel
            width: parent.width
            height: Math.min(360, selectedRunPreviewColumn.implicitHeight + 20)
            radius: 8
            color: Qt.alpha(selectedRunPreviewOverlay._token("panel_bg", "#1b1d22"), 0.96)
            border.width: 1
            border.color: Qt.alpha(selectedRunPreviewOverlay._token("border", "#3a3d45"), 0.9)

            Column {
                id: selectedRunPreviewColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 10
                spacing: 7

                Row {
                    width: parent.width
                    height: 22
                    spacing: 8

                    Rectangle {
                        width: 4
                        height: 18
                        radius: 2
                        anchors.verticalCenter: parent.verticalCenter
                        color: selectedRunPreviewOverlay._token("accent", "#60CDFF")
                    }

                    Text {
                        width: parent.width - 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: selectedRunPreviewOverlay.titleText
                        color: selectedRunPreviewOverlay._token("panel_title_fg", "#f0f4fb")
                        font.pixelSize: 13
                        font.bold: true
                        elide: Text.ElideRight
                        renderType: Text.CurveRendering
                    }
                }

                Item {
                    id: selectedRunPreviewListFrame
                    objectName: "selectedRunPreviewListFrame"
                    width: parent.width
                    height: Math.min(
                        selectedRunPreviewRowsColumn.implicitHeight,
                        selectedRunPreviewOverlay.expanded
                            ? selectedRunPreviewOverlay.maxRowListHeight
                            : selectedRunPreviewRowsColumn.implicitHeight
                    )
                    clip: true

                    Flickable {
                        id: selectedRunPreviewList
                        objectName: "selectedRunPreviewList"
                        anchors.fill: parent
                        clip: true
                        contentWidth: width
                        contentHeight: selectedRunPreviewRowsColumn.implicitHeight
                        boundsBehavior: Flickable.StopAtBounds
                        flickableDirection: Flickable.VerticalFlick
                        interactive: contentHeight > height + 1

                        Column {
                            id: selectedRunPreviewRowsColumn
                            width: selectedRunPreviewList.width
                            spacing: 7

                            Repeater {
                                model: selectedRunPreviewOverlay.visibleRows

                                delegate: Column {
                                    width: selectedRunPreviewRowsColumn.width
                                    spacing: 3
                                    readonly property string section: String(modelData.section || "")
                                    readonly property string previousSection: index > 0
                                        ? String(selectedRunPreviewOverlay.visibleRows[index - 1].section || "")
                                        : ""

                                    Text {
                                        visible: parent.section.length > 0 && parent.section !== parent.previousSection
                                        height: visible ? 14 : 0
                                        text: parent.section
                                        color: selectedRunPreviewOverlay._token("muted_fg", "#b8c0cf")
                                        font.pixelSize: 10
                                        font.bold: true
                                        renderType: Text.CurveRendering
                                    }

                                    Row {
                                        width: parent.width
                                        height: 18
                                        spacing: 7

                                        Rectangle {
                                            width: 7
                                            height: 7
                                            radius: 4
                                            anchors.verticalCenter: parent.verticalCenter
                                            color: selectedRunPreviewOverlay._rowToneColor(modelData.tone)
                                        }

                                        Text {
                                            objectName: "selectedRunPreviewRowLabel"
                                            width: parent.width - 14
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: selectedRunPreviewOverlay._rowLabel(modelData)
                                            color: selectedRunPreviewOverlay._token("panel_fg", "#dfe6f2")
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                            renderType: Text.CurveRendering
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        anchors.rightMargin: 1
                        width: 3
                        radius: 2
                        visible: selectedRunPreviewList.contentHeight > selectedRunPreviewList.height + 1
                        color: Qt.alpha(selectedRunPreviewOverlay._token("border", "#3a3d45"), 0.35)

                        Rectangle {
                            id: selectedRunPreviewScrollThumb
                            width: parent.width
                            radius: parent.radius
                            height: Math.max(
                                24,
                                parent.height * selectedRunPreviewList.height
                                    / Math.max(selectedRunPreviewList.contentHeight, 1)
                            )
                            y: Math.min(
                                parent.height - selectedRunPreviewScrollThumb.height,
                                Math.max(0, selectedRunPreviewList.visibleArea.yPosition * parent.height)
                            )
                            color: Qt.alpha(selectedRunPreviewOverlay._token("accent", "#60CDFF"), 0.65)
                        }
                    }
                }

                Item {
                    objectName: "selectedRunPreviewMoreToggle"
                    visible: selectedRunPreviewOverlay.hiddenRowCount > 0
                    width: parent.width
                    height: visible ? 16 : 0

                    Text {
                        id: selectedRunPreviewMoreText
                        objectName: "selectedRunPreviewMoreText"
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        text: selectedRunPreviewOverlay.expanded
                            ? "Show fewer"
                            : "+" + selectedRunPreviewOverlay.hiddenRowCount + " more"
                        color: selectedRunPreviewMoreMouse.containsMouse
                            ? selectedRunPreviewOverlay._token("accent", "#60CDFF")
                            : selectedRunPreviewOverlay._token("muted_fg", "#b8c0cf")
                        font.pixelSize: 10
                        font.underline: selectedRunPreviewMoreMouse.containsMouse
                        renderType: Text.CurveRendering
                    }

                    MouseArea {
                        id: selectedRunPreviewMoreMouse
                        objectName: "selectedRunPreviewMoreMouse"
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: selectedRunPreviewOverlay.expanded = !selectedRunPreviewOverlay.expanded
                    }
                }

                Row {
                    width: parent.width
                    height: 28
                    spacing: 8

                    PreviewActionButton {
                        label: "Run"
                        enabled: true
                        primary: true
                        onClicked: selectedRunPreviewOverlay._trigger("confirm_selected_run_preview")
                    }

                    PreviewActionButton {
                        label: "Cancel"
                        enabled: true
                        primary: false
                        onClicked: selectedRunPreviewOverlay._trigger("clear_selected_run_preview")
                    }
                }
            }

            MouseArea {
                objectName: "selectedRunPreviewWheelBlocker"
                anchors.fill: parent
                acceptedButtons: Qt.NoButton
                propagateComposedEvents: true
                onWheel: function(wheel) {
                    selectedRunPreviewOverlay._scrollPreviewListByWheel(wheel);
                    wheel.accepted = true;
                }
            }
        }

        component PreviewActionButton: Item {
            property string label: ""
            property bool enabled: true
            property bool primary: false
            signal clicked()

            width: Math.max(78, labelText.implicitWidth + 24)
            height: 26
            opacity: enabled ? 1.0 : 0.45

            Rectangle {
                anchors.fill: parent
                radius: 6
                color: parent.primary
                    ? selectedRunPreviewOverlay._token("accent", "#60CDFF")
                    : "transparent"
                border.width: parent.primary ? 0 : 1
                border.color: Qt.alpha(selectedRunPreviewOverlay._token("border", "#3a3d45"), 0.9)
            }

            Text {
                id: labelText
                anchors.centerIn: parent
                text: parent.label
                color: parent.primary ? "#081018" : selectedRunPreviewOverlay._token("panel_title_fg", "#f0f4fb")
                font.pixelSize: 11
                font.bold: parent.primary
                renderType: Text.CurveRendering
            }

            MouseArea {
                anchors.fill: parent
                enabled: parent.enabled
                hoverEnabled: true
                cursorShape: parent.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: parent.clicked()
            }
        }
    }

    Item {
        id: webPageAddressOverlayLayer
        objectName: "webPageAddressOverlayLayer"
        anchors.fill: parent
        visible: root.webPageAddressOverlayOpen
        z: 1100

        MouseArea {
            anchors.fill: parent
            enabled: root.webPageAddressOverlayOpen
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onPressed: function(mouse) {
                mouse.accepted = true;
            }
            onReleased: function(mouse) {
                root._cancelWebPageAddressOverlay();
                mouse.accepted = true;
            }
            onCanceled: function() {
                root._cancelWebPageAddressOverlay();
            }
        }

        WebComponents.WebPageAddressPopover {
            id: webPageAddressPopover
            themePalette: root.webPageAddressEditorSurface
                ? root.webPageAddressEditorSurface.effectiveThemePalette
                : root.themePalette
            shadowStrength: root.webPageAddressEditorHost
                ? Number(root.webPageAddressEditorHost.shadowStrength || 55)
                : 55
            shadowSoftness: root.webPageAddressEditorHost
                ? Number(root.webPageAddressEditorHost.shadowSoftness || 50)
                : 50
            shadowOffset: root.webPageAddressEditorHost
                ? Number(root.webPageAddressEditorHost.shadowOffset || 4)
                : 4
            width: Math.min(520, Math.max(320, webPageAddressOverlayLayer.width - 32))
            height: implicitHeight
            z: 1
            x: root._clampAddressOverlayX(webPageAddressOverlayLayer.width * 0.5 - width * 0.5, width)
            y: root._quickWindowAddressOverlayY(height)
            onAccepted: function(location) {
                if (root.webPageAddressEditorSurface && root.webPageAddressEditorSurface.acceptAddressEdit)
                    root.webPageAddressEditorSurface.acceptAddressEdit(location);
            }
            onCanceled: function() {
                if (root.webPageAddressEditorSurface && root.webPageAddressEditorSurface.cancelAddressEdit)
                    root.webPageAddressEditorSurface.cancelAddressEdit();
            }
        }
    }

    Item {
        id: timestampOverlayLayer
        objectName: "graphNodeTimestampOverlayLayer"
        anchors.fill: parent
        visible: root.timestampOverlayOpen
        z: 1100

        MouseArea {
            anchors.fill: parent
            enabled: root.timestampOverlayOpen
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onPressed: function(mouse) {
                mouse.accepted = true;
            }
            onReleased: function(mouse) {
                root._cancelTimestampOverlay();
                mouse.accepted = true;
            }
            onCanceled: function() {
                root._cancelTimestampOverlay();
            }
        }

        GraphPassive.GraphTimestampDateTimePopover {
            id: timestampDateTimePopover
            host: root.timestampEditorHost
            themePalette: root.themePalette
            shadowStrength: root.timestampEditorHost
                ? Number(root.timestampEditorHost.shadowStrength || 55)
                : 55
            shadowSoftness: root.timestampEditorHost
                ? Number(root.timestampEditorHost.shadowSoftness || 50)
                : 50
            shadowOffset: root.timestampEditorHost
                ? Number(root.timestampEditorHost.shadowOffset || 4)
                : 4
            width: root._timestampSheetWidth()
            height: implicitHeight
            z: 1
            x: root._timestampSheetX(width)
            y: root._timestampSheetY(height)
            onAccepted: function(timestamp) {
                if (root.timestampEditorSurface && root.timestampEditorSurface.acceptTimestampManualEdit)
                    root.timestampEditorSurface.acceptTimestampManualEdit(timestamp);
            }
            onCanceled: function() {
                if (root.timestampEditorSurface && root.timestampEditorSurface.cancelTimestampManualEdit)
                    root.timestampEditorSurface.cancelTimestampManualEdit();
            }
        }
    }

    Item {
        id: numberSliderOverlayLayer
        objectName: "graphNumberSliderOverlayLayer"
        anchors.fill: parent
        visible: root.numberSliderOverlayOpen
        z: 1100

        MouseArea {
            anchors.fill: parent
            enabled: root.numberSliderOverlayOpen
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onPressed: function(mouse) {
                mouse.accepted = true;
            }
            onReleased: function(mouse) {
                root._cancelNumberSliderOverlay();
                mouse.accepted = true;
            }
            onCanceled: function() {
                root._cancelNumberSliderOverlay();
            }
        }

        GraphPassive.GraphNumberSliderSettingsPopover {
            id: numberSliderSettingsPopover
            host: root.numberSliderEditorHost
            themePalette: root.themePalette
            shadowStrength: root.numberSliderEditorHost
                ? Number(root.numberSliderEditorHost.shadowStrength || 55)
                : 55
            shadowSoftness: root.numberSliderEditorHost
                ? Number(root.numberSliderEditorHost.shadowSoftness || 50)
                : 50
            shadowOffset: root.numberSliderEditorHost
                ? Number(root.numberSliderEditorHost.shadowOffset || 4)
                : 4
            width: root._numberSliderSheetWidth()
            height: implicitHeight
            z: 1
            x: root._numberSliderSheetX(width)
            y: root._numberSliderSheetY(height)
            onAccepted: function(payload) {
                if (root.numberSliderEditorSurface && root.numberSliderEditorSurface.acceptSliderSettings)
                    root.numberSliderEditorSurface.acceptSliderSettings(payload);
            }
            onCanceled: function() {
                if (root.numberSliderEditorSurface && root.numberSliderEditorSurface.cancelSliderSettings)
                    root.numberSliderEditorSurface.cancelSliderSettings();
            }
        }
    }

    Item {
        id: selectOverlayLayer
        objectName: "graphSelectOverlayLayer"
        anchors.fill: parent
        visible: root.selectOverlayOpen
        z: 1100

        MouseArea {
            anchors.fill: parent
            enabled: root.selectOverlayOpen
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onPressed: function(mouse) {
                mouse.accepted = true;
            }
            onReleased: function(mouse) {
                root._cancelSelectOverlay();
                mouse.accepted = true;
            }
            onCanceled: function() {
                root._cancelSelectOverlay();
            }
        }

        GraphPassive.GraphSelectSettingsPopover {
            id: selectSettingsPopover
            host: root.selectEditorHost
            themePalette: root.themePalette
            shadowStrength: root.selectEditorHost
                ? Number(root.selectEditorHost.shadowStrength || 55)
                : 55
            shadowSoftness: root.selectEditorHost
                ? Number(root.selectEditorHost.shadowSoftness || 50)
                : 50
            shadowOffset: root.selectEditorHost
                ? Number(root.selectEditorHost.shadowOffset || 4)
                : 4
            width: root._selectSheetWidth()
            height: implicitHeight
            z: 1
            x: root._selectSheetX(width)
            y: root._selectSheetY(height)
            onAccepted: function(payload) {
                if (root.selectEditorSurface && root.selectEditorSurface.acceptSelectSettings)
                    root.selectEditorSurface.acceptSelectSettings(payload);
            }
            onCanceled: function() {
                if (root.selectEditorSurface && root.selectEditorSurface.cancelSelectSettings)
                    root.selectEditorSurface.cancelSelectSettings();
            }
        }
    }

    Item {
        id: panelOverlayLayer
        objectName: "graphPanelOverlayLayer"
        anchors.fill: parent
        visible: root.panelOverlayOpen
        z: 1100

        MouseArea {
            anchors.fill: parent
            enabled: root.panelOverlayOpen
            acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
            onPressed: function(mouse) {
                mouse.accepted = true;
            }
            onReleased: function(mouse) {
                root._cancelPanelOverlay();
                mouse.accepted = true;
            }
            onCanceled: function() {
                root._cancelPanelOverlay();
            }
        }

        GraphPassive.GraphPanelEditorPopover {
            id: panelEditorPopover
            host: root.panelEditorHost
            themePalette: root.themePalette
            shadowStrength: root.panelEditorHost
                ? Number(root.panelEditorHost.shadowStrength || 55)
                : 55
            shadowSoftness: root.panelEditorHost
                ? Number(root.panelEditorHost.shadowSoftness || 50)
                : 50
            shadowOffset: root.panelEditorHost
                ? Number(root.panelEditorHost.shadowOffset || 4)
                : 4
            width: root._panelSheetWidth()
            height: implicitHeight
            z: 1
            x: root._panelSheetX(width)
            y: root._panelSheetY(height)
            onAccepted: function(payload) {
                if (root.panelEditorSurface && root.panelEditorSurface.acceptPanelSettings)
                    root.panelEditorSurface.acceptPanelSettings(payload);
            }
            onCanceled: function() {
                if (root.panelEditorSurface && root.panelEditorSurface.cancelPanelSettings)
                    root.panelEditorSurface.cancelPanelSettings();
            }
        }
    }

    GraphCanvasMinimapOverlay {
        objectName: "graphCanvasMinimapOverlay"
        canvasItem: root.canvasItem
        sceneStateBridge: root.sceneStateBridge
        viewStateBridge: root.viewStateBridge
        viewCommandBridge: root.viewCommandBridge
        tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "graph.minimap.expand")
    }
}
