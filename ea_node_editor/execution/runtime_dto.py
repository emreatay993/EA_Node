from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Mapping

from ea_node_editor.graph.model import node_instance_from_mapping

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
    custom_width: float | None = None
    custom_height: float | None = None
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RuntimeNode | None:
        node = node_instance_from_mapping(payload)
        if node is None:
            return None
        return cls(
            node_id=node.node_id,
            type_id=node.type_id,
            title=node.title,
            x=node.x,
            y=node.y,
            collapsed=node.collapsed,
            properties=copy.deepcopy(node.properties),
            exposed_ports=copy.deepcopy(node.exposed_ports),
            visual_style=copy.deepcopy(node.visual_style),
            custom_width=node.custom_width,
            custom_height=node.custom_height,
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
                "parent_node_id": None,
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

    def to_document(self) -> dict[str, str]:
        return {
            "source_node_id": self.source_node_id,
            "source_port_key": self.source_port_key,
            "target_node_id": self.target_node_id,
            "target_port_key": self.target_port_key,
        }


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

    def to_document(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.document_fields)
        payload["nodes"] = [node.to_document() for node in self.nodes]
        payload["edges"] = [edge.to_document() for edge in self.edges]
        return payload


__all__ = ["RuntimeEdge", "RuntimeNode", "RuntimeWorkspace"]
