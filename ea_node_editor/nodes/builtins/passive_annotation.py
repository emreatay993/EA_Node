from __future__ import annotations

from ea_node_editor.nodes.decorators import node_type, prop_str
from ea_node_editor.nodes.types import ExecutionContext, NodeResult

PASSIVE_ANNOTATION_CATEGORY = "Annotation"

PASSIVE_ANNOTATION_STICKY_NOTE_TYPE_ID = "passive.annotation.sticky_note"
PASSIVE_ANNOTATION_CALLOUT_TYPE_ID = "passive.annotation.callout"
PASSIVE_ANNOTATION_SECTION_HEADER_TYPE_ID = "passive.annotation.section_header"


class _PassiveAnnotationNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id=PASSIVE_ANNOTATION_STICKY_NOTE_TYPE_ID,
    display_name="Sticky Note",
    category=PASSIVE_ANNOTATION_CATEGORY,
    icon="sticky_note_2",
    description="Annotation sticky note for contextual comments.",
    ports=(),
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
    category=PASSIVE_ANNOTATION_CATEGORY,
    icon="campaign",
    description="Annotation callout for emphasized contextual notes.",
    ports=(),
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
    category=PASSIVE_ANNOTATION_CATEGORY,
    icon="title",
    description="Annotation section header with optional subtitle copy.",
    ports=(),
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


PASSIVE_ANNOTATION_NODE_PLUGINS = (
    PassiveAnnotationStickyNoteNodePlugin,
    PassiveAnnotationCalloutNodePlugin,
    PassiveAnnotationSectionHeaderNodePlugin,
)


__all__ = [
    "PASSIVE_ANNOTATION_CALLOUT_TYPE_ID",
    "PASSIVE_ANNOTATION_CATEGORY",
    "PASSIVE_ANNOTATION_NODE_PLUGINS",
    "PASSIVE_ANNOTATION_SECTION_HEADER_TYPE_ID",
    "PASSIVE_ANNOTATION_STICKY_NOTE_TYPE_ID",
    "PassiveAnnotationCalloutNodePlugin",
    "PassiveAnnotationSectionHeaderNodePlugin",
    "PassiveAnnotationStickyNoteNodePlugin",
]
