from __future__ import annotations

"""Graph theme, typography, and pixel-size payload inputs."""


from typing import TYPE_CHECKING


from ea_node_editor.app_preferences import (
    effective_graph_node_icon_pixel_size,
    normalize_plot_settings,
)
from ea_node_editor.settings import (
    DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    GRAPH_LABEL_PIXEL_SIZE_MAX,
    GRAPH_LABEL_PIXEL_SIZE_MIN,
)
from ea_node_editor.ui.graph_theme import (
    DEFAULT_GRAPH_THEME_ID,
    GraphThemeDefinition,
    resolve_graph_theme,
)

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge



class _GraphSceneThemeResolver:
    @staticmethod
    def active_graph_theme(graph_theme_bridge: GraphThemeBridge | None) -> GraphThemeDefinition:
        if graph_theme_bridge is None:
            return resolve_graph_theme(DEFAULT_GRAPH_THEME_ID)
        return resolve_graph_theme(graph_theme_bridge.theme)


def _normalize_graph_label_pixel_size(value: object) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return DEFAULT_GRAPH_LABEL_PIXEL_SIZE
    return max(GRAPH_LABEL_PIXEL_SIZE_MIN, min(numeric, GRAPH_LABEL_PIXEL_SIZE_MAX))


def _graph_typography_source(graph_theme_bridge: GraphThemeBridge | None) -> object | None:
    if graph_theme_bridge is None:
        return None
    host = graph_theme_bridge.parent()
    if host is None:
        return None
    presenter = getattr(host, "graph_canvas_presenter", None)
    return presenter if presenter is not None else host


def _graph_label_pixel_size(graph_theme_bridge: GraphThemeBridge | None) -> int:
    source = _graph_typography_source(graph_theme_bridge)
    if source is None:
        return DEFAULT_GRAPH_LABEL_PIXEL_SIZE
    return _normalize_graph_label_pixel_size(
        getattr(source, "graphics_graph_label_pixel_size", DEFAULT_GRAPH_LABEL_PIXEL_SIZE)
    )


def _graph_node_icon_pixel_size(
    graph_theme_bridge: GraphThemeBridge | None,
    *,
    graph_label_pixel_size: int,
) -> int:
    source = _graph_typography_source(graph_theme_bridge)
    if source is None:
        return effective_graph_node_icon_pixel_size(graph_label_pixel_size, None)
    effective_value = getattr(source, "graphics_node_title_icon_pixel_size", None)
    if effective_value is not None:
        return int(effective_value)
    return effective_graph_node_icon_pixel_size(
        graph_label_pixel_size,
        getattr(source, "graphics_graph_node_icon_pixel_size_override", None),
    )


def _graphics_lightweight_canvas(graph_theme_bridge: GraphThemeBridge | None) -> bool:
    source = _graph_typography_source(graph_theme_bridge)
    if source is not None and hasattr(source, "graphics_lightweight_canvas"):
        value = getattr(source, "graphics_lightweight_canvas", False)
        return bool(value) if isinstance(value, bool) else False
    host = graph_theme_bridge.parent() if graph_theme_bridge is not None else None
    controller = getattr(host, "app_preferences_controller", None) if host is not None else None
    plot_settings = getattr(controller, "plot_settings", None)
    if callable(plot_settings):
        value = normalize_plot_settings(plot_settings()).get("lightweight_canvas", False)
        return bool(value) if isinstance(value, bool) else False
    value = getattr(source, "graphics_lightweight_canvas", False) if source is not None else False
    return bool(value) if isinstance(value, bool) else False


