from __future__ import annotations

import copy
from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping, Sequence

from ea_node_editor.graph.effective_ports import (
    effective_ports as resolve_effective_ports,
    find_port,
    is_subnode_pin_type,
    port_side,
)
from ea_node_editor.graph.hierarchy import normalize_scope_path, scope_parent_id, subtree_node_ids
from ea_node_editor.graph.model import EdgeInstance, GraphModel, NodeInstance, WorkspaceData
from ea_node_editor.graph.normalization import GraphInvariantKernel
from ea_node_editor.graph.subnode_contract import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_PIN_KIND_PROPERTY,
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_PIN_PORT_KEY,
    SUBNODE_TYPE_ID,
    default_subnode_pin_label,
    is_subnode_shell_type,
    normalize_subnode_pin_data_type,
    normalize_subnode_pin_kind,
    resolve_subnode_pin_definition,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec

_PIN_OFFSET_X = 220.0
_PIN_ROW_STEP = 70.0
_FRAGMENT_EXTERNAL_PARENT_PREFIX = "__ea_external_parent__:"
_DEFAULT_LAYOUT_GRID_SIZE = 20.0


@dataclass(slots=True, frozen=True)
class GroupSubnodeResult:
    shell_node_id: str
    moved_node_ids: tuple[str, ...]
    created_pin_node_ids: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class UngroupSubnodeResult:
    removed_shell_node_id: str
    moved_node_ids: tuple[str, ...]
    removed_pin_node_ids: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class LayoutNodeBounds:
    node_id: str
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height


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


@dataclass(slots=True, frozen=True)
class SubnodeShellPinPlan:
    pin_type_id: str
    label: str
    x: float
    y: float


@dataclass(slots=True, frozen=True)
class _BoundaryEdge:
    edge: EdgeInstance
    pin_type_id: str
    label: str
    kind: str
    data_type: str


def plan_subnode_shell_pin_addition(
    *,
    workspace: WorkspaceData,
    shell_node_id: object,
    pin_type_id: object,
) -> SubnodeShellPinPlan | None:
    normalized_shell_node_id = str(shell_node_id).strip()
    normalized_pin_type_id = str(pin_type_id).strip()
    if not normalized_shell_node_id or not normalized_pin_type_id:
        return None

    shell_node = workspace.nodes.get(normalized_shell_node_id)
    if shell_node is None or not is_subnode_shell_type(shell_node.type_id):
        return None
    if normalized_pin_type_id not in {SUBNODE_INPUT_TYPE_ID, SUBNODE_OUTPUT_TYPE_ID}:
        return None

    same_direction_pins: list[NodeInstance] = []
    for candidate in workspace.nodes.values():
        if candidate.parent_node_id != shell_node.node_id:
            continue
        if str(candidate.type_id).strip() != normalized_pin_type_id:
            continue
        same_direction_pins.append(candidate)

    base_label = default_subnode_pin_label(normalized_pin_type_id)
    existing_labels = {
        resolve_subnode_pin_definition(candidate.type_id, candidate.properties).label.strip().lower()
        for candidate in same_direction_pins
    }
    pin_label = base_label
    suffix = 2
    while pin_label.strip().lower() in existing_labels:
        pin_label = f"{base_label} {suffix}"
        suffix += 1

    y_positions = [float(candidate.y) for candidate in same_direction_pins]
    pin_y = (max(y_positions) + 90.0) if y_positions else (float(shell_node.y) + 60.0)
    pin_x = float(shell_node.x) + (40.0 if normalized_pin_type_id == SUBNODE_INPUT_TYPE_ID else 360.0)
    return SubnodeShellPinPlan(
        pin_type_id=normalized_pin_type_id,
        label=pin_label,
        x=pin_x,
        y=pin_y,
    )


