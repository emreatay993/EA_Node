// Purpose: Navigate and configure source-backed declarations with guided rename review.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: root
    objectName: "scriptInterfacePane"
    property var pane
    property var editor
    property string loadedKey: ""
    property int loadedRevision: -1
    property bool committing: false
    property var collapsedSections: ({})
    readonly property bool pendingEdits: form.hasPendingInput || !!form.error || Object.keys(form.changes).length > 0 || form.omitted.length > 0
    readonly property bool invalidInput: !!form.error
    readonly property bool ownsForm: !!editor && editor.form_owner === root
    function publishFormState() {
        if (!editor || !ownsForm || committing) return;
        editor.store_form_buffer(root, {"source": editor.script_text, "key": loadedKey,
            "values": form.values, "changes": form.changes, "errors": form.errors,
            "omitted": form.omitted, "raw_inputs": form.rawInputs,
            "pending_inputs": form.pendingInputs, "numeric_mode": form.numericMode}, pendingEdits, form.error);
    }
    function activate() {
        if (!editor || !pane.visible) return;
        committing = true;
        var buffer = editor.activate_form(root);
        if (buffer.key) editor.select_item(buffer.key);
        loadedKey = editor.selected_key; loadedRevision = editor.source_revision;
        form.load(selected.kind || "", selected.fields || ({}), selected.data_type || "");
        if (buffer.key && selected.key === buffer.key) {
            form.values = buffer.values || ({}); form.changes = buffer.changes || ({});
            form.errors = buffer.errors || ({}); form.omitted = buffer.omitted || [];
            form.rawInputs = buffer.raw_inputs || ({}); form.pendingInputs = buffer.pending_inputs || ({});
            form.numericMode = buffer.numeric_mode || "decimal";
        }
        committing = false;
        publishFormState();
    }
    onPendingEditsChanged: publishFormState()
    onInvalidInputChanged: publishFormState()
    Component.onDestruction: if (editor) editor.set_form_state(root, false, "")
    readonly property var selected: editor ? editor.selected_item : ({})
    readonly property var kindNames: ({"input":"Input", "output":"Output", "text":"Text", "text_area":"Multiline text", "slider":"Slider", "number":"Number", "switch":"Switch", "dropdown":"Dropdown", "color":"Color", "path":"File path", "interval":"Interval", "list":"List"})
    function outlineItems() {
        var result = [], previousSection = "", items = editor ? editor.interface_items : [];
        for (var i = 0; i < items.length; i++) {
            var item = items[i], section = item.section || "";
            if (section && section !== previousSection) result.push({"is_section": true, "key": "", "label": section, "kind": "section", "section": section});
            if (!section || !collapsedSections[section]) result.push(item);
            previousSection = section;
        }
        return result;
    }
    function typeLabel(typeId) {
        if (typeId === "COREX.DataTypes.Double") return "Decimal";
        if (typeId === "COREX.DataTypes.Int") return "Whole number";
        var types = editor ? editor.query_types("", false, typeId || "") : [];
        for (var i = 0; i < types.length; i++) if (types[i].type_id === typeId) return types[i].label;
        return "";
    }
    spacing: 6
    function reload() {
        if (committing || !ownsForm) return;
        if (!editor || editor.analysis_status === "updating") return;
        if (loadedKey && loadedKey !== editor.selected_key && pendingEdits) {
            var requestedKey = editor.selected_key;
            if (!commitForm()) { editor.select_item(loadedKey); return; }
            if (editor.selected_key !== requestedKey) { editor.select_item(requestedKey); return; }
        }
        if (loadedKey === editor.selected_key && loadedRevision === editor.source_revision) return;
        loadedKey = editor.selected_key; loadedRevision = editor.source_revision;
        form.load(selected.kind || "", selected.fields || ({}), selected.data_type || "");
    }
    function commitForm() {
        if (committing || !loadedKey || !ownsForm) return true;
        if (form.hasPendingInput) { forceActiveFocus(); form.flushPending(); }
        if (form.error) return false;
        if (!Object.keys(form.changes).length && !form.omitted.length) return true;
        committing = true;
        var success = editor.perform_form_edit(form.request(loadedKey, false));
        committing = false;
        if (success) { form.changes = ({}); form.omitted = []; reload(); }
        publishFormState();
        return success;
    }
    function discardPending() { form.load(selected.kind || "", selected.fields || ({}), selected.data_type || ""); publishFormState(); }
    Connections {
        target: root.editor
        function onAuthoring_changed() { root.reload(); }
        function onNode_changed() { root.activate(); }
        function onForm_flush_requested() { if (root.ownsForm && root.pendingEdits) root.commitForm(); }
        function onForm_discard_requested() { if (root.ownsForm) root.discardPending(); }
    }
    Connections { target: root.pane; function onVisibleChanged() { if (root.pane.visible) root.activate(); } }
    Component.onCompleted: activate()
    RowLayout {
        Layout.fillWidth: true
        Text { text: "Interface"; color: root.pane.themePalette.panel_title_fg; font.pixelSize: 13; font.weight: Font.DemiBold }
        Item { Layout.fillWidth: true }
        Text { text: root.editor ? root.editor.interface_items.length + " items" : ""; color: root.pane.themePalette.muted_fg; font.pixelSize: 11 }
    }
    Text { visible: !root.editor || !root.editor.interface_items.length; Layout.fillWidth: true; text: "Use Add to create an input, output, or control. Your Python decorators remain the source of truth."; color: root.pane.themePalette.muted_fg; wrapMode: Text.Wrap }
    ListView {
        id: inventory
        objectName: "scriptInterfaceList"
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(194, Math.max(72, contentHeight))
        clip: true
        spacing: 0
        model: root.outlineItems()
        ScrollBar.vertical: ScrollBar { policy: inventory.contentHeight > inventory.height ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded }
        Keys.onReturnPressed: if (currentItem) root.editor.select_item(currentItem.itemKey)
        delegate: ItemDelegate {
            property string itemKey: modelData.key
            width: inventory.width
            height: 30
            highlighted: !!itemKey && root.editor.selected_key === itemKey
            onClicked: {
                if (modelData.is_section) { var next = Object.assign({}, root.collapsedSections); next[modelData.section] = !next[modelData.section]; root.collapsedSections = next; }
                else root.editor.select_item(itemKey);
            }
            background: Rectangle { color: parent.highlighted ? root.pane.selectedSurfaceColor : parent.hovered ? root.pane.themePalette.hover : "transparent" }
            contentItem: RowLayout {
                spacing: 8
                Image { Layout.preferredWidth: 18; Layout.preferredHeight: 18; source: root.pane.uiIconsRef ? root.pane.uiIconsRef.sourceSized(modelData.is_section ? root.collapsedSections[modelData.section] ? "chevrons-right" : "chevron-down" : root.pane.controlIcon(modelData.kind), 18, String(root.pane.themePalette.input_fg)) : "" }
                Text { Layout.fillWidth: true; text: modelData.label || modelData.key; color: root.pane.themePalette.input_fg; elide: Text.ElideRight; font.pixelSize: 12; font.weight: modelData.is_section ? Font.DemiBold : Font.Normal }
                Text { text: modelData.is_section ? "Section" : root.kindNames[modelData.kind] || modelData.kind; color: root.pane.themePalette.muted_fg; font.pixelSize: 10 }
            }
        }
    }
    Flow {
        Layout.fillWidth: true
        spacing: 4
        visible: !!root.selected.key
        Repeater {
            model: ["↑", "↓", "Duplicate", "Remove"]
            ScriptAuthoringButton { tooltipCategory: "general";
                themeBridgeRef: root.pane.themeBridgeRef
                graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
                uiIconsRef: root.pane.uiIconsRef
                text: ""
                iconName: ["chevron-up", "chevron-down", "duplicate", "delete"][index]
                implicitWidth: 28
                tooltipText: index === 0 ? "Move declaration up" : index === 1 ? "Move declaration down" : modelData
                onClicked: {
                    root.forceActiveFocus();
                    if (!root.commitForm()) return;
                    if (index < 2) {
                        var items = root.editor.interface_items, position = -1;
                        for (var i = 0; i < items.length; i++) if (items[i].key === root.selected.key) position = i;
                        var next = position + (index === 0 ? -1 : 1);
                        if (next >= 0 && next < items.length) root.editor.perform_edit("move", {"key": root.selected.key, "index": next});
                    } else if (index === 2) { duplicateName.text = root.selected.key + "_copy"; duplicatePopup.open(); }
                    else root.editor.perform_edit("remove", {"key": root.selected.key});
                }
            }
        }
    }
    ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 6
            visible: !!root.selected.key
            RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: root.selected.label || root.selected.key || ""; color: root.pane.themePalette.panel_title_fg; font.pixelSize: 16; font.weight: Font.DemiBold; wrapMode: Text.Wrap }
                ScriptAuthoringButton { tooltipCategory: "general"; objectName: "scriptRenameButton"; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: ""; iconName: "edit"; tooltipText: "Rename Python variable"; onClicked: { root.forceActiveFocus(); if (root.commitForm()) { renameName.text = root.selected.key; renamePopup.open(); } } }
            }
            Text { Layout.fillWidth: true; text: (root.kindNames[root.selected.kind] || "") + " · " + root.typeLabel(root.selected.data_type) + " · " + (root.selected.key || ""); color: root.pane.themePalette.muted_fg; font.pixelSize: 11; wrapMode: Text.Wrap }
            Rectangle {
                visible: !!root.selected.has_saved_value && JSON.stringify(root.selected.saved_value) !== JSON.stringify((root.selected.fields || {}).default)
                Layout.fillWidth: true; implicitHeight: savedLabel.implicitHeight + 6
                color: "transparent"
                Text { id: savedLabel; y: 3; width: parent.width; text: "Saved value: " + JSON.stringify(root.selected.saved_value); color: root.pane.themePalette.muted_fg; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
            }
            ScriptAuthoringForm {
                id: form; objectName: "scriptSelectedForm"; Layout.fillWidth: true; pane: root.pane; editor: root.editor; autoCommit: true
                onCommitRequested: root.commitForm()
                onValuesChanged: root.publishFormState()
                onChangesChanged: root.publishFormState()
                onErrorsChanged: root.publishFormState()
                onRawInputsChanged: root.publishFormState()
                onPendingInputsChanged: root.publishFormState()
            }
            Text { Layout.fillWidth: true; visible: root.selected.kind === "output"; text: 'Return key: "' + root.selected.key + '"'; color: root.pane.themePalette.muted_fg; wrapMode: Text.Wrap }
        }
    }
    Text { Layout.fillWidth: true; text: form.error || (root.editor ? root.editor.operation_error : ""); visible: text.length > 0; color: root.pane.themePalette.inspector_danger_fg || "#c04040"; wrapMode: Text.Wrap; font.pixelSize: 11 }
    ScriptAuthoringButton { tooltipCategory: "general";
        objectName: "scriptUpdateDeclaration"
        Layout.fillWidth: true
        visible: !!root.selected.key && (Object.keys(form.changes).length > 0 || form.omitted.length > 0)
        themeBridgeRef: root.pane.themeBridgeRef
        graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
        uiIconsRef: root.pane.uiIconsRef
        text: Object.keys(form.changes).length || form.omitted.length ? "Update draft" : "Changes update the draft"
        selectedStyle: true
        enabled: !form.error && root.editor && root.editor.analysis_status === "ready" && (Object.keys(form.changes).length > 0 || form.omitted.length > 0)
        onClicked: { forceActiveFocus(); root.commitForm(); }
    }
    Text { Layout.fillWidth: true; visible: !!root.selected.key && !Object.keys(form.changes).length && !form.omitted.length; text: "Edits update the draft. Apply to save to the node."; color: root.pane.themePalette.muted_fg; wrapMode: Text.Wrap; font.pixelSize: 11 }
    Popup {
        id: duplicatePopup
        parent: Overlay.overlay
        width: Math.min(400, parent.width - 24); x: (parent.width - width) / 2; y: (parent.height - height) / 2
        modal: true; padding: 16
        background: Rectangle { color: root.pane.themePalette.panel_bg; border.color: root.pane.themePalette.border; radius: 2 }
        contentItem: ColumnLayout {
            Text { text: "Duplicate declaration"; color: root.pane.themePalette.input_fg; font.bold: true }
            ScriptAuthoringTextField { id: duplicateName; pane: root.pane; Layout.fillWidth: true }
            Text { Layout.fillWidth: true; text: root.editor ? root.editor.operation_error : ""; color: root.pane.themePalette.inspector_danger_fg || "#c04040"; wrapMode: Text.Wrap }
            ScriptAuthoringButton { tooltipCategory: "general"; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: "Duplicate"; onClicked: { if (root.editor.perform_edit("duplicate", {"key": root.selected.key, "new_key": duplicateName.text})) duplicatePopup.close(); } }
        }
    }
    Popup {
        id: renamePopup
        objectName: "scriptRenamePopup"
        parent: Overlay.overlay
        width: Math.min(620, parent.width - 24); height: Math.min(540, parent.height - 24)
        x: (parent.width - width) / 2; y: (parent.height - height) / 2
        modal: true; padding: 16
        background: Rectangle { color: root.pane.themePalette.panel_bg; border.color: root.pane.themePalette.border; radius: 2 }
        ColumnLayout {
            anchors.fill: parent
            Text { text: root.selected.kind === "output" ? "Rename output key" : "Rename Python variable"; color: root.pane.themePalette.panel_title_fg; font.pixelSize: 16; font.bold: true }
            Text { Layout.fillWidth: true; text: "Review declaration, parameter, and reference changes. Compatible wires and saved values follow this guided rename when you Apply."; color: root.pane.themePalette.muted_fg; wrapMode: Text.Wrap }
            ScriptAuthoringTextField { id: renameName; objectName: "scriptRenameName"; pane: root.pane; Layout.fillWidth: true }
            ScriptAuthoringButton { tooltipCategory: "general"; objectName: "scriptRenameReviewButton"; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: "Preview rename"; onClicked: root.editor.preview_rename(root.selected.key, renameName.text) }
            Text { Layout.fillWidth: true; text: root.editor ? root.editor.rename_review.error || "" : ""; color: root.pane.themePalette.inspector_danger_fg || "#c04040"; wrapMode: Text.Wrap }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                model: root.editor ? root.editor.rename_review.changes || [] : []
                ScrollBar.vertical: ScrollBar {}
                delegate: Text { width: ListView.view.width; text: "Line " + modelData.line + ":  " + modelData.before + "  →  " + modelData.replacement; color: root.pane.themePalette.input_fg; font.family: "Consolas"; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
            }
            RowLayout {
                Item { Layout.fillWidth: true }
                ScriptAuthoringButton { tooltipCategory: "general"; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: "Cancel"; onClicked: renamePopup.close() }
                ScriptAuthoringButton { tooltipCategory: "general"; objectName: "scriptRenameConfirm"; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: "Rename"; enabled: root.editor && !root.editor.rename_review.error && root.editor.rename_review.new_key === renameName.text && (root.editor.rename_review.changes || []).length > 0; onClicked: if (root.editor.confirm_rename()) renamePopup.close() }
            }
        }
    }
}
