// Purpose: Share one responsive builder, code document, and isolated node preview.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py, tests/test_content_fullscreen_bridge.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "MainShellUtils.js" as MainShellUtils

ColumnLayout {
    id: root
    objectName: "scriptCodeEditorPane"
    property var scriptEditorBridgeRef
    property var scriptHighlighterBridgeRef
    property var themeBridgeRef: typeof themeBridge !== "undefined" ? themeBridge : null
    property var graphThemeBridgeRef: null
    property var graphCanvasStateBridgeRef: typeof graphCanvasStateBridge !== "undefined" ? graphCanvasStateBridge : null
    property var uiIconsRef: typeof uiIcons !== "undefined" ? uiIcons : null
    property bool guideButtonVisible: false
    property bool guideButtonSelected: false
    property bool applyFailed: false
    property bool syncingSource: false
    property bool selectingSource: false
    property var completion: ({"items": []})
    readonly property var themePalette: themeBridgeRef ? themeBridgeRef.palette : ({})
    readonly property color selectedSurfaceColor: Qt.alpha(themePalette.accent || "#4488cc", 0.18)
    readonly property color cardBackgroundColor: themePalette.panel_bg || "#eeeeee"
    readonly property bool editorAvailable: !!scriptEditorBridgeRef
    readonly property bool wide: width >= 1200
    readonly property bool narrow: width < 800
    signal guideRequested()
    spacing: 6
    function updateCursorMetrics() {
        if (!editorAvailable) return;
        var before = code.text.slice(0, code.cursorPosition), lines = before.split("\n");
        scriptEditorBridgeRef.set_cursor_metrics(lines.length, lines[lines.length - 1].length + 1, code.cursorPosition, Math.abs(code.selectionStart - code.selectionEnd));
        if (!selectingSource && !syncingSource) scriptEditorBridgeRef.select_source_position(code.cursorPosition);
    }
    function attachSyntaxHighlighter() {
        if (scriptHighlighterBridgeRef && scriptHighlighterBridgeRef.attach_document) scriptHighlighterBridgeRef.attach_document(code.textDocument);
    }
    function showCompletions() {
        if (!editorAvailable || !code.activeFocus) return;
        completion = scriptEditorBridgeRef.query_completions(code.cursorPosition);
        if (!completion.items || !completion.items.length) { completionPopup.close(); return; }
        completionList.currentIndex = 0;
        var rect = code.positionToRectangle(code.cursorPosition);
        var point = code.mapToItem(Overlay.overlay, rect.x, rect.y + rect.height + 4);
        completionPopup.x = Math.max(0, Math.min(point.x, Overlay.overlay.width - completionPopup.width - 8));
        completionPopup.y = Math.max(0, Math.min(point.y, Overlay.overlay.height - completionPopup.height - 8));
        completionPopup.open();
    }
    function acceptCompletion() { var index = completionList.currentIndex; completionPopup.close(); scriptEditorBridgeRef.accept_completion(index); }
    function diagnosticOffset(diagnostic) {
        var lines = code.text.split("\n"), offset = 0;
        for (var i = 0; i < Math.min(lines.length, diagnostic.line - 1); i++) offset += lines[i].length + 1;
        return Math.min(code.length, offset + diagnostic.column - 1);
    }
    function requestApply() {
        if (!prepareForm()) { applyFailed = true; return; }
        var impact = scriptEditorBridgeRef.prepare_apply();
        if (impact.error) { applyFailed = true; return; }
        if ((impact.removed_edge_ids || []).length || (impact.reset_keys || []).length) impactPopup.open();
        else applyFailed = !scriptEditorBridgeRef.apply();
    }
    function prepareForm() { codeHost.forceActiveFocus(); return interfacePane.commitForm(); }
    function openSectionEditor(name) { if (prepareForm()) addPopup.openSection(name); }
    function controlIcon(kind) { return ({"input":"script-input", "output":"script-output", "text":"title", "text_area":"file-text", "slider":"script-slider", "number":"script-number", "switch":"script-switch", "dropdown":"chevron-down", "color":"palette", "path":"folder", "interval":"script-slider", "list":"format-list-bulleted", "section":"hierarchy-2"})[kind] || "code"; }
    onScriptHighlighterBridgeRefChanged: attachSyntaxHighlighter()
    Component.onCompleted: attachSyntaxHighlighter()
    Connections {
        target: root.scriptEditorBridgeRef
        function onContent_changed() {
            root.syncingSource = true;
            if (code.text !== root.scriptEditorBridgeRef.script_text) code.text = root.scriptEditorBridgeRef.script_text;
            root.syncingSource = false;
        }
        function onSelection_range_requested(start, end) { root.selectingSource = true; code.select(end, start); root.selectingSource = false; }
    }
    Timer { id: completionTimer; interval: 120; onTriggered: root.showCompletions() }
    Rectangle {
        Layout.fillWidth: true; Layout.preferredHeight: 40; color: root.themePalette.toolbar_bg
        RowLayout {
            anchors.fill: parent; anchors.margins: 6; spacing: 4
            Text { visible: root.width >= 1000; text: root.editorAvailable ? root.scriptEditorBridgeRef.current_node_label : "Python Script"; color: root.themePalette.panel_title_fg; font.pixelSize: 13; font.weight: Font.DemiBold; Layout.maximumWidth: 220; elide: Text.ElideRight; Layout.rightMargin: 12 }
            ScriptAuthoringButton { tooltipCategory: "general"; objectName: "scriptAddButton"; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: "Add"; iconName: "plus"; tooltipText: "Add input, output or control"; enabled: root.editorAvailable && root.scriptEditorBridgeRef.analysis_status === "ready"; onClicked: if (root.prepareForm()) addPopup.open() }
            Text { Layout.fillWidth: true; visible: root.width >= 450; text: root.editorAvailable ? (root.scriptEditorBridgeRef.analysis_status === "updating" ? "Updating…" : root.scriptEditorBridgeRef.analysis_status === "unavailable" ? "Needs attention" : (root.scriptEditorBridgeRef.dirty || interfacePane.pendingEdits) ? "Draft · not applied" : "Applied") : "Select a Python Script node"; color: root.themePalette.muted_fg; font.pixelSize: 11; elide: Text.ElideRight }
            Item { visible: root.width < 450; Layout.fillWidth: true }
            ScriptAuthoringButton { tooltipCategory: "general"; visible: root.width >= 600; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: ""; iconName: "script-undo"; implicitWidth: 28; tooltipText: "Undo edit (Ctrl+Z)"; enabled: root.editorAvailable && (root.scriptEditorBridgeRef.can_undo || interfacePane.pendingEdits); onClicked: root.scriptEditorBridgeRef.undo() }
            ScriptAuthoringButton { tooltipCategory: "general"; visible: root.width >= 600; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: ""; iconName: "script-redo"; implicitWidth: 28; tooltipText: "Redo edit (Ctrl+Y)"; enabled: root.editorAvailable && root.scriptEditorBridgeRef.can_redo; onClicked: root.scriptEditorBridgeRef.redo() }
            ScriptAuthoringButton { tooltipCategory: "general"; objectName: "pythonScriptGuideButton"; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: ""; iconName: "script-help"; selectedStyle: root.guideButtonSelected; tooltipText: "Python Script customization guide"; onClicked: { if (root.guideButtonVisible) root.guideRequested(); else helpPopup.open(); } }
            ScriptAuthoringButton { tooltipCategory: "general"; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: ""; iconName: "clock-update"; tooltipText: "Revert to applied source"; enabled: root.editorAvailable && (root.scriptEditorBridgeRef.dirty || interfacePane.pendingEdits); onClicked: root.scriptEditorBridgeRef.revert() }
            ScriptAuthoringButton { tooltipCategory: "general"; objectName: "scriptApplyButton"; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: "Apply"; iconName: "check"; selectedStyle: true; implicitWidth: 86; enabled: root.editorAvailable && (root.scriptEditorBridgeRef.dirty || interfacePane.pendingEdits); onClicked: root.requestApply() }
        }
    }
    TabBar {
        id: narrowTabs; objectName: "scriptWorkspaceTabs"; Layout.fillWidth: true; visible: root.narrow; currentIndex: 1; background: Rectangle { color: root.themePalette.panel_bg }
        ScriptAuthoringTab { pane: root; text: "Interface" }
        ScriptAuthoringTab { pane: root; text: "Code" }
        ScriptAuthoringTab { pane: root; text: "Preview" }
    }
    SplitView {
        objectName: "scriptAuthoringSplitView"; Layout.fillWidth: true; Layout.fillHeight: true; orientation: Qt.Horizontal
        handle: Rectangle { implicitWidth: 9; color: SplitHandle.hovered || SplitHandle.pressed ? root.selectedSurfaceColor : "transparent"; Rectangle { anchors.centerIn: parent; width: 1; height: parent.height - 12; color: root.themePalette.border } }
        Item { id: leftHost; visible: root.wide; SplitView.preferredWidth: 340; SplitView.minimumWidth: 260 }
        ColumnLayout {
            id: codeHost; objectName: "scriptCodeHost"; visible: !root.narrow || narrowTabs.currentIndex === 1
            SplitView.fillWidth: true; SplitView.minimumWidth: root.narrow ? 200 : 300; spacing: 4
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Python"; color: root.themePalette.panel_title_fg; font.pixelSize: 13; font.weight: Font.DemiBold }
                Item { Layout.fillWidth: true }
                Text { text: "Ctrl+Space for suggestions"; color: root.themePalette.muted_fg; font.pixelSize: 10 }
            }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 0
                Rectangle {
                    Layout.preferredWidth: 43; Layout.fillHeight: true; color: root.themePalette.console_bg; border.color: root.themePalette.border; clip: true
                    Text { anchors.right: parent.right; anchors.rightMargin: 7; y: (codeScroll.contentItem ? -codeScroll.contentItem.contentY : 0) + 8; text: MainShellUtils.lineNumbersText(code.lineCount); color: root.themePalette.muted_fg; font.family: "Consolas"; font.pixelSize: 13 }
                }
                ScrollView {
                    id: codeScroll; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AsNeeded; ScrollBar.vertical.policy: ScrollBar.AsNeeded
                    TextArea {
                        id: code; objectName: "scriptEditorArea"; width: codeScroll.availableWidth
                        text: root.editorAvailable ? root.scriptEditorBridgeRef.script_text : ""
                        readOnly: !root.editorAvailable || !root.scriptEditorBridgeRef.current_node_id || interfacePane.invalidInput
                        color: root.themePalette.input_fg; font.family: "Consolas"; font.pixelSize: 13
                        wrapMode: TextArea.NoWrap; background: Rectangle { color: root.themePalette.console_bg }
                        selectByMouse: true; persistentSelection: true; padding: 8
                        selectionColor: root.selectedSurfaceColor
                        selectedTextColor: root.themePalette.input_fg
                        Keys.priority: Keys.BeforeItem
                        Keys.onPressed: function(event) {
                            if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_Space) { root.showCompletions(); event.accepted = true; }
                            else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_Z) { (event.modifiers & Qt.ShiftModifier) ? root.scriptEditorBridgeRef.redo() : root.scriptEditorBridgeRef.undo(); event.accepted = true; }
                            else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_Y) { root.scriptEditorBridgeRef.redo(); event.accepted = true; }
                            else if (completionPopup.visible && (event.key === Qt.Key_Return || event.key === Qt.Key_Enter)) { root.acceptCompletion(); event.accepted = true; }
                            else if (completionPopup.visible && event.key === Qt.Key_Down) { completionList.incrementCurrentIndex(); event.accepted = true; }
                            else if (completionPopup.visible && event.key === Qt.Key_Up) { completionList.decrementCurrentIndex(); event.accepted = true; }
                            else if (completionPopup.visible && event.key === Qt.Key_Escape) { completionPopup.close(); event.accepted = true; }
                        }
                        Keys.onTabPressed: function(event) { if (completionPopup.visible) root.acceptCompletion(); else { var position = cursorPosition; insert(position, "    "); cursorPosition = position + 4; } event.accepted = true; }
                        onTextChanged: { if (!root.syncingSource && root.editorAvailable && text !== root.scriptEditorBridgeRef.script_text) { root.scriptEditorBridgeRef.set_script_text(text); completionTimer.restart(); } root.applyFailed = false; root.updateCursorMetrics(); }
                        onCursorPositionChanged: { completionPopup.close(); root.updateCursorMetrics(); }
                        onSelectionStartChanged: completionPopup.close()
                        onSelectionEndChanged: completionPopup.close()
                        onActiveFocusChanged: if (!activeFocus) completionPopup.close()
                        Repeater {
                            model: root.editorAvailable ? root.scriptEditorBridgeRef.diagnostics : []
                            Rectangle { readonly property rect positionRect: code.positionToRectangle(root.diagnosticOffset(modelData)); x: positionRect.x; y: positionRect.y + positionRect.height - 1; width: Math.max(14, Math.min(180, code.width - x)); height: 2; color: root.themePalette.inspector_danger_fg || "#d64c4c" }
                        }
                    }
                }
            }
        }
        ColumnLayout {
            visible: !root.narrow || narrowTabs.currentIndex !== 1
            SplitView.preferredWidth: root.wide ? 325 : 340; SplitView.minimumWidth: root.narrow ? 200 : 280; SplitView.fillWidth: root.narrow; spacing: 8
            TabBar { id: sideTabs; objectName: "scriptSideTabs"; background: Rectangle { color: root.themePalette.panel_bg } visible: !root.wide && !root.narrow; Layout.fillWidth: true; ScriptAuthoringTab { pane: root; text: "Interface" } ScriptAuthoringTab { pane: root; text: "Preview" } }
            Item { id: sideBody; Layout.fillWidth: true; Layout.fillHeight: true }
        }
    }
    ScriptInterfacePane { id: interfacePane; parent: root.wide ? leftHost : sideBody; anchors.fill: parent; anchors.margins: 8; visible: root.wide || (root.narrow ? narrowTabs.currentIndex === 0 : sideTabs.currentIndex === 0); pane: root; editor: root.scriptEditorBridgeRef }
    ScriptAuthoringPreview { parent: sideBody; anchors.fill: parent; anchors.margins: 8; visible: root.wide || (root.narrow ? narrowTabs.currentIndex === 2 : sideTabs.currentIndex === 1); pane: root; editor: root.scriptEditorBridgeRef; graphThemeBridgeRef: root.graphThemeBridgeRef }
    Rectangle {
        Layout.fillWidth: true; Layout.preferredHeight: root.editorAvailable && root.scriptEditorBridgeRef.diagnostics.length ? Math.min(112, 38 + root.scriptEditorBridgeRef.diagnostics.length * 30) : 25
        color: root.themePalette.toolbar_bg
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 4; spacing: 3
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: root.applyFailed ? "Apply failed — review the problem below or Console" : root.editorAvailable && root.scriptEditorBridgeRef.diagnostics.length ? "Problems · " + root.scriptEditorBridgeRef.diagnostics.length : root.editorAvailable ? root.scriptEditorBridgeRef.cursor_label : ""; color: root.applyFailed ? (root.themePalette.inspector_danger_fg || "#c04040") : root.themePalette.muted_fg; font.pixelSize: 11; elide: Text.ElideRight }
                ScriptAuthoringButton { tooltipCategory: "general"; visible: root.editorAvailable && root.scriptEditorBridgeRef.can_synchronize; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: "Synchronize parameters"; onClicked: root.scriptEditorBridgeRef.perform_edit("synchronize_parameters", {}) }
            }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; visible: root.editorAvailable && root.scriptEditorBridgeRef.diagnostics.length > 0; model: root.editorAvailable ? root.scriptEditorBridgeRef.diagnostics : []
                delegate: ItemDelegate { width: ListView.view.width; height: 30; contentItem: Text { text: "Line " + modelData.line + ": " + modelData.message; color: root.themePalette.inspector_danger_fg || "#c04040"; elide: Text.ElideRight; font.pixelSize: 11 } onClicked: { narrowTabs.currentIndex = 1; root.scriptEditorBridgeRef.select_diagnostic(index); code.forceActiveFocus(); } }
            }
        }
    }
    ScriptAuthoringAddPopup { id: addPopup; pane: root; editor: root.scriptEditorBridgeRef }
    Popup {
        id: completionPopup; objectName: "scriptCompletionPopup"; parent: Overlay.overlay
        width: Math.min(460, parent.width - 24); height: Math.min(300, completionList.contentHeight + 10); focus: false; padding: 5
        background: Rectangle { color: root.themePalette.panel_bg; border.color: root.themePalette.accent; radius: 5 }
        contentItem: ListView {
            id: completionList; clip: true; model: root.completion.items || []; ScrollBar.vertical: ScrollBar {}
            delegate: ItemDelegate {
                focusPolicy: Qt.NoFocus
                width: completionList.width; height: 57; highlighted: ListView.isCurrentItem
                background: Rectangle { color: parent.highlighted ? root.selectedSurfaceColor : "transparent" }
                contentItem: ColumnLayout { Text { Layout.fillWidth: true; text: modelData.label; color: root.themePalette.input_fg; font.family: "Consolas"; elide: Text.ElideRight } Text { Layout.fillWidth: true; text: modelData.description || modelData.example || ""; color: root.themePalette.muted_fg; font.pixelSize: 10; elide: Text.ElideRight } }
                onClicked: { completionList.currentIndex = index; root.acceptCompletion(); }
            }
        }
    }
    Popup {
        id: helpPopup; objectName: "scriptHelpPopup"; parent: Overlay.overlay; width: Math.min(650, parent.width - 24); height: Math.min(780, parent.height - 32)
        x: (parent.width - width) / 2; y: (parent.height - height) / 2; modal: true
        contentItem: PythonScriptGuidePane { themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; onCloseRequested: helpPopup.close() }
    }
    Popup {
        id: impactPopup; objectName: "scriptApplyImpactPopup"; parent: Overlay.overlay
        width: Math.min(520, parent.width - 24); x: (parent.width - width) / 2; y: (parent.height - height) / 2; modal: true; padding: 18
        background: Rectangle { color: root.themePalette.panel_bg; border.color: root.themePalette.border; radius: 6 }
        contentItem: ColumnLayout {
            spacing: 12
            Text { text: "Review Apply changes"; color: root.themePalette.panel_title_fg; font.pixelSize: 18; font.bold: true }
            Text { Layout.fillWidth: true; text: root.editorAvailable ? "Connections removed: " + (root.scriptEditorBridgeRef.apply_impact.removed_edge_ids || []).length + "\nSaved values reset: " + ((root.scriptEditorBridgeRef.apply_impact.reset_keys || []).join(", ") || "None") : ""; color: root.themePalette.input_fg; wrapMode: Text.Wrap }
            RowLayout { Item { Layout.fillWidth: true } ScriptAuthoringButton { tooltipCategory: "general"; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: "Cancel"; onClicked: impactPopup.close() } ScriptAuthoringButton { tooltipCategory: "general"; themeBridgeRef: root.themeBridgeRef; graphCanvasStateBridgeRef: root.graphCanvasStateBridgeRef; uiIconsRef: root.uiIconsRef; text: "Apply changes"; onClicked: { root.applyFailed = !root.scriptEditorBridgeRef.apply(); impactPopup.close(); } } }
        }
    }
}
