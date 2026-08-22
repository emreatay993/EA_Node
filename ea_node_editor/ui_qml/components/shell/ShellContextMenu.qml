import QtQuick 2.15
import "../common" as Common

Item {
    id: root
    property var actions: []
    property var tooltipPolicyBridge: typeof graphCanvasStateBridge !== "undefined" ? graphCanvasStateBridge : null
    property int minimumWidth: 182
    property int rowHeight: 34
    property int contentPadding: 6
    property int cornerRadius: 8
    property alias color: menuPanel.color
    property var themeBridgeRef: typeof themeBridge !== "undefined" ? themeBridge : null
    readonly property var themePalette: root.themeBridgeRef ? root.themeBridgeRef.palette : ({})
    readonly property int shadowDepth: 12
    readonly property var visibleActions: {
        var resolved = []
        var source = root.actions || []
        for (var i = 0; i < source.length; ++i) {
            var action = source[i]
            if (!action || action.visible === false)
                continue
            resolved.push(action)
        }
        return resolved
    }
    readonly property int separatorCount: Math.max(0, root.visibleActions.length - 1)
    readonly property int panelWidth: Math.max(root.minimumWidth, contentColumn.implicitWidth + (root.contentPadding * 2))
    readonly property int panelHeight: (root.contentPadding * 2)
        + (root.visibleActions.length * root.rowHeight)
        + root.separatorCount

    signal actionTriggered(string actionId)

    implicitWidth: root.panelWidth
    implicitHeight: root.panelHeight + root.shadowDepth
    width: implicitWidth
    height: implicitHeight

    Rectangle {
        visible: root.visibleActions.length > 0
        x: 0
        y: 10
        width: root.panelWidth
        height: root.panelHeight
        radius: root.cornerRadius + 2
        color: Qt.alpha("#000000", 0.10)
    }

    Rectangle {
        visible: root.visibleActions.length > 0
        x: 0
        y: 4
        width: root.panelWidth
        height: root.panelHeight
        radius: root.cornerRadius + 1
        color: Qt.alpha("#000000", 0.06)
    }

    Rectangle {
        id: menuPanel
        visible: root.visibleActions.length > 0
        x: 0
        y: 0
        width: root.panelWidth
        height: root.panelHeight
        radius: root.cornerRadius
        color: root.themePalette.panel_bg
        border.width: 1
        border.color: Qt.alpha(root.themePalette.input_border, 0.92)

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            radius: parent.radius
            color: Qt.alpha("#ffffff", 0.35)
        }

        Column {
            id: contentColumn
            anchors.fill: parent
            anchors.margins: root.contentPadding
            spacing: 0

            Repeater {
                model: root.visibleActions

                delegate: Item {
                    readonly property bool destructive: !!(modelData && modelData.destructive)
                    readonly property bool actionEnabled: !(modelData && modelData.enabled === false)
                    readonly property bool actionChecked: !!(modelData && modelData.checked)
                    readonly property string actionText: String(modelData && modelData.text !== undefined ? modelData.text : "")
                    readonly property string actionId: String(modelData && modelData.actionId !== undefined ? modelData.actionId : "")
                    readonly property string actionTooltipText: String(modelData && modelData.tooltipText !== undefined ? modelData.tooltipText : "")
                    readonly property string actionTooltipCategory: String(modelData && modelData.tooltipCategory !== undefined ? modelData.tooltipCategory : "general")
                    implicitWidth: actionLabel.implicitWidth + 30
                    width: contentColumn.width
                    height: root.rowHeight + (index < root.visibleActions.length - 1 ? 1 : 0)

                    Rectangle {
                        id: actionBackground
                        width: parent.width
                        height: root.rowHeight
                        radius: 6
                        color: actionEnabled && actionMouseArea.containsMouse
                            ? (destructive
                                ? Qt.alpha(root.themePalette.inspector_danger_border, 0.16)
                                : Qt.alpha(root.themePalette.accent, 0.12))
                            : "transparent"
                    }

                    Rectangle {
                        visible: actionEnabled && actionMouseArea.containsMouse
                        x: 8
                        y: 7
                        width: 3
                        height: root.rowHeight - 14
                        radius: 2
                        color: destructive
                            ? root.themePalette.inspector_danger_border
                            : root.themePalette.accent
                    }

                    Text {
                        id: actionCheck
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.verticalCenter: actionBackground.verticalCenter
                        text: actionChecked ? "\u2713" : ""
                        color: root.themePalette.accent
                        font.pixelSize: 13
                        font.bold: true
                    }

                    Text {
                        id: actionLabel
                        anchors.left: parent.left
                        anchors.leftMargin: 28
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        anchors.verticalCenter: actionBackground.verticalCenter
                        text: actionText
                        color: !actionEnabled
                            ? Qt.alpha(root.themePalette.panel_title_fg, 0.46)
                            : destructive
                            ? root.themePalette.inspector_danger_fg
                            : root.themePalette.panel_title_fg
                        font.pixelSize: 12
                        font.bold: actionEnabled && actionMouseArea.containsMouse
                        elide: Text.ElideRight
                    }

                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        anchors.verticalCenter: actionBackground.verticalCenter
                        text: String(modelData && modelData.shortcutText || "")
                        color: Qt.alpha(root.themePalette.panel_title_fg, 0.56)
                        font.pixelSize: 10
                    }

                    Rectangle {
                        visible: index < root.visibleActions.length - 1
                        x: 10
                        y: root.rowHeight
                        width: parent.width - 20
                        height: 1
                        color: Qt.alpha(root.themePalette.border, 0.55)
                    }

                    MouseArea {
                        id: actionMouseArea
                        anchors.fill: actionBackground
                        hoverEnabled: actionEnabled
                        cursorShape: actionEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: function(mouse) {
                            if (actionEnabled)
                                root.actionTriggered(actionId)
                            mouse.accepted = true
                        }
                    }

                    Common.ManagedToolTip {
                        policyBridge: root.tooltipPolicyBridge
                        category: parent.actionTooltipCategory
                        active: actionEnabled && actionMouseArea.containsMouse
                        text: parent.actionTooltipText
                        delay: 400
                    }
                }
            }
        }
    }
}
