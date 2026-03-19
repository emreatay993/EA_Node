from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Mapping

_RUNTIME_NODE_FIELDS = frozenset(
    {
        "node_id",
        "type_id",
        "title",
        "x",
        "y",
        "collapsed",
        "properties",
        "exposed_ports",
        "visual_style",
        "parent_node_id",
        "custom_width",
        "custom_height",
    }
)


def _coerce_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else default
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): copy.deepcopy(item) for key, item in value.items()}

_RUNTIME_EDGE_FIELDS = frozenset(
    {
        "edge_id",
        "source_node_id",
        "source_port_key",
        "target_node_id",
        "target_port_key",
        "label",
        "visual_style",
    }
)


@dataclass(slots=True, frozen=True)
class RuntimeNode:
    node_id: str
    type_id: str
    title: str
    x: float
    y: float
    collapsed: bool = False
    properties: dict[str, Any] = field(default_factory=dict)
    exposed_ports: dict[str, bool] = field(default_factory=dict)
    visual_style: dict[str, Any] = field(default_factory=dict)
    parent_node_id: str | None = None
    custom_width: float | None = None
    custom_height: float | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RuntimeNode | None:
        node_id = _coerce_str(payload.get("node_id"))
        type_id = _coerce_str(payload.get("type_id"))
        if not node_id or not type_id:
            return None
        return cls(
            node_id=node_id,
            type_id=type_id,
            title=_coerce_str(payload.get("title"), type_id),
            x=_coerce_float(payload.get("x"), 0.0),
            y=_coerce_float(payload.get("y"), 0.0),
            collapsed=bool(payload.get("collapsed", False)),
            properties=_as_mapping(payload.get("properties")),
            exposed_ports={key: bool(value) for key, value in _as_mapping(payload.get("exposed_ports")).items()},
            visual_style=_as_mapping(payload.get("visual_style")),
            parent_node_id=_coerce_str(payload.get("parent_node_id")) or None,
            custom_width=_coerce_float(payload.get("custom_width")) if payload.get("custom_width") is not None else None,
            custom_height=_coerce_float(payload.get("custom_height")) if payload.get("custom_height") is not None else None,
            extra_fields={
                str(key): copy.deepcopy(value)
                for key, value in payload.items()
                if str(key) not in _RUNTIME_NODE_FIELDS
            },
        )

    def to_document(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.extra_fields)
        payload.update(
            {
                "node_id": self.node_id,
                "type_id": self.type_id,
                "title": self.title,
                "x": self.x,
                "y": self.y,
                "collapsed": self.collapsed,
                "properties": copy.deepcopy(self.properties),
                "exposed_ports": copy.deepcopy(self.exposed_ports),
                "visual_style": copy.deepcopy(self.visual_style),
                "parent_node_id": self.parent_node_id,
                "custom_width": self.custom_width,
                "custom_height": self.custom_height,
            }
        )
        return payload


@dataclass(slots=True, frozen=True)
class RuntimeEdge:
    source_node_id: str
    source_port_key: str
    target_node_id: str
    target_port_key: str
    edge_id: str = ""
    label: str = ""
    visual_style: dict[str, Any] = field(default_factory=dict)
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RuntimeEdge | None:
        source_node_id = str(payload.get("source_node_id", "")).strip()
        source_port_key = str(payload.get("source_port_key", "")).strip()
        target_node_id = str(payload.get("target_node_id", "")).strip()
        target_port_key = str(payload.get("target_port_key", "")).strip()
        if not source_node_id or not source_port_key or not target_node_id or not target_port_key:
            return None
        visual_style = payload.get("visual_style")
        return cls(
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
            edge_id=str(payload.get("edge_id", "")).strip(),
            label=str(payload.get("label", "")),
            visual_style=copy.deepcopy(visual_style) if isinstance(visual_style, Mapping) else {},
            extra_fields={
                str(key): copy.deepcopy(value)
                for key, value in payload.items()
                if str(key) not in _RUNTIME_EDGE_FIELDS
            },
        )

    def to_document(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.extra_fields)
        payload.update(
            {
                "source_node_id": self.source_node_id,
                "source_port_key": self.source_port_key,
                "target_node_id": self.target_node_id,
                "target_port_key": self.target_port_key,
            }
        )
        if self.edge_id:
            payload["edge_id"] = self.edge_id
            payload["label"] = self.label
            payload["visual_style"] = copy.deepcopy(self.visual_style)
        return payload


@dataclass(slots=True, frozen=True)
class RuntimeWorkspace:
    document_fields: dict[str, Any] = field(default_factory=dict)
    nodes: tuple[RuntimeNode, ...] = field(default_factory=tuple)
    edges: tuple[RuntimeEdge, ...] = field(default_factory=tuple)

    @property
    def workspace_id(self) -> str:
        return str(self.document_fields.get("workspace_id", ""))

    @property
    def nodes_by_id(self) -> dict[str, RuntimeNode]:
        return {node.node_id: node for node in self.nodes}

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RuntimeWorkspace:
        document_fields_payload = payload.get("document_fields")
        if isinstance(document_fields_payload, Mapping):
            document_fields = {
                str(key): copy.deepcopy(value)
                for key, value in document_fields_payload.items()
            }
        else:
            document_fields = {
                str(key): copy.deepcopy(value)
                for key, value in payload.items()
                if str(key) not in {"nodes", "edges"}
            }

        nodes: list[RuntimeNode] = []
        for raw_node in payload.get("nodes", []):
            if not isinstance(raw_node, Mapping):
                continue
            node = RuntimeNode.from_mapping(raw_node)
            if node is None:
                continue
            nodes.append(node)

        edges: list[RuntimeEdge] = []
        for raw_edge in payload.get("edges", []):
            if not isinstance(raw_edge, Mapping):
                continue
            edge = RuntimeEdge.from_mapping(raw_edge)
            if edge is None:
                continue
            edges.append(edge)

        return cls(
            document_fields=document_fields,
            nodes=tuple(nodes),
            edges=tuple(edges),
        )

    def to_document(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.document_fields)
        payload["nodes"] = [node.to_document() for node in self.nodes]
        payload["edges"] = [edge.to_document() for edge in self.edges]
        return payload


__all__ = ["RuntimeEdge", "RuntimeNode", "RuntimeWorkspace"]
