import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common/TooltipCopy.js" as TooltipCopy

// The Lanes section of a selected swimlane pool or lane: the pool's lanes in stack order (a standalone lane alone),
// each with its colour, role name, move and remove buttons, plus Add Lane. Every action is the scene's undoable lane
// command, reached through the Inspector bridge; rows keep their identity while values change, so a title being
// typed survives a refresh.
InspectorSectionCard {
    id: section
    objectName: "inspectorSwimlaneLanesCard"
    readonly property var bridge: section.pane ? section.pane.inspectorBridgeRef : null
    readonly property var rows: section.pane ? section.pane.selectedNodeSwimlaneLaneItems : []
    readonly property bool vertical: section.rows.length > 0 && String(section.rows[0].orientation || "") === "vertical"
    readonly property bool poolCollapsed: section.pane ? Boolean(section.pane.selectedNodeCollapsed) : false
    visible: !!section.pane && section.pane.hasSelectedNode && section.pane.isSwimlaneInspector
    title: "Lanes"
    subtitle: section.poolCollapsed
        ? "Expand the pool to edit its lanes."
        : (section.rows.length === 1 ? "1 lane" : section.rows.length + " lanes")

    function hasColor(value) {
        return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(String(value || "").trim())
    }

    function pickColor(laneId, currentValue) {
        if (!section.bridge)
            return
        var picked = String(section.bridge.pick_selected_swimlane_lane_color(laneId, currentValue) || "")
        if (picked.length)
            section.bridge.set_selected_swimlane_lane_color(laneId, picked)
    }

    InspectorRowsModel {
        id: laneRows
        rows: section.rows
        keyRole: "id"
    }

    Column {
        width: parent.width
        spacing: 6

        Repeater {
            model: laneRows

            delegate: Rectangle {
                id: laneRow
                required property string rowKey
                readonly property var lane: laneRows.rowsByKey[laneRow.rowKey] || ({})
                readonly property string laneId: String(laneRow.lane.lane_node_id || "")
                readonly property string laneColor: String(laneRow.lane.color || "")
                objectName: "inspectorSwimlaneLaneRow"
                width: parent ? parent.width : 0
                height: 38
                radius: 9
                color: laneRow.lane.selected ? section.pane.selectedSurfaceColor : "transparent"
                border.width: laneRow.lane.selected ? 1 : 0
                border.color: section.pane.selectedOutlineColor

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 3
                    spacing: 4

                    InspectorButton {
                        id: colorButton
                        objectName: "inspectorSwimlaneLaneColorButton"
                        pane: section.pane
                        compact: true
                        Layout.preferredWidth: 30
                        Layout.preferredHeight: 30
                        implicitWidth: 30
                        text: ""
                        enabled: !section.poolCollapsed
                        tooltipText: TooltipCopy.text(tooltipCopyBridge, "inspector.swimlane_lanes.color")
                        tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "inspector.swimlane_lanes.color")
                        onClicked: section.pickColor(laneRow.laneId, laneRow.laneColor)
                        // A right click gives the lane back the theme's colour.
                        TapHandler {
                            acceptedButtons: Qt.RightButton
                            onTapped: {
                                if (section.bridge)
                                    section.bridge.set_selected_swimlane_lane_color(laneRow.laneId, "")
                            }
                        }

                        background: Rectangle {
                            radius: 8
                            color: section.pane.themePalette.input_bg
                            border.width: 1
                            border.color: colorButton.hovered ? section.pane.themePalette.accent : section.pane.themePalette.input_border

                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: 5
                                radius: 5
                                color: section.hasColor(laneRow.laneColor)
                                    ? laneRow.laneColor
                                    : Qt.alpha(section.pane.themePalette.tab_bg, 0.75)
                                border.width: section.hasColor(laneRow.laneColor) ? 0 : 1
                                border.color: section.pane.themePalette.input_border
                            }
                        }
                    }

                    InspectorTextField {
                        id: titleField
                        objectName: "inspectorSwimlaneLaneTitleField"
                        pane: section.pane
                        Layout.fillWidth: true
                        implicitHeight: 30
                        enabled: !section.poolCollapsed
                        readonly property string committedTitle: String(laneRow.lane.title || "")
                        text: committedTitle
                        onCommittedTitleChanged: {
                            if (!activeFocus)
                                text = committedTitle
                        }
                        function commit() {
                            var value = text.trim()
                            if (!value.length || value === committedTitle) {
                                text = committedTitle
                                return
                            }
                            if (section.bridge)
                                section.bridge.set_selected_swimlane_lane_title(laneRow.laneId, value)
                        }
                        onAccepted: commit()
                        onEditingFinished: commit()
                    }

                    InspectorButton {
                        objectName: "inspectorSwimlaneLaneMoveUpButton"
                        pane: section.pane
                        compact: true
                        Layout.preferredWidth: 28
                        implicitWidth: 28
                        text: ""
                        iconName: "chevron-up"
                        enabled: !section.poolCollapsed && Boolean(laneRow.lane.can_move_up)
                        tooltipText: TooltipCopy.text(
                            tooltipCopyBridge,
                            section.vertical ? "inspector.swimlane_lanes.move_left" : "inspector.swimlane_lanes.move_up")
                        tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "inspector.swimlane_lanes.move_up")
                        onClicked: {
                            if (section.bridge)
                                section.bridge.move_selected_swimlane_lane(laneRow.laneId, -1)
                        }
                    }

                    InspectorButton {
                        objectName: "inspectorSwimlaneLaneMoveDownButton"
                        pane: section.pane
                        compact: true
                        Layout.preferredWidth: 28
                        implicitWidth: 28
                        text: ""
                        iconName: "chevron-down"
                        enabled: !section.poolCollapsed && Boolean(laneRow.lane.can_move_down)
                        tooltipText: TooltipCopy.text(
                            tooltipCopyBridge,
                            section.vertical ? "inspector.swimlane_lanes.move_right" : "inspector.swimlane_lanes.move_down")
                        tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "inspector.swimlane_lanes.move_down")
                        onClicked: {
                            if (section.bridge)
                                section.bridge.move_selected_swimlane_lane(laneRow.laneId, 1)
                        }
                    }

                    InspectorButton {
                        objectName: "inspectorSwimlaneLaneRemoveButton"
                        pane: section.pane
                        compact: true
                        destructive: true
                        Layout.preferredWidth: 28
                        implicitWidth: 28
                        text: ""
                        iconName: "delete"
                        enabled: !section.poolCollapsed
                        tooltipText: TooltipCopy.text(tooltipCopyBridge, "inspector.swimlane_lanes.remove")
                        tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "inspector.swimlane_lanes.remove")
                        onClicked: {
                            if (section.bridge)
                                section.bridge.remove_selected_swimlane_lane(laneRow.laneId)
                        }
                    }
                }
            }
        }

        InspectorButton {
            objectName: "inspectorAddSwimlaneLaneButton"
            pane: section.pane
            compact: true
            width: parent.width
            text: "Add Lane"
            iconName: "plus"
            enabled: !section.poolCollapsed
            tooltipText: TooltipCopy.text(tooltipCopyBridge, "inspector.swimlane_lanes.add")
            tooltipCategory: TooltipCopy.category(tooltipCopyBridge, "inspector.swimlane_lanes.add")
            onClicked: {
                if (section.bridge)
                    section.bridge.add_selected_swimlane_lane()
            }
        }
    }
}
