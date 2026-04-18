from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from ea_node_editor.graph.effective_ports import visible_ports
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.builtins.subnode import is_subnode_shell_type
from ea_node_editor.nodes.types import NodeTypeSpec, inline_property_specs
from ea_node_editor.settings import (
    DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    GRAPH_LABEL_PIXEL_SIZE_MAX,
    GRAPH_LABEL_PIXEL_SIZE_MIN,
    GRAPH_NODE_ICON_PIXEL_SIZE_MAX,
)

from .surface_contract import (
    GraphNodeSurfaceMetrics,
    STANDARD_BODY_LEFT_MARGIN,
    STANDARD_BODY_RIGHT_MARGIN,
    STANDARD_BODY_TOP,
    STANDARD_BOTTOM_PADDING,
    STANDARD_CENTER_GAP,
    STANDARD_COLLAPSED_HEIGHT,
    STANDARD_COLLAPSED_WIDTH,
    STANDARD_DEFAULT_WIDTH,
    STANDARD_HEADER_HEIGHT,
    STANDARD_HEADER_TOP_MARGIN,
    STANDARD_INLINE_ROW_SPACING,
    STANDARD_INLINE_SECTION_PADDING,
    STANDARD_MIN_HEIGHT,
    STANDARD_PORT_CENTER_OFFSET,
    STANDARD_PORT_DOT_RADIUS,
    STANDARD_PORT_GUTTER,
    STANDARD_PORT_HEIGHT,
    STANDARD_PORT_SIDE_MARGIN,
    STANDARD_RESIZE_HANDLE_SIZE,
    STANDARD_SHOW_ACCENT_BAR,
    STANDARD_SHOW_HEADER_BACKGROUND,
    STANDARD_TITLE_LEFT_MARGIN,
    STANDARD_TITLE_RIGHT_MARGIN,
    STANDARD_USE_HOST_CHROME,
    VIEWER_BODY_BOTTOM_PADDING,
    VIEWER_LEGACY_DEFAULT_BODY_HEIGHTS,
    _StandardWidthContract,
    _resolved_dimensions,
)

_STANDARD_NARROW_TEXT_CHARS = frozenset(" !\"'`.,:;|ijlItfr")
_STANDARD_WIDE_TEXT_CHARS = frozenset("MWQG@#%&wm")
_STANDARD_PUNCTUATION_TEXT_CHARS = frozenset("_-/\\+=*~^()[]{}")
_STANDARD_TEXT_WIDTH_PADDING = 2.0
_STANDARD_SUBNODE_SCOPE_BADGE_RESERVE = 56.0
_STANDARD_HEADER_BODY_GAP = max(
    0.0,
    STANDARD_BODY_TOP - (STANDARD_HEADER_TOP_MARGIN + STANDARD_HEADER_HEIGHT),
)
_STANDARD_HEADER_CONTENT_VERTICAL_PADDING = max(
    0.0,
    STANDARD_HEADER_HEIGHT - float(GRAPH_LABEL_PIXEL_SIZE_MAX + 2),
)


