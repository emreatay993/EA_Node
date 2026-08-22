from __future__ import annotations

from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type
from ea_node_editor.nodes.builtins.passive_flow_ports import CARDINAL_PASSIVE_FLOW_PORTS
from ea_node_editor.nodes.decorators import plugin_descriptor, prop_enum
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.file_dialog_filters import (
    IMAGE_FILES_FILTER,
    MAIL_FILES_FILTER,
    PDF_FILES_FILTER,
    VIDEO_FILES_FILTER,
)
from ea_node_editor.nodes.node_specs import PropertySpec

PASSIVE_MEDIA_CATEGORY = "Media"
PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID = "passive.media.image_panel"
PASSIVE_MEDIA_PDF_PANEL_TYPE_ID = "passive.media.pdf_panel"
PASSIVE_MEDIA_VIDEO_PANEL_TYPE_ID = "passive.media.video_panel"
PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID = "passive.media.mail_panel"


class _PassiveMediaNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@builtin_node_type(
    type_id=PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID,
    display_name="Image Panel",
    category_path=(PASSIVE_MEDIA_CATEGORY,),
    description="Passive local-image panel with fit controls.",
    keywords=("image", "media", "preview"),
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        PropertySpec(
            "source_path",
            "path",
            "",
            "Image Source",
            inline_editor="path",
            file_filter=IMAGE_FILES_FILTER,
        ),
        prop_enum(
            "fit_mode",
            "contain",
            "Fit Mode",
            values=("contain", "cover", "original"),
        ),
        PropertySpec(
            "animation_playback_mode",
            "enum",
            "auto",
            "Animation Playback",
            enum_values=("auto", "play", "pause"),
            inspector_visible=False,
        ),
        PropertySpec("lock_aspect_ratio", "bool", False, "Lock Aspect Ratio", inspector_visible=False),
        PropertySpec("show_title", "bool", True, "Show Title", inspector_visible=False),
        PropertySpec("show_frame", "bool", True, "Show Frame", inspector_visible=False),
        PropertySpec("crop_x", "float", 0.0, "Crop X", inspector_visible=False),
        PropertySpec("crop_y", "float", 0.0, "Crop Y", inspector_visible=False),
        PropertySpec("crop_w", "float", 1.0, "Crop Width", inspector_visible=False),
        PropertySpec("crop_h", "float", 1.0, "Crop Height", inspector_visible=False),
        PropertySpec("rotation_degrees", "int", 0, "Rotation", inspector_visible=False),
        PropertySpec("mirror_horizontal", "bool", False, "Mirror Horizontal", inspector_visible=False),
        PropertySpec("mirror_vertical", "bool", False, "Mirror Vertical", inspector_visible=False),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="media",
    surface_variant="image_panel",
    render_quality={
        "supported_quality_tiers": ["full", "proxy"],
    },
)
class PassiveMediaImagePanelNodePlugin(_PassiveMediaNodePlugin):
    pass


@builtin_node_type(
    type_id=PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
    display_name="PDF Panel",
    category_path=(PASSIVE_MEDIA_CATEGORY,),
    description="Passive local-PDF panel with single-page preview.",
    keywords=("pdf", "document", "preview"),
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        PropertySpec(
            "source_path",
            "path",
            "",
            "PDF Source",
            inline_editor="path",
            file_filter=PDF_FILES_FILTER,
        ),
        PropertySpec("page_number", "int", 1, "Page Number"),
        PropertySpec("show_title", "bool", True, "Show Title", inspector_visible=False),
        PropertySpec("show_frame", "bool", True, "Show Frame", inspector_visible=False),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="media",
    surface_variant="pdf_panel",
    render_quality={
        "supported_quality_tiers": ["full", "proxy"],
    },
)
class PassiveMediaPdfPanelNodePlugin(_PassiveMediaNodePlugin):
    pass


