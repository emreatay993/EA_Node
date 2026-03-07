from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal


class StatusItemModel(QObject):
    changed = pyqtSignal()

    def __init__(self, icon: str, text: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._icon = icon
        self._text = text

    def set_icon(self, value: str) -> None:
        if self._icon == value:
            return
        self._icon = value
        self.changed.emit()

    def set_text(self, value: str) -> None:
        if self._text == value:
            return
        self._text = value
        self.changed.emit()

    def icon(self) -> str:
        return self._icon

    def text(self) -> str:
        return self._text

    @pyqtProperty(str, notify=changed)
    def icon_value(self) -> str:
        return self._icon

    @pyqtProperty(str, notify=changed)
    def text_value(self) -> str:
        return self._text
