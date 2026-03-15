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
    QWidget,
    QLineEdit,
)

from ea_node_editor.ui.dialogs.passive_style_controls import (
    ColorHexFieldControl,
    DEFAULT_LINE_EDIT_STYLE,
    INVALID_LINE_EDIT_STYLE,
    PASSIVE_NODE_STYLE_FONT_WEIGHTS,
    normalize_passive_node_style_payload,
)


class PassiveNodeStyleDialog(QDialog):
    def __init__(self, initial_style: Any | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Passive Node Style")
        self.setModal(True)
        self.resize(460, 0)

        self._color_fields: dict[str, ColorHexFieldControl] = {}
        self._numeric_fields: dict[str, QLineEdit] = {}

        self._build_ui()
        self._load_style(initial_style)

    def node_style(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, field in self._color_fields.items():
            value = field.text().strip()
            if value:
                payload[key] = value
        for key, field in self._numeric_fields.items():
            value = field.text().strip()
            if value:
                payload[key] = value
        weight = str(self.font_weight_combo.currentData() or "").strip()
        if weight:
            payload["font_weight"] = weight
        return normalize_passive_node_style_payload(payload)

    def accept(self) -> None:
        if not self._validate():
            return
        super().accept()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        note = QLabel("Overrides apply only to passive nodes. Leave fields blank to inherit the graph theme.", self)
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
            ("fill_color", "Fill Color"),
            ("border_color", "Border Color"),
            ("text_color", "Text Color"),
            ("accent_color", "Accent Color"),
            ("header_color", "Header Color"),
        ):
            field = ColorHexFieldControl(self, allow_empty=True, color_dialog_title=f"Pick {label}")
            field.setObjectNames(value_name=f"{key}_value", swatch_name=f"{key}_swatch")
            field.valueChanged.connect(self._sync_validation_message)
            self._color_fields[key] = field
            form.addRow(label, field)

        self._numeric_fields["border_width"] = self._numeric_field(
            object_name="border_width_value",
            placeholder="inherit",
            validator=QRegularExpressionValidator(QRegularExpression(r"(?:\d+(?:\.\d+)?)?"), self),
        )
        form.addRow("Border Width", self._numeric_fields["border_width"])

        self._numeric_fields["corner_radius"] = self._numeric_field(
            object_name="corner_radius_value",
            placeholder="inherit",
            validator=QRegularExpressionValidator(QRegularExpression(r"(?:\d+(?:\.\d+)?)?"), self),
        )
        form.addRow("Corner Radius", self._numeric_fields["corner_radius"])

        self._numeric_fields["font_size"] = self._numeric_field(
            object_name="font_size_value",
            placeholder="inherit",
            validator=QRegularExpressionValidator(QRegularExpression(r"(?:\d+)?"), self),
        )
        form.addRow("Font Size", self._numeric_fields["font_size"])

        self.font_weight_combo = QComboBox(self)
        self.font_weight_combo.setObjectName("font_weight_combo")
        self.font_weight_combo.addItem("Inherit", "")
        for value in PASSIVE_NODE_STYLE_FONT_WEIGHTS:
            self.font_weight_combo.addItem(value.title(), value)
        form.addRow("Font Weight", self.font_weight_combo)

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

    def _numeric_field(
        self,
        *,
        object_name: str,
        placeholder: str,
        validator: QRegularExpressionValidator,
    ) -> QLineEdit:
        field = QLineEdit(self)
        field.setObjectName(object_name)
        field.setPlaceholderText(placeholder)
        field.setValidator(validator)
        field.textChanged.connect(self._sync_validation_message)
        return field

    def _load_style(self, initial_style: Any | None) -> None:
        normalized = normalize_passive_node_style_payload(initial_style)
        for key, field in self._color_fields.items():
            field.setText(normalized.get(key, ""))
        if "border_width" in normalized:
            self._numeric_fields["border_width"].setText(_format_number(normalized["border_width"]))
        if "corner_radius" in normalized:
            self._numeric_fields["corner_radius"].setText(_format_number(normalized["corner_radius"]))
        if "font_size" in normalized:
            self._numeric_fields["font_size"].setText(str(normalized["font_size"]))
        weight = str(normalized.get("font_weight", "")).strip()
        index = max(0, self.font_weight_combo.findData(weight))
        self.font_weight_combo.setCurrentIndex(index)
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

        invalid |= _validate_positive_number_field(self._numeric_fields["border_width"], allow_zero=False)
        invalid |= _validate_positive_number_field(self._numeric_fields["corner_radius"], allow_zero=True)
        invalid |= _validate_int_field(self._numeric_fields["font_size"], allow_zero=False)

        self.validation_message.setVisible(invalid)
        if invalid:
            QMessageBox.warning(
                self,
                "Invalid Passive Node Style",
                "Passive node styles must use valid hex colors and positive numeric values.",
            )
            return False
        return True

    def _sync_validation_message(self) -> None:
        invalid_colors = any(field.text().strip() and not field.is_valid() for field in self._color_fields.values())
        invalid_numeric = any(
            (
                key == "font_size" and not _is_valid_int(field.text(), allow_zero=False)
            )
            or (
                key != "font_size"
                and not _is_valid_decimal(field.text(), allow_zero=(key == "corner_radius"))
            )
            for key, field in self._numeric_fields.items()
            if field.text().strip()
        )
        self.validation_message.setVisible(invalid_colors or invalid_numeric)


def _format_number(value: object) -> str:
    numeric = float(value)
    return str(int(numeric)) if numeric.is_integer() else str(numeric)


def _is_valid_decimal(value: str, *, allow_zero: bool) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return True
    try:
        numeric = float(normalized)
    except ValueError:
        return False
    return numeric >= 0.0 if allow_zero else numeric > 0.0


def _is_valid_int(value: str, *, allow_zero: bool) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return True
    try:
        numeric = int(normalized)
    except ValueError:
        return False
    return numeric >= 0 if allow_zero else numeric > 0


def _validate_positive_number_field(field: QLineEdit, *, allow_zero: bool) -> bool:
    if _is_valid_decimal(field.text(), allow_zero=allow_zero):
        field.setStyleSheet(DEFAULT_LINE_EDIT_STYLE)
        return False
    field.setStyleSheet(INVALID_LINE_EDIT_STYLE)
    return True


def _validate_int_field(field: QLineEdit, *, allow_zero: bool) -> bool:
    if _is_valid_int(field.text(), allow_zero=allow_zero):
        field.setStyleSheet(DEFAULT_LINE_EDIT_STYLE)
        return False
    field.setStyleSheet(INVALID_LINE_EDIT_STYLE)
    return True


__all__ = ["PassiveNodeStyleDialog"]
