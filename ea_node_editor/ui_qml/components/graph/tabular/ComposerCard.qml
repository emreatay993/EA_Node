// Purpose: Themed content grouping for the fullscreen composer.
// Map: feature_routes/tabular_data_addon_preview.md
// Tests: tests/test_tabular_composer_qml.py
import QtQuick 2.15
import QtQuick.Controls 2.15

Frame {
    id: card
    padding: 16
    background: Rectangle { radius: 10; color: card.palette.base; border.color: card.palette.mid }
}
