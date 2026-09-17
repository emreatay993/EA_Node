from __future__ import annotations

from dataclasses import asdict, dataclass

from ea_node_editor.ui.graph_theme.tokens import (
    GRAPH_PORT_KIND_TOKENS_V1,
    GRAPH_STITCH_DARK_EDGE_TOKENS_V1,
    GRAPH_STITCH_DARK_NODE_TOKENS_V1,
    GRAPH_STITCH_DARK_PORT_STATE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_NODE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_PORT_STATE_TOKENS_V1,
    GraphEdgeTokens,
    GraphNodeTokens,
    GraphPortKindTokens,
    GraphPortStateTokens,
)
from ea_node_editor.ui.theme.registry import resolve_theme_id

DEFAULT_GRAPH_THEME_ID = "graph_stitch_dark"


@dataclass(frozen=True, slots=True)
class GraphThemeDefinition:
    theme_id: str
    label: str
    node_tokens: GraphNodeTokens
    edge_tokens: GraphEdgeTokens
    port_kind_tokens: GraphPortKindTokens
    # Grip flow-state colors are shared per brightness rather than authored
    # per palette family: warning/error/neutral must read as alerts in every
    # theme, so hue-family variation would only dilute them.
    port_state_tokens: GraphPortStateTokens = GRAPH_STITCH_DARK_PORT_STATE_TOKENS_V1

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


# Graph palettes are not user-selectable: each shell theme owns exactly one.
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
        port_kind_tokens=GRAPH_PORT_KIND_TOKENS_V1,
        port_state_tokens=GRAPH_STITCH_DARK_PORT_STATE_TOKENS_V1,
    ),
    "graph_stitch_light": GraphThemeDefinition(
        theme_id="graph_stitch_light",
        label="Graph Stitch Light",
        node_tokens=GRAPH_STITCH_LIGHT_NODE_TOKENS_V1,
        edge_tokens=GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1,
        port_kind_tokens=GRAPH_PORT_KIND_TOKENS_V1,
        port_state_tokens=GRAPH_STITCH_LIGHT_PORT_STATE_TOKENS_V1,
    ),
}


def resolve_graph_theme(theme_id: object) -> GraphThemeDefinition:
    if isinstance(theme_id, GraphThemeDefinition):
        return theme_id
    normalized = str(theme_id).strip()
    return GRAPH_THEME_REGISTRY.get(normalized, GRAPH_THEME_REGISTRY[DEFAULT_GRAPH_THEME_ID])


def default_graph_theme_id_for_shell_theme(theme_id: object) -> str:
    resolved_shell_theme_id = resolve_theme_id(theme_id)
    return SHELL_THEME_TO_GRAPH_THEME.get(resolved_shell_theme_id, DEFAULT_GRAPH_THEME_ID)


__all__ = [
    "DEFAULT_GRAPH_THEME_ID",
    "GRAPH_THEME_REGISTRY",
    "SHELL_THEME_TO_GRAPH_THEME",
    "GraphThemeDefinition",
    "default_graph_theme_id_for_shell_theme",
    "resolve_graph_theme",
]
