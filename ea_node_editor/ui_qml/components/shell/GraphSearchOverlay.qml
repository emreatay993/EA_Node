import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property var mainWindowRef
    readonly property var themePalette: themeBridge.palette

    visible: root.mainWindowRef.graph_search_open
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
        if (!visible)
            return
        Qt.callLater(function() {
            graphSearchField.forceActiveFocus()
            graphSearchField.selectAll()
        })
    }

    Connections {
        target: root.mainWindowRef
        function onGraph_search_changed() {
            var index = Number(root.mainWindowRef.graph_search_highlight_index)
            if (!root.visible || index < 0 || index >= graphSearchResultsList.count)
                return
            graphSearchResultsList.positionViewAtIndex(index, ListView.Contain)
        }
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

        TextField {
            id: graphSearchField
            width: parent.width
            placeholderText: "Search title or node type"
            text: root.mainWindowRef.graph_search_query
            selectByMouse: true
            color: root.themePalette.input_fg
            placeholderTextColor: root.themePalette.muted_fg
            Keys.priority: Keys.BeforeItem
            background: Rectangle {
                color: root.themePalette.input_bg
                border.color: root.themePalette.input_border
                radius: 4
            }
            onTextChanged: root.mainWindowRef.set_graph_search_query(text)
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Up) {
                    root.mainWindowRef.request_graph_search_move(-1)
                    event.accepted = true
                    return
                }
                if (event.key === Qt.Key_Down) {
                    root.mainWindowRef.request_graph_search_move(1)
                    event.accepted = true
                    return
                }
                if (event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
                    root.mainWindowRef.request_graph_search_accept()
                    event.accepted = true
                    return
                }
                if (event.key === Qt.Key_Escape) {
                    root.mainWindowRef.request_close_graph_search()
                    event.accepted = true
                }
            }
        }

        ListView {
            id: graphSearchResultsList
            width: parent.width
            height: visible ? Math.min(
                320,
                Math.max(44, root.mainWindowRef.graph_search_results.length * 44)
            ) : 0
            clip: true
            spacing: 2
            model: root.mainWindowRef.graph_search_results
            visible: root.mainWindowRef.graph_search_results.length > 0

            delegate: Rectangle {
                width: ListView.view.width
                height: 42
                radius: 3
                color: index === root.mainWindowRef.graph_search_highlight_index
                    ? root.themePalette.accent_strong
                    : (resultMouse.containsMouse ? root.themePalette.hover : "transparent")
                border.width: index === root.mainWindowRef.graph_search_highlight_index ? 1 : 0
                border.color: index === root.mainWindowRef.graph_search_highlight_index
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
                        color: index === root.mainWindowRef.graph_search_highlight_index
                            ? root.themePalette.tab_selected_fg
                            : root.themePalette.app_fg
                        font.pixelSize: 12
                        font.bold: index === root.mainWindowRef.graph_search_highlight_index
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width
                        text: String(modelData.workspace_name || "")
                            + "  |  "
                            + String(modelData.display_name || "")
                            + "  |  "
                            + String(modelData.type_id || "")
                        color: index === root.mainWindowRef.graph_search_highlight_index
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
                    onEntered: root.mainWindowRef.request_graph_search_highlight(index)
                    onClicked: root.mainWindowRef.request_graph_search_jump(index)
                }
            }
        }

        Text {
            visible: root.mainWindowRef.graph_search_query.length > 0
                && root.mainWindowRef.graph_search_results.length === 0
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
