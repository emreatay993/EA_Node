import QtQuick 2.15
import QtQuick.Controls 2.15

ToolButton {
    id: control
    property bool selectedStyle: false
    property string iconName: ""
    property url iconSource: ""
    property string tooltipText: ""
    property int iconSize: iconName.length > 0 && uiIcons.has(iconName) ? uiIcons.defaultSize(iconName) : 16
    property color iconColor: selectedStyle ? "#DFF2FF" : "#D8DEEA"
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
                color: control.selectedStyle ? "#DFF2FF" : "#D8DEEA"
                font.pixelSize: 11
                font.bold: control.selectedStyle
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    background: Rectangle {
        radius: 2
        border.color: control.down ? "#5A606B" : "#4A4E58"
        color: control.selectedStyle
            ? "#2A4F68"
            : (control.down ? "#3A3E46" : (control.hovered ? "#343943" : "#2B2F37"))
    }
}
