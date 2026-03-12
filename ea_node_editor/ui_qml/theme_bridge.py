from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.ui.theme import DEFAULT_THEME_ID, resolve_theme


class ThemeBridge(QObject):
    changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None, *, theme_id: object = DEFAULT_THEME_ID) -> None:
        super().__init__(parent)
        self._theme = resolve_theme(theme_id)

    def apply_theme(self, theme_id: Any) -> str:
        resolved = resolve_theme(theme_id)
        if resolved == self._theme:
            return self._theme.theme_id
        self._theme = resolved
        self.changed.emit()
        return self._theme.theme_id

    @pyqtProperty(str, notify=changed)
    def theme_id(self) -> str:
        return self._theme.theme_id

    @pyqtProperty(str, notify=changed)
    def theme_label(self) -> str:
        return self._theme.label

    @pyqtProperty("QVariantMap", notify=changed)
    def palette(self) -> dict[str, str]:
        return self._theme.tokens.as_dict()

    @pyqtSlot(str, result=str)
    def token(self, name: str) -> str:
        return str(self._theme.tokens.as_dict().get(str(name).strip(), ""))
