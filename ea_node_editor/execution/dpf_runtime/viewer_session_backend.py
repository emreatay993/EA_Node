from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ea_node_editor.execution.worker_runtime import resolve_runtime_artifact_store

if TYPE_CHECKING:
    from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot, RuntimeSnapshotContext
    from ea_node_editor.execution.worker_services import WorkerServices

_FIELDS_REF_OPTION_KEY = "fields_key"
_MODEL_REF_OPTION_KEY = "model_key"
_MESH_REF_OPTION_KEY = "mesh_key"
_FIELDS_REF_KEYS = ("fields", "fields_container", "field_data", "result")
_MODEL_REF_KEYS = ("model",)
_MESH_REF_KEYS = ("mesh",)


@dataclass(slots=True, frozen=True)
class ViewerSessionMaterializationRequest:
    workspace_id: str
    node_id: str
    session_id: str
    owner_scope: str
    source_refs: Mapping[str, Any]
    session_options: Mapping[str, Any]
    request_options: Mapping[str, Any]
    output_profile: str
    export_formats: tuple[str, ...] = ()
    project_path: str = ""
    runtime_snapshot: RuntimeSnapshot | None = None
    runtime_snapshot_context: RuntimeSnapshotContext | None = None


@dataclass(slots=True, frozen=True)
class ViewerSessionMaterializationResult:
    data_refs: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


class DpfViewerSessionMaterializationBackend:
    def __init__(self, worker_services: WorkerServices) -> None:
        self._worker_services = worker_services

    def materialize(
        self,
        request: ViewerSessionMaterializationRequest,
    ) -> ViewerSessionMaterializationResult:
        fields_ref = self._lookup_source_ref(
            request.source_refs,
            request_options=request.request_options,
            option_key=_FIELDS_REF_OPTION_KEY,
            default_keys=_FIELDS_REF_KEYS,
        )
        model_ref = self._lookup_source_ref(
            request.source_refs,
            request_options=request.request_options,
            option_key=_MODEL_REF_OPTION_KEY,
            default_keys=_MODEL_REF_KEYS,
        )
        mesh_ref = self._lookup_source_ref(
            request.source_refs,
            request_options=request.request_options,
            option_key=_MESH_REF_OPTION_KEY,
            default_keys=_MESH_REF_KEYS,
        )
        if fields_ref is None or model_ref is None:
            raise ValueError(
                "Viewer session is missing cached fields/model refs required for materialization."
            )

        artifact_store = None
        if request.output_profile in {"stored", "both"}:
            artifact_store = resolve_runtime_artifact_store(
                project_path=request.project_path,
                runtime_snapshot=request.runtime_snapshot,
                runtime_context=request.runtime_snapshot_context,
            )

        materialized = self._worker_services.dpf_runtime_service.materialize_viewer_dataset(
            fields_ref,
            model=model_ref,
            mesh=mesh_ref,
            output_profile=request.output_profile,
            artifact_store=artifact_store,
            artifact_key=self._artifact_key(request),
            export_formats=request.export_formats,
            temporary_root_parent=request.request_options.get("temporary_root_parent"),
            owner_scope=request.owner_scope,
        )

        data_refs: dict[str, Any] = {}
        if materialized.dataset_ref is not None:
            data_refs["dataset"] = materialized.dataset_ref
        data_refs.update(materialized.artifacts)
        return ViewerSessionMaterializationResult(
            data_refs=data_refs,
            summary=copy.deepcopy(materialized.summary),
        )

    @staticmethod
    def _artifact_key(request: ViewerSessionMaterializationRequest) -> str:
        explicit_key = str(request.request_options.get("artifact_key", "")).strip()
        if explicit_key:
            return explicit_key
        return f"{request.node_id}_{request.session_id}"

    @staticmethod
    def _lookup_source_ref(
        source_refs: Mapping[str, Any],
        *,
        request_options: Mapping[str, Any],
        option_key: str,
        default_keys: tuple[str, ...],
    ) -> Any | None:
        explicit_key = str(request_options.get(option_key, "")).strip()
        candidate_keys = (explicit_key,) if explicit_key else default_keys
        for key in candidate_keys:
            if key in source_refs:
                return source_refs[key]
        return None


__all__ = [
    "DpfViewerSessionMaterializationBackend",
    "ViewerSessionMaterializationRequest",
    "ViewerSessionMaterializationResult",
]
