from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class GraphNodeTokens:
    card_bg: str
    card_border: str
    card_selected_border: str
    header_bg: str
    header_fg: str
    scope_badge_bg: str
    scope_badge_border: str
    scope_badge_fg: str
    inline_row_bg: str
    inline_row_border: str
    inline_label_fg: str
    inline_input_fg: str
    inline_input_bg: str
    inline_input_border: str
    inline_driven_fg: str
    port_label_fg: str
    port_interactive_fill: str
    port_interactive_border: str
    port_interactive_ring_fill: str
    port_interactive_ring_border: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GraphEdgeTokens:
    warning_stroke: str
    selected_stroke: str
    preview_stroke: str
    valid_drag_stroke: str
    invalid_drag_stroke: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GraphCategoryAccentTokens:
    default: str
    core: str
    input_output: str
    physics: str
    logic: str
    hpc: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GraphPortKindTokens:
    data: str
    exec: str
    completed: str
    failed: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


GRAPH_CATEGORY_ACCENT_TOKENS_V1 = GraphCategoryAccentTokens(
    default="#4AA9D6",
    core="#2F89FF",
    input_output="#22B455",
    physics="#D88C32",
    logic="#B35BD1",
    hpc="#C75050",
)


GRAPH_PORT_KIND_TOKENS_V1 = GraphPortKindTokens(
    data="#7AA8FF",
    exec="#67D487",
    completed="#E4CE7D",
    failed="#D94F4F",
)


GRAPH_STITCH_DARK_NODE_TOKENS_V1 = GraphNodeTokens(
    card_bg="#1b1d22",
    card_border="#3a3d45",
    card_selected_border="#60CDFF",
    header_bg="#2a2b30",
    header_fg="#f0f4fb",
    scope_badge_bg="#1D8CE0",
    scope_badge_border="#60CDFF",
    scope_badge_fg="#f2f4f8",
    inline_row_bg="#24262c",
    inline_row_border="#4a4f5a",
    inline_label_fg="#d0d5de",
    inline_input_fg="#f0f2f5",
    inline_input_bg="#22242a",
    inline_input_border="#4a4f5a",
    inline_driven_fg="#bdc5d3",
    port_label_fg="#d0d5de",
    port_interactive_fill="#FFDA6B",
    port_interactive_border="#FFE48B",
    port_interactive_ring_fill="#44FFC857",
    port_interactive_ring_border="#66FFE29A",
)


GRAPH_STITCH_LIGHT_NODE_TOKENS_V1 = GraphNodeTokens(
    card_bg="#f5f7fa",
    card_border="#b7c2ce",
    card_selected_border="#1D8CE0",
    header_bg="#e5ebf2",
    header_fg="#1b2733",
    scope_badge_bg="#b9dcf7",
    scope_badge_border="#1D8CE0",
    scope_badge_fg="#162231",
    inline_row_bg="#ffffff",
    inline_row_border="#96a6ba",
    inline_label_fg="#5f6b7a",
    inline_input_fg="#17212b",
    inline_input_bg="#ffffff",
    inline_input_border="#96a6ba",
    inline_driven_fg="#4f5e70",
    port_label_fg="#5f6b7a",
    port_interactive_fill="#FFDA6B",
    port_interactive_border="#E7C35D",
    port_interactive_ring_fill="#33A7D98A",
    port_interactive_ring_border="#5598C971",
)


GRAPH_STITCH_DARK_EDGE_TOKENS_V1 = GraphEdgeTokens(
    warning_stroke="#E8A838",
    selected_stroke="#f0f4fb",
    preview_stroke="#60CDFF",
    valid_drag_stroke="#60CDFF",
    invalid_drag_stroke="#d0d5de",
)


GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1 = GraphEdgeTokens(
    warning_stroke="#D58E1E",
    selected_stroke="#1b2733",
    preview_stroke="#1D8CE0",
    valid_drag_stroke="#1D8CE0",
    invalid_drag_stroke="#5f6b7a",
)


__all__ = [
    "GRAPH_CATEGORY_ACCENT_TOKENS_V1",
    "GRAPH_PORT_KIND_TOKENS_V1",
    "GRAPH_STITCH_DARK_EDGE_TOKENS_V1",
    "GRAPH_STITCH_DARK_NODE_TOKENS_V1",
    "GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1",
    "GRAPH_STITCH_LIGHT_NODE_TOKENS_V1",
    "GraphCategoryAccentTokens",
    "GraphEdgeTokens",
    "GraphNodeTokens",
    "GraphPortKindTokens",
]
