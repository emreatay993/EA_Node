import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common" as Common
import "../common/FontFamilyOptions.js" as FontFamilyOptions
import "../graph/surface_controls" as SurfaceControls

Column {
    id: propertyEditor
    property var pane
    property var propertyItem: ({})
    readonly property string propertyKey: String(propertyItem ? propertyItem.key || "" : "")
    readonly property string editorMode: String(propertyItem ? propertyItem.editor_mode || "" : "")
    readonly property string pathDialogMode: String(propertyItem ? propertyItem.path_dialog_mode || "" : "")
    readonly property bool pathSupportsManagedCopy: !!(propertyItem && propertyItem.path_supports_managed_copy)
    readonly property bool pathSupportsExternalLink: !!(propertyItem && propertyItem.path_supports_external_link)
    readonly property string pathCurrentSourceMode: String(
        propertyItem && propertyItem.path_current_source_mode
            ? propertyItem.path_current_source_mode
            : "external_link"
    )
    readonly property bool pathSourceModeChoicesVisible: pathDialogMode !== "folder"
        && pathSupportsManagedCopy
        && pathSupportsExternalLink
    readonly property bool overriddenByInput: !!(propertyItem && propertyItem.overridden_by_input)
    readonly property bool displayValueAvailable: !propertyItem
        || typeof propertyItem.display_value_available === "undefined"
        || !!propertyItem.display_value_available
    readonly property var displayValue: propertyEditor.displayValueAvailable
        && propertyItem
        ? (propertyItem.display_value !== undefined ? propertyItem.display_value : propertyItem.value)
        : null
    readonly property bool editorEnabled: !!propertyItem
        && (typeof propertyItem.editor_enabled === "boolean"
            ? propertyItem.editor_enabled
            : !propertyEditor.overriddenByInput)
    readonly property string editorDisabledReason: String(
        propertyItem && propertyItem.editor_disabled_reason
            ? propertyItem.editor_disabled_reason
            : (propertyEditor.overriddenByInput
                ? propertyItem.override_reason || "Value supplied by connected input."
                : "")
    )
    readonly property bool searchableEnum: !!(propertyItem && propertyItem.searchable)
    readonly property bool attentionRequired: !!(propertyItem && propertyItem.attention_required)
    readonly property string metadataState: String(
        propertyItem && propertyItem.metadata_state ? propertyItem.metadata_state : ""
    )
    readonly property string metadataStatusText: {
        if (propertyEditor.metadataState === "loading")
            return "Loading DPF metadata…"
        if (propertyEditor.metadataState === "error")
            return "DPF metadata unavailable"
        if (propertyEditor.metadataState === "empty")
            return "No metadata options available"
        if (propertyEditor.attentionRequired)
            return "Action required"
        return ""
    }
    readonly property string inputPortLabel: String(propertyItem ? propertyItem.input_port_label || "" : "")
    readonly property string propertyValueText: String(
        propertyEditor.displayValue !== undefined && propertyEditor.displayValue !== null
            ? propertyEditor.displayValue
            : (!propertyEditor.displayValueAvailable && propertyEditor.overriddenByInput
                ? "\u2014"
            : ""
            )
    )

    width: parent ? parent.width : implicitWidth
    spacing: 4

    function _selectedPathSourceMode() {
        if (!propertyEditor.pathSourceModeChoicesVisible)
            return ""
        return sourceStorageCombo.currentIndex === 1 ? "managed_copy" : "external_link"
    }

    function _pathSourceModeIndex(sourceMode) {
        return String(sourceMode || "").trim().toLowerCase() === "managed_copy" ? 1 : 0
    }

    function _syncSourceStorageCombo() {
        sourceStorageCombo.currentIndex = propertyEditor._pathSourceModeIndex(propertyEditor.pathCurrentSourceMode)
    }

    function _browseAndCommitPath(currentPath, sourceMode) {
        if (!propertyEditor.pane.inspectorBridgeRef)
            return
        var normalizedSourceMode = String(sourceMode || "").trim()
        var selectedPath = normalizedSourceMode.length > 0
            ? propertyEditor.pane.inspectorBridgeRef.browse_selected_node_property_path(
                propertyEditor.propertyKey,
                currentPath,
                normalizedSourceMode
            )
            : propertyEditor.pane.inspectorBridgeRef.browse_selected_node_property_path(
                propertyEditor.propertyKey,
                currentPath
            )
        if (!String(selectedPath || "").length)
            return
        pathEditor.text = String(selectedPath)
        propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, pathEditor.text)
    }

    onPathCurrentSourceModeChanged: Qt.callLater(_syncSourceStorageCombo)
    onPathSourceModeChoicesVisibleChanged: Qt.callLater(_syncSourceStorageCombo)

    Component.onCompleted: _syncSourceStorageCombo()

    Text {
        width: parent.width
        visible: propertyEditor.editorMode !== "axis_compact"
        text: String(propertyEditor.propertyItem.label || "")
        color: propertyEditor.pane.themePalette.group_title_fg
        font.pixelSize: 10
        font.bold: true
        elide: Text.ElideRight
    }

    Text {
        width: parent.width
        visible: !propertyEditor.editorEnabled && propertyEditor.editorDisabledReason.length > 0
        objectName: "inspectorPropertyOverrideReason"
        property string propertyKey: propertyEditor.propertyKey
        text: propertyEditor.editorDisabledReason
        color: propertyEditor.pane.themePalette.muted_fg
        font.pixelSize: 10
        elide: Text.ElideRight
    }

    Text {
        width: parent.width
        visible: String(propertyEditor.propertyItem && propertyEditor.propertyItem.help_text || "").length > 0
        text: String(propertyEditor.propertyItem && propertyEditor.propertyItem.help_text || "")
        color: propertyEditor.pane.themePalette.muted_fg
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }

    Rectangle {
        objectName: "inspectorPropertyStatusChip"
        property string propertyKey: propertyEditor.propertyKey
        visible: propertyEditor.metadataStatusText.length > 0
        radius: 8
        implicitWidth: propertyStatusText.implicitWidth + 12
        implicitHeight: propertyStatusText.implicitHeight + 5
        color: propertyEditor.attentionRequired || propertyEditor.metadataState === "error"
            ? Qt.alpha(propertyEditor.pane.themePalette.inspector_danger_border, 0.16)
            : Qt.alpha(propertyEditor.pane.themePalette.accent, 0.12)
        border.width: 1
        border.color: propertyEditor.attentionRequired || propertyEditor.metadataState === "error"
            ? propertyEditor.pane.themePalette.inspector_danger_border
            : Qt.alpha(propertyEditor.pane.themePalette.accent, 0.52)

        Text {
            id: propertyStatusText
            anchors.centerIn: parent
            text: propertyEditor.metadataStatusText
            color: propertyEditor.attentionRequired || propertyEditor.metadataState === "error"
                ? propertyEditor.pane.themePalette.inspector_danger_fg
                : propertyEditor.pane.themePalette.group_title_fg
            font.pixelSize: 9
            font.bold: true
        }
    }

    Common.SecretEditor {
        objectName: "inspectorSecretEditor"
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "secret"
        editorEnabled: propertyEditor.editorEnabled
        hasValue: Boolean(
            propertyEditor.displayValue
            && propertyEditor.displayValue.has_value
        )
        accessibleName: String(propertyEditor.propertyItem.label || propertyEditor.propertyKey)
        textColor: propertyEditor.pane.themePalette.input_fg
        mutedTextColor: propertyEditor.pane.themePalette.muted_fg
        fieldColor: propertyEditor.pane.themePalette.input_bg
        borderColor: propertyEditor.pane.themePalette.input_border
        accentColor: propertyEditor.pane.themePalette.accent
        onReplaceRequested: function(plaintext) {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_secret(
                    propertyEditor.propertyKey,
                    plaintext
                )
        }
        onClearRequested: {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.clear_selected_node_secret(
                    propertyEditor.propertyKey
                )
        }
    }

    Row {
        width: parent.width
        visible: propertyEditor.overriddenByInput
        spacing: 6

        Rectangle {
            objectName: "inspectorPropertyInactiveChip"
            property string propertyKey: propertyEditor.propertyKey
            radius: 8
            implicitWidth: inactiveChipText.implicitWidth + 10
            implicitHeight: inactiveChipText.implicitHeight + 4
            color: Qt.alpha(propertyEditor.pane.themePalette.accent, 0.14)
            border.width: 1
            border.color: Qt.alpha(propertyEditor.pane.themePalette.accent, 0.36)

            Text {
                id: inactiveChipText
                anchors.centerIn: parent
                text: "Inactive"
                color: propertyEditor.pane.themePalette.group_title_fg
                font.pixelSize: 10
                font.bold: true
            }
        }
    }

    Rectangle {
        width: parent.width
        visible: propertyEditor.editorMode === "toggle"
        radius: 10
        color: propertyEditor.pane.themePalette.input_bg
        border.color: propertyEditor.pane.themePalette.input_border
        border.width: 1
        implicitHeight: 38

        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 8

            InspectorCheckBox {
                id: boolToggle
                pane: propertyEditor.pane
                enabled: propertyEditor.editorEnabled
                checked: propertyEditor.displayValueAvailable && !!propertyEditor.displayValue
                onToggled: {
                    if (propertyEditor.pane.inspectorBridgeRef)
                        propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, checked)
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: boolToggle.checked ? "Enabled" : "Disabled"
                color: propertyEditor.pane.themePalette.input_fg
                font.pixelSize: 11
            }
        }
    }

    InspectorComboBox {
        width: parent.width
        pane: propertyEditor.pane
        visible: propertyEditor.editorMode === "enum" && !propertyEditor.searchableEnum
        enabled: propertyEditor.editorEnabled
        placeholderText: propertyEditor.displayValueAvailable ? "" : "\u2014"
        model: propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values ? propertyEditor.propertyItem.enum_values : []
        currentIndex: {
            var values = propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values
                ? propertyEditor.propertyItem.enum_values
                : []
            if (!propertyEditor.displayValueAvailable)
                return -1
            var value = propertyEditor.propertyValueText
            var index = values.indexOf(value)
            return index >= 0 ? index : 0
        }
        onActivated: {
            var values = propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values
                ? propertyEditor.propertyItem.enum_values
                : []
            if (!propertyEditor.pane.inspectorBridgeRef || currentIndex < 0 || currentIndex >= values.length)
                return
            propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                propertyEditor.propertyKey,
                String(values[currentIndex])
            )
        }
    }

    InspectorEditableComboBox {
        id: searchableEnumEditor
        pane: propertyEditor.pane
        objectName: "inspectorSearchableEnumEditor"
        property string propertyKey: propertyEditor.propertyKey
        width: parent.width
        visible: propertyEditor.editorMode === "enum" && propertyEditor.searchableEnum
        enabled: propertyEditor.editorEnabled
        model: propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values
            ? propertyEditor.propertyItem.enum_values
            : []
        selectedValue: propertyEditor.propertyValueText

        function commitDeclaredValue(value) {
            var candidate = String(value || "")
            var values = propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values
                ? propertyEditor.propertyItem.enum_values
                : []
            for (var index = 0; index < values.length; ++index) {
                if (String(values[index]) !== candidate)
                    continue
                if (propertyEditor.pane.inspectorBridgeRef)
                    propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                        propertyEditor.propertyKey,
                        candidate
                    )
                return
            }
            editText = propertyEditor.propertyValueText
        }

        onValueActivated: function(value) { commitDeclaredValue(value) }
        onAccepted: commitDeclaredValue(editText)
        onActiveFocusChanged: {
            if (!activeFocus)
                editText = propertyEditor.propertyValueText
        }
    }

    SurfaceControls.GraphSurfaceIntervalSlider {
        id: intervalEditor
        objectName: "inspectorIntervalSlider"
        property string propertyKey: propertyEditor.propertyKey
        width: parent.width
        visible: propertyEditor.editorMode === "interval_slider"
        enabled: propertyEditor.editorEnabled
        from: isFinite(Number(propertyEditor.propertyItem.minimum))
            ? Number(propertyEditor.propertyItem.minimum)
            : 0
        to: isFinite(Number(propertyEditor.propertyItem.maximum))
            ? Number(propertyEditor.propertyItem.maximum)
            : 1
        stepSize: Math.max(0, Number(propertyEditor.propertyItem.step || 0))
        semanticStart: propertyEditor._intervalEndpoint("start", from)
        semanticEnd: propertyEditor._intervalEndpoint("end", to)
        displayValueAvailable: propertyEditor.displayValueAvailable
        intervalDirection: String(propertyEditor.propertyItem.interval_direction || "increasing")
        accentColor: propertyEditor.pane.themePalette.accent
        trackColor: propertyEditor.pane.themePalette.input_border
        handleFillColor: propertyEditor.pane.themePalette.input_bg
        handleBorderColor: propertyEditor.pane.themePalette.input_fg
        textColor: propertyEditor.pane.themePalette.input_fg
        disabledColor: propertyEditor.pane.themePalette.muted_fg
        onCommitRequested: function(value) {
            if (propertyEditor.editorEnabled && propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                    propertyEditor.propertyKey,
                    value
                )
        }
    }

    InspectorEditableComboBox {
        id: pinDataTypeEditor
        pane: propertyEditor.pane
        width: parent.width
        visible: propertyEditor.pane.isPinInspector
            && propertyEditor.propertyKey === "data_type"
        enabled: propertyEditor.editorEnabled
        model: propertyEditor.pane.pinDataTypeOptions
        selectedValue: String(propertyEditor.propertyItem && propertyEditor.propertyItem.value || "").toLowerCase()
        onValueActivated: function(value) {
            if (!propertyEditor.pane.inspectorBridgeRef)
                return
            propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                propertyEditor.propertyKey,
                String(value || "")
            )
        }
        onAccepted: {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, editText)
        }
        onActiveFocusChanged: {
            if (!activeFocus && propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, editText)
        }
        Component.onCompleted: editText = propertyEditor.propertyValueText
        onVisibleChanged: {
            if (visible && !activeFocus)
                editText = propertyEditor.propertyValueText
        }
    }

    InspectorEditableComboBox {
        id: editableComboEditor
        pane: propertyEditor.pane
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "editable_combo"
        enabled: propertyEditor.editorEnabled
        placeholderText: String(
            propertyEditor.propertyItem && propertyEditor.propertyItem.placeholder_text
                ? propertyEditor.propertyItem.placeholder_text
                : ""
        )
        model: propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values
            ? propertyEditor.propertyItem.enum_values
            : []
        selectedValue: propertyEditor.propertyValueText
        onValueActivated: function(value) {
            if (!propertyEditor.pane.inspectorBridgeRef)
                return
            propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                propertyEditor.propertyKey,
                String(value || "")
            )
        }
        onAccepted: {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, editText)
        }
        onActiveFocusChanged: {
            if (!activeFocus && propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, editText)
        }
        Component.onCompleted: editText = propertyEditor.propertyValueText
        onVisibleChanged: {
            if (visible && !activeFocus)
                editText = propertyEditor.propertyValueText
        }
    }

    InspectorEditableComboBox {
        id: fontFamilyEditor
        pane: propertyEditor.pane
        objectName: "inspectorFontFamilyEditor"
        property string propertyKey: propertyEditor.propertyKey
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "font_family"
        enabled: propertyEditor.editorEnabled
        placeholderText: "Search fonts"
        model: FontFamilyOptions.withDefault()
        selectedValue: FontFamilyOptions.displayName(propertyEditor.propertyValueText)
        previewValueAsFontFamily: true
        defaultFontFamilyLabel: FontFamilyOptions.DEFAULT_FONT_FAMILY_LABEL

        function commitDisplayValue(value) {
            if (!propertyEditor.pane.inspectorBridgeRef)
                return
            var display = String(value || "").trim()
            if (!display.length) {
                editText = selectedValue
                return
            }
            var family = FontFamilyOptions.canonicalFamily(display)
            if (!family.length && display.toLowerCase() !== FontFamilyOptions.DEFAULT_FONT_FAMILY_LABEL.toLowerCase()) {
                editText = selectedValue
                return
            }
            propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                propertyEditor.propertyKey,
                family
            )
            editText = FontFamilyOptions.displayName(family)
        }

        onValueActivated: function(value) {
            commitDisplayValue(value)
        }
        onAccepted: commitDisplayValue(editText)
        onActiveFocusChanged: {
            if (!activeFocus)
                commitDisplayValue(editText)
        }
        Component.onCompleted: editText = selectedValue
        onVisibleChanged: {
            if (visible && !activeFocus)
                editText = selectedValue
        }
    }

    Column {
        id: textareaEditorGroup
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "textarea"
        spacing: 6
        property string propertyKey: propertyEditor.propertyKey
        property string committedText: propertyEditor._displayEditorText()
        property string draftText: committedText
        property bool draftDirty: draftText !== committedText

        function syncDraftToCommitted() {
            draftText = committedText
            if (textareaEditor.text !== committedText)
                textareaEditor.text = committedText
        }

        function commitDraft() {
            if (!propertyEditor.pane.inspectorBridgeRef)
                return
            propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyKey, draftText)
        }

        onCommittedTextChanged: {
            if (!textareaEditor.activeFocus || !draftDirty)
                syncDraftToCommitted()
        }

        InspectorTextArea {
            id: textareaEditor
            pane: propertyEditor.pane
            objectName: "inspectorTextareaEditor"
            property string propertyKey: textareaEditorGroup.propertyKey
            width: parent.width
            enabled: propertyEditor.editorEnabled
            text: textareaEditorGroup.draftText
            onTextChanged: {
                if (textareaEditorGroup.draftText !== text)
                    textareaEditorGroup.draftText = text
            }
            Keys.onPressed: function(event) {
                if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
                        && (event.modifiers & Qt.ControlModifier)) {
                    textareaEditorGroup.commitDraft()
                    event.accepted = true
                } else if (event.key === Qt.Key_Escape) {
                    textareaEditorGroup.syncDraftToCommitted()
                    event.accepted = true
                }
            }
        }

        RowLayout {
            width: parent.width
            spacing: 6

            InspectorButton {
                pane: propertyEditor.pane
                objectName: "inspectorTextareaApplyButton"
                property string propertyKey: textareaEditorGroup.propertyKey
                compact: true
                enabled: propertyEditor.editorEnabled && textareaEditorGroup.draftDirty
                text: "Apply"
                onClicked: textareaEditorGroup.commitDraft()
            }

            InspectorButton {
                pane: propertyEditor.pane
                objectName: "inspectorTextareaResetButton"
                property string propertyKey: textareaEditorGroup.propertyKey
                compact: true
                enabled: propertyEditor.editorEnabled && textareaEditorGroup.draftDirty
                text: "Reset"
                onClicked: textareaEditorGroup.syncDraftToCommitted()
            }

            Text {
                Layout.fillWidth: true
                verticalAlignment: Text.AlignVCenter
                text: textareaEditorGroup.draftDirty
                    ? "Ctrl+Enter to commit"
                    : "Committed"
                color: propertyEditor.pane.themePalette.muted_fg
                font.pixelSize: 10
                elide: Text.ElideRight
            }
        }
    }

    Column {
        width: parent.width
        visible: !pinDataTypeEditor.visible
            && propertyEditor.editorMode === "path"
        spacing: 6

        RowLayout {
            width: parent.width
            spacing: 6

            InspectorTextField {
                id: pathEditor
                pane: propertyEditor.pane
                objectName: "inspectorPathEditor"
                property string propertyKey: propertyEditor.propertyKey
                property string pathDialogMode: propertyEditor.pathDialogMode
                Layout.fillWidth: true
                enabled: propertyEditor.editorEnabled
                text: propertyEditor._displayEditorText()
                onAccepted: {
                    if (propertyEditor.pane.inspectorBridgeRef)
                        propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, text)
                }
                onEditingFinished: {
                    if (propertyEditor.pane.inspectorBridgeRef)
                        propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, text)
                }
            }

            InspectorButton {
                pane: propertyEditor.pane
                objectName: "inspectorPathBrowseButton"
                property string propertyKey: propertyEditor.propertyKey
                property string pathDialogMode: propertyEditor.pathDialogMode
                compact: true
                enabled: propertyEditor.editorEnabled
                text: "Browse"
                iconName: "folder-open"
                onClicked: {
                    propertyEditor._browseAndCommitPath(
                        pathEditor.text,
                        propertyEditor._selectedPathSourceMode()
                    )
                }
            }
        }

        RowLayout {
            width: parent.width
            spacing: 6
            visible: propertyEditor.pathSourceModeChoicesVisible

            Text {
                Layout.alignment: Qt.AlignVCenter
                text: "Source storage"
                color: propertyEditor.pane.themePalette.muted_fg
                font.pixelSize: 10
                elide: Text.ElideRight
            }

            InspectorComboBox {
                id: sourceStorageCombo
                pane: propertyEditor.pane
                objectName: "inspectorPathSourceStorageComboBox"
                property string propertyKey: propertyEditor.propertyKey
                Layout.fillWidth: true
                enabled: propertyEditor.editorEnabled
                model: ["External", "Internal"]
                currentIndex: 0
            }
        }

        Rectangle {
            width: parent.width
            visible: !!(propertyEditor.propertyItem && propertyEditor.propertyItem.file_issue_active)
            radius: 8
            color: Qt.alpha(propertyEditor.pane.themePalette.accent, 0.12)
            border.width: 1
            border.color: Qt.alpha(propertyEditor.pane.themePalette.accent, 0.48)
            implicitHeight: issueColumn.implicitHeight + 12

            Column {
                id: issueColumn
                anchors.fill: parent
                anchors.margins: 6
                spacing: 6

                Text {
                    width: parent.width
                    text: String(propertyEditor.propertyItem && propertyEditor.propertyItem.file_issue_message || "")
                    color: propertyEditor.pane.themePalette.input_fg
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }

                InspectorButton {
                    pane: propertyEditor.pane
                    objectName: "inspectorPathRepairButton"
                    property string propertyKey: propertyEditor.propertyKey
                    compact: true
                    text: "Repair file..."
                    onClicked: {
                        if (!propertyEditor.pane.inspectorBridgeRef)
                            return
                        var repairedPath = propertyEditor.pane.inspectorBridgeRef.browse_selected_node_property_path(
                            propertyEditor.propertyKey,
                            String(propertyEditor.propertyItem && propertyEditor.propertyItem.file_issue_request || "")
                        )
                        if (!String(repairedPath || "").length)
                            return
                        pathEditor.text = String(repairedPath)
                        propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, pathEditor.text)
                    }
                }
            }
        }
    }

    InspectorColorField {
        pane: propertyEditor.pane
        width: parent.width
        tooltipCategory: "general"
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "color"
        enabled: propertyEditor.editorEnabled
        propertyKey: propertyEditor.propertyKey
        committedText: propertyEditor._displayEditorText()
    }

    Column {
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "chip_list"
        spacing: 6
        property var chipValues: propertyEditor.propertyItem && propertyEditor.propertyItem.value
            ? propertyEditor.propertyItem.value
            : []

        Flow {
            width: parent.width
            spacing: 6
            visible: chipValues.length > 0

            Repeater {
                model: chipValues

                Rectangle {
                    property int chipIndex: index
                    radius: 8
                    color: Qt.alpha(propertyEditor.pane.themePalette.accent, 0.14)
                    border.width: 1
                    border.color: Qt.alpha(propertyEditor.pane.themePalette.accent, 0.36)
                    implicitWidth: chipRow.implicitWidth + 10
                    implicitHeight: chipRow.implicitHeight + 6

                    Row {
                        id: chipRow
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            text: String(modelData || "")
                            color: propertyEditor.pane.themePalette.input_fg
                            font.pixelSize: 10
                        }

                        InspectorButton {
                            pane: propertyEditor.pane
                            compact: true
                            text: "x"
                            enabled: propertyEditor.editorEnabled
                            onClicked: {
                                if (!propertyEditor.pane.inspectorBridgeRef)
                                    return
                                var values = []
                                for (var row = 0; row < chipValues.length; ++row) {
                                    if (row !== chipIndex)
                                        values.push(String(chipValues[row] || ""))
                                }
                                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                                    propertyEditor.propertyKey,
                                    values
                                )
                            }
                        }
                    }
                }
            }
        }

        InspectorEditableComboBox {
            id: chipListEditor
            pane: propertyEditor.pane
            width: parent.width
            enabled: propertyEditor.editorEnabled
            placeholderText: String(
                propertyEditor.propertyItem && propertyEditor.propertyItem.placeholder_text
                    ? propertyEditor.propertyItem.placeholder_text
                    : "Add value"
            )
            model: propertyEditor.propertyItem && propertyEditor.propertyItem.enum_values
                ? propertyEditor.propertyItem.enum_values
                : []
            selectedValue: ""

            function commitChip(value) {
                if (!propertyEditor.pane.inspectorBridgeRef)
                    return
                var text = String(value || "").trim()
                if (!text.length)
                    return
                var values = []
                var normalized = text.toLowerCase()
                var seen = false
                for (var index = 0; index < chipValues.length; ++index) {
                    var existing = String(chipValues[index] || "")
                    values.push(existing)
                    if (existing.toLowerCase() === normalized)
                        seen = true
                }
                if (!seen)
                    values.push(text)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(
                    propertyEditor.propertyKey,
                    values
                )
                editText = ""
            }

            onValueActivated: function(value) {
                commitChip(value)
            }
            onAccepted: commitChip(editText)
        }
    }

    Rectangle {
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "summary"
        radius: 10
        color: propertyEditor.attentionRequired
            ? Qt.alpha(propertyEditor.pane.themePalette.inspector_danger_border, 0.12)
            : Qt.alpha(propertyEditor.pane.themePalette.accent, 0.10)
        border.color: propertyEditor.attentionRequired
            ? propertyEditor.pane.themePalette.inspector_danger_border
            : Qt.alpha(propertyEditor.pane.themePalette.accent, 0.34)
        border.width: 1
        implicitHeight: summaryText.implicitHeight + 16

        Text {
            id: summaryText
            objectName: "inspectorPropertySummaryValue"
            property string propertyKey: propertyEditor.propertyKey
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            text: propertyEditor._displayEditorText()
            color: propertyEditor.pane.themePalette.input_fg
            font.pixelSize: 11
            wrapMode: Text.Wrap
        }
    }

    InspectorAxisCompactEditor {
        pane: propertyEditor.pane
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "axis_compact"
        enabled: propertyEditor.editorEnabled
        propertyItem: propertyEditor.propertyItem
        overriddenByInput: propertyEditor.overriddenByInput
    }

    InspectorTextField {
        pane: propertyEditor.pane
        width: parent.width
        visible: !pinDataTypeEditor.visible && propertyEditor.editorMode === "text"
        enabled: propertyEditor.editorEnabled
        text: propertyEditor._displayEditorText()
        onAccepted: {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, text)
        }
        onEditingFinished: {
            if (propertyEditor.pane.inspectorBridgeRef)
                propertyEditor.pane.inspectorBridgeRef.set_selected_node_property(propertyEditor.propertyKey, text)
        }
    }

    function _intervalEndpoint(endpoint, fallback) {
        var candidate = propertyEditor.displayValueAvailable
            ? propertyEditor.displayValue
            : propertyEditor.propertyItem.value
        if (!candidate || typeof candidate !== "object")
            return fallback
        var value = Number(candidate[endpoint])
        return isFinite(value) ? value : fallback
    }

    function _displayEditorText() {
        if (!propertyEditor.displayValueAvailable && propertyEditor.overriddenByInput)
            return "\u2014"
        if (String(propertyEditor.propertyItem.type || "") === "json") {
            try {
                return JSON.stringify(propertyEditor.displayValue)
            } catch (error) {
                return ""
            }
        }
        return propertyEditor.propertyValueText
    }
}
