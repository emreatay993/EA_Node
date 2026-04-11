from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from ea_node_editor.graph.hierarchy import subtree_node_ids
from ea_node_editor.graph.model import GraphModel, NodeInstance, WorkspaceData
from ea_node_editor.graph.normalization import GraphInvariantKernel
from ea_node_editor.graph.subnode_contract import is_subnode_shell_type
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec

if TYPE_CHECKING:
    from ea_node_editor.graph.mutation_service import WorkspaceMutationService


_FRAGMENT_EXTERNAL_PARENT_PREFIX = "__ea_external_parent__:"


@dataclass(slots=True, frozen=True)
class GraphFragmentBounds:
    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        return self.x + (self.width * 0.5)

    @property
    def center_y(self) -> float:
        return self.y + (self.height * 0.5)


def encode_fragment_external_parent_id(parent_node_id: object) -> str | None:
    normalized_parent_id = str(parent_node_id).strip()
    if not normalized_parent_id:
        return None
    return f"{_FRAGMENT_EXTERNAL_PARENT_PREFIX}{normalized_parent_id}"


def expand_subtree_fragment_node_ids(
    *,
    workspace: WorkspaceData,
    selected_node_ids: Sequence[object],
) -> list[str]:
    normalized_selected: list[str] = []
    seen_selected: set[str] = set()
    for value in selected_node_ids:
        node_id = str(value).strip()
        if not node_id or node_id in seen_selected:
            continue
        if node_id not in workspace.nodes:
            continue
        seen_selected.add(node_id)
        normalized_selected.append(node_id)

    expanded: list[str] = []
    seen_expanded: set[str] = set()
    for node_id in normalized_selected:
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        fragment_ids = [node_id]
        if is_subnode_shell_type(node.type_id):
            fragment_ids = subtree_node_ids(workspace, [node_id])
        for fragment_id in fragment_ids:
            if fragment_id in seen_expanded or fragment_id not in workspace.nodes:
                continue
            seen_expanded.add(fragment_id)
            expanded.append(fragment_id)
    return expanded


def expand_comment_backdrop_fragment_node_ids(
    *,
    workspace: WorkspaceData,
    selected_node_ids: Sequence[object],
    backdrop_payloads: Sequence[Mapping[str, Any]],
) -> list[str]:
    normalized_selected: list[str] = []
    selected_lookup: set[str] = set()
    backdrop_payload_by_id: dict[str, Mapping[str, Any]] = {}

    for payload in backdrop_payloads:
        node_id = str(payload.get("node_id", "")).strip()
        if not node_id:
            continue
        backdrop_payload_by_id[node_id] = payload

    for value in selected_node_ids:
        node_id = str(value).strip()
        if not node_id or node_id in selected_lookup or node_id not in workspace.nodes:
            continue
        selected_lookup.add(node_id)
        normalized_selected.append(node_id)

        payload = backdrop_payload_by_id.get(node_id)
        if payload is None or not bool(payload.get("collapsed", False)):
            continue
        for key in ("contained_backdrop_ids", "contained_node_ids"):
            raw_ids = payload.get(key)
            if not isinstance(raw_ids, Sequence) or isinstance(raw_ids, (str, bytes)):
                continue
            for raw_id in raw_ids:
                descendant_id = str(raw_id).strip()
                if not descendant_id or descendant_id in selected_lookup or descendant_id not in workspace.nodes:
                    continue
                selected_lookup.add(descendant_id)
                normalized_selected.append(descendant_id)

    return expand_subtree_fragment_node_ids(
        workspace=workspace,
        selected_node_ids=normalized_selected,
    )


def build_subtree_fragment_payload_data(
    *,
    workspace: WorkspaceData,
    selected_node_ids: Sequence[object],
) -> dict[str, list[dict[str, Any]]] | None:
    fragment_node_ids = expand_subtree_fragment_node_ids(
        workspace=workspace,
        selected_node_ids=selected_node_ids,
    )
    if not fragment_node_ids:
        return None

    selected_node_set = set(fragment_node_ids)
    nodes_payload: list[dict[str, Any]] = []
    for node_id in fragment_node_ids:
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        nodes_payload.append(
            {
                "ref_id": node.node_id,
                "type_id": node.type_id,
                "title": node.title,
                "x": float(node.x),
                "y": float(node.y),
                "collapsed": bool(node.collapsed),
                "properties": copy.deepcopy(node.properties),
                "locked_ports": copy.deepcopy(node.locked_ports),
                "exposed_ports": dict(node.exposed_ports),
                "visual_style": copy.deepcopy(node.visual_style),
                "parent_node_id": node.parent_node_id,
                "custom_width": float(node.custom_width) if node.custom_width is not None else None,
                "custom_height": float(node.custom_height) if node.custom_height is not None else None,
            }
        )
    if not nodes_payload:
        return None

    edges_payload: list[dict[str, Any]] = []
    workspace_edges = sorted(
        workspace.edges.values(),
        key=lambda edge: edge.edge_id,
    )
    for edge in workspace_edges:
        if edge.source_node_id not in selected_node_set or edge.target_node_id not in selected_node_set:
            continue
        edges_payload.append(
            {
                "source_ref_id": edge.source_node_id,
                "source_port_key": edge.source_port_key,
                "target_ref_id": edge.target_node_id,
                "target_port_key": edge.target_port_key,
                "label": str(edge.label),
                "visual_style": copy.deepcopy(edge.visual_style),
            }
        )
    return {
        "nodes": nodes_payload,
        "edges": edges_payload,
    }


