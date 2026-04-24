from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.graph.hierarchy import normalize_scope_path
from ea_node_editor.graph.model import (
    ProjectData,
    ViewState,
    WorkspaceData,
    edge_instance_from_mapping,
    edge_instance_to_mapping,
    node_instance_from_mapping,
    node_instance_to_mapping,
    sanitize_workspace_parent_links,
)
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.artifact_refs import (
    ManagedArtifactRef,
    StagedArtifactRef,
    parse_artifact_ref,
)
from ea_node_editor.persistence.artifact_store import normalize_artifact_store_metadata
from ea_node_editor.persistence.envelope import (
    LEGACY_RUNTIME_PERSISTENCE_KEY,
    PERSISTENCE_ENVELOPE_KEY,
    ProjectDocumentFlavor,
    ProjectPersistenceEnvelope,
    ProjectPersistenceWorkspaceEnvelope,
    install_workspace_persistence_envelope,
)
from ea_node_editor.persistence.migration import JsonProjectMigration
from ea_node_editor.persistence.overlay import MISSING_ADDON_PLACEHOLDER_KEY, with_missing_addon_placeholder
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.workspace.ownership import resolve_workspace_ownership, sync_project_workspace_ownership

_COMMENT_BACKDROP_RUNTIME_MEMBERSHIP_KEYS = (
    "owner_backdrop_id",
    "backdrop_depth",
    "member_node_ids",
    "member_backdrop_ids",
    "contained_node_ids",
    "contained_backdrop_ids",
)
_VIEW_FILTER_STATE_METADATA_KEY = "port_locking_view_state"


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


def _view_filter_state_from_metadata(payload: Any) -> dict[str, dict[str, dict[str, bool]]]:
    if not isinstance(payload, Mapping):
        return {}
    workspace_state: dict[str, dict[str, dict[str, bool]]] = {}
    for raw_workspace_id, raw_workspace_payload in payload.items():
        workspace_id = str(raw_workspace_id).strip()
        if not workspace_id or not isinstance(raw_workspace_payload, Mapping):
            continue
        view_state: dict[str, dict[str, bool]] = {}
        for raw_view_id, raw_view_payload in raw_workspace_payload.items():
            view_id = str(raw_view_id).strip()
            if not view_id or not isinstance(raw_view_payload, Mapping):
                continue
            hide_locked_ports = _coerce_bool(raw_view_payload.get("hide_locked_ports"), False)
            hide_optional_ports = _coerce_bool(raw_view_payload.get("hide_optional_ports"), False)
            if not hide_locked_ports and not hide_optional_ports:
                continue
            view_state[view_id] = {
                "hide_locked_ports": hide_locked_ports,
                "hide_optional_ports": hide_optional_ports,
            }
        if view_state:
            workspace_state[workspace_id] = view_state
    return workspace_state


def _reject_runtime_persistence_metadata(metadata: Mapping[str, Any]) -> None:
    if LEGACY_RUNTIME_PERSISTENCE_KEY in metadata:
        raise ValueError(
            "Legacy runtime persistence metadata is not supported. "
            "Persist the current workspace graph shape instead."
        )
    if PERSISTENCE_ENVELOPE_KEY in metadata:
        ProjectPersistenceEnvelope.from_metadata_value(metadata.get(PERSISTENCE_ENVELOPE_KEY))


@dataclass(frozen=True, slots=True)
class ProjectArtifactReferenceSet:
    managed_ids: frozenset[str]
    staged_ids: frozenset[str]


def collect_project_artifact_references(payload: Any) -> ProjectArtifactReferenceSet:
    managed_ids: set[str] = set()
    staged_ids: set[str] = set()
    _collect_project_artifact_references(payload, managed_ids=managed_ids, staged_ids=staged_ids)
    return ProjectArtifactReferenceSet(
        managed_ids=frozenset(managed_ids),
        staged_ids=frozenset(staged_ids),
    )


def _collect_project_artifact_references(
    payload: Any,
    *,
    managed_ids: set[str],
    staged_ids: set[str],
) -> None:
    if isinstance(payload, str):
        parsed = parse_artifact_ref(payload)
        if isinstance(parsed, ManagedArtifactRef):
            managed_ids.add(parsed.artifact_id)
        elif isinstance(parsed, StagedArtifactRef):
            staged_ids.add(parsed.artifact_id)
        return
    if isinstance(payload, Mapping):
        for value in payload.values():
            _collect_project_artifact_references(value, managed_ids=managed_ids, staged_ids=staged_ids)
        return
    if isinstance(payload, list | tuple | set | frozenset):
        for value in payload:
            _collect_project_artifact_references(value, managed_ids=managed_ids, staged_ids=staged_ids)


