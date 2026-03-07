from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import PropertySpec


class NodeInspectorPanel(QWidget):
    property_changed = pyqtSignal(str, str, object)
    port_exposed_changed = pyqtSignal(str, str, bool)
    collapse_changed = pyqtSignal(str, bool)

    def __init__(self, registry: NodeRegistry, parent=None) -> None:
        super().__init__(parent)
        self._registry = registry
        self._node: NodeInstance | None = None

        title = QLabel("Inspector")
        title.setObjectName("panelTitle")
        self.node_name_label = QLabel("No node selected")
        self.node_name_label.setWordWrap(True)

        self.collapse_button = QPushButton("Toggle Collapse")
        self.collapse_button.clicked.connect(self._toggle_collapse)
        self.collapse_button.setEnabled(False)

        self.property_group = QGroupBox("Properties")
        self.property_form = QFormLayout(self.property_group)

        self.ports_group = QGroupBox("Exposed Ports")
        self.ports_layout = QVBoxLayout(self.ports_group)
        self.ports_layout.setContentsMargins(6, 6, 6, 6)
        self.ports_layout.setSpacing(4)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(self.node_name_label)
        layout.addWidget(self.collapse_button)
        layout.addWidget(self.property_group)
        layout.addWidget(self.ports_group)
        layout.addStretch(1)

    def set_node(self, node: NodeInstance | None) -> None:
        self._node = node
        self._clear_dynamic_content()
        if node is None:
            self.node_name_label.setText("No node selected")
            self.collapse_button.setEnabled(False)
            return

        spec = self._registry.get_spec(node.type_id)
        self.node_name_label.setText(f"{spec.display_name}\n{node.node_id}")
        self.collapse_button.setEnabled(spec.collapsible)
        self._build_property_rows(node, spec.properties)
        self._build_port_rows(node)

    def _clear_dynamic_content(self) -> None:
        while self.property_form.rowCount() > 0:
            self.property_form.removeRow(0)
        for index in reversed(range(self.ports_layout.count())):
            item = self.ports_layout.takeAt(index)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _build_property_rows(self, node: NodeInstance, properties: tuple[PropertySpec, ...]) -> None:
        for prop in properties:
            editor = self._build_property_editor(node, prop)
            self.property_form.addRow(prop.label, editor)

    def _build_property_editor(self, node: NodeInstance, prop: PropertySpec) -> QWidget:
        value = node.properties.get(prop.key, prop.default)
        if prop.type == "bool":
            checkbox = QCheckBox()
            checkbox.setChecked(bool(value))
            checkbox.toggled.connect(
                lambda checked, node_id=node.node_id, key=prop.key: self.property_changed.emit(node_id, key, checked)
            )
            return checkbox
        if prop.type == "int":
            spin = QSpinBox()
            spin.setRange(-1_000_000_000, 1_000_000_000)
            spin.setValue(int(value))
            spin.valueChanged.connect(
                lambda changed, node_id=node.node_id, key=prop.key: self.property_changed.emit(node_id, key, int(changed))
            )
            return spin
        if prop.type == "float":
            spin = QDoubleSpinBox()
            spin.setDecimals(6)
            spin.setRange(-1_000_000_000.0, 1_000_000_000.0)
            spin.setValue(float(value))
            spin.valueChanged.connect(
                lambda changed, node_id=node.node_id, key=prop.key: self.property_changed.emit(
                    node_id, key, float(changed)
                )
            )
            return spin
        if prop.type == "enum":
            combo = QComboBox()
            values = list(prop.enum_values) if prop.enum_values else [str(value)]
            for candidate in values:
                combo.addItem(candidate, candidate)
            idx = combo.findData(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.currentIndexChanged.connect(
                lambda _idx, editor=combo, node_id=node.node_id, key=prop.key: self.property_changed.emit(
                    node_id, key, editor.currentData()
                )
            )
            return combo
        edit = QLineEdit()
        if prop.type == "json":
            edit.setText(json.dumps(value))
            edit.editingFinished.connect(
                lambda editor=edit, node_id=node.node_id, spec=prop: self._on_edit_finished(node_id, spec, editor)
            )
        else:
            edit.setText(str(value))
            edit.textChanged.connect(
                lambda changed, node_id=node.node_id, key=prop.key: self.property_changed.emit(node_id, key, changed)
            )
        return edit

    def _on_edit_finished(self, node_id: str, prop: PropertySpec, editor: QLineEdit) -> None:
        text = editor.text()
        if prop.type == "json":
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                value = prop.default
                editor.setText(json.dumps(value))
        else:
            value = text
        self.property_changed.emit(node_id, prop.key, value)

    def _build_port_rows(self, node: NodeInstance) -> None:
        spec = self._registry.get_spec(node.type_id)
        for port in spec.ports:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            label = QLabel(f"{port.direction}:{port.key}")
            checkbox = QCheckBox("Expose")
            checkbox.setChecked(node.exposed_ports.get(port.key, port.exposed))
            checkbox.toggled.connect(
                lambda checked, node_id=node.node_id, key=port.key: self.port_exposed_changed.emit(node_id, key, checked)
            )
            row_layout.addWidget(label)
            row_layout.addStretch(1)
            row_layout.addWidget(checkbox)
            self.ports_layout.addWidget(row)

    def _toggle_collapse(self) -> None:
        if self._node is None:
            return
        self.collapse_changed.emit(self._node.node_id, not self._node.collapsed)
