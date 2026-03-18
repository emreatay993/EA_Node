import QtQuick 2.15
import QtQuick.Controls 2.15

InspectorSectionCard {
    id: portSection
    property var pane

    objectName: "inspectorPortManagementCard"
    width: parent ? parent.width : implicitWidth
    visible: pane.showPortSection
    title: "Port Management"

    InspectorButton {
        pane: portSection.pane
        objectName: "inspectorDeletePortButton"
        width: parent.width
        visible: portSection.pane.canManageSubnodePorts
        destructive: true
        enabled: portSection.pane.selectedPortKey.length > 0
        text: "Delete"
        tooltipText: "Delete the selected subnode port"
        onClicked: portSection.pane.deleteSelectedPort()
    }

    Rectangle {
        objectName: "inspectorPortTabs"
        width: parent.width
        height: 44
        radius: 11
        color: portSection.pane.themePalette.input_bg
        border.color: portSection.pane.themePalette.input_border
        border.width: 1

        Row {
            anchors.fill: parent
            anchors.margins: 3
            spacing: 4

            InspectorSegmentButton {
                pane: portSection.pane
                objectName: "inspectorInputsTab"
                width: (parent.width - 4) / 2
                height: parent.height
                text: "INPUTS (" + portSection.pane.inputPortCount + ")"
                selectedStyle: portSection.pane.activePortDirection === "in"
                onClicked: portSection.pane.activePortDirection = "in"
            }

            InspectorSegmentButton {
                pane: portSection.pane
                objectName: "inspectorOutputsTab"
                width: (parent.width - 4) / 2
                height: parent.height
                text: "OUTPUTS (" + portSection.pane.outputPortCount + ")"
                selectedStyle: portSection.pane.activePortDirection === "out"
                onClicked: portSection.pane.activePortDirection = "out"
            }
        }
    }

    Text {
        width: parent.width
        visible: portSection.pane.visiblePortItems.length === 0
        wrapMode: Text.WordWrap
        text: portSection.pane.activePortDirection === "in"
            ? "No input ports are available for the current node."
            : "No output ports are available for the current node."
        color: portSection.pane.themePalette.muted_fg
        font.pixelSize: 10
    }

    Column {
        objectName: "inspectorPortList"
        width: parent.width
        spacing: 4

        Repeater {
            model: portSection.pane.visiblePortItems

            delegate: InspectorPortRow {
                pane: portSection.pane
                width: parent ? parent.width : portSection.width
                portItem: modelData
            }
        }
    }

    InspectorButton {
        pane: portSection.pane
        objectName: "inspectorAddPortButton"
        width: parent.width
        visible: portSection.pane.canManageSubnodePorts
        text: portSection.pane.activePortDirection === "in" ? "+ Input" : "+ Output"
        tooltipText: portSection.pane.activePortDirection === "in"
            ? "Add an input port to the selected subnode"
            : "Add an output port to the selected subnode"
        onClicked: portSection.pane.addSubnodePort(portSection.pane.activePortDirection)
    }
}