def rewrite_project_artifact_refs(payload: Any, replacements: Mapping[str, str]) -> Any:
    replacement_map = {
        str(source): str(target)
        for source, target in replacements.items()
        if str(source).strip() and str(target).strip()
    }
    if not replacement_map:
        return copy.deepcopy(payload)
    return _rewrite_project_artifact_refs(payload, replacements=replacement_map)


def _rewrite_project_artifact_refs(payload: Any, *, replacements: Mapping[str, str]) -> Any:
    if isinstance(payload, str):
        return replacements.get(payload, payload)
    if isinstance(payload, Mapping):
        return {
            copy.deepcopy(key): _rewrite_project_artifact_refs(value, replacements=replacements)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_rewrite_project_artifact_refs(value, replacements=replacements) for value in payload]
    if isinstance(payload, tuple):
        return tuple(_rewrite_project_artifact_refs(value, replacements=replacements) for value in payload)
    if isinstance(payload, set):
        return {_rewrite_project_artifact_refs(value, replacements=replacements) for value in payload}
    if isinstance(payload, frozenset):
        return frozenset(_rewrite_project_artifact_refs(value, replacements=replacements) for value in payload)
    return copy.deepcopy(payload)


class JsonProjectCodec:
    def __init__(self, registry: NodeRegistry | None = None) -> None:
        self._registry = registry

    @staticmethod
    def _copy_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(dict(mapping))

    @classmethod
    def _copy_node_mapping(cls, mapping: Mapping[str, Any]) -> dict[str, Any]:
        copied = cls._copy_mapping(mapping)
        for key in _COMMENT_BACKDROP_RUNTIME_MEMBERSHIP_KEYS:
            copied.pop(key, None)
        return copied

    def to_document(self, project: ProjectData) -> dict[str, Any]:
        return self._encode_document(project, flavor=ProjectDocumentFlavor.RUNTIME)

    def to_persistent_document(self, project: ProjectData) -> dict[str, Any]:
        return self._encode_document(project, flavor=ProjectDocumentFlavor.AUTHORED)

    def _encode_document(
        self,
        project: ProjectData,
        *,
        flavor: ProjectDocumentFlavor,
    ) -> dict[str, Any]:
        metadata = project.metadata if isinstance(project.metadata, Mapping) else {}
        ownership = resolve_workspace_ownership(
            project.workspaces,
            order_sources=(metadata.get("workspace_order"),),
            active_workspace_id=project.active_workspace_id,
        )
        metadata = JsonProjectMigration.normalize_metadata(metadata, ownership.workspace_order)
        _reject_runtime_persistence_metadata(metadata)
        metadata["artifact_store"] = normalize_artifact_store_metadata(metadata.get("artifact_store"))
        metadata.pop(PERSISTENCE_ENVELOPE_KEY, None)
        metadata.pop(_VIEW_FILTER_STATE_METADATA_KEY, None)
        persistence_metadata = None
        if flavor is ProjectDocumentFlavor.RUNTIME:
            persistence_metadata = ProjectPersistenceEnvelope.from_workspaces(
                project.workspaces,
                workspace_order=ownership.workspace_order,
            ).metadata_value()

        workspaces: list[dict[str, Any]] = []
        view_filter_state: dict[str, dict[str, dict[str, bool]]] = {}
        for workspace_id in ownership.workspace_order:
            workspace = project.workspaces[workspace_id]
            workspace.ensure_default_view()
            active_view_id = workspace.active_view_id
            if active_view_id not in workspace.views:
                active_view_id = next(iter(workspace.views))
            workspace_doc = {
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
                        "hide_locked_ports": view.hide_locked_ports,
                        "hide_optional_ports": view.hide_optional_ports,
                    }
                    for view in workspace.views.values()
                ],
            }
            if flavor is ProjectDocumentFlavor.RUNTIME:
                workspace_doc["document_fields"] = {
                    key: copy.deepcopy(value)
                    for key, value in workspace_doc.items()
                    if key not in {"nodes", "edges", "document_fields"}
                }
            workspace_view_filter_state = {
                view.view_id: {
                    "hide_locked_ports": view.hide_locked_ports,
                    "hide_optional_ports": view.hide_optional_ports,
                }
                for view in workspace.views.values()
                if view.hide_locked_ports or view.hide_optional_ports
            }
            if workspace_view_filter_state:
                view_filter_state[workspace.workspace_id] = workspace_view_filter_state
            if flavor is ProjectDocumentFlavor.AUTHORED:
                workspace_doc["nodes"] = self._workspace_authored_node_docs(workspace)
                workspace_doc["edges"] = self._workspace_authored_edge_docs(workspace)
            else:
                workspace_doc["nodes"] = self._workspace_runtime_node_docs(workspace)
                workspace_doc["edges"] = self._workspace_runtime_edge_docs(workspace)
            workspaces.append(workspace_doc)
        if view_filter_state:
            metadata[_VIEW_FILTER_STATE_METADATA_KEY] = copy.deepcopy(view_filter_state)
        if persistence_metadata is not None:
            metadata[PERSISTENCE_ENVELOPE_KEY] = persistence_metadata
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": project.project_id,
            "name": project.name,
            "active_workspace_id": ownership.active_workspace_id,
            "workspace_order": ownership.workspace_order,
            "workspaces": workspaces,
            "metadata": metadata,
        }

    def from_document(self, payload: dict[str, Any]) -> ProjectData:
        persistence_envelope = ProjectPersistenceEnvelope.from_document(payload)
        deferred_rebind_edge_docs: dict[str, list[dict[str, Any]]] = {}
        project = ProjectData(
            project_id=payload.get("project_id", "proj_unknown"),
            name=payload.get("name", "untitled"),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
            active_workspace_id=payload.get("active_workspace_id", ""),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata"), Mapping) else {},
        )
        _reject_runtime_persistence_metadata(project.metadata)
        project.metadata.pop(PERSISTENCE_ENVELOPE_KEY, None)
        view_filter_state = _view_filter_state_from_metadata(project.metadata.pop(_VIEW_FILTER_STATE_METADATA_KEY, None))
        for ws_doc in payload.get("workspaces", []):
            if not isinstance(ws_doc, Mapping):
                continue
            workspace_id = str(ws_doc.get("workspace_id", "")).strip()
            workspace_name = str(ws_doc.get("name", "")).strip()
            if not workspace_id or not workspace_name:
                continue
            workspace = WorkspaceData(
                workspace_id=workspace_id,
                name=workspace_name,
                active_view_id=ws_doc.get("active_view_id", ""),
                dirty=bool(ws_doc.get("dirty", False)),
            )
            for view_doc in ws_doc.get("views", []):
                if not isinstance(view_doc, Mapping):
                    continue
                view_id = view_doc.get("view_id")
                if not view_id:
                    continue
                view = ViewState(
                    view_id=str(view_id),
                    name=view_doc.get("name", "V"),
                    zoom=float(view_doc.get("zoom", 1.0)),
                    pan_x=float(view_doc.get("pan_x", 0.0)),
                    pan_y=float(view_doc.get("pan_y", 0.0)),
                    scope_path=[
                        str(item).strip()
                        for item in view_doc.get("scope_path", [])
                        if str(item).strip()
                    ],
                    hide_locked_ports=_coerce_bool(view_doc.get("hide_locked_ports"), False),
                    hide_optional_ports=_coerce_bool(view_doc.get("hide_optional_ports"), False),
                )
                persisted_view_state = view_filter_state.get(workspace.workspace_id, {}).get(view.view_id)
                if isinstance(persisted_view_state, Mapping):
                    view.hide_locked_ports = _coerce_bool(
                        persisted_view_state.get("hide_locked_ports"),
                        view.hide_locked_ports,
                    )
                    view.hide_optional_ports = _coerce_bool(
                        persisted_view_state.get("hide_optional_ports"),
                        view.hide_optional_ports,
                    )
                workspace.views[view.view_id] = view
            workspace.ensure_default_view()
            if workspace.active_view_id not in workspace.views:
                workspace.active_view_id = next(iter(workspace.views))

            workspace_envelope = persistence_envelope.workspace_envelope(workspace_id)
            unresolved_node_docs = copy.deepcopy(workspace_envelope.unresolved_node_docs)
            unresolved_edge_docs = copy.deepcopy(workspace_envelope.unresolved_edge_docs)
            authored_node_overrides = copy.deepcopy(workspace_envelope.authored_node_overrides)
            formerly_unresolved_node_ids: set[str] = set()

            for node_doc in ws_doc.get("nodes", []):
                if not isinstance(node_doc, Mapping):
                    continue
                if self._node_doc_is_unresolved(node_doc):
                    node_id = str(node_doc.get("node_id", "")).strip()
                    if node_id and node_id not in workspace.nodes and node_id not in unresolved_node_docs:
                        unresolved_node_docs[node_id] = with_missing_addon_placeholder(
                            self._copy_node_mapping(node_doc)
                        )
                    continue
                node_id = str(node_doc.get("node_id", "")).strip()
                if node_id and MISSING_ADDON_PLACEHOLDER_KEY in node_doc:
                    formerly_unresolved_node_ids.add(node_id)
                self._decode_workspace_node_doc(workspace, node_doc=node_doc)
            valid_node_ids = set(workspace.nodes)
            unresolved_node_ids = set(unresolved_node_docs)
            deferred_workspace_edges: list[dict[str, Any]] = []
            for edge_doc in ws_doc.get("edges", []):
                if not isinstance(edge_doc, Mapping):
                    continue
                edge_id = str(edge_doc.get("edge_id", "")).strip()
                source_node_id = str(edge_doc.get("source_node_id", "")).strip()
                target_node_id = str(edge_doc.get("target_node_id", "")).strip()
                if (
                    edge_id
                    and edge_id not in unresolved_edge_docs
                    and (
                        source_node_id in unresolved_node_ids
                        or target_node_id in unresolved_node_ids
                    )
                ):
                    unresolved_edge_docs[edge_id] = copy.deepcopy(dict(edge_doc))
                    continue
                if source_node_id in formerly_unresolved_node_ids or target_node_id in formerly_unresolved_node_ids:
                    deferred_workspace_edges.append(copy.deepcopy(dict(edge_doc)))
                    continue
                self._decode_workspace_edge_doc(
                    workspace,
                    edge_doc=edge_doc,
                    valid_node_ids=valid_node_ids,
                )
            for node_id, node in workspace.nodes.items():
                parent_node_id = str(node.parent_node_id or "").strip()
                if parent_node_id and parent_node_id not in workspace.nodes and parent_node_id in unresolved_node_docs:
                    node_overrides = dict(authored_node_overrides.get(node_id, {}))
                    node_overrides["parent_node_id"] = parent_node_id
                    authored_node_overrides[node_id] = node_overrides
            sanitize_workspace_parent_links(workspace)
            install_workspace_persistence_envelope(
                workspace,
                ProjectPersistenceWorkspaceEnvelope(
                    unresolved_node_docs=unresolved_node_docs,
                    unresolved_edge_docs=unresolved_edge_docs,
                    authored_node_overrides=authored_node_overrides,
                ),
            )
            if deferred_workspace_edges:
                deferred_rebind_edge_docs[workspace.workspace_id] = deferred_workspace_edges
            project.workspaces[workspace.workspace_id] = workspace

        project.ensure_default_workspace()
        ownership = sync_project_workspace_ownership(
            project,
            order_sources=(payload.get("workspace_order"),),
        )
        project.metadata = JsonProjectMigration.normalize_metadata(project.metadata, ownership.workspace_order)
        project.metadata["artifact_store"] = normalize_artifact_store_metadata(project.metadata.get("artifact_store"))
        if self._registry is not None:
            normalize_project_for_registry(project, self._registry)
            self._restore_deferred_rebind_edges(project, deferred_rebind_edge_docs)
        for workspace in project.workspaces.values():
            for view in workspace.views.values():
                view.scope_path = list(normalize_scope_path(workspace, view.scope_path))
        return project

    def _workspace_runtime_node_docs(self, workspace: WorkspaceData) -> list[dict[str, Any]]:
        return [
            self._copy_node_mapping(node_instance_to_mapping(node))
            for node in sorted(workspace.nodes.values(), key=lambda item: item.node_id)
        ]

    def _workspace_runtime_edge_docs(self, workspace: WorkspaceData) -> list[dict[str, Any]]:
        return [
            edge_instance_to_mapping(edge)
            for edge in sorted(workspace.edges.values(), key=lambda item: item.edge_id)
        ]

    def _workspace_authored_node_docs(self, workspace: WorkspaceData) -> list[dict[str, Any]]:
        persistence_state = ProjectPersistenceWorkspaceEnvelope.from_workspace(workspace)
        live_docs: dict[str, dict[str, Any]] = {}
        for node in sorted(workspace.nodes.values(), key=lambda item: item.node_id):
            node_doc = self._copy_node_mapping(node_instance_to_mapping(node))
            overrides = persistence_state.authored_node_overrides.get(node.node_id)
            if isinstance(overrides, Mapping):
                node_doc.update(copy.deepcopy(dict(overrides)))
            live_docs[node.node_id] = node_doc

        for node_id, node_doc in sorted(persistence_state.unresolved_node_docs.items()):
            if node_id not in live_docs:
                live_docs[node_id] = self._copy_node_mapping(node_doc)
        return [live_docs[node_id] for node_id in sorted(live_docs)]

    def _workspace_authored_edge_docs(self, workspace: WorkspaceData) -> list[dict[str, Any]]:
        persistence_state = ProjectPersistenceWorkspaceEnvelope.from_workspace(workspace)
        live_docs = {
            edge.edge_id: edge_instance_to_mapping(edge)
            for edge in sorted(workspace.edges.values(), key=lambda item: item.edge_id)
        }
        for edge_id, edge_doc in sorted(persistence_state.unresolved_edge_docs.items()):
            if edge_id not in live_docs:
                live_docs[edge_id] = copy.deepcopy(edge_doc)
        return [live_docs[edge_id] for edge_id in sorted(live_docs)]

    def _restore_deferred_rebind_edges(
        self,
        project: ProjectData,
        deferred_edges_by_workspace: Mapping[str, list[dict[str, Any]]],
    ) -> None:
        for workspace_id, edge_docs in deferred_edges_by_workspace.items():
            workspace = project.workspaces.get(workspace_id)
            if workspace is None:
                continue
            valid_node_ids = set(workspace.nodes)
            for edge_doc in edge_docs:
                edge_id = str(edge_doc.get("edge_id", "")).strip()
                if not edge_id or edge_id in workspace.edges:
                    continue
                source_node_id = str(edge_doc.get("source_node_id", "")).strip()
                target_node_id = str(edge_doc.get("target_node_id", "")).strip()
                if source_node_id not in valid_node_ids or target_node_id not in valid_node_ids:
                    continue
                edge = edge_instance_from_mapping(edge_doc)
                if edge is not None:
                    workspace.edges[edge.edge_id] = edge

    def _node_doc_is_unresolved(self, node_doc: Mapping[str, Any]) -> bool:
        node_id = str(node_doc.get("node_id", "")).strip()
        type_id = str(node_doc.get("type_id", "")).strip()
        if not node_id or not type_id or self._registry is None:
            return False
        return self._registry.spec_or_none(type_id) is None

    def _decode_workspace_node_doc(
        self,
        workspace: WorkspaceData,
        *,
        node_doc: Mapping[str, Any],
    ) -> None:
        node_id = str(node_doc.get("node_id", "")).strip()
        type_id = str(node_doc.get("type_id", "")).strip()
        if not node_id or not type_id:
            return
        if node_id in workspace.nodes:
            return
        sanitized_node_doc = self._copy_node_mapping(node_doc)
        if self._registry is not None:
            spec = self._registry.spec_or_none(type_id)
            if spec is None:
                return
            if not str(sanitized_node_doc.get("title", "")).strip():
                sanitized_node_doc["title"] = spec.display_name
        node = node_instance_from_mapping(sanitized_node_doc)
        if node is None:
            return
        workspace.nodes[node.node_id] = node

    def _decode_workspace_edge_doc(
        self,
        workspace: WorkspaceData,
        *,
        edge_doc: Mapping[str, Any],
        valid_node_ids: set[str],
    ) -> None:
        edge_id = str(edge_doc.get("edge_id", "")).strip()
        source_node_id = str(edge_doc.get("source_node_id", "")).strip()
        source_port_key = str(edge_doc.get("source_port_key", "")).strip()
        target_node_id = str(edge_doc.get("target_node_id", "")).strip()
        target_port_key = str(edge_doc.get("target_port_key", "")).strip()
        if not edge_id or not source_node_id or not target_node_id:
            return
        if edge_id in workspace.edges:
            return
        if source_node_id not in valid_node_ids or target_node_id not in valid_node_ids:
            return
        source_node = workspace.nodes.get(source_node_id)
        target_node = workspace.nodes.get(target_node_id)
        if source_node is not None and not source_node.exposed_ports.get(source_port_key, True):
            return
        if target_node is not None and not target_node.exposed_ports.get(target_port_key, True):
            return
        edge = edge_instance_from_mapping(edge_doc)
        if edge is None:
            return
        workspace.edges[edge.edge_id] = edge
