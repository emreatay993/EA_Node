from __future__ import annotations

from ea_node_editor.nodes.decorators import node_type, prop_enum
from ea_node_editor.nodes.types import ExecutionContext, NodeResult, PropertySpec

PASSIVE_MEDIA_CATEGORY = "Media"
PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID = "passive.media.image_panel"
PASSIVE_MEDIA_PDF_PANEL_TYPE_ID = "passive.media.pdf_panel"


class _PassiveMediaNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id=PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID,
    display_name="Image Panel",
    category=PASSIVE_MEDIA_CATEGORY,
    icon="image",
    description="Passive local-image panel with caption and fit controls.",
    ports=(),
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
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="media",
    surface_variant="image_panel",
)
class PassiveMediaImagePanelNodePlugin(_PassiveMediaNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
    display_name="PDF Panel",
    category=PASSIVE_MEDIA_CATEGORY,
    icon="file",
    description="Passive local-PDF panel with single-page preview and caption.",
    ports=(),
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
