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
    property var tabSlots: []
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

    function tabLabelForItem(itemData) {
        if (itemData && itemData[root.tabLabelKey] !== undefined)
            return String(itemData[root.tabLabelKey])
        return ""
    }

    function orderedTabSlots() {
        var slots = []
        for (var index = 0; index < root.tabSlots.length; index += 1) {
            var child = root.tabSlots[index]
            if (!child || child.width <= 0 || !child.visible)
                continue
            slots.push(child)
        }
        slots.sort(function(a, b) { return a.x - b.x })
        return slots
    }

    function reorderTargetIndexForCenterX(slots, centerX) {
        var targetIndex = slots.length - 1
        for (var slotIndex = 0; slotIndex < slots.length; slotIndex += 1) {
            var midpoint = slots[slotIndex].x + (slots[slotIndex].width / 2)
            if (centerX <= midpoint) {
                targetIndex = slotIndex
                break
            }
        }
        return targetIndex
    }

    function updateTabReorderTarget(tabButton) {
        if (!root.canReorderTabs || !tabButton || !tabsList.contentItem)
            return
        var slots = root.orderedTabSlots()
        if (!slots.length)
            return
        var centerPoint = tabButton.mapToItem(tabsList.contentItem, tabButton.width / 2, tabButton.height / 2)
        var targetIndex = root.reorderTargetIndexForCenterX(slots, centerPoint.x)
        if (targetIndex < 0 || targetIndex === tabButton.visualIndex)
            return
        visualModel.items.move(tabButton.visualIndex, targetIndex)
    }

    function setTabSlotRegistration(slot, registered) {
        if (!slot)
            return
        var nextSlots = []
        var exists = false
        for (var index = 0; index < root.tabSlots.length; index += 1) {
            var current = root.tabSlots[index]
            if (!current)
                continue
            if (current === slot) {
                exists = true
                if (!registered)
                    continue
            }
            nextSlots.push(current)
        }
        if (registered && !exists)
            nextSlots.push(slot)
        root.tabSlots = nextSlots
    }

    function registerTabSlot(slot) {
        root.setTabSlotRegistration(slot, true)
    }

    function unregisterTabSlot(slot) {
        root.setTabSlotRegistration(slot, false)
    }

    function dragMinimumXForSlot(slot) {
        if (!slot || slot.draggingInOverlay)
            return 0
        return -slot.x
    }

    function dragMaximumXForSlot(slot) {
        if (!slot)
            return 0
        var maxOffset = dragOverlay.width - slot.buttonWidth
        if (slot.draggingInOverlay)
            return Math.max(0, maxOffset)
        return Math.max(0, maxOffset - slot.x)
    }

    function resetDraggedTabPosition(tabButton) {
        if (!tabButton)
            return
        tabButton.x = 0
        tabButton.y = 0
    }

    function finalizeTabDrag(tabButton) {
        if (!tabButton)
            return
        var didReorder = tabButton.dragStartIndex >= 0 && tabButton.dragStartIndex !== tabButton.visualIndex
        tabButton.suppressClick = didReorder || tabButton.dragging
        var fromIndex = tabButton.dragStartIndex
        var toIndex = tabButton.visualIndex
        tabButton.dragStartIndex = -1
        if (fromIndex >= 0 && fromIndex !== toIndex)
            root.tabMoveRequested(fromIndex, toIndex, tabButton.itemData)
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

            DelegateModel {
                id: visualModel
                model: root.model || []
                delegate: Item {
                    id: tabSlot
                    property int visualIndex: DelegateModel.itemsIndex
                    property var itemData: modelData
                    readonly property string itemLabel: root.tabLabelForItem(itemData)
                    readonly property int buttonWidth: Math.max(
                        root.effectiveMinTabWidth,
                        Math.ceil(tabLabelMetrics.advanceWidth + root.effectiveTabHorizontalPadding)
                    )
                    readonly property bool draggingInOverlay: tabButton.parent === dragOverlay
                    // Allow non-leftmost tabs to move left before the overlay reparenting kicks in.
                    readonly property real dragMinimumX: root.dragMinimumXForSlot(tabSlot)
                    readonly property real dragMaximumX: root.dragMaximumXForSlot(tabSlot)
                    width: buttonWidth
                    height: root.tabHeight
                    Component.onCompleted: root.registerTabSlot(tabSlot)
                    Component.onDestruction: root.unregisterTabSlot(tabSlot)

                    TextMetrics {
                        id: tabLabelMetrics
                        text: tabSlot.itemLabel
                        font.pixelSize: root.tabFontSize
                        font.bold: false
                    }

                    Rectangle {
                        id: tabButton
                        width: tabSlot.buttonWidth
                        height: root.tabHeight
                        property int dragStartIndex: -1
                        property bool suppressClick: false
                        property int visualIndex: tabSlot.visualIndex
                        property var itemData: tabSlot.itemData
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
                        z: dragging ? 200 : 0
                        scale: dragging ? 1.02 : 1.0
                        opacity: dragging ? 0.98 : 1.0
                        onXChanged: {
                            if (tabButton.dragging)
                                root.updateTabReorderTarget(tabButton)
                        }
                        onDraggingChanged: {
                            if (!tabButton.dragging)
                                root.resetDraggedTabPosition(tabButton)
                        }

                        Behavior on scale {
                            NumberAnimation {
                                duration: 120
                                easing.type: Easing.OutCubic
                            }
                        }

                        states: State {
                            when: tabButton.dragging
                            ParentChange {
                                target: tabButton
                                parent: dragOverlay
                            }
                            PropertyChanges {
                                target: tabButton
                                width: tabSlot.buttonWidth
                                height: root.tabHeight
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: tabSlot.itemLabel
                            color: tabButton.active
                                ? root.themePalette.tab_selected_fg
                                : root.themePalette.tab_fg
                            font.pixelSize: root.tabFontSize
                            font.bold: tabButton.active
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
                            drag.minimumX: tabSlot.dragMinimumX
                            drag.maximumX: tabSlot.dragMaximumX
                            onPressed: function(mouse) {
                                if (mouse.button === Qt.LeftButton) {
                                    tabButton.dragStartIndex = tabButton.visualIndex
                                    tabButton.suppressClick = false
                                }
                            }
                            onReleased: function(mouse) {
                                if (mouse.button !== Qt.LeftButton)
                                    return
                                root.finalizeTabDrag(tabButton)
                            }
                            onCanceled: {
                                tabButton.dragStartIndex = -1
                                tabButton.suppressClick = false
                            }
                            onClicked: function(mouse) {
                                if (mouse.button === Qt.LeftButton) {
                                    if (tabButton.suppressClick) {
                                        tabButton.suppressClick = false
                                        return
                                    }
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

            ListView {
                id: tabsList
                orientation: ListView.Horizontal
                interactive: false
                spacing: root.cardSpacing
                clip: false
                implicitWidth: contentWidth
                implicitHeight: root.tabHeight
                width: contentWidth
                height: root.tabHeight
                model: visualModel
                displaced: Transition {
                    NumberAnimation {
                        properties: "x,y"
                        duration: 180
                        easing.type: Easing.OutCubic
                    }
                }
                moveDisplaced: Transition {
                    NumberAnimation {
                        properties: "x,y"
                        duration: 180
                        easing.type: Easing.OutCubic
                    }
                }
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
            x: stripRow.x
            y: stripRow.y
            width: tabsList.width
            height: tabsList.height
            z: 100
        }
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
