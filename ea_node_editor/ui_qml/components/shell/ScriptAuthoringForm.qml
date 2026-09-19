// Purpose: Configure decorators through native, typed fields instead of Python literals.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common" as Common

ColumnLayout {
    id: root
    property var pane
    property var editor
    property string kind: ""
    property var values: ({})
    property var definitions: []
    property var changes: ({})
    property var omitted: []
    property var pendingInputs: ({})
    property var rawInputs: ({})
    readonly property bool hasPendingInput: Object.keys(pendingInputs).length > 0
    property string numericMode: "decimal"
    property bool advanced: false
    property bool autoCommit: false
    signal commitRequested()
    property var errors: ({})
    readonly property string error: Object.keys(errors).map(function(key) { return errors[key]; }).filter(function(value) { return !!value; }).join("\n")
    readonly property bool hasExplicitType: kind !== "input" && kind !== "output" || !!values.value_type
    spacing: 4
    function load(kindValue, fieldValues, dataType) {
        var oldKind = kind;
        kind = kindValue;
        values = Object.assign({}, fieldValues);
        if (oldKind !== kind || !definitions.length) definitions = editor ? editor.fields_for(kind, values) : [];
        changes = ({}); omitted = []; errors = ({}); pendingInputs = ({}); rawInputs = ({});
        numericMode = String(dataType).indexOf(".Int") >= 0 ? "whole" : "decimal";
    }
    function setField(name, value) {
        var raw = Object.assign({}, rawInputs); delete raw[name]; rawInputs = raw;
        var next = Object.assign({}, values); next[name] = value; values = next;
        var delta = Object.assign({}, changes); delta[name] = value; changes = delta;
        omitted = omitted.filter(function(key) { return key !== name; });
        if (autoCommit) commitTimer.restart();
    }
    function omit(name) {
        var next = Object.assign({}, values); delete next[name]; values = next;
        var delta = Object.assign({}, changes); delete delta[name]; changes = delta;
        if (omitted.indexOf(name) < 0) omitted = omitted.concat([name]);
        setError(name, ""); setError(name + "_lower", ""); setError(name + "_upper", "");
        if (autoCommit) commitTimer.restart();
    }
    function setError(name, message) { var next = Object.assign({}, errors); if (message) next[name] = message; else delete next[name]; errors = next; }
    function markInput(name, text) { var raw = Object.assign({}, rawInputs); raw[name] = text; rawInputs = raw; var next = Object.assign({}, pendingInputs); next[name] = true; pendingInputs = next; }
    function finishInput(name) { var next = Object.assign({}, pendingInputs); delete next[name]; pendingInputs = next; }
    function flushPending() {
        Object.keys(pendingInputs).forEach(function(name) {
            var raw = rawInputs[name];
            var match = /^(.*)_(lower|upper)$/.exec(name);
            if (match) {
                finishInput(name);
                if (!String(raw).trim().length || !isFinite(Number(raw))) { setError(name, "Enter numeric interval bounds."); return; }
                setError(name, "");
                var bounds = (values[match[1]] || [0, 1]).slice(); bounds[match[2] === "lower" ? 0 : 1] = Number(raw);
                setField(match[1], bounds); return;
            }
            var definition = definitions.filter(function(item) { return item.name === name; })[0];
            if (!definition) { finishInput(name); return; }
            if (definition.editor === "number") { numberValue(name, String(raw)); return; }
            if (raw && typeof raw !== "string" && raw.length !== undefined) {
                var numeric = definition.editor === "integer_rows" || definition.editor === "list" && /Int|Double|float|int/.test(String(values.item_type));
                var whole = definition.editor === "integer_rows" || /Int|^int$/.test(String(values.item_type));
                if (numeric && raw.some(function(item) { return !String(item).trim().length || !isFinite(Number(item)) || whole && Number(item) % 1 !== 0; })) {
                    setError(name, whole ? "Each row must be a whole number." : "Each row must be a number."); finishInput(name); return;
                }
                raw = numeric ? raw.map(Number) : raw;
            }
            finishInput(name); setError(name, ""); setField(name, raw);
        });
    }
    Timer { id: commitTimer; interval: 0; onTriggered: if (!root.error) root.commitRequested() }
    function request(key, adding) {
        var result = {"key": key, "fields": adding ? values : changes};
        if (adding) result.kind = kind;
        else result.remove_fields = omitted;
        if (kind === "number" || kind === "slider") result.numeric_mode = numericMode;
        return result;
    }
    function setNumericMode(mode) {
        numericMode = mode;
        ["default", "minimum", "maximum", "step"].forEach(function(name) {
            if (values[name] !== undefined) setField(name, values[name]);
        });
    }
    function numberValue(name, text) {
        finishInput(name);
        var raw = Object.assign({}, rawInputs); raw[name] = text; rawInputs = raw;
        if (!text.trim().length) { omit(name); return; }
        if (!isFinite(Number(text))) { setError(name, "Enter a number for " + name + "."); return; }
        setError(name, ""); setField(name, Number(text));
    }
    RowLayout {
        visible: root.kind === "number" || root.kind === "slider"
        Layout.fillWidth: true
        Text { Layout.preferredWidth: 86; text: "Number type"; color: root.pane.themePalette.input_fg; font.pixelSize: 12 }
        ScriptAuthoringComboBox {
            objectName: "scriptNumericMode"
            pane: root.pane
            Layout.fillWidth: true
            model: ["Decimal", "Whole number"]
            currentIndex: root.numericMode === "whole" ? 1 : 0
            onActivated: root.setNumericMode(index === 1 ? "whole" : "decimal")
        }
    }
    Repeater {
        model: root.definitions
        GridLayout {
            id: field
            columns: 3
            columnSpacing: 6
            rowSpacing: 4
            required property var modelData
            readonly property var definition: modelData
            readonly property string name: definition.name
            readonly property var value: root.values[name]
            readonly property string editorKind: definition.editor
            readonly property var choiceValues: editorKind === "input_key"
                ? root.editor.interface_items.filter(function(item) { return item.kind === "input" && item.data_type === "COREX.DataTypes.Any" && item.data_access === (root.values.structure || "item"); }).map(function(item) { return {"label": item.label + " (" + item.key + ")", "value": item.key}; })
                : name === "default" && root.kind === "dropdown"
                ? (root.values.options || []).map(function(label, i) { return {"label": label, "value": root.values.codes ? root.values.codes[i] : label}; }) : definition.choices
            Layout.fillWidth: true
            visible: name !== "maximum" && (!definition.advanced || root.advanced)
            Text {
                Layout.columnSpan: 3
                Layout.fillWidth: true
                Layout.topMargin: 8
                Layout.bottomMargin: 3
                visible: field.name === "default" || field.name === "minimum" || field.name === "port"
                text: field.name === "default" ? "Value" : field.name === "minimum" ? "Range" : "Connection"
                color: root.pane.themePalette.panel_title_fg; font.pixelSize: 12; font.weight: Font.DemiBold
                Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: Math.max(0, parent.width - 80); height: 1; color: root.pane.themePalette.border }
            }
            Text {
                Layout.preferredWidth: 86
                Layout.alignment: Qt.AlignTop
                Layout.topMargin: 6
                text: field.name === "minimum" ? "Limits" : field.name === "default" ? "Default" : field.name === "port" ? "Input port" : field.definition.label
                color: root.pane.themePalette.input_fg; font.pixelSize: 12; wrapMode: Text.Wrap
                MouseArea { id: fieldHelpHover; anchors.fill: parent; hoverEnabled: true }
                Common.ManagedToolTip { policyBridge: root.pane.graphCanvasStateBridgeRef; category: "general"; active: fieldHelpHover.containsMouse; text: field.definition.help; delay: 300 }
            }
            Loader {
                Layout.fillWidth: true
                sourceComponent: field.name === "minimum" ? rangeField
                    : field.name === "section" ? sectionField
                    : field.editorKind === "type" || field.editorKind === "list_item_type" ? typeField
                    : field.editorKind === "boolean" ? booleanField
                    : field.editorKind === "choice" || field.editorKind === "input_key" ? choiceField
                    : field.editorKind === "color" || field.editorKind === "path" ? pickerField
                    : field.editorKind === "interval" ? intervalField
                    : field.editorKind === "text_rows" || field.editorKind === "integer_rows" || field.editorKind === "list" ? rowsField
                    : field.editorKind === "textarea" ? multilineField : textField
            }
            ScriptAuthoringButton { tooltipCategory: "general";
                enabled: !field.definition.required && field.value !== undefined
                themeBridgeRef: root.pane.themeBridgeRef; graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef; uiIconsRef: root.pane.uiIconsRef
                implicitWidth: 20; implicitHeight: 24
                iconName: "x"; text: ""
                tooltipText: "Restore automatic value"
                onClicked: root.omit(field.name)
            }
            Text { Layout.columnSpan: 3; Layout.fillWidth: true; visible: field.name === "port" || field.name === "structure"; text: field.definition.help; color: root.pane.themePalette.muted_fg; font.pixelSize: 11; wrapMode: Text.Wrap }
            Component {
                id: sectionField
                ScriptAuthoringComboBox {
                    pane: root.pane
                    readonly property var sectionNames: root.editor.sections.map(function(item) { return item.name; })
                    model: ["No section"].concat(sectionNames).concat(["Create section…", "Rename section…"])
                    currentIndex: Math.max(0, sectionNames.indexOf(String(field.value || "")) + 1)
                    onActivated: {
                        if (index === 0) root.omit("section");
                        else if (index <= sectionNames.length) root.setField("section", sectionNames[index - 1]);
                        else root.pane.openSectionEditor(index === sectionNames.length + 1 ? "" : String(field.value || ""));
                    }
                }
            }
            Component {
                id: rangeField
                RowLayout {
                    spacing: 10
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 4
                        Text { text: "Minimum"; color: root.pane.themePalette.muted_fg; font.pixelSize: 11 }
                        ScriptAuthoringTextField { objectName: "scriptField_minimum"; pane: root.pane; Layout.fillWidth: true; text: root.rawInputs.minimum !== undefined ? String(root.rawInputs.minimum) : root.values.minimum === undefined ? "" : String(root.values.minimum); placeholderText: "No minimum"; placeholderTextColor: root.pane.themePalette.muted_fg; font.pixelSize: 12; onTextEdited: root.markInput("minimum", text); onEditingFinished: root.numberValue("minimum", text) }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 4
                        Text { text: "Maximum"; color: root.pane.themePalette.muted_fg; font.pixelSize: 11 }
                        ScriptAuthoringTextField { objectName: "scriptField_maximum"; pane: root.pane; Layout.fillWidth: true; text: root.rawInputs.maximum !== undefined ? String(root.rawInputs.maximum) : root.values.maximum === undefined ? "" : String(root.values.maximum); placeholderText: "No maximum"; placeholderTextColor: root.pane.themePalette.muted_fg; font.pixelSize: 12; onTextEdited: root.markInput("maximum", text); onEditingFinished: root.numberValue("maximum", text) }
                    }
                }
            }
            Component {
                id: pickerField
                RowLayout {
                    ScriptAuthoringTextField {
                        id: pickerText
                        pane: root.pane
                        Layout.fillWidth: true
                        text: field.value === undefined ? "" : String(field.value)
                        onTextEdited: root.markInput(field.name, text)
                        onEditingFinished: { root.finishInput(field.name); root.setField(field.name, text); }
                    }
                    ScriptAuthoringButton { tooltipCategory: "general";
                        themeBridgeRef: root.pane.themeBridgeRef
                        graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
                        uiIconsRef: root.pane.uiIconsRef
                        text: field.editorKind === "color" ? "Choose…" : "Browse…"
                        onClicked: {
                            var value = field.editorKind === "color" ? root.editor.choose_color(pickerText.text)
                                : root.editor.choose_path(pickerText.text, String(root.values.file_filter || "All files (*)"));
                            if (value) root.setField(field.name, value);
                        }
                    }
                }
            }
            Component {
                id: textField
                ScriptAuthoringTextField {
                    objectName: "scriptField_" + field.name
                    pane: root.pane
                    text: root.rawInputs[field.name] !== undefined ? String(root.rawInputs[field.name]) : field.value === undefined || field.value === null ? "" : String(field.value)
                    placeholderText: field.editorKind === "number" ? "Not set" : field.name === "label" ? (field.value === "" ? "Label hidden (empty text)" : "From the Python name") : field.name === "section" ? "No section" : "Optional"
                    placeholderTextColor: root.pane.themePalette.muted_fg
                    font.pixelSize: 12
                    onTextEdited: root.markInput(field.name, text)
                    onEditingFinished: {
                        root.finishInput(field.name);
                        if (field.editorKind === "number") root.numberValue(field.name, text);
                        else root.setField(field.name, text);
                    }
                }
            }
            Component {
                id: multilineField
                TextArea {
                    objectName: "scriptField_" + field.name
                    text: field.value === undefined ? "" : String(field.value)
                    color: root.pane.themePalette.input_fg
                    selectByMouse: true; wrapMode: TextArea.Wrap; implicitHeight: 80
                    background: Rectangle { color: root.pane.themePalette.input_bg; border.color: root.pane.themePalette.input_border; radius: 5 }
                    onTextChanged: if (activeFocus) root.markInput(field.name, text)
                    onActiveFocusChanged: if (!activeFocus) { root.finishInput(field.name); root.setField(field.name, text); }
                }
            }
            Component {
                id: booleanField
                InspectorCheckBox { pane: root.pane; checked: field.value === undefined ? field.name === "required" || field.name === "affects_execution" : Boolean(field.value); text: checked ? "On" : "Off"; onClicked: root.setField(field.name, checked) }
            }
            Component {
                id: typeField
                ScriptAuthoringTypePicker { pane: root.pane; editor: root.editor; value: String(field.value || ""); listItems: field.editorKind === "list_item_type"; onChosen: function(typeId) { root.setField(field.name, typeId); } }
            }
            Component {
                id: choiceField
                ScriptAuthoringComboBox {
                    pane: root.pane
                    model: field.choiceValues.map(function(item) { return item.label; })
                    currentIndex: {
                        var value = field.value === undefined && field.name === "structure" ? "item" : field.value;
                        for (var i = 0; i < field.choiceValues.length; i++) if (field.choiceValues[i].value === value) return i;
                        return -1;
                    }
                    placeholderText: "Choose…"
                    onActivated: root.setField(field.name, field.choiceValues[index].value)
                }
            }
            Component {
                id: intervalField
                ColumnLayout {
                    InspectorCheckBox { pane: root.pane; text: "Automatic interval"; checked: field.value === null; onClicked: { root.setError(field.name + "_lower", ""); root.setError(field.name + "_upper", ""); root.setField(field.name, checked ? null : [0, 1]); } }
                    RowLayout {
                        enabled: field.value !== null
                        ScriptAuthoringTextField { objectName: "scriptIntervalLower"; pane: root.pane; Layout.fillWidth: true; text: root.rawInputs[field.name + "_lower"] !== undefined ? String(root.rawInputs[field.name + "_lower"]) : field.value ? String(field.value[0]) : "0"; placeholderText: "Lower"; onTextEdited: root.markInput(field.name + "_lower", text); onEditingFinished: { root.finishInput(field.name + "_lower"); if (text.trim().length && isFinite(Number(text))) { root.setError(field.name + "_lower", ""); root.setField(field.name, [Number(text), field.value ? field.value[1] : 1]); } else root.setError(field.name + "_lower", "Enter a numeric lower bound."); } }
                        Text { text: "to"; color: root.pane.themePalette.muted_fg }
                        ScriptAuthoringTextField { objectName: "scriptIntervalUpper"; pane: root.pane; Layout.fillWidth: true; text: root.rawInputs[field.name + "_upper"] !== undefined ? String(root.rawInputs[field.name + "_upper"]) : field.value ? String(field.value[1]) : "1"; placeholderText: "Upper"; onTextEdited: root.markInput(field.name + "_upper", text); onEditingFinished: { root.finishInput(field.name + "_upper"); if (text.trim().length && isFinite(Number(text))) { root.setError(field.name + "_upper", ""); root.setField(field.name, [field.value ? field.value[0] : 0, Number(text)]); } else root.setError(field.name + "_upper", "Enter a numeric upper bound."); } }
                    }
                }
            }
            Component {
                id: rowsField
                ScriptAuthoringRows {
                    pane: root.pane
                    values: root.rawInputs[field.name] && root.rawInputs[field.name].length !== undefined ? root.rawInputs[field.name] : field.value && field.value.length !== undefined ? field.value : []
                    numeric: field.editorKind === "integer_rows" || field.editorKind === "list" && /Int|Double|float|int/.test(String(root.values.item_type))
                    whole: field.editorKind === "integer_rows" || /Int|^int$/.test(String(root.values.item_type))
                    onEdited: function(values) { root.finishInput(field.name); root.setField(field.name, values); }
                    onDraftChanged: function(values) { root.markInput(field.name, values); }
                    onErrorChanged: root.setError(field.name, error)
                }
            }
        }
    }
    ScriptAuthoringButton { tooltipCategory: "general";
        themeBridgeRef: root.pane.themeBridgeRef
        graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
        uiIconsRef: root.pane.uiIconsRef
        text: root.advanced ? "Hide advanced settings" : "Advanced settings"
        onClicked: root.advanced = !root.advanced
    }
    Text { Layout.fillWidth: true; visible: text.length > 0; text: root.error; color: root.pane.themePalette.inspector_danger_fg || "#c04040"; wrapMode: Text.Wrap }
}
