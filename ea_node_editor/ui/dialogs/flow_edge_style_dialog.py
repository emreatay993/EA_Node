from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
)

from ea_node_editor.ui.dialogs.passive_style_controls import (
    ColorHexFieldControl,
    DEFAULT_LINE_EDIT_STYLE,
    FLOW_EDGE_ARROW_HEADS,
    FLOW_EDGE_STYLE_PATTERNS,
    INVALID_LINE_EDIT_STYLE,
    normalize_flow_edge_style_payload,
)


class FlowEdgeStyleDialog(QDialog):
    def __init__(self, initial_style: Any | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Flow Edge Style")
        self.setModal(True)
        self.resize(430, 0)

        self._color_fields: dict[str, ColorHexFieldControl] = {}
        self._build_ui()
        self._load_style(initial_style)

    def edge_style(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, field in self._color_fields.items():
            value = field.text().strip()
            if value:
                payload[key] = value
        stroke_width = self.stroke_width_field.text().strip()
        if stroke_width:
            payload["stroke_width"] = stroke_width
        stroke_pattern = str(self.stroke_pattern_combo.currentData() or "").strip()
        if stroke_pattern:
            payload["stroke_pattern"] = stroke_pattern
        arrow_head = str(self.arrow_head_combo.currentData() or "").strip()
        if arrow_head:
            payload["arrow_head"] = arrow_head
        return normalize_flow_edge_style_payload(payload)

    def accept(self) -> None:
        if not self._validate():
            return
        super().accept()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        note = QLabel("Overrides apply only to flow edges. Leave fields blank to inherit the graph theme.", self)
        note.setWordWrap(True)
        note.setStyleSheet("color: #8899aa;")
        root.addWidget(note)

        self.validation_message = QLabel("Fix invalid style values before applying.", self)
        self.validation_message.setWordWrap(True)
        self.validation_message.setStyleSheet("color: #C75050;")
        self.validation_message.hide()
        root.addWidget(self.validation_message)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        root.addLayout(form)

        for key, label in (
            ("stroke_color", "Stroke Color"),
            ("label_text_color", "Label Text Color"),
            ("label_background_color", "Label Background Color"),
        ):
            field = ColorHexFieldControl(self, allow_empty=True, color_dialog_title=f"Pick {label}")
            field.setObjectNames(value_name=f"{key}_value", swatch_name=f"{key}_swatch")
            field.valueChanged.connect(self._sync_validation_message)
            self._color_fields[key] = field
            form.addRow(label, field)

        self.stroke_width_field = QLineEdit(self)
        self.stroke_width_field.setObjectName("stroke_width_value")
        self.stroke_width_field.setPlaceholderText("inherit")
        self.stroke_width_field.setValidator(QRegularExpressionValidator(QRegularExpression(r"(?:\d+(?:\.\d+)?)?"), self))
        self.stroke_width_field.textChanged.connect(self._sync_validation_message)
        form.addRow("Stroke Width", self.stroke_width_field)

        self.stroke_pattern_combo = QComboBox(self)
        self.stroke_pattern_combo.setObjectName("stroke_pattern_combo")
        self.stroke_pattern_combo.addItem("Inherit", "")
        for value in FLOW_EDGE_STYLE_PATTERNS:
            self.stroke_pattern_combo.addItem(value.title(), value)
        form.addRow("Stroke Pattern", self.stroke_pattern_combo)

        self.arrow_head_combo = QComboBox(self)
        self.arrow_head_combo.setObjectName("arrow_head_combo")
        self.arrow_head_combo.addItem("Inherit", "")
        for value in FLOW_EDGE_ARROW_HEADS:
            self.arrow_head_combo.addItem(value.title(), value)
        form.addRow("Arrow Head", self.arrow_head_combo)

        buttons = QHBoxLayout()
        buttons.addStretch(1)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)

        self.apply_button = QPushButton("Apply", self)
        self.apply_button.setObjectName("primaryButton")
        self.apply_button.clicked.connect(self.accept)
        buttons.addWidget(self.apply_button)

        root.addLayout(buttons)

    def _load_style(self, initial_style: Any | None) -> None:
        normalized = normalize_flow_edge_style_payload(initial_style)
        for key, field in self._color_fields.items():
            field.setText(normalized.get(key, ""))
        if "stroke_width" in normalized:
            self.stroke_width_field.setText(_format_number(normalized["stroke_width"]))
        self.stroke_pattern_combo.setCurrentIndex(max(0, self.stroke_pattern_combo.findData(normalized.get("stroke_pattern", ""))))
        self.arrow_head_combo.setCurrentIndex(max(0, self.arrow_head_combo.findData(normalized.get("arrow_head", ""))))
        self._sync_validation_message()

    def _validate(self) -> bool:
        invalid = False
        for field in self._color_fields.values():
            value = field.text().strip()
            if value and field.is_valid():
                field.mark_valid()
            elif not value:
                field.mark_valid()
            else:
                field.mark_invalid()
                invalid = True

        if _is_valid_decimal(self.stroke_width_field.text()):
            self.stroke_width_field.setStyleSheet(DEFAULT_LINE_EDIT_STYLE)
        else:
            self.stroke_width_field.setStyleSheet(INVALID_LINE_EDIT_STYLE)
            invalid = True

        self.validation_message.setVisible(invalid)
        if invalid:
            QMessageBox.warning(
                self,
                "Invalid Flow Edge Style",
                "Flow edge styles must use valid hex colors and positive numeric values.",
            )
            return False
        return True

    def _sync_validation_message(self) -> None:
        invalid_colors = any(field.text().strip() and not field.is_valid() for field in self._color_fields.values())
        invalid_width = not _is_valid_decimal(self.stroke_width_field.text())
        self.validation_message.setVisible(invalid_colors or invalid_width)


def _format_number(value: object) -> str:
    numeric = float(value)
    return str(int(numeric)) if numeric.is_integer() else str(numeric)


def _is_valid_decimal(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return True
    try:
        numeric = float(normalized)
    except ValueError:
        return False
    return numeric > 0.0


__all__ = ["FlowEdgeStyleDialog"]