def standard_inline_row_height(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> float:
    return float(max(24, standard_inline_property_pixel_size(value) + 16))


def standard_inline_textarea_row_height(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> float:
    return float(max(96, int(round(standard_inline_row_height(value) * 4.0))))


def standard_inline_body_height(
    spec: NodeTypeSpec,
    *,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
) -> float:
    inline_specs = inline_property_specs(spec)
    if len(inline_specs) <= 0:
        return 0.0
    inline_row_height = standard_inline_row_height(graph_label_pixel_size)
    textarea_row_height = standard_inline_textarea_row_height(graph_label_pixel_size)
    total_row_height = 0.0
    for property_spec in inline_specs:
        editor = str(property_spec.inline_editor or "").strip().lower()
        total_row_height += (
            textarea_row_height
            if editor == "textarea"
            else inline_row_height
        )
    return (
        STANDARD_INLINE_SECTION_PADDING
        + total_row_height
        + max(0, len(inline_specs) - 1) * STANDARD_INLINE_ROW_SPACING
    )


def _estimated_standard_text_unit_width(character: str) -> float:
    if not character:
        return 0.0
    if character.isspace() or character in _STANDARD_NARROW_TEXT_CHARS:
        return 0.24
    if character in _STANDARD_WIDE_TEXT_CHARS:
        return 0.62
    if character in _STANDARD_PUNCTUATION_TEXT_CHARS:
        return 0.34
    if character.isupper() or character.isdigit():
        return 0.48
    return 0.44


def _normalize_graph_label_pixel_size(value: object) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return DEFAULT_GRAPH_LABEL_PIXEL_SIZE
    return max(GRAPH_LABEL_PIXEL_SIZE_MIN, min(numeric, GRAPH_LABEL_PIXEL_SIZE_MAX))


def standard_graph_label_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return _normalize_graph_label_pixel_size(value)


def standard_node_title_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return standard_graph_label_pixel_size(value) + 2


def standard_node_title_icon_pixel_size(
    value: object | None = None,
    *,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
) -> int:
    fallback = standard_graph_label_pixel_size(graph_label_pixel_size)
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(GRAPH_LABEL_PIXEL_SIZE_MIN, min(numeric, GRAPH_NODE_ICON_PIXEL_SIZE_MAX))


def standard_header_height(
    *,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    graph_node_icon_pixel_size: object | None = None,
) -> float:
    title_pixel_size = standard_node_title_pixel_size(graph_label_pixel_size)
    icon_pixel_size = standard_node_title_icon_pixel_size(
        graph_node_icon_pixel_size,
        graph_label_pixel_size=graph_label_pixel_size,
    )
    content_height = max(title_pixel_size, icon_pixel_size)
    return float(
        max(
            STANDARD_HEADER_HEIGHT,
            content_height + _STANDARD_HEADER_CONTENT_VERTICAL_PADDING,
        )
    )


def standard_body_top(
    *,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    graph_node_icon_pixel_size: object | None = None,
) -> float:
    return float(
        STANDARD_HEADER_TOP_MARGIN
        + standard_header_height(
            graph_label_pixel_size=graph_label_pixel_size,
            graph_node_icon_pixel_size=graph_node_icon_pixel_size,
        )
        + _STANDARD_HEADER_BODY_GAP
    )


def standard_port_label_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return standard_graph_label_pixel_size(value)


def standard_elapsed_footer_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return standard_graph_label_pixel_size(value)


def standard_inline_property_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return standard_graph_label_pixel_size(value)


def standard_badge_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return max(9, standard_graph_label_pixel_size(value) - 1)


def standard_edge_label_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return standard_graph_label_pixel_size(value) + 1


def standard_edge_pill_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return standard_graph_label_pixel_size(value) + 2


def standard_exec_arrow_port_pixel_size(value: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE) -> int:
    return standard_graph_label_pixel_size(value) + 8


def standard_viewer_port_row_height(
    *,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
) -> float:
    return float(
        max(
            STANDARD_PORT_HEIGHT,
            standard_exec_arrow_port_pixel_size(graph_label_pixel_size),
        )
    )


@lru_cache(maxsize=1024)
def _qt_standard_text_width(content: str, pixel_size: int, font_description: str) -> float:
    from PyQt6.QtGui import QFont, QFontMetricsF

    font = QFont()
    if font_description:
        font.fromString(font_description)
    font.setPixelSize(max(1, int(pixel_size)))
    metrics = QFontMetricsF(font)
    return round(max(0.0, metrics.horizontalAdvance(content) + _STANDARD_TEXT_WIDTH_PADDING), 3)


def _estimate_standard_text_width(text: Any, *, pixel_size: float) -> float:
    content = str(text or "")
    if not content:
        return 0.0
    try:
        from PyQt6.QtWidgets import QApplication
    except Exception:
        QApplication = None
    if QApplication is not None:
        app = QApplication.instance()
        if app is not None:
            return _qt_standard_text_width(
                content,
                int(round(float(pixel_size))),
                app.font().toString(),
            )
    width = sum(_estimated_standard_text_unit_width(character) for character in content) * float(pixel_size)
    return round(max(0.0, width + _STANDARD_TEXT_WIDTH_PADDING), 3)


def _standard_title_full_width(
    node: NodeInstance,
    *,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
) -> float:
    title_width = _estimate_standard_text_width(
        node.title,
        pixel_size=standard_node_title_pixel_size(graph_label_pixel_size),
    )
    scope_badge_reserve = _STANDARD_SUBNODE_SCOPE_BADGE_RESERVE if is_subnode_shell_type(node.type_id) else 0.0
    return round(title_width + STANDARD_TITLE_LEFT_MARGIN + STANDARD_TITLE_RIGHT_MARGIN + scope_badge_reserve, 3)


def _standard_visible_label_widths(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
    *,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
) -> tuple[float, float]:
    scoped_nodes = workspace_nodes or {node.node_id: node}
    port_label_pixel_size = standard_port_label_pixel_size(graph_label_pixel_size)
    in_ports, out_ports = visible_ports(node=node, spec=spec, workspace_nodes=scoped_nodes)
    left_label_width = max(
        (
            _estimate_standard_text_width(port.label or port.key, pixel_size=port_label_pixel_size)
            for port in in_ports
        ),
        default=0.0,
    )
    right_label_width = max(
        (
            _estimate_standard_text_width(port.label or port.key, pixel_size=port_label_pixel_size)
            for port in out_ports
        ),
        default=0.0,
    )
    return round(left_label_width, 3), round(right_label_width, 3)


def _standard_port_label_min_width(left_label_width: float, right_label_width: float) -> float:
    return round(
        float(left_label_width) + float(right_label_width) + (STANDARD_PORT_GUTTER * 2.0) + STANDARD_CENTER_GAP,
        3,
    )


def _standard_surface_min_width_contract(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
    *,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
) -> _StandardWidthContract:
    left_label_width, right_label_width = _standard_visible_label_widths(
        node,
        spec,
        workspace_nodes,
        graph_label_pixel_size=graph_label_pixel_size,
    )
    return _StandardWidthContract(
        title_full_width=_standard_title_full_width(
            node,
            graph_label_pixel_size=graph_label_pixel_size,
        ),
        left_label_width=left_label_width,
        right_label_width=right_label_width,
        port_gutter=STANDARD_PORT_GUTTER,
        center_gap=STANDARD_CENTER_GAP,
        port_label_min_width=_standard_port_label_min_width(left_label_width, right_label_width),
    )


def _standard_surface_metrics(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
    *,
    show_port_labels: bool = True,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    graph_node_icon_pixel_size: object | None = None,
) -> GraphNodeSurfaceMetrics:
    from .surface_contract import _visible_port_count

    port_count = _visible_port_count(node, spec, workspace_nodes)
    header_height = standard_header_height(
        graph_label_pixel_size=graph_label_pixel_size,
        graph_node_icon_pixel_size=graph_node_icon_pixel_size,
    )
    body_top = standard_body_top(
        graph_label_pixel_size=graph_label_pixel_size,
        graph_node_icon_pixel_size=graph_node_icon_pixel_size,
    )
    body_height = standard_inline_body_height(
        spec,
        graph_label_pixel_size=graph_label_pixel_size,
    )
    default_height = header_height + body_height + port_count * STANDARD_PORT_HEIGHT + STANDARD_BOTTOM_PADDING
    width_contract = _standard_surface_min_width_contract(
        node,
        spec,
        workspace_nodes,
        graph_label_pixel_size=graph_label_pixel_size,
    )
    min_width = width_contract.min_width_with_labels if show_port_labels else width_contract.min_width_without_labels
    min_height = max(float(STANDARD_MIN_HEIGHT), float(default_height))
    return GraphNodeSurfaceMetrics(
        default_width=STANDARD_DEFAULT_WIDTH,
        default_height=default_height,
        min_width=min_width,
        min_height=min_height,
        collapsed_width=STANDARD_COLLAPSED_WIDTH,
        collapsed_height=STANDARD_COLLAPSED_HEIGHT,
        header_height=header_height,
        header_top_margin=STANDARD_HEADER_TOP_MARGIN,
        body_top=body_top,
        body_height=body_height,
        port_top=body_top + body_height,
        port_height=STANDARD_PORT_HEIGHT,
        port_center_offset=STANDARD_PORT_CENTER_OFFSET,
        port_side_margin=STANDARD_PORT_SIDE_MARGIN,
        port_dot_radius=STANDARD_PORT_DOT_RADIUS,
        resize_handle_size=STANDARD_RESIZE_HANDLE_SIZE,
        title_top=STANDARD_HEADER_TOP_MARGIN,
        title_height=header_height,
        title_left_margin=STANDARD_TITLE_LEFT_MARGIN,
        title_right_margin=STANDARD_TITLE_RIGHT_MARGIN,
        title_centered=False,
        body_left_margin=STANDARD_BODY_LEFT_MARGIN,
        body_right_margin=STANDARD_BODY_RIGHT_MARGIN,
        body_bottom_margin=STANDARD_BOTTOM_PADDING,
        show_header_background=STANDARD_SHOW_HEADER_BACKGROUND,
        show_accent_bar=STANDARD_SHOW_ACCENT_BAR,
        use_host_chrome=STANDARD_USE_HOST_CHROME,
        standard_title_full_width=width_contract.title_full_width,
        standard_left_label_width=width_contract.left_label_width,
        standard_right_label_width=width_contract.right_label_width,
        standard_port_gutter=width_contract.port_gutter,
        standard_center_gap=width_contract.center_gap,
        standard_port_label_min_width=width_contract.port_label_min_width,
    )


def resolved_node_surface_size(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
    *,
    show_port_labels: bool = True,
    surface_metrics: GraphNodeSurfaceMetrics | None = None,
    clamp_height: bool = False,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    graph_node_icon_pixel_size: object | None = None,
) -> tuple[float, float]:
    metrics = surface_metrics or node_surface_metrics(
        node,
        spec,
        workspace_nodes,
        show_port_labels=show_port_labels,
        graph_label_pixel_size=graph_label_pixel_size,
        graph_node_icon_pixel_size=graph_node_icon_pixel_size,
    )
    if node.collapsed:
        return float(metrics.collapsed_width), float(metrics.collapsed_height)

    width, height = _resolved_dimensions(
        node,
        default_width=metrics.default_width,
        default_height=metrics.default_height,
    )
    resolved_width = max(float(metrics.min_width), float(width))
    resolved_height = max(float(metrics.min_height), float(height))
    family = str(spec.surface_family or "standard").strip() or "standard"
    if family == "viewer" and node.custom_height is not None:
        viewer_height_tolerance = 1.0

        def _matches_viewer_height(value: float, expected: float) -> bool:
            return abs(float(value) - float(expected)) <= viewer_height_tolerance

        baseline_node = node.clone()
        baseline_node.custom_height = None
        baseline_metrics = node_surface_metrics(
            baseline_node,
            spec,
            workspace_nodes,
            show_port_labels=show_port_labels,
            graph_label_pixel_size=graph_label_pixel_size,
            graph_node_icon_pixel_size=None,
        )
        from .surface_contract import _visible_port_count

        port_count = _visible_port_count(node, spec, workspace_nodes)
        body_top = standard_body_top(
            graph_label_pixel_size=graph_label_pixel_size,
            graph_node_icon_pixel_size=graph_node_icon_pixel_size,
        )
        port_row_height = standard_viewer_port_row_height(
            graph_label_pixel_size=graph_label_pixel_size,
        )
        inline_body_height = standard_inline_body_height(
            spec,
            graph_label_pixel_size=graph_label_pixel_size,
        )
        legacy_default_heights = {
            float(
                body_top
                + max(float(legacy_body_height), float(inline_body_height))
                + port_count * port_row_height
                + VIEWER_BODY_BOTTOM_PADDING
            )
            for legacy_body_height in VIEWER_LEGACY_DEFAULT_BODY_HEIGHTS
        }
        if _matches_viewer_height(float(node.custom_height), float(baseline_metrics.default_height)) or any(
            _matches_viewer_height(float(node.custom_height), legacy_height)
            for legacy_height in legacy_default_heights
        ):
            resolved_height = float(metrics.default_height)
    if clamp_height:
        resolved_height = max(float(metrics.min_height), resolved_height)
    return resolved_width, resolved_height


def node_surface_metrics(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
    *,
    show_port_labels: bool = True,
    graph_label_pixel_size: object = DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
    graph_node_icon_pixel_size: object | None = None,
) -> GraphNodeSurfaceMetrics:
    family = str(spec.surface_family or "standard").strip() or "standard"
    if family == "flowchart":
        from .flowchart_metrics import _flowchart_surface_metrics

        return _flowchart_surface_metrics(node, spec, workspace_nodes)
    if family == "planning":
        from .panel_metrics import _planning_surface_metrics

        return _planning_surface_metrics(node, spec)
    if family == "annotation":
        from .panel_metrics import _annotation_surface_metrics

        return _annotation_surface_metrics(node, spec)
    if family == "comment_backdrop":
        from .panel_metrics import _comment_backdrop_surface_metrics

        return _comment_backdrop_surface_metrics(node, spec)
    if family == "media":
        from .panel_metrics import _media_surface_metrics

        return _media_surface_metrics(node, spec)
    if family == "viewer":
        from .viewer_metrics import _viewer_surface_metrics

        return _viewer_surface_metrics(
            node,
            spec,
            workspace_nodes,
            show_port_labels=show_port_labels,
            graph_label_pixel_size=graph_label_pixel_size,
            graph_node_icon_pixel_size=graph_node_icon_pixel_size,
        )
    return _standard_surface_metrics(
        node,
        spec,
        workspace_nodes,
        show_port_labels=show_port_labels,
        graph_label_pixel_size=graph_label_pixel_size,
        graph_node_icon_pixel_size=graph_node_icon_pixel_size,
    )
