"""Reusable graph-theme preview widgets for settings dialogs."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ea_node_editor.ui.graph_theme.registry import GraphThemeDefinition


class NodePreviewWidget(QWidget):
    """Clean miniature node card focused on card/header/inline/port tokens."""

    def __init__(self, theme: GraphThemeDefinition, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._theme = theme
        self.setFixedSize(260, 96)

    def set_theme(self, theme: GraphThemeDefinition) -> None:
        self._theme = theme
        self.update()

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        n = self._theme.node_tokens

        w = self.width()
        h = self.height()
        margin = 6
        card_x = margin
        card_y = margin
        card_w = w - margin * 2
        card_h = h - margin * 2
        r = 8

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # -- Card --
        p.setPen(QPen(QColor(n.card_border), 1.5))
        p.setBrush(QColor(n.card_bg))
        p.drawRoundedRect(card_x, card_y, card_w, card_h, r, r)

        # -- Selected border highlight (subtle inner glow) --
        sel_color = QColor(n.card_selected_border)
        sel_color.setAlpha(60)
        p.setPen(QPen(sel_color, 0.75))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(card_x + 2, card_y + 2, card_w - 4, card_h - 4, r - 1, r - 1)

        # -- Header --
        header_h = 28
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(n.header_bg))
        p.drawRoundedRect(card_x + 1, card_y + 1, card_w - 2, header_h, r - 1, r - 1)
        p.drawRect(card_x + 1, card_y + header_h - 6, card_w - 2, 6)

        # Header text
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(n.header_fg))
        p.drawText(card_x + 12, card_y + 20, "Node Title")

        # Scope badge
        badge_w = 48
        badge_h = 16
        badge_x = card_x + card_w - badge_w - 10
        badge_y = card_y + 7
        p.setPen(QPen(QColor(n.scope_badge_border), 1))
        p.setBrush(QColor(n.scope_badge_bg))
        p.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 3, 3)
        font.setPointSize(7)
        font.setBold(False)
        p.setFont(font)
        p.setPen(QColor(n.scope_badge_fg))
        p.drawText(badge_x + 10, badge_y + 12, "scope")

        # -- Inline row --
        body_y = card_y + header_h + 1
        row_h = 26
        row_x = card_x + 1
        row_w = card_w - 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(n.inline_row_bg))
        p.drawRect(row_x, body_y, row_w, row_h)
        p.setPen(QPen(QColor(n.inline_row_border), 0.5))
        p.drawLine(row_x, body_y + row_h, row_x + row_w, body_y + row_h)

        # Port dot in row
        dot_r = 5
        dot_cx = row_x + 14
        dot_cy = body_y + row_h // 2
        p.setPen(QPen(QColor(n.port_interactive_border), 1.2))
        p.setBrush(QColor(n.port_interactive_fill))
        p.drawEllipse(dot_cx - dot_r, dot_cy - dot_r, dot_r * 2, dot_r * 2)

        # Inline label
        font.setPointSize(7)
        p.setFont(font)
        p.setPen(QColor(n.inline_label_fg))
        p.drawText(dot_cx + dot_r + 8, dot_cy + 4, "value")

        # Inline input box
        inp_x = row_x + row_w // 2 + 4
        inp_y = body_y + 5
        inp_w = row_w // 2 - 12
        inp_h = 16
        p.setPen(QPen(QColor(n.inline_input_border), 1))
        p.setBrush(QColor(n.inline_input_bg))
        p.drawRoundedRect(inp_x, inp_y, inp_w, inp_h, 3, 3)
        p.setPen(QColor(n.inline_input_fg))
        p.drawText(inp_x + 6, inp_y + 12, "0.0")

        # -- Second row (output port + driven indicator) --
        row2_y = body_y + row_h + 1
        row2_h = card_h - header_h - row_h - 3
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(n.inline_row_bg))
        # Use bottom-rounded rect so it follows the card shape
        p.drawRoundedRect(row_x, row2_y, row_w, row2_h, r - 2, r - 2)
        p.drawRect(row_x, row2_y, row_w, row2_h // 2)

        # Port label
        dot2_cy = row2_y + row2_h // 2
        p.setPen(QColor(n.port_label_fg))
        font.setPointSize(7)
        p.setFont(font)
        p.drawText(dot_cx + dot_r + 8, dot2_cy + 4, "output")

        # Driven indicator on the right
        p.setPen(QColor(n.inline_driven_fg))
        font.setPointSize(6)
        font.setItalic(True)
        p.setFont(font)
        p.drawText(inp_x + 6, dot2_cy + 4, "driven")
        font.setItalic(False)

        p.end()


class ShadowPreviewWidget(QWidget):
    """Node card preview with a live QGraphicsDropShadowEffect for shadow tuning."""

    def __init__(
        self,
        theme: GraphThemeDefinition,
        strength: int = 70,
        softness: int = 50,
        offset: int = 4,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet("ShadowPreviewWidget { background: transparent; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self._node = NodePreviewWidget(theme, self)
        layout.addWidget(self._node, alignment=Qt.AlignmentFlag.AlignCenter)
        self._shadow = QGraphicsDropShadowEffect(self._node)
        self._shadow.setXOffset(0)
        self._node.setGraphicsEffect(self._shadow)
        self.set_shadow(strength, softness, offset)

    def set_theme(self, theme: GraphThemeDefinition) -> None:
        self._node.set_theme(theme)

    def set_shadow(self, strength: int, softness: int, offset: int) -> None:
        self._shadow.setColor(QColor(0, 0, 0, int(strength * 255 / 100)))
        self._shadow.setBlurRadius(softness * 0.4)
        self._shadow.setYOffset(offset)


# ---------------------------------------------------------------------------
# Legend building blocks
# ---------------------------------------------------------------------------

class _ColorDotSwatch(QWidget):
    """Small filled circle swatch for legend rows."""

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._color = QColor(color)
        self.setFixedSize(12, 12)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(1, 1, 10, 10)
        p.end()


class _LineSwatch(QWidget):
    """Small horizontal coloured line swatch for legend rows."""

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._color = QColor(color)
        self.setFixedSize(24, 6)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(self._color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(2, 3, self.width() - 2, 3)
        p.end()


def _build_legend_row(
    items: list[tuple[str, str]],
    swatch_cls: type,
    parent: QWidget,
) -> tuple[QWidget, list[tuple[str, QWidget]]]:
    """Build a horizontal legend row.  Returns (row_widget, [(attr, swatch), ...])."""
    row = QWidget(parent)
    row.setStyleSheet("QWidget { background: transparent; }")
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    label_font = QFont()
    label_font.setPointSize(7)
    swatches: list[tuple[str, QWidget]] = []
    for attr, text in items:
        swatch = swatch_cls("", row)
        label = QLabel(text, row)
        label.setFont(label_font)
        pair = QWidget(row)
        pair.setStyleSheet("QWidget { background: transparent; }")
        pair_layout = QHBoxLayout(pair)
        pair_layout.setContentsMargins(0, 0, 0, 0)
        pair_layout.setSpacing(4)
        pair_layout.addWidget(swatch, alignment=Qt.AlignmentFlag.AlignVCenter)
        pair_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(pair)
        swatches.append((attr, swatch))
    layout.addStretch()
    return row, swatches


# ---------------------------------------------------------------------------
# Composite preview widget
# ---------------------------------------------------------------------------

class GraphThemePreviewWidget(QWidget):
    """Node preview + category / port / edge legends for settings dialogs."""

    _CATEGORY_ITEMS = [
        ("default", "Default"),
        ("core", "Core"),
        ("input_output", "I/O"),
        ("physics", "Physics"),
        ("logic", "Logic"),
        ("hpc", "HPC"),
    ]

    _PORT_ITEMS = [
        ("data", "Data"),
        ("exec", "Exec"),
        ("completed", "Done"),
        ("failed", "Failed"),
    ]

    _EDGE_ITEMS = [
        ("preview_stroke", "Preview"),
        ("selected_stroke", "Selected"),
        ("warning_stroke", "Warning"),
        ("valid_drag_stroke", "Valid"),
        ("invalid_drag_stroke", "Invalid"),
    ]

    def __init__(self, theme: GraphThemeDefinition, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("GraphThemePreviewWidget { background: transparent; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 0)
        layout.setSpacing(4)

        # Node card preview
        self._node_preview = NodePreviewWidget(theme, self)
        layout.addWidget(self._node_preview, alignment=Qt.AlignmentFlag.AlignCenter)

        # Legend sections
        section_font = QFont()
        section_font.setPointSize(7)
        section_font.setBold(True)

        # Category accents
        cat_label = QLabel("Category accents")
        cat_label.setFont(section_font)
        layout.addWidget(cat_label, alignment=Qt.AlignmentFlag.AlignCenter)
        cat_row, self._cat_swatches = _build_legend_row(self._CATEGORY_ITEMS, _ColorDotSwatch, self)
        layout.addWidget(cat_row, alignment=Qt.AlignmentFlag.AlignCenter)

        # Port kinds
        port_label = QLabel("Port kinds")
        port_label.setFont(section_font)
        layout.addWidget(port_label, alignment=Qt.AlignmentFlag.AlignCenter)
        port_row, self._port_swatches = _build_legend_row(self._PORT_ITEMS, _ColorDotSwatch, self)
        layout.addWidget(port_row, alignment=Qt.AlignmentFlag.AlignCenter)

        # Edge colors
        edge_label = QLabel("Edge colors")
        edge_label.setFont(section_font)
        layout.addWidget(edge_label, alignment=Qt.AlignmentFlag.AlignCenter)
        edge_row, self._edge_swatches = _build_legend_row(self._EDGE_ITEMS, _LineSwatch, self)
        layout.addWidget(edge_row, alignment=Qt.AlignmentFlag.AlignCenter)

        # Apply initial colours
        self._apply_colors(theme)

    def set_theme(self, theme: GraphThemeDefinition) -> None:
        self._node_preview.set_theme(theme)
        self._apply_colors(theme)

    def _apply_colors(self, theme: GraphThemeDefinition) -> None:
        for attr, swatch in self._cat_swatches:
            swatch.set_color(getattr(theme.category_accent_tokens, attr))
        for attr, swatch in self._port_swatches:
            swatch.set_color(getattr(theme.port_kind_tokens, attr))
        for attr, swatch in self._edge_swatches:
            swatch.set_color(getattr(theme.edge_tokens, attr))
