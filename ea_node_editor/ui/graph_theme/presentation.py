from __future__ import annotations

from collections.abc import Sequence

from ea_node_editor.nodes.category_paths import CATEGORY_DISPLAY_SEPARATOR, normalize_category_path
from ea_node_editor.ui.graph_theme.registry import GraphThemeDefinition, resolve_graph_theme


def resolve_category_accent(graph_theme: GraphThemeDefinition | object, category: object) -> str:
    theme = _resolve_theme(graph_theme)
    normalized = _category_root_segment(category).strip().lower()
    if normalized.startswith("core"):
        return theme.category_accent_tokens.core
    if "input" in normalized or "output" in normalized:
        return theme.category_accent_tokens.input_output
    if "physics" in normalized:
        return theme.category_accent_tokens.physics
    if "logic" in normalized:
        return theme.category_accent_tokens.logic
    if "hpc" in normalized:
        return theme.category_accent_tokens.hpc
    return theme.category_accent_tokens.default


def _category_root_segment(category: object) -> str:
    category_path = getattr(category, "category_path", None)
    if category_path is not None:
        try:
            return normalize_category_path(category_path)[0]
        except (TypeError, ValueError):
            pass

    if isinstance(category, Sequence) and not isinstance(category, (str, bytes, bytearray)):
        try:
            return normalize_category_path(category)[0]
        except (TypeError, ValueError):
            pass

    text = str(category).strip()
    if CATEGORY_DISPLAY_SEPARATOR in text:
        return text.split(CATEGORY_DISPLAY_SEPARATOR, 1)[0].strip()
    return text


def resolve_port_kind_color(graph_theme: GraphThemeDefinition | object, port_kind: object) -> str:
    theme = _resolve_theme(graph_theme)
    normalized = str(port_kind).strip().lower()
    if normalized == "exec":
        return theme.port_kind_tokens.exec
    if normalized == "completed":
        return theme.port_kind_tokens.completed
    if normalized == "failed":
        return theme.port_kind_tokens.failed
    return theme.port_kind_tokens.data


def resolve_edge_default_color(graph_theme: GraphThemeDefinition | object, port_kind: object) -> str:
    return resolve_port_kind_color(graph_theme, port_kind)


def resolve_edge_warning_color(graph_theme: GraphThemeDefinition | object) -> str:
    return _resolve_theme(graph_theme).edge_tokens.warning_stroke


def resolve_edge_color(
    graph_theme: GraphThemeDefinition | object,
    *,
    port_kind: object,
    data_type_warning: bool = False,
) -> str:
    if data_type_warning:
        return resolve_edge_warning_color(graph_theme)
    return resolve_edge_default_color(graph_theme, port_kind)


def _resolve_theme(graph_theme: GraphThemeDefinition | object) -> GraphThemeDefinition:
    if isinstance(graph_theme, GraphThemeDefinition):
        return graph_theme
    return resolve_graph_theme(graph_theme)


__all__ = [
    "resolve_category_accent",
    "resolve_edge_color",
    "resolve_edge_default_color",
    "resolve_edge_warning_color",
    "resolve_port_kind_color",
]
