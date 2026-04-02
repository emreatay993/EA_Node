from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec

NodeSizeResolver = Callable[
    [NodeInstance, NodeTypeSpec, Mapping[str, NodeInstance] | None],
    tuple[float, float],
]
PdfPageNumberResolver = Callable[[str, Any], int | None]

_DEFAULT_FALLBACK_NODE_WIDTH = 240.0
_DEFAULT_FALLBACK_NODE_HEIGHT = 160.0
_DEFAULT_FALLBACK_PAGE_NUMBER = 1


def _fallback_node_size(
    node: NodeInstance,
    _spec: NodeTypeSpec,
    _workspace_nodes: Mapping[str, NodeInstance] | None = None,
    *,
    show_port_labels: bool = True,
) -> tuple[float, float]:
    del show_port_labels
    width = float(node.custom_width) if node.custom_width is not None else _DEFAULT_FALLBACK_NODE_WIDTH
    height = float(node.custom_height) if node.custom_height is not None else _DEFAULT_FALLBACK_NODE_HEIGHT
    return max(1.0, width), max(1.0, height)


def _fallback_clamp_pdf_page_number(source: str, page_number: Any) -> int | None:
    if not str(source or "").strip():
        return None
    if isinstance(page_number, bool):
        return _DEFAULT_FALLBACK_PAGE_NUMBER
    try:
        normalized = int(page_number)
    except (TypeError, ValueError):
        return None
    return max(_DEFAULT_FALLBACK_PAGE_NUMBER, normalized)


@dataclass(slots=True)
class GraphBoundaryAdapters:
    node_size_resolver: NodeSizeResolver
    clamp_pdf_page_number_resolver: PdfPageNumberResolver

    def node_size(
        self,
        node: NodeInstance,
        spec: NodeTypeSpec,
        workspace_nodes: Mapping[str, NodeInstance] | None = None,
        *,
        show_port_labels: bool = True,
    ) -> tuple[float, float]:
        return self.node_size_resolver(
            node,
            spec,
            workspace_nodes,
            show_port_labels=show_port_labels,
        )

    def clamp_pdf_page_number(self, source: str, page_number: Any) -> int | None:
        return self.clamp_pdf_page_number_resolver(source, page_number)


def build_graph_boundary_adapters(
    *,
    node_size_resolver: NodeSizeResolver | None = None,
    clamp_pdf_page_number_resolver: PdfPageNumberResolver | None = None,
) -> GraphBoundaryAdapters:
    return GraphBoundaryAdapters(
        node_size_resolver=node_size_resolver or _fallback_node_size,
        clamp_pdf_page_number_resolver=clamp_pdf_page_number_resolver or _fallback_clamp_pdf_page_number,
    )


def fallback_graph_boundary_adapters() -> GraphBoundaryAdapters:
    return build_graph_boundary_adapters()


__all__ = [
    "GraphBoundaryAdapters",
    "NodeSizeResolver",
    "PdfPageNumberResolver",
    "build_graph_boundary_adapters",
    "fallback_graph_boundary_adapters",
]
