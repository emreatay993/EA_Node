// Purpose: Composer actions using shared dialog behavior and inherited theme tokens.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import "../../common" as Common

Common.DialogButton {
    id: control
    property bool quiet: false
    property bool compact: false
    selected: highlighted || checked
    primary: highlighted
    controlHeight: compact ? 30 : 36
    implicitWidth: Math.max(compact ? 30 : 72, contentItem.implicitWidth + 24)
    themePalette: ({input_bg: palette.base, input_fg: palette.text, muted_fg: palette.placeholderText,
                    input_border: palette.mid, accent: palette.highlight, accent_strong: palette.highlight,
                    tab_selected_fg: palette.highlightedText, hover: palette.alternateBase,
                    pressed: palette.alternateBase})
    background: Rectangle {
        radius: 7
        color: control.selected && control.enabled ? control.palette.highlight
             : control.quiet && !control.hovered && !control.down ? "transparent" : control.fillColor
        border.width: control.activeFocus ? 2 : control.quiet && !control.selected ? 0 : 1
        border.color: control.enabled && (control.activeFocus || control.selected) ? control.palette.highlight : control.palette.mid
    }
}
