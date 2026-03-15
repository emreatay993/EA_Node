from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

from PyQt6.QtCore import QRegularExpression, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QRegularExpressionValidator
from PyQt6.QtWidgets import QColorDialog, QFrame, QHBoxLayout, QLineEdit, QWidget

FINAL_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")
INVALID_LINE_EDIT_STYLE = "border: 1px solid #C75050;"
DEFAULT_LINE_EDIT_STYLE = ""
DEFAULT_SWATCH_STYLE = "border: 1px solid #5f6b7a; border-radius: 4px;"
INVALID_SWATCH_STYLE = "background-color: transparent; border: 1px solid #C75050; border-radius: 4px;"
EMPTY_SWATCH_STYLE = "background-color: transparent; border: 1px dashed #5f6b7a; border-radius: 4px;"

PASSIVE_NODE_STYLE_FONT_WEIGHTS = ("normal", "bold")
FLOW_EDGE_STYLE_PATTERNS = ("solid", "dashed", "dotted")
FLOW_EDGE_ARROW_HEADS = ("filled", "open", "none")


class ColorSwatchFrame(QFrame):
    """A 32x32 clickable color swatch that can open a QColorDialog."""

    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._editable = False

    @property
    def editable(self) -> bool:
        return self._editable

    @editable.setter
    def editable(self, value: bool) -> None:
        self._editable = bool(value)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if self._editable else Qt.CursorShape.ArrowCursor
        )

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if self._editable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            return
        super().mousePressEvent(event)


class ColorHexFieldControl(QWidget):
    valueChanged = pyqtSignal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        allow_empty: bool = False,
        color_dialog_title: str = "Pick Color",
    ) -> None:
        super().__init__(parent)
        self._allow_empty = bool(allow_empty)
        self._color_dialog_title = str(color_dialog_title)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.swatch = ColorSwatchFrame(self)
        self.swatch.clicked.connect(self._choose_color)
        layout.addWidget(self.swatch, stretch=0, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.line_edit = QLineEdit(self)
        self.line_edit.setValidator(hex_color_validator(self, allow_empty=self._allow_empty))
        self.line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.line_edit, stretch=1)

        self.refresh_swatch()

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, value: object) -> None:
        self.line_edit.setText(str(value or "").strip())

    def setReadOnly(self, value: bool) -> None:
        read_only = bool(value)
        self.line_edit.setReadOnly(read_only)
        self.swatch.editable = not read_only

    def setLineEditStyleSheet(self, style: str) -> None:
        self.line_edit.setStyleSheet(style)

    def setObjectNames(self, *, value_name: str, swatch_name: str) -> None:
        self.line_edit.setObjectName(value_name)
        self.swatch.setObjectName(swatch_name)

    def is_valid(self) -> bool:
        return is_valid_hex_color(self.text(), allow_empty=self._allow_empty)

    def mark_invalid(self) -> None:
        self.line_edit.setStyleSheet(INVALID_LINE_EDIT_STYLE)
        self.swatch.setStyleSheet(INVALID_SWATCH_STYLE)

    def mark_valid(self, *, line_edit_style: str = DEFAULT_LINE_EDIT_STYLE) -> None:
        self.line_edit.setStyleSheet(line_edit_style)
        self.refresh_swatch()

    def refresh_swatch(self) -> None:
        self.swatch.setStyleSheet(swatch_style(self.text(), allow_empty=self._allow_empty))

    def _on_text_changed(self, text: str) -> None:
        normalized = str(text or "").strip()
        if text != normalized:
            self.line_edit.blockSignals(True)
            self.line_edit.setText(normalized)
            self.line_edit.blockSignals(False)
        self.refresh_swatch()
        self.valueChanged.emit(normalized)

    def _choose_color(self) -> None:
        current_text = self.text().strip()
        initial_color = QColor(current_text) if is_valid_hex_color(current_text) else QColor("#ffffff")
        color = QColorDialog.getColor(
            initial_color,
            self,
            self._color_dialog_title,
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if not color.isValid():
            return
        self.setText(color_to_hex(color))


def color_to_hex(color: QColor) -> str:
    if color.alpha() < 255:
        return f"#{color.alpha():02X}{color.red():02X}{color.green():02X}{color.blue():02X}"
    return color.name().upper()


def hex_color_validator(parent: QWidget | None = None, *, allow_empty: bool = False) -> QRegularExpressionValidator:
    pattern = r"(?:#[0-9A-Fa-f]{0,8})?" if allow_empty else r"#[0-9A-Fa-f]{0,8}"
    return QRegularExpressionValidator(QRegularExpression(pattern), parent)


def is_valid_hex_color(value: object, *, allow_empty: bool = False) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return allow_empty
    return bool(FINAL_HEX_COLOR.match(normalized))


def swatch_style(value: object, *, allow_empty: bool = False) -> str:
    normalized = str(value or "").strip()
    if not normalized and allow_empty:
        return EMPTY_SWATCH_STYLE
    if not is_valid_hex_color(normalized, allow_empty=allow_empty):
        return INVALID_SWATCH_STYLE
    return f"background-color: {normalized}; {DEFAULT_SWATCH_STYLE}"


def normalize_passive_node_style_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}

    for key in ("fill_color", "border_color", "text_color", "accent_color", "header_color"):
        color_value = _normalized_hex_color(value.get(key))
        if color_value:
            normalized[key] = color_value

    border_width = _normalized_positive_number(value.get("border_width"))
    if border_width is not None:
        normalized["border_width"] = border_width

    corner_radius = _normalized_nonnegative_number(value.get("corner_radius"))
    if corner_radius is not None:
        normalized["corner_radius"] = corner_radius

    font_size = _normalized_positive_int(value.get("font_size"))
    if font_size is not None:
        normalized["font_size"] = font_size

    font_weight = str(value.get("font_weight", "")).strip().lower()
    if font_weight in PASSIVE_NODE_STYLE_FONT_WEIGHTS:
        normalized["font_weight"] = font_weight

    return normalized


