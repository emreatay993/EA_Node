from __future__ import annotations

import copy
from typing import Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.ui.graph_theme import DEFAULT_GRAPH_THEME_ID, GraphThemeDefinition, resolve_graph_theme


class GraphThemeBridge(QObject):
    changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        theme_id: object = DEFAULT_GRAPH_THEME_ID,
    ) -> None:
        super().__init__(parent)
        self._theme: GraphThemeDefinition = resolve_graph_theme(theme_id)
        self._theme_cache: dict[str, object] | None = None
        self._node_palette_cache: dict[str, object] | None = None
        self._edge_palette_cache: dict[str, str] | None = None
        self._port_kind_palette_cache: dict[str, str] | None = None
        self._port_state_palette_cache: dict[str, str] | None = None

    def _clear_projection_cache(self) -> None:
        self._theme_cache = None
        self._node_palette_cache = None
        self._edge_palette_cache = None
        self._port_kind_palette_cache = None
        self._port_state_palette_cache = None

    def apply_theme(self, theme_id: Any) -> str:
        resolved_theme = resolve_graph_theme(theme_id)
        if resolved_theme != self._theme:
            self._theme = resolved_theme
            self._clear_projection_cache()
            self.changed.emit()
        return self._theme.theme_id

    @pyqtProperty(str, notify=changed)
    def theme_id(self) -> str:
        return self._theme.theme_id

    @pyqtProperty(str, notify=changed)
    def theme_label(self) -> str:
        return self._theme.label

    @pyqtProperty("QVariantMap", notify=changed)
    def theme(self) -> dict[str, object]:
        if self._theme_cache is None:
            self._theme_cache = self._theme.as_dict()
        return copy.deepcopy(self._theme_cache)

    @pyqtProperty("QVariantMap", notify=changed)
    def node_palette(self) -> dict[str, object]:
        if self._node_palette_cache is None:
            self._node_palette_cache = self._theme.node_tokens.as_dict()
        return dict(self._node_palette_cache)

    @pyqtProperty("QVariantMap", notify=changed)
    def edge_palette(self) -> dict[str, str]:
        if self._edge_palette_cache is None:
            self._edge_palette_cache = self._theme.edge_tokens.as_dict()
        return dict(self._edge_palette_cache)

    @pyqtProperty("QVariantMap", notify=changed)
    def port_kind_palette(self) -> dict[str, str]:
        if self._port_kind_palette_cache is None:
            self._port_kind_palette_cache = self._theme.port_kind_tokens.as_dict()
        return dict(self._port_kind_palette_cache)

    @pyqtProperty("QVariantMap", notify=changed)
    def port_state_palette(self) -> dict[str, str]:
        if self._port_state_palette_cache is None:
            self._port_state_palette_cache = self._theme.port_state_tokens.as_dict()
        return dict(self._port_state_palette_cache)

    @pyqtSlot(str, result=str)
    def resolve_data_type_color(self, _color_token: str) -> str:
        """Resolve a projected family token through the active graph palette."""
        return self._theme.port_kind_tokens.data
