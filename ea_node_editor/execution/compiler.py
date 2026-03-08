from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_PORT_KEY,
    SUBNODE_TYPE_ID,
)

_COMPILE_ONLY_TYPES = frozenset({SUBNODE_TYPE_ID, SUBNODE_INPUT_TYPE_ID, SUBNODE_OUTPUT_TYPE_ID})
_EdgeTuple = tuple[str, str, str, str]


def compile_workspace_document(workspace_doc: Mapping[str, Any]) -> dict[str, Any]:
    """Compile nested subnode authoring constructs into a flat execution graph."""
    nodes_by_id, node_order = _normalize_nodes(workspace_doc.get("nodes"))
    edge_set = _normalize_edges(workspace_doc.get("edges"), valid_node_ids=set(nodes_by_id))

    input_pins_by_shell: dict[str, set[str]] = defaultdict(set)
    output_pin_parent: dict[str, str] = {}

    for node_id, node_doc in nodes_by_id.items():
        type_id = str(node_doc.get("type_id", ""))
        parent_id = _normalize_optional_id(node_doc.get("parent_node_id"))
        if type_id == SUBNODE_INPUT_TYPE_ID and parent_id and _node_type(nodes_by_id, parent_id) == SUBNODE_TYPE_ID:
            input_pins_by_shell[parent_id].add(node_id)
        elif type_id == SUBNODE_OUTPUT_TYPE_ID and parent_id and _node_type(nodes_by_id, parent_id) == SUBNODE_TYPE_ID:
            output_pin_parent[node_id] = parent_id

    compiled_edges = _compile_edges(
        nodes_by_id=nodes_by_id,
        edge_set=edge_set,
        input_pins_by_shell=input_pins_by_shell,
        output_pin_parent=output_pin_parent,
    )

    compiled_nodes: list[dict[str, Any]] = []
    real_node_ids: set[str] = set()
    for node_id in node_order:
        node_doc = nodes_by_id[node_id]
        if _is_compile_only(node_doc):
            continue
        compiled = dict(node_doc)
        compiled["parent_node_id"] = None
        compiled_nodes.append(compiled)
        real_node_ids.add(node_id)

    flattened_edges: list[dict[str, str]] = []
    for source_node_id, source_port_key, target_node_id, target_port_key in sorted(compiled_edges):
        if source_node_id not in real_node_ids or target_node_id not in real_node_ids:
            continue
        flattened_edges.append(
            {
                "source_node_id": source_node_id,
                "source_port_key": source_port_key,
                "target_node_id": target_node_id,
                "target_port_key": target_port_key,
            }
        )

    compiled_workspace = {key: value for key, value in workspace_doc.items() if key not in {"nodes", "edges"}}
    compiled_workspace["nodes"] = compiled_nodes
    compiled_workspace["edges"] = flattened_edges
    return compiled_workspace


def _compile_edges(
    *,
    nodes_by_id: Mapping[str, Mapping[str, Any]],
    edge_set: set[_EdgeTuple],
    input_pins_by_shell: Mapping[str, set[str]],
    output_pin_parent: Mapping[str, str],
) -> set[_EdgeTuple]:
    compiled_edges = set(edge_set)
    while True:
        outgoing_by_source: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        for source_node_id, source_port_key, target_node_id, target_port_key in compiled_edges:
            outgoing_by_source[(source_node_id, source_port_key)].append((target_node_id, target_port_key))

        additions: set[_EdgeTuple] = set()
        for source_node_id, source_port_key, target_node_id, target_port_key in compiled_edges:
            target_type_id = _node_type(nodes_by_id, target_node_id)
            if target_type_id == SUBNODE_TYPE_ID:
                if target_port_key not in input_pins_by_shell.get(target_node_id, set()):
                    continue
                for next_target_node_id, next_target_port_key in outgoing_by_source.get(
                    (target_port_key, SUBNODE_PIN_PORT_KEY),
                    [],
                ):
                    additions.add(
                        (
                            source_node_id,
                            source_port_key,
                            next_target_node_id,
                            next_target_port_key,
                        )
                    )
                continue

            if target_type_id == SUBNODE_OUTPUT_TYPE_ID and target_port_key == SUBNODE_PIN_PORT_KEY:
                shell_node_id = output_pin_parent.get(target_node_id, "")
                if not shell_node_id:
                    continue
                for next_target_node_id, next_target_port_key in outgoing_by_source.get(
                    (shell_node_id, target_node_id),
                    [],
                ):
                    additions.add(
                        (
                            source_node_id,
                            source_port_key,
                            next_target_node_id,
                            next_target_port_key,
                        )
                    )

        new_edges = additions - compiled_edges
        if not new_edges:
            return compiled_edges
        compiled_edges.update(new_edges)


def _normalize_nodes(raw_nodes: object) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not isinstance(raw_nodes, list):
        return {}, []

    nodes_by_id: dict[str, dict[str, Any]] = {}
    node_order: list[str] = []
    for raw_node in raw_nodes:
        if not isinstance(raw_node, Mapping):
            continue
        node_id = _normalize_required_id(raw_node.get("node_id"))
        type_id = _normalize_required_id(raw_node.get("type_id"))
        if not node_id or not type_id or node_id in nodes_by_id:
            continue
        node_doc = dict(raw_node)
        node_doc["node_id"] = node_id
        node_doc["type_id"] = type_id
        node_doc["parent_node_id"] = _normalize_optional_id(raw_node.get("parent_node_id"))
        nodes_by_id[node_id] = node_doc
        node_order.append(node_id)
    return nodes_by_id, node_order


def _normalize_edges(raw_edges: object, *, valid_node_ids: set[str]) -> set[_EdgeTuple]:
    if not isinstance(raw_edges, list):
        return set()

    edges: set[_EdgeTuple] = set()
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, Mapping):
            continue
        source_node_id = _normalize_required_id(raw_edge.get("source_node_id"))
        source_port_key = _normalize_required_id(raw_edge.get("source_port_key"))
        target_node_id = _normalize_required_id(raw_edge.get("target_node_id"))
        target_port_key = _normalize_required_id(raw_edge.get("target_port_key"))
        if (
            not source_node_id
            or not source_port_key
            or not target_node_id
            or not target_port_key
            or source_node_id not in valid_node_ids
            or target_node_id not in valid_node_ids
        ):
            continue
        edges.add(
            (
                source_node_id,
                source_port_key,
                target_node_id,
                target_port_key,
            )
        )
    return edges


def _is_compile_only(node_doc: Mapping[str, Any]) -> bool:
    return str(node_doc.get("type_id", "")) in _COMPILE_ONLY_TYPES


def _node_type(nodes_by_id: Mapping[str, Mapping[str, Any]], node_id: str) -> str:
    node_doc = nodes_by_id.get(node_id)
    if node_doc is None:
        return ""
    return str(node_doc.get("type_id", ""))


def _normalize_required_id(value: object) -> str:
    return str(value or "").strip()


def _normalize_optional_id(value: object) -> str | None:
    normalized = _normalize_required_id(value)
    if not normalized:
        return None
    return normalized


__all__ = ["compile_workspace_document"]
