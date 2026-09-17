"""Node card preview widgets used by the Graphics Settings shadow preview."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QVBoxLayout, QWidget

from ea_node_editor.ui.graph_theme.registry import GraphThemeDefinition


class NodePreviewWidget(QWidget):
    """Clean miniature passive card focused on default card and inline tokens."""

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
        p.setBrush(
            _node_gradient_brush(
                card_x,
                card_y,
                card_w,
                card_h,
                base_color=n.card_bg,
                gradient_enabled=n.card_gradient_enabled,
                gradient_color=n.card_gradient_color,
                gradient_direction=n.card_gradient_direction,
            )
        )
        p.drawRoundedRect(card_x, card_y, card_w, card_h, r, r)

        # -- Selected border highlight (subtle inner glow) --
        sel_color = QColor(n.card_selected_border)
        sel_color.setAlpha(60)
        p.setPen(QPen(sel_color, 0.75))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(card_x + 2, card_y + 2, card_w - 4, card_h - 4, r - 1, r - 1)

        # -- Title --
        header_h = 28
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(n.header_fg))
        p.drawText(card_x + 12, card_y + 20, "Passive Surface")

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
        p.drawText(badge_x + 8, badge_y + 12, "default")

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

        # Surface marker
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
        p.drawText(dot_cx + dot_r + 8, dot_cy + 4, "content")

        # Inline input box
        inp_x = row_x + row_w // 2 + 4
        inp_y = body_y + 5
        inp_w = row_w // 2 - 12
        inp_h = 16
        p.setPen(QPen(QColor(n.inline_input_border), 1))
        p.setBrush(QColor(n.inline_input_bg))
        p.drawRoundedRect(inp_x, inp_y, inp_w, inp_h, 3, 3)
        p.setPen(QColor(n.inline_input_fg))
        p.drawText(inp_x + 6, inp_y + 12, "note")

        # -- Second row (passive preview details) --
        row2_y = body_y + row_h + 1
        row2_h = card_h - header_h - row_h - 3
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(n.inline_row_bg))
        # Use bottom-rounded rect so it follows the card shape
        p.drawRoundedRect(row_x, row2_y, row_w, row2_h, r - 2, r - 2)
        p.drawRect(row_x, row2_y, row_w, row2_h // 2)

        # Preview label
        dot2_cy = row2_y + row2_h // 2
        p.setPen(QColor(n.port_label_fg))
        font.setPointSize(7)
        p.setFont(font)
        p.drawText(dot_cx + dot_r + 8, dot2_cy + 4, "preview")

        # Default-state indicator on the right
        p.setPen(QColor(n.inline_driven_fg))
        font.setPointSize(6)
        font.setItalic(True)
        p.setFont(font)
        p.drawText(inp_x + 6, dot2_cy + 4, "default")
        font.setItalic(False)

        p.end()


def _node_gradient_brush(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    base_color: str,
    gradient_enabled: bool,
    gradient_color: str,
    gradient_direction: str,
) -> QBrush:
    base = QColor(base_color)
    end = QColor(gradient_color)
    if not gradient_enabled or not end.isValid():
        return QBrush(base)
    direction = str(gradient_direction or "south").strip().lower()
    if direction == "radial":
        gradient = QRadialGradient(x + width / 2.0, y + height / 2.0, max(width, height) / 2.0)
        gradient.setColorAt(0.0, base)
        gradient.setColorAt(1.0, end)
        return QBrush(gradient)
    if direction == "north":
        gradient = QLinearGradient(x, y + height, x, y)
    elif direction == "east":
        gradient = QLinearGradient(x, y, x + width, y)
    elif direction == "west":
        gradient = QLinearGradient(x + width, y, x, y)
    else:
        gradient = QLinearGradient(x, y, x, y + height)
    gradient.setColorAt(0.0, base)
    gradient.setColorAt(1.0, end)
    return QBrush(gradient)


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
