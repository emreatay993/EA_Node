from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ea_node_editor.custom_workflows import normalize_custom_workflow_metadata
from ea_node_editor.execution.runtime_dto import RuntimeWorkspace
from ea_node_editor.passive_style_normalization import normalize_passive_style_presets
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.settings import DEFAULT_WORKFLOW_SETTINGS, SCHEMA_VERSION
from ea_node_editor.workspace.ownership import resolve_workspace_ownership

if TYPE_CHECKING:
    from ea_node_editor.graph.model import ProjectData, WorkspaceData

_PERSISTENCE_ENVELOPE_KEY = "_persistence_envelope"
_LEGACY_RUNTIME_PERSISTENCE_KEY = "_runtime_unresolved_workspaces"
_RUNTIME_DOCUMENT_FLAVOR = "runtime"


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


def _as_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value for key, value in value.items()}


def _merge_defaults(values: Any, defaults: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(defaults)
    if not isinstance(values, Mapping):
        return merged
    for key, value in values.items():
        normalized_key = str(key)
        if normalized_key in merged and isinstance(merged[normalized_key], dict) and isinstance(value, Mapping):
            merged[normalized_key] = _merge_defaults(value, merged[normalized_key])
        else:
            merged[normalized_key] = copy.deepcopy(value)
    return merged


def _copy_mapping_excluding(payload: Mapping[str, Any], *excluded_keys: str) -> dict[str, Any]:
    excluded = set(excluded_keys)
    return {
        str(key): copy.deepcopy(value)
        for key, value in payload.items()
        if str(key) not in excluded
    }


def _normalize_project_ui_metadata(payload: Any) -> dict[str, Any]:
    ui_metadata = _as_mapping(payload)
    normalized = _copy_mapping_excluding(ui_metadata, "script_editor", "passive_style_presets")
    normalized["script_editor"] = {
        "visible": _coerce_bool(_as_mapping(ui_metadata.get("script_editor")).get("visible"), False),
        "floating": _coerce_bool(_as_mapping(ui_metadata.get("script_editor")).get("floating"), False),
    }
    normalized["passive_style_presets"] = normalize_passive_style_presets(ui_metadata.get("passive_style_presets"))
    return normalized


def normalize_runtime_project_metadata(source: Any, workspace_order: tuple[str, ...]) -> dict[str, Any]:
    metadata = _as_mapping(source)
    normalized = _copy_mapping_excluding(metadata, "ui", "workflow_settings")
    normalized["ui"] = _normalize_project_ui_metadata(metadata.get("ui"))
    normalized["workflow_settings"] = _merge_defaults(
        metadata.get("workflow_settings"),
        DEFAULT_WORKFLOW_SETTINGS,
    )
    normalized["workspace_order"] = list(workspace_order)
    normalized["custom_workflows"] = normalize_custom_workflow_metadata(normalized.get("custom_workflows"))
    normalized["artifact_store"] = ProjectArtifactStore(
        project_path=None,
        metadata=normalized.get("artifact_store"),
    ).metadata
    normalized.pop(_PERSISTENCE_ENVELOPE_KEY, None)
    normalized.pop(_LEGACY_RUNTIME_PERSISTENCE_KEY, None)
    return normalized


def _copy_overlay_docs(payload: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return {}
    copied: dict[str, dict[str, Any]] = {}
    for raw_key, raw_doc in payload.items():
        key = str(raw_key).strip()
        if not key or key in copied or not isinstance(raw_doc, Mapping):
            continue
        copied[key] = copy.deepcopy(dict(raw_doc))
    return copied


def _workspace_runtime_persistence_envelope(workspace: "WorkspaceData") -> dict[str, Any] | None:
    unresolved_node_docs = _copy_overlay_docs(workspace.unresolved_node_docs)
    unresolved_edge_docs = _copy_overlay_docs(workspace.unresolved_edge_docs)
    authored_node_overrides = _copy_overlay_docs(workspace.authored_node_overrides)

    envelope: dict[str, Any] = {}
    if unresolved_node_docs:
        envelope["unresolved_nodes"] = [
            copy.deepcopy(unresolved_node_docs[node_id])
            for node_id in sorted(unresolved_node_docs)
        ]
    if unresolved_edge_docs:
        envelope["unresolved_edges"] = [
            copy.deepcopy(unresolved_edge_docs[edge_id])
            for edge_id in sorted(unresolved_edge_docs)
        ]
    if authored_node_overrides:
        envelope["authored_node_overrides"] = {
            node_id: copy.deepcopy(authored_node_overrides[node_id])
            for node_id in sorted(authored_node_overrides)
            if authored_node_overrides[node_id]
        }
    return envelope or None


def _project_runtime_persistence_metadata(workspace_envelopes: Mapping[str, dict[str, Any]]) -> dict[str, Any] | None:
    workspace_payload = {
        workspace_id: copy.deepcopy(envelope)
        for workspace_id, envelope in sorted(workspace_envelopes.items())
        if str(workspace_id).strip() and envelope
    }
    if not workspace_payload:
        return None
    return {
        "document_flavor": _RUNTIME_DOCUMENT_FLAVOR,
        "workspaces": workspace_payload,
    }


@dataclass(frozen=True, slots=True)
class RuntimeSnapshotAssembly:
    schema_version: int
    active_workspace_id: str
    workspace_order: tuple[str, ...]
    metadata: dict[str, Any]
    workspaces: tuple[RuntimeWorkspace, ...]

    @classmethod
    def from_project_data(cls, project: "ProjectData") -> "RuntimeSnapshotAssembly":
        metadata = project.metadata if isinstance(project.metadata, Mapping) else {}
        ownership = resolve_workspace_ownership(
            project.workspaces,
            order_sources=(metadata.get("workspace_order"),),
            active_workspace_id=project.active_workspace_id,
        )
        workspace_order = tuple(ownership.workspace_order)
        runtime_metadata = normalize_runtime_project_metadata(metadata, workspace_order)

        workspaces: list[RuntimeWorkspace] = []
        workspace_envelopes: dict[str, dict[str, Any]] = {}
        for workspace_id in workspace_order:
            workspace = project.workspaces[workspace_id]
            workspaces.append(RuntimeWorkspace.from_workspace_data(workspace))
            envelope = _workspace_runtime_persistence_envelope(workspace)
            if envelope is not None:
                workspace_envelopes[workspace.workspace_id] = envelope

        persistence_metadata = _project_runtime_persistence_metadata(workspace_envelopes)
        if persistence_metadata is not None:
            runtime_metadata[_PERSISTENCE_ENVELOPE_KEY] = persistence_metadata

        return cls(
            schema_version=SCHEMA_VERSION,
            active_workspace_id=ownership.active_workspace_id,
            workspace_order=workspace_order,
            metadata=runtime_metadata,
            workspaces=tuple(workspaces),
        )


__all__ = ["RuntimeSnapshotAssembly", "normalize_runtime_project_metadata"]
