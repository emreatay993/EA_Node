import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: control
    property var pane
    property bool destructive: false
    property bool selectedStyle: false
    property bool compact: false
    property string tooltipText: ""
    function _tooltipBridge() {
        if (typeof graphCanvasStateBridge !== "undefined" && graphCanvasStateBridge)
            return graphCanvasStateBridge;
        return null;
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
    readonly property color fillColor: !enabled
        ? pane.themePalette.tab_bg
        : destructive
            ? (down ? pane.themePalette.inspector_danger_border
                : (hovered ? pane.themePalette.inspector_danger_border : pane.themePalette.inspector_danger_bg))
            : selectedStyle
                ? pane.themePalette.accent_strong
                : (down
                    ? pane.themePalette.hover
                    : (hovered ? pane.themePalette.hover : pane.themePalette.input_bg))
    readonly property color outlineColor: destructive
        ? pane.themePalette.inspector_danger_border
        : (selectedStyle ? pane.themePalette.accent : pane.themePalette.input_border)
    readonly property color labelColor: !enabled
        ? pane.themePalette.muted_fg
        : (destructive
            ? pane.themePalette.inspector_danger_fg
            : (selectedStyle ? pane.themePalette.panel_title_fg : pane.themePalette.tab_fg))

    implicitHeight: compact ? 30 : 36
    implicitWidth: Math.max(compact ? 80 : 92, label.implicitWidth + (compact ? 18 : 22))
    hoverEnabled: true
    padding: 0

    ToolTip.visible: tooltipVisible
    ToolTip.delay: 280
    ToolTip.text: tooltipText

    contentItem: Text {
        id: label
        text: control.text
        color: control.labelColor
        font.pixelSize: control.compact ? 10 : 12
        font.bold: true
        font.letterSpacing: control.compact ? 0.5 : 0.2
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: control.compact ? 10 : 11
        color: control.fillColor
        border.color: control.outlineColor
        border.width: 1
    }
}
