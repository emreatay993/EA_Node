from __future__ import annotations

from ea_node_editor.nodes.builtins.passive_flow_ports import CARDINAL_PASSIVE_FLOW_PORTS
from ea_node_editor.nodes.decorators import node_type, plugin_descriptor, prop_str
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult

PASSIVE_ANNOTATION_CATEGORY = "Annotation"

PASSIVE_ANNOTATION_STICKY_NOTE_TYPE_ID = "passive.annotation.sticky_note"
PASSIVE_ANNOTATION_CALLOUT_TYPE_ID = "passive.annotation.callout"
PASSIVE_ANNOTATION_SECTION_HEADER_TYPE_ID = "passive.annotation.section_header"
PASSIVE_ANNOTATION_COMMENT_BACKDROP_TYPE_ID = "passive.annotation.comment_backdrop"
PASSIVE_ANNOTATION_COMMENT_BACKDROP_SURFACE_FAMILY = "comment_backdrop"


def _enable_comment_backdrop_surface_family() -> None:
    supported_families = set(getattr(NodeRegistry, "_SUPPORTED_SURFACE_FAMILIES", ()))
    supported_families.add(PASSIVE_ANNOTATION_COMMENT_BACKDROP_SURFACE_FAMILY)
    NodeRegistry._SUPPORTED_SURFACE_FAMILIES = supported_families


_enable_comment_backdrop_surface_family()


class _PassiveAnnotationNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id=PASSIVE_ANNOTATION_STICKY_NOTE_TYPE_ID,
    display_name="Sticky Note",
    category_path=(PASSIVE_ANNOTATION_CATEGORY,),
    icon="sticky_note_2",
    description="Annotation sticky note for contextual comments.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        prop_str("title", "Sticky Note", "Title"),
        prop_str("body", "", "Body", inspector_editor="textarea"),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="annotation",
    surface_variant="sticky_note",
)
class PassiveAnnotationStickyNoteNodePlugin(_PassiveAnnotationNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_ANNOTATION_CALLOUT_TYPE_ID,
    display_name="Callout",
    category_path=(PASSIVE_ANNOTATION_CATEGORY,),
    icon="campaign",
    description="Annotation callout for emphasized contextual notes.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        prop_str("title", "Callout", "Title"),
        prop_str("body", "", "Body", inspector_editor="textarea"),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="annotation",
    surface_variant="callout",
)
class PassiveAnnotationCalloutNodePlugin(_PassiveAnnotationNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_ANNOTATION_SECTION_HEADER_TYPE_ID,
    display_name="Section Header",
    category_path=(PASSIVE_ANNOTATION_CATEGORY,),
    icon="title",
    description="Annotation section header with optional subtitle copy.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=(
        prop_str("title", "Section Header", "Title"),
        prop_str("subtitle", "", "Subtitle"),
    ),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="annotation",
    surface_variant="section_header",
)
class PassiveAnnotationSectionHeaderNodePlugin(_PassiveAnnotationNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_ANNOTATION_COMMENT_BACKDROP_TYPE_ID,
    display_name="Comment Backdrop",
    category_path=(PASSIVE_ANNOTATION_CATEGORY,),
    icon="comment",
    description="Backdrop annotation for grouping related nodes without flow ports.",
    ports=(),
    properties=(
        prop_str("title", "Comment Backdrop", "Title"),
        prop_str("body", "", "Body", inspector_editor="textarea"),
    ),
    collapsible=True,
    runtime_behavior="passive",
    surface_family=PASSIVE_ANNOTATION_COMMENT_BACKDROP_SURFACE_FAMILY,
    surface_variant="comment_backdrop",
)
class PassiveAnnotationCommentBackdropNodePlugin(_PassiveAnnotationNodePlugin):
    pass


PASSIVE_ANNOTATION_NODE_PLUGINS = (
    PassiveAnnotationStickyNoteNodePlugin,
    PassiveAnnotationCalloutNodePlugin,
    PassiveAnnotationSectionHeaderNodePlugin,
    PassiveAnnotationCommentBackdropNodePlugin,
)
PASSIVE_ANNOTATION_NODE_DESCRIPTORS = tuple(
    plugin_descriptor(plugin)
    for plugin in PASSIVE_ANNOTATION_NODE_PLUGINS
)


__all__ = [
    "PASSIVE_ANNOTATION_CALLOUT_TYPE_ID",
    "PASSIVE_ANNOTATION_CATEGORY",
    "PASSIVE_ANNOTATION_COMMENT_BACKDROP_SURFACE_FAMILY",
    "PASSIVE_ANNOTATION_COMMENT_BACKDROP_TYPE_ID",
    "PASSIVE_ANNOTATION_NODE_DESCRIPTORS",
    "PASSIVE_ANNOTATION_NODE_PLUGINS",
    "PASSIVE_ANNOTATION_SECTION_HEADER_TYPE_ID",
    "PASSIVE_ANNOTATION_STICKY_NOTE_TYPE_ID",
    "PassiveAnnotationCalloutNodePlugin",
    "PassiveAnnotationCommentBackdropNodePlugin",
    "PassiveAnnotationSectionHeaderNodePlugin",
    "PassiveAnnotationStickyNoteNodePlugin",
]
