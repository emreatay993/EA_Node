// Purpose: Fullscreen data composer with a draft mapping, saved rules and bounded preview.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "TabularSurfaceUtils.js" as TabularUtils
import "../../common/contrast_utils.js" as ContrastUtils

Pane {
    id: surface
    objectName: "contentFullscreenTabularSurface"
    property var payload: ({})
    property var bridgeRef: null
    property var themePalette: ({})
    readonly property var composer: bridgeRef && bridgeRef.tabular_composer ? bridgeRef.tabular_composer : null
    readonly property var dataState: composer ? composer.state : ({})
    readonly property var draft: dataState.draft || ({})
    readonly property var view: draft.data_view || ({version: 1, mode: "source"})
    readonly property var activePreview: dataState.preview || ({})
    readonly property string previewKind: String(activePreview.preview_kind || "")
    readonly property bool arrayMode: view.mode === "array" || (view.mode === "source" && previewKind === "array")
    readonly property bool ready: activePreview.state === "ready" && !dataState.busy
    readonly property bool hasSource: String(draft.path || "").trim().length > 0
    readonly property color panelColor: String(themePalette.panel_bg || "#202329")
    readonly property color panelAltColor: String(themePalette.panel_alt_bg || "#272b33")
    readonly property color textColor: String(themePalette.panel_fg || "#edf0f7")
    readonly property color mutedColor: String(themePalette.muted_fg || "#a8b2c3")
    readonly property color borderColor: String(themePalette.border || "#363c46")
    readonly property color accentColor: String(themePalette.accent || "#69baff")
    readonly property bool lightTheme: panelColor.r + panelColor.g + panelColor.b > 1.8
    readonly property color cardColor: String(themePalette.input_bg || (lightTheme ? "#ffffff" : "#252a33"))
    readonly property color accentTextColor: ContrastUtils.pickHighestContrastForeground("", "#152239", "#ffffff", String(accentColor), 4.5)
    readonly property color successColor: lightTheme ? "#168165" : "#6bd5b1"
    property string selectedMember: ""
    property var selectedColumns: []
    property var tableViewState: ({})
    property var tableDraftBackup: null
    readonly property int rowOffset: (dataState.preview_request || ({})).row_offset || 0
    readonly property int columnOffset: (dataState.preview_request || ({})).column_offset || 0
    readonly property string searchText: (dataState.preview_request || ({})).search || ""
    property string lastCopiedText: ""
    property var lastExportResult: ({})
    padding: width < 900 ? 14 : 22
    font.pixelSize: 12

    palette.window: panelColor
    palette.base: cardColor
    palette.alternateBase: panelAltColor
    palette.text: textColor
    palette.windowText: textColor
    palette.button: panelAltColor
    palette.buttonText: textColor
    palette.placeholderText: mutedColor
    palette.mid: borderColor
    palette.dark: borderColor
    palette.light: panelAltColor
    palette.brightText: textColor
    palette.highlight: accentColor
    palette.highlightedText: accentTextColor
    background: Rectangle { color: surface.lightTheme ? Qt.tint(surface.panelColor, Qt.alpha(surface.accentColor, 0.025)) : surface.panelColor }

    function clone(value) { return JSON.parse(JSON.stringify(value)); }
    function primaryMember() {
        if (view.mode === "table" && view.segments && view.segments.length && view.segments[0].blocks.length)
            return String(view.segments[0].blocks[0].member || "");
        return String(view.member || "");
    }
    function memberInfo(member) { return dataState && composer ? composer.member_details(member) : ({}); }
    function editableTable() {
        var next = clone(view);
        if (next.mode !== "table") {
            next.mode = "table";
            next.member = "";
            next.array_slices = [];
            next.segments = [{blocks: [{id: "block1", member: primaryMember()}], coordinate: null}];
        }
        return next;
    }
    function chooseLayout(array) {
        if (!composer) return;
        if (array) {
            tableDraftBackup = clone(view);
            composer.update_definition({version: 1, mode: "array", member: primaryMember()});
        } else {
            composer.update_definition(tableDraftBackup || editableTable());
            tableDraftBackup = null;
        }
    }
    function useValues() {
        var next = editableTable();
        next.segments[0].blocks[0].member = selectedMember;
        composer.update_definition(next);
    }
    function requestWindow(row, column, newSearch) {
        var request = {row_offset: Math.max(0, row), row_limit: 50, column_offset: Math.max(0, column), column_limit: 50};
        var text = newSearch === undefined ? searchText : String(newSearch);
        if (text.trim().length && !arrayMode) request.search = text.trim();
        if (composer) composer.request_preview(request);
    }
    function copySelection() {
        lastCopiedText = dataGrid.copySelection();
        if (composer && composer.copy_text) composer.copy_text(lastCopiedText);
        return lastCopiedText;
    }
    function rawSlice(axis, position, value) {
        var next = clone(view);
        next.mode = "array";
        next.member = primaryMember();
        var shape = (composer ? composer.member_details(next.member).shape : []) || [];
        next.array_slices = next.array_slices || shape.map(function() { return [0, 0]; });
        if (!next.array_slices.length) next.array_slices = shape.map(function() { return [0, 0]; });
        next.array_slices[axis][position] = value;
        composer.update_definition(next);
    }
    function previewAxisEdit(key, value) {
        var axes = clone(dataState.preview_axes || {row: 0, column: 1, fixed: {}});
        axes[key] = value;
        delete axes.fixed[String(axes.row)];
        delete axes.fixed[String(axes.column)];
        composer.set_preview_axes(axes);
    }
    function previewFixedAxes() {
        var shape = (activePreview.array || ({})).shape || memberInfo(primaryMember()).shape || [];
        var axes = dataState.preview_axes || {row: 0, column: 1, fixed: {}};
        var result = [];
        for (var i = 0; i < shape.length; ++i) if (i !== axes.row && i !== axes.column) result.push({axis: i, size: shape[i]});
        return result;
    }
    function outputSummary() {
        if (!dataState.valid) return dataState.busy ? "Preparing output..." : "Configure a valid output";
        var shape = activePreview.array ? activePreview.array.shape : [];
        var metadata = activePreview.metadata || ({});
        if (arrayMode) return "Array Data · " + shape.join(" × ");
        var rows = metadata.row_count;
        var columns = metadata.column_count;
        return "Table Data · " + (rows === undefined || rows === null ? "?" : rows.toLocaleString()) + " rows × " + (columns === undefined ? "?" : columns) + " columns";
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Rectangle {
                width: 40; height: 40; radius: 11
                color: Qt.alpha(surface.accentColor, 0.12)
                Grid {
                    anchors.centerIn: parent; columns: 3; spacing: 3
                    Repeater { model: 9; Rectangle { width: 5; height: 5; radius: 1; color: surface.accentColor; opacity: index < 3 ? 1 : 0.5 } }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                Label { text: "Configure data"; font.pixelSize: 22; font.weight: Font.DemiBold }
                Label { Layout.fillWidth: true; text: "Shape your source into a reusable table or array"; color: surface.mutedColor; elide: Text.ElideRight }
            }
            Rectangle {
                visible: surface.width >= 900
                implicitWidth: badgeText.implicitWidth + 24; implicitHeight: 28; radius: 14
                color: Qt.alpha(surface.accentColor, 0.09)
                Label { id: badgeText; anchors.centerIn: parent; text: "DATA WORKSPACE"; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1; color: surface.textColor }
            }
        }
        ComposerCard {
            Layout.fillWidth: true
            visible: !!draft.data_view_migration_notice && Object.keys(draft.data_view_migration_notice).length > 0
            RowLayout {
                anchors.fill: parent
                Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: "Review this imported view. Previous preview limits no longer restrict the output."; color: surface.mutedColor }
                ComposerButton { text: "Use previous selection"; onClicked: composer.use_previous_selection() }
                ComposerButton { quiet: true; text: "Dismiss"; onClicked: composer.dismiss_notice() }
            }
        }
        SplitView {
            id: mainSplit
            Layout.fillWidth: true; Layout.fillHeight: true
            orientation: surface.width >= 980 ? Qt.Horizontal : Qt.Vertical
            handle: Rectangle {
                implicitWidth: 14; implicitHeight: 12; color: "transparent"
                Rectangle {
                    anchors.centerIn: parent
                    width: mainSplit.orientation === Qt.Horizontal ? 2 : 30
                    height: mainSplit.orientation === Qt.Horizontal ? 30 : 2
                    radius: 1
                    color: SplitHandle.hovered || SplitHandle.pressed ? surface.accentColor : surface.borderColor
                }
            }
            Pane {
                objectName: "tabularComposerSidebar"
                SplitView.preferredWidth: 252; SplitView.minimumWidth: 224
                SplitView.preferredHeight: 212; SplitView.minimumHeight: 180
                padding: 14
                background: Rectangle { color: surface.cardColor; radius: 11; border.color: surface.borderColor }
                ColumnLayout {
                    anchors.fill: parent; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "SOURCE"; font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.1; color: surface.mutedColor; Layout.fillWidth: true }
                        Label { text: composer && surface.hasSource ? composer.catalogue.total + " objects" : ""; color: surface.mutedColor; font.pixelSize: 11 }
                    }
                    Label { Layout.fillWidth: true; text: dataState.source_name || "No source connected"; elide: Text.ElideMiddle; font.pixelSize: 13; font.weight: Font.DemiBold }
                    ComposerButton {
                        objectName: "tabularComposerChooseSource"
                        text: surface.hasSource ? "Change source…" : "Choose source…"
                        Layout.fillWidth: true; onClicked: sourceMenu.open()
                    }
                    Menu {
                        id: sourceMenu
                        MenuItem { text: "Link an external file…"; onTriggered: composer.browse_source(false) }
                        MenuItem { text: "Copy a file into the project…"; onTriggered: composer.browse_source(true) }
                    }
                    ComposerField {
                        objectName: "tabularComposerSearch"; Layout.fillWidth: true
                        visible: surface.hasSource
                        placeholderText: "Search datasets…"
                        onTextEdited: if (composer) composer.catalogue.search(text)
                    }
                    Item {
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 0
                        ListView {
                            id: sourceList
                            objectName: "tabularComposerCatalogue"
                            anchors.fill: parent
                            clip: true; spacing: 3
                            model: composer ? composer.catalogue : null
                            boundsBehavior: Flickable.StopAtBounds
                            delegate: ItemDelegate {
                                required property string object_id
                                required property string display_name
                                required property string shape_text
                                required property string dtype
                                required property bool supported
                                width: sourceList.width; height: 56; padding: 10
                                enabled: supported
                                highlighted: surface.selectedMember === object_id || (!surface.selectedMember && surface.primaryMember() === object_id)
                                onClicked: surface.selectedMember = object_id
                                background: Rectangle {
                                    radius: 7
                                    color: highlighted ? Qt.alpha(surface.accentColor, 0.11) : parent.hovered ? surface.panelAltColor : "transparent"
                                    border.width: highlighted ? 1 : 0
                                    border.color: Qt.alpha(surface.accentColor, 0.35)
                                }
                                contentItem: Column {
                                    spacing: 4
                                    Label { width: parent.width; text: display_name; elide: Text.ElideMiddle; font.pixelSize: 12; font.weight: highlighted ? Font.DemiBold : Font.Normal; opacity: supported ? 1 : 0.5 }
                                    Label { width: parent.width; text: shape_text + (dtype.length ? " · " + dtype : ""); elide: Text.ElideRight; color: surface.mutedColor; font.pixelSize: 10 }
                                }
                            }
                            ScrollBar.vertical: ScrollBar { }
                        }
                        Label {
                            anchors.centerIn: parent; width: parent.width - 12
                            visible: !surface.hasSource || (!!composer && composer.catalogue.matched === 0 && !dataState.busy)
                            text: surface.hasSource ? "No datasets match your search." : "Your arrays, sheets and datasets\nwill appear here."
                            horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap; color: surface.mutedColor; font.pixelSize: 11
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        visible: surface.hasSource && surface.width >= 980
                        ComposerButton { Layout.fillWidth: true; text: "Use as values"; enabled: surface.selectedMember.length > 0; onClicked: surface.useValues() }
                        ComposerButton { quiet: true; text: "Inspect"; enabled: surface.selectedMember.length > 0; onClicked: composer.select_member(surface.selectedMember) }
                    }
                    ComposerCheckBox { text: "Include metadata"; visible: surface.hasSource && surface.width >= 980; onClicked: if (composer) composer.catalogue.show_metadata(checked) }
                }
            }
            ColumnLayout {
                SplitView.fillWidth: true; SplitView.fillHeight: true
                SplitView.minimumWidth: 380
                spacing: 12
                RowLayout {
                    visible: surface.hasSource
                    Layout.fillWidth: true; spacing: 10
                    ComposerField {
                        objectName: "tabularComposerViewName"
                        Layout.fillWidth: true; placeholderText: "Untitled view"
                        text: draft.data_view_name || ""
                        onEditingFinished: if (composer) composer.edit_property("data_view_name", text)
                    }
                    ComposerButton { objectName: "tabularComposerTableMode"; text: "Table"; checkable: true; checked: !surface.arrayMode; onClicked: surface.chooseLayout(false) }
                    ComposerButton { objectName: "tabularComposerArrayMode"; text: "Array"; checkable: true; checked: surface.arrayMode; enabled: surface.memberInfo(surface.primaryMember()).kind === "array"; onClicked: surface.chooseLayout(true) }
                }
                TabBar {
                    id: editorTabs
                    visible: surface.hasSource
                    Layout.fillWidth: true
                    background: Rectangle { color: "transparent"; Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: surface.borderColor } }
                    ComposerTabButton { objectName: "tabularComposerMappingTab"; width: 116; text: "Mapping" }
                    ComposerTabButton { width: 124; objectName: "tabularComposerRulesTab"; text: "Output rules"; enabled: !surface.arrayMode }
                    ComposerTabButton { width: 128; text: "Source options" }
                }
                ScrollView {
                    id: editorScroll
                    objectName: "tabularComposerEditor"
                    visible: surface.hasSource
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    Layout.preferredHeight: surface.width < 980 ? 300 : Math.max(240, Math.min(370, surface.height * 0.43))
                    Layout.maximumHeight: Layout.preferredHeight
                    clip: true
                    contentWidth: availableWidth
                    ColumnLayout {
                        width: editorScroll.availableWidth
                        spacing: 12
                        TabularComposerMapping {
                            visible: editorTabs.currentIndex === 0 && !surface.arrayMode
                            Layout.fillWidth: true
                            composer: surface.composer; view: surface.view; mutedColor: surface.mutedColor
                            onEdited: function(definition) { if (composer) composer.update_definition(definition); }
                        }
                        ColumnLayout {
                            visible: editorTabs.currentIndex === 0 && surface.arrayMode
                            Layout.fillWidth: true
                            Label { text: "Raw array output"; font.bold: true }
                            Label { Layout.fillWidth: true; text: "Keep the original dimensions, or set explicit slices for output."; wrapMode: Text.Wrap; color: surface.mutedColor }
                            Repeater {
                                model: surface.memberInfo(surface.primaryMember()).shape || []
                                delegate: RowLayout {
                                    required property int index
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Label { text: "Axis " + index + " (" + modelData + ")"; Layout.preferredWidth: 100 }
                                    ComposerField { Layout.fillWidth: true; placeholderText: "Start: 1"; text: view.array_slices && view.array_slices.length ? String(view.array_slices[index][0] + 1) : ""; onEditingFinished: surface.rawSlice(index, 0, text.trim().length ? Number(text) - 1 : 0) }
                                    ComposerField { Layout.fillWidth: true; placeholderText: "Count: all"; text: view.array_slices && view.array_slices.length && view.array_slices[index][1] ? String(view.array_slices[index][1]) : ""; onEditingFinished: surface.rawSlice(index, 1, text.trim().length ? Number(text) : 0) }
                                }
                            }
                            Label { text: "Preview plane (does not change output)"; font.bold: true; visible: (surface.memberInfo(surface.primaryMember()).shape || []).length > 2 }
                            RowLayout {
                                visible: (surface.memberInfo(surface.primaryMember()).shape || []).length > 2
                                Layout.fillWidth: true
                                Label { text: "Row axis" }
                                ComposerSpinBox { from: 0; to: Math.max(1, (surface.memberInfo(surface.primaryMember()).shape || []).length - 1); value: (dataState.preview_axes || ({})).row || 0; editable: true; onValueModified: surface.previewAxisEdit("row", value) }
                                Label { text: "Column axis" }
                                ComposerSpinBox { from: 0; to: Math.max(1, (surface.memberInfo(surface.primaryMember()).shape || []).length - 1); value: (dataState.preview_axes || ({})).column || 0; editable: true; onValueModified: surface.previewAxisEdit("column", value) }
                            }
                            Repeater {
                                model: (surface.memberInfo(surface.primaryMember()).shape || []).length > 2 ? surface.previewFixedAxes() : []
                                delegate: RowLayout {
                                    required property var modelData
                                    Label { text: "Axis " + modelData.axis + " index"; Layout.preferredWidth: 100 }
                                    ComposerField {
                                        Layout.fillWidth: true; placeholderText: "Choose 0–" + (modelData.size - 1)
                                        text: dataState.preview_axes && dataState.preview_axes.fixed[String(modelData.axis)] !== undefined ? String(dataState.preview_axes.fixed[String(modelData.axis)]) : ""
                                        onEditingFinished: { var fixed = surface.clone(dataState.preview_axes.fixed); if (text.trim().length) fixed[String(modelData.axis)] = Number(text); else delete fixed[String(modelData.axis)]; surface.previewAxisEdit("fixed", fixed); }
                                    }
                                }
                            }
                        }

                        TabularComposerRules {
                            visible: editorTabs.currentIndex === 1 && !surface.arrayMode
                            Layout.fillWidth: true
                            view: surface.view; schema: surface.dataState.schema || []; mutedColor: surface.mutedColor
                            onEdited: function(definition) { if (composer) composer.update_definition(definition); }
                        }
                        GridLayout {
                            visible: editorTabs.currentIndex === 2
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: 12; rowSpacing: 10
                            Label { text: "Source path" }
                            ComposerField { Layout.fillWidth: true; text: draft.path || ""; onEditingFinished: if (text !== draft.path) composer.set_source(text, false) }
                            Label { text: "Delimiter" }
                            ComposerField { Layout.fillWidth: true; placeholderText: "Automatic"; text: draft.delimiter || ""; onEditingFinished: composer.edit_property("delimiter", text) }
                            Label { text: "Encoding" }
                            ComposerField { Layout.fillWidth: true; text: draft.encoding || "utf-8"; onEditingFinished: composer.edit_property("encoding", text) }
                            Label { text: "Header row" }
                            ComposerField { Layout.fillWidth: true; placeholderText: "None"; text: draft.header_row === null ? "" : String((draft.header_row || 0) + 1); onEditingFinished: composer.edit_property("header_row", text.trim().length ? Number(text) - 1 : null) }
                            Label { text: "Skip rows" }
                            ComposerField { Layout.fillWidth: true; text: String(draft.skip_rows || 0); onEditingFinished: composer.edit_property("skip_rows", Number(text)) }
                            ComposerCheckBox { Layout.columnSpan: 2; text: "Allow large NPZ array loading"; checked: !!draft.allow_npz_archive_preview; onClicked: composer.edit_property("allow_npz_archive_preview", checked) }
                            Label { Layout.columnSpan: 2; Layout.fillWidth: true; wrapMode: Text.Wrap; text: dataState.managed_copy ? "The source will be copied into the project when you apply." : "File contents are read on demand. The source is not modified."; color: surface.mutedColor }
                        }
                    }
                }
                ComposerCard {
                    objectName: "tabularComposerPreviewCard"
                    Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 200
                    padding: 0
                    ColumnLayout {
                        anchors.fill: parent; spacing: 0
                        RowLayout {
                            visible: surface.hasSource
                            Layout.fillWidth: true; Layout.margins: 12; spacing: 8
                            ColumnLayout {
                                Layout.fillWidth: true; spacing: 2
                                Label { text: "Output preview"; font.weight: Font.DemiBold; font.pixelSize: 13 }
                                Label { text: "Inspection only · does not limit your output"; color: surface.mutedColor; font.pixelSize: 10; visible: surface.width >= 1100 }
                            }
                            ComposerField { objectName: "tabularComposerFind"; Layout.preferredWidth: surface.width < 1100 ? 150 : 190; placeholderText: "Find in preview…"; text: surface.searchText; visible: !surface.arrayMode; onEditingFinished: surface.requestWindow(0, 0, text) }
                            ComposerButton { quiet: true; text: "Copy"; enabled: surface.ready; onClicked: surface.copySelection() }
                            ComposerButton { objectName: "tabularComposerExport"; text: "Export…"; enabled: surface.ready && !!composer && !!composer.export_data; onClicked: exportMenu.open() }
                            Menu {
                                id: exportMenu
                                MenuItem { objectName: "tabularComposerExportVisible"; text: "Visible preview"; onTriggered: if (composer) composer.export_data("visible", {}) }
                                MenuItem { text: "Selected cell or columns"; enabled: surface.selectedColumns.length > 0 || dataGrid.selectedRow >= 0; onTriggered: if (composer) composer.export_data("selection", {columns: surface.selectedColumns, row: dataGrid.selectedRow, column: dataGrid.selectedColumn}) }
                                MenuItem { text: dataState.dirty ? "Configured output (draft)" : "Configured output"; onTriggered: if (composer) composer.export_data("output", {}) }
                            }
                        }
                        Rectangle { visible: surface.hasSource; Layout.fillWidth: true; height: 1; color: surface.borderColor }
                        Item {
                            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 120
                            TabularTableViewport {
                                id: dataGrid
                                objectName: "contentFullscreenTabularGrid"
                                anchors.fill: parent; anchors.margins: 1
                                visible: surface.ready
                                preview: surface.activePreview
                                themePalette: surface.themePalette
                                tableViewState: surface.tableViewState
                                selectedColumns: surface.selectedColumns
                                objectNamePrefix: "contentFullscreenTabular"
                                onSelectedColumnsEdited: function(columns) { surface.selectedColumns = columns; }
                                onTableViewStateEdited: function(state) { surface.tableViewState = state; if (bridgeRef && bridgeRef.save_tabular_table_view_state) bridgeRef.save_tabular_table_view_state(state); }
                            }
                            ColumnLayout {
                                objectName: "tabularComposerEmptyState"
                                anchors.centerIn: parent; width: Math.min(parent.width - 40, 420); spacing: 12
                                visible: !surface.ready
                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter; width: 56; height: 56; radius: 16
                                    color: Qt.alpha(surface.accentColor, 0.09)
                                    Rectangle { anchors.centerIn: parent; width: 20; height: 2; radius: 1; color: surface.accentColor; visible: !dataState.error }
                                    Rectangle { anchors.centerIn: parent; width: 2; height: 20; radius: 1; color: surface.accentColor; visible: !dataState.error }
                                    Label { anchors.centerIn: parent; text: "!"; visible: !!dataState.error; font.pixelSize: 26; color: surface.accentColor }
                                }
                                BusyIndicator { Layout.alignment: Qt.AlignHCenter; visible: !!dataState.busy; running: visible; implicitWidth: 28; implicitHeight: 28 }
                                Label {
                                    Layout.fillWidth: true; text: !surface.hasSource ? "Start with a source file" : dataState.busy ? "Preparing your data" : dataState.error ? "This view needs attention" : "Choose a dataset to continue"
                                    horizontalAlignment: Text.AlignHCenter; font.pixelSize: 18; font.weight: Font.DemiBold
                                }
                                Label {
                                    Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
                                    text: !surface.hasSource ? "Connect your data, choose the values you need,\nand build an output that is ready for your graph." : (dataState.error || activePreview.message || "Select a dataset in the source browser.")
                                    maximumLineCount: 5; elide: Text.ElideRight; color: surface.mutedColor
                                }
                                ComposerButton { Layout.alignment: Qt.AlignHCenter; visible: !surface.hasSource; text: "Choose a source file"; highlighted: true; onClicked: if (composer) composer.browse_source(false) }
                                Label { Layout.fillWidth: true; visible: !surface.hasSource; text: "CSV · Excel · Parquet · NumPy · HDF5"; horizontalAlignment: Text.AlignHCenter; color: surface.mutedColor; font.pixelSize: 10; Layout.topMargin: 2 }
                            }
                        }
                        Rectangle { visible: surface.hasSource; Layout.fillWidth: true; height: 1; color: surface.borderColor }
                        RowLayout {
                            visible: surface.hasSource
                            Layout.fillWidth: true; Layout.margins: 7; spacing: 4
                            Label { Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; text: surface.ready ? TabularUtils.visibleSummary(surface.activePreview) : "Preview unavailable"; color: surface.mutedColor; font.pixelSize: 10 }
                            ComposerButton { quiet: true; compact: true; text: "‹"; Accessible.name: "Previous rows"; enabled: surface.ready && surface.rowOffset > 0; onClicked: surface.requestWindow(surface.rowOffset - 50, surface.columnOffset) }
                            ComposerButton { quiet: true; compact: true; text: "›"; Accessible.name: "Next rows"; enabled: surface.ready; onClicked: surface.requestWindow(surface.rowOffset + 50, surface.columnOffset) }
                            Rectangle { width: 1; height: 16; color: surface.borderColor }
                            ComposerButton { quiet: true; compact: true; text: "←"; Accessible.name: "Previous columns"; enabled: surface.ready && surface.columnOffset > 0; onClicked: surface.requestWindow(surface.rowOffset, surface.columnOffset - 50) }
                            ComposerButton { quiet: true; compact: true; text: "→"; Accessible.name: "Next columns"; enabled: surface.ready; onClicked: surface.requestWindow(surface.rowOffset, surface.columnOffset + 50) }
                        }
                    }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: surface.borderColor }
        RowLayout {
            objectName: "tabularComposerFooter"
            Layout.fillWidth: true; spacing: 10
            Rectangle { width: 7; height: 7; radius: 4; color: dataState.valid ? surface.successColor : surface.mutedColor }
            ColumnLayout {
                Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 4
                Label { Layout.fillWidth: true; text: surface.hasSource ? surface.outputSummary() : "No output configured"; font.weight: Font.DemiBold; elide: Text.ElideRight }
                Label { Layout.fillWidth: true; text: dataState.export_status || (dataState.conflict ? "Configuration changed elsewhere." : dataState.dirty ? "Draft changes · apply when you are ready" : "Your source file is never modified"); color: surface.mutedColor; elide: Text.ElideRight; font.pixelSize: 11 }
            }
            ComposerButton { quiet: true; visible: surface.hasSource; text: dataState.conflict ? "Reload current" : "Refresh"; onClicked: if (composer) { if (dataState.conflict) composer.reload_current(); else composer.refresh(); } }
            ComposerButton { text: "Cancel export"; visible: !!dataState.export_busy; onClicked: composer.cancel_export() }
            ComposerButton { objectName: "tabularComposerCancel"; text: "Cancel"; onClicked: if (composer) composer.discard() }
            ComposerButton { objectName: "tabularComposerApply"; text: "Apply to node"; enabled: !!dataState.valid && !dataState.busy && !dataState.export_busy && !dataState.conflict; highlighted: true; onClicked: if (composer) composer.apply() }
        }
    }
    Dialog {
        id: dirtyCloseDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        title: "Unapplied data changes"
        modal: true
        visible: !!surface.dataState.close_pending
        closePolicy: Popup.NoAutoClose
        width: Math.min(470, parent ? parent.width - 32 : 470)
        contentItem: ColumnLayout {
            Label { text: dataState.export_busy ? "An export is running. Discarding and closing will cancel it." : "Apply this configuration before returning to the graph?"; Layout.fillWidth: true; wrapMode: Text.Wrap }
            RowLayout {
                Layout.fillWidth: true
                ComposerButton { text: "Keep editing"; onClicked: composer.keep_editing() }
                ComposerButton { text: "Discard"; onClicked: composer.discard() }
                ComposerButton { text: "Apply"; enabled: !!dataState.valid && !dataState.busy; onClicked: composer.apply() }
            }
        }
    }
}
