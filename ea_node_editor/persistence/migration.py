from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from ea_node_editor.custom_workflows import normalize_custom_workflow_metadata
from ea_node_editor.graph.model import node_instance_from_mapping
from ea_node_editor.graph.normalization import (
    accept_registry_edge,
    normalized_exposed_ports,
    resolve_registry_nodes,
    validate_registry_edge,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.passive_style_normalization import normalize_passive_style_presets
from ea_node_editor.persistence.utils import merge_defaults as merge_defaults_dict
from ea_node_editor.settings import (
    DEFAULT_UI_STATE,
    DEFAULT_WORKFLOW_SETTINGS,
    SCHEMA_VERSION,
)
from ea_node_editor.workspace.ownership import resolve_workspace_ownership


class JsonProjectMigration:
    def __init__(self, registry: NodeRegistry) -> None:
        self._registry = registry

    def migrate(self, raw_doc: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw_doc, Mapping):
            raise ValueError("Project document must be a JSON object.")
        version = self._coerce_int(raw_doc.get("schema_version", 0), default=0)
        doc = dict(raw_doc)
        if version > SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema version: {version}")
        while version < SCHEMA_VERSION:
            if version == 0:
                doc = self._migrate_v0_to_v1(doc)
                version = 1
            elif version == 1:
                doc = self._migrate_v1_to_v2(doc)
                version = 2
            elif version == 2:
                doc = self._migrate_v2_to_v3(doc)
                version = 3
            elif version == 3:
                doc = self._migrate_v3_to_v4(doc)
                version = 4
            else:
                raise ValueError(f"Unsupported schema version: {version}")
        return self._normalize_document(doc)

    @staticmethod
    def _migrate_v0_to_v1(doc: dict[str, Any]) -> dict[str, Any]:
        migrated = dict(doc)
        migrated["schema_version"] = 1
        if "metadata" not in migrated:
            migrated["metadata"] = {}
        return migrated

    @staticmethod
    def _migrate_v1_to_v2(doc: dict[str, Any]) -> dict[str, Any]:
        migrated = dict(doc)
        metadata = migrated.get("metadata")
        if not isinstance(metadata, Mapping):
            metadata = {}
        merged = dict(metadata)
        if "ui" not in merged:
            merged["ui"] = {}
        if "workflow_settings" not in merged:
            merged["workflow_settings"] = {}
        migrated["metadata"] = merged
        migrated["schema_version"] = 2
        return migrated

    @staticmethod
    def _migrate_v2_to_v3(doc: dict[str, Any]) -> dict[str, Any]:
        migrated = dict(doc)
        metadata = migrated.get("metadata")
        if not isinstance(metadata, Mapping):
            metadata = {}
        merged = dict(metadata)
        if "custom_workflows" not in merged:
            merged["custom_workflows"] = []
        migrated["metadata"] = merged
        migrated["schema_version"] = 3
        return migrated

    @staticmethod
    def _migrate_v3_to_v4(doc: dict[str, Any]) -> dict[str, Any]:
        migrated = dict(doc)
        migrated["schema_version"] = 4
        return migrated

    @staticmethod
    def _coerce_str(value: Any, default: str = "") -> str:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else default
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    @staticmethod
    def _coerce_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on"}:
                return True
            if normalized in {"0", "false", "no", "n", "off"}:
                return False
        return default

    @staticmethod
    def as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return {str(key): item for key, item in value.items()}
        return {}

    @staticmethod
    def merge_defaults(values: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(values, Mapping):
            return merge_defaults_dict({}, defaults)
        return merge_defaults_dict({str(key): value for key, value in values.items()}, defaults)

    @staticmethod
    def as_list(value: Any) -> list[Any]:
        if isinstance(value, list):
            return list(value)
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, Mapping):
            return list(value.values())
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return list(value)
        return []

    @staticmethod
    def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(dict(value))

    @staticmethod
    def normalize_metadata(source: Any, workspace_order: list[str]) -> dict[str, Any]:
        metadata = JsonProjectMigration.as_dict(source)
        metadata["workspace_order"] = list(workspace_order)
        metadata["ui"] = JsonProjectMigration.merge_defaults(metadata.get("ui"), DEFAULT_UI_STATE)
        metadata["ui"]["passive_style_presets"] = normalize_passive_style_presets(
            metadata["ui"].get("passive_style_presets")
        )
        metadata["workflow_settings"] = JsonProjectMigration.merge_defaults(
            metadata.get("workflow_settings"),
            DEFAULT_WORKFLOW_SETTINGS,
        )
        metadata["custom_workflows"] = normalize_custom_workflow_metadata(metadata.get("custom_workflows"))
        return metadata

    def _normalize_document(self, doc: dict[str, Any]) -> dict[str, Any]:
        normalized_workspaces: dict[str, dict[str, Any]] = {}
        for workspace_doc in self.as_list(doc.get("workspaces", [])):
            if not isinstance(workspace_doc, Mapping):
                continue
            workspace_id = self._coerce_str(workspace_doc.get("workspace_id"))
            if not workspace_id or workspace_id in normalized_workspaces:
                continue
            normalized_workspaces[workspace_id] = self._normalize_workspace_doc(workspace_doc, workspace_id)

        ownership = resolve_workspace_ownership(
            normalized_workspaces,
            order_sources=(
                doc.get("workspace_order"),
                self.as_dict(doc.get("metadata")).get("workspace_order"),
            ),
            active_workspace_id=doc.get("active_workspace_id"),
        )

        metadata = self.normalize_metadata(doc.get("metadata"), ownership.workspace_order)

        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": self._coerce_str(doc.get("project_id"), "proj_unknown"),
            "name": self._coerce_str(doc.get("name"), "untitled"),
            "active_workspace_id": ownership.active_workspace_id,
            "workspace_order": ownership.workspace_order,
            "workspaces": [normalized_workspaces[workspace_id] for workspace_id in ownership.workspace_order],
            "metadata": metadata,
        }

    def _normalize_workspace_doc(self, workspace_doc: Mapping[str, Any], workspace_id: str) -> dict[str, Any]:
        views_by_id: dict[str, dict[str, Any]] = {}
        for index, view_doc in enumerate(self.as_list(workspace_doc.get("views", [])), start=1):
            if not isinstance(view_doc, Mapping):
                continue
            view_id = self._coerce_str(view_doc.get("view_id"))
            if not view_id or view_id in views_by_id:
                continue
            views_by_id[view_id] = {
                "view_id": view_id,
                "name": self._coerce_str(view_doc.get("name"), f"V{index}"),
                "zoom": self._coerce_float(view_doc.get("zoom"), 1.0),
                "pan_x": self._coerce_float(view_doc.get("pan_x"), 0.0),
                "pan_y": self._coerce_float(view_doc.get("pan_y"), 0.0),
                "scope_path": [
                    self._coerce_str(item)
                    for item in self.as_list(view_doc.get("scope_path"))
                    if self._coerce_str(item)
                ],
            }

        if not views_by_id:
            fallback_view_id = f"{workspace_id}_view_1"
            views_by_id[fallback_view_id] = {
                "view_id": fallback_view_id,
                "name": "V1",
                "zoom": 1.0,
                "pan_x": 0.0,
                "pan_y": 0.0,
                "scope_path": [],
            }

        active_view_id = self._coerce_str(workspace_doc.get("active_view_id"))
        if active_view_id not in views_by_id:
            active_view_id = next(iter(views_by_id))

        nodes_by_id: dict[str, dict[str, Any]] = {}
        unresolved_node_ids: set[str] = set()
        for node_doc in self.as_list(workspace_doc.get("nodes", [])):
            if not isinstance(node_doc, Mapping):
                continue
            node_id = self._coerce_str(node_doc.get("node_id"))
            type_id = self._coerce_str(node_doc.get("type_id"))
            if not node_id or node_id in nodes_by_id or not type_id:
                continue
            spec = self._registry.spec_or_none(type_id)
            if spec is None:
                preserved_node = self._copy_mapping(node_doc)
                preserved_node["node_id"] = node_id
                preserved_node["type_id"] = type_id
                nodes_by_id[node_id] = preserved_node
                unresolved_node_ids.add(node_id)
                continue
            nodes_by_id[node_id] = {
                "node_id": node_id,
                "type_id": type_id,
                "title": self._coerce_str(node_doc.get("title"), spec.display_name),
                "x": self._coerce_float(node_doc.get("x"), 0.0),
                "y": self._coerce_float(node_doc.get("y"), 0.0),
                "collapsed": self._coerce_bool(node_doc.get("collapsed"), False),
                "properties": self._registry.normalize_properties(
                    type_id,
                    self.as_dict(node_doc.get("properties")),
                    include_defaults=False,
                ),
                "exposed_ports": {
                    key: self._coerce_bool(value)
                    for key, value in self.as_dict(node_doc.get("exposed_ports")).items()
                },
                "visual_style": self.as_dict(node_doc.get("visual_style")),
                "parent_node_id": self._coerce_str(node_doc.get("parent_node_id")) or None,
                "custom_width": self._coerce_float(node_doc["custom_width"]) if node_doc.get("custom_width") is not None else None,
                "custom_height": self._coerce_float(node_doc["custom_height"]) if node_doc.get("custom_height") is not None else None,
            }

        for node_id, node in nodes_by_id.items():
            parent_id = self._coerce_str(node.get("parent_node_id")) or None
            if parent_id not in nodes_by_id or parent_id == node_id:
                if node_id not in unresolved_node_ids:
                    node["parent_node_id"] = None

        workspace_nodes_for_ports = {
            node_id: node_instance_from_mapping(node)
            for node_id, node in nodes_by_id.items()
        }
        workspace_nodes_for_ports = {
            node_id: node
            for node_id, node in workspace_nodes_for_ports.items()
            if node is not None
        }
        resolved_nodes = resolve_registry_nodes(workspace_nodes_for_ports, self._registry)
        for node_id, resolution in resolved_nodes.items():
            normalized_ports = normalized_exposed_ports(
                resolution,
                workspace_nodes=workspace_nodes_for_ports,
            )
            nodes_by_id[node_id]["exposed_ports"] = normalized_ports
            workspace_nodes_for_ports[node_id].exposed_ports = dict(normalized_ports)

        edges_by_id: dict[str, dict[str, Any]] = {}
        seen_connections: set[tuple[str, str, str, str]] = set()
        occupied_single_target_ports: set[tuple[str, str]] = set()
        for edge_doc in self.as_list(workspace_doc.get("edges", [])):
            if not isinstance(edge_doc, Mapping):
                continue
            edge_id = self._coerce_str(edge_doc.get("edge_id"))
            source_node_id = self._coerce_str(edge_doc.get("source_node_id"))
            source_port_key = self._coerce_str(edge_doc.get("source_port_key"))
            target_node_id = self._coerce_str(edge_doc.get("target_node_id"))
            target_port_key = self._coerce_str(edge_doc.get("target_port_key"))
            if (
                not edge_id
                or not source_node_id
                or not source_port_key
                or not target_node_id
                or not target_port_key
            ):
                continue
            if edge_id in edges_by_id:
                continue
            if source_node_id not in nodes_by_id or target_node_id not in nodes_by_id:
                continue
            if source_node_id in unresolved_node_ids or target_node_id in unresolved_node_ids:
                preserved_edge = self._copy_mapping(edge_doc)
                preserved_edge["edge_id"] = edge_id
                preserved_edge["source_node_id"] = source_node_id
                preserved_edge["source_port_key"] = source_port_key
                preserved_edge["target_node_id"] = target_node_id
                preserved_edge["target_port_key"] = target_port_key
                edges_by_id[edge_id] = preserved_edge
                continue

            resolution = validate_registry_edge(
                source_node_id=source_node_id,
                source_port_key=source_port_key,
                target_node_id=target_node_id,
                target_port_key=target_port_key,
                resolved_nodes=resolved_nodes,
                require_source_output=True,
                require_target_input=True,
                require_exposed_ports=True,
            )
            if resolution is None or not accept_registry_edge(
                resolution,
                seen_connections=seen_connections,
                occupied_single_target_ports=occupied_single_target_ports,
            ):
                continue

            edges_by_id[edge_id] = {
                "edge_id": edge_id,
                "source_node_id": source_node_id,
                "source_port_key": source_port_key,
                "target_node_id": target_node_id,
                "target_port_key": target_port_key,
                "label": self._coerce_str(edge_doc.get("label")),
                "visual_style": self.as_dict(edge_doc.get("visual_style")),
            }

        return {
            "workspace_id": workspace_id,
            "name": self._coerce_str(workspace_doc.get("name"), "Workspace"),
            "dirty": self._coerce_bool(workspace_doc.get("dirty"), False),
            "active_view_id": active_view_id,
            "views": list(views_by_id.values()),
            "nodes": [nodes_by_id[node_id] for node_id in sorted(nodes_by_id)],
            "edges": [edges_by_id[edge_id] for edge_id in sorted(edges_by_id)],
        }
