// Purpose: Author saved output conditions, stable sorting, ranges and ordered columns.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ComposerCard {
    id: rules
    property var view: ({})
    property var schema: []
    property color mutedColor: "#95a0b8"
    readonly property var query: view.query || ({match: "all", filters: [], sort: []})
    readonly property var output: view.output || ({row_offset: 0, row_limit: 0, columns: []})
    readonly property var columnNames: schema.map(function(column) { return column.name; })
    readonly property var operators: ["eq", "ne", "gt", "ge", "lt", "le", "contains", "not_contains", "starts_with", "ends_with", "is_missing", "is_present"]
    readonly property var operatorLabels: ["equals", "does not equal", "greater than", "at least", "less than", "at most", "contains", "does not contain", "starts with", "ends with", "is missing", "is present"]
    signal edited(var definition)

    function clone(value) { return JSON.parse(JSON.stringify(value)); }
    function nextView() {
        var next = clone(view);
        next.query = clone(query);
        next.query.filters = next.query.filters || [];
        next.query.sort = next.query.sort || [];
        next.output = clone(output);
        return next;
    }
    function filterEdit(index, key, value) { var next = nextView(); next.query.filters[index][key] = value; edited(next); }
    function sortEdit(index, key, value) { var next = nextView(); next.query.sort[index][key] = value; edited(next); }
    function outputEdit(key, value) { var next = nextView(); next.output[key] = value; edited(next); }
    function toggleColumn(name, included) {
        var columns = output.columns && output.columns.length ? clone(output.columns) : clone(columnNames);
        var at = columns.indexOf(name);
        if (included && at < 0) columns.push(name);
        else if (!included && at >= 0 && columns.length > 1) columns.splice(at, 1);
        outputEdit("columns", columns);
    }

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 12
    Label { text: "Output rules"; font.pixelSize: 13; font.weight: Font.DemiBold }
    Label { Layout.fillWidth: true; text: "Applied to every plot, calculation and full-output export."; color: rules.mutedColor; wrapMode: Text.Wrap }
    RowLayout {
        Layout.fillWidth: true
        Label { text: "Keep rows matching" }
        ComposerComboBox { model: ["All conditions", "Any condition"]; currentIndex: rules.query.match === "any" ? 1 : 0; onActivated: { var next = rules.nextView(); next.query.match = currentIndex ? "any" : "all"; rules.edited(next); } }
        Item { Layout.fillWidth: true }
    }
    Repeater {
        model: rules.query.filters || []
        delegate: RowLayout {
            id: condition
            required property int index
            required property var modelData
            Layout.fillWidth: true
            ComposerComboBox { Layout.fillWidth: true; Layout.minimumWidth: 90; model: rules.columnNames; displayText: condition.modelData.column; onActivated: rules.filterEdit(condition.index, "column", currentText) }
            ComposerComboBox { Layout.preferredWidth: 145; model: rules.operatorLabels; currentIndex: rules.operators.indexOf(condition.modelData.op); onActivated: rules.filterEdit(condition.index, "op", rules.operators[currentIndex]) }
            ComposerField {
                objectName: "tabularComposerFilterValue"
                Layout.fillWidth: true; Layout.minimumWidth: 70
                placeholderText: "Value"; text: condition.modelData.value || ""
                enabled: condition.modelData.op !== "is_missing" && condition.modelData.op !== "is_present"
                onEditingFinished: rules.filterEdit(condition.index, "value", text)
            }
            ComposerButton { quiet: true; compact: true; text: "×"; Accessible.name: "Remove condition"; onClicked: { var next = rules.nextView(); next.query.filters.splice(condition.index, 1); rules.edited(next); } }
        }
    }
    ComposerButton { objectName: "tabularComposerAddCondition"; text: "+ Add condition"; enabled: rules.columnNames.length > 0; onClicked: { var next = rules.nextView(); next.query.filters.push({column: rules.columnNames[0], op: "gt", value: ""}); rules.edited(next); } }
    Rectangle { Layout.fillWidth: true; height: 1; color: rules.mutedColor; opacity: 0.25 }
    Label { text: "Sort output"; font.bold: true }
    Repeater {
        model: rules.query.sort || []
        delegate: RowLayout {
            id: sortRow
            required property int index
            required property var modelData
            Layout.fillWidth: true
            Label { text: String(sortRow.index + 1) }
            ComposerComboBox { Layout.fillWidth: true; model: rules.columnNames; displayText: sortRow.modelData.column; onActivated: rules.sortEdit(sortRow.index, "column", currentText) }
            ComposerComboBox { model: ["Ascending", "Descending"]; currentIndex: sortRow.modelData.descending ? 1 : 0; onActivated: rules.sortEdit(sortRow.index, "descending", currentIndex === 1) }
            ComposerButton { quiet: true; compact: true; text: "×"; Accessible.name: "Remove sort key"; onClicked: { var next = rules.nextView(); next.query.sort.splice(sortRow.index, 1); rules.edited(next); } }
        }
    }
    ComposerButton { text: "+ Add sort key"; enabled: rules.columnNames.length > 0; onClicked: { var next = rules.nextView(); next.query.sort.push({column: rules.columnNames[0], descending: false}); rules.edited(next); } }
    Rectangle { Layout.fillWidth: true; height: 1; color: rules.mutedColor; opacity: 0.25 }
    Label { text: "Output range after filtering and sorting"; font.bold: true }
    RowLayout {
        Layout.fillWidth: true
        Label { text: "Start row" }
        ComposerField { objectName: "tabularComposerOutputStart"; Layout.fillWidth: true; text: String((rules.output.row_offset || 0) + 1); inputMethodHints: Qt.ImhDigitsOnly; onEditingFinished: rules.outputEdit("row_offset", Math.max(0, Number(text) - 1)) }
        Label { text: "Row count" }
        ComposerField { objectName: "tabularComposerOutputCount"; Layout.fillWidth: true; placeholderText: "All remaining"; text: rules.output.row_limit ? String(rules.output.row_limit) : ""; inputMethodHints: Qt.ImhDigitsOnly; onEditingFinished: rules.outputEdit("row_limit", text.trim().length ? Number(text) : 0) }
    }
    RowLayout {
        Layout.fillWidth: true
        ComposerCheckBox { text: "All columns"; checked: !rules.output.columns || rules.output.columns.length === 0; onClicked: rules.outputEdit("columns", checked ? [] : rules.columnNames.slice(0, 1)) }
        ComposerButton { text: "Choose columns..."; enabled: rules.columnNames.length > 0; onClicked: columnPicker.open() }
        Item { Layout.fillWidth: true }
    }
    ListView {
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(150, contentHeight)
        clip: true
        model: rules.output.columns || []
        delegate: RowLayout {
            id: selectedColumn
            required property int index
            required property var modelData
            width: ListView.view.width
            Label { Layout.fillWidth: true; text: String(selectedColumn.modelData); elide: Text.ElideRight }
            ComposerButton { quiet: true; compact: true; text: "↑"; Accessible.name: "Move column earlier"; enabled: selectedColumn.index > 0; onClicked: { var cols = rules.clone(rules.output.columns); var item = cols.splice(selectedColumn.index, 1)[0]; cols.splice(selectedColumn.index - 1, 0, item); rules.outputEdit("columns", cols); } }
            ComposerButton { quiet: true; compact: true; text: "↓"; Accessible.name: "Move column later"; enabled: selectedColumn.index < rules.output.columns.length - 1; onClicked: { var cols = rules.clone(rules.output.columns); var item = cols.splice(selectedColumn.index, 1)[0]; cols.splice(selectedColumn.index + 1, 0, item); rules.outputEdit("columns", cols); } }
        }
    }
    Popup {
        id: columnPicker
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(400, parent ? parent.width - 32 : 400)
        height: Math.min(400, parent ? parent.height - 64 : 400)
        modal: true; focus: true
        ColumnLayout {
            anchors.fill: parent
            Label { text: "Include output columns"; font.bold: true }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                model: rules.columnNames
                delegate: CheckDelegate { required property var modelData; width: ListView.view.width; text: modelData; checked: !rules.output.columns || rules.output.columns.length === 0 || rules.output.columns.indexOf(modelData) >= 0; onClicked: rules.toggleColumn(modelData, checked) }
                ScrollBar.vertical: ScrollBar { }
            }
            ComposerButton { text: "Done"; Layout.alignment: Qt.AlignRight; onClicked: columnPicker.close() }
        }
    }
    }
}
