from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusItem(QWidget):
    def __init__(
        self,
        icon: str,
        text: str,
        on_click: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._icon_label = QLabel(icon)
        self._text_label = QLabel(text)
        self._on_click = on_click
        self.setProperty("clickable", bool(on_click))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(4)
        layout.addWidget(self._icon_label)
        layout.addWidget(self._text_label)
        if on_click:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_text(self, value: str) -> None:
        self._text_label.setText(value)

    def set_icon(self, value: str) -> None:
        self._icon_label.setText(value)

    def text(self) -> str:
        return self._text_label.text()

    def icon(self) -> str:
        return self._icon_label.text()

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if self._on_click:
            self._on_click()
        super().mousePressEvent(event)
