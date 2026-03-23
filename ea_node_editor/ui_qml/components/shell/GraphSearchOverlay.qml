import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    readonly property var shellLibraryBridgeRef: shellLibraryBridge
    readonly property var themePalette: themeBridge.palette
    property bool filterDropdownOpen: false

    visible: root.shellLibraryBridgeRef.graph_search_open
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.verticalCenter: parent.verticalCenter
    width: Math.min(parent.width * 0.62, 760)
    height: graphSearchContent.implicitHeight + 20
    color: themePalette.panel_alt_bg
    border.color: themePalette.accent
    border.width: 1
    radius: 6
    z: 1100
    focus: visible
    activeFocusOnTab: visible

    onVisibleChanged: {
        if (!visible) {
            filterDropdownOpen = false
            return
        }
        Qt.callLater(function() {
            graphSearchField.forceActiveFocus()
            graphSearchField.selectAll()
        })
    }

    Connections {
        target: root.shellLibraryBridgeRef
        function onGraph_search_changed() {
            var index = Number(root.shellLibraryBridgeRef.graph_search_highlight_index)
            if (!root.visible || index < 0 || index >= graphSearchResultsList.count)
                return
            graphSearchResultsList.positionViewAtIndex(index, ListView.Contain)
        }
    }

    function matchFieldLabel(field) {
        var labels = {
            "title": "title",
            "node_type": "type",
            "port_label": "port",
            "description": "description",
            "category": "category",
            "properties": "property"
        }
        return labels[field] || field
    }

    function activeFilterCount() {
        var filters = root.shellLibraryBridgeRef.graph_search_active_filters
        return filters ? filters.length : 0
    }

    function isFilterActive(field) {
        var filters = root.shellLibraryBridgeRef.graph_search_active_filters
        if (!filters) return false
        for (var i = 0; i < filters.length; i++) {
            if (filters[i] === field) return true
        }
        return false
    }

    Column {
        id: graphSearchContent
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 10
        spacing: 8

        RowLayout {
            width: parent.width

            Text {
                text: "Graph Search"
                color: root.themePalette.panel_title_fg
                font.pixelSize: 12
                font.bold: true
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "Esc to close"
                color: root.themePalette.muted_fg
                font.pixelSize: 11
            }
        }

        Item {
            width: parent.width
            height: graphSearchField.height

            TextField {
                id: graphSearchField
                anchors.left: parent.left
                anchors.right: filterButton.left
                anchors.rightMargin: 4
                placeholderText: root.activeFilterCount() > 0
                    ? "Search in filtered fields..."
                    : "Search all fields"
                text: root.shellLibraryBridgeRef.graph_search_query
                selectByMouse: true
                color: root.themePalette.input_fg
                placeholderTextColor: root.themePalette.muted_fg
                Keys.priority: Keys.BeforeItem
                background: Rectangle {
                    color: root.themePalette.input_bg
                    border.color: root.themePalette.input_border
                    radius: 4
                }
                onTextChanged: root.shellLibraryBridgeRef.set_graph_search_query(text)
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Up) {
                        root.shellLibraryBridgeRef.request_graph_search_move(-1)
                        event.accepted = true
                        return
                    }
                    if (event.key === Qt.Key_Down) {
                        root.shellLibraryBridgeRef.request_graph_search_move(1)
                        event.accepted = true
                        return
                    }
                    if (event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
                        root.shellLibraryBridgeRef.request_graph_search_accept()
                        event.accepted = true
                        return
                    }
                    if (event.key === Qt.Key_Escape) {
                        if (root.filterDropdownOpen) {
                            root.filterDropdownOpen = false
                            event.accepted = true
                            return
                        }
                        root.shellLibraryBridgeRef.request_close_graph_search()
                        event.accepted = true
                    }
                }
            }

            Rectangle {
                id: filterButton
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 32
                height: graphSearchField.height
                radius: 4
                color: filterButtonMouse.containsMouse
                    ? root.themePalette.hover
                    : root.themePalette.input_bg
                border.color: root.activeFilterCount() > 0
                    ? root.themePalette.accent
                    : root.themePalette.input_border
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "\u2261"
                    color: root.activeFilterCount() > 0
                        ? root.themePalette.accent
                        : root.themePalette.input_fg
                    font.pixelSize: 16
                    font.bold: true
                }

                Rectangle {
                    visible: root.activeFilterCount() > 0
                    width: 14
                    height: 14
                    radius: 7
                    color: root.themePalette.accent
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.topMargin: -4
                    anchors.rightMargin: -4

                    Text {
                        anchors.centerIn: parent
                        text: String(root.activeFilterCount())
                        color: root.themePalette.panel_bg
                        font.pixelSize: 8
                        font.bold: true
                    }
                }

                MouseArea {
                    id: filterButtonMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.filterDropdownOpen = !root.filterDropdownOpen
                        graphSearchField.forceActiveFocus()
                    }
                }
            }
        }

        Rectangle {
            id: filterDropdown
            width: parent.width
            height: filterDropdownOpen ? filterDropdownContent.implicitHeight + 16 : 0
            visible: filterDropdownOpen
            color: root.themePalette.input_bg
            border.color: root.themePalette.input_border
            border.width: 1
            radius: 4
            clip: true

            Behavior on height { NumberAnimation { duration: 120; easing.type: Easing.OutQuad } }

            Column {
                id: filterDropdownContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 8
                spacing: 4

                Text {
                    text: "Filter by field:"
                    color: root.themePalette.muted_fg
                    font.pixelSize: 10
                }

                Grid {
                    columns: 3
                    columnSpacing: 8
                    rowSpacing: 2
                    width: parent.width

                    Repeater {
                        model: [
                            { field: "title", label: "Title" },
                            { field: "node_type", label: "Node Type" },
                            { field: "port_label", label: "Port Label" },
                            { field: "description", label: "Description" },
                            { field: "category", label: "Category" },
                            { field: "properties", label: "Properties" }
                        ]

                        CheckBox {
                            id: filterCheckBox
                            text: modelData.label
                            checked: root.isFilterActive(modelData.field)
                            hoverEnabled: true
                            spacing: 6
                            padding: 0

                            indicator: Rectangle {
                                implicitWidth: 14
                                implicitHeight: 14
                                radius: 3
                                color: filterCheckBox.checked
                                    ? root.themePalette.accent
                                    : root.themePalette.input_bg
                                border.color: filterCheckBox.checked
                                    ? root.themePalette.accent
                                    : root.themePalette.input_border
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    text: filterCheckBox.checked ? "\u2713" : ""
                                    color: filterCheckBox.checked
                                        ? root.themePalette.panel_bg
                                        : "transparent"
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }

                            contentItem: Text {
                                text: filterCheckBox.text
                                leftPadding: filterCheckBox.indicator.width + filterCheckBox.spacing
                                color: filterCheckBox.hovered
                                    ? root.themePalette.app_fg
                                    : root.themePalette.input_fg
                                font.pixelSize: 11
                                verticalAlignment: Text.AlignVCenter
                            }

                            onClicked: {
                                root.shellLibraryBridgeRef.toggle_graph_search_filter(modelData.field)
                                graphSearchField.forceActiveFocus()
                            }
                        }
                    }
                }
            }
        }

        ListView {
            id: graphSearchResultsList
            width: parent.width
            height: visible ? Math.min(
                320,
                Math.max(44, root.shellLibraryBridgeRef.graph_search_results.length * 44)
            ) : 0
            clip: true
            spacing: 2
            model: root.shellLibraryBridgeRef.graph_search_results
            visible: root.shellLibraryBridgeRef.graph_search_results.length > 0

            delegate: Rectangle {
                width: ListView.view.width
                height: 42
                radius: 3
                color: index === root.shellLibraryBridgeRef.graph_search_highlight_index
                    ? root.themePalette.accent_strong
                    : (resultMouse.containsMouse ? root.themePalette.hover : "transparent")
                border.width: index === root.shellLibraryBridgeRef.graph_search_highlight_index ? 1 : 0
                border.color: index === root.shellLibraryBridgeRef.graph_search_highlight_index
                    ? root.themePalette.accent
                    : "transparent"

                Column {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    anchors.topMargin: 4
                    anchors.bottomMargin: 4
                    spacing: 1

                    Text {
                        width: parent.width
                        text: String(modelData.node_title || "")
                        color: index === root.shellLibraryBridgeRef.graph_search_highlight_index
                            ? root.themePalette.tab_selected_fg
                            : root.themePalette.app_fg
                        font.pixelSize: 12
                        font.bold: index === root.shellLibraryBridgeRef.graph_search_highlight_index
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width
                        text: {
                            var base = String(modelData.workspace_name || "")
                                + "  |  "
                                + String(modelData.display_name || "")
                                + "  |  "
                                + String(modelData.instance_label || "")
                            var mf = String(modelData.match_field || "")
                            if (mf && mf !== "title" && mf !== "node_type")
                                base += "  \u2022  " + root.matchFieldLabel(mf)
                            return base
                        }
                        color: index === root.shellLibraryBridgeRef.graph_search_highlight_index
                            ? root.themePalette.tab_selected_fg
                            : root.themePalette.muted_fg
                        font.pixelSize: 10
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: resultMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton
                    onEntered: root.shellLibraryBridgeRef.request_graph_search_highlight(index)
                    onClicked: root.shellLibraryBridgeRef.request_graph_search_jump(index)
                }
            }
        }

        Text {
            visible: root.shellLibraryBridgeRef.graph_search_query.length > 0
                && root.shellLibraryBridgeRef.graph_search_results.length === 0
            text: "No matching nodes."
            color: root.themePalette.muted_fg
            font.pixelSize: 11
        }

        Text {
            text: "Up/Down to select, Enter to jump"
            color: root.themePalette.muted_fg
            font.pixelSize: 10
        }
    }
}
