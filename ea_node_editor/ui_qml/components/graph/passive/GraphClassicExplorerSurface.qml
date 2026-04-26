import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../surface_controls" as SurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry

Item {
    id: root
    objectName: "graphClassicExplorerSurface"
    property Item host: null
    property string activePath: _propertyString("current_path")
    property string searchText: ""
    property string sortKey: "name"
    property bool sortReverse: false
    property int selectedIndex: -1
    property int contextEntryIndex: -1
    property bool maximized: false
    property var navigationHistory: []
    property int navigationHistoryIndex: -1
    property var listingPayload: ({
        "directory_path": activePath,
        "parent_path": "",
        "breadcrumbs": _fallbackBreadcrumbs(activePath),
        "entries": [],
        "sort_key": sortKey,
        "reverse": sortReverse,
        "filter_text": searchText
    })
    property var lastActionResult: ({})
    property var lastDragPayload: ({})
    property string statusMessage: ""

    readonly property bool blocksHostInteraction: rowContextMenu.visible
    readonly property string nodeId: host && host.nodeData ? String(host.nodeData.node_id || "") : ""
    readonly property string currentPath: _propertyString("current_path")
    readonly property var entries: Array.isArray(listingPayload.entries) ? listingPayload.entries : []
    readonly property var breadcrumbs: {
        var crumbs = listingPayload && Array.isArray(listingPayload.breadcrumbs)
            ? listingPayload.breadcrumbs
            : [];
        return crumbs.length > 0 ? crumbs : _fallbackBreadcrumbs(activePath);
    }
    readonly property string parentPath: String(listingPayload && listingPayload.parent_path || "")
    readonly property string displayedFolderName: _displayNameForPath(activePath)
    readonly property real panelLeft: Math.max(6.0, Number(host && host.surfaceMetrics ? host.surfaceMetrics.body_left_margin || 8.0 : 8.0))
    readonly property real panelRight: Math.max(6.0, Number(host && host.surfaceMetrics ? host.surfaceMetrics.body_right_margin || 8.0 : 8.0))
    readonly property real panelTop: Math.max(30.0, Number(host && host.surfaceMetrics ? host.surfaceMetrics.body_top || 30.0 : 30.0))
    readonly property real panelBottom: Math.max(6.0, Number(host && host.surfaceMetrics ? host.surfaceMetrics.body_bottom_margin || 8.0 : 8.0))
    readonly property real explorerWidth: Math.max(0.0, width - panelLeft - panelRight)
    readonly property real explorerHeight: Math.max(0.0, height - panelTop - panelBottom)
    readonly property real sideNavWidth: Math.min(122.0, Math.max(92.0, explorerWidth * 0.26))
    readonly property real detailsHeaderHeight: 24.0
    readonly property real rowHeight: 24.0
    readonly property real dateColumnWidth: 104.0
    readonly property real typeColumnWidth: 82.0
    readonly property real sizeColumnWidth: 58.0
    readonly property real rowMenuWidth: 28.0
    readonly property real nameColumnWidth: Math.max(
        96.0,
        detailsPanel.width - dateColumnWidth - typeColumnWidth - sizeColumnWidth - rowMenuWidth - 12.0
    )
    readonly property var _interactiveRectGeometryKey: {
        var total = width + height + selectedIndex + contextEntryIndex;
        total += titleBar.x + titleBar.y + titleBar.width + titleBar.height;
        total += commandBar.x + commandBar.y + commandBar.width + commandBar.height;
        total += breadcrumbRow.x + breadcrumbRow.y + breadcrumbRow.width + breadcrumbRow.height;
        total += sideNavColumn.x + sideNavColumn.y + sideNavColumn.width + sideNavColumn.height;
        total += entryRepeater.count + rowClickTargetRepeater.count;
        for (var index = 0; index < entryRepeater.count; index++) {
            var row = entryRepeater.itemAt(index);
            if (!row)
                continue;
            total += row.x + row.y + row.width + row.height + (row.visible ? 1 : 0);
        }
        return total;
    }
    readonly property var embeddedInteractiveRects: {
        var _geometryKey = root._interactiveRectGeometryKey;
        return root._embeddedInteractiveRects();
    }
    readonly property var surfaceActions: [
        {
            "id": "refresh",
            "label": "Refresh",
            "icon": "refresh",
            "kind": "folder_explorer",
            "enabled": activePath.length > 0,
            "primary": false
        },
        {
            "id": "maximize",
            "label": maximized ? "Restore" : "Maximize",
            "icon": maximized ? "minimize" : "maximize",
            "kind": "folder_explorer",
            "enabled": true,
            "primary": maximized
        }
    ]

    implicitHeight: Math.max(260.0, explorerHeight)
    clip: true

    onCurrentPathChanged: {
        var nextPath = String(currentPath || "");
        if (nextPath === activePath)
            return;
        activePath = nextPath;
        _resetHistory(activePath);
        refreshListing();
    }

    onSortKeyChanged: {
        if (listingPayload && listingPayload.sort_key !== sortKey)
            listingPayload.sort_key = sortKey;
    }

    onSortReverseChanged: {
        if (listingPayload && listingPayload.reverse !== sortReverse)
            listingPayload.reverse = sortReverse;
    }

    Component.onCompleted: {
        _resetHistory(activePath);
        Qt.callLater(refreshListing);
    }

    function dispatchSurfaceAction(actionId) {
        var normalized = String(actionId || "").trim();
        if (normalized === "refresh") {
            refreshListing();
            return true;
        }
        if (normalized === "maximize") {
            toggleMaximized();
            return true;
        }
        return false;
    }

    function _propertyString(key) {
        if (!host || !host.nodeData)
            return "";
        var properties = host.nodeData.properties || ({});
        return String(properties[key] || host.nodeData[key] || "");
    }

    function _clonePayload(payload) {
        var result = {};
        var source = payload || ({});
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key))
                result[key] = source[key];
        }
        return result;
    }

    function _actionRouter() {
        if (!host || !host.canvasItem || !host.canvasItem.canvasActionRouter)
            return null;
        return host.canvasItem.canvasActionRouter;
    }

    function _actionId(command) {
        var router = _actionRouter();
        var normalized = String(command || "").trim();
        if (router && router.folderExplorerActionId) {
            var routed = String(router.folderExplorerActionId(normalized) || "").trim();
            if (routed.length > 0)
                return routed;
        }
        return normalized;
    }

    function _scenePointForCommand() {
        if (!host || !host.nodeData)
            return {"x": 0.0, "y": 0.0};
        return {
            "x": Number(host.nodeData.x || 0.0) + Number(host.width || host.nodeData.width || 0.0) + 24.0,
            "y": Number(host.nodeData.y || 0.0) + 36.0
        };
    }

    function _request(command, payload) {
        var router = _actionRouter();
        var actionId = _actionId(command);
        var requestPayload = _clonePayload(payload);
        if (!requestPayload.path)
            requestPayload.path = activePath;
        requestPayload.node_id = nodeId;
        if (host && nodeId.length > 0)
            host.surfaceControlInteractionStarted(nodeId);
        if (!nodeId.length || !router || !router.requestFolderExplorerAction) {
            lastActionResult = {
                "success": false,
                "cancelled": false,
                "action_id": actionId,
                "node_id": nodeId,
                "path": String(requestPayload.path || ""),
                "error": {
                    "code": "bridge_unavailable",
                    "message": "Folder explorer action router is not available.",
                    "operation": actionId,
                    "path": String(requestPayload.path || ""),
                    "target_path": ""
                }
            };
            statusMessage = String(lastActionResult.error.message || "");
            return lastActionResult;
        }
        lastActionResult = router.requestFolderExplorerAction(actionId, requestPayload);
        if (lastActionResult && lastActionResult.error && String(lastActionResult.error.message || "").length > 0)
            statusMessage = String(lastActionResult.error.message || "");
        else
            statusMessage = "";
        return lastActionResult || ({});
    }

    function _applyListing(payload) {
        var listing = payload || ({});
        var directoryPath = String(listing.directory_path || listing.path || activePath || "");
        listingPayload = {
            "directory_path": directoryPath,
            "parent_path": String(listing.parent_path || ""),
            "breadcrumbs": Array.isArray(listing.breadcrumbs) ? listing.breadcrumbs : _fallbackBreadcrumbs(directoryPath),
            "entries": Array.isArray(listing.entries) ? listing.entries : [],
            "sort_key": String(listing.sort_key || sortKey || "name"),
            "reverse": Boolean(listing.reverse),
            "filter_text": String(listing.filter_text || searchText || "")
        };
        activePath = directoryPath;
        sortKey = String(listingPayload.sort_key || "name");
        sortReverse = Boolean(listingPayload.reverse);
        searchText = String(listingPayload.filter_text || "");
        selectedIndex = -1;
    }

    function _listingFromResult(result) {
        if (!result)
            return null;
        if (result.listing)
            return result.listing;
        if (result.directory_path || result.entries)
            return result;
        return null;
    }

    function refreshListing() {
        if (!activePath.length)
            return false;
        var result = _request("list", {
            "path": activePath,
            "sort_key": sortKey,
            "reverse": sortReverse,
            "filter_text": searchText
        });
        if (result && result.success) {
            var listing = _listingFromResult(result);
            if (listing)
                _applyListing(listing);
            return true;
        }
        return false;
    }

    function navigateTo(path, pushHistory) {
        var targetPath = String(path || "").trim();
        if (!targetPath.length)
            return false;
        var result = _request("navigate", {
            "path": targetPath,
            "sort_key": sortKey,
            "reverse": sortReverse,
            "filter_text": searchText
        });
        if (result && result.success) {
            var listing = _listingFromResult(result);
            if (listing)
                _applyListing(listing);
            else
                activePath = String(result.path || targetPath);
            if (pushHistory !== false)
                _pushHistory(activePath);
            return true;
        }
        return false;
    }

    function navigateBack() {
        if (navigationHistoryIndex <= 0)
            return false;
        navigationHistoryIndex -= 1;
        return navigateTo(String(navigationHistory[navigationHistoryIndex] || ""), false);
    }

    function navigateForward() {
        if (navigationHistoryIndex < 0 || navigationHistoryIndex + 1 >= navigationHistory.length)
            return false;
        navigationHistoryIndex += 1;
        return navigateTo(String(navigationHistory[navigationHistoryIndex] || ""), false);
    }

    function navigateUp() {
        var target = parentPath.length > 0 ? parentPath : _parentPath(activePath);
        return navigateTo(target, true);
    }

    function setSearchText(text) {
        searchText = String(text || "");
        var result = _request("setSearch", {
            "path": activePath,
            "filter_text": searchText,
            "sort_key": sortKey,
            "reverse": sortReverse
        });
        if (result && result.success) {
            var listing = _listingFromResult(result);
            if (listing)
                _applyListing(listing);
            return true;
        }
        return false;
    }

    function setSort(key) {
        var normalized = String(key || "name").trim();
        if (!normalized.length)
            normalized = "name";
        if (sortKey === normalized)
            sortReverse = !sortReverse;
        else {
            sortKey = normalized;
            sortReverse = false;
        }
        var result = _request("setSort", {
            "path": activePath,
            "sort_key": sortKey,
            "reverse": sortReverse,
            "filter_text": searchText
        });
        if (result && result.success) {
            var listing = _listingFromResult(result);
            if (listing)
                _applyListing(listing);
            return true;
        }
        return false;
    }

    function selectEntry(index) {
        var numeric = Number(index);
        if (!isFinite(numeric) || numeric < 0 || numeric >= entries.length) {
            selectedIndex = -1;
            return false;
        }
        selectedIndex = numeric;
        return true;
    }

    function entryAt(index) {
        var numeric = Number(index);
        if (!isFinite(numeric) || numeric < 0 || numeric >= entries.length)
            return null;
        return entries[numeric];
    }

    function openEntry(index) {
        var entry = entryAt(index);
        if (!entry)
            return false;
        if (Boolean(entry.is_folder))
            return navigateTo(String(entry.absolute_path || ""), true);
        return triggerContextAction("open", index, {});
    }

    function triggerContextAction(command, index, extraPayload) {
        var normalized = String(command || "").trim();
        var entry = entryAt(index);
        var payload = _clonePayload(extraPayload);
        var scenePoint = _scenePointForCommand();
        if (!payload.path)
            payload.path = entry ? String(entry.absolute_path || "") : activePath;
        if (normalized === "newFolder" && !payload.name)
            payload.name = "New Folder";
        if (normalized === "rename" && entry && !payload.new_name)
            payload.new_name = String(entry.name || "");
        if ((normalized === "openInNewWindow" || normalized === "sendToCorexPathPointer") && payload.scene_x === undefined) {
            payload.scene_x = scenePoint.x;
            payload.scene_y = scenePoint.y;
        }
        var result = _request(normalized, payload);
        if (result && result.success) {
            var listing = _listingFromResult(result);
            if (listing)
                _applyListing(listing);
            return true;
        }
        return false;
    }

    function dragPayloadForEntry(index) {
        var entry = entryAt(index);
        if (!entry) {
            lastDragPayload = ({});
            return lastDragPayload;
        }
        var path = String(entry.absolute_path || "");
        var canvas = host ? host.canvasItem : null;
        if (canvas && canvas.folderExplorerDragPayload)
            lastDragPayload = canvas.folderExplorerDragPayload(path, Boolean(entry.is_folder));
        else
            lastDragPayload = {
                "action_id": _actionId("sendToCorexPathPointer"),
                "type_id": "io.path_pointer",
                "properties": {
                    "path": path,
                    "mode": Boolean(entry.is_folder) ? "folder" : "file"
                }
            };
        return lastDragPayload;
    }

    function createPathPointerFromEntry(index) {
        var entry = entryAt(index);
        if (!entry)
            return false;
        var scenePoint = _scenePointForCommand();
        return triggerContextAction(
            "sendToCorexPathPointer",
            index,
            {
                "path": String(entry.absolute_path || ""),
                "scene_x": scenePoint.x,
                "scene_y": scenePoint.y
            }
        );
    }

    function closeSurface() {
        if (!host)
            return false;
        host.dispatchNodeAction("delete", {"source": "folder_explorer_surface"});
        return true;
    }

    function toggleMaximized() {
        maximized = !maximized;
        return maximized;
    }

    function _resetHistory(path) {
        var normalized = String(path || "");
        navigationHistory = normalized.length ? [normalized] : [];
        navigationHistoryIndex = navigationHistory.length > 0 ? 0 : -1;
    }

    function _pushHistory(path) {
        var normalized = String(path || "");
        if (!normalized.length)
            return;
        if (navigationHistoryIndex >= 0 && navigationHistory[navigationHistoryIndex] === normalized)
            return;
        var nextHistory = [];
        for (var index = 0; index <= navigationHistoryIndex && index < navigationHistory.length; index++)
            nextHistory.push(navigationHistory[index]);
        nextHistory.push(normalized);
        navigationHistory = nextHistory;
        navigationHistoryIndex = navigationHistory.length - 1;
    }

    function _parentPath(path) {
        var text = String(path || "").replace(/[\\/]+$/, "");
        if (!text.length)
            return "";
        var index = Math.max(text.lastIndexOf("/"), text.lastIndexOf("\\"));
        if (index <= 0)
            return text;
        return text.slice(0, index);
    }

    function _displayNameForPath(path) {
        var text = String(path || "").replace(/[\\/]+$/, "");
        if (!text.length)
            return "Folder Explorer";
        var index = Math.max(text.lastIndexOf("/"), text.lastIndexOf("\\"));
        return index >= 0 ? text.slice(index + 1) || text : text;
    }

    function _fallbackBreadcrumbs(path) {
        var text = String(path || "");
        if (!text.length)
            return [];
        var normalized = text.replace(/\\/g, "/");
        var segments = normalized.split("/");
        var crumbs = [];
        var prefix = "";
        for (var index = 0; index < segments.length; index++) {
            var segment = segments[index];
            if (!segment.length) {
                if (index === 0)
                    prefix = "/";
                continue;
            }
            if (prefix.length === 0)
                prefix = segment;
            else if (prefix === "/")
                prefix += segment;
            else
                prefix += "/" + segment;
            crumbs.push({
                "name": segment,
                "absolute_path": prefix
            });
        }
        if (crumbs.length === 0)
            crumbs.push({"name": text, "absolute_path": text});
        return crumbs;
    }

    function _formatModified(entry) {
        var timestamp = Number(entry && entry.modified_timestamp !== undefined ? entry.modified_timestamp : NaN);
        if (!isFinite(timestamp) || timestamp <= 0)
            return "";
        var date = new Date(timestamp * 1000);
        var month = String(date.getMonth() + 1);
        var day = String(date.getDate());
        var hours = String(date.getHours());
        var minutes = String(date.getMinutes());
        if (month.length < 2)
            month = "0" + month;
        if (day.length < 2)
            day = "0" + day;
        if (hours.length < 2)
            hours = "0" + hours;
        if (minutes.length < 2)
            minutes = "0" + minutes;
        return date.getFullYear() + "-" + month + "-" + day + " " + hours + ":" + minutes;
    }

    function _embeddedInteractiveRects() {
        var rectLists = [
            backButton.embeddedInteractiveRects,
            forwardButton.embeddedInteractiveRects,
            upButton.embeddedInteractiveRects,
            refreshButton.embeddedInteractiveRects,
            newFolderButton.embeddedInteractiveRects,
            maximizeButton.embeddedInteractiveRects,
            closeButton.embeddedInteractiveRects,
            pathEditor.embeddedInteractiveRects,
            searchField.embeddedInteractiveRects,
            currentNavButton.embeddedInteractiveRects,
            parentNavButton.embeddedInteractiveRects,
            rootNavButton.embeddedInteractiveRects,
            nameSortButton.embeddedInteractiveRects,
            dateSortButton.embeddedInteractiveRects,
            typeSortButton.embeddedInteractiveRects,
            sizeSortButton.embeddedInteractiveRects
        ];
        for (var crumbIndex = 0; crumbIndex < breadcrumbRepeater.count; crumbIndex++) {
            var crumb = breadcrumbRepeater.itemAt(crumbIndex);
            if (crumb && crumb.embeddedInteractiveRects)
                rectLists.push(crumb.embeddedInteractiveRects);
        }
        for (var rowIndex = 0; rowIndex < entryRepeater.count; rowIndex++) {
            var row = entryRepeater.itemAt(rowIndex);
            if (row && row.embeddedInteractiveRects)
                rectLists.push(row.embeddedInteractiveRects);
        }
        for (var targetIndex = 0; targetIndex < rowClickTargetRepeater.count; targetIndex++) {
            var target = rowClickTargetRepeater.itemAt(targetIndex);
            if (target && target.embeddedInteractiveRects)
                rectLists.push(target.embeddedInteractiveRects);
        }
        return SurfaceControlGeometry.combineRectLists(rectLists);
    }

    Rectangle {
        id: explorerPanel
        objectName: "graphClassicExplorerPanel"
        x: root.panelLeft
        y: root.panelTop
        width: root.explorerWidth
        height: root.explorerHeight
        radius: 5
        color: "#15181d"
        border.width: 1
        border.color: "#313842"
        clip: true

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                id: titleBar
                objectName: "graphClassicExplorerTitleBar"
                Layout.fillWidth: true
                Layout.preferredHeight: 34
                color: "#1f232b"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 6
                    spacing: 8

                    Text {
                        objectName: "graphClassicExplorerFolderIcon"
                        text: "[ ]"
                        color: "#f2c14e"
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    Text {
                        objectName: "graphClassicExplorerTitleText"
                        Layout.fillWidth: true
                        text: root.displayedFolderName
                        color: "#eef3ff"
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }

                    SurfaceControls.GraphSurfaceButton {
                        id: maximizeButton
                        objectName: "graphClassicExplorerMaximizeButton"
                        host: root.host
                        iconOnly: true
                        text: root.maximized ? "R" : "M"
                        iconName: root.maximized ? "minimize" : "maximize"
                        tooltipText: root.maximized ? "Restore" : "Maximize"
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 24
                        contentHorizontalPadding: 4
                        contentVerticalPadding: 3
                        baseFillColor: "transparent"
                        baseBorderColor: "transparent"
                        onControlStarted: {
                            if (host && root.nodeId.length > 0)
                                host.surfaceControlInteractionStarted(root.nodeId);
                        }
                        onClicked: root.toggleMaximized()
                    }

                    SurfaceControls.GraphSurfaceButton {
                        id: closeButton
                        objectName: "graphClassicExplorerCloseButton"
                        host: root.host
                        iconOnly: true
                        text: "X"
                        iconName: "close"
                        tooltipText: "Close"
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 24
                        contentHorizontalPadding: 4
                        contentVerticalPadding: 3
                        baseFillColor: "transparent"
                        baseBorderColor: "transparent"
                        accentColor: "#ff6b6b"
                        onControlStarted: {
                            if (host && root.nodeId.length > 0)
                                host.surfaceControlInteractionStarted(root.nodeId);
                        }
                        onClicked: root.closeSurface()
                    }
                }
            }

            Rectangle {
                id: commandBar
                objectName: "graphClassicExplorerCommandBar"
                Layout.fillWidth: true
                Layout.preferredHeight: 36
                color: "#191d23"
                border.width: 0

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 6

                    SurfaceControls.GraphSurfaceButton {
                        id: backButton
                        objectName: "graphClassicExplorerBackButton"
                        host: root.host
                        iconOnly: true
                        text: "<"
                        iconName: "arrow-left"
                        tooltipText: "Back"
                        enabled: root.navigationHistoryIndex > 0
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 24
                        onClicked: root.navigateBack()
                    }

                    SurfaceControls.GraphSurfaceButton {
                        id: forwardButton
                        objectName: "graphClassicExplorerForwardButton"
                        host: root.host
                        iconOnly: true
                        text: ">"
                        iconName: "arrow-right"
                        tooltipText: "Forward"
                        enabled: root.navigationHistoryIndex >= 0
                            && root.navigationHistoryIndex + 1 < root.navigationHistory.length
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 24
                        onClicked: root.navigateForward()
                    }

                    SurfaceControls.GraphSurfaceButton {
                        id: upButton
                        objectName: "graphClassicExplorerUpButton"
                        host: root.host
                        iconOnly: true
                        text: "^"
                        iconName: "arrow-up"
                        tooltipText: "Up"
                        enabled: root.activePath.length > 0
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 24
                        onClicked: root.navigateUp()
                    }

                    SurfaceControls.GraphSurfaceButton {
                        id: refreshButton
                        objectName: "graphClassicExplorerRefreshButton"
                        host: root.host
                        iconOnly: true
                        text: "R"
                        iconName: "refresh"
                        tooltipText: "Refresh"
                        enabled: root.activePath.length > 0
                        Layout.preferredWidth: 28
                        Layout.preferredHeight: 24
                        onClicked: root.refreshListing()
                    }

                    SurfaceControls.GraphSurfaceButton {
                        id: newFolderButton
                        objectName: "graphClassicExplorerNewFolderButton"
                        host: root.host
                        text: "New"
                        iconName: "folder-plus"
                        tooltipText: "New Folder"
                        enabled: root.activePath.length > 0
                        Layout.preferredWidth: 64
                        Layout.preferredHeight: 24
                        onClicked: root.triggerContextAction("newFolder", -1, {"name": "New Folder"})
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }
            }

            Rectangle {
                id: breadcrumbRow
                objectName: "graphClassicExplorerBreadcrumbRow"
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                color: "#15181d"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 8

                    SurfaceControls.GraphSurfacePathEditor {
                        id: pathEditor
                        objectName: "graphClassicExplorerPathEditor"
                        host: root.host
                        propertyKey: "current_path"
                        committedText: root.activePath
                        fieldObjectName: "graphClassicExplorerPathField"
                        browseButtonObjectName: "graphClassicExplorerPathBrowseButton"
                        browseButtonText: "Browse"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 26
                        browsePathResolver: function(currentPath) {
                            if (!host || !host.browseNodePropertyPath)
                                return "";
                            return host.browseNodePropertyPath("current_path", currentPath);
                        }
                        onControlStarted: {
                            if (host && root.nodeId.length > 0)
                                host.surfaceControlInteractionStarted(root.nodeId);
                        }
                        onCommitRequested: function(value) {
                            root.navigateTo(value, true);
                        }
                    }

                    SurfaceControls.GraphSurfaceTextField {
                        id: searchField
                        objectName: "graphClassicExplorerSearchField"
                        host: root.host
                        placeholderText: "Search"
                        text: root.searchText
                        Layout.preferredWidth: Math.max(84, Math.min(152, root.explorerWidth * 0.28))
                        Layout.preferredHeight: 26
                        onControlStarted: {
                            if (host && root.nodeId.length > 0)
                                host.surfaceControlInteractionStarted(root.nodeId);
                        }
                        onTextEdited: root.searchText = text
                        onAccepted: root.setSearchText(text)
                        onEditingFinished: root.setSearchText(text)
                    }
                }
            }

            RowLayout {
                id: contentRow
                objectName: "graphClassicExplorerContentRow"
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    id: sideNav
                    objectName: "graphClassicExplorerSideNavigation"
                    Layout.preferredWidth: root.sideNavWidth
                    Layout.fillHeight: true
                    color: "#171b21"
                    border.width: 0

                    ColumnLayout {
                        id: sideNavColumn
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 6

                        SurfaceControls.GraphSurfaceButton {
                            id: currentNavButton
                            objectName: "graphClassicExplorerCurrentNavButton"
                            host: root.host
                            text: "Current"
                            iconName: "folder"
                            Layout.fillWidth: true
                            Layout.preferredHeight: 26
                            onClicked: root.navigateTo(root.activePath, true)
                        }

                        SurfaceControls.GraphSurfaceButton {
                            id: parentNavButton
                            objectName: "graphClassicExplorerParentNavButton"
                            host: root.host
                            text: "Parent"
                            iconName: "folder-up"
                            enabled: root.activePath.length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 26
                            onClicked: root.navigateUp()
                        }

                        SurfaceControls.GraphSurfaceButton {
                            id: rootNavButton
                            objectName: "graphClassicExplorerRootNavButton"
                            host: root.host
                            text: "Root"
                            iconName: "hard-drive"
                            enabled: root.breadcrumbs.length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: 26
                            onClicked: {
                                var first = root.breadcrumbs.length > 0 ? root.breadcrumbs[0] : null;
                                if (first)
                                    root.navigateTo(String(first.absolute_path || root.activePath), true);
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 1
                            color: "#303743"
                        }

                        Text {
                            objectName: "graphClassicExplorerBreadcrumbSummary"
                            Layout.fillWidth: true
                            text: root.breadcrumbs.length + " locations"
                            color: "#9aa6b8"
                            font.pixelSize: 10
                            elide: Text.ElideRight
                            renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                        }

                        Item {
                            Layout.fillHeight: true
                        }
                    }
                }

                Rectangle {
                    id: detailsPanel
                    objectName: "graphClassicExplorerDetailsPanel"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#111418"
                    border.width: 0
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        Rectangle {
                            objectName: "graphClassicExplorerBreadcrumbStrip"
                            Layout.fillWidth: true
                            Layout.preferredHeight: 28
                            color: "#161a20"

                            Flickable {
                                anchors.fill: parent
                                anchors.leftMargin: 6
                                anchors.rightMargin: 6
                                contentWidth: breadcrumbButtonRow.implicitWidth
                                contentHeight: height
                                boundsBehavior: Flickable.StopAtBounds
                                interactive: contentWidth > width
                                clip: true

                                Row {
                                    id: breadcrumbButtonRow
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 4

                                    Repeater {
                                        id: breadcrumbRepeater
                                        model: root.breadcrumbs

                                        SurfaceControls.GraphSurfaceButton {
                                            objectName: "graphClassicExplorerBreadcrumbButton"
                                            property string crumbPath: String(modelData.absolute_path || "")
                                            property int crumbIndex: index
                                            host: root.host
                                            text: String(modelData.name || modelData.absolute_path || "")
                                            iconName: index === 0 ? "hard-drive" : "chevron-right"
                                            height: 22
                                            contentHorizontalPadding: 6
                                            contentVerticalPadding: 2
                                            onClicked: root.navigateTo(crumbPath, true)
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            id: detailsHeader
                            objectName: "graphClassicExplorerDetailsHeader"
                            Layout.fillWidth: true
                            Layout.preferredHeight: root.detailsHeaderHeight
                            color: "#1b2028"

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 4
                                spacing: 0

                                SurfaceControls.GraphSurfaceButton {
                                    id: nameSortButton
                                    objectName: "graphClassicExplorerColumnName"
                                    host: root.host
                                    text: "Name"
                                    width: root.nameColumnWidth
                                    height: parent.height
                                    baseFillColor: "transparent"
                                    baseBorderColor: "transparent"
                                    chromeRadius: 0
                                    onClicked: root.setSort("name")
                                }

                                SurfaceControls.GraphSurfaceButton {
                                    id: dateSortButton
                                    objectName: "graphClassicExplorerColumnDateModified"
                                    host: root.host
                                    text: "Date modified"
                                    width: root.dateColumnWidth
                                    height: parent.height
                                    baseFillColor: "transparent"
                                    baseBorderColor: "transparent"
                                    chromeRadius: 0
                                    onClicked: root.setSort("modified")
                                }

                                SurfaceControls.GraphSurfaceButton {
                                    id: typeSortButton
                                    objectName: "graphClassicExplorerColumnType"
                                    host: root.host
                                    text: "Type"
                                    width: root.typeColumnWidth
                                    height: parent.height
                                    baseFillColor: "transparent"
                                    baseBorderColor: "transparent"
                                    chromeRadius: 0
                                    onClicked: root.setSort("type")
                                }

                                SurfaceControls.GraphSurfaceButton {
                                    id: sizeSortButton
                                    objectName: "graphClassicExplorerColumnSize"
                                    host: root.host
                                    text: "Size"
                                    width: root.sizeColumnWidth
                                    height: parent.height
                                    baseFillColor: "transparent"
                                    baseBorderColor: "transparent"
                                    chromeRadius: 0
                                    onClicked: root.setSort("size")
                                }
                            }
                        }

                        Flickable {
                            id: detailsFlickable
                            objectName: "graphClassicExplorerDetailsList"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            contentWidth: width
                            contentHeight: entriesColumn.implicitHeight
                            boundsBehavior: Flickable.StopAtBounds
                            clip: true

                            Column {
                                id: entriesColumn
                                width: detailsFlickable.width

                                Repeater {
                                    id: entryRepeater
                                    model: root.entries

                                    Rectangle {
                                        id: entryRow
                                        objectName: "graphClassicExplorerDetailsRow"
                                        property int entryIndex: index
                                        property string entryPath: String(modelData.absolute_path || "")
                                        property bool folderEntry: Boolean(modelData.is_folder)
                                        readonly property var embeddedInteractiveRects: rowMenuButton.embeddedInteractiveRects
                                        width: entriesColumn.width
                                        height: root.rowHeight
                                        color: root.selectedIndex === index
                                            ? "#24344a"
                                            : (index % 2 === 0 ? "#12161b" : "#151a20")
                                        border.width: root.selectedIndex === index ? 1 : 0
                                        border.color: "#5da9ff"

                                        Drag.mimeData: {
                                            var payload = root.dragPayloadForEntry(index);
                                            return {
                                                "application/x-corex-path-pointer": JSON.stringify(payload),
                                                "text/plain": String(modelData.absolute_path || "")
                                            };
                                        }

                                        Row {
                                            anchors.fill: parent
                                            anchors.leftMargin: 8
                                            anchors.rightMargin: 4
                                            spacing: 0

                                            Text {
                                                objectName: "graphClassicExplorerRowName"
                                                property int entryIndex: index
                                                width: root.nameColumnWidth
                                                height: parent.height
                                                verticalAlignment: Text.AlignVCenter
                                                text: (modelData.is_folder ? "[ ] " : "    ") + String(modelData.name || "")
                                                color: modelData.is_folder ? "#f2c14e" : "#eef3ff"
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                                            }

                                            Text {
                                                objectName: "graphClassicExplorerRowDateModified"
                                                property int entryIndex: index
                                                width: root.dateColumnWidth
                                                height: parent.height
                                                verticalAlignment: Text.AlignVCenter
                                                text: root._formatModified(modelData)
                                                color: "#aeb8ca"
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                                            }

                                            Text {
                                                objectName: "graphClassicExplorerRowType"
                                                property int entryIndex: index
                                                width: root.typeColumnWidth
                                                height: parent.height
                                                verticalAlignment: Text.AlignVCenter
                                                text: String(modelData.type_label || modelData.kind || "")
                                                color: "#aeb8ca"
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                                            }

                                            Text {
                                                objectName: "graphClassicExplorerRowSize"
                                                property int entryIndex: index
                                                width: root.sizeColumnWidth
                                                height: parent.height
                                                verticalAlignment: Text.AlignVCenter
                                                horizontalAlignment: Text.AlignRight
                                                text: String(modelData.display_size || "")
                                                color: "#aeb8ca"
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                                renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                                            }

                                            SurfaceControls.GraphSurfaceButton {
                                                id: rowMenuButton
                                                objectName: "graphClassicExplorerRowContextButton"
                                                property int entryIndex: index
                                                host: root.host
                                                text: "..."
                                                tooltipText: "Actions"
                                                width: root.rowMenuWidth
                                                height: parent.height - 4
                                                anchors.verticalCenter: parent.verticalCenter
                                                contentHorizontalPadding: 4
                                                contentVerticalPadding: 2
                                                baseFillColor: "transparent"
                                                baseBorderColor: "transparent"
                                                onClicked: {
                                                    root.contextEntryIndex = index;
                                                    rowContextMenu.popup();
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        objectName: "graphClassicExplorerEmptyState"
                        anchors.centerIn: parent
                        width: Math.max(120, parent.width - 32)
                        visible: root.entries.length === 0
                        text: root.statusMessage.length > 0
                            ? root.statusMessage
                            : (root.activePath.length > 0 ? "No items" : "Choose a folder path")
                        color: "#8e98aa"
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        renderType: host ? host.nodeTextRenderType : Text.CurveRendering
                    }
                }
            }
        }
    }

    Repeater {
        id: rowClickTargetRepeater
        model: entryRepeater.count

        SurfaceControls.GraphSurfaceDoubleClickTarget {
            host: root.host
            targetItem: entryRepeater.itemAt(index)
            enabled: !!targetItem
            onSingleClicked: root.selectEntry(index)
            onDoubleClicked: root.openEntry(index)
        }
    }

    Menu {
        id: rowContextMenu
        objectName: "graphClassicExplorerRowContextMenu"

        MenuItem {
            objectName: "graphClassicExplorerContextOpen"
            text: "Open"
            onTriggered: root.triggerContextAction("open", root.contextEntryIndex, {})
        }

        MenuItem {
            objectName: "graphClassicExplorerContextOpenInNewWindow"
            text: "Open in new window"
            onTriggered: root.triggerContextAction("openInNewWindow", root.contextEntryIndex, {})
        }

        MenuSeparator {}

        MenuItem {
            objectName: "graphClassicExplorerContextCut"
            text: "Cut"
            onTriggered: root.triggerContextAction("cut", root.contextEntryIndex, {})
        }

        MenuItem {
            objectName: "graphClassicExplorerContextCopy"
            text: "Copy"
            onTriggered: root.triggerContextAction("copy", root.contextEntryIndex, {})
        }

        MenuItem {
            objectName: "graphClassicExplorerContextPaste"
            text: "Paste"
            onTriggered: root.triggerContextAction("paste", -1, {"path": root.activePath})
        }

        MenuSeparator {}

        MenuItem {
            objectName: "graphClassicExplorerContextCopyAsPath"
            text: "Copy as path"
            onTriggered: root.triggerContextAction("copyPath", root.contextEntryIndex, {})
        }

        MenuItem {
            objectName: "graphClassicExplorerContextRename"
            text: "Rename"
            onTriggered: root.triggerContextAction("rename", root.contextEntryIndex, {})
        }

        MenuItem {
            objectName: "graphClassicExplorerContextDelete"
            text: "Delete"
            onTriggered: root.triggerContextAction("delete", root.contextEntryIndex, {})
        }

        MenuSeparator {}

        MenuItem {
            objectName: "graphClassicExplorerContextSendToCorexPathPointer"
            text: "Send to COREX as Path Pointer"
            onTriggered: root.createPathPointerFromEntry(root.contextEntryIndex)
        }

        MenuItem {
            objectName: "graphClassicExplorerContextProperties"
            text: "Properties"
            onTriggered: root.triggerContextAction("properties", root.contextEntryIndex, {})
        }
    }
}
