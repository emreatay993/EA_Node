from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.execution.protocol import (
    CloseViewerSessionCommand,
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    UpdateViewerSessionCommand,
    ViewerDataMaterializedEvent,
    ViewerSessionClosedEvent,
    ViewerSessionFailedEvent,
    ViewerSessionOpenedEvent,
    ViewerSessionUpdatedEvent,
)
from ea_node_editor.execution.viewer_backend import ViewerBackendMaterializationRequest
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.nodes.types import RuntimeArtifactRef, coerce_runtime_handle_ref

if TYPE_CHECKING:
    from ea_node_editor.execution.protocol import WorkerEvent, WorkerCommand
    from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot, RuntimeSnapshotContext
    from ea_node_editor.execution.worker_services import WorkerServices

_DEFAULT_OUTPUT_PROFILE = "memory"
_SESSION_ID_PREFIX = "viewer_session_"
_SESSION_INVALIDATION_REASON_RERUN = "workspace_rerun"
_MATERIALIZED_DATA_KEYS = frozenset({"dataset", "preview", "csv", "png", "vtu", "vtm"})
_MATERIALIZE_TRANSIENT_OPTION_KEYS = frozenset({"temporary_root_parent", "force_recompute"})
_CLOSE_TRANSIENT_OPTION_KEYS = frozenset({"reason", "release_handles"})


def _copy_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): copy.deepcopy(item) for key, item in value.items()}


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class _ViewerWorkspaceContext:
    project_path: str = ""
    runtime_snapshot: RuntimeSnapshot | None = None
    runtime_snapshot_context: RuntimeSnapshotContext | None = None


@dataclass(slots=True)
class _ViewerSessionRecord:
    workspace_id: str
    node_id: str
    session_id: str
    owner_scope: str
    backend_id: str = DPF_EXECUTION_VIEWER_BACKEND_ID
    source_refs: dict[str, Any] = field(default_factory=dict)
    materialized_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(
        default_factory=lambda: {
            "state": "paused",
            "step_index": 0,
        }
    )
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    session_state: str = "open"
    invalidated_reason: str = ""
    stale_ref_keys: set[str] = field(default_factory=set)

    def has_live_dataset(self) -> bool:
        return coerce_runtime_handle_ref(self.materialized_refs.get("dataset")) is not None

    def cache_state(self) -> str:
        if self.invalidated_reason:
            return "invalidated"
        if self.session_state == "closed":
            return "closed"
        if self.has_live_dataset():
            return "live_ready"
        if self.source_refs or self.materialized_refs:
            return "proxy_ready"
        return "empty"

    def public_data_refs(self) -> dict[str, Any]:
        return copy.deepcopy(self.materialized_refs)

    def public_summary(self) -> dict[str, Any]:
        summary = copy.deepcopy(self.summary)
        summary["cache_state"] = self.cache_state()
        summary["has_source_data"] = bool(self.source_refs)
        summary["has_materialized_data"] = bool(self.materialized_refs)
        summary["backend_id"] = self.backend_id
        summary["transport_revision"] = self.transport_revision
        summary["live_open_status"] = self.live_open_status
        if self.invalidated_reason:
            summary["invalidated_reason"] = self.invalidated_reason
        if self.live_open_blocker:
            summary["live_open_blocker"] = copy.deepcopy(self.live_open_blocker)
        if self.camera_state:
            summary["camera"] = copy.deepcopy(self.camera_state)
            summary["camera_state"] = copy.deepcopy(self.camera_state)
        if self.stale_ref_keys:
            summary["stale_ref_keys"] = sorted(self.stale_ref_keys)
        artifact_formats = sorted(
            key
            for key, value in self.materialized_refs.items()
            if isinstance(value, RuntimeArtifactRef)
        )
        if artifact_formats:
            summary["artifact_formats"] = artifact_formats
        if self.has_live_dataset():
            summary["live_dataset_key"] = "dataset"
        return summary

    def public_options(self) -> dict[str, Any]:
        options = copy.deepcopy(self.options)
        requested_live_mode = str(options.get("live_mode", "")).strip() or "proxy"
        options["live_mode"] = requested_live_mode if self.has_live_dataset() and not self.invalidated_reason else "proxy"
        options["session_state"] = self.session_state
        options["cache_state"] = self.cache_state()
        options["backend_id"] = self.backend_id
        options["transport_revision"] = self.transport_revision
        options["live_open_status"] = self.live_open_status
        if self.live_open_blocker:
            options["live_open_blocker"] = copy.deepcopy(self.live_open_blocker)
        playback_state = copy.deepcopy(self.playback_state)
        options["playback_state"] = str(playback_state.get("state", "paused")).strip() or "paused"
        options["step_index"] = _coerce_int(playback_state.get("step_index"), default=0)
        options["playback"] = playback_state
        return options


