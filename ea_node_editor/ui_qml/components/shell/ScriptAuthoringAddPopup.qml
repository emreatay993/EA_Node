// Purpose: Discover and add ports and all supported controls using explicit native choices.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Popup {
    id: root
    objectName: "scriptAuthoringAddPopup"
    property var pane
    property var editor
    property var choice: ({})
    property var sectionKeys: []
    property string oldSection: ""
    parent: Overlay.overlay
    x: Math.max(0, (parent.width - width) / 2)
    y: Math.max(0, (parent.height - height) / 2)
    width: Math.min(580, parent.width - 24)
    height: Math.min(choice.kind === "section" ? 230 + Math.min(320, (editor ? editor.interface_items.length : 0) * 25) : 650, parent.height - 32)
    modal: true
    padding: 16
    onOpened: { if (!oldSection) choice = ({}); search.text = ""; search.forceActiveFocus(); }
    onClosed: oldSection = ""
    background: Rectangle { color: root.pane.themePalette.panel_bg; border.color: root.pane.themePalette.border; radius: 2 }
    function choose(item) {
        choice = item;
        if (item.kind === "section") {
            oldSection = "";
            nameField.text = "Settings";
            sectionKeys = editor.selected_item.kind && editor.selected_item.kind !== "output" ? [editor.selected_key] : [];
            nameField.forceActiveFocus(); nameField.selectAll();
            return;
        }
        var proposed = item.kind === "list" ? "values" : item.kind;
        var keys = editor.interface_items.map(function(value) { return value.key; });
        var suffix = 1, candidate = proposed;
        while (keys.indexOf(candidate) >= 0) candidate = proposed + suffix++;
        nameField.text = candidate;
        form.load(item.kind, item.initial_fields, "");
        nameField.forceActiveFocus(); nameField.selectAll();
    }
    function openSection(name) {
        oldSection = name;
        open();
        choice = {"kind": "section", "label": "Section", "description": "Choose at least one input or control. Sections can be expanded or collapsed on the node."};
        nameField.text = name || "Settings";
        sectionKeys = [];
        var items = editor.interface_items;
        for (var i = 0; i < items.length; i++) if (items[i].kind !== "output" && (name ? items[i].section === name : items[i].key === editor.selected_key)) sectionKeys = sectionKeys.concat([items[i].key]);
        nameField.forceActiveFocus(); nameField.selectAll();
    }
    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            Text { Layout.fillWidth: true; text: root.choice.kind ? "Add " + root.choice.label : "Add to your interface"; color: root.pane.themePalette.panel_title_fg; font.pixelSize: 16; font.bold: true }
            ScriptAuthoringButton { tooltipCategory: "general"; visible: !!root.choice.kind; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: "Back"; onClicked: root.choice = ({}) }
        }
        ScriptAuthoringTextField {
            id: search
            objectName: "scriptAddSearch"
            pane: root.pane
            visible: !root.choice.kind
            Layout.fillWidth: true
            placeholderText: "Search inputs, outputs, sliders, color…"
        }
        ListView {
            id: palette
            visible: !root.choice.kind
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 1
            model: root.editor ? root.editor.query_decorators(search.text) : []
            ScrollBar.vertical: ScrollBar {}
            Keys.onReturnPressed: if (currentItem) currentItem.choose()
            delegate: ItemDelegate {
                objectName: "scriptAddChoice_" + modelData.kind
                width: palette.width
                height: 43
                function choose() { root.choose(modelData); }
                onClicked: choose()
                highlighted: ListView.isCurrentItem
                background: Rectangle { color: parent.hovered || parent.highlighted ? root.pane.selectedSurfaceColor : "transparent" }
                contentItem: RowLayout {
                    spacing: 10
                    Image { Layout.preferredWidth: 20; Layout.preferredHeight: 20; source: root.pane.uiIconsRef ? root.pane.uiIconsRef.sourceSized(root.pane.controlIcon(modelData.kind), 20, String(root.pane.themePalette.input_fg)) : "" }
                    Text { Layout.preferredWidth: 104; text: modelData.label; color: root.pane.themePalette.input_fg; font.weight: Font.DemiBold; font.pixelSize: 12 }
                    Text { Layout.fillWidth: true; text: modelData.description; color: root.pane.themePalette.muted_fg; wrapMode: Text.Wrap; font.pixelSize: 11 }
                }
            }
        }
        ScrollView {
            visible: !!root.choice.kind
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: 12
                Text { Layout.fillWidth: true; text: root.choice.description || ""; color: root.pane.themePalette.muted_fg; wrapMode: Text.Wrap }
                Text { text: root.choice.kind === "section" ? "Section name" : root.choice.kind === "output" ? "Output key" : "Python variable name"; color: root.pane.themePalette.input_fg; font.bold: true }
                ScriptAuthoringTextField { id: nameField; objectName: "scriptAddName"; pane: root.pane; Layout.fillWidth: true; placeholderText: "e.g. line_width" }
                ScriptAuthoringForm { id: form; objectName: "scriptAddForm"; visible: root.choice.kind !== "section"; Layout.fillWidth: true; pane: root.pane; editor: root.editor }
                ColumnLayout {
                    visible: root.choice.kind === "section"
                    Layout.fillWidth: true
                    Text { Layout.fillWidth: true; text: "Choose at least one input or control. Outputs stay outside sections."; color: root.pane.themePalette.muted_fg; wrapMode: Text.Wrap }
                    Repeater {
                        model: root.editor ? root.editor.interface_items.filter(function(item) { return item.kind !== "output"; }) : []
                        InspectorCheckBox {
                            pane: root.pane
                            text: modelData.label + " (" + modelData.key + ")"
                            checked: root.sectionKeys.indexOf(modelData.key) >= 0
                            onClicked: root.sectionKeys = checked ? root.sectionKeys.concat([modelData.key]) : root.sectionKeys.filter(function(key) { return key !== modelData.key; })
                        }
                    }
                }
                Text { visible: root.choice.kind === "output"; Layout.fillWidth: true; text: 'Return your calculated value as {"' + nameField.text + '": value}. Calculation code is yours to write.'; color: root.pane.themePalette.muted_fg; wrapMode: Text.Wrap }
            }
        }
        Text { visible: !!root.editor && root.editor.operation_error.length > 0; Layout.fillWidth: true; text: root.editor ? root.editor.operation_error : ""; color: root.pane.themePalette.inspector_danger_fg || "#c04040"; wrapMode: Text.Wrap }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            ScriptAuthoringButton { tooltipCategory: "general"; themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef; text: "Cancel"; onClicked: root.close() }
            ScriptAuthoringButton { tooltipCategory: "general";
                objectName: "scriptAddConfirm"
                themeBridgeRef: root.pane.themeBridgeRef
                graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
                uiIconsRef: root.pane.uiIconsRef
                visible: !!root.choice.kind
                enabled: nameField.text.length > 0 && (root.choice.kind === "section" ? root.sectionKeys.length > 0 : form.hasExplicitType && !form.error)
                selectedStyle: true
                text: root.oldSection ? "Update section" : "Add"
                onClicked: {
                    forceActiveFocus();
                    var success = root.choice.kind === "section"
                        ? root.editor.perform_edit("section", {"name": nameField.text, "keys": root.sectionKeys, "old_name": root.oldSection})
                        : root.editor.perform_edit("add", form.request(nameField.text, true));
                    if (success) root.close();
                }
            }
        }
    }
}
