from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

from ea_node_editor.ui.graph_theme import DEFAULT_GRAPH_THEME_ID, GraphThemeService


class GraphThemeBridge(QObject):
    changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        theme_id: object = DEFAULT_GRAPH_THEME_ID,
        graph_theme_service: GraphThemeService | None = None,
    ) -> None:
        super().__init__(parent)
        self._graph_theme_service = graph_theme_service or GraphThemeService(theme_id=theme_id)

    def apply_theme(self, theme_id: Any) -> str:
        if self._graph_theme_service.apply_theme(theme_id):
            self.changed.emit()
        return self._graph_theme_service.theme_id

    def apply_settings(self, *, shell_theme_id: Any, graph_theme_settings: Any) -> str:
        if self._graph_theme_service.apply_settings(
            shell_theme_id=shell_theme_id,
            graph_theme_settings=graph_theme_settings,
        ):
            self.changed.emit()
        return self._graph_theme_service.theme_id

    @pyqtProperty(str, notify=changed)
    def theme_id(self) -> str:
        return self._graph_theme_service.theme_id

    @pyqtProperty(str, notify=changed)
    def theme_label(self) -> str:
        return self._graph_theme_service.label

    @pyqtProperty("QVariantMap", notify=changed)
    def theme(self) -> dict[str, object]:
        return self._graph_theme_service.theme.as_dict()

    @pyqtProperty("QVariantMap", notify=changed)
    def node_palette(self) -> dict[str, str]:
        return self._graph_theme_service.theme.node_tokens.as_dict()

    @pyqtProperty("QVariantMap", notify=changed)
    def edge_palette(self) -> dict[str, str]:
        return self._graph_theme_service.theme.edge_tokens.as_dict()

    @pyqtProperty("QVariantMap", notify=changed)
    def category_accent_palette(self) -> dict[str, str]:
        return self._graph_theme_service.theme.category_accent_tokens.as_dict()

    @pyqtProperty("QVariantMap", notify=changed)
    def port_kind_palette(self) -> dict[str, str]:
        return self._graph_theme_service.theme.port_kind_tokens.as_dict()