def collect_layout_node_bounds(
    *,
    workspace: WorkspaceData,
    node_ids: Sequence[str],
    spec_lookup: Callable[[str], NodeTypeSpec],
    size_resolver: Callable[[NodeInstance, NodeTypeSpec, Mapping[str, NodeInstance]], tuple[float, float]],
) -> list[LayoutNodeBounds]:
    layout_nodes: list[LayoutNodeBounds] = []
    for node_id in node_ids:
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        spec = spec_lookup(node.type_id)
        width, height = size_resolver(node, spec, workspace.nodes)
        layout_nodes.append(
            LayoutNodeBounds(
                node_id=node_id,
                x=float(node.x),
                y=float(node.y),
                width=float(width),
                height=float(height),
            )
        )
    return layout_nodes


def snap_coordinate(value: float, grid_size: float, *, default_step: float = _DEFAULT_LAYOUT_GRID_SIZE) -> float:
    step = float(grid_size)
    if not math.isfinite(step) or step <= 0.0:
        step = float(default_step)
    target = float(value)
    if not math.isfinite(target):
        return 0.0
    return round(target / step) * step


def build_alignment_position_updates(
    *,
    layout_nodes: Sequence[LayoutNodeBounds],
    alignment: str,
) -> dict[str, tuple[float, float]]:
    normalized_alignment = str(alignment).strip().lower()
    if normalized_alignment not in {"left", "right", "top", "bottom"}:
        return {}
    if len(layout_nodes) < 2:
        return {}

    updates: dict[str, tuple[float, float]] = {}
    if normalized_alignment == "left":
        target_left = min(node.left for node in layout_nodes)
        for node in layout_nodes:
            updates[node.node_id] = (target_left, node.y)
    elif normalized_alignment == "right":
        target_right = max(node.right for node in layout_nodes)
        for node in layout_nodes:
            updates[node.node_id] = (target_right - node.width, node.y)
    elif normalized_alignment == "top":
        target_top = min(node.top for node in layout_nodes)
        for node in layout_nodes:
            updates[node.node_id] = (node.x, target_top)
    else:
        target_bottom = max(node.bottom for node in layout_nodes)
        for node in layout_nodes:
            updates[node.node_id] = (node.x, target_bottom - node.height)
    return updates


def build_distribution_position_updates(
    *,
    layout_nodes: Sequence[LayoutNodeBounds],
    orientation: str,
) -> dict[str, tuple[float, float]]:
    normalized_orientation = str(orientation).strip().lower()
    if normalized_orientation not in {"horizontal", "vertical"}:
        return {}
    if len(layout_nodes) < 3:
        return {}

    updates: dict[str, tuple[float, float]] = {}
    if normalized_orientation == "horizontal":
        ordered = sorted(layout_nodes, key=lambda node: (node.left, node.top, node.node_id))
        total_span = ordered[-1].right - ordered[0].left
        total_size = sum(node.width for node in ordered)
        gap = (total_span - total_size) / float(len(ordered) - 1)
        cursor = ordered[0].right + gap
        for node in ordered[1:-1]:
            updates[node.node_id] = (cursor, node.y)
            cursor += node.width + gap
    else:
        ordered = sorted(layout_nodes, key=lambda node: (node.top, node.left, node.node_id))
        total_span = ordered[-1].bottom - ordered[0].top
        total_size = sum(node.height for node in ordered)
        gap = (total_span - total_size) / float(len(ordered) - 1)
        cursor = ordered[0].bottom + gap
        for node in ordered[1:-1]:
            updates[node.node_id] = (node.x, cursor)
            cursor += node.height + gap
    return updates


