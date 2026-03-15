from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ea_node_editor.custom_workflows import normalize_custom_workflow_metadata
from ea_node_editor.graph.effective_ports import find_port as find_effective_port
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.persistence.utils import merge_defaults as merge_defaults_dict
from ea_node_editor.settings import (
    DEFAULT_UI_STATE,
    DEFAULT_WORKFLOW_SETTINGS,
    SCHEMA_VERSION,
)
from ea_node_editor.ui.passive_style_presets import normalize_passive_style_presets


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

    def _normalize_workspace_order(self, doc: dict[str, Any], workspace_ids: set[str]) -> list[str]:
        order: list[str] = []
        for source in (
            doc.get("workspace_order"),
            self.as_dict(doc.get("metadata")).get("workspace_order"),
        ):
            for workspace_id in self.as_list(source):
                normalized_id = self._coerce_str(workspace_id)
                if normalized_id and normalized_id in workspace_ids and normalized_id not in order:
                    order.append(normalized_id)
        for workspace_id in sorted(workspace_ids):
            if workspace_id not in order:
                order.append(workspace_id)
        return order

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

        workspace_order = self._normalize_workspace_order(doc, set(normalized_workspaces))
        active_workspace_id = self._coerce_str(doc.get("active_workspace_id"))
        if active_workspace_id not in normalized_workspaces:
            active_workspace_id = workspace_order[0] if workspace_order else ""

        metadata = self.normalize_metadata(doc.get("metadata"), workspace_order)

        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": self._coerce_str(doc.get("project_id"), "proj_unknown"),
            "name": self._coerce_str(doc.get("name"), "untitled"),
            "active_workspace_id": active_workspace_id,
            "workspace_order": workspace_order,
            "workspaces": [normalized_workspaces[workspace_id] for workspace_id in workspace_order],
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
            active_view_id = sorted(views_by_id)[0]

        nodes_by_id: dict[str, dict[str, Any]] = {}
        node_specs: dict[str, NodeTypeSpec] = {}
        for node_doc in self.as_list(workspace_doc.get("nodes", [])):
            if not isinstance(node_doc, Mapping):
                continue
            node_id = self._coerce_str(node_doc.get("node_id"))
            type_id = self._coerce_str(node_doc.get("type_id"))
            if not node_id or node_id in nodes_by_id or not type_id:
                continue
            try:
                spec = self._registry.get_spec(type_id)
            except KeyError:
                continue
            raw_exposed_ports = self.as_dict(node_doc.get("exposed_ports"))
            normalized_exposed_ports = {
                port.key: self._coerce_bool(raw_exposed_ports.get(port.key, port.exposed), port.exposed)
                for port in spec.ports
            }
            nodes_by_id[node_id] = {
                "node_id": node_id,
                "type_id": type_id,
                "title": self._coerce_str(node_doc.get("title"), spec.display_name),
                "x": self._coerce_float(node_doc.get("x"), 0.0),
                "y": self._coerce_float(node_doc.get("y"), 0.0),
                "collapsed": self._coerce_bool(node_doc.get("collapsed"), False),
                "properties": self._registry.normalize_properties(type_id, self.as_dict(node_doc.get("properties"))),
                "exposed_ports": normalized_exposed_ports,
                "visual_style": self.as_dict(node_doc.get("visual_style")),
                "parent_node_id": self._coerce_str(node_doc.get("parent_node_id")) or None,
                "custom_width": self._coerce_float(node_doc["custom_width"]) if node_doc.get("custom_width") is not None else None,
                "custom_height": self._coerce_float(node_doc["custom_height"]) if node_doc.get("custom_height") is not None else None,
            }
            node_specs[node_id] = spec

        for node_id, node in nodes_by_id.items():
            parent_id = node.get("parent_node_id")
            if parent_id not in nodes_by_id or parent_id == node_id:
                node["parent_node_id"] = None

        workspace_nodes_for_ports: dict[str, NodeInstance] = {
            node_id: NodeInstance(
                node_id=node_id,
                type_id=str(node["type_id"]),
                title=str(node["title"]),
                x=float(node["x"]),
                y=float(node["y"]),
                collapsed=bool(node["collapsed"]),
                properties=dict(node["properties"]),
                exposed_ports=dict(node["exposed_ports"]),
                visual_style=dict(node["visual_style"]),
                parent_node_id=node["parent_node_id"],
            )
            for node_id, node in nodes_by_id.items()
        }

        candidate_edges: list[dict[str, Any]] = []
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
            if source_node_id not in nodes_by_id or target_node_id not in nodes_by_id:
                continue

            source_spec = node_specs[source_node_id]
            target_spec = node_specs[target_node_id]
            source_node = workspace_nodes_for_ports[source_node_id]
            target_node = workspace_nodes_for_ports[target_node_id]
            source_port = find_effective_port(
                node=source_node,
                spec=source_spec,
                workspace_nodes=workspace_nodes_for_ports,
                port_key=source_port_key,
            )
            target_port = find_effective_port(
                node=target_node,
                spec=target_spec,
                workspace_nodes=workspace_nodes_for_ports,
                port_key=target_port_key,
            )
            if source_port is None or target_port is None:
                continue
            if source_port.direction != "out" or target_port.direction != "in":
                continue
            source_exposed = bool(source_port.exposed)
            target_exposed = bool(target_port.exposed)
            if not source_exposed or not target_exposed:
                continue

            candidate_edges.append(
                {
                    "edge_id": edge_id,
                    "source_node_id": source_node_id,
                    "source_port_key": source_port_key,
                    "target_node_id": target_node_id,
                    "target_port_key": target_port_key,
                    "label": self._coerce_str(edge_doc.get("label")),
                    "visual_style": self.as_dict(edge_doc.get("visual_style")),
                }
            )

        edges_by_id: dict[str, dict[str, Any]] = {}
        seen_connections: set[tuple[str, str, str, str]] = set()
        seen_target_inputs: set[tuple[str, str]] = set()
        for edge in candidate_edges:
            edge_id = edge["edge_id"]
            if edge_id in edges_by_id:
                continue
            connection = (
                edge["source_node_id"],
                edge["source_port_key"],
                edge["target_node_id"],
                edge["target_port_key"],
            )
            if connection in seen_connections:
                continue
            target_input = (
                edge["target_node_id"],
                edge["target_port_key"],
            )
            if target_input in seen_target_inputs:
                continue
            seen_connections.add(connection)
            seen_target_inputs.add(target_input)
            edges_by_id[edge_id] = edge

        return {
            "workspace_id": workspace_id,
            "name": self._coerce_str(workspace_doc.get("name"), "Workspace"),
            "dirty": self._coerce_bool(workspace_doc.get("dirty"), False),
            "active_view_id": active_view_id,
            "views": [views_by_id[view_id] for view_id in sorted(views_by_id)],
            "nodes": [nodes_by_id[node_id] for node_id in sorted(nodes_by_id)],
            "edges": [edges_by_id[edge_id] for edge_id in sorted(edges_by_id)],
        }