def fragment_node_from_payload(node_payload: Mapping[str, Any]) -> NodeInstance:
    return GraphInvariantKernel.fragment_node_from_payload(node_payload)


def graph_fragment_bounds(
    *,
    nodes_payload: Sequence[Mapping[str, Any]],
    registry: NodeRegistry,
    size_resolver: Callable[[NodeInstance, NodeTypeSpec, Mapping[str, NodeInstance]], tuple[float, float]],
) -> GraphFragmentBounds | None:
    fragment_nodes: dict[str, NodeInstance] = {}
    node_specs: dict[str, NodeTypeSpec] = {}
    for node_payload in nodes_payload:
        ref_id = str(node_payload.get("ref_id", "")).strip()
        type_id = str(node_payload.get("type_id", "")).strip()
        if not ref_id or not type_id:
            return None
        try:
            node_specs[ref_id] = registry.get_spec(type_id)
        except KeyError:
            return None
        fragment_nodes[ref_id] = fragment_node_from_payload(node_payload)

    min_x: float | None = None
    min_y: float | None = None
    max_x: float | None = None
    max_y: float | None = None
    for node_id, node in fragment_nodes.items():
        spec = node_specs[node_id]
        width, height = size_resolver(node, spec, fragment_nodes)
        node_left = float(node.x)
        node_top = float(node.y)
        node_right = node_left + float(width)
        node_bottom = node_top + float(height)
        min_x = node_left if min_x is None else min(min_x, node_left)
        min_y = node_top if min_y is None else min(min_y, node_top)
        max_x = node_right if max_x is None else max(max_x, node_right)
        max_y = node_bottom if max_y is None else max(max_y, node_bottom)

    if min_x is None or min_y is None or max_x is None or max_y is None:
        return None
    return GraphFragmentBounds(
        x=min_x,
        y=min_y,
        width=max(0.0, max_x - min_x),
        height=max(0.0, max_y - min_y),
    )


def graph_fragment_payload_is_valid(
    *,
    fragment_payload: Mapping[str, Any],
    registry: NodeRegistry,
) -> bool:
    return GraphInvariantKernel.graph_fragment_payload_is_valid(
        fragment_payload=fragment_payload,
        registry=registry,
    )


def insert_graph_fragment(
    *,
    model: GraphModel,
    workspace_id: str,
    fragment_payload: dict[str, Any],
    delta_x: float,
    delta_y: float,
) -> list[str]:
    workspace = model.project.workspaces.get(str(workspace_id).strip())
    if workspace is None:
        return []
    return _insert_graph_fragment_operation(
        mutations=model.mutation_service(workspace.workspace_id),
        fragment_payload=fragment_payload,
        delta_x=delta_x,
        delta_y=delta_y,
    )


