from __future__ import annotations

import copy
import hashlib
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ea_node_editor.execution.worker_runtime import resolve_runtime_artifact_store

if TYPE_CHECKING:
    from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot, RuntimeSnapshotContext
    from ea_node_editor.execution.worker_services import WorkerServices

_FIELDS_REF_OPTION_KEY = "fields_key"
_MODEL_REF_OPTION_KEY = "model_key"
_MESH_REF_OPTION_KEY = "mesh_key"
_FIELDS_REF_KEYS = ("fields_container", "fields", "field")
_MODEL_REF_KEYS = ("model",)
_MESH_REF_KEYS = ("mesh",)


@dataclass(slots=True)
class _SessionTransportCacheEntry:
    workspace_id: str
    session_id: str
    session_root: Path
    source_signature: str
    transport_revision: int
    transport: dict[str, Any]


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
    camera_state: Mapping[str, Any] = field(default_factory=dict)
    export_formats: tuple[str, ...] = ()
    project_path: str = ""
    runtime_snapshot: RuntimeSnapshot | None = None
    runtime_snapshot_context: RuntimeSnapshotContext | None = None


@dataclass(slots=True, frozen=True)
class ViewerSessionMaterializationResult:
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


class DpfViewerSessionMaterializationBackend:
    def __init__(self, worker_services: WorkerServices) -> None:
        self._worker_services = worker_services
        self._transport_cache: dict[tuple[str, str], _SessionTransportCacheEntry] = {}

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
            camera_state=request.camera_state,
            artifact_store=artifact_store,
            artifact_key=self._artifact_key(request),
            export_formats=request.export_formats,
            temporary_root_parent=request.request_options.get("temporary_root_parent"),
            owner_scope=request.owner_scope,
        )
        transport, transport_revision = self._resolve_transport_bundle(
            request,
            fields_ref=fields_ref,
            model_ref=model_ref,
            mesh_ref=mesh_ref,
        )
        live_open_status = "ready" if self._transport_is_live(transport) else "blocked"
        live_open_blocker: dict[str, Any] = {}
        if live_open_status != "ready":
            live_open_blocker = {
                "code": "rerun_required",
                "reason": "Live viewer transport is unavailable and requires rerun.",
                "rerun_required": True,
            }

        data_refs: dict[str, Any] = {}
        if materialized.dataset_ref is not None:
            data_refs["dataset"] = materialized.dataset_ref
        data_refs.update(materialized.artifacts)
        summary = copy.deepcopy(materialized.summary)
        summary["transport_kind"] = str(transport.get("kind", "")).strip()
        summary["transport_manifest_path"] = str(transport.get("manifest_path", "")).strip()
        summary["transport_entry_path"] = str(transport.get("entry_path", "")).strip()
        summary["transport_revision"] = transport_revision
        return ViewerSessionMaterializationResult(
            data_refs=data_refs,
            transport=transport,
            transport_revision=transport_revision,
            live_open_status=live_open_status,
            live_open_blocker=live_open_blocker,
            summary=summary,
        )

    def release_session_transport(self, *, workspace_id: str, session_id: str) -> None:
        cache_entry = self._transport_cache.pop((str(workspace_id).strip(), str(session_id).strip()), None)
        if cache_entry is None:
            return
        shutil.rmtree(cache_entry.session_root, ignore_errors=True)

    def release_workspace_transport(self, *, workspace_id: str) -> None:
        normalized_workspace_id = str(workspace_id).strip()
        stale_keys = [
            cache_key
            for cache_key in self._transport_cache
            if cache_key[0] == normalized_workspace_id
        ]
        for cache_key in stale_keys:
            cache_entry = self._transport_cache.pop(cache_key, None)
            if cache_entry is None:
                continue
            shutil.rmtree(cache_entry.session_root, ignore_errors=True)

    def reset(self) -> None:
        cache_entries = list(self._transport_cache.values())
        self._transport_cache.clear()
        for cache_entry in cache_entries:
            shutil.rmtree(cache_entry.session_root, ignore_errors=True)

    def _resolve_transport_bundle(
        self,
        request: ViewerSessionMaterializationRequest,
        *,
        fields_ref: Any,
        model_ref: Any,
        mesh_ref: Any,
    ) -> tuple[dict[str, Any], int]:
        cache_key = (request.workspace_id, request.session_id)
        force_recompute = bool(request.request_options.get("force_recompute", False))
        source_signature = self._transport_source_signature(
            fields_ref=fields_ref,
            model_ref=model_ref,
            mesh_ref=mesh_ref,
        )
        cached = self._transport_cache.get(cache_key)
        if (
            cached is not None
            and not force_recompute
            and cached.source_signature == source_signature
            and self._transport_is_live(cached.transport)
        ):
            return copy.deepcopy(cached.transport), cached.transport_revision

        if cached is None:
            session_root = Path(
                tempfile.mkdtemp(
                    prefix=f"ea_dpf_viewer_transport_{self._session_temp_token(request)}_"
                )
            )
            next_revision = 1
        else:
            session_root = cached.session_root
            next_revision = cached.transport_revision + 1
            shutil.rmtree(session_root, ignore_errors=True)
            session_root.mkdir(parents=True, exist_ok=True)

        bundle_root = session_root / f"transport_r{next_revision:04d}"
        try:
            transport = self._worker_services.dpf_runtime_service.export_viewer_transport_bundle(
                fields_ref,
                model=model_ref,
                mesh=mesh_ref,
                bundle_root=bundle_root,
                workspace_id=request.workspace_id,
                session_id=request.session_id,
                transport_revision=next_revision,
            )
        except Exception as exc:  # noqa: BLE001
            transport = self._build_blocked_transport_bundle(
                request=request,
                bundle_root=bundle_root,
                transport_revision=next_revision,
                source_signature=source_signature,
                error=exc,
            )
        transport["transport_revision"] = int(next_revision)
        transport["source_signature"] = source_signature
        self._transport_cache[cache_key] = _SessionTransportCacheEntry(
            workspace_id=request.workspace_id,
            session_id=request.session_id,
            session_root=session_root,
            source_signature=source_signature,
            transport_revision=next_revision,
            transport=copy.deepcopy(transport),
        )
        return copy.deepcopy(transport), next_revision

    @staticmethod
    def _artifact_key(request: ViewerSessionMaterializationRequest) -> str:
        explicit_key = str(request.request_options.get("artifact_key", "")).strip()
        if explicit_key:
            return explicit_key
        return f"{request.node_id}_{request.session_id}"

    @staticmethod
    def _session_temp_token(request: ViewerSessionMaterializationRequest) -> str:
        digest = hashlib.sha1(
            f"{request.workspace_id}:{request.session_id}".encode("utf-8")
        ).hexdigest()
        return digest[:16]

    @staticmethod
    def _transport_source_signature(*, fields_ref: Any, model_ref: Any, mesh_ref: Any) -> str:
        fields_handle_id = str(getattr(fields_ref, "handle_id", "")).strip()
        model_handle_id = str(getattr(model_ref, "handle_id", "")).strip()
        mesh_handle_id = str(getattr(mesh_ref, "handle_id", "")).strip() if mesh_ref is not None else ""
        return hashlib.sha1(
            f"fields={fields_handle_id};model={model_handle_id};mesh={mesh_handle_id}".encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _transport_is_live(transport: Mapping[str, Any]) -> bool:
        manifest_path = str(transport.get("manifest_path", "")).strip()
        entry_path = str(transport.get("entry_path", "")).strip()
        if not manifest_path or not entry_path:
            return False
        return Path(manifest_path).is_file() and Path(entry_path).is_file()

    @staticmethod
    def _build_blocked_transport_bundle(
        *,
        request: ViewerSessionMaterializationRequest,
        bundle_root: Path,
        transport_revision: int,
        source_signature: str,
        error: Exception,
    ) -> dict[str, Any]:
        error_message = str(error).strip() or type(error).__name__
        return {
            "kind": "dpf_transport_bundle",
            "version": 1,
            "schema": "ea.dpf.viewer_transport_bundle.v1",
            "bundle_root": str(bundle_root),
            "manifest_path": "",
            "entry_file": "",
            "entry_path": "",
            "files": [],
            "metadata": {
                "workspace_id": str(request.workspace_id).strip(),
                "session_id": str(request.session_id).strip(),
                "transport_revision": int(transport_revision),
                "source_signature": source_signature,
                "transport_state": "blocked",
                "export_error": error_message,
            },
            "status": "blocked",
        }

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
