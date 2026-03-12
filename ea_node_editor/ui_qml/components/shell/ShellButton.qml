import QtQuick 2.15
import QtQuick.Controls 2.15

ToolButton {
    id: control
    readonly property var themePalette: themeBridge.palette
    property bool selectedStyle: false
    property string iconName: ""
    property url iconSource: ""
    property string tooltipText: ""
    property int iconSize: iconName.length > 0 && uiIcons.has(iconName) ? uiIcons.defaultSize(iconName) : 16
    property color iconColor: selectedStyle ? themePalette.tab_selected_fg : themePalette.tab_fg
    readonly property string resolvedIconSource: iconName.length > 0
        ? uiIcons.sourceSized(iconName, iconSize, String(iconColor))
        : iconSource
    readonly property string resolvedTooltipText: tooltipText.length > 0
        ? tooltipText
        : (iconName.length > 0 ? uiIcons.label(iconName) : "")
    implicitHeight: 24
    implicitWidth: Math.max(control.resolvedIconSource !== "" && control.text.length === 0 ? 28 : 64, contentRow.implicitWidth + 16)
    padding: 0
    hoverEnabled: true

    ToolTip.visible: hovered && resolvedTooltipText.length > 0
    ToolTip.text: resolvedTooltipText
    ToolTip.delay: 300

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: control.text.length > 0 && control.resolvedIconSource !== "" ? 6 : 0

            Image {
                visible: control.resolvedIconSource !== ""
                source: control.resolvedIconSource
                width: control.iconSize
                height: control.iconSize
                fillMode: Image.PreserveAspectFit
                smooth: true
                mipmap: true
                sourceSize.width: control.iconSize
                sourceSize.height: control.iconSize
            }

            Text {
                id: label
                visible: control.text.length > 0
                text: control.text
                color: control.selectedStyle ? control.themePalette.tab_selected_fg : control.themePalette.tab_fg
                font.pixelSize: 11
                font.bold: control.selectedStyle
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    background: Rectangle {
        radius: 2
        border.color: control.selectedStyle
            ? control.themePalette.accent
            : (control.down ? control.themePalette.input_border : control.themePalette.border)
        color: control.selectedStyle
            ? control.themePalette.accent_strong
            : (control.down
                ? control.themePalette.pressed
                : (control.hovered ? control.themePalette.hover : control.themePalette.tab_bg))
    }
}