def _insert_graph_fragment_operation(
    *,
    mutations: "WorkspaceMutationService",
    fragment_payload: dict[str, Any],
    delta_x: float,
    delta_y: float,
) -> list[str]:
    workspace = mutations.workspace
    nodes_payload = fragment_payload.get("nodes")
    edges_payload = fragment_payload.get("edges")
    if not isinstance(nodes_payload, list) or not isinstance(edges_payload, list):
        return []

    node_id_map: dict[str, str] = {}
    inserted_node_ids: list[str] = []

    for node_payload in nodes_payload:
        if not isinstance(node_payload, dict):
            continue
        source_node_id = str(node_payload.get("ref_id", "")).strip()
        type_id = str(node_payload.get("type_id", "")).strip()
        if not source_node_id or not type_id:
            continue
        created = mutations._add_node_record(
            type_id=type_id,
            title=str(node_payload.get("title", "")),
            x=float(node_payload.get("x", 0.0)) + float(delta_x),
            y=float(node_payload.get("y", 0.0)) + float(delta_y),
            properties=dict(node_payload.get("properties", {})),
            exposed_ports=dict(node_payload.get("exposed_ports", {})),
            locked_ports=dict(node_payload.get("locked_ports", {})),
            visual_style=copy.deepcopy(node_payload.get("visual_style", {})),
        )
        mutations._set_node_fragment_state_record(
            created.node_id,
            collapsed=bool(node_payload.get("collapsed", False)),
            custom_width=float(node_payload["custom_width"]) if node_payload.get("custom_width") is not None else None,
            custom_height=(
                float(node_payload["custom_height"]) if node_payload.get("custom_height") is not None else None
            ),
        )
        node_id_map[source_node_id] = created.node_id
        inserted_node_ids.append(created.node_id)

    if not inserted_node_ids:
        return []

    for node_payload in nodes_payload:
        if not isinstance(node_payload, dict):
            continue
        source_node_id = str(node_payload.get("ref_id", "")).strip()
        inserted_node_id = node_id_map.get(source_node_id)
        if not inserted_node_id:
            continue
        mutations._set_node_parent_record(
            inserted_node_id,
            _remap_fragment_parent_id(
                source_parent_id=node_payload.get("parent_node_id"),
                node_id_map=node_id_map,
                workspace=workspace,
            ),
        )

    for edge_payload in edges_payload:
        if not isinstance(edge_payload, dict):
            continue
        source_ref_id = str(edge_payload.get("source_ref_id", "")).strip()
        target_ref_id = str(edge_payload.get("target_ref_id", "")).strip()
        source_port_key = str(edge_payload.get("source_port_key", "")).strip()
        target_port_key = str(edge_payload.get("target_port_key", "")).strip()
        if not source_ref_id or not target_ref_id or not source_port_key or not target_port_key:
            continue
        source_node_id = node_id_map.get(source_ref_id)
        target_node_id = node_id_map.get(target_ref_id)
        if not source_node_id or not target_node_id:
            continue
        source_port_key = _remap_fragment_edge_port_key(
            workspace=workspace,
            node_id_map=node_id_map,
            endpoint_node_id=source_node_id,
            port_key=source_port_key,
        )
        target_port_key = _remap_fragment_edge_port_key(
            workspace=workspace,
            node_id_map=node_id_map,
            endpoint_node_id=target_node_id,
            port_key=target_port_key,
        )
        try:
            mutations._add_edge_record(
                source_node_id=source_node_id,
                source_port_key=source_port_key,
                target_node_id=target_node_id,
                target_port_key=target_port_key,
                label=str(edge_payload.get("label", "")),
                visual_style=copy.deepcopy(edge_payload.get("visual_style", {})),
            )
        except ValueError:
            continue
    return inserted_node_ids


def _remap_fragment_parent_id(
    *,
    source_parent_id: object,
    node_id_map: dict[str, str],
    workspace: WorkspaceData,
) -> str | None:
    if source_parent_id is None:
        return None
    normalized_parent_id = str(source_parent_id).strip()
    if not normalized_parent_id:
        return None
    external_parent_id = _decode_fragment_external_parent_id(normalized_parent_id)
    if external_parent_id is not None:
        if external_parent_id in workspace.nodes:
            return external_parent_id
        return None
    if normalized_parent_id in node_id_map:
        return node_id_map[normalized_parent_id]
    if normalized_parent_id in workspace.nodes:
        return normalized_parent_id
    return None


def _decode_fragment_external_parent_id(encoded_parent_id: str) -> str | None:
    if not encoded_parent_id.startswith(_FRAGMENT_EXTERNAL_PARENT_PREFIX):
        return None
    normalized_parent_id = encoded_parent_id[len(_FRAGMENT_EXTERNAL_PARENT_PREFIX) :].strip()
    return normalized_parent_id or None


def _remap_fragment_edge_port_key(
    *,
    workspace: WorkspaceData,
    node_id_map: dict[str, str],
    endpoint_node_id: str,
    port_key: str,
) -> str:
    endpoint_node = workspace.nodes.get(endpoint_node_id)
    if endpoint_node is None:
        return port_key
    # Subnode shell edge port keys are child pin node ids; remap those ids with the fragment map.
    if not is_subnode_shell_type(endpoint_node.type_id):
        return port_key
    return node_id_map.get(port_key, port_key)


__all__ = [
    "GraphFragmentBounds",
    "build_subtree_fragment_payload_data",
    "encode_fragment_external_parent_id",
    "expand_comment_backdrop_fragment_node_ids",
    "expand_subtree_fragment_node_ids",
    "fragment_node_from_payload",
    "graph_fragment_bounds",
    "graph_fragment_payload_is_valid",
    "insert_graph_fragment",
]
