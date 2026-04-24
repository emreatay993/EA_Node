from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from ea_node_editor.custom_workflows import normalize_custom_workflow_metadata
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.passive_style_normalization import normalize_passive_style_presets
from ea_node_editor.persistence.artifact_store import normalize_artifact_store_metadata
from ea_node_editor.persistence.utils import merge_defaults as merge_defaults_dict
from ea_node_editor.settings import (
    DEFAULT_WORKFLOW_SETTINGS,
    SCHEMA_VERSION,
)
from ea_node_editor.workspace.ownership import resolve_workspace_ownership


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


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    raise ValueError("Expected a JSON object.")


def _merge_defaults(values: Any, defaults: dict[str, Any]) -> dict[str, Any]:
    if values is None:
        return merge_defaults_dict({}, defaults)
    if not isinstance(values, Mapping):
        raise ValueError("Expected a JSON object.")
    return merge_defaults_dict({str(key): value for key, value in values.items()}, defaults)


def _copy_mapping_excluding(payload: Mapping[str, Any], *excluded_keys: str) -> dict[str, Any]:
    excluded = set(excluded_keys)
    return {
        str(key): copy.deepcopy(value)
        for key, value in payload.items()
        if str(key) not in excluded
    }


@dataclass(frozen=True, slots=True)
class ScriptEditorSessionState:
    visible: bool = False
    floating: bool = False

    @classmethod
    def from_mapping(cls, payload: Any) -> "ScriptEditorSessionState":
        state = _as_dict(payload)
        return cls(
            visible=_coerce_bool(state.get("visible"), False),
            floating=_coerce_bool(state.get("floating"), False),
        )

    def to_mapping(self) -> dict[str, bool]:
        return {
            "visible": self.visible,
            "floating": self.floating,
        }


@dataclass(frozen=True, slots=True)
class ProjectUiSessionMetadata:
    script_editor: ScriptEditorSessionState = field(default_factory=ScriptEditorSessionState)
    passive_style_presets: dict[str, Any] = field(default_factory=lambda: normalize_passive_style_presets(None))
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Any) -> "ProjectUiSessionMetadata":
        ui_metadata = _as_dict(payload)
        return cls(
            script_editor=ScriptEditorSessionState.from_mapping(ui_metadata.get("script_editor")),
            passive_style_presets=normalize_passive_style_presets(ui_metadata.get("passive_style_presets")),
            extra=_copy_mapping_excluding(ui_metadata, "script_editor", "passive_style_presets"),
        )

    def to_mapping(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.extra)
        payload["script_editor"] = self.script_editor.to_mapping()
        payload["passive_style_presets"] = copy.deepcopy(self.passive_style_presets)
        return payload

    def with_script_editor_state(self, *, visible: bool, floating: bool) -> "ProjectUiSessionMetadata":
        return replace(
            self,
            script_editor=ScriptEditorSessionState(
                visible=bool(visible),
                floating=bool(floating),
            ),
        )


