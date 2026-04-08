import QtQuick 2.15

QtObject {
    id: root
    property var host: null

    readonly property var passiveStyle: host && host.isPassiveNode && host.nodeData && host.nodeData.visual_style
        ? host.nodeData.visual_style
        : ({})
    readonly property string passiveFillOverride: host ? host._styleString(root.passiveStyle.fill_color) : ""
    readonly property string passiveBorderOverride: host ? host._styleString(root.passiveStyle.border_color) : ""
    readonly property string passiveTextOverride: host ? host._styleString(root.passiveStyle.text_color) : ""
    readonly property string passiveAccentOverride: host ? host._styleString(root.passiveStyle.accent_color) : ""
    readonly property string passiveHeaderOverride: host ? host._styleString(root.passiveStyle.header_color) : ""
    readonly property bool hasPassiveFillOverride: !!host && host.isPassiveNode && root.passiveFillOverride.length > 0
    readonly property bool hasPassiveBorderOverride: !!host && host.isPassiveNode && root.passiveBorderOverride.length > 0
    readonly property bool hasPassiveTextOverride: !!host && host.isPassiveNode && root.passiveTextOverride.length > 0
    readonly property bool hasPassiveAccentOverride: !!host && host.isPassiveNode && root.passiveAccentOverride.length > 0
    readonly property bool hasPassiveHeaderOverride: !!host && host.isPassiveNode && root.passiveHeaderOverride.length > 0

    readonly property color themeSurfaceColor: host && host.nodePalette ? (host.nodePalette.card_bg || "#1b1d22") : "#1b1d22"
    readonly property color themeOutlineColor: host && host.nodePalette ? (host.nodePalette.card_border || "#3a3d45") : "#3a3d45"
    readonly property color themeSelectedOutlineColor: host && host.nodePalette
        ? (host.nodePalette.card_selected_border || "#60CDFF")
        : "#60CDFF"
    readonly property color themeHeaderColor: host && host.nodePalette ? (host.nodePalette.header_bg || "#2a2b30") : "#2a2b30"
    readonly property color themeHeaderTextColor: host && host.nodePalette
        ? (host.nodePalette.header_fg || "#f0f4fb")
        : "#f0f4fb"
    readonly property color themeScopeBadgeColor: host && host.nodePalette
        ? (host.nodePalette.scope_badge_bg || "#1D8CE0")
        : "#1D8CE0"
    readonly property color themeScopeBadgeBorderColor: host && host.nodePalette
        ? (host.nodePalette.scope_badge_border || "#60CDFF")
        : "#60CDFF"
    readonly property color themeScopeBadgeTextColor: host && host.nodePalette
        ? (host.nodePalette.scope_badge_fg || "#f2f4f8")
        : "#f2f4f8"
    readonly property color themeInlineRowColor: host && host.nodePalette
        ? (host.nodePalette.inline_row_bg || "#24262c")
        : "#24262c"
    readonly property color themeInlineRowBorderColor: host && host.nodePalette
        ? (host.nodePalette.inline_row_border || "#4a4f5a")
        : "#4a4f5a"
    readonly property color themeInlineLabelColor: host && host.nodePalette
        ? (host.nodePalette.inline_label_fg || "#d0d5de")
        : "#d0d5de"
    readonly property color themeInlineInputTextColor: host && host.nodePalette
        ? (host.nodePalette.inline_input_fg || "#f0f2f5")
        : "#f0f2f5"
    readonly property color themeInlineInputBackgroundColor: host && host.nodePalette
        ? (host.nodePalette.inline_input_bg || "#22242a")
        : "#22242a"
    readonly property color themeInlineInputBorderColor: host && host.nodePalette
        ? (host.nodePalette.inline_input_border || "#4a4f5a")
        : "#4a4f5a"
    readonly property color themeInlineDrivenTextColor: host && host.nodePalette
        ? (host.nodePalette.inline_driven_fg || "#bdc5d3")
        : "#bdc5d3"
    readonly property color themePortLabelColor: host && host.nodePalette
        ? (host.nodePalette.port_label_fg || "#d0d5de")
        : "#d0d5de"
    readonly property color flowchartDefaultFillColor: "#F5FAFD"
    readonly property color flowchartDefaultOutlineColor: "#61798B"
    readonly property color flowchartDefaultSelectedOutlineColor: "#2C85BF"
    readonly property color flowchartDefaultTextColor: "#173247"
    readonly property color failureOutlineColor: "#FF6B57"
    readonly property color failureGlowColor: "#FFB199"
    readonly property color failureBadgeFillColor: "#421617"
    readonly property color failureBadgeBorderColor: "#FF8C74"
    readonly property color failureBadgeTextColor: "#FFE5DE"
    readonly property color runningOutlineColor: "#4A9EFF"
    readonly property color runningGlowColor: "#6EC6FF"
    readonly property color completedOutlineColor: "#4ADE80"
    readonly property color completedGlowColor: "#86EFAC"
    readonly property color runningElapsedFooterColor: root.runningOutlineColor
    readonly property color completedElapsedFooterColor: root.completedOutlineColor
    readonly property real runningElapsedFooterOpacity: 0.88
    readonly property real completedElapsedFooterOpacity: 0.72

    readonly property color surfaceColor: host && host.isPassiveNode
        ? (root.passiveFillOverride || (host.isFlowchartSurface ? root.flowchartDefaultFillColor : root.themeSurfaceColor))
        : root.themeSurfaceColor
    readonly property color outlineColor: host && host.isPassiveNode
        ? (root.passiveBorderOverride || (host.isFlowchartSurface ? root.flowchartDefaultOutlineColor : root.themeOutlineColor))
        : root.themeOutlineColor
    readonly property color selectedOutlineColor: host && host.isPassiveNode
        ? (host.isFlowchartSurface
            ? (root.hasPassiveBorderOverride
                ? Qt.lighter(root.outlineColor, 1.18)
                : root.flowchartDefaultSelectedOutlineColor)
            : Qt.lighter(root.outlineColor, 1.25))
        : root.themeSelectedOutlineColor
    readonly property color headerColor: host && host.isPassiveNode
        ? (root.passiveHeaderOverride || (host.isFlowchartSurface ? root.surfaceColor : root.themeHeaderColor))
        : root.themeHeaderColor
    readonly property color headerTextColor: host && host.isPassiveNode
        ? (root.passiveTextOverride || (host.isFlowchartSurface ? root.flowchartDefaultTextColor : root.themeHeaderTextColor))
        : root.themeHeaderTextColor
    readonly property color scopeBadgeColor: host && host.isPassiveNode
        ? (root.passiveAccentOverride || (host.isFlowchartSurface ? root.selectedOutlineColor : root.themeScopeBadgeColor))
        : root.themeScopeBadgeColor
    readonly property color scopeBadgeBorderColor: host && host.isPassiveNode
        ? Qt.lighter(root.scopeBadgeColor, 1.16)
        : root.themeScopeBadgeBorderColor
    readonly property color scopeBadgeTextColor: host && host.isPassiveNode ? "#f2f4f8" : root.themeScopeBadgeTextColor
    readonly property color inlineRowColor: host && host.isPassiveNode ? Qt.darker(root.surfaceColor, 1.04) : root.themeInlineRowColor
    readonly property color inlineRowBorderColor: host && host.isPassiveNode
        ? Qt.alpha(root.outlineColor, 0.85)
        : root.themeInlineRowBorderColor
    readonly property color inlineLabelColor: host && host.isPassiveNode
        ? Qt.alpha(root.headerTextColor, 0.82)
        : root.themeInlineLabelColor
    readonly property color inlineInputTextColor: host && host.isPassiveNode
        ? root.headerTextColor
        : root.themeInlineInputTextColor
    readonly property color inlineInputBackgroundColor: host && host.isPassiveNode
        ? Qt.darker(root.surfaceColor, 1.08)
        : root.themeInlineInputBackgroundColor
    readonly property color inlineInputBorderColor: host && host.isPassiveNode
        ? Qt.alpha(root.outlineColor, 0.9)
        : root.themeInlineInputBorderColor
    readonly property color inlineDrivenTextColor: host && host.isPassiveNode
        ? Qt.alpha(root.headerTextColor, 0.72)
        : root.themeInlineDrivenTextColor
    readonly property color portLabelColor: host && host.isPassiveNode
        ? Qt.alpha(root.headerTextColor, host.usesCardinalNeutralFlowHandles ? 0.74 : 0.84)
        : root.themePortLabelColor
    readonly property color portInteractiveFillColor: host && host.usesCardinalNeutralFlowHandles
        ? Qt.alpha(root.selectedOutlineColor, 0.18)
        : ((host && host.nodePalette) ? (host.nodePalette.port_interactive_fill || "#FFDA6B") : "#FFDA6B")
    readonly property color portInteractiveBorderColor: host && host.usesCardinalNeutralFlowHandles
        ? root.selectedOutlineColor
        : ((host && host.nodePalette) ? (host.nodePalette.port_interactive_border || "#FFE48B") : "#FFE48B")
    readonly property color portInteractiveRingFillColor: host && host.usesCardinalNeutralFlowHandles
        ? Qt.alpha(root.selectedOutlineColor, 0.1)
        : ((host && host.nodePalette) ? (host.nodePalette.port_interactive_ring_fill || "#44FFC857") : "#44FFC857")
    readonly property color portInteractiveRingBorderColor: host && host.usesCardinalNeutralFlowHandles
        ? Qt.alpha(root.selectedOutlineColor, 0.38)
        : ((host && host.nodePalette) ? (host.nodePalette.port_interactive_ring_border || "#66FFE29A") : "#66FFE29A")
    readonly property color flowchartConnectedPortFillColor: Qt.alpha(root.outlineColor, 0.18)

    readonly property real flowchartRestPortDiameter: 6.0
    readonly property real flowchartConnectedPortDiameter: 7.0
    readonly property real flowchartSelectedPortDiameter: 8.0
    readonly property real flowchartInteractivePortDiameter: 11.0
    readonly property real flowchartInteractiveRingDiameter: 15.0
    readonly property real passiveBorderWidth: host ? host._styleNumber(root.passiveStyle.border_width, 1.0, false) : 1.0
    readonly property real passiveCornerRadius: host ? host._styleNumber(root.passiveStyle.corner_radius, 6.0, true) : 6.0
    readonly property real passiveFontPixelSize: host ? host._styleNumber(root.passiveStyle.font_size, 12.0, false) : 12.0
    readonly property bool passiveFontBold: host ? host._styleString(root.passiveStyle.font_weight).toLowerCase() === "bold" : false
    readonly property real resolvedBorderWidth: host && host.isPassiveNode
        ? (host.isSelected ? Math.max(2.0, root.passiveBorderWidth) : root.passiveBorderWidth)
        : ((host && host.isSelected) ? 2.0 : 1.0)
    readonly property real resolvedCornerRadius: host && host.isPassiveNode ? root.passiveCornerRadius : 6.0
}
