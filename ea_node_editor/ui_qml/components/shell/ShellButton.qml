import QtQuick 2.15
import QtQuick.Controls 2.15

ToolButton {
    id: control
    property var themeBridgeRef: typeof themeBridge !== "undefined" ? themeBridge : null
    property var graphCanvasStateBridgeRef: typeof graphCanvasStateBridge !== "undefined" ? graphCanvasStateBridge : null
    property var uiIconsRef: typeof uiIcons !== "undefined" ? uiIcons : null
    readonly property var themePalette: control.themeBridgeRef ? control.themeBridgeRef.palette : ({})
    property bool selectedStyle: false
    property string iconName: ""
    property url iconSource: ""
    property string tooltipText: ""
    property int iconSize: iconName.length > 0 && control.uiIconsRef && control.uiIconsRef.has(iconName) ? control.uiIconsRef.defaultSize(iconName) : 16
    function _tooltipBridge() {
        return control.graphCanvasStateBridgeRef;
    }
    readonly property color foregroundColor: !control.enabled
        ? Qt.alpha(control.themePalette.muted_fg, 0.55)
        : (control.selectedStyle ? control.themePalette.tab_selected_fg : control.themePalette.tab_fg)
    readonly property color chromeBorderColor: !control.enabled
        ? Qt.alpha(control.themePalette.border, 0.65)
        : (control.selectedStyle
            ? control.themePalette.accent
            : (control.down ? control.themePalette.input_border : control.themePalette.border))
    readonly property color chromeFillColor: !control.enabled
        ? Qt.alpha(
            control.selectedStyle ? control.themePalette.accent_strong : control.themePalette.tab_bg,
            control.selectedStyle ? 0.35 : 0.9
        )
        : (control.selectedStyle
            ? control.themePalette.accent_strong
            : ((control.enabled && control.down)
                ? control.themePalette.pressed
                : ((control.enabled && control.hovered) ? control.themePalette.hover : control.themePalette.tab_bg)))
    readonly property real contentOpacity: control.enabled ? 1.0 : 0.72
    property color iconColor: control.foregroundColor
    readonly property string resolvedIconSource: iconName.length > 0
        ? (control.uiIconsRef ? control.uiIconsRef.sourceSized(iconName, iconSize, String(iconColor)) : "")
        : iconSource
    readonly property string resolvedTooltipText: tooltipText.length > 0
        ? tooltipText
        : (iconName.length > 0 && control.uiIconsRef ? control.uiIconsRef.label(iconName) : "")
    readonly property bool informationalTooltipsEnabled: {
        var bridge = control._tooltipBridge();
        if (bridge && bridge.graphics_show_tooltips !== undefined)
            return Boolean(bridge.graphics_show_tooltips);
        return true;
    }
    readonly property bool tooltipVisible: control.enabled
        && informationalTooltipsEnabled
        && hovered
        && resolvedTooltipText.length > 0
    implicitHeight: 24
    implicitWidth: Math.max(control.resolvedIconSource !== "" && control.text.length === 0 ? 28 : 64, contentRow.implicitWidth + 16)
    padding: 0
    hoverEnabled: control.enabled

    ToolTip.visible: tooltipVisible
    ToolTip.text: resolvedTooltipText
    ToolTip.delay: 300

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight
        opacity: control.contentOpacity

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
                color: control.foregroundColor
                font.pixelSize: 11
                font.bold: control.selectedStyle
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    background: Rectangle {
        radius: 2
        border.color: control.chromeBorderColor
        color: control.chromeFillColor
    }
}