def normalize_flow_edge_style_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}

    for key in ("stroke_color", "label_text_color", "label_background_color"):
        color_value = _normalized_hex_color(value.get(key))
        if color_value:
            normalized[key] = color_value

    stroke_width = _normalized_positive_number(value.get("stroke_width"))
    if stroke_width is not None:
        normalized["stroke_width"] = stroke_width

    stroke_pattern = str(value.get("stroke_pattern", "")).strip().lower()
    if stroke_pattern in FLOW_EDGE_STYLE_PATTERNS:
        normalized["stroke_pattern"] = stroke_pattern

    arrow_head = str(value.get("arrow_head", "")).strip().lower()
    if arrow_head in FLOW_EDGE_ARROW_HEADS:
        normalized["arrow_head"] = arrow_head

    return normalized


def _normalized_hex_color(value: Any) -> str:
    normalized = str(value or "").strip()
    if not is_valid_hex_color(normalized):
        return ""
    return normalized


def _normalized_positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric <= 0.0:
        return None
    return numeric


def _normalized_nonnegative_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0.0:
        return None
    return numeric


def _normalized_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    return numeric


__all__ = [
    "ColorHexFieldControl",
    "ColorSwatchFrame",
    "DEFAULT_LINE_EDIT_STYLE",
    "DEFAULT_SWATCH_STYLE",
    "EMPTY_SWATCH_STYLE",
    "FLOW_EDGE_ARROW_HEADS",
    "FLOW_EDGE_STYLE_PATTERNS",
    "FINAL_HEX_COLOR",
    "INVALID_LINE_EDIT_STYLE",
    "INVALID_SWATCH_STYLE",
    "PASSIVE_NODE_STYLE_FONT_WEIGHTS",
    "color_to_hex",
    "hex_color_validator",
    "is_valid_hex_color",
    "normalize_flow_edge_style_payload",
    "normalize_passive_node_style_payload",
    "swatch_style",
]
