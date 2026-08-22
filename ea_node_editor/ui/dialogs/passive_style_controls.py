from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from typing import Any

from PyQt6.QtCore import QRegularExpression, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QRegularExpressionValidator
from PyQt6.QtWidgets import QColorDialog, QFrame, QHBoxLayout, QLineEdit, QWidget

FINAL_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")

PASSIVE_NODE_STYLE_FONT_WEIGHTS = ("normal", "bold")
PASSIVE_NODE_STYLE_GRADIENT_DIRECTIONS = ("north", "east", "south", "west", "radial")
DEFAULT_PASSIVE_NODE_STYLE_GRADIENT_DIRECTION = "south"
FLOW_EDGE_STYLE_PATTERNS = ("solid", "dashed", "dotted")
FLOW_EDGE_ARROW_HEADS = ("filled", "open", "none")
FLOW_EDGE_PATH_MODES = ("auto", "pipe", "bezier")


class ColorSwatchFrame(QFrame):
    """A 32x32 clickable color swatch that can open a QColorDialog."""

    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setProperty("dialogSwatch", True)
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
        self._before_color_apply: Callable[[str], bool] | None = None

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
        # Keep the swatch clickability aligned with the field editability.
        self.setReadOnly(self.line_edit.isReadOnly())

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, value: object) -> None:
        self.line_edit.setText(str(value or "").strip())

    def setReadOnly(self, value: bool) -> None:
        read_only = bool(value)
        self.line_edit.setReadOnly(read_only)
        self.swatch.editable = not read_only

    def setObjectNames(self, *, value_name: str, swatch_name: str) -> None:
        self.line_edit.setObjectName(value_name)
        self.swatch.setObjectName(swatch_name)

    def setBeforeColorApply(self, callback: Callable[[str], bool] | None) -> None:
        self._before_color_apply = callback

    def is_valid(self) -> bool:
        return is_valid_hex_color(self.text(), allow_empty=self._allow_empty)

    def mark_invalid(self) -> None:
        set_dialog_role(self.line_edit, "error")
        set_dialog_role(self.swatch, "error")

    def mark_valid(self) -> None:
        set_dialog_role(self.line_edit, None)
        self.refresh_swatch()

    def refresh_swatch(self) -> None:
        normalized = self.text().strip()
        if not normalized and self._allow_empty:
            role = "empty"
        elif not is_valid_hex_color(normalized, allow_empty=self._allow_empty):
            role = "error"
        else:
            role = None
        set_dialog_role(self.swatch, role)
        self.swatch.setStyleSheet(swatch_style(normalized, allow_empty=self._allow_empty))

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
        selected_hex = color_to_hex(color)
        if self._before_color_apply is not None and not self._before_color_apply(selected_hex):
            return
        self.setText(selected_hex)


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


def set_dialog_role(widget: QWidget, role: str | None) -> None:
    if widget.property("dialogRole") == role:
        return
    widget.setProperty("dialogRole", role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def swatch_style(value: object, *, allow_empty: bool = False) -> str:
    normalized = str(value or "").strip()
    if not normalized and allow_empty:
        return "background-color: transparent;"
    if not is_valid_hex_color(normalized, allow_empty=allow_empty):
        return "background-color: transparent;"
    return f"background-color: {normalized};"


def normalize_passive_node_style_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}

    for key in ("fill_color", "border_color", "text_color"):
        color_value = _normalized_hex_color(value.get(key))
        if color_value:
            normalized[key] = color_value

    _normalize_node_gradient_fields(
        value,
        normalized,
        enabled_key="gradient_enabled",
        color_key="gradient_color",
        direction_key="gradient_direction",
    )
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

    path_mode = str(value.get("path_mode", "")).strip().lower()
    if path_mode in FLOW_EDGE_PATH_MODES and path_mode != "auto":
        normalized["path_mode"] = path_mode

    return normalized


def _normalized_hex_color(value: Any) -> str:
    normalized = str(value or "").strip()
    if not is_valid_hex_color(normalized):
        return ""
    return normalized


def _normalize_node_gradient_fields(
    source: Mapping[str, Any],
    target: dict[str, Any],
    *,
    enabled_key: str,
    color_key: str,
    direction_key: str,
) -> None:
    enabled = _normalized_optional_bool(source.get(enabled_key))
    if enabled is False:
        target[enabled_key] = False
        return
    color_value = _normalized_hex_color(source.get(color_key))
    if enabled is True:
        if not color_value:
            return
        target[enabled_key] = True
        target[color_key] = color_value
        target[direction_key] = _normalized_gradient_direction(source.get(direction_key))
        return
    if color_value:
        target[color_key] = color_value
        target[direction_key] = _normalized_gradient_direction(source.get(direction_key))


def _normalized_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    return None


def _normalized_gradient_direction(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in PASSIVE_NODE_STYLE_GRADIENT_DIRECTIONS:
        return normalized
    return DEFAULT_PASSIVE_NODE_STYLE_GRADIENT_DIRECTION


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
    "DEFAULT_PASSIVE_NODE_STYLE_GRADIENT_DIRECTION",
    "FLOW_EDGE_ARROW_HEADS",
    "FLOW_EDGE_PATH_MODES",
    "FLOW_EDGE_STYLE_PATTERNS",
    "FINAL_HEX_COLOR",
    "PASSIVE_NODE_STYLE_GRADIENT_DIRECTIONS",
    "PASSIVE_NODE_STYLE_FONT_WEIGHTS",
    "color_to_hex",
    "hex_color_validator",
    "is_valid_hex_color",
    "normalize_flow_edge_style_payload",
    "normalize_passive_node_style_payload",
    "set_dialog_role",
    "swatch_style",
]
