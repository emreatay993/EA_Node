# Purpose: Prove QML presentation updates retain delegates until identities change.
# Map: feature_routes/run_controller_selected_workspace_state
# Tests: this file
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtQml import QQmlComponent, QQmlEngine


def test_qml_value_updates_retain_editor_rows_and_contract_changes_rebuild(qapp):
    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.setData(
        b"""
        import QtQuick 2.15
        import "../ea_node_editor/ui_qml/components/common/PresentationModelKeys.js" as Keys
        Item {
            id: root
            property var rows: []
            property var keys: []
            property int createdRows: 0
            property int removedRows: 0
            readonly property var firstRow: repeater.count > 0 ? repeater.itemAt(0) : null
            onRowsChanged: keys = Keys.retain(keys, Keys.properties(rows))
            Repeater {
                id: repeater
                model: root.keys
                delegate: Item {
                    required property int index
                    property string settingKey: root.rows[index].key
                    property int settingValue: root.rows[index].value
                    Component.onCompleted: root.createdRows += 1
                    Component.onDestruction: root.removedRows += 1
                }
            }
        }
    """,
        QUrl.fromLocalFile(str(Path(__file__).resolve().with_suffix(".qml"))),
    )
    assert component.isReady(), [error.toString() for error in component.errors()]
    root = component.create()
    assert root is not None
    items = [
        {"key": "a", "type": "int", "value": 1},
        {"key": "b", "type": "int", "value": 2},
    ]
    root.setProperty("rows", items)
    qapp.processEvents()
    row = root.property("firstRow")
    assert root.property("createdRows") == 2
    root.setProperty("rows", [{**items[0], "value": 7}, items[1]])
    qapp.processEvents()
    assert root.property("firstRow") is row
    assert row.property("settingValue") == 7
    assert root.property("createdRows") == 2
    assert root.property("removedRows") == 0
    root.setProperty("rows", [{**items[0], "type": "float"}, items[1]])
    qapp.processEvents()
    assert root.property("createdRows") == 4
    assert root.property("removedRows") == 2
    for field, value in (("list_item_type", "int"), ("exact_selectors", True)):
        before = root.property("createdRows")
        items[0][field] = value
        root.setProperty("rows", items)
        qapp.processEvents()
        assert root.property("createdRows") == before + 2
    root.deleteLater()
    qapp.processEvents()
