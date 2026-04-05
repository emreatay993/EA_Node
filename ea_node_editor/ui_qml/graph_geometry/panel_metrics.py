from __future__ import annotations

import math
import textwrap

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.media_preview_provider import local_image_dimensions
from ea_node_editor.ui.pdf_preview_provider import local_pdf_page_dimensions

from .surface_contract import (
    ANNOTATION_VARIANT_LAYOUTS,
    COMMENT_BACKDROP_VARIANT_LAYOUTS,
    MEDIA_CAPTION_CHAR_WIDTH_FACTOR,
    MEDIA_CAPTION_LINE_HEIGHT_FACTOR,
    MEDIA_CAPTION_MAX_LINES,
    MEDIA_CAPTION_SPACING,
    MEDIA_VARIANT_LAYOUTS,
    PASSIVE_PORT_DOT_RADIUS,
    PASSIVE_PORT_SIDE_MARGIN,
    PASSIVE_SURFACE_RESIZE_HANDLE_SIZE,
    PLANNING_VARIANT_LAYOUTS,
    STANDARD_COLLAPSED_HEIGHT,
    STANDARD_COLLAPSED_WIDTH,
    GraphNodeSurfaceMetrics,
    _MediaPanelLayout,
    _PassivePanelLayout,
    _resolved_dimensions,
    _safe_number,
)


def normalize_planning_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    return normalized if normalized in PLANNING_VARIANT_LAYOUTS else "task_card"


def normalize_annotation_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    return normalized if normalized in ANNOTATION_VARIANT_LAYOUTS else "sticky_note"


def normalize_comment_backdrop_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    return normalized if normalized in COMMENT_BACKDROP_VARIANT_LAYOUTS else "comment_backdrop"


def normalize_media_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    return normalized if normalized in MEDIA_VARIANT_LAYOUTS else "image_panel"


def _wrapped_media_caption_lines(text: str, max_chars_per_line: int) -> int:
    line_count = 0
    paragraphs = text.splitlines() or [text]
    wrap_width = max(1, int(max_chars_per_line))
    for paragraph in paragraphs:
        normalized = paragraph.expandtabs(4)
        if not normalized:
            line_count += 1
        else:
            wrapped = textwrap.wrap(
                normalized,
                width=wrap_width,
                break_long_words=True,
                break_on_hyphens=False,
                drop_whitespace=False,
                replace_whitespace=False,
            )
            line_count += max(1, len(wrapped))
        if line_count >= MEDIA_CAPTION_MAX_LINES:
            return MEDIA_CAPTION_MAX_LINES
    return max(1, min(line_count, MEDIA_CAPTION_MAX_LINES))


def _media_caption_height(node: NodeInstance, content_width: float) -> float:
    caption = str(node.properties.get("caption", "") or "")
    if not caption:
        return 0.0
    font_size = max(1.0, _safe_number(node.visual_style.get("font_size"), 12.0))
    line_height = max(1.0, math.ceil(font_size * MEDIA_CAPTION_LINE_HEIGHT_FACTOR))
    average_char_width = max(1.0, font_size * MEDIA_CAPTION_CHAR_WIDTH_FACTOR)
    max_chars_per_line = max(1, int(max(1.0, content_width) / average_char_width))
    line_count = _wrapped_media_caption_lines(caption, max_chars_per_line)
    return line_height * line_count


def _media_default_dimensions(
    node: NodeInstance,
    layout: _MediaPanelLayout,
    *,
    variant: str,
) -> tuple[float, float]:
    default_width = float(layout.default_width)
    default_height = float(layout.default_height)
    source_path = str(node.properties.get("source_path", "") or "")
    if variant == "pdf_panel":
        media_dimensions = local_pdf_page_dimensions(source_path, node.properties.get("page_number"))
    else:
        media_dimensions = local_image_dimensions(source_path)
    if media_dimensions is None:
        return default_width, default_height
    media_width, media_height = media_dimensions
    if media_width <= 0 or media_height <= 0:
        return default_width, default_height

    preview_width = max(1.0, default_width - layout.body_left_margin - layout.body_right_margin)
    preview_height = preview_width * (float(media_height) / float(media_width))
    caption_height = _media_caption_height(node, preview_width)
    caption_extra = (MEDIA_CAPTION_SPACING + caption_height) if caption_height > 0.0 else 0.0
    body_height = max(layout.min_body_height, preview_height + caption_extra)
    return (
        default_width,
        max(layout.min_height, layout.body_top + layout.body_bottom_margin + body_height),
    )


