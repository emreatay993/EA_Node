import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "MainShellUtils.js" as MainShellUtils

Rectangle {
    id: root
    property var mainWindowRef
    readonly property var themePalette: themeBridge.palette

    Layout.preferredWidth: 300
    Layout.fillHeight: true
    color: themePalette.panel_alt_bg
    border.color: themePalette.border

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        Text {
            text: "PROPERTIES"
            color: root.themePalette.group_title_fg
            font.pixelSize: 12
            font.bold: true
        }

        Rectangle {
            Layout.fillWidth: true
            visible: root.mainWindowRef.has_selected_node
            color: root.themePalette.panel_bg
            border.color: root.themePalette.border
            radius: 10
            implicitHeight: heroContent.implicitHeight + 26

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: 1
                anchors.rightMargin: 1
                anchors.topMargin: 1
                height: 4
                radius: 10
                color: root.themePalette.accent
            }

            ColumnLayout {
                id: heroContent
                anchors.fill: parent
                anchors.margins: 12
                anchors.topMargin: 16
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Text {
                            Layout.fillWidth: true
                            text: root.mainWindowRef.selected_node_title
                            color: root.themePalette.panel_title_fg
                            font.pixelSize: 18
                            font.bold: true
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: text.length > 0
                            text: root.mainWindowRef.selected_node_subtitle
                            wrapMode: Text.WordWrap
                            color: root.themePalette.muted_fg
                            font.pixelSize: 11
                        }
                    }

                    ShellButton {
                        visible: root.mainWindowRef.selected_node_collapsible
                        text: root.mainWindowRef.selected_node_collapsed ? "Expand Node" : "Collapse Node"
                        selectedStyle: root.mainWindowRef.selected_node_collapsed
                        tooltipText: root.mainWindowRef.selected_node_collapsed
                            ? "Expand the selected node body"
                            : "Collapse the selected node body"
                        onClicked: root.mainWindowRef.set_selected_node_collapsed(!root.mainWindowRef.selected_node_collapsed)
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    width: parent.width
                    spacing: 6
                    visible: root.mainWindowRef.selected_node_header_items.length > 0

                    Repeater {
                        model: root.mainWindowRef.selected_node_header_items

                        delegate: Rectangle {
                            height: 28
                            width: chipRow.implicitWidth + 18
                            radius: 14
                            color: root.themePalette.accent_strong
                            border.color: root.themePalette.accent

                            Row {
                                id: chipRow
                                anchors.centerIn: parent
                                spacing: 6

                                Text {
                                    text: modelData.label
                                    color: root.themePalette.accent
                                    font.pixelSize: 10
                                    font.bold: true
                                }

                                Text {
                                    text: modelData.value
                                    color: root.themePalette.tab_selected_fg
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: root.themePalette.panel_bg
            border.color: root.themePalette.border
            radius: 8

            ScrollView {
                id: inspectorScroll
                anchors.fill: parent
                anchors.margins: 8
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                Column {
                    id: inspectorColumn
                    width: inspectorScroll.availableWidth
                    spacing: 10

                    Text {
                        visible: !root.mainWindowRef.has_selected_node
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: "Select a node to edit properties and port exposure."
                        color: root.themePalette.muted_fg
                        font.pixelSize: 12
                    }

                    Text {
                        visible: root.mainWindowRef.selected_node_is_subnode_pin
                        width: parent.width
                        wrapMode: Text.WordWrap
                        text: "Pin ports are configured through Label, Kind, and Data Type."
                        color: root.themePalette.accent
                        font.pixelSize: 10
                    }

                    Repeater {
                        model: root.mainWindowRef.selected_node_property_items
                        delegate: Column {
                            width: inspectorColumn.width
                            spacing: 4
                            visible: root.mainWindowRef.has_selected_node

                            Text {
                                width: parent.width
                                text: modelData.label
                                color: root.themePalette.tab_fg
                                font.pixelSize: 11
                            }

                            CheckBox {
                                width: parent.width
                                visible: modelData.type === "bool"
                                checked: !!modelData.value
                                onToggled: root.mainWindowRef.set_selected_node_property(modelData.key, checked)
                            }

                            ComboBox {
                                width: parent.width
                                visible: modelData.type === "enum"
                                model: modelData.enum_values || []
                                currentIndex: {
                                    var values = modelData.enum_values || []
                                    var value = String(modelData.value || "")
                                    var index = values.indexOf(value)
                                    return index >= 0 ? index : 0
                                }
                                onActivated: {
                                    var values = modelData.enum_values || []
                                    if (currentIndex < 0 || currentIndex >= values.length)
                                        return
                                    root.mainWindowRef.set_selected_node_property(modelData.key, String(values[currentIndex]))
                                }
                            }

                            ComboBox {
                                id: pinDataTypeEditor
                                width: parent.width
                                visible: modelData.type === "str"
                                    && modelData.key === "data_type"
                                    && root.mainWindowRef.selected_node_is_subnode_pin
                                editable: true
                                model: root.mainWindowRef.pin_data_type_options
                                currentIndex: {
                                    var values = root.mainWindowRef.pin_data_type_options || []
                                    var value = String(modelData.value || "").toLowerCase()
                                    var index = values.indexOf(value)
                                    return index
                                }
                                Component.onCompleted: {
                                    if (visible)
                                        editText = String(modelData.value || "")
                                }
                                onActivated: {
                                    var values = root.mainWindowRef.pin_data_type_options || []
                                    if (currentIndex < 0 || currentIndex >= values.length)
                                        return
                                    root.mainWindowRef.set_selected_node_property(modelData.key, String(values[currentIndex]))
                                }
                                onAccepted: root.mainWindowRef.set_selected_node_property(modelData.key, editText)
                                onActiveFocusChanged: {
                                    if (!activeFocus)
                                        root.mainWindowRef.set_selected_node_property(modelData.key, editText)
                                }
                            }

                            TextField {
                                width: parent.width
                                visible: modelData.type !== "bool"
                                    && modelData.type !== "enum"
                                    && !(modelData.type === "str"
                                        && modelData.key === "data_type"
                                        && root.mainWindowRef.selected_node_is_subnode_pin)
                                text: MainShellUtils.toEditorText(modelData)
                                selectByMouse: true
                                color: root.themePalette.input_fg
                                background: Rectangle {
                                    color: root.themePalette.input_bg
                                    border.color: root.themePalette.input_border
                                    radius: 3
                                }
                                onAccepted: root.mainWindowRef.set_selected_node_property(modelData.key, text)
                                onEditingFinished: root.mainWindowRef.set_selected_node_property(modelData.key, text)
                            }
                        }
                    }

                    Text {
                        visible: root.mainWindowRef.has_selected_node && !root.mainWindowRef.selected_node_is_subnode_pin
                        text: "Exposed Ports"
                        color: root.themePalette.muted_fg
                        font.pixelSize: 11
                        font.bold: true
                    }

                    Repeater {
                        model: root.mainWindowRef.selected_node_port_items
                        delegate: Rectangle {
                            width: inspectorColumn.width
                            height: 32
                            color: root.themePalette.tab_bg
                            border.color: root.themePalette.border
                            radius: 3
                            visible: root.mainWindowRef.has_selected_node && !root.mainWindowRef.selected_node_is_subnode_pin

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 6
                                anchors.rightMargin: 6
                                spacing: 6

                                CheckBox {
                                    checked: modelData.exposed
                                    onToggled: root.mainWindowRef.set_selected_port_exposed(modelData.key, checked)
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.direction + ":" + (modelData.label || modelData.key) + " [" + modelData.kind + " / " + modelData.data_type + "]"
                                    color: root.themePalette.app_fg
                                    font.pixelSize: 10
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