@builtin_node_type(
    type_id=PASSIVE_MEDIA_VIDEO_PANEL_TYPE_ID,
    display_name="Video Panel",
    category_path=(PASSIVE_MEDIA_CATEGORY,),
    description="Passive local-video panel with playback, fit, and fullscreen controls.",
    keywords=("video", "media", "playback"),
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        PropertySpec(
            "source_path",
            "path",
            "",
            "Video Source",
            inline_editor="path",
            file_filter=VIDEO_FILES_FILTER,
        ),
        prop_enum(
            "fit_mode",
            "contain",
            "Fit Mode",
            values=("contain", "cover"),
        ),
        PropertySpec("show_title", "bool", True, "Show Title", inspector_visible=False),
        PropertySpec("show_frame", "bool", True, "Show Frame", inspector_visible=False),
        PropertySpec("auto_play", "bool", False, "Auto Play"),
        PropertySpec("loop", "bool", False, "Loop"),
        PropertySpec("muted", "bool", False, "Muted"),
        PropertySpec("volume", "float", 1.0, "Volume"),
        PropertySpec("playback_rate", "float", 1.0, "Playback Rate"),
        PropertySpec("position_ms", "int", 0, "Position", inspector_visible=False),
        PropertySpec("timeline_bookmarks", "json", [], "Timeline Bookmarks"),
        PropertySpec("clip_enabled", "bool", False, "Clip Range Enabled"),
        PropertySpec("clip_start_ms", "int", 0, "Clip Start"),
        PropertySpec("clip_end_ms", "int", 0, "Clip End"),
        PropertySpec(
            "unfocused_behavior",
            "enum",
            "pause_keep_loaded",
            "When Unfocused",
            enum_values=("pause_keep_loaded", "keep_playing"),
            inspector_visible=False,
        ),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="media",
    surface_variant="video_panel",
    render_quality={
        "supported_quality_tiers": ["full", "proxy"],
    },
)
class PassiveMediaVideoPanelNodePlugin(_PassiveMediaNodePlugin):
    pass


@builtin_node_type(
    type_id=PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID,
    display_name="Mail Panel",
    category_path=(PASSIVE_MEDIA_CATEGORY,),
    description="Passive local-mail panel with rich HTML preview.",
    keywords=("mail", "email", "preview"),
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        PropertySpec(
            "source_path",
            "path",
            "",
            "Mail Source",
            inline_editor="path",
            file_filter=MAIL_FILES_FILTER,
        ),
        PropertySpec("show_title", "bool", True, "Show Title", inspector_visible=False),
        PropertySpec("show_frame", "bool", True, "Show Frame", inspector_visible=False),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="media",
    surface_variant="mail_panel",
    render_quality={
        "supported_quality_tiers": ["full", "proxy"],
    },
)
class PassiveMediaMailPanelNodePlugin(_PassiveMediaNodePlugin):
    pass


PASSIVE_MEDIA_NODE_PLUGINS = (
    PassiveMediaImagePanelNodePlugin,
    PassiveMediaPdfPanelNodePlugin,
    PassiveMediaVideoPanelNodePlugin,
    PassiveMediaMailPanelNodePlugin,
)
PASSIVE_MEDIA_NODE_DESCRIPTORS = tuple(
    plugin_descriptor(plugin)
    for plugin in PASSIVE_MEDIA_NODE_PLUGINS
)


__all__ = [
    "PASSIVE_MEDIA_CATEGORY",
    "PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID",
    "PASSIVE_MEDIA_MAIL_PANEL_TYPE_ID",
    "PASSIVE_MEDIA_PDF_PANEL_TYPE_ID",
    "PASSIVE_MEDIA_VIDEO_PANEL_TYPE_ID",
    "PASSIVE_MEDIA_NODE_DESCRIPTORS",
    "PASSIVE_MEDIA_NODE_PLUGINS",
    "PassiveMediaImagePanelNodePlugin",
    "PassiveMediaMailPanelNodePlugin",
    "PassiveMediaPdfPanelNodePlugin",
    "PassiveMediaVideoPanelNodePlugin",
]
