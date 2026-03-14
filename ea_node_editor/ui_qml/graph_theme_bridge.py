from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

from ea_node_editor.ui.graph_theme import DEFAULT_GRAPH_THEME_ID, resolve_active_graph_theme, resolve_graph_theme


class GraphThemeBridge(QObject):
    changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None, *, theme_id: object = DEFAULT_GRAPH_THEME_ID) -> None:
        super().__init__(parent)
        self._theme = resolve_graph_theme(theme_id)

    def apply_theme(self, theme_id: Any) -> str:
        return self._apply_resolved_theme(resolve_graph_theme(theme_id))

    def apply_settings(self, *, shell_theme_id: Any, graph_theme_settings: Any) -> str:
        resolved = resolve_active_graph_theme(
            shell_theme_id=shell_theme_id,
            graph_theme_settings=graph_theme_settings,
        )
        return self._apply_resolved_theme(resolved)

    @pyqtProperty(str, notify=changed)
    def theme_id(self) -> str:
        return self._theme.theme_id

    @pyqtProperty(str, notify=changed)
    def theme_label(self) -> str:
        return self._theme.label

    @pyqtProperty("QVariantMap", notify=changed)
    def theme(self) -> dict[str, object]:
        return self._theme.as_dict()

    @pyqtProperty("QVariantMap", notify=changed)
    def node_palette(self) -> dict[str, str]:
        return self._theme.node_tokens.as_dict()

    @pyqtProperty("QVariantMap", notify=changed)
    def edge_palette(self) -> dict[str, str]:
        return self._theme.edge_tokens.as_dict()

    @pyqtProperty("QVariantMap", notify=changed)
    def category_accent_palette(self) -> dict[str, str]:
        return self._theme.category_accent_tokens.as_dict()

    @pyqtProperty("QVariantMap", notify=changed)
    def port_kind_palette(self) -> dict[str, str]:
        return self._theme.port_kind_tokens.as_dict()

    def _apply_resolved_theme(self, resolved_theme: Any) -> str:
        if resolved_theme == self._theme:
            return self._theme.theme_id
        self._theme = resolved_theme
        self.changed.emit()
        return self._theme.theme_id
