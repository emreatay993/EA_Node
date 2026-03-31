import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ShellCollapsibleSidePane {
    id: root
    objectName: "inspectorPane"
    readonly property var inspectorBridgeRef: shellInspectorBridge
    property string activePortDirection: "in"
    property string selectedPortKey: ""
    property string editingPortKey: ""
    property string editingPortLabel: ""
    readonly property bool hasSelectedNode: !!root.inspectorBridgeRef && root.inspectorBridgeRef.has_selected_node
    readonly property bool isPinInspector: !!root.inspectorBridgeRef && root.inspectorBridgeRef.selected_node_is_subnode_pin
    readonly property bool showPortSection: root.hasSelectedNode && !root.isPinInspector
    readonly property bool canManageSubnodePorts: !!root.inspectorBridgeRef && root.inspectorBridgeRef.selected_node_is_subnode_shell
    readonly property bool canEditPortLabels: root.hasSelectedNode && !root.isPinInspector
    readonly property string selectedNodeTitle: root.inspectorBridgeRef ? root.inspectorBridgeRef.selected_node_title : ""
    readonly property string selectedNodeSubtitle: root.inspectorBridgeRef ? root.inspectorBridgeRef.selected_node_subtitle : ""
    readonly property bool selectedNodeCollapsible: !!root.inspectorBridgeRef && root.inspectorBridgeRef.selected_node_collapsible
    readonly property bool selectedNodeCollapsed: !!root.inspectorBridgeRef && root.inspectorBridgeRef.selected_node_collapsed
    readonly property var selectedNodePortItems: root.inspectorBridgeRef ? (root.inspectorBridgeRef.selected_node_port_items || []) : []
    readonly property var selectedNodeHeaderItems: root.inspectorBridgeRef ? (root.inspectorBridgeRef.selected_node_header_items || []) : []
    readonly property var selectedNodePropertyItems: root.inspectorBridgeRef ? (root.inspectorBridgeRef.selected_node_property_items || []) : []
    readonly property var pinDataTypeOptions: root.inspectorBridgeRef ? (root.inspectorBridgeRef.pin_data_type_options || []) : []
    readonly property var visiblePortItems: root.portItemsForDirection(activePortDirection)
    readonly property int inputPortCount: root.portItemsForDirection("in").length
    readonly property int outputPortCount: root.portItemsForDirection("out").length
    readonly property color cardBackgroundColor: root.themePalette.inspector_card_bg
    readonly property color sectionHeaderColor: root.themePalette.inspector_section_header_bg
    readonly property color selectedSurfaceColor: root.themePalette.inspector_selected_bg
    readonly property color selectedOutlineColor: root.themePalette.inspector_selected_border

    paneTitle: "PROPERTIES"
    side: "right"
    expandedWidth: 300
    contentSpacing: 0
    collapseButtonTooltip: "Collapse properties pane"
    expandHandleTooltip: "Expand properties pane"

    function portItemsForDirection(direction) {
        var normalizedDirection = String(direction || "").toLowerCase()
        var items = root.selectedNodePortItems
        var filtered = []
        for (var index = 0; index < items.length; ++index) {
            var item = items[index]
            if (!item)
                continue
            if (String(item.direction || "").toLowerCase() !== normalizedDirection)
                continue
            filtered.push(item)
        }
        return filtered
    }

    function hasVisiblePort(portKey) {
        var normalizedKey = String(portKey || "")
        if (!normalizedKey.length)
            return false
        for (var index = 0; index < visiblePortItems.length; ++index) {
            var item = visiblePortItems[index]
            if (String(item.key || "") === normalizedKey)
                return true
        }
        return false
    }

    function portItemByKey(portKey) {
        var normalizedKey = String(portKey || "")
        if (!normalizedKey.length)
            return null
        var items = root.selectedNodePortItems
        for (var index = 0; index < items.length; ++index) {
            var item = items[index]
            if (!item)
                continue
            if (String(item.key || "") === normalizedKey)
                return item
        }
        return null
    }

    function syncSelectedPortSelection() {
        if (!showPortSection || visiblePortItems.length === 0) {
            selectedPortKey = ""
            editingPortKey = ""
            editingPortLabel = ""
            return
        }
        if (!hasVisiblePort(selectedPortKey))
            selectedPortKey = String(visiblePortItems[visiblePortItems.length - 1].key || "")
        if (editingPortKey.length > 0 && !hasVisiblePort(editingPortKey)) {
            editingPortKey = ""
            editingPortLabel = ""
        }
    }

    function addSubnodePort(direction) {
        var normalizedDirection = String(direction || "").toLowerCase()
        if (!root.inspectorBridgeRef)
            return
        var createdPortKey = root.inspectorBridgeRef.request_add_selected_subnode_pin(normalizedDirection)
        if (!String(createdPortKey || "").length)
            return
        activePortDirection = normalizedDirection
        selectedPortKey = String(createdPortKey)
    }

    function selectPort(portKey) {
        var normalizedKey = String(portKey || "")
        if (!normalizedKey.length)
            return
        selectedPortKey = normalizedKey
    }

    function _isEditablePortKind(kind) {
        var k = String(kind || "").toLowerCase();
        return k !== "exec" && k !== "completed" && k !== "failed";
    }

    function beginPortLabelEdit(portKey) {
        var normalizedKey = String(portKey || "")
        if (!canEditPortLabels || !normalizedKey.length)
            return
        var item = portItemByKey(normalizedKey)
        if (!item || !root._isEditablePortKind(item.kind))
            return
        editingPortLabel = String(item ? (item.label || item.key || "") : normalizedKey)
        selectPort(normalizedKey)
        editingPortKey = normalizedKey
    }

    function commitPortLabelEdit(portKey, label) {
        var normalizedKey = String(portKey || "")
        if (editingPortKey !== normalizedKey)
            return
        if (root.inspectorBridgeRef)
            root.inspectorBridgeRef.set_selected_port_label(normalizedKey, String(label || ""))
        editingPortKey = ""
        editingPortLabel = ""
    }

    function cancelPortLabelEdit(portKey) {
        var normalizedKey = String(portKey || "")
        if (editingPortKey === normalizedKey) {
            editingPortKey = ""
            editingPortLabel = ""
        }
    }

    function focusInspectorBackground() {
        if (editingPortKey.length > 0)
            commitPortLabelEdit(editingPortKey, editingPortLabel)
        root.forceActiveFocus()
    }

    function deleteSelectedPort() {
        var normalizedKey = String(selectedPortKey || "")
        if (!root.inspectorBridgeRef || !normalizedKey.length)
            return
        focusInspectorBackground()
        root.inspectorBridgeRef.request_remove_selected_port(normalizedKey)
    }

    onVisiblePortItemsChanged: syncSelectedPortSelection()
    onShowPortSectionChanged: syncSelectedPortSelection()

    contentData: [
        Rectangle {
            objectName: "inspectorContentSurface"
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"

            TapHandler {
                enabled: root.editingPortKey.length > 0
                acceptedButtons: Qt.LeftButton
                onTapped: root.focusInspectorBackground()
            }

            ScrollView {
                id: inspectorScroll
                objectName: "inspectorScrollView"
                anchors.fill: parent
                anchors.leftMargin: 2
                anchors.rightMargin: 2
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                TapHandler {
                    enabled: root.editingPortKey.length > 0
                    acceptedButtons: Qt.LeftButton
                    onTapped: root.focusInspectorBackground()
                }

                background: Rectangle {
                    color: "transparent"

                    TapHandler {
                        acceptedButtons: Qt.LeftButton
                        onTapped: root.focusInspectorBackground()
                    }
                }

                Column {
                    id: inspectorColumn
                    width: inspectorScroll.availableWidth
                    spacing: 10

                    InspectorSectionCard {
                        pane: root
                        objectName: "inspectorEmptyStateCard"
                        width: inspectorColumn.width
                        visible: !root.hasSelectedNode
                        title: "No Selection"
                        subtitle: "Select a node on the graph to inspect its properties and exposed ports."

                        Text {
                            width: parent.width
                            text: "The selected node's definition, editable fields, and port exposure controls will appear here."
                            wrapMode: Text.WordWrap
                            color: root.themePalette.muted_fg
                            font.pixelSize: 11
                        }
                    }

                    InspectorNodeDefinitionSection {
                        pane: root
                        width: inspectorColumn.width
                    }

                    InspectorPortManagementSection {
                        pane: root
                        width: inspectorColumn.width
                    }
                }
            }
        }
    ]

    Connections {
        target: root.inspectorBridgeRef
        function onInspectorStateChanged() {
            root.syncSelectedPortSelection()
        }
    }
}
