from __future__ import annotations

"""Media-panel payload contributions.

Currently owns the PDF-panel page-number clamp applied during property
normalization. New media-panel payload fields (image/video/pdf) belong here.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ea_node_editor.graph.boundary_adapters import GraphBoundaryAdapters
    from ea_node_editor.nodes.node_specs import NodeTypeSpec


def normalize_pdf_panel_properties(
    properties: dict[str, Any],
    *,
    node: Any,
    spec: "NodeTypeSpec",
    boundary_adapters: "GraphBoundaryAdapters",
) -> dict[str, Any]:
    del node, spec
    resolved_page_number = boundary_adapters.clamp_pdf_page_number(
        str(properties.get("source_path", "") or ""),
        properties.get("page_number"),
    )
    if resolved_page_number is not None:
        properties["page_number"] = resolved_page_number
    return properties
