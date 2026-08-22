from __future__ import annotations

from ea_node_editor.graph.boundary_adapters import GraphBoundaryAdapters
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.registry import NodeRegistry


PDF_PANEL_PROPERTY_KEYS = frozenset({"page_number", "source_path"})


def normalize_pdf_panel_pages(
    *,
    model: GraphModel,
    workspace_id: str,
    registry: NodeRegistry,
    boundary_adapters: GraphBoundaryAdapters,
) -> bool:
    workspace = model.project.workspaces.get(str(workspace_id).strip())
    if workspace is None:
        return False
    changed = False
    for node_id in list(workspace.nodes):
        changed = normalize_pdf_panel_page_number(
            model=model,
            workspace_id=workspace.workspace_id,
            registry=registry,
            boundary_adapters=boundary_adapters,
            node_id=node_id,
        ) or changed
    return changed


def normalize_pdf_panel_page_number(
    *,
    model: GraphModel,
    workspace_id: str,
    registry: NodeRegistry,
    boundary_adapters: GraphBoundaryAdapters,
    node_id: str,
) -> bool:
    workspace = model.project.workspaces.get(str(workspace_id).strip())
    if workspace is None:
        return False
    node = workspace.nodes.get(str(node_id).strip())
    if node is None:
        return False
    spec = registry.spec_or_none(node.type_id)
    if spec is None:
        return False
    if str(spec.surface_family or "").strip() != "media":
        return False
    if str(spec.surface_variant or "").strip() != "pdf_panel":
        return False
    resolved_page_number = boundary_adapters.clamp_pdf_page_number(
        str(node.properties.get("source_path", "") or ""),
        node.properties.get("page_number"),
    )
    if resolved_page_number is None:
        return False
    if node.properties.get("page_number") == resolved_page_number:
        return False
    model._set_node_property_record(workspace.workspace_id, node.node_id, "page_number", resolved_page_number)
    return True


__all__ = ["PDF_PANEL_PROPERTY_KEYS", "normalize_pdf_panel_page_number", "normalize_pdf_panel_pages"]
