// Purpose: Consistent composer text entry, reusing shared contrast and focus behavior.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import "../../common" as Common

Common.DialogTextField {
    themePalette: ({input_bg: palette.base, input_fg: palette.text, muted_fg: palette.placeholderText,
                    input_border: palette.mid, accent: palette.highlight,
                    input_selected_fg: palette.highlightedText})
}
