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
    property string createButtonText: ""
    property bool createButtonAccentOutline: false
    readonly property var themePalette: themeBridge.palette
    readonly property bool compactDensity: String(root.densityPreset).toLowerCase() === "compact"
    readonly property int titleFontSize: root.compactDensity ? 8 : 10
    readonly property real titleLetterSpacing: root.compactDensity ? 0.9 : 1.1
    readonly property int cardVerticalPadding: root.compactDensity ? 1 : 5
    readonly property int cardHorizontalPadding: root.compactDensity ? 6 : 8
    readonly property int cardRadius: root.compactDensity ? 9 : 12
    readonly property int cardSpacing: root.compactDensity ? 4 : 6
    readonly property int tabHeight: root.compactDensity ? 22 : 28
    readonly property int tabRadius: root.compactDensity ? 7 : 9
    readonly property int tabFontSize: root.compactDensity ? 10 : 12
    readonly property int createButtonHeight: root.compactDensity ? 24 : 30
    readonly property int createButtonFontSize: root.compactDensity ? 9 : 11
    readonly property int createButtonIconSize: root.compactDensity ? 14 : 18

    signal tabActivated(var itemData)
    signal createActivated()

    implicitWidth: titleLabel.implicitWidth + spacing + stripCard.implicitWidth
    implicitHeight: Math.max(titleLabel.implicitHeight, stripCard.implicitHeight)
    spacing: 10

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
                        onClicked: root.tabActivated(modelData)
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
}
