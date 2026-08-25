"""Typed worker command/event contracts with queue-boundary dict adapters.

This module owns process transport DTOs and their dict adapters only. Runtime
snapshot assembly lives in ``runtime_snapshot``/``runtime_snapshot_assembly``,
workspace compilation in ``compiler``, worker execution and cancellation in the
worker/client modules, and viewer state machines in ``viewer_session_service``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, replace
import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Any, Literal, TypeAlias

from ea_node_editor.common.clr_type_names import (
    ClrTypeNameError,
    validate_canonical_clr_type_id,
)
from ea_node_editor.common.payload_tools import copy_json_safe
from ea_node_editor.execution.backends import (
    ExecutionBackendSelection,
    coerce_execution_backend_selection,
)
from ea_node_editor.nodes.function_plugin import (
    EMPTY_PLUGIN_FINGERPRINT,
    PluginBundleRef,
    PythonFunctionRef,
)
from ea_node_editor.nodes.plugin_generation import _is_reparse_point
from ea_node_editor.settings import plugin_generations_dir
from ea_node_editor.runtime_contracts import (
    DataTree,
    DataTypeCatalog,
    deserialize_runtime_value,
    serialize_runtime_value,
)
from ea_node_editor.runtime_contracts.data_types import MAX_PAYLOAD_SCHEMA_VERSION
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    coerce_runtime_snapshot,
)

EngineState = Literal["ready", "running", "paused", "error"]
RunTransition = Literal["start", "pause", "resume", "stop", "complete", "fail"]
EventType = Literal[
    "run_started",
    "run_state",
    "run_completed",
    "run_failed",
    "run_stopped",
    "node_started",
    "node_settled",
    "trigger_capture_settled",
    "trigger_published",
    "log",
    "protocol_error",
    "viewer_session_opened",
    "viewer_session_updated",
    "viewer_session_closed",
    "viewer_data_materialized",
    "viewer_query_result",
    "viewer_session_failed",
]
SettledStatus = Literal["value", "empty", "failed"]
NodeSettlementStatus = Literal["completed", "empty", "failed", "blocked"]

VIEWER_COMMAND_TYPES = frozenset(
    {
        "open_viewer_session",
        "update_viewer_session",
        "close_viewer_session",
        "materialize_viewer_data",
        "query_viewer_session",
    }
)
VIEWER_RESPONSE_EVENT_TYPES = frozenset(
    {
        "viewer_session_opened",
        "viewer_session_updated",
        "viewer_session_closed",
        "viewer_data_materialized",
        "viewer_query_result",
        "viewer_session_failed",
    }
)
_RUNTIME_VALUE_MARKER_KEY = "__ea_runtime_value__"
_VIEWER_RUNTIME_MARKERS = frozenset(
    {
        "artifact_ref",
        "handle_ref",
        "tabular_data_ref",
        "array_data_ref",
        "tabular_window_ref",
        "array_slice_2d_ref",
        "data_tree",
    }
)
_CATALOG_FINGERPRINT_LENGTH = 64
_CATALOG_REVISION_RECORD_LIMIT = 4096
_CATALOG_REVISION_IDENTITY_LENGTH = 1024
_CATALOG_REVISION_OWNER_LENGTH = 256
_CATALOG_REVISION_VERSION_LENGTH = 128
_CATALOG_REVISION_KINDS = frozenset({"family", "type", "conversion"})
_CATALOG_DIAGNOSTIC_DIFFERENCE_LIMIT = 8
_CATALOG_DIAGNOSTIC_IDENTITY_LENGTH = 160
_CATALOG_DIAGNOSTIC_MESSAGE_LENGTH = 2048
_PLUGIN_BUNDLE_LIMIT = 128
_PLUGIN_FUNCTION_LIMIT = 4096
_ADDON_RUNTIME_CONFIG_LIMIT = 64
_ADDON_RUNTIME_ID_LIMIT = 128
EMPTY_REGISTRY_CONTRACT_FINGERPRINT = hashlib.sha256(b"").hexdigest()
_PLUGIN_OWNER_LENGTH = 256
_PLUGIN_VERSION_LENGTH = 128
_PLUGIN_PATH_LENGTH = 1024
_PLUGIN_FUNCTION_NAME_LENGTH = 128
_PLUGIN_UNAVAILABLE_REASON_LENGTH = 2048


@dataclass(frozen=True)
class RootExecutionError:
    node_id: str = ""
    error: str = ""
    traceback: str = ""


@dataclass(frozen=True)
class SettledPortResult:
    status: SettledStatus | str = "empty"
    value: DataTree | None = None
    errors: tuple[RootExecutionError, ...] = ()


@dataclass(frozen=True)
class CatalogRevisionRecord:
    kind: Literal["family", "type", "conversion"]
    identity: str
    payload_schema_version: int
    implementation_version: str
    owner_id: str
    owner_version: str
    semantic_digest: str


@dataclass(frozen=True)
class StartRunCommand:
    type: Literal["start_run"] = "start_run"
    run_id: str = ""
    project_path: str = ""
    workspace_id: str = ""
    trigger: dict[str, Any] = field(default_factory=dict)
    runtime_snapshot: RuntimeSnapshot | None = None
    execution_backend: ExecutionBackendSelection = field(
        default_factory=ExecutionBackendSelection
    )
    target_node_ids: tuple[str, ...] = ()
    trigger_publications: dict[str, SettledPortResult] = field(default_factory=dict)
    trigger_captures: dict[str, SettledPortResult] = field(default_factory=dict)
    clicked_trigger_node_id: str = ""
    developer_mode: bool = False
    catalog_fingerprint: str = ""
    catalog_revisions: tuple[CatalogRevisionRecord, ...] = ()
    plugin_bundles: tuple[PluginBundleRef, ...] = ()
    plugin_fingerprint: str = ""
    runtime_registry_fingerprint: str = ""
    registry_contract_fingerprint: str = EMPTY_REGISTRY_CONTRACT_FINGERPRINT
    addon_runtime_config: tuple[tuple[str, bool], ...] = ()


@dataclass(frozen=True)
class StopRunCommand:
    type: Literal["stop_run"] = "stop_run"
    run_id: str = ""
    workspace_id: str = ""


@dataclass(frozen=True)
class PauseRunCommand:
    type: Literal["pause_run"] = "pause_run"
    run_id: str = ""


@dataclass(frozen=True)
class ResumeRunCommand:
    type: Literal["resume_run"] = "resume_run"
    run_id: str = ""


@dataclass(frozen=True)
class ShutdownCommand:
    type: Literal["shutdown"] = "shutdown"


@dataclass(frozen=True)
class OpenViewerSessionCommand:
    type: Literal["open_viewer_session"] = "open_viewer_session"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UpdateViewerSessionCommand:
    type: Literal["update_viewer_session"] = "update_viewer_session"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CloseViewerSessionCommand:
    type: Literal["close_viewer_session"] = "close_viewer_session"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MaterializeViewerDataCommand:
    type: Literal["materialize_viewer_data"] = "materialize_viewer_data"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryViewerSessionCommand(MaterializeViewerDataCommand):
    """Serializable viewer query routed through the existing worker command path."""

    type: Literal["query_viewer_session"] = "query_viewer_session"
    query_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


WorkerCommand: TypeAlias = (
    StartRunCommand
    | StopRunCommand
    | PauseRunCommand
    | ResumeRunCommand
    | ShutdownCommand
    | OpenViewerSessionCommand
    | UpdateViewerSessionCommand
    | CloseViewerSessionCommand
    | QueryViewerSessionCommand
    | MaterializeViewerDataCommand
)


@dataclass(frozen=True)
class RunStartedEvent:
    type: Literal["run_started"] = "run_started"
    run_id: str = ""
    workspace_id: str = ""


@dataclass(frozen=True)
class RunStateEvent:
    type: Literal["run_state"] = "run_state"
    run_id: str = ""
    workspace_id: str = ""
    state: EngineState = "ready"
    transition: RunTransition | str = ""
    reason: str = ""


@dataclass(frozen=True)
class RunCompletedEvent:
    type: Literal["run_completed"] = "run_completed"
    run_id: str = ""
    workspace_id: str = ""
    state: Literal["ready"] = "ready"


@dataclass(frozen=True)
class RunFailedEvent:
    type: Literal["run_failed"] = "run_failed"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    error: str = ""
    traceback: str = ""
    state: Literal["error"] = "error"
    fatal: bool = False


@dataclass(frozen=True)
class RunStoppedEvent:
    type: Literal["run_stopped"] = "run_stopped"
    run_id: str = ""
    workspace_id: str = ""
    reason: str = ""
    state: Literal["ready"] = "ready"


@dataclass(frozen=True)
class NodeStartedEvent:
    type: Literal["node_started"] = "node_started"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    started_at_epoch_ms: float = 0.0


@dataclass(frozen=True)
class NodeSettledEvent:
    type: Literal["node_settled"] = "node_settled"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    status: NodeSettlementStatus | str = "completed"
    elapsed_ms: float = 0.0
    outputs: dict[str, SettledPortResult] = field(default_factory=dict)
    errors: tuple[RootExecutionError, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TriggerCaptureSettledEvent:
    type: Literal["trigger_capture_settled"] = "trigger_capture_settled"
    run_id: str = ""
    workspace_id: str = ""
    trigger_node_id: str = ""
    result: SettledPortResult = field(default_factory=SettledPortResult)


@dataclass(frozen=True)
class TriggerPublishedEvent:
    type: Literal["trigger_published"] = "trigger_published"
    run_id: str = ""
    workspace_id: str = ""
    trigger_node_id: str = ""
    result: SettledPortResult = field(default_factory=SettledPortResult)


@dataclass(frozen=True)
class LogEvent:
    type: Literal["log"] = "log"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    level: str = "info"
    message: str = ""


@dataclass(frozen=True)
class ProtocolErrorEvent:
    type: Literal["protocol_error"] = "protocol_error"
    run_id: str = ""
    workspace_id: str = ""
    request_id: str = ""
    command: str = ""
    error: str = ""


@dataclass(frozen=True)
class ViewerSessionOpenedEvent:
    type: Literal["viewer_session_opened"] = "viewer_session_opened"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewerSessionUpdatedEvent:
    type: Literal["viewer_session_updated"] = "viewer_session_updated"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewerSessionClosedEvent:
    type: Literal["viewer_session_closed"] = "viewer_session_closed"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewerDataMaterializedEvent:
    type: Literal["viewer_data_materialized"] = "viewer_data_materialized"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewerQueryResultEvent:
    type: Literal["viewer_query_result"] = "viewer_query_result"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    query_type: str = ""
    supported: bool = False
    value: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""


@dataclass(frozen=True)
class ViewerSessionFailedEvent:
    type: Literal["viewer_session_failed"] = "viewer_session_failed"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    command: str = ""
    error: str = ""


WorkerEvent: TypeAlias = (
    RunStartedEvent
    | RunStateEvent
    | RunCompletedEvent
    | RunFailedEvent
    | RunStoppedEvent
    | NodeStartedEvent
    | NodeSettledEvent
    | TriggerCaptureSettledEvent
    | TriggerPublishedEvent
    | LogEvent
    | ProtocolErrorEvent
    | ViewerSessionOpenedEvent
    | ViewerSessionUpdatedEvent
    | ViewerSessionClosedEvent
    | ViewerDataMaterializedEvent
    | ViewerQueryResultEvent
    | ViewerSessionFailedEvent
)


_SCALAR_PROTOCOL_TYPES = frozenset(
    {
        StopRunCommand,
        PauseRunCommand,
        ResumeRunCommand,
        ShutdownCommand,
        RunStartedEvent,
        RunStateEvent,
        RunCompletedEvent,
        RunFailedEvent,
        RunStoppedEvent,
        NodeStartedEvent,
        LogEvent,
        ProtocolErrorEvent,
        ViewerSessionFailedEvent,
    }
)
_ENGINE_STATE_VALUES = frozenset({"ready", "running", "paused", "error"})
_RUN_TRANSITION_VALUES = frozenset(
    {"", "start", "pause", "resume", "stop", "complete", "fail"}
)
_FIXED_RUN_EVENT_STATES = {
    RunCompletedEvent: "ready",
    RunFailedEvent: "error",
    RunStoppedEvent: "ready",
}


def _string_field(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    default: str = "",
    strip: bool = False,
) -> str:
    if field_name not in payload:
        return default
    value = payload[field_name]
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    return value.strip() if strip else value


def _bool_field(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    default: bool = False,
) -> bool:
    if field_name not in payload:
        return default
    value = payload[field_name]
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean.")
    return value


def _float_field(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    default: float = 0.0,
) -> float:
    if field_name not in payload:
        return default
    value = payload[field_name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number.")
    normalized = float(value)
    if not isfinite(normalized):
        raise ValueError(f"{field_name} must be finite.")
    return normalized


def _nonnegative_int_field(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    default: int = 0,
) -> int:
    if field_name not in payload:
        return default
    value = payload[field_name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return value


def _string_list_field(
    payload: Mapping[str, Any],
    field_name: str,
) -> tuple[str, ...]:
    if field_name not in payload:
        return ()
    value = payload[field_name]
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list.")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"{field_name}[{index}] must be a string.")
        item = item.strip()
        if item:
            normalized.append(item)
    return tuple(normalized)


def _bounded_catalog_text(
    value: object,
    *,
    field_name: str,
    max_length: int,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    if value != value.strip():
        raise ValueError(f"{field_name} must be a trimmed string.")
    if not allow_empty and not value:
        raise ValueError(f"{field_name} must be non-empty.")
    if len(value) > max_length:
        raise ValueError(f"{field_name} is too long.")
    if any(not character.isprintable() for character in value):
        raise ValueError(f"{field_name} contains control characters.")
    return value


def _sha256_digest(value: object, *, field_name: str) -> str:
    digest = _bounded_catalog_text(
        value,
        field_name=field_name,
        max_length=_CATALOG_FINGERPRINT_LENGTH,
    )
    if len(digest) != _CATALOG_FINGERPRINT_LENGTH or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(f"{field_name} must be a 64-character lowercase SHA-256.")
    return digest


def _catalog_fingerprint(value: object) -> str:
    return _sha256_digest(value, field_name="catalog_fingerprint")


def _plugin_fingerprint(value: object) -> str:
    return _sha256_digest(value, field_name="plugin_fingerprint")


def runtime_registry_fingerprint(
    catalog_fingerprint: object,
    plugin_fingerprint: object,
) -> str:
    catalog_digest = _catalog_fingerprint(catalog_fingerprint)
    plugin_digest = _plugin_fingerprint(plugin_fingerprint)
    return hashlib.sha256(
        f"{catalog_digest}:{plugin_digest}".encode("ascii")
    ).hexdigest()


def _python_function_ref_payload(function: PythonFunctionRef) -> dict[str, object]:
    return {
        "bundle_id": function.bundle_id,
        "bundle_digest": function.bundle_digest,
        "module_relative_path": function.module_relative_path,
        "function_name": function.function_name,
        "source_digest": function.source_digest,
        "is_async": function.is_async,
    }


def _python_function_ref(
    value: PythonFunctionRef | Mapping[str, object],
    *,
    index: int,
) -> PythonFunctionRef:
    payload = (
        _python_function_ref_payload(value)
        if isinstance(value, PythonFunctionRef)
        else value
    )
    if not isinstance(payload, Mapping):
        raise ValueError(f"plugin function {index} must be a mapping")
    expected_fields = {
        "bundle_id",
        "bundle_digest",
        "module_relative_path",
        "function_name",
        "source_digest",
        "is_async",
    }
    if set(payload) != expected_fields:
        raise ValueError(f"plugin function {index} has unexpected fields")
    bundle_id = _logical_catalog_identifier(
        _bounded_catalog_text(
            payload["bundle_id"],
            field_name=f"plugin function {index} bundle_id",
            max_length=_PLUGIN_OWNER_LENGTH,
        ),
        field_name=f"plugin function {index} bundle_id",
    )
    module_relative_path = _bounded_catalog_text(
        payload["module_relative_path"],
        field_name=f"plugin function {index} module_relative_path",
        max_length=_PLUGIN_PATH_LENGTH,
    )
    function_name = _bounded_catalog_text(
        payload["function_name"],
        field_name=f"plugin function {index} function_name",
        max_length=_PLUGIN_FUNCTION_NAME_LENGTH,
    )
    is_async = payload["is_async"]
    if not isinstance(is_async, bool):
        raise ValueError(f"plugin function {index} is_async must be a boolean")
    try:
        return PythonFunctionRef(
            bundle_id=bundle_id,
            bundle_digest=_sha256_digest(
                payload["bundle_digest"],
                field_name=f"plugin function {index} bundle_digest",
            ),
            module_relative_path=module_relative_path,
            function_name=function_name,
            source_digest=_sha256_digest(
                payload["source_digest"],
                field_name=f"plugin function {index} source_digest",
            ),
            is_async=is_async,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"plugin function {index} is invalid: {exc}") from exc


def _approved_generation_path(value: object, *, bundle_digest: str) -> str:
    text = _bounded_catalog_text(
        value,
        field_name="approved_generation_root",
        max_length=_PLUGIN_PATH_LENGTH,
    )
    candidate = Path(text)
    if not candidate.is_absolute():
        raise ValueError("approved_generation_root must be absolute")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError("approved_generation_root does not exist") from exc
    approved_root = plugin_generations_dir().resolve()
    if (
        resolved.parent != approved_root
        or resolved.name != bundle_digest
        or not resolved.is_dir()
        or _is_reparse_point(resolved)
    ):
        raise ValueError(
            "approved_generation_root must be a direct immutable generation child"
        )
    return str(resolved)


def _plugin_bundle_ref(
    value: PluginBundleRef | Mapping[str, object],
    *,
    index: int,
    function_offset: int,
) -> PluginBundleRef:
    payload: Mapping[str, object]
    if isinstance(value, PluginBundleRef):
        payload = {
            "owner_id": value.owner_id,
            "version": value.version,
            "generation_id": value.generation_id,
            "bundle_digest": value.bundle_digest,
            "approved_generation_root": value.approved_generation_root,
            "functions": [_python_function_ref_payload(item) for item in value.functions],
            "unavailable_reason": value.unavailable_reason,
        }
    elif isinstance(value, Mapping):
        payload = value
    else:
        raise ValueError(f"plugin bundle {index} must be a mapping")
    expected_fields = {
        "owner_id",
        "version",
        "generation_id",
        "bundle_digest",
        "approved_generation_root",
        "functions",
        "unavailable_reason",
    }
    if set(payload) != expected_fields:
        raise ValueError(f"plugin bundle {index} has unexpected fields")
    owner_id = _logical_catalog_identifier(
        _bounded_catalog_text(
            payload["owner_id"],
            field_name=f"plugin bundle {index} owner_id",
            max_length=_PLUGIN_OWNER_LENGTH,
        ),
        field_name=f"plugin bundle {index} owner_id",
    )
    version = _bounded_catalog_text(
        payload["version"],
        field_name=f"plugin bundle {index} version",
        max_length=_PLUGIN_VERSION_LENGTH,
        allow_empty=True,
    )
    generation_id = _sha256_digest(
        payload["generation_id"],
        field_name=f"plugin bundle {index} generation_id",
    )
    bundle_digest = _sha256_digest(
        payload["bundle_digest"],
        field_name=f"plugin bundle {index} bundle_digest",
    )
    raw_functions = payload["functions"]
    if isinstance(raw_functions, (str, bytes)) or not isinstance(
        raw_functions, Sequence
    ):
        raise ValueError(f"plugin bundle {index} functions must be a list")
    if len(raw_functions) > _PLUGIN_FUNCTION_LIMIT - function_offset:
        raise ValueError("plugin_bundles contains too many functions")
    functions = tuple(
        _python_function_ref(item, index=function_offset + offset)
        for offset, item in enumerate(raw_functions)
    )
    unavailable_reason = _bounded_catalog_text(
        payload["unavailable_reason"],
        field_name=f"plugin bundle {index} unavailable_reason",
        max_length=_PLUGIN_UNAVAILABLE_REASON_LENGTH,
        allow_empty=True,
    )
    try:
        return PluginBundleRef(
            owner_id=owner_id,
            version=version,
            generation_id=generation_id,
            bundle_digest=bundle_digest,
            approved_generation_root=_approved_generation_path(
                payload["approved_generation_root"],
                bundle_digest=bundle_digest,
            ),
            functions=functions,
            unavailable_reason=unavailable_reason,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"plugin bundle {index} is invalid: {exc}") from exc


def normalize_plugin_bundle_refs(
    value: object,
) -> tuple[PluginBundleRef, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("plugin_bundles must be a list")
    if len(value) > _PLUGIN_BUNDLE_LIMIT:
        raise ValueError("plugin_bundles contains too many bundles")
    bundles: list[PluginBundleRef] = []
    function_offset = 0
    for index, item in enumerate(value):
        bundle = _plugin_bundle_ref(
            item,
            index=index,
            function_offset=function_offset,
        )
        function_offset += len(bundle.functions)
        if function_offset > _PLUGIN_FUNCTION_LIMIT:
            raise ValueError("plugin_bundles contains too many functions")
        bundles.append(bundle)
    owners = [bundle.owner_id for bundle in bundles]
    if len(owners) != len(set(owners)):
        raise ValueError("plugin_bundles contains duplicate owner ids")
    functions = [function for bundle in bundles for function in bundle.functions]
    if len(functions) != len(set(functions)):
        raise ValueError("plugin_bundles contains duplicate function refs")
    return tuple(bundles)


def _plugin_bundle_payload(bundle: PluginBundleRef) -> dict[str, object]:
    return {
        "owner_id": bundle.owner_id,
        "version": bundle.version,
        "generation_id": bundle.generation_id,
        "bundle_digest": bundle.bundle_digest,
        "approved_generation_root": bundle.approved_generation_root,
        "functions": [_python_function_ref_payload(item) for item in bundle.functions],
        "unavailable_reason": bundle.unavailable_reason,
    }


def _plugin_agreement(
    plugin_bundles: object,
    plugin_fingerprint: object,
    runtime_fingerprint: object,
    *,
    catalog_fingerprint: str,
) -> tuple[tuple[PluginBundleRef, ...], str, str]:
    bundles = normalize_plugin_bundle_refs(plugin_bundles)
    if not plugin_fingerprint:
        if bundles:
            raise ValueError("plugin_fingerprint is required when plugin_bundles is non-empty")
        plugin_digest = EMPTY_PLUGIN_FINGERPRINT
    else:
        plugin_digest = _plugin_fingerprint(plugin_fingerprint)
    expected_runtime = runtime_registry_fingerprint(
        catalog_fingerprint,
        plugin_digest,
    )
    if runtime_fingerprint:
        supplied_runtime = _sha256_digest(
            runtime_fingerprint,
            field_name="runtime_registry_fingerprint",
        )
        if supplied_runtime != expected_runtime:
            raise ValueError(
                "runtime_registry_fingerprint does not match catalog and plugin fingerprints"
            )
    return bundles, plugin_digest, expected_runtime


def _logical_catalog_identifier(value: str, *, field_name: str) -> str:
    if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
        raise ValueError(f"{field_name} must be a path-free logical identifier.")
    if any(
        not (character.isalnum() or character in "._:@+-")
        for character in value
    ):
        raise ValueError(f"{field_name} must be a path-free logical identifier.")
    return value


def normalize_addon_runtime_config(
    value: object,
) -> tuple[tuple[str, bool], ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("addon_runtime_config must be a list")
    if len(value) > _ADDON_RUNTIME_CONFIG_LIMIT:
        raise ValueError("addon_runtime_config contains too many entries")
    normalized: dict[str, bool] = {}
    for index, raw_entry in enumerate(value):
        if isinstance(raw_entry, Mapping):
            if set(raw_entry) != {"addon_id", "enabled"}:
                raise ValueError(
                    f"addon_runtime_config[{index}] must contain addon_id and enabled"
                )
            raw_addon_id = raw_entry["addon_id"]
            enabled = raw_entry["enabled"]
        elif (
            isinstance(raw_entry, Sequence)
            and not isinstance(raw_entry, (str, bytes))
            and len(raw_entry) == 2
        ):
            raw_addon_id, enabled = raw_entry
        else:
            raise ValueError(
                f"addon_runtime_config[{index}] must be an add-on state"
            )
        if not isinstance(raw_addon_id, str):
            raise ValueError(
                f"addon_runtime_config[{index}].addon_id must be a string"
            )
        addon_id = raw_addon_id.strip()
        if not addon_id or len(addon_id) > _ADDON_RUNTIME_ID_LIMIT:
            raise ValueError(
                f"addon_runtime_config[{index}].addon_id must be 1 to "
                f"{_ADDON_RUNTIME_ID_LIMIT} characters"
            )
        _logical_catalog_identifier(
            addon_id,
            field_name=f"addon_runtime_config[{index}].addon_id",
        )
        if type(enabled) is not bool:
            raise ValueError(
                f"addon_runtime_config[{index}].enabled must be a boolean"
            )
        if addon_id in normalized:
            raise ValueError("addon_runtime_config contains duplicate add-on ids")
        normalized[addon_id] = enabled
    return tuple(sorted(normalized.items()))


def _addon_runtime_config_payload(
    value: tuple[tuple[str, bool], ...],
) -> list[dict[str, object]]:
    return [
        {"addon_id": addon_id, "enabled": enabled}
        for addon_id, enabled in normalize_addon_runtime_config(value)
    ]


def _canonical_catalog_type_id(value: str, *, field_name: str) -> str:
    try:
        validate_canonical_clr_type_id(value)
    except ClrTypeNameError as exc:
        raise ValueError(f"{field_name} must be a canonical CLR type ID.") from exc
    return value


def _catalog_revision_identity(
    value: object,
    *,
    kind: str,
    field_name: str,
) -> str:
    identity = _bounded_catalog_text(
        value,
        field_name=field_name,
        max_length=_CATALOG_REVISION_IDENTITY_LENGTH,
    )
    if kind == "family":
        return _logical_catalog_identifier(identity, field_name=field_name)
    if kind == "type":
        return _canonical_catalog_type_id(identity, field_name=field_name)
    endpoints = identity.split(" -> ")
    if len(endpoints) != 2 or not all(endpoints):
        raise ValueError(
            f"{field_name} must contain two canonical CLR type IDs."
        )
    for endpoint in endpoints:
        _canonical_catalog_type_id(endpoint, field_name=field_name)
    return identity


def _catalog_revision_record(
    value: CatalogRevisionRecord | Mapping[str, object],
    *,
    index: int,
) -> CatalogRevisionRecord:
    if isinstance(value, CatalogRevisionRecord):
        payload: Mapping[str, object] = {
            "kind": value.kind,
            "identity": value.identity,
            "payload_schema_version": value.payload_schema_version,
            "implementation_version": value.implementation_version,
            "owner_id": value.owner_id,
            "owner_version": value.owner_version,
            "semantic_digest": value.semantic_digest,
        }
    elif isinstance(value, Mapping):
        payload = value
    else:
        raise ValueError(f"catalog_revisions[{index}] must be a mapping.")
    expected_fields = {
        "kind",
        "identity",
        "payload_schema_version",
        "implementation_version",
        "owner_id",
        "owner_version",
        "semantic_digest",
    }
    if set(payload) != expected_fields:
        raise ValueError(
            f"catalog_revisions[{index}] must contain exactly "
            f"{sorted(expected_fields)!r}."
        )
    kind = _bounded_catalog_text(
        payload["kind"],
        field_name=f"catalog_revisions[{index}].kind",
        max_length=16,
    )
    if kind not in _CATALOG_REVISION_KINDS:
        raise ValueError(f"catalog_revisions[{index}].kind is invalid.")
    schema_version = payload["payload_schema_version"]
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version < 0
        or schema_version > MAX_PAYLOAD_SCHEMA_VERSION
        or (kind == "type" and schema_version == 0)
        or (kind in {"family", "conversion"} and schema_version != 0)
    ):
        raise ValueError(
            f"catalog_revisions[{index}].payload_schema_version is invalid."
        )
    return CatalogRevisionRecord(
        kind=kind,  # type: ignore[arg-type]
        identity=_catalog_revision_identity(
            payload["identity"],
            kind=kind,
            field_name=f"catalog_revisions[{index}].identity",
        ),
        payload_schema_version=schema_version,
        implementation_version=_logical_catalog_identifier(
            _bounded_catalog_text(
                payload["implementation_version"],
                field_name=f"catalog_revisions[{index}].implementation_version",
                max_length=_CATALOG_REVISION_VERSION_LENGTH,
                allow_empty=kind == "family",
            ),
            field_name=f"catalog_revisions[{index}].implementation_version",
        ),
        owner_id=_logical_catalog_identifier(
            _bounded_catalog_text(
                payload["owner_id"],
                field_name=f"catalog_revisions[{index}].owner_id",
                max_length=_CATALOG_REVISION_OWNER_LENGTH,
            ),
            field_name=f"catalog_revisions[{index}].owner_id",
        ),
        owner_version=_logical_catalog_identifier(
            _bounded_catalog_text(
                payload["owner_version"],
                field_name=f"catalog_revisions[{index}].owner_version",
                max_length=_CATALOG_REVISION_VERSION_LENGTH,
                allow_empty=True,
            ),
            field_name=f"catalog_revisions[{index}].owner_version",
        ),
        semantic_digest=_sha256_digest(
            payload["semantic_digest"],
            field_name=f"catalog_revisions[{index}].semantic_digest",
        ),
    )


def normalize_catalog_revisions(value: object) -> tuple[CatalogRevisionRecord, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("catalog_revisions must be a list.")
    if len(value) > _CATALOG_REVISION_RECORD_LIMIT:
        raise ValueError("catalog_revisions contains too many records.")
    records = tuple(
        _catalog_revision_record(item, index=index)
        for index, item in enumerate(value)
    )
    if records != tuple(
        sorted(
            records,
            key=lambda record: (
                record.kind,
                record.identity,
                record.payload_schema_version,
                record.implementation_version,
                record.owner_id,
                record.owner_version,
                record.semantic_digest,
            ),
        )
    ):
        raise ValueError("catalog_revisions must be deterministically sorted.")
    identities = [(record.kind, record.identity) for record in records]
    if len(identities) != len(set(identities)):
        raise ValueError("catalog_revisions contains duplicate identities.")
    return records


def catalog_revision_records(
    catalog: DataTypeCatalog,
) -> tuple[CatalogRevisionRecord, ...]:
    if not isinstance(catalog, DataTypeCatalog) or not catalog.is_frozen:
        raise ValueError("catalog agreement requires a frozen data-type catalog.")
    records: list[CatalogRevisionRecord] = []
    for snapshot_record in catalog.snapshot():
        kind = snapshot_record.get("kind")
        semantic_digest = _catalog_snapshot_record_digest(snapshot_record)
        if kind == "family":
            records.append(
                CatalogRevisionRecord(
                    kind="family",
                    identity=str(snapshot_record["family_id"]),
                    payload_schema_version=0,
                    implementation_version="",
                    owner_id=str(snapshot_record["owner_id"]),
                    owner_version=str(snapshot_record["owner_version"]),
                    semantic_digest=semantic_digest,
                )
            )
        elif kind == "type":
            records.append(
                CatalogRevisionRecord(
                    kind="type",
                    identity=str(snapshot_record["type_id"]),
                    payload_schema_version=int(
                        snapshot_record["payload_schema_version"]
                    ),
                    implementation_version=str(
                        snapshot_record["implementation_version"]
                    ),
                    owner_id=str(snapshot_record["owner_id"]),
                    owner_version=str(snapshot_record["owner_version"]),
                    semantic_digest=semantic_digest,
                )
            )
        elif kind == "conversion":
            records.append(
                CatalogRevisionRecord(
                    kind="conversion",
                    identity=(
                        f"{snapshot_record['source_type_id']} -> "
                        f"{snapshot_record['target_type_id']}"
                    ),
                    payload_schema_version=0,
                    implementation_version=str(
                        snapshot_record["implementation_version"]
                    ),
                    owner_id=str(snapshot_record["owner_id"]),
                    owner_version=str(snapshot_record["owner_version"]),
                    semantic_digest=semantic_digest,
                )
            )
    return normalize_catalog_revisions(
        sorted(
            records,
            key=lambda record: (
                record.kind,
                record.identity,
                record.payload_schema_version,
                record.implementation_version,
                record.owner_id,
                record.owner_version,
                record.semantic_digest,
            ),
        )
    )


def _catalog_snapshot_record_digest(
    snapshot_record: Mapping[str, object],
) -> str:
    semantic_record = {
        str(key): value
        for key, value in snapshot_record.items()
        if key != "source_label"
    }
    payload = json.dumps(
        semantic_record,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def catalog_agreement(
    catalog: DataTypeCatalog,
) -> tuple[str, tuple[CatalogRevisionRecord, ...]]:
    return _catalog_fingerprint(catalog.fingerprint()), catalog_revision_records(catalog)


def catalog_agreement_from_payload(
    payload: Mapping[str, object],
) -> tuple[str, tuple[CatalogRevisionRecord, ...]]:
    if "catalog_fingerprint" not in payload or "catalog_revisions" not in payload:
        raise ValueError(
            "start_run requires catalog_fingerprint and catalog_revisions."
        )
    return (
        _catalog_fingerprint(payload["catalog_fingerprint"]),
        normalize_catalog_revisions(payload["catalog_revisions"]),
    )


def _catalog_revision_payload(
    record: CatalogRevisionRecord,
) -> dict[str, object]:
    normalized = _catalog_revision_record(record, index=0)
    return {
        "kind": normalized.kind,
        "identity": normalized.identity,
        "payload_schema_version": normalized.payload_schema_version,
        "implementation_version": normalized.implementation_version,
        "owner_id": normalized.owner_id,
        "owner_version": normalized.owner_version,
        "semantic_digest": normalized.semantic_digest,
    }


def catalog_mismatch_message(
    expected_fingerprint: str,
    expected_revisions: object,
    worker_catalog: DataTypeCatalog,
) -> str:
    expected_fingerprint = _catalog_fingerprint(expected_fingerprint)
    expected_records = normalize_catalog_revisions(expected_revisions)
    worker_fingerprint, worker_records = catalog_agreement(worker_catalog)
    if expected_fingerprint == worker_fingerprint:
        return ""

    expected_by_identity = {
        (record.kind, record.identity): record for record in expected_records
    }
    worker_by_identity = {
        (record.kind, record.identity): record for record in worker_records
    }
    changed_keys = [
        key
        for key in sorted(set(expected_by_identity) | set(worker_by_identity))
        if expected_by_identity.get(key) != worker_by_identity.get(key)
    ]
    details: list[str] = []
    for key in changed_keys[:_CATALOG_DIAGNOSTIC_DIFFERENCE_LIMIT]:
        desktop = expected_by_identity.get(key)
        worker = worker_by_identity.get(key)
        if worker is None:
            details.append(
                f"{_trusted_catalog_revision_label(desktop)}: desktop-only"
            )
            continue
        label = _trusted_catalog_revision_label(worker)
        if desktop is None:
            details.append(f"{label}: worker-only")
            continue
        details.append(
            f"{label}: desktop digest={desktop.semantic_digest[:12]}, "
            f"worker digest={worker.semantic_digest[:12]}"
        )
    if len(changed_keys) > _CATALOG_DIAGNOSTIC_DIFFERENCE_LIMIT:
        details.append(
            f"{len(changed_keys) - _CATALOG_DIAGNOSTIC_DIFFERENCE_LIMIT} "
            "more differences"
        )
    if not details:
        details.append(
            "compact semantic records agree; other catalog metadata differs"
        )
    message_prefix = (
        "Data-type catalog mismatch before execution: "
        f"desktop={expected_fingerprint}, worker={worker_fingerprint}. "
    )
    return _bounded_catalog_mismatch_message(
        message_prefix,
        details,
        total_differences=len(changed_keys),
    )


def _bounded_catalog_mismatch_message(
    prefix: str,
    details: list[str],
    *,
    total_differences: int,
) -> str:
    message = prefix + "; ".join(details)
    if len(message) <= _CATALOG_DIAGNOSTIC_MESSAGE_LENGTH:
        return message

    kept_details = list(details)
    while kept_details:
        kept_details.pop()
        shown = min(
            len(kept_details),
            total_differences,
            _CATALOG_DIAGNOSTIC_DIFFERENCE_LIMIT,
        )
        marker = (
            "[catalog mismatch details truncated: "
            f"showing {shown} of {total_differences} differences]"
        )
        message = prefix + "; ".join((*kept_details, marker))
        if len(message) <= _CATALOG_DIAGNOSTIC_MESSAGE_LENGTH:
            return message

    marker = (
        "[catalog mismatch details truncated: "
        f"showing 0 of {total_differences} differences]"
    )
    return prefix + marker


def _trusted_catalog_revision_label(record: CatalogRevisionRecord) -> str:
    identity = record.identity
    if len(identity) > _CATALOG_DIAGNOSTIC_IDENTITY_LENGTH:
        digest_tag = f"#{record.semantic_digest[:12]}"
        readable_length = (
            _CATALOG_DIAGNOSTIC_IDENTITY_LENGTH - len("...") - len(digest_tag)
        )
        prefix_length = (readable_length * 2) // 3
        suffix_length = readable_length - prefix_length
        identity = (
            f"{identity[:prefix_length]}..."
            f"{identity[-suffix_length:]}{digest_tag}"
        )
    revisions = [f"owner={record.owner_id}"]
    if record.payload_schema_version:
        revisions.insert(0, f"schema={record.payload_schema_version}")
    return (
        f"{record.kind} {identity} "
        f"({', '.join(revisions)})"
    )


def _execution_backend_from_payload(
    payload: Mapping[str, Any],
) -> ExecutionBackendSelection:
    if "execution_backend" not in payload:
        return ExecutionBackendSelection()
    value = payload["execution_backend"]
    if not isinstance(value, Mapping):
        raise ValueError("execution_backend must be a mapping.")
    normalized = {
        "backend_id": _string_field(
            value,
            "backend_id",
            default=ExecutionBackendSelection().backend_id,
            strip=True,
        ),
        "isolation": _string_field(
            value,
            "isolation",
            default="process",
            strip=True,
        ),
        "reason": _string_field(value, "reason", strip=True),
        "trusted_in_process": _bool_field(value, "trusted_in_process"),
        "external_subprocess": _bool_field(value, "external_subprocess"),
        "python_executable": _string_field(
            value,
            "python_executable",
            strip=True,
        ),
        "runtime_backend_ids": _string_list_field(value, "runtime_backend_ids"),
    }
    return coerce_execution_backend_selection(normalized)


def _string_value(value: Any, *, field_name: str) -> str:
    return _string_field({field_name: value}, field_name)


def _bool_value(value: Any, *, field_name: str) -> bool:
    return _bool_field({field_name: value}, field_name)


def _float_value(value: Any, *, field_name: str) -> float:
    return _float_field({field_name: value}, field_name)


def _nonnegative_int_value(value: Any, *, field_name: str) -> int:
    return _nonnegative_int_field({field_name: value}, field_name)


def _literal_value(
    value: Any,
    *,
    field_name: str,
    allowed_values: frozenset[str],
) -> str:
    normalized = _string_value(value, field_name=field_name)
    if normalized not in allowed_values:
        raise ValueError(f"invalid {field_name}: {normalized!r}")
    return normalized


def _literal_field(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    allowed_values: frozenset[str],
    default: str,
) -> str:
    return _literal_value(
        _string_field(payload, field_name, default=default),
        field_name=field_name,
        allowed_values=allowed_values,
    )


def _fixed_run_event_state(
    payload: Mapping[str, Any],
    *,
    expected: str,
) -> str:
    state = _string_field(payload, "state", default=expected)
    if state != expected:
        raise ValueError(f"state must be {expected!r}.")
    return state


def _serialize_scalar_payload(
    value: Any,
    *,
    catalog: DataTypeCatalog | None,
) -> dict[str, Any]:
    if type(value) not in _SCALAR_PROTOCOL_TYPES:
        raise TypeError(f"Unsupported protocol DTO: {type(value).__name__}")
    if type(value) is RunStateEvent:
        _literal_value(
            value.state,
            field_name="state",
            allowed_values=_ENGINE_STATE_VALUES,
        )
        _literal_value(
            value.transition,
            field_name="transition",
            allowed_values=_RUN_TRANSITION_VALUES,
        )
    expected_state = _FIXED_RUN_EVENT_STATES.get(type(value))
    if expected_state is not None and value.state != expected_state:
        actual_state = _string_value(value.state, field_name="state")
        raise ValueError(
            f"state must be {expected_state!r}; received {actual_state!r}."
        )
    payload: dict[str, Any] = {}
    for field_info in fields(value):
        field_value = getattr(value, field_info.name)
        if field_info.name == "fatal":
            field_value = _bool_value(field_value, field_name=field_info.name)
        elif field_info.name == "started_at_epoch_ms":
            field_value = _float_value(field_value, field_name=field_info.name)
        else:
            field_value = _string_value(field_value, field_name=field_info.name)
        payload[field_info.name] = serialize_runtime_value(
            field_value,
            catalog=catalog,
        )
    return payload


def _serialize_viewer_value(
    value: Any,
    *,
    field_name: str,
    catalog: DataTypeCatalog | None,
) -> Any:
    try:
        serialized = serialize_runtime_value(value, catalog=catalog)
    except TypeError as exc:
        raise TypeError(f"{field_name} must be JSON-safe: {exc}") from exc
    if serialized is None or isinstance(serialized, (str, int, float, bool)):
        return serialized
    if isinstance(serialized, list):
        return [
            _serialize_viewer_value(item, field_name=field_name, catalog=catalog)
            for item in serialized
        ]
    if isinstance(serialized, tuple):
        return [
            _serialize_viewer_value(item, field_name=field_name, catalog=catalog)
            for item in serialized
        ]
    if isinstance(serialized, Mapping):
        marker = serialized.get(_RUNTIME_VALUE_MARKER_KEY)
        if marker in _VIEWER_RUNTIME_MARKERS:
            return dict(serialized)
        normalized: dict[str, Any] = {}
        for key, item in serialized.items():
            if not isinstance(key, str):
                raise TypeError(f"{field_name} keys must be strings.")
            normalized[key] = _serialize_viewer_value(
                item,
                field_name=field_name,
                catalog=catalog,
            )
        return normalized
    raise TypeError(
        f"{field_name} must be JSON-safe and may only contain scalar values, lists, "
        "dictionaries, runtime handle refs, or runtime artifact refs."
    )


def _serialize_viewer_mapping(
    value: Any,
    *,
    field_name: str,
    catalog: DataTypeCatalog | None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a dictionary payload.")
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"{field_name} keys must be strings.")
        normalized[key] = _serialize_viewer_value(
            item,
            field_name=field_name,
            catalog=catalog,
        )
    return normalized


def _deserialize_viewer_mapping(
    payload: Mapping[str, Any],
    field_name: str,
    *,
    catalog: DataTypeCatalog | None,
) -> dict[str, Any]:
    if field_name not in payload:
        return {}
    value = payload[field_name]
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be a dictionary payload.")
    decoded = deserialize_runtime_value(value, catalog=catalog)
    if not isinstance(decoded, Mapping):
        raise ValueError(f"{field_name} must decode to a dictionary payload.")
    if any(not isinstance(key, str) for key in decoded):
        raise ValueError(f"{field_name} keys must be strings.")
    return dict(decoded)


def normalize_target_node_ids(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        candidates = tuple(value)
    else:
        raise ValueError("target_node_ids must be a list.")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, str):
            raise ValueError(f"target_node_ids[{index}] must be a string.")
        node_id = candidate.strip()
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        normalized.append(node_id)
    return tuple(normalized)


def normalize_root_execution_errors(value: Any) -> tuple[RootExecutionError, ...]:
    if isinstance(value, RootExecutionError):
        candidates = (value,)
    elif isinstance(value, (list, tuple)):
        candidates = tuple(value)
    else:
        raise ValueError("settled result errors must be a list")
    normalized: list[RootExecutionError] = []
    for candidate in candidates:
        if isinstance(candidate, RootExecutionError):
            normalized.append(candidate)
            continue
        if not isinstance(candidate, Mapping):
            raise ValueError(
                "settled result errors must be RootExecutionError mappings"
            )
        normalized.append(
            RootExecutionError(
                node_id=_string_field(candidate, "node_id"),
                error=_string_field(candidate, "error"),
                traceback=_string_field(candidate, "traceback"),
            )
        )
    return tuple(normalized)


def normalize_settled_port_result(
    value: Any,
    *,
    catalog: DataTypeCatalog | None = None,
) -> SettledPortResult:
    if isinstance(value, SettledPortResult):
        payload: Mapping[str, Any] = {
            "status": value.status,
            "value": value.value,
            "errors": value.errors,
        }
    elif isinstance(value, Mapping):
        payload = value
    else:
        decoded = deserialize_runtime_value(value, catalog=catalog)
        if not isinstance(decoded, Mapping):
            raise ValueError("settled port result must be a mapping")
        payload = decoded
    status = _string_field(
        payload,
        "status",
        default="empty",
        strip=True,
    ).lower()
    if status not in {"value", "empty", "failed"}:
        raise ValueError(f"invalid settled port status: {status!r}")
    tree = payload.get("value")
    if tree is not None and not isinstance(tree, DataTree):
        tree = deserialize_runtime_value(tree, catalog=catalog)
    errors = normalize_root_execution_errors(payload.get("errors", ()))
    if status == "value":
        if not isinstance(tree, DataTree):
            raise ValueError("value settled port results require a DataTree")
        if errors:
            raise ValueError("value settled port results cannot contain errors")
        return SettledPortResult(status="value", value=tree)
    if tree is not None:
        raise ValueError(f"{status} settled port results cannot contain a value")
    if status == "empty":
        if errors:
            raise ValueError("empty settled port results cannot contain errors")
        return SettledPortResult(status="empty")
    if not errors:
        raise ValueError("failed settled port results require a root error")
    return SettledPortResult(status="failed", errors=errors)


def normalize_settled_output_mapping(
    value: Any,
    *,
    catalog: DataTypeCatalog | None = None,
) -> dict[str, SettledPortResult]:
    if isinstance(value, Mapping):
        payload = value
    else:
        payload = deserialize_runtime_value(value, catalog=catalog)
    if not isinstance(payload, Mapping):
        raise ValueError("settled output mapping must be a mapping")
    normalized: dict[str, SettledPortResult] = {}
    for raw_key, raw_result in payload.items():
        if not isinstance(raw_key, str):
            raise ValueError("settled output mapping keys must be strings")
        key = raw_key.strip()
        if not key:
            raise ValueError("settled output mapping keys must be non-empty")
        normalized[key] = normalize_settled_port_result(raw_result, catalog=catalog)
    return normalized


def _root_error_to_dict(error: RootExecutionError) -> dict[str, str]:
    return {
        "node_id": _string_value(error.node_id, field_name="node_id"),
        "error": _string_value(error.error, field_name="error"),
        "traceback": _string_value(error.traceback, field_name="traceback"),
    }


def _settled_port_to_dict(
    result: SettledPortResult,
    *,
    catalog: DataTypeCatalog | None,
) -> dict[str, Any]:
    normalized = normalize_settled_port_result(result, catalog=catalog)
    return {
        "status": normalized.status,
        "value": serialize_runtime_value(normalized.value, catalog=catalog),
        "errors": [_root_error_to_dict(error) for error in normalized.errors],
    }


def _settled_outputs_to_dict(
    values: Mapping[str, SettledPortResult],
    *,
    catalog: DataTypeCatalog | None,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, result in values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("settled output mapping keys must be non-empty strings")
        normalized[key.strip()] = _settled_port_to_dict(result, catalog=catalog)
    return normalized


def command_to_dict(
    command: WorkerCommand,
    *,
    catalog: DataTypeCatalog | None = None,
) -> dict[str, Any]:
    if isinstance(command, StartRunCommand):
        if (
            catalog is not None
            and not command.catalog_fingerprint
            and not command.catalog_revisions
        ):
            fingerprint, revisions = catalog_agreement(catalog)
            command = replace(
                command,
                catalog_fingerprint=fingerprint,
                catalog_revisions=revisions,
            )
        command = coerce_start_run_command(command, catalog=catalog)
        execution_backend = _execution_backend_from_payload(
            {"execution_backend": command.execution_backend.to_payload()}
        )
        payload = {
            "type": _string_value(command.type, field_name="type"),
            "run_id": _string_value(command.run_id, field_name="run_id"),
            "project_path": _string_value(
                command.project_path,
                field_name="project_path",
            ),
            "workspace_id": _string_value(
                command.workspace_id,
                field_name="workspace_id",
            ),
            "trigger": serialize_runtime_value(command.trigger, catalog=catalog),
            "runtime_snapshot": command.runtime_snapshot.to_document(catalog=catalog),
            "execution_backend": execution_backend.to_payload(),
            "target_node_ids": list(command.target_node_ids),
            "trigger_publications": _settled_outputs_to_dict(
                command.trigger_publications,
                catalog=catalog,
            ),
            "trigger_captures": _settled_outputs_to_dict(
                command.trigger_captures,
                catalog=catalog,
            ),
            "clicked_trigger_node_id": _string_value(
                command.clicked_trigger_node_id,
                field_name="clicked_trigger_node_id",
            ),
            "developer_mode": _bool_value(
                command.developer_mode,
                field_name="developer_mode",
            ),
            "catalog_fingerprint": command.catalog_fingerprint,
            "catalog_revisions": [
                _catalog_revision_payload(record)
                for record in command.catalog_revisions
            ],
            "plugin_bundles": [
                _plugin_bundle_payload(bundle) for bundle in command.plugin_bundles
            ],
            "plugin_fingerprint": command.plugin_fingerprint,
            "runtime_registry_fingerprint": command.runtime_registry_fingerprint,
            "registry_contract_fingerprint": command.registry_contract_fingerprint,
            "addon_runtime_config": _addon_runtime_config_payload(
                command.addon_runtime_config
            ),
        }
        dict_to_command(payload, catalog=catalog)
        return payload
    if isinstance(command, QueryViewerSessionCommand):
        return {
            "type": _string_value(command.type, field_name="type"),
            "request_id": _string_value(
                command.request_id,
                field_name="request_id",
            ),
            "workspace_id": _string_value(
                command.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(command.node_id, field_name="node_id"),
            "session_id": _string_value(
                command.session_id,
                field_name="session_id",
            ),
            "backend_id": _string_value(
                command.backend_id,
                field_name="backend_id",
            ),
            "query_type": _string_value(
                command.query_type,
                field_name="query_type",
            ),
            "payload": _serialize_viewer_mapping(
                command.payload,
                field_name="payload",
                catalog=catalog,
            ),
            "options": _serialize_viewer_mapping(
                command.options,
                field_name="options",
                catalog=catalog,
            ),
        }
    if isinstance(command, (OpenViewerSessionCommand, UpdateViewerSessionCommand)):
        return {
            "type": _string_value(command.type, field_name="type"),
            "request_id": _string_value(
                command.request_id,
                field_name="request_id",
            ),
            "workspace_id": _string_value(
                command.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(command.node_id, field_name="node_id"),
            "session_id": _string_value(
                command.session_id,
                field_name="session_id",
            ),
            "backend_id": _string_value(
                command.backend_id,
                field_name="backend_id",
            ),
            "data_refs": _serialize_viewer_mapping(
                command.data_refs, field_name="data_refs", catalog=catalog
            ),
            "transport": _serialize_viewer_mapping(
                command.transport, field_name="transport", catalog=catalog
            ),
            "transport_revision": _nonnegative_int_value(
                command.transport_revision,
                field_name="transport_revision",
            ),
            "live_open_status": _string_value(
                command.live_open_status,
                field_name="live_open_status",
            ),
            "live_open_blocker": _serialize_viewer_mapping(
                command.live_open_blocker,
                field_name="live_open_blocker",
                catalog=catalog,
            ),
            "camera_state": _serialize_viewer_mapping(
                command.camera_state, field_name="camera_state", catalog=catalog
            ),
            "playback_state": _serialize_viewer_mapping(
                command.playback_state, field_name="playback_state", catalog=catalog
            ),
            "summary": _serialize_viewer_mapping(
                command.summary, field_name="summary", catalog=catalog
            ),
            "options": _serialize_viewer_mapping(
                command.options, field_name="options", catalog=catalog
            ),
        }
    if isinstance(command, CloseViewerSessionCommand):
        return {
            "type": _string_value(command.type, field_name="type"),
            "request_id": _string_value(
                command.request_id,
                field_name="request_id",
            ),
            "workspace_id": _string_value(
                command.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(command.node_id, field_name="node_id"),
            "session_id": _string_value(
                command.session_id,
                field_name="session_id",
            ),
            "options": _serialize_viewer_mapping(
                command.options, field_name="options", catalog=catalog
            ),
        }
    if isinstance(command, MaterializeViewerDataCommand):
        return {
            "type": _string_value(command.type, field_name="type"),
            "request_id": _string_value(
                command.request_id,
                field_name="request_id",
            ),
            "workspace_id": _string_value(
                command.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(command.node_id, field_name="node_id"),
            "session_id": _string_value(
                command.session_id,
                field_name="session_id",
            ),
            "backend_id": _string_value(
                command.backend_id,
                field_name="backend_id",
            ),
            "options": _serialize_viewer_mapping(
                command.options, field_name="options", catalog=catalog
            ),
        }
    return _serialize_scalar_payload(command, catalog=catalog)


def event_to_dict(
    event: WorkerEvent,
    *,
    catalog: DataTypeCatalog | None = None,
) -> dict[str, Any]:
    if isinstance(event, NodeSettledEvent):
        status = _string_value(event.status, field_name="status").strip().lower()
        if status not in {"completed", "empty", "failed", "blocked"}:
            raise ValueError(f"invalid node settlement status: {status!r}")
        warnings = _string_list_field(
            {"warnings": event.warnings},
            "warnings",
        )
        errors = normalize_root_execution_errors(event.errors)
        return {
            "type": _string_value(event.type, field_name="type"),
            "run_id": _string_value(event.run_id, field_name="run_id"),
            "workspace_id": _string_value(
                event.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(event.node_id, field_name="node_id"),
            "status": status,
            "elapsed_ms": _float_value(
                event.elapsed_ms,
                field_name="elapsed_ms",
            ),
            "outputs": _settled_outputs_to_dict(event.outputs, catalog=catalog),
            "errors": [_root_error_to_dict(error) for error in errors],
            "warnings": list(warnings),
        }
    if isinstance(event, (TriggerCaptureSettledEvent, TriggerPublishedEvent)):
        return {
            "type": _string_value(event.type, field_name="type"),
            "run_id": _string_value(event.run_id, field_name="run_id"),
            "workspace_id": _string_value(
                event.workspace_id,
                field_name="workspace_id",
            ),
            "trigger_node_id": _string_value(
                event.trigger_node_id,
                field_name="trigger_node_id",
            ),
            "result": _settled_port_to_dict(event.result, catalog=catalog),
        }
    if isinstance(event, ViewerQueryResultEvent):
        return {
            "type": _string_value(event.type, field_name="type"),
            "request_id": _string_value(
                event.request_id,
                field_name="request_id",
            ),
            "workspace_id": _string_value(
                event.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(event.node_id, field_name="node_id"),
            "session_id": _string_value(
                event.session_id,
                field_name="session_id",
            ),
            "backend_id": _string_value(
                event.backend_id,
                field_name="backend_id",
            ),
            "query_type": _string_value(
                event.query_type,
                field_name="query_type",
            ),
            "supported": _bool_value(event.supported, field_name="supported"),
            "value": _serialize_viewer_mapping(
                event.value, field_name="value", catalog=catalog
            ),
            "explanation": _string_value(
                event.explanation,
                field_name="explanation",
            ),
        }
    if isinstance(
        event,
        (
            ViewerSessionOpenedEvent,
            ViewerSessionUpdatedEvent,
            ViewerDataMaterializedEvent,
        ),
    ):
        return {
            "type": _string_value(event.type, field_name="type"),
            "request_id": _string_value(
                event.request_id,
                field_name="request_id",
            ),
            "workspace_id": _string_value(
                event.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(event.node_id, field_name="node_id"),
            "session_id": _string_value(
                event.session_id,
                field_name="session_id",
            ),
            "backend_id": _string_value(
                event.backend_id,
                field_name="backend_id",
            ),
            "data_refs": _serialize_viewer_mapping(
                event.data_refs, field_name="data_refs", catalog=catalog
            ),
            "transport": _serialize_viewer_mapping(
                event.transport, field_name="transport", catalog=catalog
            ),
            "transport_revision": _nonnegative_int_value(
                event.transport_revision,
                field_name="transport_revision",
            ),
            "live_open_status": _string_value(
                event.live_open_status,
                field_name="live_open_status",
            ),
            "live_open_blocker": _serialize_viewer_mapping(
                event.live_open_blocker,
                field_name="live_open_blocker",
                catalog=catalog,
            ),
            "camera_state": _serialize_viewer_mapping(
                event.camera_state, field_name="camera_state", catalog=catalog
            ),
            "playback_state": _serialize_viewer_mapping(
                event.playback_state, field_name="playback_state", catalog=catalog
            ),
            "summary": _serialize_viewer_mapping(
                event.summary, field_name="summary", catalog=catalog
            ),
            "options": _serialize_viewer_mapping(
                event.options, field_name="options", catalog=catalog
            ),
        }
    if isinstance(event, ViewerSessionClosedEvent):
        return {
            "type": _string_value(event.type, field_name="type"),
            "request_id": _string_value(
                event.request_id,
                field_name="request_id",
            ),
            "workspace_id": _string_value(
                event.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(event.node_id, field_name="node_id"),
            "session_id": _string_value(
                event.session_id,
                field_name="session_id",
            ),
            "backend_id": _string_value(
                event.backend_id,
                field_name="backend_id",
            ),
            "transport": _serialize_viewer_mapping(
                event.transport, field_name="transport", catalog=catalog
            ),
            "transport_revision": _nonnegative_int_value(
                event.transport_revision,
                field_name="transport_revision",
            ),
            "live_open_status": _string_value(
                event.live_open_status,
                field_name="live_open_status",
            ),
            "live_open_blocker": _serialize_viewer_mapping(
                event.live_open_blocker,
                field_name="live_open_blocker",
                catalog=catalog,
            ),
            "camera_state": _serialize_viewer_mapping(
                event.camera_state, field_name="camera_state", catalog=catalog
            ),
            "playback_state": _serialize_viewer_mapping(
                event.playback_state, field_name="playback_state", catalog=catalog
            ),
            "summary": _serialize_viewer_mapping(
                event.summary, field_name="summary", catalog=catalog
            ),
            "options": _serialize_viewer_mapping(
                event.options, field_name="options", catalog=catalog
            ),
        }
    if isinstance(event, ViewerSessionFailedEvent):
        return {
            "type": _string_value(event.type, field_name="type"),
            "request_id": _string_value(
                event.request_id,
                field_name="request_id",
            ),
            "workspace_id": _string_value(
                event.workspace_id,
                field_name="workspace_id",
            ),
            "node_id": _string_value(event.node_id, field_name="node_id"),
            "session_id": _string_value(
                event.session_id,
                field_name="session_id",
            ),
            "command": _string_value(event.command, field_name="command"),
            "error": _string_value(event.error, field_name="error"),
        }
    return _serialize_scalar_payload(event, catalog=catalog)


def _start_run_command_from_payload(
    payload: Mapping[str, Any],
    *,
    catalog: DataTypeCatalog | None,
) -> StartRunCommand:
    required_plugin_fields = {
        "plugin_bundles",
        "plugin_fingerprint",
        "runtime_registry_fingerprint",
        "registry_contract_fingerprint",
        "addon_runtime_config",
    }
    if missing_plugin_fields := required_plugin_fields - set(payload):
        raise ValueError(
            "start_run requires plugin agreement fields: "
            + ", ".join(sorted(missing_plugin_fields))
        )
    if not isinstance(payload["plugin_bundles"], list):
        raise ValueError("start_run plugin_bundles must be a list")
    _plugin_fingerprint(payload["plugin_fingerprint"])
    _sha256_digest(
        payload["runtime_registry_fingerprint"],
        field_name="runtime_registry_fingerprint",
    )
    registry_contract_fingerprint = _sha256_digest(
        payload["registry_contract_fingerprint"],
        field_name="registry_contract_fingerprint",
    )
    addon_runtime_config = normalize_addon_runtime_config(
        payload["addon_runtime_config"]
    )
    catalog_fingerprint, catalog_revisions = catalog_agreement_from_payload(payload)
    if catalog is not None:
        mismatch = catalog_mismatch_message(
            catalog_fingerprint,
            catalog_revisions,
            catalog,
        )
        if mismatch:
            raise ValueError(mismatch)
    plugin_bundles, plugin_fingerprint, runtime_fingerprint = _plugin_agreement(
        payload.get("plugin_bundles", ()),
        payload.get("plugin_fingerprint", ""),
        payload.get("runtime_registry_fingerprint", ""),
        catalog_fingerprint=catalog_fingerprint,
    )
    raw_trigger = payload.get("trigger", {})
    if not isinstance(raw_trigger, Mapping):
        raise ValueError("trigger must be a mapping.")
    trigger_payload = deserialize_runtime_value(raw_trigger, catalog=catalog)
    if not isinstance(trigger_payload, Mapping):
        raise ValueError("trigger must decode to a mapping.")
    runtime_snapshot_payload = payload.get("runtime_snapshot")
    if not isinstance(runtime_snapshot_payload, Mapping):
        raise ValueError("start_run requires runtime_snapshot.")
    runtime_snapshot = coerce_runtime_snapshot(
        runtime_snapshot_payload,
        catalog=catalog,
    )
    if runtime_snapshot is None:
        raise ValueError("start_run requires runtime_snapshot.")
    return StartRunCommand(
        run_id=_string_field(payload, "run_id"),
        project_path=_string_field(payload, "project_path"),
        workspace_id=_string_field(payload, "workspace_id"),
        trigger=dict(trigger_payload),
        runtime_snapshot=runtime_snapshot,
        execution_backend=_execution_backend_from_payload(payload),
        target_node_ids=normalize_target_node_ids(payload.get("target_node_ids", ())),
        trigger_publications=normalize_settled_output_mapping(
            payload.get("trigger_publications", {}),
            catalog=catalog,
        ),
        trigger_captures=normalize_settled_output_mapping(
            payload.get("trigger_captures", {}),
            catalog=catalog,
        ),
        clicked_trigger_node_id=_string_field(
            payload,
            "clicked_trigger_node_id",
            strip=True,
        ),
        developer_mode=_bool_field(payload, "developer_mode"),
        catalog_fingerprint=catalog_fingerprint,
        catalog_revisions=catalog_revisions,
        plugin_bundles=plugin_bundles,
        plugin_fingerprint=plugin_fingerprint,
        runtime_registry_fingerprint=runtime_fingerprint,
        registry_contract_fingerprint=registry_contract_fingerprint,
        addon_runtime_config=addon_runtime_config,
    )


def coerce_start_run_command(
    command: StartRunCommand | Mapping[str, Any],
    *,
    catalog: DataTypeCatalog | None = None,
) -> StartRunCommand:
    if isinstance(command, StartRunCommand):
        if command.runtime_snapshot is None:
            raise ValueError("start_run requires runtime_snapshot.")
        if not isinstance(command.trigger, Mapping):
            raise ValueError("trigger must be a mapping.")
        if not isinstance(command.execution_backend, ExecutionBackendSelection):
            raise ValueError("execution_backend must be an ExecutionBackendSelection.")
        if not isinstance(command.developer_mode, bool):
            raise ValueError("developer_mode must be a boolean.")
        catalog_fingerprint = _catalog_fingerprint(command.catalog_fingerprint)
        catalog_revisions = normalize_catalog_revisions(command.catalog_revisions)
        if catalog is not None:
            mismatch = catalog_mismatch_message(
                catalog_fingerprint,
                catalog_revisions,
                catalog,
            )
            if mismatch:
                raise ValueError(mismatch)
        plugin_bundles, plugin_fingerprint, runtime_fingerprint = _plugin_agreement(
            command.plugin_bundles,
            command.plugin_fingerprint,
            command.runtime_registry_fingerprint,
            catalog_fingerprint=catalog_fingerprint,
        )
        registry_contract_fingerprint = _sha256_digest(
            command.registry_contract_fingerprint,
            field_name="registry_contract_fingerprint",
        )
        addon_runtime_config = normalize_addon_runtime_config(
            command.addon_runtime_config
        )
        return StartRunCommand(
            run_id=_string_field({"run_id": command.run_id}, "run_id"),
            project_path=_string_field(
                {"project_path": command.project_path},
                "project_path",
            ),
            workspace_id=_string_field(
                {"workspace_id": command.workspace_id},
                "workspace_id",
            ),
            trigger=dict(command.trigger),
            runtime_snapshot=command.runtime_snapshot,
            execution_backend=command.execution_backend,
            target_node_ids=normalize_target_node_ids(command.target_node_ids),
            trigger_publications=normalize_settled_output_mapping(
                command.trigger_publications,
                catalog=catalog,
            ),
            trigger_captures=normalize_settled_output_mapping(
                command.trigger_captures,
                catalog=catalog,
            ),
            clicked_trigger_node_id=_string_field(
                {"clicked_trigger_node_id": command.clicked_trigger_node_id},
                "clicked_trigger_node_id",
                strip=True,
            ),
            developer_mode=command.developer_mode,
            catalog_fingerprint=catalog_fingerprint,
            catalog_revisions=catalog_revisions,
            plugin_bundles=plugin_bundles,
            plugin_fingerprint=plugin_fingerprint,
            runtime_registry_fingerprint=runtime_fingerprint,
            registry_contract_fingerprint=registry_contract_fingerprint,
            addon_runtime_config=addon_runtime_config,
        )

    if (
        catalog is not None
        and "catalog_fingerprint" not in command
        and "catalog_revisions" not in command
    ):
        catalog_fingerprint, catalog_revisions = catalog_agreement(catalog)
    else:
        catalog_fingerprint, catalog_revisions = catalog_agreement_from_payload(
            command
        )
    if catalog is not None:
        mismatch = catalog_mismatch_message(
            catalog_fingerprint,
            catalog_revisions,
            catalog,
        )
        if mismatch:
            raise ValueError(mismatch)
    plugin_bundles, plugin_fingerprint, runtime_fingerprint = _plugin_agreement(
        command.get("plugin_bundles", ()),
        command.get("plugin_fingerprint", ""),
        command.get("runtime_registry_fingerprint", ""),
        catalog_fingerprint=catalog_fingerprint,
    )
    registry_contract_fingerprint = _sha256_digest(
        command.get("registry_contract_fingerprint", ""),
        field_name="registry_contract_fingerprint",
    )
    addon_runtime_config = normalize_addon_runtime_config(
        command.get("addon_runtime_config", ())
    )
    raw_trigger = command.get("trigger", {})
    if not isinstance(raw_trigger, Mapping):
        raise ValueError("trigger must be a mapping.")
    runtime_snapshot = coerce_runtime_snapshot(
        command.get("runtime_snapshot"),
        catalog=catalog,
    )
    if runtime_snapshot is None:
        raise ValueError("start_run requires runtime_snapshot.")
    return StartRunCommand(
        run_id=_string_field(command, "run_id"),
        project_path=_string_field(command, "project_path"),
        workspace_id=_string_field(command, "workspace_id"),
        trigger=dict(raw_trigger),
        runtime_snapshot=runtime_snapshot,
        execution_backend=_execution_backend_from_payload(command),
        target_node_ids=normalize_target_node_ids(command.get("target_node_ids", ())),
        trigger_publications=normalize_settled_output_mapping(
            command.get("trigger_publications", {}),
            catalog=catalog,
        ),
        trigger_captures=normalize_settled_output_mapping(
            command.get("trigger_captures", {}),
            catalog=catalog,
        ),
        clicked_trigger_node_id=_string_field(
            command,
            "clicked_trigger_node_id",
            strip=True,
        ),
        developer_mode=_bool_field(command, "developer_mode"),
        catalog_fingerprint=catalog_fingerprint,
        catalog_revisions=catalog_revisions,
        plugin_bundles=plugin_bundles,
        plugin_fingerprint=plugin_fingerprint,
        runtime_registry_fingerprint=runtime_fingerprint,
        registry_contract_fingerprint=registry_contract_fingerprint,
        addon_runtime_config=addon_runtime_config,
    )


def dict_to_command(
    payload: dict[str, Any],
    *,
    catalog: DataTypeCatalog | None = None,
) -> WorkerCommand:
    payload = dict(copy_json_safe(payload, field_name="worker command"))
    command_type = _string_field(payload, "type")
    if command_type == "start_run":
        return _start_run_command_from_payload(payload, catalog=catalog)
    if command_type == "stop_run":
        return StopRunCommand(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
        )
    if command_type == "pause_run":
        return PauseRunCommand(run_id=_string_field(payload, "run_id"))
    if command_type == "resume_run":
        return ResumeRunCommand(run_id=_string_field(payload, "run_id"))
    if command_type == "shutdown":
        return ShutdownCommand()
    if command_type == "open_viewer_session":
        return OpenViewerSessionCommand(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            data_refs=_deserialize_viewer_mapping(
                payload, "data_refs", catalog=catalog
            ),
            transport=_deserialize_viewer_mapping(
                payload, "transport", catalog=catalog
            ),
            transport_revision=_nonnegative_int_field(
                payload,
                "transport_revision",
            ),
            live_open_status=_string_field(payload, "live_open_status"),
            live_open_blocker=_deserialize_viewer_mapping(
                payload, "live_open_blocker", catalog=catalog
            ),
            camera_state=_deserialize_viewer_mapping(
                payload, "camera_state", catalog=catalog
            ),
            playback_state=_deserialize_viewer_mapping(
                payload, "playback_state", catalog=catalog
            ),
            summary=_deserialize_viewer_mapping(payload, "summary", catalog=catalog),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    if command_type == "update_viewer_session":
        return UpdateViewerSessionCommand(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            data_refs=_deserialize_viewer_mapping(
                payload, "data_refs", catalog=catalog
            ),
            transport=_deserialize_viewer_mapping(
                payload, "transport", catalog=catalog
            ),
            transport_revision=_nonnegative_int_field(
                payload,
                "transport_revision",
            ),
            live_open_status=_string_field(payload, "live_open_status"),
            live_open_blocker=_deserialize_viewer_mapping(
                payload, "live_open_blocker", catalog=catalog
            ),
            camera_state=_deserialize_viewer_mapping(
                payload, "camera_state", catalog=catalog
            ),
            playback_state=_deserialize_viewer_mapping(
                payload, "playback_state", catalog=catalog
            ),
            summary=_deserialize_viewer_mapping(payload, "summary", catalog=catalog),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    if command_type == "close_viewer_session":
        return CloseViewerSessionCommand(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    if command_type == "materialize_viewer_data":
        return MaterializeViewerDataCommand(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    if command_type == "query_viewer_session":
        return QueryViewerSessionCommand(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            query_type=_string_field(payload, "query_type"),
            payload=_deserialize_viewer_mapping(payload, "payload", catalog=catalog),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    raise ValueError(f"Unknown command type: {command_type!r}")


def dict_to_event(
    payload: dict[str, Any],
    *,
    catalog: DataTypeCatalog | None = None,
) -> WorkerEvent:
    payload = dict(copy_json_safe(payload, field_name="worker event"))
    event_type = _string_field(payload, "type")
    if event_type == "run_started":
        return RunStartedEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
        )
    if event_type == "run_state":
        return RunStateEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            state=_literal_field(  # type: ignore[arg-type]
                payload,
                "state",
                allowed_values=_ENGINE_STATE_VALUES,
                default="ready",
            ),
            transition=_literal_field(
                payload,
                "transition",
                allowed_values=_RUN_TRANSITION_VALUES,
                default="",
            ),
            reason=_string_field(payload, "reason"),
        )
    if event_type == "run_completed":
        _fixed_run_event_state(payload, expected="ready")
        return RunCompletedEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
        )
    if event_type == "run_failed":
        _fixed_run_event_state(payload, expected="error")
        return RunFailedEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            error=_string_field(payload, "error"),
            traceback=_string_field(payload, "traceback"),
            fatal=_bool_field(payload, "fatal"),
        )
    if event_type == "run_stopped":
        _fixed_run_event_state(payload, expected="ready")
        return RunStoppedEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            reason=_string_field(payload, "reason"),
        )
    if event_type == "node_started":
        return NodeStartedEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            started_at_epoch_ms=_float_field(payload, "started_at_epoch_ms"),
        )
    if event_type == "node_settled":
        warnings = _string_list_field(payload, "warnings")
        status = _string_field(
            payload,
            "status",
            default="completed",
            strip=True,
        ).lower()
        if status not in {"completed", "empty", "failed", "blocked"}:
            raise ValueError(f"invalid node settlement status: {status!r}")
        return NodeSettledEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            status=status,
            elapsed_ms=_float_field(payload, "elapsed_ms"),
            outputs=normalize_settled_output_mapping(
                payload.get("outputs", {}),
                catalog=catalog,
            ),
            errors=normalize_root_execution_errors(payload.get("errors", ())),
            warnings=warnings,
        )
    if event_type in {"trigger_capture_settled", "trigger_published"}:
        event_type_args = {
            "run_id": _string_field(payload, "run_id"),
            "workspace_id": _string_field(payload, "workspace_id"),
            "trigger_node_id": _string_field(payload, "trigger_node_id"),
            "result": normalize_settled_port_result(
                payload.get(
                    "result",
                    {"status": "empty", "value": None, "errors": ()},
                ),
                catalog=catalog,
            ),
        }
        if event_type == "trigger_capture_settled":
            return TriggerCaptureSettledEvent(**event_type_args)
        return TriggerPublishedEvent(**event_type_args)
    if event_type == "log":
        return LogEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            level=_string_field(payload, "level", default="info"),
            message=_string_field(payload, "message"),
        )
    if event_type == "protocol_error":
        return ProtocolErrorEvent(
            run_id=_string_field(payload, "run_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            request_id=_string_field(payload, "request_id"),
            command=_string_field(payload, "command"),
            error=_string_field(payload, "error"),
        )
    if event_type == "viewer_session_opened":
        return ViewerSessionOpenedEvent(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            data_refs=_deserialize_viewer_mapping(
                payload, "data_refs", catalog=catalog
            ),
            transport=_deserialize_viewer_mapping(
                payload, "transport", catalog=catalog
            ),
            transport_revision=_nonnegative_int_field(
                payload,
                "transport_revision",
            ),
            live_open_status=_string_field(payload, "live_open_status"),
            live_open_blocker=_deserialize_viewer_mapping(
                payload, "live_open_blocker", catalog=catalog
            ),
            camera_state=_deserialize_viewer_mapping(
                payload, "camera_state", catalog=catalog
            ),
            playback_state=_deserialize_viewer_mapping(
                payload, "playback_state", catalog=catalog
            ),
            summary=_deserialize_viewer_mapping(payload, "summary", catalog=catalog),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    if event_type == "viewer_session_updated":
        return ViewerSessionUpdatedEvent(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            data_refs=_deserialize_viewer_mapping(
                payload, "data_refs", catalog=catalog
            ),
            transport=_deserialize_viewer_mapping(
                payload, "transport", catalog=catalog
            ),
            transport_revision=_nonnegative_int_field(
                payload,
                "transport_revision",
            ),
            live_open_status=_string_field(payload, "live_open_status"),
            live_open_blocker=_deserialize_viewer_mapping(
                payload, "live_open_blocker", catalog=catalog
            ),
            camera_state=_deserialize_viewer_mapping(
                payload, "camera_state", catalog=catalog
            ),
            playback_state=_deserialize_viewer_mapping(
                payload, "playback_state", catalog=catalog
            ),
            summary=_deserialize_viewer_mapping(payload, "summary", catalog=catalog),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    if event_type == "viewer_session_closed":
        return ViewerSessionClosedEvent(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            transport=_deserialize_viewer_mapping(
                payload, "transport", catalog=catalog
            ),
            transport_revision=_nonnegative_int_field(
                payload,
                "transport_revision",
            ),
            live_open_status=_string_field(payload, "live_open_status"),
            live_open_blocker=_deserialize_viewer_mapping(
                payload, "live_open_blocker", catalog=catalog
            ),
            camera_state=_deserialize_viewer_mapping(
                payload, "camera_state", catalog=catalog
            ),
            playback_state=_deserialize_viewer_mapping(
                payload, "playback_state", catalog=catalog
            ),
            summary=_deserialize_viewer_mapping(payload, "summary", catalog=catalog),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    if event_type == "viewer_data_materialized":
        return ViewerDataMaterializedEvent(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            data_refs=_deserialize_viewer_mapping(
                payload, "data_refs", catalog=catalog
            ),
            transport=_deserialize_viewer_mapping(
                payload, "transport", catalog=catalog
            ),
            transport_revision=_nonnegative_int_field(
                payload,
                "transport_revision",
            ),
            live_open_status=_string_field(payload, "live_open_status"),
            live_open_blocker=_deserialize_viewer_mapping(
                payload, "live_open_blocker", catalog=catalog
            ),
            camera_state=_deserialize_viewer_mapping(
                payload, "camera_state", catalog=catalog
            ),
            playback_state=_deserialize_viewer_mapping(
                payload, "playback_state", catalog=catalog
            ),
            summary=_deserialize_viewer_mapping(payload, "summary", catalog=catalog),
            options=_deserialize_viewer_mapping(payload, "options", catalog=catalog),
        )
    if event_type == "viewer_query_result":
        return ViewerQueryResultEvent(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            backend_id=_string_field(payload, "backend_id"),
            query_type=_string_field(payload, "query_type"),
            supported=_bool_field(payload, "supported"),
            value=_deserialize_viewer_mapping(payload, "value", catalog=catalog),
            explanation=_string_field(payload, "explanation"),
        )
    if event_type == "viewer_session_failed":
        return ViewerSessionFailedEvent(
            request_id=_string_field(payload, "request_id"),
            workspace_id=_string_field(payload, "workspace_id"),
            node_id=_string_field(payload, "node_id"),
            session_id=_string_field(payload, "session_id"),
            command=_string_field(payload, "command"),
            error=_string_field(payload, "error"),
        )
    raise ValueError(f"Unknown event type: {event_type!r}")