def normalize_layout_position_updates(
    *,
    workspace: WorkspaceData,
    updates: Mapping[str, tuple[float, float]],
    snap_to_grid: bool,
    grid_size: float,
    default_grid_size: float = _DEFAULT_LAYOUT_GRID_SIZE,
) -> dict[str, tuple[float, float]]:
    final_positions: dict[str, tuple[float, float]] = {}
    for node_id, (x_value, y_value) in updates.items():
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        final_x = float(x_value)
        final_y = float(y_value)
        if snap_to_grid:
            final_x = snap_coordinate(final_x, grid_size, default_step=default_grid_size)
            final_y = snap_coordinate(final_y, grid_size, default_step=default_grid_size)
        if float(node.x) == final_x and float(node.y) == final_y:
            continue
        final_positions[node_id] = (final_x, final_y)
    return final_positions


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
        if not isinstance(payload, Mapping):
            continue
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
                if (
                    not descendant_id
                    or descendant_id in selected_lookup
                    or descendant_id not in workspace.nodes
                ):
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


def build_subnode_custom_workflow_snapshot_data(
    *,
    workspace: WorkspaceData,
    registry: NodeRegistry,
    shell_node_id: object,
) -> dict[str, Any] | None:
    normalized_shell_node_id = str(shell_node_id).strip()
    if not normalized_shell_node_id:
        return None
    shell_node = workspace.nodes.get(normalized_shell_node_id)
    if shell_node is None or not is_subnode_shell_type(shell_node.type_id):
        return None
    try:
        shell_spec = registry.get_spec(shell_node.type_id)
    except KeyError:
        return None

    fragment_payload = build_subtree_fragment_payload_data(
        workspace=workspace,
        selected_node_ids=[normalized_shell_node_id],
    )
    if fragment_payload is None:
        return None

    ports_payload: list[dict[str, Any]] = []
    for port in resolve_effective_ports(
        node=shell_node,
        spec=shell_spec,
        workspace_nodes=workspace.nodes,
    ):
        ports_payload.append(
            {
                "key": port.key,
                "label": port.label,
                "direction": port.direction,
                "kind": port.kind,
                "data_type": port.data_type,
                "side": port_side(port),
                "exposed": bool(port.exposed),
            }
        )

    return {
        "ports": ports_payload,
        "fragment": fragment_payload,
    }


def fragment_node_from_payload(node_payload: Mapping[str, Any]) -> NodeInstance:
    return NodeInstance(
        node_id=str(node_payload.get("ref_id", "")),
        type_id=str(node_payload.get("type_id", "")),
        title=str(node_payload.get("title", "")),
        x=float(node_payload.get("x", 0.0)),
        y=float(node_payload.get("y", 0.0)),
        collapsed=bool(node_payload.get("collapsed", False)),
        properties=dict(node_payload.get("properties", {})),
        exposed_ports=dict(node_payload.get("exposed_ports", {})),
        visual_style=copy.deepcopy(node_payload.get("visual_style", {})),
        parent_node_id=node_payload.get("parent_node_id"),
        custom_width=float(node_payload["custom_width"]) if node_payload.get("custom_width") is not None else None,
        custom_height=float(node_payload["custom_height"]) if node_payload.get("custom_height") is not None else None,
    )


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
    return _insert_graph_fragment_transaction(
        mutations=model.mutation_service(workspace.workspace_id),
        workspace=workspace,
        fragment_payload=fragment_payload,
        delta_x=delta_x,
        delta_y=delta_y,
    )