@dataclass(frozen=True, slots=True)
class ProjectSessionMetadata:
    ui: ProjectUiSessionMetadata = field(default_factory=ProjectUiSessionMetadata)
    workflow_settings: dict[str, Any] = field(default_factory=lambda: _merge_defaults({}, DEFAULT_WORKFLOW_SETTINGS))
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Any) -> "ProjectSessionMetadata":
        metadata = _as_dict(payload)
        return cls(
            ui=ProjectUiSessionMetadata.from_mapping(metadata.get("ui")),
            workflow_settings=_merge_defaults(metadata.get("workflow_settings"), DEFAULT_WORKFLOW_SETTINGS),
            extra=_copy_mapping_excluding(metadata, "ui", "workflow_settings"),
        )

    def to_mapping(self) -> dict[str, Any]:
        payload = copy.deepcopy(self.extra)
        payload["ui"] = self.ui.to_mapping()
        payload["workflow_settings"] = copy.deepcopy(self.workflow_settings)
        return payload

    def with_script_editor_state(self, *, visible: bool, floating: bool) -> "ProjectSessionMetadata":
        return replace(
            self,
            ui=self.ui.with_script_editor_state(visible=visible, floating=floating),
        )

    def with_workflow_settings(self, workflow_settings: Any) -> "ProjectSessionMetadata":
        return replace(
            self,
            workflow_settings=_merge_defaults(workflow_settings, DEFAULT_WORKFLOW_SETTINGS),
        )


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
        if version < SCHEMA_VERSION:
            raise ValueError(
                "Unsupported schema version: "
                f"{version}. Only schema version {SCHEMA_VERSION} documents are supported."
            )
        doc["schema_version"] = SCHEMA_VERSION
        return self._normalize_document(doc)

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
        return _as_dict(value)

    @staticmethod
    def merge_defaults(values: Any, defaults: dict[str, Any]) -> dict[str, Any]:
        return _merge_defaults(values, defaults)

    @staticmethod
    def as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        raise ValueError("Expected a JSON array.")

    @staticmethod
    def _copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(dict(value))

    @staticmethod
    def normalize_metadata(source: Any, workspace_order: list[str]) -> dict[str, Any]:
        metadata = ProjectSessionMetadata.from_mapping(source).to_mapping()
        metadata["workspace_order"] = list(workspace_order)
        metadata["custom_workflows"] = normalize_custom_workflow_metadata(metadata.get("custom_workflows"))
        metadata["artifact_store"] = normalize_artifact_store_metadata(metadata.get("artifact_store"))
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
        for node_doc in self.as_list(workspace_doc.get("nodes", [])):
            if not isinstance(node_doc, Mapping):
                continue
            normalized_node = self._normalize_node_doc(node_doc)
            if normalized_node is None:
                continue
            node_id = normalized_node["node_id"]
            if node_id in nodes_by_id:
                continue
            nodes_by_id[node_id] = normalized_node

        edges_by_id: dict[str, dict[str, Any]] = {}
        for edge_doc in self.as_list(workspace_doc.get("edges", [])):
            if not isinstance(edge_doc, Mapping):
                continue
            normalized_edge = self._normalize_edge_doc(
                edge_doc,
                valid_node_ids=set(nodes_by_id),
            )
            if normalized_edge is None:
                continue
            edge_id = normalized_edge["edge_id"]
            if edge_id in edges_by_id:
                continue
            edges_by_id[edge_id] = normalized_edge

        return {
            "workspace_id": workspace_id,
            "name": self._coerce_str(workspace_doc.get("name"), "Workspace"),
            "dirty": self._coerce_bool(workspace_doc.get("dirty"), False),
            "active_view_id": active_view_id,
            "views": list(views_by_id.values()),
            "nodes": list(nodes_by_id.values()),
            "edges": list(edges_by_id.values()),
        }

    def _normalize_node_doc(self, node_doc: Mapping[str, Any]) -> dict[str, Any] | None:
        node_id = self._coerce_str(node_doc.get("node_id"))
        type_id = self._coerce_str(node_doc.get("type_id"))
        if not node_id or not type_id:
            return None
        title_default = type_id
        spec = self._registry.spec_or_none(type_id)
        if spec is not None:
            title_default = spec.display_name
        normalized = self._copy_mapping(node_doc)
        normalized["node_id"] = node_id
        normalized["type_id"] = type_id
        normalized["title"] = self._coerce_str(node_doc.get("title"), title_default)
        normalized["x"] = self._coerce_float(node_doc.get("x"), 0.0)
        normalized["y"] = self._coerce_float(node_doc.get("y"), 0.0)
        normalized["collapsed"] = self._coerce_bool(node_doc.get("collapsed"), False)
        normalized["properties"] = self.as_dict(node_doc.get("properties"))
        normalized["exposed_ports"] = {
            key: self._coerce_bool(value)
            for key, value in self.as_dict(node_doc.get("exposed_ports")).items()
            if key
        }
        port_labels = {
            key: self._coerce_str(value)
            for key, value in self.as_dict(node_doc.get("port_labels")).items()
            if key and self._coerce_str(value)
        }
        if "port_labels" in node_doc or port_labels:
            normalized["port_labels"] = port_labels
        visual_style = self.as_dict(node_doc.get("visual_style"))
        if "visual_style" in node_doc or visual_style:
            normalized["visual_style"] = visual_style
        normalized["parent_node_id"] = self._coerce_str(node_doc.get("parent_node_id")) or None
        if "custom_width" in node_doc:
            normalized["custom_width"] = (
                self._coerce_float(node_doc["custom_width"])
                if node_doc.get("custom_width") is not None
                else None
            )
        if "custom_height" in node_doc:
            normalized["custom_height"] = (
                self._coerce_float(node_doc["custom_height"])
                if node_doc.get("custom_height") is not None
                else None
            )
        return normalized

    def _normalize_edge_doc(
        self,
        edge_doc: Mapping[str, Any],
        *,
        valid_node_ids: set[str],
    ) -> dict[str, Any] | None:
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
            return None
        if source_node_id not in valid_node_ids or target_node_id not in valid_node_ids:
            return None
        normalized = self._copy_mapping(edge_doc)
        normalized["edge_id"] = edge_id
        normalized["source_node_id"] = source_node_id
        normalized["source_port_key"] = source_port_key
        normalized["target_node_id"] = target_node_id
        normalized["target_port_key"] = target_port_key
        label = self._coerce_str(edge_doc.get("label"))
        if "label" in edge_doc or label:
            normalized["label"] = label
        visual_style = self.as_dict(edge_doc.get("visual_style"))
        if "visual_style" in edge_doc or visual_style:
            normalized["visual_style"] = visual_style
        return normalized
