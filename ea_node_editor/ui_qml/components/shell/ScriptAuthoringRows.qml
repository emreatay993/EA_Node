// Purpose: Edit ordinary option and typed-list values as individual rows.
// Map: subsystems/qml_shell_and_bridges.md
// Tests: tests/test_python_script_authoring_ui.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: root
    property var pane
    property var values: []
    property bool numeric: false
    property bool whole: false
    property bool syncing: false
    property string error: ""
    signal edited(var values)
    signal draftChanged(var values)
    spacing: 4
    function sync() {
        if (rows.count === values.length) {
            var same = true;
            for (var j = 0; j < values.length; j++) if (rows.get(j).textValue !== String(values[j])) same = false;
            if (same) return;
        }
        syncing = true;
        rows.clear();
        for (var i = 0; i < values.length; i++) rows.append({"textValue": String(values[i])});
        syncing = false;
    }
    function publish() {
        var result = [];
        for (var i = 0; i < rows.count; i++) {
            var value = rows.get(i).textValue;
            if (numeric) {
                if (!value.trim().length || !isFinite(Number(value)) || (whole && Number(value) % 1 !== 0)) {
                    error = whole ? "Each row must be a whole number." : "Each row must be a number.";
                    return;
                }
                value = Number(value);
            }
            result.push(value);
        }
        error = "";
        edited(result);
    }
    function rawValues() { var result = []; for (var i = 0; i < rows.count; i++) result.push(rows.get(i).textValue); return result; }
    onValuesChanged: if (!activeFocus && !syncing) sync()
    Component.onCompleted: sync()
    ListModel { id: rows }
    Repeater {
        model: rows
        RowLayout {
            Layout.fillWidth: true
            ScriptAuthoringTextField {
                objectName: "scriptListRow_" + index
                pane: root.pane
                Layout.fillWidth: true
                text: textValue
                placeholderText: "Value " + (index + 1)
                onTextEdited: { rows.setProperty(index, "textValue", text); root.syncing = true; root.draftChanged(root.rawValues()); root.syncing = false; }
                onEditingFinished: root.publish()
            }
            ScriptAuthoringButton { tooltipCategory: "general";
                themeBridgeRef: root.pane.themeBridgeRef
                graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
                uiIconsRef: root.pane.uiIconsRef
                text: "−"
                implicitWidth: 28
                tooltipText: "Remove row"
                onClicked: { rows.remove(index); root.publish(); }
            }
        }
    }
    Text { Layout.fillWidth: true; visible: text.length > 0; text: root.error; color: root.pane.themePalette.inspector_danger_fg || "#c04040"; wrapMode: Text.Wrap; font.pixelSize: 11 }
    ScriptAuthoringButton { tooltipCategory: "general";
        themeBridgeRef: root.pane.themeBridgeRef
        graphCanvasStateBridgeRef: root.pane.graphCanvasStateBridgeRef
        uiIconsRef: root.pane.uiIconsRef
        text: "+ Add row"
        onClicked: { rows.append({"textValue": root.numeric ? "0" : ""}); root.publish(); }
    }
}