def _build_panel_surface_metrics(
    *,
    default_width: float,
    default_height: float,
    min_width: float,
    min_height: float,
    active_height: float,
    body_top: float,
    body_height: float,
    title_top: float,
    title_height: float,
    title_left_margin: float,
    title_right_margin: float,
    title_centered: bool,
    body_left_margin: float,
    body_right_margin: float,
    body_bottom_margin: float,
    show_header_background: bool,
    show_accent_bar: bool,
    use_host_chrome: bool,
) -> GraphNodeSurfaceMetrics:
    return GraphNodeSurfaceMetrics(
        default_width=default_width,
        default_height=default_height,
        min_width=min_width,
        min_height=min_height,
        collapsed_width=STANDARD_COLLAPSED_WIDTH,
        collapsed_height=STANDARD_COLLAPSED_HEIGHT,
        header_height=0.0,
        header_top_margin=0.0,
        body_top=body_top,
        body_height=body_height,
        port_top=active_height - body_bottom_margin,
        port_height=0.0,
        port_center_offset=0.0,
        port_side_margin=PASSIVE_PORT_SIDE_MARGIN,
        port_dot_radius=PASSIVE_PORT_DOT_RADIUS,
        resize_handle_size=PASSIVE_SURFACE_RESIZE_HANDLE_SIZE,
        title_top=title_top,
        title_height=title_height,
        title_left_margin=title_left_margin,
        title_right_margin=title_right_margin,
        title_centered=title_centered,
        body_left_margin=body_left_margin,
        body_right_margin=body_right_margin,
        body_bottom_margin=body_bottom_margin,
        show_header_background=show_header_background,
        show_accent_bar=show_accent_bar,
        use_host_chrome=use_host_chrome,
    )


def _passive_panel_surface_metrics(
    node: NodeInstance,
    layout: _PassivePanelLayout,
) -> GraphNodeSurfaceMetrics:
    _active_width, active_height = _resolved_dimensions(
        node,
        default_width=layout.default_width,
        default_height=layout.default_height,
    )
    body_height = max(layout.body_height, active_height - layout.body_top - layout.body_bottom_margin)
    return _build_panel_surface_metrics(
        default_width=layout.default_width,
        default_height=layout.default_height,
        min_width=layout.min_width,
        min_height=layout.min_height,
        active_height=active_height,
        body_top=layout.body_top,
        body_height=body_height,
        title_top=layout.title_top,
        title_height=layout.title_height,
        title_left_margin=layout.title_left_margin,
        title_right_margin=layout.title_right_margin,
        title_centered=layout.title_centered,
        body_left_margin=layout.body_left_margin,
        body_right_margin=layout.body_right_margin,
        body_bottom_margin=layout.body_bottom_margin,
        show_header_background=layout.show_header_background,
        show_accent_bar=layout.show_accent_bar,
        use_host_chrome=layout.use_host_chrome,
    )


def _planning_surface_metrics(node: NodeInstance, spec: NodeTypeSpec) -> GraphNodeSurfaceMetrics:
    layout = PLANNING_VARIANT_LAYOUTS[normalize_planning_variant(spec.surface_variant)]
    return _passive_panel_surface_metrics(node, layout)


def _annotation_surface_metrics(node: NodeInstance, spec: NodeTypeSpec) -> GraphNodeSurfaceMetrics:
    layout = ANNOTATION_VARIANT_LAYOUTS[normalize_annotation_variant(spec.surface_variant)]
    return _passive_panel_surface_metrics(node, layout)


def _comment_backdrop_surface_metrics(node: NodeInstance, spec: NodeTypeSpec) -> GraphNodeSurfaceMetrics:
    layout = COMMENT_BACKDROP_VARIANT_LAYOUTS[normalize_comment_backdrop_variant(spec.surface_variant)]
    _active_width, active_height = _resolved_dimensions(
        node,
        default_width=layout.default_width,
        default_height=layout.default_height,
    )
    body_height = max(0.0, active_height - layout.body_top - layout.body_bottom_margin)
    return _build_panel_surface_metrics(
        default_width=layout.default_width,
        default_height=layout.default_height,
        min_width=layout.min_width,
        min_height=layout.min_height,
        active_height=active_height,
        body_top=layout.body_top,
        body_height=body_height,
        title_top=layout.title_top,
        title_height=layout.title_height,
        title_left_margin=layout.title_left_margin,
        title_right_margin=layout.title_right_margin,
        title_centered=layout.title_centered,
        body_left_margin=layout.body_left_margin,
        body_right_margin=layout.body_right_margin,
        body_bottom_margin=layout.body_bottom_margin,
        show_header_background=layout.show_header_background,
        show_accent_bar=layout.show_accent_bar,
        use_host_chrome=layout.use_host_chrome,
    )


def _media_surface_metrics(node: NodeInstance, spec: NodeTypeSpec) -> GraphNodeSurfaceMetrics:
    variant = normalize_media_variant(spec.surface_variant)
    layout = MEDIA_VARIANT_LAYOUTS[variant]
    default_width, default_height = _media_default_dimensions(node, layout, variant=variant)
    _active_width, active_height = _resolved_dimensions(
        node,
        default_width=default_width,
        default_height=default_height,
    )
    body_height = max(layout.min_body_height, active_height - layout.body_top - layout.body_bottom_margin)
    return _build_panel_surface_metrics(
        default_width=default_width,
        default_height=default_height,
        min_width=layout.min_width,
        min_height=layout.min_height,
        active_height=active_height,
        body_top=layout.body_top,
        body_height=body_height,
        title_top=layout.title_top,
        title_height=layout.title_height,
        title_left_margin=layout.title_left_margin,
        title_right_margin=layout.title_right_margin,
        title_centered=layout.title_centered,
        body_left_margin=layout.body_left_margin,
        body_right_margin=layout.body_right_margin,
        body_bottom_margin=layout.body_bottom_margin,
        show_header_background=False,
        show_accent_bar=False,
        use_host_chrome=True,
    )
