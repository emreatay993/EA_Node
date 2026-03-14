from __future__ import annotations

from dataclasses import asdict, dataclass

from ea_node_editor.ui.graph_theme.tokens import (
    GRAPH_CATEGORY_ACCENT_TOKENS_V1,
    GRAPH_PORT_KIND_TOKENS_V1,
    GRAPH_STITCH_DARK_EDGE_TOKENS_V1,
    GRAPH_STITCH_DARK_NODE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_NODE_TOKENS_V1,
    GraphCategoryAccentTokens,
    GraphEdgeTokens,
    GraphNodeTokens,
    GraphPortKindTokens,
)
from ea_node_editor.ui.theme.registry import resolve_theme_id

DEFAULT_GRAPH_THEME_ID = "graph_stitch_dark"


@dataclass(frozen=True, slots=True)
class GraphThemeDefinition:
    theme_id: str
    label: str
    node_tokens: GraphNodeTokens
    edge_tokens: GraphEdgeTokens
    category_accent_tokens: GraphCategoryAccentTokens
    port_kind_tokens: GraphPortKindTokens

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


SHELL_THEME_TO_GRAPH_THEME = {
    "stitch_dark": "graph_stitch_dark",
    "stitch_light": "graph_stitch_light",
}


GRAPH_THEME_REGISTRY: dict[str, GraphThemeDefinition] = {
    "graph_stitch_dark": GraphThemeDefinition(
        theme_id="graph_stitch_dark",
        label="Graph Stitch Dark",
        node_tokens=GRAPH_STITCH_DARK_NODE_TOKENS_V1,
        edge_tokens=GRAPH_STITCH_DARK_EDGE_TOKENS_V1,
        category_accent_tokens=GRAPH_CATEGORY_ACCENT_TOKENS_V1,
        port_kind_tokens=GRAPH_PORT_KIND_TOKENS_V1,
    ),
    "graph_stitch_light": GraphThemeDefinition(
        theme_id="graph_stitch_light",
        label="Graph Stitch Light",
        node_tokens=GRAPH_STITCH_LIGHT_NODE_TOKENS_V1,
        edge_tokens=GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1,
        category_accent_tokens=GRAPH_CATEGORY_ACCENT_TOKENS_V1,
        port_kind_tokens=GRAPH_PORT_KIND_TOKENS_V1,
    ),
}


def graph_theme_choices() -> tuple[tuple[str, str], ...]:
    return tuple((theme.theme_id, theme.label) for theme in GRAPH_THEME_REGISTRY.values())


def is_known_graph_theme_id(theme_id: object) -> bool:
    return str(theme_id).strip() in GRAPH_THEME_REGISTRY


def resolve_graph_theme(theme_id: object) -> GraphThemeDefinition:
    normalized = str(theme_id).strip()
    return GRAPH_THEME_REGISTRY.get(normalized, GRAPH_THEME_REGISTRY[DEFAULT_GRAPH_THEME_ID])


def resolve_graph_theme_id(theme_id: object) -> str:
    return resolve_graph_theme(theme_id).theme_id


def default_graph_theme_id_for_shell_theme(theme_id: object) -> str:
    resolved_shell_theme_id = resolve_theme_id(theme_id)
    return SHELL_THEME_TO_GRAPH_THEME.get(resolved_shell_theme_id, DEFAULT_GRAPH_THEME_ID)


__all__ = [
    "DEFAULT_GRAPH_THEME_ID",
    "GRAPH_THEME_REGISTRY",
    "SHELL_THEME_TO_GRAPH_THEME",
    "GraphThemeDefinition",
    "default_graph_theme_id_for_shell_theme",
    "graph_theme_choices",
    "is_known_graph_theme_id",
    "resolve_graph_theme",
    "resolve_graph_theme_id",
]
