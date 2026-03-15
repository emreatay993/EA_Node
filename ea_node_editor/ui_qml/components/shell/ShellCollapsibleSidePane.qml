import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    property bool paneCollapsed: false
    property string paneTitle: ""
    property string side: "right"
    property real expandedWidth: 300
    property real minExpandedWidth: 180
    property real maxExpandedWidth: 600
    property int collapsedRailWidth: 0
    property int collapsedHandleWidth: 30
    property int collapsedTabTopMargin: 112
    property int collapsedPaneZ: 10
    property int contentMargins: 10
    property int contentSpacing: 8
    property real handleFadeShift: 12
    property string collapseButtonTooltip: ""
    property string expandHandleTooltip: ""
    property alias contentData: paneContentLayout.data
    property alias headerActionsData: headerActionsLayout.data
    readonly property var themePalette: themeBridge.palette
    readonly property bool isLeftSide: String(side || "").toLowerCase() === "left"
    readonly property string collapseButtonText: root.isLeftSide ? "‹" : "›"
    readonly property string collapseButtonIconName: root.isLeftSide ? "chevrons-left" : "chevrons-right"
    readonly property string expandHandleArrow: root.isLeftSide ? "›" : "‹"
    property real animatedPaneWidth: root.paneCollapsed ? root.collapsedRailWidth : root.expandedWidth
    property real expandedContentOpacity: root.paneCollapsed ? 0 : 1
    property real collapsedHandleShift: root.paneCollapsed ? 0 : (root.isLeftSide ? -root.handleFadeShift : root.handleFadeShift)

    function refreshAncestorLayouts() {
        var candidate = root.parent
        while (candidate) {
            if (candidate.forceLayout)
                candidate.forceLayout()
            candidate = candidate.parent
        }
    }

    function collapsePane() {
        root.paneCollapsed = true
        Qt.callLater(root.refreshAncestorLayouts)
    }

    function expandPane() {
        root.paneCollapsed = false
        Qt.callLater(root.refreshAncestorLayouts)
    }

    function togglePane() {
        root.paneCollapsed = !root.paneCollapsed
        Qt.callLater(root.refreshAncestorLayouts)
    }

    Layout.preferredWidth: root.animatedPaneWidth
    Layout.minimumWidth: root.animatedPaneWidth
    Layout.maximumWidth: root.animatedPaneWidth
    implicitWidth: root.animatedPaneWidth
    Layout.fillHeight: true
    color: root.paneCollapsed ? "transparent" : root.themePalette.panel_alt_bg
    border.color: root.paneCollapsed ? "transparent" : root.themePalette.border
    z: root.paneCollapsed ? root.collapsedPaneZ : 0
    clip: false

    Behavior on animatedPaneWidth {
        enabled: !resizeHandle.pressed
        NumberAnimation {
            duration: 240
            easing.type: Easing.InOutCubic
        }
    }

    Behavior on expandedContentOpacity {
        NumberAnimation {
            duration: 150
            easing.type: Easing.OutCubic
        }
    }

    Rectangle {
        id: collapsedHandle
        objectName: "collapsedSidePaneHandle"
        width: root.collapsedHandleWidth
        height: Math.max(132, collapsedTabLabel.implicitWidth + 44)
        anchors.top: parent.top
        anchors.topMargin: root.collapsedTabTopMargin
        anchors.left: root.isLeftSide ? parent.left : undefined
        anchors.right: root.isLeftSide ? undefined : parent.right
        visible: root.paneCollapsed || opacity > 0.01
        z: 2
        color: root.themePalette.panel_bg
        border.color: root.themePalette.border
        radius: 10
        opacity: root.paneCollapsed ? 1 : 0

        transform: Translate {
            x: root.collapsedHandleShift

            Behavior on x {
                NumberAnimation {
                    duration: 170
                    easing.type: Easing.OutCubic
                }
            }
        }

        Behavior on opacity {
            NumberAnimation {
                duration: 140
                easing.type: Easing.OutCubic
            }
        }

        Rectangle {
            width: 10
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: root.isLeftSide ? parent.left : undefined
            anchors.right: root.isLeftSide ? undefined : parent.right
            color: parent.color
        }

        Column {
            anchors.centerIn: parent
            spacing: 6

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.expandHandleArrow
                color: root.themePalette.group_title_fg
                font.pixelSize: 15
                font.bold: true
            }

            Item {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 14
                height: collapsedTabLabel.implicitWidth + 6

                Text {
                    id: collapsedTabLabel
                    anchors.centerIn: parent
                    rotation: root.isLeftSide ? 90 : -90
                    transformOrigin: Item.Center
                    text: root.paneTitle
                    color: root.themePalette.group_title_fg
                    font.pixelSize: 11
                    font.bold: true
                    renderType: Text.NativeRendering
                }
            }
        }

        HoverHandler {
            id: collapsedHandleHover
            enabled: root.expandHandleTooltip.length > 0
        }

        ToolTip.visible: collapsedHandleHover.hovered && root.paneCollapsed && root.expandHandleTooltip.length > 0
        ToolTip.text: root.expandHandleTooltip

        TapHandler {
            enabled: root.paneCollapsed
            onTapped: root.expandPane()
        }
    }

    Item {
        anchors.fill: parent
        visible: root.expandedContentOpacity > 0.01
        opacity: root.expandedContentOpacity
        enabled: root.expandedContentOpacity > 0.99
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.contentMargins
            spacing: root.contentSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    text: root.paneTitle
                    color: root.themePalette.group_title_fg
                    font.pixelSize: 12
                    font.bold: true
                }

                Item {
                    Layout.fillWidth: true
                }

                RowLayout {
                    id: headerActionsLayout
                    spacing: 6
                }

                ShellButton {
                    iconName: root.collapseButtonIconName
                    iconSize: 14
                    implicitWidth: 26
                    implicitHeight: 24
                    tooltipText: root.collapseButtonTooltip
                    onClicked: root.collapsePane()

                    background: Rectangle {
                        radius: 4
                        color: parent.down
                            ? root.themePalette.pressed
                            : (parent.hovered ? root.themePalette.hover : "transparent")
                        border.color: parent.hovered || parent.down ? root.themePalette.border : "transparent"
                        border.width: 1
                    }
                }
            }

            ColumnLayout {
                id: paneContentLayout
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: root.contentSpacing
            }
        }
    }

    MouseArea {
        id: resizeHandle
        width: 6
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.right: root.isLeftSide ? parent.right : undefined
        anchors.left: root.isLeftSide ? undefined : parent.left
        visible: !root.paneCollapsed && root.expandedContentOpacity > 0.5
        cursorShape: Qt.SplitHCursor
        z: 20

        property real dragStartX: 0
        property real dragStartWidth: 0

        onPressed: {
            dragStartX = mapToItem(null, mouseX, 0).x
            dragStartWidth = root.expandedWidth
        }

        onPositionChanged: {
            if (!pressed)
                return
            var currentX = mapToItem(null, mouseX, 0).x
            var delta = root.isLeftSide
                ? (currentX - dragStartX)
                : (dragStartX - currentX)
            var newWidth = Math.max(root.minExpandedWidth,
                Math.min(root.maxExpandedWidth, dragStartWidth + delta))
            root.expandedWidth = newWidth
        }

        Rectangle {
            anchors.centerIn: parent
            width: 2
            height: 24
            radius: 1
            color: resizeHandle.containsMouse || resizeHandle.pressed
                ? root.themePalette.accent
                : root.themePalette.border
            opacity: resizeHandle.containsMouse || resizeHandle.pressed ? 1.0 : 0.0

            Behavior on opacity {
                NumberAnimation { duration: 150 }
            }
            Behavior on color {
                ColorAnimation { duration: 150 }
            }
        }
    }
}
