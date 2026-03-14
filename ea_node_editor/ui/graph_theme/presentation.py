from __future__ import annotations

from ea_node_editor.ui.graph_theme.registry import GraphThemeDefinition, resolve_graph_theme


def resolve_category_accent(graph_theme: GraphThemeDefinition | object, category: object) -> str:
    theme = _resolve_theme(graph_theme)
    normalized = str(category).strip().lower()
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
