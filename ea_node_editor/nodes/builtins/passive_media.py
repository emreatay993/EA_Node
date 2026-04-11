from __future__ import annotations

from ea_node_editor.nodes.builtins.passive_flow_ports import CARDINAL_PASSIVE_FLOW_PORTS
from ea_node_editor.nodes.decorators import node_type, prop_enum
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import PropertySpec

PASSIVE_MEDIA_CATEGORY = "Media"
PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID = "passive.media.image_panel"
PASSIVE_MEDIA_PDF_PANEL_TYPE_ID = "passive.media.pdf_panel"


class _PassiveMediaNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id=PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID,
    display_name="Image Panel",
    category_path=(PASSIVE_MEDIA_CATEGORY,),
    icon="image",
    description="Passive local-image panel with caption and fit controls.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        PropertySpec("source_path", "path", "", "Image Source", inline_editor="path"),
        PropertySpec(
            "caption",
            "str",
            "",
            "Caption",
            inline_editor="textarea",
            inspector_editor="textarea",
        ),
        prop_enum(
            "fit_mode",
            "contain",
            "Fit Mode",
            values=("contain", "cover", "original"),
        ),
        PropertySpec("crop_x", "float", 0.0, "Crop X", inspector_visible=False),
        PropertySpec("crop_y", "float", 0.0, "Crop Y", inspector_visible=False),
        PropertySpec("crop_w", "float", 1.0, "Crop Width", inspector_visible=False),
        PropertySpec("crop_h", "float", 1.0, "Crop Height", inspector_visible=False),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="media",
    surface_variant="image_panel",
    render_quality={
        "weight_class": "heavy",
        "max_performance_strategy": "proxy_surface",
        "supported_quality_tiers": ["full", "proxy"],
    },
)
class PassiveMediaImagePanelNodePlugin(_PassiveMediaNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
    display_name="PDF Panel",
    category_path=(PASSIVE_MEDIA_CATEGORY,),
    icon="file",
    description="Passive local-PDF panel with single-page preview and caption.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        PropertySpec("source_path", "path", "", "PDF Source", inline_editor="path"),
        PropertySpec("page_number", "int", 1, "Page Number"),
        PropertySpec(
            "caption",
            "str",
            "",
            "Caption",
            inline_editor="textarea",
            inspector_editor="textarea",
        ),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="media",
    surface_variant="pdf_panel",
    render_quality={
        "weight_class": "heavy",
        "max_performance_strategy": "proxy_surface",
        "supported_quality_tiers": ["full", "proxy"],
    },
)
class PassiveMediaPdfPanelNodePlugin(_PassiveMediaNodePlugin):
    pass


PASSIVE_MEDIA_NODE_PLUGINS = (
    PassiveMediaImagePanelNodePlugin,
    PassiveMediaPdfPanelNodePlugin,
)


__all__ = [
    "PASSIVE_MEDIA_CATEGORY",
    "PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID",
    "PASSIVE_MEDIA_PDF_PANEL_TYPE_ID",
    "PASSIVE_MEDIA_NODE_PLUGINS",
    "PassiveMediaImagePanelNodePlugin",
    "PassiveMediaPdfPanelNodePlugin",
]
