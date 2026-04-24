"""Runtime workspace DTOs plus explicit graph conversion adapters.

This module owns the execution-time document shape. Graph objects enter only
through the ``from_*`` assembly adapters; worker execution and persistence
codecs stay outside this DTO layer.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from ea_node_editor.graph.model import EdgeInstance, NodeInstance, WorkspaceData

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


def _require_mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    raise ValueError(f"{field_name} must be a mapping.")


def _require_sequence(value: Any, *, field_name: str) -> list[Any] | tuple[Any, ...]:
    if isinstance(value, (list, tuple)):
        return value
    raise ValueError(f"{field_name} must be a list.")

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

    @classmethod
    def from_node_instance(cls, node: "NodeInstance") -> RuntimeNode:
        from ea_node_editor.graph.model import node_instance_to_mapping

        runtime_node = cls.from_mapping(node_instance_to_mapping(node))
        if runtime_node is None:
            raise ValueError(f"Unable to materialize runtime node: {node.node_id}")
        return runtime_node

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

    @classmethod
    def from_edge_instance(cls, edge: "EdgeInstance") -> RuntimeEdge:
        from ea_node_editor.graph.model import edge_instance_to_mapping

        runtime_edge = cls.from_mapping(edge_instance_to_mapping(edge))
        if runtime_edge is None:
            raise ValueError(f"Unable to materialize runtime edge: {edge.edge_id}")
        return runtime_edge

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
        document_fields_source = _require_mapping(
            document_fields_payload,
            field_name="runtime_workspace.document_fields",
        )
        document_fields = {
            str(key): copy.deepcopy(value)
            for key, value in document_fields_source.items()
        }

        nodes: list[RuntimeNode] = []
        for raw_node in _require_sequence(payload.get("nodes"), field_name="runtime_workspace.nodes"):
            _require_mapping(raw_node, field_name="runtime_workspace.nodes entry")
            node = RuntimeNode.from_mapping(raw_node)
            if node is None:
                raise ValueError("runtime_workspace.nodes entries require node_id and type_id.")
            nodes.append(node)

        edges: list[RuntimeEdge] = []
        for raw_edge in _require_sequence(payload.get("edges"), field_name="runtime_workspace.edges"):
            _require_mapping(raw_edge, field_name="runtime_workspace.edges entry")
            edge = RuntimeEdge.from_mapping(raw_edge)
            if edge is None:
                raise ValueError("runtime_workspace.edges entries require complete endpoint fields.")
            edges.append(edge)

        return cls(
            document_fields=document_fields,
            nodes=tuple(nodes),
            edges=tuple(edges),
        )

    @classmethod
    def from_workspace_data(cls, workspace: "WorkspaceData") -> RuntimeWorkspace:
        from ea_node_editor.graph.hierarchy import normalize_scope_path

        workspace.ensure_default_view()
        active_view_id = workspace.active_view_id
        if active_view_id not in workspace.views:
            active_view_id = next(iter(workspace.views))

        document_fields = {
            "workspace_id": workspace.workspace_id,
            "name": workspace.name,
            "dirty": workspace.dirty,
            "active_view_id": active_view_id,
            "views": [
                {
                    "view_id": view.view_id,
                    "name": view.name,
                    "zoom": view.zoom,
                    "pan_x": view.pan_x,
                    "pan_y": view.pan_y,
                    "scope_path": list(normalize_scope_path(workspace, view.scope_path)),
                }
                for view in workspace.views.values()
            ],
        }
        return cls(
            document_fields=document_fields,
            nodes=tuple(
                RuntimeNode.from_node_instance(node)
                for node in sorted(workspace.nodes.values(), key=lambda item: item.node_id)
            ),
            edges=tuple(
                RuntimeEdge.from_edge_instance(edge)
                for edge in sorted(workspace.edges.values(), key=lambda item: item.edge_id)
            ),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "document_fields": copy.deepcopy(self.document_fields),
            "nodes": [node.to_document() for node in self.nodes],
            "edges": [edge.to_document() for edge in self.edges],
        }


__all__ = ["RuntimeEdge", "RuntimeNode", "RuntimeWorkspace"]
