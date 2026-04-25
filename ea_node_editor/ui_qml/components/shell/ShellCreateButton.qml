import QtQuick 2.15
import QtQuick.Controls 2.15

ToolButton {
    id: control
    property var themeBridgeRef: typeof themeBridge !== "undefined" ? themeBridge : null
    property var graphCanvasStateBridgeRef: typeof graphCanvasStateBridge !== "undefined" ? graphCanvasStateBridge : null
    readonly property var themePalette: control.themeBridgeRef ? control.themeBridgeRef.palette : ({})
    property string tooltipText: text
    function _tooltipBridge() {
        return control.graphCanvasStateBridgeRef;
    }
    readonly property bool informationalTooltipsEnabled: {
        var bridge = control._tooltipBridge();
        if (bridge && bridge.graphics_show_tooltips !== undefined)
            return Boolean(bridge.graphics_show_tooltips);
        return true;
    }
    readonly property bool tooltipVisible: informationalTooltipsEnabled
        && hovered
        && tooltipText.length > 0
    property bool accentOutline: false
    property int buttonHeight: 30
    property int labelFontPixelSize: 11
    property int iconCircleSize: 18
    property int iconBarLong: Math.max(8, control.iconCircleSize - 8)
    property int iconBarShort: 2
    property int cornerRadius: 9
    property int contentSpacing: 8
    property int minimumButtonWidth: 108
    property int contentHorizontalPadding: 10

    implicitHeight: control.buttonHeight
    implicitWidth: Math.max(
        control.minimumButtonWidth,
        contentRow.implicitWidth + (control.contentHorizontalPadding * 2)
    )
    padding: 0
    hoverEnabled: true

    ToolTip.visible: tooltipVisible
    ToolTip.text: tooltipText
    ToolTip.delay: 300

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: control.contentSpacing

            Rectangle {
                width: control.iconCircleSize
                height: control.iconCircleSize
                radius: control.iconCircleSize / 2
                color: control.themePalette.accent

                Rectangle {
                    anchors.centerIn: parent
                    width: control.iconBarLong
                    height: control.iconBarShort
                    radius: 1
                    color: "#ffffff"
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: control.iconBarShort
                    height: control.iconBarLong
                    radius: 1
                    color: "#ffffff"
                }
            }

            Text {
                text: control.text
                color: control.themePalette.panel_title_fg
                font.pixelSize: control.labelFontPixelSize
                font.bold: true
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    background: Rectangle {
        radius: control.cornerRadius
        border.width: 1
        border.color: control.down
            ? control.themePalette.accent
            : ((control.hovered || control.accentOutline)
                ? control.themePalette.accent
                : control.themePalette.border)
        color: control.down
            ? control.themePalette.pressed
            : (control.hovered ? control.themePalette.hover : control.themePalette.panel_alt_bg)
    }
}
