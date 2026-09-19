// Purpose: Reuse the production node host with an isolated temporary-value facade.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../graph" as Graph

ColumnLayout {
    id: root
    objectName: "scriptAuthoringPreview"
    property var pane
    property var editor
    readonly property var preview: editor ? editor.preview_bridge : null
    readonly property bool ready: editor && editor.analysis_status === "ready" && preview && !!preview.payload.node_id
    readonly property var selected: editor ? editor.selected_item : ({})
    property var graphThemeBridgeRef: null
    property string revealedKey: ""
    spacing: 10
    function bindTheme() { if (preview) preview.set_theme(graphThemeBridgeRef); }
    function controlItem(item, key, point) {
        if (!item || !item.visible) return null;
        if (point && (point.x < 0 || point.y < 0 || point.x > item.width || point.y > item.height)) return null;
        var itemKey = item.propertyKey !== undefined ? String(item.propertyKey)
            : item.propertyData !== undefined && item.propertyData ? String(item.propertyData.key || "") : "";
        if (itemKey && (key === "" || key === itemKey)) return item;
        for (var i = 0; i < item.children.length; i++) {
            var child = item.children[i];
            var childPoint = point ? child.mapFromItem(item, point.x, point.y) : null;
            var found = controlItem(child, key, childPoint);
            if (found) return found;
        }
        return null;
    }
    function revealSelection() {
        if (!ready || !selected.key || revealedKey === selected.key) return;
        var item = controlItem(nodeHost, selected.key, null);
        if (!item) return;
        revealedKey = selected.key;
        var point = item.mapToItem(previewCanvas, 0, 0);
        var flick = previewScroll.contentItem;
        if (flick && point.y + item.height > flick.contentY + previewScroll.availableHeight)
            flick.contentY = Math.min(previewScroll.contentHeight - previewScroll.availableHeight, Math.max(0, point.y + item.height - previewScroll.availableHeight + 14));
        else if (flick && point.y < flick.contentY) flick.contentY = Math.max(0, point.y - 14);
    }
    onPreviewChanged: bindTheme()
    onGraphThemeBridgeRefChanged: bindTheme()
    Component.onCompleted: bindTheme()
    Text { text: "Node preview"; color: root.pane.themePalette.panel_title_fg; font.pixelSize: 13; font.weight: Font.DemiBold }
    Text { Layout.fillWidth: true; text: "Try your interface. Changes here stay in the preview."; color: root.pane.themePalette.muted_fg; font.pixelSize: 12; wrapMode: Text.Wrap }
    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: root.pane.themePalette.console_bg
        border.color: root.pane.themePalette.border
        radius: 2
        clip: true
        Text {
            anchors.centerIn: parent
            width: parent.width - 28
            visible: !root.ready
            text: root.editor && root.editor.analysis_status === "updating" ? "Updating…"
                : root.preview && root.preview.error ? root.preview.error : "Preview unavailable\nFix the highlighted declaration error."
            color: root.pane.themePalette.muted_fg
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
        }
        ScrollView {
            id: previewScroll
            anchors.fill: parent
            visible: root.ready
            clip: true
            contentWidth: Math.max(availableWidth, nodeHost.width + 42)
            contentHeight: nodeHost.height + 48
            Item {
                id: previewCanvas
                objectName: "scriptPreviewCanvas"
                width: Math.max(parent.width, nodeHost.width + 42)
                height: nodeHost.height + 48
                // There is intentionally no live graph command bridge or run action here.
                property var sceneCommandBridge: null
                property var sceneBridge: ({"selected_node_lookup": ({}), "selected_node_ids": []})
                property var viewBridge: ({"zoom_value": 1.0})
                property var executionFacts: ({})
                property var prefs: ({"graphLabelPixelSize": 12, "nodeTitleIconPixelSize": 12})
                property bool interactWithLockedObjects: false
                property var activeToolbarHost: null
                property var wireDragState: null
                function pickNodePropertyColor(nodeId, key, value) { root.editor.select_item(key); return root.editor.choose_color(value); }
                function browseNodePropertyPath(nodeId, key, value) {
                    root.editor.select_item(key);
                    return root.editor.choose_path(value, String(root.editor.selected_item.fields.file_filter || "All files (*)"));
                }
                Graph.GraphNodeHost {
                    id: nodeHost
                    objectName: "scriptPreviewNode"
                    x: Math.max(20, (previewCanvas.width - width) / 2)
                    y: 24
                    nodeData: root.ready ? root.preview.payload : null
                    graphThemeBridgeRef: root.graphThemeBridgeRef
                    canvasItem: previewCanvas
                    settingsGroupAnimationsEnabled: false
                    graphLabelPixelSize: 12
                    onInlinePropertyCommitted: function(nodeId, key, value) { root.preview.set_value(key, value); }
                    onSettingsGroupExpansionRequested: function(nodeId, groupId, expanded) { root.preview.set_group_expanded(groupId, expanded); }
                    onPortClicked: function(nodeId, portKey) { root.editor.select_item(portKey); }
                    PointHandler {
                        acceptedButtons: Qt.LeftButton
                        onActiveChanged: {
                            if (!active) return;
                            var item = root.controlItem(nodeHost, "", point.position);
                            if (item) root.editor.select_item(item.propertyKey !== undefined ? String(item.propertyKey) : String(item.propertyData.key));
                        }
                    }
                }
            }
        }
    }
    Text { Layout.fillWidth: true; visible: root.ready && !!root.selected.key && root.selected.kind !== "input" && root.selected.kind !== "output"; text: root.preview ? root.selected.key + " · Preview: " + JSON.stringify(root.preview.values[root.selected.key]) : ""; color: root.pane.themePalette.input_fg; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
    RowLayout {
        Layout.fillWidth: true
        ScriptAuthoringButton { tooltipCategory: "general";
            objectName: "scriptUsePreviewDefault"
            themeBridgeRef: root.pane.themeBridgeRef
            graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
            uiIconsRef: root.pane.uiIconsRef
            text: "Use as default"
            enabled: root.ready && !!root.selected.key && root.selected.kind !== "input" && root.selected.kind !== "output"
            onClicked: if (root.pane.prepareForm()) root.preview.use_as_default(root.selected.key)
        }
        Item { Layout.fillWidth: true }
        ScriptAuthoringButton { tooltipCategory: "general"; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: "Reset preview"; enabled: root.ready; onClicked: root.preview.reset() }
    }
}
