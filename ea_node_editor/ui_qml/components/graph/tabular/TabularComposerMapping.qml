// Purpose: Edit one table's value blocks, append segments, coordinates and explicit axes.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: mapping
    property var composer: null
    property var view: ({})
    property color mutedColor: "#95a0b8"
    property bool advancedExpanded: false
    readonly property var segments: view.mode === "table" ? (view.segments || []) : [{blocks: [{id: "block1", member: view.member || ""}], coordinate: null}]
    signal edited(var definition)
    spacing: 10

    function clone(value) { return JSON.parse(JSON.stringify(value)); }
    function renameSummary(names) { return Object.keys(names || ({})).map(function(key) { return "Column " + (Number(key) + 1) + " → " + names[key]; }).join(", "); }
    function tableView() {
        var value = clone(view);
        value.version = 1;
        value.mode = "table";
        value.member = "";
        value.array_slices = [];
        value.segments = clone(segments);
        return value;
    }
    function blockEdit(segment, block, key, value) {
        var next = tableView();
        next.segments[segment].blocks[block][key] = value;
        edited(next);
    }
    function detail(block) {
        if (!composer) return ({});
        var currentState = composer.state;
        return currentState ? composer.member_details(String(block.member || "")) : ({});
    }
    function axes(block) {
        var rank = (detail(block).shape || []).length;
        return block.axes || {row: 0, column: rank === 1 ? null : 1, fixed: {}};
    }
    function axisEdit(segment, block, key, value) {
        var next = tableView();
        var item = next.segments[segment].blocks[block];
        var state = clone(axes(item));
        state[key] = value;
        state.fixed = state.fixed || ({});
        delete state.fixed[String(state.row)];
        if (state.column !== null) delete state.fixed[String(state.column)];
        item.axes = state;
        edited(next);
    }
    function fixedAxes(block) {
        var shape = detail(block).shape || [];
        var state = axes(block);
        var result = [];
        for (var i = 0; i < shape.length; ++i)
            if (i !== state.row && i !== state.column) result.push({axis: i, size: shape[i]});
        return result;
    }
    function coordinateEdit(segment, key, value) {
        var next = tableView();
        var coordinate = next.segments[segment].coordinate || {member: "", name: "Time", unit: "", column: null};
        coordinate[key] = value;
        next.segments[segment].coordinate = coordinate;
        edited(next);
    }

    Repeater {
        model: mapping.segments
        delegate: ComposerCard {
            id: segmentFrame
            required property int index
            required property var modelData
            Layout.fillWidth: true
            padding: 12
            ColumnLayout {
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: 9
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: mapping.segments.length > 1 ? "Row segment " + (segmentFrame.index + 1) : "Table mapping"; font.weight: Font.DemiBold; font.pixelSize: 13; Layout.fillWidth: true }
                    ComposerButton { objectName: "tabularComposerAdvanced"; quiet: true; text: mapping.advancedExpanded ? "Hide advanced" : "Advanced…"; onClicked: mapping.advancedExpanded = !mapping.advancedExpanded }
                    ComposerButton { text: "Suggest mapping"; visible: segmentFrame.index === 0; onClicked: if (composer) composer.suggest_mapping() }
                    ComposerButton { quiet: true; compact: true;
                        text: "Remove segment"
                        visible: mapping.segments.length > 1
                        onClicked: { var next = mapping.tableView(); next.segments.splice(segmentFrame.index, 1); mapping.edited(next); }
                    }
                }
                Repeater {
                    model: segmentFrame.modelData.blocks || []
                    delegate: ColumnLayout {
                        id: blockEditor
                        required property int index
                        required property var modelData
                        readonly property var information: mapping.detail(modelData)
                        readonly property var axisState: mapping.axes(modelData)
                        Layout.fillWidth: true
                        spacing: 7
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Values"; Layout.preferredWidth: 90 }
                            ComposerComboBox {
                                objectName: "tabularComposerValues"
                                Layout.fillWidth: true
                                model: mapping.composer ? mapping.composer.members : null
                                textRole: "display_name"; valueRole: "object_id"
                                displayText: blockEditor.modelData.member || "Choose values..."
                                onActivated: mapping.blockEdit(segmentFrame.index, blockEditor.index, "member", String(currentValue))
                            }
                            ComposerButton { quiet: true; compact: true;
                                text: "Remove"
                                visible: segmentFrame.modelData.blocks.length > 1
                                onClicked: { var next = mapping.tableView(); next.segments[segmentFrame.index].blocks.splice(blockEditor.index, 1); mapping.edited(next); }
                            }
                        }
                        Label { text: blockEditor.information.shape_text || ""; color: mapping.mutedColor; visible: text.length > 0; Layout.leftMargin: 96 }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Column labels"; Layout.preferredWidth: 90 }
                            ComposerComboBox {
                                objectName: "tabularComposerLabels"
                                Layout.fillWidth: true
                                model: mapping.composer ? mapping.composer.members : null
                                textRole: "display_name"; valueRole: "object_id"
                                displayText: blockEditor.modelData.labels_member || "Use source column names"
                                onActivated: mapping.blockEdit(segmentFrame.index, blockEditor.index, "labels_member", String(currentValue))
                            }
                            ComposerButton { quiet: true; compact: true; text: "Clear"; enabled: !!blockEditor.modelData.labels_member; onClicked: mapping.blockEdit(segmentFrame.index, blockEditor.index, "labels_member", "") }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            visible: mapping.advancedExpanded
                            Label { text: "Prefix / unit"; Layout.preferredWidth: 90 }
                            ComposerField { Layout.fillWidth: true; placeholderText: "Optional prefix"; text: blockEditor.modelData.prefix || ""; onEditingFinished: mapping.blockEdit(segmentFrame.index, blockEditor.index, "prefix", text) }
                            ComposerField { Layout.preferredWidth: 88; placeholderText: "Unit"; text: blockEditor.modelData.unit || ""; onEditingFinished: mapping.blockEdit(segmentFrame.index, blockEditor.index, "unit", text) }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            visible: !!blockEditor.modelData.labels_member && mapping.detail({member: blockEditor.modelData.labels_member}).kind === "table"
                            Label { text: "Label column"; Layout.preferredWidth: 90 }
                            ComposerField {
                                Layout.fillWidth: true; placeholderText: "Column name, or number starting at 1"
                                text: blockEditor.modelData.labels_column === null || blockEditor.modelData.labels_column === undefined ? "" : (typeof blockEditor.modelData.labels_column === "number" ? String(blockEditor.modelData.labels_column + 1) : blockEditor.modelData.labels_column)
                                onEditingFinished: mapping.blockEdit(segmentFrame.index, blockEditor.index, "labels_column", text.trim().length ? (/^[0-9]+$/.test(text.trim()) ? Number(text) - 1 : text) : null)
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            visible: mapping.advancedExpanded
                            Label { text: "Source columns"; Layout.preferredWidth: 90 }
                            ComposerField {
                                objectName: "tabularComposerBlockColumns"
                                Layout.fillWidth: true; placeholderText: "All, or names / numbers such as 1, 3, 5"
                                text: (blockEditor.modelData.columns || []).map(function(column) { return typeof column === "number" ? column + 1 : column; }).join(", ")
                                onEditingFinished: mapping.blockEdit(segmentFrame.index, blockEditor.index, "columns", text.trim().length ? text.split(",").map(function(column) { var value = column.trim(); return /^[0-9]+$/.test(value) ? Number(value) - 1 : value; }) : [])
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            visible: (blockEditor.information.shape || []).length > 2 || (mapping.advancedExpanded && (blockEditor.information.shape || []).length > 1)
                            Label { text: "Array axes"; Layout.preferredWidth: 90 }
                            Label { text: "Rows" }
                            ComposerSpinBox { objectName: "tabularComposerRowAxis"; from: 0; to: Math.max(0, (blockEditor.information.shape || []).length - 1); value: blockEditor.axisState.row; editable: true; onValueModified: mapping.axisEdit(segmentFrame.index, blockEditor.index, "row", value) }
                            Label { text: "Columns" }
                            ComposerSpinBox { objectName: "tabularComposerColumnAxis"; from: 0; to: Math.max(0, (blockEditor.information.shape || []).length - 1); value: blockEditor.axisState.column || 0; editable: true; onValueModified: mapping.axisEdit(segmentFrame.index, blockEditor.index, "column", value) }
                            Item { Layout.fillWidth: true }
                        }
                        Repeater {
                            model: mapping.fixedAxes(blockEditor.modelData)
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                Label { text: "Axis " + modelData.axis + " index"; Layout.preferredWidth: 90 }
                                ComposerField {
                                    objectName: "tabularComposerFixedIndex"
                                    Layout.fillWidth: true
                                    placeholderText: "Choose 0–" + (modelData.size - 1)
                                    text: blockEditor.axisState.fixed && blockEditor.axisState.fixed[String(modelData.axis)] !== undefined ? String(blockEditor.axisState.fixed[String(modelData.axis)]) : ""
                                    inputMethodHints: Qt.ImhDigitsOnly
                                    onEditingFinished: {
                                        var next = mapping.clone(blockEditor.axisState.fixed || ({}));
                                        if (text.trim().length) next[String(modelData.axis)] = Number(text); else delete next[String(modelData.axis)];
                                        mapping.axisEdit(segmentFrame.index, blockEditor.index, "fixed", next);
                                    }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            visible: mapping.advancedExpanded
                            Label { text: "Rename column"; Layout.preferredWidth: 90 }
                            ComposerSpinBox { id: renamePosition; from: 1; to: 100000; value: 1; editable: true; Layout.preferredWidth: 95 }
                            ComposerField { id: renameText; Layout.fillWidth: true; placeholderText: "New column name" }
                            ComposerButton { text: "Set"; enabled: renameText.text.trim().length > 0; onClicked: { var names = mapping.clone(blockEditor.modelData.names || ({})); names[String(renamePosition.value - 1)] = renameText.text; mapping.blockEdit(segmentFrame.index, blockEditor.index, "names", names); } }
                        }
                        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: mapping.mutedColor; visible: Object.keys(blockEditor.modelData.names || ({})).length > 0; text: mapping.renameSummary(blockEditor.modelData.names) }
                        Rectangle { Layout.fillWidth: true; height: 1; color: mapping.mutedColor; opacity: 0.25; Layout.topMargin: 3; Layout.bottomMargin: 3 }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Row coordinate"; Layout.preferredWidth: 90 }
                    ComposerComboBox {
                        objectName: "tabularComposerCoordinate"
                        Layout.fillWidth: true
                        model: mapping.composer ? mapping.composer.members : null
                        textRole: "display_name"; valueRole: "object_id"
                        displayText: segmentFrame.modelData.coordinate ? segmentFrame.modelData.coordinate.member : "Use row numbers"
                        onActivated: {
                            var next = mapping.tableView();
                            next.segments[segmentFrame.index].coordinate = {member: String(currentValue), name: String(currentValue), unit: "", column: null};
                            mapping.edited(next);
                        }
                    }
                    ComposerButton { quiet: true; compact: true; text: "Clear"; enabled: !!segmentFrame.modelData.coordinate; onClicked: { var next = mapping.tableView(); next.segments[segmentFrame.index].coordinate = null; mapping.edited(next); } }
                }
                RowLayout {
                    visible: mapping.advancedExpanded && !!segmentFrame.modelData.coordinate
                    Layout.fillWidth: true
                    Label { text: "Name / unit"; Layout.preferredWidth: 90 }
                    ComposerField { Layout.fillWidth: true; text: segmentFrame.modelData.coordinate ? segmentFrame.modelData.coordinate.name : ""; onEditingFinished: mapping.coordinateEdit(segmentFrame.index, "name", text) }
                    ComposerField { Layout.preferredWidth: 88; placeholderText: "Unit"; text: segmentFrame.modelData.coordinate ? segmentFrame.modelData.coordinate.unit : ""; onEditingFinished: mapping.coordinateEdit(segmentFrame.index, "unit", text) }
                }
                RowLayout {
                    visible: !!segmentFrame.modelData.coordinate && mapping.composer && (mapping.detail({member: segmentFrame.modelData.coordinate.member}).kind === "table" || (mapping.detail({member: segmentFrame.modelData.coordinate.member}).shape || []).length === 2)
                    Layout.fillWidth: true
                    Label { text: "Source column"; Layout.preferredWidth: 90 }
                    ComposerField {
                        Layout.fillWidth: true; placeholderText: "Column name, or number starting at 1"
                        text: !segmentFrame.modelData.coordinate || segmentFrame.modelData.coordinate.column === null || segmentFrame.modelData.coordinate.column === undefined ? "" : (typeof segmentFrame.modelData.coordinate.column === "number" ? String(segmentFrame.modelData.coordinate.column + 1) : segmentFrame.modelData.coordinate.column)
                        onEditingFinished: mapping.coordinateEdit(segmentFrame.index, "column", text.trim().length ? (/^[0-9]+$/.test(text.trim()) ? Number(text) - 1 : text) : null)
                    }
                }
                ComposerButton {
                    objectName: "tabularComposerAddColumns"
                    quiet: true
                    text: "+ Add another value block"
                    onClicked: { var next = mapping.tableView(); next.segments[segmentFrame.index].blocks.push({id: "block" + Date.now(), member: ""}); mapping.edited(next); }
                }
            }
        }
    }
    ComposerButton {
        objectName: "tabularComposerAppendRows"
        text: "+ Append rows"
        onClicked: { var next = mapping.tableView(); next.segments.push({blocks: [{id: "block1", member: ""}], coordinate: null}); mapping.edited(next); }
    }
    Label { Layout.fillWidth: true; text: "Columns align by row position. Appended segments match column names."; color: mapping.mutedColor; wrapMode: Text.Wrap }
    Label { Layout.fillWidth: true; text: composer ? composer.state.suggestion : ""; visible: text.length > 0; color: mapping.mutedColor; wrapMode: Text.Wrap }
}
