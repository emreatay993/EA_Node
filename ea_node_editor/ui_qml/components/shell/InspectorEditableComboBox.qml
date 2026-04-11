import QtQuick 2.15
import QtQuick.Controls 2.15

ComboBox {
    id: control
    property var pane
    property string placeholderText: ""
    property string selectedValue: ""
    readonly property real popupMaxHeight: 240
    readonly property var optionValues: control._optionValues()
    readonly property string activeFilterText: control.filterActive ? String(control.editText || "") : ""
    readonly property var filteredOptions: control._filteredOptionsFor(control.activeFilterText)
    property bool filterActive: false
    property bool suppressEditTextHandling: false
    property bool suppressActivatedHandling: false
    implicitHeight: 34
    editable: true
    leftPadding: 8
    rightPadding: 30
    hoverEnabled: true
    font.pixelSize: 11
    palette.buttonText: pane.themePalette.input_fg
    palette.text: pane.themePalette.input_fg
    palette.highlight: pane.selectedSurfaceColor
    palette.highlightedText: pane.themePalette.panel_title_fg
    palette.base: pane.themePalette.input_bg
    palette.window: pane.cardBackgroundColor

    signal valueActivated(string value)

    function _optionValues() {
        var values = []
        var source = control.model
        if (!source || source.length === undefined)
            return values
        for (var index = 0; index < source.length; ++index)
            values.push(String(source[index]))
        return values
    }

    function _normalizedText(value) {
        return String(value || "").toLowerCase()
    }

    function _optionIndex(value) {
        var normalizedValue = String(value || "")
        for (var index = 0; index < control.optionValues.length; ++index) {
            if (control.optionValues[index] === normalizedValue)
                return index
        }
        return -1
    }

    function _filteredOptionsFor(filterText) {
        var normalizedFilter = control._normalizedText(filterText).trim()
        var exactMatches = []
        var prefixMatches = []
        var containsMatches = []
        for (var index = 0; index < control.optionValues.length; ++index) {
            var value = control.optionValues[index]
            var normalizedValue = control._normalizedText(value)
            var option = {
                "sourceIndex": index,
                "value": value
            }
            if (!normalizedFilter.length) {
                prefixMatches.push(option)
            } else if (normalizedValue === normalizedFilter) {
                exactMatches.push(option)
            } else if (normalizedValue.indexOf(normalizedFilter) === 0) {
                prefixMatches.push(option)
            } else if (normalizedValue.indexOf(normalizedFilter) >= 0) {
                containsMatches.push(option)
            }
        }
        return exactMatches.concat(prefixMatches, containsMatches)
    }

    function _filteredIndexForSourceIndex(sourceIndex) {
        for (var index = 0; index < control.filteredOptions.length; ++index) {
            var option = control.filteredOptions[index]
            if (option && option.sourceIndex === sourceIndex)
                return index
        }
        return control.filteredOptions.length > 0 ? 0 : -1
    }

    function _setEditTextSilently(value) {
        control.suppressEditTextHandling = true
        control.editText = String(value || "")
        control.suppressEditTextHandling = false
    }

    function _syncSelectionFromValue() {
        var nextIndex = control._optionIndex(control.selectedValue)
        control.suppressActivatedHandling = true
        if (control.currentIndex !== nextIndex)
            control.currentIndex = nextIndex
        control.suppressActivatedHandling = false
        if (!control.activeFocus) {
            control.filterActive = false
            control._setEditTextSilently(control.selectedValue)
        }
    }

    function _syncCurrentIndexFromEditText() {
        var nextIndex = control._optionIndex(control.editText)
        control.suppressActivatedHandling = true
        if (control.currentIndex !== nextIndex)
            control.currentIndex = nextIndex
        control.suppressActivatedHandling = false
    }

    function _refreshPopupForFilter() {
        if (!control.activeFocus)
            return
        if (control.filteredOptions.length > 0)
            control.popup.open()
        else
            control.popup.close()
    }

    function _commitFilteredOption(option) {
        if (!option)
            return
        control.filterActive = false
        control.suppressActivatedHandling = true
        if (control.currentIndex !== option.sourceIndex)
            control.currentIndex = option.sourceIndex
        control.suppressActivatedHandling = false
        control._setEditTextSilently(option.value)
        control.popup.close()
        control.valueActivated(String(option.value || ""))
    }

    Component.onCompleted: control._syncSelectionFromValue()
    onSelectedValueChanged: control._syncSelectionFromValue()
    onEditTextChanged: {
        if (control.suppressEditTextHandling)
            return
        control.filterActive = control.activeFocus
        control._syncCurrentIndexFromEditText()
        control._refreshPopupForFilter()
    }
    onAccepted: {
        control.filterActive = false
        control._syncCurrentIndexFromEditText()
        control.popup.close()
    }
    onActivated: function(index) {
        if (control.suppressActivatedHandling || index < 0 || index >= control.optionValues.length)
            return
        control.filterActive = false
        control.valueActivated(control.optionValues[index])
    }
    onActiveFocusChanged: {
        if (!control.activeFocus) {
            control.filterActive = false
            control.popup.close()
        }
    }

    indicator: Text {
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        text: "▾"
        color: control.pane.themePalette.muted_fg
        font.pixelSize: 11
        font.bold: true
    }

    background: Rectangle {
        radius: 9
        color: control.pane.themePalette.input_bg
        border.color: control.activeFocus ? control.pane.themePalette.accent : control.pane.themePalette.input_border
        border.width: 1
    }

    delegate: ItemDelegate {
        width: ListView.view ? ListView.view.width : control.width
        highlighted: ListView.isCurrentItem
        contentItem: Text {
            text: modelData.value
            color: highlighted ? control.pane.themePalette.panel_title_fg : control.pane.themePalette.input_fg
            font.pixelSize: 11
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: highlighted ? control.pane.selectedSurfaceColor : "transparent"
            radius: 7
        }
        onClicked: control._commitFilteredOption(modelData)
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 4

        background: Rectangle {
            radius: 9
            color: control.pane.cardBackgroundColor
            border.color: control.pane.themePalette.input_border
            border.width: 1
        }

        contentItem: ListView {
            clip: true
            implicitHeight: Math.min(contentHeight, control.popupMaxHeight)
            model: control.popup.visible ? control.filteredOptions : null
            currentIndex: control._filteredIndexForSourceIndex(control.currentIndex)
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
                interactive: true
            }
        }
    }

    Text {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: control.leftPadding
        anchors.rightMargin: control.rightPadding
        text: control.placeholderText
        color: control.pane.themePalette.muted_fg
        font.pixelSize: control.font.pixelSize
        elide: Text.ElideRight
        visible: control.editable
            && !String(control.editText || "").length
            && String(control.placeholderText || "").length > 0
    }
}
