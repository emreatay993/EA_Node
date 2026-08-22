import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQml 2.15
import "TooltipPolicy.js" as TooltipPolicy

ToolTip {
    id: control
    property var policyBridge: null
    property var themeBridgeRef: typeof themeBridge !== "undefined" ? themeBridge : null
    property string category: TooltipPolicy.GENERAL
    property bool active: false
    property int textFormat: Text.PlainText
    property int maximumTextWidth: 360
    property bool screenStablePositioning: false
    property real anchorScale: 1.0
    property real screenGap: 3.0
    property string screenStablePlacement: "above"
    readonly property var themePalette: control.themeBridgeRef ? control.themeBridgeRef.palette : ({})
    readonly property color resolvedBackgroundColor: control.themePalette.panel_alt_bg
        || control.themePalette.panel_bg
        || "#24262c"
    readonly property color resolvedBorderColor: control.themePalette.input_border
        || control.themePalette.border
        || "#4a4f5a"
    readonly property color resolvedTextColor: control.themePalette.app_fg
        || control.themePalette.panel_title_fg
        || "#e8e8e8"
    readonly property bool policyAllowsTooltip: TooltipPolicy.categoryEnabled(policyBridge, category)
    readonly property bool managedVisible: TooltipPolicy.tooltipVisible(
        policyBridge,
        category,
        active && text.length > 0
    )
    readonly property real _resolvedAnchorScale: Math.max(0.1, Number(anchorScale || 1.0))
    readonly property real _screenStableX: {
        if (!parent)
            return control.x;
        if (control.screenStablePlacement === "left")
            return -(control.width + control.screenGap) / control._resolvedAnchorScale;
        if (control.screenStablePlacement === "right")
            return parent.width + control.screenGap / control._resolvedAnchorScale;
        return parent.width * 0.5 - control.width / (2 * control._resolvedAnchorScale);
    }
    readonly property real _screenStableY: {
        if (!parent)
            return control.y;
        if (control.screenStablePlacement === "below")
            return parent.height + control.screenGap / control._resolvedAnchorScale;
        if (control.screenStablePlacement === "left" || control.screenStablePlacement === "right")
            return parent.height * 0.5 - control.height / (2 * control._resolvedAnchorScale);
        return -(control.height + control.screenGap) / control._resolvedAnchorScale;
    }

    visible: managedVisible
    leftPadding: 12
    rightPadding: 12
    topPadding: 8
    bottomPadding: 8
    // Render as a real popup window so tooltips composite above native child
    // widgets (embedded plot/viewer/web surfaces). Platforms without popup
    // window support silently fall back to the in-scene item.
    popupType: Popup.Window
    // Enlarge the background below the control so the soft-shadow tail stays
    // inside the popup window instead of being clipped at the control bounds.
    bottomInset: -8

    contentItem: Text {
        text: control.text
        color: control.resolvedTextColor
        font: control.font
        textFormat: control.textFormat
        wrapMode: Text.WordWrap
        width: Math.min(implicitWidth, control.maximumTextWidth)
    }

    background: Item {
        Rectangle {
            x: 0
            y: 8
            width: parent.width
            height: parent.height - 8
            radius: 10
            color: Qt.alpha("#000000", 0.10)
        }

        Rectangle {
            x: 0
            y: 4
            width: parent.width
            height: parent.height - 8
            radius: 9
            color: Qt.alpha("#000000", 0.06)
        }

        Rectangle {
            id: tooltipPanel
            objectName: "managedToolTipPanel"
            anchors.fill: parent
            anchors.bottomMargin: 8
            radius: 8
            color: control.resolvedBackgroundColor
            border.width: 1
            border.color: Qt.alpha(control.resolvedBorderColor, 0.92)
        }
    }

    Binding {
        target: control
        property: "x"
        value: control._screenStableX
        when: control.screenStablePositioning
        restoreMode: Binding.RestoreBindingOrValue
    }

    Binding {
        target: control
        property: "y"
        value: control._screenStableY
        when: control.screenStablePositioning
        restoreMode: Binding.RestoreBindingOrValue
    }
}
