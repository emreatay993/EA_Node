from __future__ import annotations

import copy
import json
from typing import Any

GRAPH_FRAGMENT_MIME_TYPE = "application/x-ea-node-editor-graph-fragment+json"
GRAPH_FRAGMENT_KIND = "ea-node-editor/graph-fragment"
GRAPH_FRAGMENT_VERSION = 1


def build_graph_fragment_payload(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": GRAPH_FRAGMENT_KIND,
        "version": GRAPH_FRAGMENT_VERSION,
        "nodes": nodes,
        "edges": edges,
    }


def serialize_graph_fragment_payload(payload: Any) -> str | None:
    normalized = normalize_graph_fragment_payload(payload)
    if normalized is None:
        return None
    try:
        return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return None


def parse_graph_fragment_payload(raw_text: str) -> dict[str, Any] | None:
    text = str(raw_text)
    if not text.strip():
        return None
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return None
    return normalize_graph_fragment_payload(decoded)


def normalize_graph_fragment_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != GRAPH_FRAGMENT_KIND:
        return None
    if int(payload.get("version", -1)) != GRAPH_FRAGMENT_VERSION:
        return None

    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        return None

    normalized_nodes: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()
    for raw_node in raw_nodes:
        normalized_node = _normalize_node_entry(raw_node)
        if normalized_node is None:
            return None
        ref_id = normalized_node["ref_id"]
        if ref_id in seen_node_ids:
            return None
        seen_node_ids.add(ref_id)
        normalized_nodes.append(normalized_node)
    if not normalized_nodes:
        return None

    normalized_edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str, str, str]] = set()
    seen_target_inputs: set[tuple[str, str]] = set()
    for raw_edge in raw_edges:
        normalized_edge = _normalize_edge_entry(raw_edge)
        if normalized_edge is None:
            return None
        source_ref_id = normalized_edge["source_ref_id"]
        target_ref_id = normalized_edge["target_ref_id"]
        if source_ref_id not in seen_node_ids or target_ref_id not in seen_node_ids:
            return None
        edge_key = (
            source_ref_id,
            normalized_edge["source_port_key"],
            target_ref_id,
            normalized_edge["target_port_key"],
        )
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        target_key = (target_ref_id, normalized_edge["target_port_key"])
        if target_key in seen_target_inputs:
            return None
        seen_target_inputs.add(target_key)
        normalized_edges.append(normalized_edge)

    return build_graph_fragment_payload(nodes=normalized_nodes, edges=normalized_edges)


def _normalize_node_entry(raw_node: Any) -> dict[str, Any] | None:
    if not isinstance(raw_node, dict):
        return None

    ref_id = str(raw_node.get("ref_id", "")).strip()
    type_id = str(raw_node.get("type_id", "")).strip()
    if not ref_id or not type_id:
        return None

    try:
        x = float(raw_node.get("x", 0.0))
        y = float(raw_node.get("y", 0.0))
    except (TypeError, ValueError):
        return None

    raw_exposed_ports = raw_node.get("exposed_ports", {})
    if not isinstance(raw_exposed_ports, dict):
        return None
    normalized_exposed_ports: dict[str, bool] = {}
    for key, value in raw_exposed_ports.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            return None
        normalized_exposed_ports[normalized_key] = bool(value)

    raw_properties = raw_node.get("properties", {})
    if not isinstance(raw_properties, dict):
        return None

    raw_parent = raw_node.get("parent_node_id")
    parent_node_id: str | None = None
    if raw_parent is not None:
        normalized_parent = str(raw_parent).strip()
        parent_node_id = normalized_parent or None

    return {
        "ref_id": ref_id,
        "type_id": type_id,
        "title": str(raw_node.get("title", "")),
        "x": x,
        "y": y,
        "collapsed": bool(raw_node.get("collapsed", False)),
        "properties": copy.deepcopy(raw_properties),
        "exposed_ports": normalized_exposed_ports,
        "parent_node_id": parent_node_id,
    }


def _normalize_edge_entry(raw_edge: Any) -> dict[str, str] | None:
    if not isinstance(raw_edge, dict):
        return None
    source_ref_id = str(raw_edge.get("source_ref_id", "")).strip()
    source_port_key = str(raw_edge.get("source_port_key", "")).strip()
    target_ref_id = str(raw_edge.get("target_ref_id", "")).strip()
    target_port_key = str(raw_edge.get("target_port_key", "")).strip()
    if not source_ref_id or not source_port_key or not target_ref_id or not target_port_key:
        return None
    return {
        "source_ref_id": source_ref_id,
        "source_port_key": source_port_key,
        "target_ref_id": target_ref_id,
        "target_port_key": target_port_key,
    }


__all__ = [
    "GRAPH_FRAGMENT_KIND",
    "GRAPH_FRAGMENT_MIME_TYPE",
    "GRAPH_FRAGMENT_VERSION",
    "build_graph_fragment_payload",
    "normalize_graph_fragment_payload",
    "parse_graph_fragment_payload",
    "serialize_graph_fragment_payload",
]