class ViewerSessionService:
    def __init__(self, worker_services: WorkerServices) -> None:
        self._worker_services = worker_services
        self._backend_registry = worker_services.viewer_backend_registry
        self._materialization_backend = self._backend_registry.resolve(DPF_EXECUTION_VIEWER_BACKEND_ID)
        self._sessions: dict[tuple[str, str], _ViewerSessionRecord] = {}
        self._workspace_contexts: dict[str, _ViewerWorkspaceContext] = {}

    def prepare_workspace_context(
        self,
        *,
        workspace_id: str,
        project_path: str = "",
        runtime_snapshot: RuntimeSnapshot | None = None,
        runtime_snapshot_context: RuntimeSnapshotContext | None = None,
        invalidate_existing: bool = False,
    ) -> None:
        normalized_workspace_id = self._normalize_required_string("workspace_id", workspace_id)
        if invalidate_existing:
            self.invalidate_workspace(
                normalized_workspace_id,
                reason=_SESSION_INVALIDATION_REASON_RERUN,
            )
        self._workspace_contexts[normalized_workspace_id] = _ViewerWorkspaceContext(
            project_path=str(project_path).strip(),
            runtime_snapshot=runtime_snapshot,
            runtime_snapshot_context=runtime_snapshot_context,
        )

    def invalidate_workspace(self, workspace_id: str, *, reason: str) -> int:
        normalized_workspace_id = self._normalize_required_string("workspace_id", workspace_id)
        normalized_reason = self._normalize_required_string("reason", reason)
        invalidated_count = 0
        for session_key, record in self._sessions.items():
            if session_key[0] != normalized_workspace_id:
                continue
            self._release_owner_scope(record.owner_scope)
            record.source_refs.clear()
            record.materialized_refs.clear()
            self._set_transport_state(
                record,
                transport={},
                transport_revision=record.transport_revision + 1 if record.transport else record.transport_revision,
            )
            record.session_state = "invalidated"
            record.invalidated_reason = normalized_reason
            record.stale_ref_keys.clear()
            self._refresh_public_contract(record)
            invalidated_count += 1
        return invalidated_count

    def reset(self) -> None:
        released_owner_scopes = {
            record.owner_scope
            for record in self._sessions.values()
        }
        for owner_scope in released_owner_scopes:
            self._release_owner_scope(owner_scope)
        self._sessions.clear()
        self._workspace_contexts.clear()

    def handle_command(self, command: WorkerCommand) -> WorkerEvent:
        if isinstance(command, OpenViewerSessionCommand):
            return self.open_session(command)
        if isinstance(command, UpdateViewerSessionCommand):
            return self.update_session(command)
        if isinstance(command, CloseViewerSessionCommand):
            return self.close_session(command)
        if isinstance(command, MaterializeViewerDataCommand):
            return self.materialize_data(command)
        raise TypeError(f"Unsupported viewer session command: {type(command)!r}")

    def open_session(self, command: OpenViewerSessionCommand) -> ViewerSessionOpenedEvent | ViewerSessionFailedEvent:
        workspace_id, node_id = self._normalize_workspace_and_node(command)
        if not workspace_id or not node_id:
            return self._failure(command, "workspace_id and node_id are required.")

        session_id = str(command.session_id).strip() or self._next_session_id()
        session_key = (workspace_id, session_id)
        record = self._sessions.get(session_key)
        if record is None:
            record = _ViewerSessionRecord(
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                owner_scope=self._session_owner_scope(workspace_id, session_id),
            )
            self._sessions[session_key] = record
        elif record.node_id != node_id:
            return self._failure(
                command,
                f"session_id {session_id!r} is already bound to node_id {record.node_id!r}.",
                session_id=session_id,
            )

        self._sanitize_record(record)
        self._apply_session_payload(
            record,
            backend_id=command.backend_id,
            data_refs=command.data_refs,
            transport=command.transport,
            transport_revision=command.transport_revision,
            live_open_status=command.live_open_status,
            live_open_blocker=command.live_open_blocker,
            camera_state=command.camera_state,
            playback_state=command.playback_state,
            summary=command.summary,
            options=command.options,
        )
        if command.data_refs or command.transport:
            record.invalidated_reason = ""
        record.session_state = "open"
        self._refresh_public_contract(record)
        return ViewerSessionOpenedEvent(
            request_id=command.request_id,
            workspace_id=workspace_id,
            node_id=node_id,
            session_id=session_id,
            backend_id=record.backend_id,
            data_refs=record.public_data_refs(),
            transport=copy.deepcopy(record.transport),
            transport_revision=record.transport_revision,
            live_open_status=record.live_open_status,
            live_open_blocker=copy.deepcopy(record.live_open_blocker),
            camera_state=copy.deepcopy(record.camera_state),
            playback_state=copy.deepcopy(record.playback_state),
            summary=record.public_summary(),
            options=record.public_options(),
        )

    def update_session(self, command: UpdateViewerSessionCommand) -> ViewerSessionUpdatedEvent | ViewerSessionFailedEvent:
        record = self._require_record(command)
        if isinstance(record, ViewerSessionFailedEvent):
            return record

        self._sanitize_record(record)
        self._apply_session_payload(
            record,
            backend_id=command.backend_id,
            data_refs=command.data_refs,
            transport=command.transport,
            transport_revision=command.transport_revision,
            live_open_status=command.live_open_status,
            live_open_blocker=command.live_open_blocker,
            camera_state=command.camera_state,
            playback_state=command.playback_state,
            summary=command.summary,
            options=command.options,
        )
        if command.data_refs or command.transport:
            record.invalidated_reason = ""
        record.session_state = "open"
        self._refresh_public_contract(record)
        return ViewerSessionUpdatedEvent(
            request_id=command.request_id,
            workspace_id=record.workspace_id,
            node_id=record.node_id,
            session_id=record.session_id,
            backend_id=record.backend_id,
            data_refs=record.public_data_refs(),
            transport=copy.deepcopy(record.transport),
            transport_revision=record.transport_revision,
            live_open_status=record.live_open_status,
            live_open_blocker=copy.deepcopy(record.live_open_blocker),
            camera_state=copy.deepcopy(record.camera_state),
            playback_state=copy.deepcopy(record.playback_state),
            summary=record.public_summary(),
            options=record.public_options(),
        )

    def close_session(self, command: CloseViewerSessionCommand) -> ViewerSessionClosedEvent | ViewerSessionFailedEvent:
        record = self._require_record(command)
        if isinstance(record, ViewerSessionFailedEvent):
            return record

        self._sanitize_record(record)
        if bool(command.options.get("release_handles", False)):
            self._release_materialized_handles(record)

        reason = str(command.options.get("reason", "")).strip()
        if reason:
            record.summary["close_reason"] = reason
        record.session_state = "closed"
        self._refresh_public_contract(record)

        event_options = record.public_options()
        if reason:
            event_options["reason"] = reason
        if "release_handles" in command.options:
            event_options["release_handles"] = bool(command.options.get("release_handles", False))
        return ViewerSessionClosedEvent(
            request_id=command.request_id,
            workspace_id=record.workspace_id,
            node_id=record.node_id,
            session_id=record.session_id,
            backend_id=record.backend_id,
            transport=copy.deepcopy(record.transport),
            transport_revision=record.transport_revision,
            live_open_status=record.live_open_status,
            live_open_blocker=copy.deepcopy(record.live_open_blocker),
            camera_state=copy.deepcopy(record.camera_state),
            playback_state=copy.deepcopy(record.playback_state),
            summary=record.public_summary(),
            options=event_options,
        )

    def materialize_data(
        self,
        command: MaterializeViewerDataCommand,
    ) -> ViewerDataMaterializedEvent | ViewerSessionFailedEvent:
        record = self._require_record(command)
        if isinstance(record, ViewerSessionFailedEvent):
            return record

        self._sanitize_record(record)
        request_options = copy.deepcopy(command.options)
        persistent_options = {
            str(key): copy.deepcopy(value)
            for key, value in request_options.items()
            if str(key) not in _MATERIALIZE_TRANSIENT_OPTION_KEYS
        }
        if persistent_options:
            record.options.update(persistent_options)

        output_profile = self._resolve_output_profile(record, request_options)
        export_formats = self._normalize_export_formats(request_options.get("export_formats", record.options.get("export_formats")))
        if not bool(request_options.get("force_recompute", False)):
            cached_event = self._cached_materialization_event(
                record,
                command=command,
                output_profile=output_profile,
                export_formats=export_formats,
            )
            if cached_event is not None:
                record.session_state = "open"
                return cached_event

        if record.invalidated_reason and not record.source_refs:
            return self._failure(
                command,
                f"Viewer session {record.session_id!r} is invalidated: {record.invalidated_reason}.",
            )

        context = self._workspace_contexts.get(record.workspace_id)
        backend_id = str(command.backend_id).strip() or record.backend_id or DPF_EXECUTION_VIEWER_BACKEND_ID
        backend = self._backend_registry.resolve(backend_id)
        backend_request = ViewerBackendMaterializationRequest(
            workspace_id=record.workspace_id,
            node_id=record.node_id,
            session_id=record.session_id,
            owner_scope=record.owner_scope,
            source_refs=record.source_refs,
            session_summary=record.summary,
            session_options=record.options,
            request_options=request_options,
            output_profile=output_profile,
            export_formats=export_formats,
            project_path=context.project_path if context is not None else "",
            runtime_snapshot=context.runtime_snapshot if context is not None else None,
            runtime_snapshot_context=context.runtime_snapshot_context if context is not None else None,
        )

        try:
            result = backend.materialize(backend_request)
        except Exception as exc:  # noqa: BLE001
            return self._failure(command, str(exc))

        self._merge_record_refs(
            record,
            source_refs={},
            materialized_refs=result.data_refs,
        )
        result_backend_id = str(getattr(result, "backend_id", "")).strip() or backend_id
        result_transport = _copy_mapping(getattr(result, "transport", {}))
        result_transport_revision = _coerce_int(getattr(result, "transport_revision", 0))
        result_camera_state = _copy_mapping(getattr(result, "camera_state", {}))
        result_playback_state = _copy_mapping(getattr(result, "playback_state", {}))
        result_live_open_status = str(getattr(result, "live_open_status", "")).strip()
        result_live_open_blocker = _copy_mapping(getattr(result, "live_open_blocker", {}))
        if not result_transport and result.data_refs:
            result_transport = {
                "kind": "legacy_data_refs",
                "version": 1,
                "backend_id": result_backend_id,
                "data_refs": copy.deepcopy(result.data_refs),
            }
        record.backend_id = result_backend_id
        self._set_transport_state(
            record,
            transport=result_transport,
            transport_revision=result_transport_revision,
        )
        if result_camera_state:
            record.camera_state = result_camera_state
        if result_playback_state:
            record.playback_state = self._normalize_playback_state(
                result_playback_state,
                fallback=record.playback_state,
            )
        record.summary.update(copy.deepcopy(result.summary))
        record.summary["materialized_output_profile"] = output_profile
        record.invalidated_reason = ""
        record.session_state = "open"
        self._refresh_public_contract(
            record,
            live_open_status=result_live_open_status,
            live_open_blocker=result_live_open_blocker,
        )
        return ViewerDataMaterializedEvent(
            request_id=command.request_id,
            workspace_id=record.workspace_id,
            node_id=record.node_id,
            session_id=record.session_id,
            backend_id=record.backend_id,
            data_refs=record.public_data_refs(),
            transport=copy.deepcopy(record.transport),
            transport_revision=record.transport_revision,
            live_open_status=record.live_open_status,
            live_open_blocker=copy.deepcopy(record.live_open_blocker),
            camera_state=copy.deepcopy(record.camera_state),
            playback_state=copy.deepcopy(record.playback_state),
            summary=record.public_summary(),
            options=record.public_options(),
        )

    @staticmethod
    def _next_session_id() -> str:
        return f"{_SESSION_ID_PREFIX}{uuid4().hex[:12]}"

    @staticmethod
    def _normalize_required_string(field_name: str, value: Any) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{field_name} is required.")
        return normalized

    @staticmethod
    def _normalize_workspace_and_node(command: Any) -> tuple[str, str]:
        workspace_id = str(getattr(command, "workspace_id", "")).strip()
        node_id = str(getattr(command, "node_id", "")).strip()
        return workspace_id, node_id

    @staticmethod
    def _session_owner_scope(workspace_id: str, session_id: str) -> str:
        return f"cache:viewer_session:{workspace_id}:{session_id}"

    @staticmethod
    def _is_materialized_ref(key: str, value: Any) -> bool:
        return isinstance(value, RuntimeArtifactRef) or str(key) in _MATERIALIZED_DATA_KEYS

    @staticmethod
    def _resolve_output_profile(record: _ViewerSessionRecord, request_options: Mapping[str, Any]) -> str:
        profile = str(request_options.get("output_profile", record.options.get("output_profile", _DEFAULT_OUTPUT_PROFILE))).strip()
        return profile or _DEFAULT_OUTPUT_PROFILE

    @staticmethod
    def _normalize_export_formats(value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            normalized = value.strip()
            return (normalized,) if normalized else ()
        if not isinstance(value, Iterable) or isinstance(value, Mapping):
            return ()
        formats: list[str] = []
        for item in value:
            token = str(item).strip()
            if token and token not in formats:
                formats.append(token)
        return tuple(formats)

    def _require_record(self, command: Any) -> _ViewerSessionRecord | ViewerSessionFailedEvent:
        workspace_id, node_id = self._normalize_workspace_and_node(command)
        session_id = str(getattr(command, "session_id", "")).strip()
        if not workspace_id or not node_id or not session_id:
            return self._failure(command, "workspace_id, node_id, and session_id are required.")
        record = self._sessions.get((workspace_id, session_id))
        if record is None:
            return self._failure(command, f"Unknown viewer session: {session_id!r}.")
        if record.node_id != node_id:
            return self._failure(
                command,
                f"Viewer session {session_id!r} belongs to node_id {record.node_id!r}, not {node_id!r}.",
            )
        return record

    def _failure(self, command: Any, error: str, *, session_id: str = "") -> ViewerSessionFailedEvent:
        return ViewerSessionFailedEvent(
            request_id=str(getattr(command, "request_id", "")).strip(),
            workspace_id=str(getattr(command, "workspace_id", "")).strip(),
            node_id=str(getattr(command, "node_id", "")).strip(),
            session_id=session_id or str(getattr(command, "session_id", "")).strip(),
            command=str(getattr(command, "type", "")).strip(),
            error=str(error).strip() or "viewer session command failed",
        )

    def _sanitize_record(self, record: _ViewerSessionRecord) -> None:
        record.source_refs, stale_source = self._sanitize_ref_map(record.source_refs)
        record.materialized_refs, stale_materialized = self._sanitize_ref_map(record.materialized_refs)
        record.stale_ref_keys = stale_source | stale_materialized
        self._refresh_transport_refs(record)
        self._refresh_public_contract(record)

    def _sanitize_ref_map(self, ref_map: Mapping[str, Any]) -> tuple[dict[str, Any], set[str]]:
        sanitized: dict[str, Any] = {}
        stale_keys: set[str] = set()
        for key, value in ref_map.items():
            runtime_ref = coerce_runtime_handle_ref(value)
            if runtime_ref is None:
                sanitized[str(key)] = copy.deepcopy(value)
                continue
            try:
                self._worker_services.resolve_handle(runtime_ref, expected_kind=runtime_ref.kind)
            except (StaleHandleError, TypeError):
                stale_keys.add(str(key))
                continue
            sanitized[str(key)] = runtime_ref
        return sanitized, stale_keys

    def _apply_session_payload(
        self,
        record: _ViewerSessionRecord,
        *,
        backend_id: str,
        data_refs: Mapping[str, Any],
        transport: Mapping[str, Any],
        transport_revision: int,
        live_open_status: str,
        live_open_blocker: Mapping[str, Any],
        camera_state: Mapping[str, Any],
        playback_state: Mapping[str, Any],
        summary: Mapping[str, Any],
        options: Mapping[str, Any],
    ) -> None:
        source_refs: dict[str, Any] = {}
        materialized_refs: dict[str, Any] = {}
        for key, value in data_refs.items():
            normalized_key = str(key)
            persisted_value = self._persist_ref_value(
                value,
                owner_scope=record.owner_scope,
            )
            if persisted_value is None:
                record.stale_ref_keys.add(normalized_key)
                continue
            if self._is_materialized_ref(normalized_key, persisted_value):
                materialized_refs[normalized_key] = persisted_value
            else:
                source_refs[normalized_key] = persisted_value
            record.stale_ref_keys.discard(normalized_key)

        self._merge_record_refs(
            record,
            source_refs=source_refs,
            materialized_refs=materialized_refs,
        )
        normalized_backend_id = str(backend_id).strip()
        if normalized_backend_id:
            record.backend_id = normalized_backend_id

        if isinstance(summary, Mapping):
            record.summary.update(
                {str(key): copy.deepcopy(value) for key, value in summary.items()}
            )
        if isinstance(options, Mapping):
            record.options.update(
                {
                    str(key): copy.deepcopy(value)
                    for key, value in options.items()
                    if str(key) not in _CLOSE_TRANSIENT_OPTION_KEYS
                }
            )
        if camera_state:
            record.camera_state = _copy_mapping(camera_state)
        else:
            record.camera_state = _copy_mapping(record.summary.get("camera_state") or record.summary.get("camera"))
        if playback_state:
            record.playback_state = self._normalize_playback_state(
                playback_state,
                fallback=record.playback_state,
            )
        else:
            record.playback_state = self._normalize_playback_state(
                record.options,
                fallback=record.playback_state,
            )
        if transport or _coerce_int(transport_revision) > 0:
            self._set_transport_state(
                record,
                transport=transport,
                transport_revision=transport_revision,
            )
        self._refresh_public_contract(
            record,
            live_open_status=live_open_status,
            live_open_blocker=live_open_blocker if live_open_status or live_open_blocker else None,
        )

    @staticmethod
    def _normalize_playback_state(
        value: Mapping[str, Any] | Any,
        *,
        fallback: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        base = _copy_mapping(fallback)
        payload = _copy_mapping(value)
        state = str(payload.get("state", base.get("state", payload.get("playback_state", "paused")))).strip() or "paused"
        step_index = _coerce_int(
            payload.get("step_index", base.get("step_index", payload.get("frame_index", 0))),
            default=_coerce_int(base.get("step_index"), default=0),
        )
        return {
            "state": state,
            "step_index": step_index,
        }

    def _set_transport_state(
        self,
        record: _ViewerSessionRecord,
        *,
        transport: Mapping[str, Any],
        transport_revision: int,
    ) -> None:
        normalized_transport = _copy_mapping(transport)
        if normalized_transport != record.transport:
            if normalized_transport:
                explicit_revision = _coerce_int(transport_revision)
                record.transport_revision = explicit_revision if explicit_revision > 0 else record.transport_revision + 1
            elif record.transport:
                record.transport_revision += 1
            record.transport = normalized_transport
            return
        explicit_revision = _coerce_int(transport_revision)
        if explicit_revision > record.transport_revision:
            record.transport_revision = explicit_revision

    def _default_live_open_state(self, record: _ViewerSessionRecord) -> tuple[str, dict[str, Any]]:
        if record.invalidated_reason:
            blocker = {
                "code": "session_invalidated",
                "reason": record.invalidated_reason,
            }
            if record.invalidated_reason == _SESSION_INVALIDATION_REASON_RERUN:
                blocker["rerun_required"] = True
            return "blocked", blocker
        if record.session_state == "closed":
            return "blocked", {
                "code": "session_closed",
                "reason": str(record.summary.get("close_reason", "session_closed")).strip() or "session_closed",
            }
        if record.transport:
            transport_refs = _copy_mapping(record.transport.get("data_refs"))
            if "data_refs" not in record.transport:
                return "ready", {}
            if "dataset" in transport_refs:
                return "ready", {}
        if record.source_refs or record.materialized_refs:
            return "blocked", {
                "code": "transport_not_ready",
                "reason": "Live viewer transport is not materialized.",
            }
        return "blocked", {
            "code": "no_source_data",
            "reason": "Viewer session does not have source data.",
        }

    def _refresh_public_contract(
        self,
        record: _ViewerSessionRecord,
        *,
        live_open_status: str = "",
        live_open_blocker: Mapping[str, Any] | None = None,
    ) -> None:
        default_status, default_blocker = self._default_live_open_state(record)
        normalized_status = str(live_open_status).strip() or default_status
        normalized_blocker = _copy_mapping(live_open_blocker if live_open_blocker is not None else default_blocker)
        if normalized_status == "ready":
            normalized_blocker = {}
        elif not normalized_blocker:
            normalized_blocker = copy.deepcopy(default_blocker)
        record.live_open_status = normalized_status
        record.live_open_blocker = normalized_blocker

    def _refresh_transport_refs(self, record: _ViewerSessionRecord) -> None:
        if not record.transport or "data_refs" not in record.transport:
            return
        updated_transport = _copy_mapping(record.transport)
        updated_transport["data_refs"] = record.public_data_refs()
        self._set_transport_state(
            record,
            transport=updated_transport,
            transport_revision=record.transport_revision,
        )

    def _persist_ref_value(self, value: Any, *, owner_scope: str) -> Any | None:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is None:
            return copy.deepcopy(value)
        try:
            self._worker_services.resolve_handle(runtime_ref, expected_kind=runtime_ref.kind)
        except (StaleHandleError, TypeError):
            return None
        if runtime_ref.owner_scope == owner_scope:
            return runtime_ref
        resolved_value = self._worker_services.resolve_handle(runtime_ref, expected_kind=runtime_ref.kind)
        return self._worker_services.register_handle(
            resolved_value,
            kind=runtime_ref.kind,
            owner_scope=owner_scope,
            metadata=runtime_ref.metadata,
        )

    def _merge_record_refs(
        self,
        record: _ViewerSessionRecord,
        *,
        source_refs: Mapping[str, Any],
        materialized_refs: Mapping[str, Any],
    ) -> None:
        for key, value in source_refs.items():
            if key in record.materialized_refs:
                self._release_session_handle(record.materialized_refs.pop(key), owner_scope=record.owner_scope)
            previous = record.source_refs.get(key)
            if previous != value:
                self._release_session_handle(previous, owner_scope=record.owner_scope)
            record.source_refs[str(key)] = value

        for key, value in materialized_refs.items():
            if key in record.source_refs:
                self._release_session_handle(record.source_refs.pop(key), owner_scope=record.owner_scope)
            previous = record.materialized_refs.get(key)
            if previous != value:
                self._release_session_handle(previous, owner_scope=record.owner_scope)
            record.materialized_refs[str(key)] = value

    def _release_materialized_handles(self, record: _ViewerSessionRecord) -> None:
        retained_refs: dict[str, Any] = {}
        for key, value in record.materialized_refs.items():
            runtime_ref = coerce_runtime_handle_ref(value)
            if runtime_ref is None:
                retained_refs[key] = value
                continue
            self._release_session_handle(runtime_ref, owner_scope=record.owner_scope)
        record.materialized_refs = retained_refs
        self._refresh_transport_refs(record)

    def _release_session_handle(self, value: Any, *, owner_scope: str) -> None:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is None or runtime_ref.owner_scope != owner_scope:
            return
        try:
            self._worker_services.release_handle(runtime_ref)
        except (StaleHandleError, TypeError):
            return

    def _release_owner_scope(self, owner_scope: str) -> None:
        if not str(owner_scope).strip():
            return
        self._worker_services.handle_registry.release_owner_scope(owner_scope)

    def _cached_materialization_event(
        self,
        record: _ViewerSessionRecord,
        *,
        command: MaterializeViewerDataCommand,
        output_profile: str,
        export_formats: tuple[str, ...],
    ) -> ViewerDataMaterializedEvent | None:
        cached_refs: dict[str, Any] = {}
        if output_profile in {"memory", "both"}:
            dataset_ref = record.materialized_refs.get("dataset")
            if dataset_ref is not None:
                cached_refs["dataset"] = dataset_ref
            elif output_profile == "memory":
                return None

        requested_artifact_keys = export_formats or tuple(
            key
            for key, value in record.materialized_refs.items()
            if isinstance(value, RuntimeArtifactRef)
        )
        if output_profile in {"stored", "both"}:
            missing_artifacts = [
                key for key in requested_artifact_keys
                if not isinstance(record.materialized_refs.get(key), RuntimeArtifactRef)
            ]
            if missing_artifacts:
                return None
            cached_refs.update(
                {
                    key: record.materialized_refs[key]
                    for key in requested_artifact_keys
                    if key in record.materialized_refs
                }
            )

        if not cached_refs:
            return None

        summary = record.public_summary()
        summary["materialized_output_profile"] = output_profile
        self._refresh_public_contract(record)
        return ViewerDataMaterializedEvent(
            request_id=command.request_id,
            workspace_id=record.workspace_id,
            node_id=record.node_id,
            session_id=record.session_id,
            backend_id=record.backend_id,
            data_refs=copy.deepcopy(cached_refs),
            transport=copy.deepcopy(record.transport),
            transport_revision=record.transport_revision,
            live_open_status=record.live_open_status,
            live_open_blocker=copy.deepcopy(record.live_open_blocker),
            camera_state=copy.deepcopy(record.camera_state),
            playback_state=copy.deepcopy(record.playback_state),
            summary=summary,
            options=record.public_options(),
        )


__all__ = [
    "ViewerSessionService",
]