def _insert_graph_fragment_transaction(
    *,
    mutations: "WorkspaceMutationService",
    workspace: WorkspaceData,
    fragment_payload: dict[str, Any],
    delta_x: float,
    delta_y: float,
) -> list[str]:

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
        created = mutations.add_node_raw(
            type_id=type_id,
            title=str(node_payload.get("title", "")),
            x=float(node_payload.get("x", 0.0)) + float(delta_x),
            y=float(node_payload.get("y", 0.0)) + float(delta_y),
            properties=dict(node_payload.get("properties", {})),
            exposed_ports=dict(node_payload.get("exposed_ports", {})),
            visual_style=copy.deepcopy(node_payload.get("visual_style", {})),
        )
        mutations.set_node_fragment_state(
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
        mutations.set_node_parent_raw(
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
            mutations.add_edge_raw(
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


def group_selection_into_subnode(
    *,
    model: GraphModel,
    registry: NodeRegistry,
    workspace_id: str,
    selected_node_ids: Sequence[object],
    scope_path: Sequence[object] | None,
    shell_x: float,
    shell_y: float,
) -> GroupSubnodeResult | None:
    workspace = model.project.workspaces.get(str(workspace_id).strip())
    if workspace is None:
        return None
    return _group_selection_into_subnode_transaction(
        mutations=model.validated_mutations(workspace.workspace_id, registry),
        registry=registry,
        workspace=workspace,
        selected_node_ids=selected_node_ids,
        scope_path=scope_path,
        shell_x=shell_x,
        shell_y=shell_y,
    )


def _group_selection_into_subnode_transaction(
    *,
    mutations: "WorkspaceMutationService",
    registry: NodeRegistry,
    workspace: WorkspaceData,
    selected_node_ids: Sequence[object],
    scope_path: Sequence[object] | None,
    shell_x: float,
    shell_y: float,
) -> GroupSubnodeResult | None:

    normalized_scope = normalize_scope_path(workspace, scope_path)
    expected_parent_id = scope_parent_id(normalized_scope)
    roots = _normalize_selected_roots(
        workspace=workspace,
        selected_node_ids=selected_node_ids,
        expected_parent_id=expected_parent_id,
    )
    if len(roots) < 2:
        return None
    if not _roots_share_parent(workspace=workspace, node_ids=roots):
        return None

    selected_set = set(roots)
    incoming_edges, outgoing_edges = _boundary_edges(
        workspace=workspace,
        selected_node_ids=selected_set,
    )
    incoming_boundary = [
        _build_boundary_edge(
            edge=edge,
            pin_type_id=SUBNODE_INPUT_TYPE_ID,
            registry=registry,
            workspace=workspace,
            inner_node_id=edge.target_node_id,
            inner_port_key=edge.target_port_key,
        )
        for edge in incoming_edges
    ]
    outgoing_boundary = [
        _build_boundary_edge(
            edge=edge,
            pin_type_id=SUBNODE_OUTPUT_TYPE_ID,
            registry=registry,
            workspace=workspace,
            inner_node_id=edge.source_node_id,
            inner_port_key=edge.source_port_key,
        )
        for edge in outgoing_edges
    ]

    shell_defaults = registry.default_properties(SUBNODE_TYPE_ID)
    shell_spec = registry.get_spec(SUBNODE_TYPE_ID)
    shell = mutations.add_node(
        type_id=SUBNODE_TYPE_ID,
        title=shell_spec.display_name,
        x=float(shell_x),
        y=float(shell_y),
        properties=shell_defaults,
        exposed_ports={},
        parent_node_id=expected_parent_id,
    )

    for node_id in roots:
        mutations.set_node_parent_raw(node_id, shell.node_id)

    created_pin_ids: list[str] = []

    for index, boundary in enumerate(incoming_boundary):
        pin_id = _create_boundary_pin(
            mutations=mutations,
            registry=registry,
            shell_node_id=shell.node_id,
            pin_type_id=boundary.pin_type_id,
            x=float(shell_x) - _PIN_OFFSET_X,
            y=float(shell_y) + (index * _PIN_ROW_STEP),
            label=boundary.label,
            kind=boundary.kind,
            data_type=boundary.data_type,
        )
        created_pin_ids.append(pin_id)
        mutations.remove_edge_raw(boundary.edge.edge_id)
        mutations.add_edge_raw(
            source_node_id=boundary.edge.source_node_id,
            source_port_key=boundary.edge.source_port_key,
            target_node_id=shell.node_id,
            target_port_key=pin_id,
        )
        mutations.add_edge_raw(
            source_node_id=pin_id,
            source_port_key=SUBNODE_PIN_PORT_KEY,
            target_node_id=boundary.edge.target_node_id,
            target_port_key=boundary.edge.target_port_key,
        )

    for index, boundary in enumerate(outgoing_boundary):
        pin_id = _create_boundary_pin(
            mutations=mutations,
            registry=registry,
            shell_node_id=shell.node_id,
            pin_type_id=boundary.pin_type_id,
            x=float(shell_x) + _PIN_OFFSET_X,
            y=float(shell_y) + (index * _PIN_ROW_STEP),
            label=boundary.label,
            kind=boundary.kind,
            data_type=boundary.data_type,
        )
        created_pin_ids.append(pin_id)
        mutations.remove_edge_raw(boundary.edge.edge_id)
        mutations.add_edge_raw(
            source_node_id=boundary.edge.source_node_id,
            source_port_key=boundary.edge.source_port_key,
            target_node_id=pin_id,
            target_port_key=SUBNODE_PIN_PORT_KEY,
        )
        mutations.add_edge_raw(
            source_node_id=shell.node_id,
            source_port_key=pin_id,
            target_node_id=boundary.edge.target_node_id,
            target_port_key=boundary.edge.target_port_key,
        )

    return GroupSubnodeResult(
        shell_node_id=shell.node_id,
        moved_node_ids=tuple(roots),
        created_pin_node_ids=tuple(created_pin_ids),
    )


def ungroup_subnode(
    *,
    model: GraphModel,
    workspace_id: str,
    shell_node_id: object,
) -> UngroupSubnodeResult | None:
    workspace = model.project.workspaces.get(str(workspace_id).strip())
    if workspace is None:
        return None
    return _ungroup_subnode_transaction(
        mutations=model.mutation_service(workspace.workspace_id),
        workspace=workspace,
        shell_node_id=shell_node_id,
    )


def _ungroup_subnode_transaction(
    *,
    mutations: "WorkspaceMutationService",
    workspace: WorkspaceData,
    shell_node_id: object,
) -> UngroupSubnodeResult | None:

    normalized_shell_id = str(shell_node_id).strip()
    if not normalized_shell_id:
        return None
    shell = workspace.nodes.get(normalized_shell_id)
    if shell is None or not is_subnode_shell_type(shell.type_id):
        return None

    direct_children = [
        node
        for node in workspace.nodes.values()
        if node.parent_node_id == normalized_shell_id
    ]
    direct_children.sort(key=lambda node: (float(node.y), float(node.x), node.node_id))

    pin_nodes = [node for node in direct_children if is_subnode_pin_type(node.type_id)]
    moved_nodes = [node for node in direct_children if not is_subnode_pin_type(node.type_id)]

    rewired_edges: set[tuple[str, str, str, str]] = set()
    for pin_node in pin_nodes:
        if pin_node.type_id == SUBNODE_INPUT_TYPE_ID:
            outer_edges = [
                edge
                for edge in workspace.edges.values()
                if edge.target_node_id == normalized_shell_id
                and edge.target_port_key == pin_node.node_id
            ]
            inner_edges = [
                edge
                for edge in workspace.edges.values()
                if edge.source_node_id == pin_node.node_id
                and edge.source_port_key == SUBNODE_PIN_PORT_KEY
            ]
            outer_edges.sort(key=_edge_sort_key)
            inner_edges.sort(key=_edge_sort_key)
            for outer in outer_edges:
                for inner in inner_edges:
                    rewired_edges.add(
                        (
                            outer.source_node_id,
                            outer.source_port_key,
                            inner.target_node_id,
                            inner.target_port_key,
                        )
                    )
        else:
            inner_edges = [
                edge
                for edge in workspace.edges.values()
                if edge.target_node_id == pin_node.node_id
                and edge.target_port_key == SUBNODE_PIN_PORT_KEY
            ]
            outer_edges = [
                edge
                for edge in workspace.edges.values()
                if edge.source_node_id == normalized_shell_id
                and edge.source_port_key == pin_node.node_id
            ]
            inner_edges.sort(key=_edge_sort_key)
            outer_edges.sort(key=_edge_sort_key)
            for inner in inner_edges:
                for outer in outer_edges:
                    rewired_edges.add(
                        (
                            inner.source_node_id,
                            inner.source_port_key,
                            outer.target_node_id,
                            outer.target_port_key,
                        )
                    )

    for node in moved_nodes:
        mutations.set_node_parent_raw(node.node_id, shell.parent_node_id)

    for pin_node in pin_nodes:
        mutations.remove_node_raw(pin_node.node_id)
    mutations.remove_node_raw(normalized_shell_id)

    for source_node_id, source_port_key, target_node_id, target_port_key in sorted(rewired_edges):
        if source_node_id not in workspace.nodes or target_node_id not in workspace.nodes:
            continue
        try:
            mutations.add_edge_raw(
                source_node_id=source_node_id,
                source_port_key=source_port_key,
                target_node_id=target_node_id,
                target_port_key=target_port_key,
            )
        except (KeyError, ValueError):
            continue

    return UngroupSubnodeResult(
        removed_shell_node_id=normalized_shell_id,
        moved_node_ids=tuple(node.node_id for node in moved_nodes),
        removed_pin_node_ids=tuple(node.node_id for node in pin_nodes),
    )


def _normalize_selected_roots(
    *,
    workspace: WorkspaceData,
    selected_node_ids: Sequence[object],
    expected_parent_id: str | None,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in selected_node_ids:
        node_id = str(value).strip()
        if not node_id or node_id in seen:
            continue
        node = workspace.nodes.get(node_id)
        if node is None:
            continue
        if node.parent_node_id != expected_parent_id:
            continue
        seen.add(node_id)
        normalized.append(node_id)
    return normalized


def _roots_share_parent(*, workspace: WorkspaceData, node_ids: Sequence[str]) -> bool:
    parent_values = {
        workspace.nodes[node_id].parent_node_id
        for node_id in node_ids
        if node_id in workspace.nodes
    }
    return len(parent_values) == 1


def _boundary_edges(
    *,
    workspace: WorkspaceData,
    selected_node_ids: set[str],
) -> tuple[list[EdgeInstance], list[EdgeInstance]]:
    incoming: list[EdgeInstance] = []
    outgoing: list[EdgeInstance] = []
    for edge in workspace.edges.values():
        source_in = edge.source_node_id in selected_node_ids
        target_in = edge.target_node_id in selected_node_ids
        if source_in and not target_in:
            outgoing.append(edge)
        elif target_in and not source_in:
            incoming.append(edge)
    incoming.sort(
        key=lambda edge: _incoming_boundary_sort_key(workspace, edge),
    )
    outgoing.sort(
        key=lambda edge: _outgoing_boundary_sort_key(workspace, edge),
    )
    return incoming, outgoing


def _incoming_boundary_sort_key(
    workspace: WorkspaceData,
    edge: EdgeInstance,
) -> tuple[float, float, float, float, str, str, str]:
    source_y, source_x = _node_sort_position(workspace, edge.source_node_id)
    target_y, target_x = _node_sort_position(workspace, edge.target_node_id)
    return (
        source_y,
        source_x,
        target_y,
        target_x,
        edge.source_port_key,
        edge.target_port_key,
        edge.edge_id,
    )


def _outgoing_boundary_sort_key(
    workspace: WorkspaceData,
    edge: EdgeInstance,
) -> tuple[float, float, float, float, str, str, str]:
    source_y, source_x = _node_sort_position(workspace, edge.source_node_id)
    target_y, target_x = _node_sort_position(workspace, edge.target_node_id)
    return (
        target_y,
        target_x,
        source_y,
        source_x,
        edge.target_port_key,
        edge.source_port_key,
        edge.edge_id,
    )


def _node_sort_position(workspace: WorkspaceData, node_id: str) -> tuple[float, float]:
    node = workspace.nodes.get(node_id)
    if node is None:
        return (0.0, 0.0)
    return (float(node.y), float(node.x))


def _build_boundary_edge(
    *,
    edge: EdgeInstance,
    pin_type_id: str,
    registry: NodeRegistry,
    workspace: WorkspaceData,
    inner_node_id: str,
    inner_port_key: str,
) -> _BoundaryEdge:
    label, kind, data_type = _pin_signature_for_inner_port(
        registry=registry,
        workspace=workspace,
        node_id=inner_node_id,
        port_key=inner_port_key,
    )
    return _BoundaryEdge(
        edge=edge,
        pin_type_id=pin_type_id,
        label=label,
        kind=kind,
        data_type=data_type,
    )


def _pin_signature_for_inner_port(
    *,
    registry: NodeRegistry,
    workspace: WorkspaceData,
    node_id: str,
    port_key: str,
) -> tuple[str, str, str]:
    default_label = str(port_key).strip() or "Port"
    default_signature = (default_label, "data", "any")
    node = workspace.nodes.get(node_id)
    if node is None:
        return default_signature
    try:
        spec = registry.get_spec(node.type_id)
    except KeyError:
        return default_signature

    port = find_port(
        node=node,
        spec=spec,
        workspace_nodes=workspace.nodes,
        port_key=port_key,
    )
    if port is None:
        return default_signature

    label = str(port.label).strip() or default_label
    kind = normalize_subnode_pin_kind(port.kind)
    data_type = normalize_subnode_pin_data_type(kind, port.data_type)
    return label, kind, data_type


def _create_boundary_pin(
    *,
    mutations,
    registry: NodeRegistry,
    shell_node_id: str,
    pin_type_id: str,
    x: float,
    y: float,
    label: str,
    kind: str,
    data_type: str,
) -> str:
    pin_spec = registry.get_spec(pin_type_id)
    pin_defaults = registry.default_properties(pin_type_id)
    pin = mutations.add_node(
        type_id=pin_type_id,
        title=pin_spec.display_name,
        x=float(x),
        y=float(y),
        properties=pin_defaults,
        exposed_ports={},
        parent_node_id=shell_node_id,
    )
    normalized_kind = normalize_subnode_pin_kind(kind)
    normalized_data_type = normalize_subnode_pin_data_type(normalized_kind, data_type)
    mutations.set_node_properties(
        pin.node_id,
        {
            SUBNODE_PIN_LABEL_PROPERTY: str(label).strip() or default_subnode_pin_label(pin_type_id),
            SUBNODE_PIN_KIND_PROPERTY: normalized_kind,
            SUBNODE_PIN_DATA_TYPE_PROPERTY: normalized_data_type,
        },
    )
    mutations.set_exposed_port(shell_node_id, pin.node_id, True)
    return pin.node_id


def _edge_sort_key(edge: EdgeInstance) -> tuple[str, str, str, str, str]:
    return (
        edge.source_node_id,
        edge.source_port_key,
        edge.target_node_id,
        edge.target_port_key,
        edge.edge_id,
    )


__all__ = [
    "GraphFragmentBounds",
    "GroupSubnodeResult",
    "LayoutNodeBounds",
    "SubnodeShellPinPlan",
    "UngroupSubnodeResult",
    "build_alignment_position_updates",
    "build_distribution_position_updates",
    "build_subnode_custom_workflow_snapshot_data",
    "build_subtree_fragment_payload_data",
    "collect_layout_node_bounds",
    "encode_fragment_external_parent_id",
    "expand_comment_backdrop_fragment_node_ids",
    "expand_subtree_fragment_node_ids",
    "fragment_node_from_payload",
    "graph_fragment_bounds",
    "graph_fragment_payload_is_valid",
    "group_selection_into_subnode",
    "insert_graph_fragment",
    "normalize_layout_position_updates",
    "plan_subnode_shell_pin_addition",
    "snap_coordinate",
    "ungroup_subnode",
]
