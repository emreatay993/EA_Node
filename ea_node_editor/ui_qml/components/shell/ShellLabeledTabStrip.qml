import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

RowLayout {
    id: root
    property string titleText: ""
    property var model: []
    property var isTabActive: null
    property string densityPreset: "compact"
    property string tabLabelKey: "label"
    property int minTabWidth: 56
    property int tabHorizontalPadding: 24
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
    readonly property int createButtonHeight: root.compactDensity ? 24 : 30
    readonly property int createButtonFontSize: root.compactDensity ? 9 : 11
    readonly property int createButtonIconSize: root.compactDensity ? 14 : 18

    signal tabActivated(var itemData)
    signal contextMenuActionRequested(string actionId, var itemData)
    signal createActivated()

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

            Repeater {
                model: root.model
                delegate: Rectangle {
                    id: tabButton
                    property bool active: typeof root.isTabActive === "function"
                        ? !!root.isTabActive(modelData)
                        : false
                    height: root.tabHeight
                    width: Math.max(root.minTabWidth, tabLabel.implicitWidth + root.tabHorizontalPadding)
                    radius: root.tabRadius
                    color: active
                        ? root.themePalette.tab_selected_bg
                        : (tabMouse.containsMouse
                            ? root.themePalette.hover
                            : root.themePalette.tab_bg)
                    border.width: 1
                    border.color: active
                        ? root.themePalette.accent
                        : (tabMouse.containsMouse
                            ? root.themePalette.input_border
                            : root.themePalette.border)

                    Text {
                        id: tabLabel
                        anchors.centerIn: parent
                        text: String(
                            modelData && modelData[root.tabLabelKey] !== undefined
                                ? modelData[root.tabLabelKey]
                                : ""
                        )
                        color: active
                            ? root.themePalette.tab_selected_fg
                            : root.themePalette.tab_fg
                        font.pixelSize: root.tabFontSize
                        font.bold: active
                    }

                    MouseArea {
                        id: tabMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        acceptedButtons: Qt.LeftButton | Qt.RightButton
                        onClicked: function(mouse) {
                            if (mouse.button === Qt.LeftButton) {
                                root.tabActivated(modelData)
                                return
                            }
                            if (mouse.button === Qt.RightButton) {
                                var popupPosition = tabButton.mapToItem(root, mouse.x, mouse.y)
                                root.openContextMenu(modelData, popupPosition.x, popupPosition.y)
                            }
                        }
                    }
                }
            }

            ShellCreateButton {
                text: root.createButtonText
                accentOutline: root.createButtonAccentOutline
                buttonHeight: root.createButtonHeight
                labelFontPixelSize: root.createButtonFontSize
                iconCircleSize: root.createButtonIconSize
                contentSpacing: root.compactDensity ? 6 : 8
                cornerRadius: root.tabRadius
                onClicked: root.createActivated()
            }
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
