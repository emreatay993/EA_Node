import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQml.Models 2.15

RowLayout {
    id: root
    property string titleText: ""
    property var model: []
    property var isTabActive: null
    property string densityPreset: "compact"
    property string tabLabelKey: "label"
    property int minTabWidth: 56
    property int tabHorizontalPadding: 24
    property int createButtonMinimumWidth: 108
    property int createButtonHorizontalPadding: 10
    property var contextMenuActions: []
    property string createButtonText: ""
    property bool createButtonAccentOutline: false
    property var contextMenuItemData: null
    readonly property var themePalette: themeBridge.palette
    readonly property bool compactDensity: String(root.densityPreset).toLowerCase() === "compact"
    readonly property int contextMenuRowHeight: 29
    readonly property int titleFontSize: root.compactDensity ? 8 : 10
    readonly property real titleLetterSpacing: root.compactDensity ? 0.9 : 1.1
    readonly property int cardVerticalPadding: root.compactDensity ? 1 : 5
    readonly property int cardHorizontalPadding: root.compactDensity ? 3 : 6
    readonly property int cardRadius: root.compactDensity ? 9 : 12
    readonly property int cardSpacing: root.compactDensity ? 3 : 5
    readonly property int tabHeight: root.compactDensity ? 22 : 28
    readonly property int tabRadius: root.compactDensity ? 7 : 9
    readonly property int tabFontSize: root.compactDensity ? 10 : 12
    readonly property int effectiveMinTabWidth: root.compactDensity
        ? Math.max(42, Math.round(root.minTabWidth * 0.82))
        : root.minTabWidth
    readonly property int effectiveTabHorizontalPadding: root.compactDensity
        ? Math.max(12, root.tabHorizontalPadding - 4)
        : root.tabHorizontalPadding
    readonly property int createButtonHeight: root.compactDensity ? 24 : 30
    readonly property int createButtonFontSize: root.compactDensity ? 9 : 11
    readonly property int createButtonIconSize: root.compactDensity ? 14 : 18
    readonly property int effectiveCreateButtonMinimumWidth: root.compactDensity
        ? Math.max(88, root.createButtonMinimumWidth - 18)
        : root.createButtonMinimumWidth
    readonly property int effectiveCreateButtonHorizontalPadding: root.compactDensity
        ? Math.max(8, root.createButtonHorizontalPadding - 2)
        : root.createButtonHorizontalPadding

    signal tabActivated(var itemData)
    signal tabMoveRequested(int fromIndex, int toIndex, var itemData)
    signal contextMenuActionRequested(string actionId, var itemData)
    signal createActivated()

    readonly property bool canReorderTabs: root.model && root.model.length !== undefined && root.model.length > 1

    function tabWidthForItem(itemData) {
        var label = ""
        if (itemData && itemData[root.tabLabelKey] !== undefined)
            label = String(itemData[root.tabLabelKey])
        labelMetrics.text = label
        return Math.max(root.effectiveMinTabWidth, labelMetrics.advanceWidth + root.effectiveTabHorizontalPadding)
    }

    function openContextMenu(itemData, positionX, positionY) {
        var actions = root.contextMenuActions || []
        if (!actions.length)
            return
        root.contextMenuItemData = itemData
        var popupWidth = Math.max(1, Number(contextActionPopup.implicitWidth) || 148)
        var popupHeight = Math.max(1, Number(contextActionPopup.implicitHeight) || root.contextMenuRowHeight)
        contextActionPopup.x = Math.max(0, Math.min(root.width - popupWidth, Math.round(Number(positionX) || 0)))
        contextActionPopup.y = Math.max(0, Math.min(root.height - popupHeight, Math.round(Number(positionY) || 0)))
        contextActionPopup.open()
    }

    implicitWidth: titleLabel.implicitWidth + spacing + stripCard.implicitWidth
    implicitHeight: Math.max(titleLabel.implicitHeight, stripCard.implicitHeight)
    spacing: root.compactDensity ? 8 : 10

    onWidthChanged: {
        if (contextActionPopup.visible)
            contextActionPopup.close()
    }

    onHeightChanged: {
        if (contextActionPopup.visible)
            contextActionPopup.close()
    }

    Text {
        id: titleLabel
        Layout.alignment: Qt.AlignVCenter
        text: root.titleText
        color: root.themePalette.muted_fg
        font.pixelSize: root.titleFontSize
        font.bold: true
        font.letterSpacing: root.titleLetterSpacing
    }

    Rectangle {
        id: stripCard
        Layout.alignment: Qt.AlignVCenter
        implicitWidth: stripRow.implicitWidth + (root.cardHorizontalPadding * 2)
        implicitHeight: stripRow.implicitHeight + (root.cardVerticalPadding * 2)
        radius: root.cardRadius
        color: root.themePalette.panel_alt_bg
        border.color: root.themePalette.border

        Row {
            id: stripRow
            anchors.fill: parent
            anchors.leftMargin: root.cardHorizontalPadding
            anchors.rightMargin: root.cardHorizontalPadding
            anchors.topMargin: root.cardVerticalPadding
            anchors.bottomMargin: root.cardVerticalPadding
            spacing: root.cardSpacing
            move: Transition {
                NumberAnimation {
                    properties: "x,y"
                    duration: 140
                    easing.type: Easing.OutCubic
                }
            }

            DelegateModel {
                id: visualModel
                model: root.model || []
                delegate: DropArea {
                    id: tabDropArea
                    property int visualIndex: DelegateModel.itemsIndex
                    property var itemData: modelData
                    readonly property int buttonWidth: root.tabWidthForItem(itemData)
                    width: buttonWidth
                    height: root.tabHeight

                    onEntered: function(drag) {
                        if (!root.canReorderTabs || drag.source === null)
                            return
                        var fromIndex = Number(drag.source.visualIndex)
                        var toIndex = Number(tabDropArea.visualIndex)
                        if (!Number.isInteger(fromIndex) || !Number.isInteger(toIndex))
                            return
                        if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex)
                            return
                        visualModel.items.move(fromIndex, toIndex)
                    }

                    Rectangle {
                        id: tabButton
                        anchors.fill: parent
                        property int dragStartIndex: -1
                        property int visualIndex: tabDropArea.visualIndex
                        property var itemData: tabDropArea.itemData
                        property bool active: typeof root.isTabActive === "function"
                            ? !!root.isTabActive(itemData)
                            : false
                        property bool dragging: dragArea.drag.active
                        radius: root.tabRadius
                        color: active
                            ? root.themePalette.tab_selected_bg
                            : (dragArea.containsMouse
                                ? root.themePalette.hover
                                : root.themePalette.tab_bg)
                        border.width: 1
                        border.color: active
                            ? root.themePalette.accent
                            : (dragArea.containsMouse
                                ? root.themePalette.input_border
                                : root.themePalette.border)
                        Drag.active: root.canReorderTabs && dragArea.drag.active
                        Drag.source: tabButton
                        Drag.hotSpot.x: dragArea.mouseX
                        Drag.hotSpot.y: dragArea.mouseY
                        z: dragging ? 20 : 0

                        states: State {
                            when: tabButton.dragging
                            ParentChange {
                                target: tabButton
                                parent: dragOverlay
                            }
                            AnchorChanges {
                                target: tabButton
                                anchors.left: undefined
                                anchors.right: undefined
                                anchors.top: undefined
                                anchors.bottom: undefined
                            }
                            PropertyChanges {
                                target: tabButton
                                width: tabDropArea.buttonWidth
                                height: root.tabHeight
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: String(
                                tabButton.itemData && tabButton.itemData[root.tabLabelKey] !== undefined
                                    ? tabButton.itemData[root.tabLabelKey]
                                    : ""
                            )
                            color: active
                                ? root.themePalette.tab_selected_fg
                                : root.themePalette.tab_fg
                            font.pixelSize: root.tabFontSize
                            font.bold: active
                        }

                        MouseArea {
                            id: dragArea
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            cursorShape: root.canReorderTabs
                                ? (dragArea.drag.active ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
                                : Qt.PointingHandCursor
                            drag.target: root.canReorderTabs ? tabButton : null
                            drag.axis: Drag.XAxis
                            drag.minimumX: 0
                            drag.maximumX: Math.max(0, dragOverlay.width - tabDropArea.buttonWidth)
                            onPressed: function(mouse) {
                                if (mouse.button === Qt.LeftButton)
                                    tabButton.dragStartIndex = tabButton.visualIndex
                            }
                            onReleased: function(mouse) {
                                if (mouse.button !== Qt.LeftButton)
                                    return
                                if (tabButton.dragging)
                                    tabButton.Drag.drop()
                                var fromIndex = tabButton.dragStartIndex
                                var toIndex = tabButton.visualIndex
                                tabButton.dragStartIndex = -1
                                if (fromIndex >= 0 && fromIndex !== toIndex)
                                    root.tabMoveRequested(fromIndex, toIndex, tabButton.itemData)
                            }
                            onClicked: function(mouse) {
                                if (mouse.button === Qt.LeftButton) {
                                    root.tabActivated(tabButton.itemData)
                                    return
                                }
                                if (mouse.button === Qt.RightButton) {
                                    var popupPosition = tabButton.mapToItem(root, mouse.x, mouse.y)
                                    root.openContextMenu(tabButton.itemData, popupPosition.x, popupPosition.y)
                                }
                            }
                        }
                    }
                }
            }

            Repeater {
                model: visualModel
            }

            ShellCreateButton {
                id: createButton
                text: root.createButtonText
                accentOutline: root.createButtonAccentOutline
                buttonHeight: root.createButtonHeight
                labelFontPixelSize: root.createButtonFontSize
                iconCircleSize: root.createButtonIconSize
                minimumButtonWidth: root.effectiveCreateButtonMinimumWidth
                contentHorizontalPadding: root.effectiveCreateButtonHorizontalPadding
                contentSpacing: root.compactDensity ? 6 : 8
                cornerRadius: root.tabRadius
                onClicked: root.createActivated()
            }
        }

        Item {
            id: dragOverlay
            anchors.fill: stripRow
            anchors.rightMargin: createButton.width + stripRow.spacing
            z: 100
        }
    }

    TextMetrics {
        id: labelMetrics
        font.pixelSize: root.tabFontSize
        font.bold: false
    }

    Popup {
        id: contextActionPopup
        parent: root
        modal: false
        focus: true
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        implicitWidth: contextActionMenu.implicitWidth
        implicitHeight: contextActionMenu.implicitHeight
        z: 1000

        background: Item {}

        contentItem: ShellContextMenu {
            id: contextActionMenu
            minimumWidth: 188
            actions: root.contextMenuActions
            onActionTriggered: function(actionId) {
                root.contextMenuActionRequested(actionId, root.contextMenuItemData)
                contextActionPopup.close()
            }
        }
    }
}
