# Purpose: Execution backend clients — process-isolated, external-python, and
#          trusted in-process runtimes behind a common ExecutionBackendClient.
# Map: subsystems/execution
# Tests: tests/test_execution_client.py
# Landmarks: ExecutionBackendClient, ProcessExecutionClient, ExternalPythonExecutionClient, TrustedInProcessExecutionClient
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import multiprocessing as mp
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import traceback
import uuid
from collections import deque
from collections.abc import Callable, Mapping
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, replace
from functools import wraps
from pathlib import Path
from typing import Any

from ea_node_editor.common.coercions import normalize_path_text
from ea_node_editor.execution.backends import (
    EXTERNAL_SUBPROCESS_BACKEND,
    TRUSTED_IN_PROCESS_BACKEND,
    ExecutionBackendOrchestrator,
    ExecutionBackendSelection,
    coerce_execution_backend_selection,
)
from ea_node_editor.execution.protocol import (
    CloseViewerSessionCommand,
    EMPTY_REGISTRY_CONTRACT_FINGERPRINT,
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    PauseRunCommand,
    ProtocolErrorEvent,
    QueryViewerSessionCommand,
    ResumeRunCommand,
    RunFailedEvent,
    RunStateEvent,
    ShutdownCommand,
    StartRunCommand,
    StopRunCommand,
    UpdateViewerSessionCommand,
    VIEWER_COMMAND_TYPES,
    VIEWER_RESPONSE_EVENT_TYPES,
    ViewerSessionFailedEvent,
    WorkerCommand,
    WorkerEvent,
    catalog_agreement,
    command_to_dict,
    coerce_start_run_command,
    dict_to_event,
    event_to_dict,
    normalize_addon_runtime_config,
    runtime_registry_fingerprint,
)
from ea_node_editor.runtime_contracts.settled_results import SettledPortResult
from ea_node_editor.execution.python_environment import (
    resolve_python_environment,
    workflow_python_path_from_snapshot,
)
from ea_node_editor.execution.solution_identity import canonical_digest
from ea_node_editor.execution.worker import run_workflow, worker_main
from ea_node_editor.execution.worker_protocol import dispatch_viewer_command
from ea_node_editor.execution.worker_runtime import (
    DEFAULT_RUNTIME_PREPARATION_CACHE,
)
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.function_plugin import (
    EMPTY_PLUGIN_FINGERPRINT,
    INTERNAL_BUILTIN_FUNCTION_OWNER_ID,
    PluginBundleRef,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import (
    DataTypeCatalog,
    DataTypeCatalogError,
    RuntimeHandleRef,
)

_LISTENER_SHUTDOWN_SENTINEL = {"type": "__listener_shutdown__"}

_EXTERNAL_RUNTIME_IDENTITY_PROBE = r"""
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

names = json.loads(sys.argv[1])
mapping = importlib.metadata.packages_distributions()
packages = []
for name in names:
    distributions = mapping.get(name, ()) or (name,)
    versions = []
    for distribution in sorted(set(distributions)):
        try:
            versions.append((distribution, importlib.metadata.version(distribution)))
        except importlib.metadata.PackageNotFoundError:
            continue
    packages.append((name, versions or [("", "missing")]))
executable = Path(sys.executable)
digest = hashlib.sha256()
with executable.open("rb") as source:
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
print(json.dumps({
    "implementation": sys.implementation.name,
    "cache_tag": sys.implementation.cache_tag or "",
    "version": list(sys.version_info[:3]),
    "platform": [platform.system(), platform.release(), platform.machine()],
    "executable_size": executable.stat().st_size,
    "executable_sha256": digest.hexdigest(),
    "packages": packages,
}, sort_keys=True, separators=(",", ":")))
"""


def _package_versions(package_names: tuple[str, ...]) -> tuple[tuple[str, object], ...]:
    mapping = importlib.metadata.packages_distributions()
    result = []
    for name in package_names:
        distributions = mapping.get(name, ()) or (name,)
        versions = []
        for distribution in sorted(set(distributions)):
            try:
                versions.append(
                    (distribution, importlib.metadata.version(distribution))
                )
            except importlib.metadata.PackageNotFoundError:
                continue
        result.append((name, tuple(versions) or (("", "missing"),)))
    return tuple(result)


def _local_runtime_identity(package_names: tuple[str, ...]) -> dict[str, object]:
    executable = Path(sys.executable)
    digest = hashlib.sha256()
    with executable.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "implementation": sys.implementation.name,
        "cache_tag": sys.implementation.cache_tag or "",
        "version": tuple(sys.version_info[:3]),
        "platform": (platform.system(), platform.release(), platform.machine()),
        "executable_size": executable.stat().st_size,
        "executable_sha256": digest.hexdigest(),
        "packages": _package_versions(package_names),
    }


def _registry_contract_digest(value: object) -> str:
    digest = str(value)
    if len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise ValueError(
            "registry_contract_fingerprint must be a lowercase SHA-256 digest"
        )
    return digest


def _registry_admitted(method: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(method)
    def guarded(self: Any, *args: Any, **kwargs: Any) -> Any:
        with self.registry_publication_guard():
            return method(self, *args, **kwargs)

    return guarded


@dataclass(frozen=True)
class _PendingViewerRequest:
    request_id: str
    command: str
    workspace_id: str
    node_id: str
    session_id: str
    generation_token: int = 0


@dataclass(frozen=True)
class _GenerationTaggedEventSink:
    event_queue: queue.Queue[Any]
    generation_token: int

    def put(self, event: Any) -> None:
        self.event_queue.put((self.generation_token, event))


@dataclass
class _ProvisionalViewerRoute:
    session_key: tuple[str, str]
    baseline_client: Any | None
    baseline_generation: int
    baseline_request_order: int
    requests: list[tuple[int, str, Any, int]]


@dataclass(frozen=True, slots=True)
class ExecutionGenerationSnapshot:
    selection: ExecutionBackendSelection
    backend_generation: int
    runtime_generation: int
    environment_digest: str
    available: bool
    reason: str = ""

    def route_compatible_with(self, selection: ExecutionBackendSelection) -> bool:
        return _result_affecting_selection_payload(self.selection) == (
            _result_affecting_selection_payload(selection)
        )

    def compatible_with(self, other: object) -> bool:
        return bool(
            isinstance(other, ExecutionGenerationSnapshot)
            and self.route_compatible_with(other.selection)
            and self.backend_generation == other.backend_generation
            and self.runtime_generation == other.runtime_generation
            and self.environment_digest == other.environment_digest
            and self.available == other.available
        )


@dataclass(frozen=True, slots=True)
class ExecutionRunReservation:
    run_id: str
    workspace_id: str
    selection: ExecutionBackendSelection
    generation_snapshot: ExecutionGenerationSnapshot


@dataclass(frozen=True, slots=True)
class ExecutionResourceLease:
    client: Any
    value: RuntimeHandleRef


def _result_affecting_selection_payload(
    selection: ExecutionBackendSelection,
) -> dict[str, object]:
    return {
        "backend_id": selection.backend_id,
        "isolation": selection.isolation,
        "trusted_in_process": selection.trusted_in_process,
        "external_subprocess": selection.external_subprocess,
        "python_executable_digest": canonical_digest(
            str(selection.python_executable or "")
        ),
        "runtime_backend_ids": selection.runtime_backend_ids,
    }


def _coerce_positive_timeout(value: Any) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        return 0.0
    return timeout if timeout > 0.0 else 0.0


def _python_script_timeout_by_node_id(
    runtime_snapshot: Any, workspace_id: str
) -> dict[str, float]:
    if runtime_snapshot is None:
        return {}
    workspaces: list[Any] = []
    normalized_workspace_id = str(workspace_id or "").strip()
    if normalized_workspace_id:
        try:
            workspaces.append(runtime_snapshot.workspace(normalized_workspace_id))
        except (AttributeError, KeyError, ValueError):
            workspaces = []
    if not workspaces:
        workspaces = list(getattr(runtime_snapshot, "workspaces", ()) or ())

    timeouts: dict[str, float] = {}
    for workspace in workspaces:
        for node in getattr(workspace, "nodes", ()) or ():
            if str(getattr(node, "type_id", "") or "").strip() != "core.python_script":
                continue
            node_id = str(getattr(node, "node_id", "") or "").strip()
            if not node_id:
                continue
            properties = getattr(node, "properties", {}) or {}
            if not isinstance(properties, dict):
                continue
            timeout = _coerce_positive_timeout(properties.get("timeout_sec"))
            if timeout > 0.0:
                timeouts[node_id] = timeout
    return timeouts


class _ExecutionClientCommon:
    _TERMINAL_EVENT_TYPES = {"run_completed", "run_failed", "run_stopped"}

    @contextmanager
    def registry_publication_guard(self):  # noqa: ANN201
        with self._start_lock:
            yield

    def _bind_data_types(
        self,
        data_types: DataTypeCatalog | None,
        *,
        plugin_bundles: tuple[PluginBundleRef, ...] = (),
        plugin_fingerprint: str = EMPTY_PLUGIN_FINGERPRINT,
        registry_contract_fingerprint: str,
        addon_runtime_config: tuple[tuple[str, bool], ...],
    ) -> None:
        if not isinstance(data_types, DataTypeCatalog):
            raise DataTypeCatalogError(
                "start_run requires the authoritative data-type catalog"
            )
        if not data_types.is_frozen:
            raise DataTypeCatalogError("data-type catalog must be frozen")
        requested_fingerprint = data_types.fingerprint()
        requested_runtime_fingerprint = runtime_registry_fingerprint(
            requested_fingerprint,
            plugin_fingerprint,
        )
        requested_contract_fingerprint = _registry_contract_digest(
            registry_contract_fingerprint
        )
        normalized_addon_runtime_config = normalize_addon_runtime_config(
            addon_runtime_config
        )
        pinned_fingerprint = getattr(
            self,
            "_registry_contract_generation_fingerprint",
            "",
        )
        if (
            pinned_fingerprint
            and pinned_fingerprint != requested_contract_fingerprint
        ):
            raise DataTypeCatalogError(
                "registry contract differs from the active worker generation"
            )
        self._data_types = data_types
        self._catalog_generation_fingerprint = requested_fingerprint
        self._plugin_bundles = tuple(plugin_bundles)
        self._plugin_fingerprint = plugin_fingerprint
        self._runtime_registry_generation_fingerprint = (
            requested_runtime_fingerprint
        )
        self._registry_contract_generation_fingerprint = (
            requested_contract_fingerprint
        )
        self._addon_runtime_config = normalized_addon_runtime_config

    def _catalog_agreement(self) -> tuple[str, tuple[Any, ...]]:
        return catalog_agreement(self._data_types)

    def _plugin_agreement(
        self,
    ) -> tuple[tuple[PluginBundleRef, ...], str, str]:
        catalog_fingerprint = self._data_types.fingerprint()
        plugin_bundles = tuple(getattr(self, "_plugin_bundles", ()))
        plugin_fingerprint = str(
            getattr(self, "_plugin_fingerprint", EMPTY_PLUGIN_FINGERPRINT)
        )
        return (
            plugin_bundles,
            plugin_fingerprint,
            runtime_registry_fingerprint(
                catalog_fingerprint,
                plugin_fingerprint,
            ),
        )

    def _registry_contract_agreement(
        self,
    ) -> tuple[str, tuple[tuple[str, bool], ...]]:
        return (
            _registry_contract_digest(
                getattr(self, "_registry_contract_generation_fingerprint", "")
            ),
            normalize_addon_runtime_config(
                getattr(self, "_addon_runtime_config", ())
            ),
        )

    def _catalog_generation_fingerprint_value(self) -> str:
        with self._state_lock:
            return self._catalog_generation_fingerprint

    def _runtime_registry_fingerprint_value(self) -> str:
        with self._state_lock:
            return str(
                getattr(self, "_runtime_registry_generation_fingerprint", "")
            )

    def _catalog_generation_token_value(self) -> int:
        with self._state_lock:
            return int(getattr(self, "_catalog_generation_token", 0))

    def _install_physical_generation(self) -> int:
        with self._state_lock:
            catalog_generation = int(
                getattr(self, "_catalog_generation_token", 0)
            )
            physical_generation = int(
                getattr(self, "_physical_generation_token", 0)
            )
            if catalog_generation <= 0:
                catalog_generation = 1
            elif (
                physical_generation > 0
                and physical_generation == catalog_generation
            ):
                catalog_generation += 1
            self._catalog_generation_token = catalog_generation
            self._physical_generation_token = catalog_generation
            self._accepted_physical_generation_token = catalog_generation
            self._execution_environment_digest = ""
            self._execution_environment_registry_fingerprint = ""
            self._execution_environment_selection_digest = ""
            self._run_generation_tokens.clear()
            if (
                self._active_run_id
                and self._start_run_pending_id == self._active_run_id
            ):
                self._run_generation_tokens[self._active_run_id] = (
                    catalog_generation
                )
            return catalog_generation

    def _invalidate_physical_generation(self) -> int:
        with self._state_lock:
            generation_token = int(
                getattr(self, "_physical_generation_token", 0)
            )
            self._accepted_physical_generation_token = -1
            self._execution_environment_digest = ""
            self._execution_environment_registry_fingerprint = ""
            self._execution_environment_selection_digest = ""
            return generation_token

    def _restore_physical_generation(self, generation_token: int) -> None:
        with self._state_lock:
            if (
                self._physical_generation_token == generation_token
                and self._accepted_physical_generation_token == -1
            ):
                self._accepted_physical_generation_token = generation_token

    def _source_generation_is_current(self, generation_token: int) -> bool:
        with self._state_lock:
            return (
                self._catalog_generation_token == generation_token
                and int(
                    getattr(
                        self,
                        "_accepted_physical_generation_token",
                        generation_token,
                    )
                )
                == generation_token
            )

    def _drop_stale_viewer_generation(self, error: str) -> None:
        with self._viewer_request_lock:
            pending_requests = tuple(self._pending_viewer_requests.values())
            self._pending_viewer_requests.clear()
            self._viewer_session_ids.clear()
            self._viewer_session_generations.clear()
        for pending in pending_requests:
            self._dispatch_viewer_request_failure(
                pending,
                error,
                generation_token=pending.generation_token,
            )

    def _viewer_generation_is_live(self) -> bool:
        return True

    def _assert_registry_replaceable_locked(self) -> None:
        with self._state_lock:
            run_thread = getattr(self, "_run_thread", None)
            if (
                self._active_run_id
                or self._start_run_pending_id
                or (run_thread is not None and run_thread.is_alive())
            ):
                raise DataTypeCatalogError(
                    "Cannot replace the registry during an active run"
                )
        with self._viewer_request_lock:
            if self._pending_viewer_requests or self._viewer_session_ids:
                raise DataTypeCatalogError(
                    "Cannot replace the registry while viewer requests or sessions remain active"
                )

    def assert_registry_replaceable(self) -> None:
        with self._start_lock:
            self._assert_registry_replaceable_locked()

    def replace_registry(self, registry: NodeRegistry) -> bool:
        if not isinstance(registry, NodeRegistry):
            raise TypeError("registry must be a NodeRegistry")
        if not registry.data_types.is_frozen:
            raise DataTypeCatalogError("replacement data-type catalog must be frozen")
        requested_fingerprint = registry.contract_fingerprint()
        with self._start_lock:
            self._assert_registry_replaceable_locked()
            with self._state_lock:
                pinned_fingerprint = str(
                    getattr(
                        self,
                        "_registry_contract_generation_fingerprint",
                        "",
                    )
                )
            if not pinned_fingerprint or pinned_fingerprint == requested_fingerprint:
                return False
            self._recycle_catalog_generation()
            with self._state_lock:
                self._data_types = None
                self._catalog_generation_fingerprint = ""
                self._plugin_bundles = ()
                self._plugin_fingerprint = EMPTY_PLUGIN_FINGERPRINT
                self._runtime_registry_generation_fingerprint = ""
                self._registry_contract_generation_fingerprint = ""
                self._addon_runtime_config = ()
            return True

    def _prepare_start_run(
        self,
        run_id: str,
        workspace_id: str,
        data_types: DataTypeCatalog | None,
        plugin_bundles: tuple[PluginBundleRef, ...] = (),
        plugin_fingerprint: str = EMPTY_PLUGIN_FINGERPRINT,
        registry_contract_fingerprint: str = EMPTY_REGISTRY_CONTRACT_FINGERPRINT,
        addon_runtime_config: tuple[tuple[str, bool], ...] = (),
    ) -> bool:
        if not isinstance(data_types, DataTypeCatalog):
            raise DataTypeCatalogError(
                "start_run requires the authoritative data-type catalog"
            )
        if not data_types.is_frozen:
            raise DataTypeCatalogError("data-type catalog must be frozen")
        requested_fingerprint = data_types.fingerprint()
        requested_contract_fingerprint = _registry_contract_digest(
            registry_contract_fingerprint
        )
        with self._start_lock:
            with self._state_lock:
                run_thread = getattr(self, "_run_thread", None)
                if self._active_run_id or (
                    run_thread is not None and run_thread.is_alive()
                ):
                    return False
                pinned_fingerprint = getattr(
                    self,
                    "_registry_contract_generation_fingerprint",
                    "",
                )
                physical_generation = int(
                    getattr(self, "_physical_generation_token", 0)
                )
                accepted_physical_generation = int(
                    getattr(
                        self,
                        "_accepted_physical_generation_token",
                        0,
                    )
                )
                reuse_unpinned_physical_generation = (
                    not pinned_fingerprint
                    and physical_generation > 0
                    and self._catalog_generation_token
                    == physical_generation
                    == accepted_physical_generation
                )
            contract_changed = bool(
                pinned_fingerprint
                and pinned_fingerprint != requested_contract_fingerprint
            )
            dropped_dead_viewer_generation = False
            if contract_changed and not self._viewer_generation_is_live():
                self._invalidate_physical_generation()
                self._drop_stale_viewer_generation(
                    "The worker generation ended before the viewer request "
                    "completed."
                )
                dropped_dead_viewer_generation = True
            with self._viewer_request_lock:
                if contract_changed and (
                    self._pending_viewer_requests
                    or self._viewer_session_ids
                ):
                    raise DataTypeCatalogError(
                        "Cannot start a different registry contract while viewer "
                        "requests or sessions from the current worker generation "
                        "remain active."
                    )
            if contract_changed:
                try:
                    self._recycle_catalog_generation()
                except Exception as exc:  # noqa: BLE001
                    if dropped_dead_viewer_generation:
                        self._invalidate_physical_generation()
                    raise DataTypeCatalogError(
                        "Failed to recycle the idle worker generation for "
                        "the requested registry contract."
                    ) from exc
                with self._state_lock:
                    self._data_types = None
                    self._catalog_generation_fingerprint = ""
                    self._plugin_bundles = ()
                    self._plugin_fingerprint = EMPTY_PLUGIN_FINGERPRINT
                    self._runtime_registry_generation_fingerprint = ""
                    self._registry_contract_generation_fingerprint = ""
                    self._addon_runtime_config = ()
            new_generation = contract_changed or (
                not pinned_fingerprint
                and not reuse_unpinned_physical_generation
            )
            if new_generation:
                with self._viewer_request_lock:
                    self._viewer_session_generations.clear()
            with self._state_lock:
                if new_generation:
                    self._catalog_generation_token += 1
                    self._run_generation_tokens.clear()
                    self._execution_environment_digest = ""
                    self._execution_environment_registry_fingerprint = ""
                    self._execution_environment_selection_digest = ""
                self._bind_data_types(
                    data_types,
                    plugin_bundles=plugin_bundles,
                    plugin_fingerprint=plugin_fingerprint,
                    registry_contract_fingerprint=requested_contract_fingerprint,
                    addon_runtime_config=addon_runtime_config,
                )
                self._active_run_id = run_id
                self._active_workspace_id = workspace_id
                self._start_run_pending_id = run_id
                self._run_generation_tokens[run_id] = (
                    self._catalog_generation_token
                )
        return True

    def _release_start_run(self, run_id: str) -> None:
        with self._state_lock:
            self._run_generation_tokens.pop(run_id, None)
            if self._active_run_id == run_id:
                self._clear_active_run_state_locked()

    def _mark_start_run_dispatched(self, run_id: str) -> None:
        with self._state_lock:
            if self._start_run_pending_id == run_id:
                self._start_run_pending_id = ""

    def _encode_command(self, command: WorkerCommand) -> dict[str, Any]:
        return command_to_dict(command, catalog=getattr(self, "_data_types", None))

    def _decode_command(self, payload: dict[str, Any]) -> WorkerCommand:
        from ea_node_editor.execution.protocol import dict_to_command

        return dict_to_command(payload, catalog=getattr(self, "_data_types", None))

    def _decode_event(self, payload: dict[str, Any]) -> WorkerEvent:
        return dict_to_event(payload, catalog=getattr(self, "_data_types", None))

    def subscribe(
        self,
        callback: Callable[..., None],
        *,
        include_generation: bool = False,
    ) -> None:
        if include_generation:
            self._generation_callbacks.append(callback)
            return
        self._callbacks.append(callback)

    def _dispatch_event(
        self,
        event: WorkerEvent,
        *,
        generation_token: int | None = None,
    ) -> None:
        payload = event_to_dict(event, catalog=getattr(self, "_data_types", None))
        for callback in list(self._callbacks):
            try:
                callback(dict(payload))
            except Exception:
                continue
        token = (
            self._catalog_generation_token_value()
            if generation_token is None
            else int(generation_token)
        )
        for callback in list(getattr(self, "_generation_callbacks", ())):
            try:
                callback(dict(payload), token)
            except Exception:
                continue

    def _notify_generation_change(
        self,
        *,
        reason: str,
        generation_token: int,
    ) -> None:
        payload = {
            "type": "execution_generation_changed",
            "reason": str(reason).strip(),
        }
        for callback in list(getattr(self, "_generation_callbacks", ())):
            try:
                callback(dict(payload), int(generation_token))
            except Exception:
                continue

    def _clear_active_node_state_locked(self) -> None:
        self._active_node_id = ""
        self._active_node_deadline = 0.0
        self._active_node_timeout_sec = 0.0

    def _clear_active_run_state_locked(self) -> None:
        self._active_run_id = ""
        self._active_workspace_id = ""
        self._start_run_pending_id = ""
        self._script_timeout_by_node_id = {}
        self._clear_active_node_state_locked()

    def _record_execution_event_state(
        self,
        payload: dict[str, Any],
        *,
        expected_generation_token: int | None = None,
    ) -> None:
        event_type = str(payload.get("type", "") or "")
        event_run_id = str(payload.get("run_id", "") or "")
        node_id = str(payload.get("node_id", "") or "").strip()
        with self._state_lock:
            if (
                expected_generation_token is not None
                and (
                    self._catalog_generation_token
                    != expected_generation_token
                    or int(
                        getattr(
                            self,
                            "_accepted_physical_generation_token",
                            expected_generation_token,
                        )
                    )
                    != expected_generation_token
                )
            ):
                return
            if (
                event_run_id
                and self._active_run_id
                and event_run_id != self._active_run_id
            ):
                return
            if event_type == "node_started":
                self._active_node_id = node_id
                timeout_sec = self._script_timeout_by_node_id.get(node_id, 0.0)
                self._active_node_timeout_sec = timeout_sec
                self._active_node_deadline = (
                    time.monotonic() + timeout_sec if timeout_sec > 0.0 else 0.0
                )
            elif event_type == "node_settled":
                if not node_id or node_id == self._active_node_id:
                    self._clear_active_node_state_locked()
            elif event_type in self._TERMINAL_EVENT_TYPES:
                self._clear_active_run_state_locked()

    def _emit_protocol_error(
        self,
        message: str,
        *,
        run_id: str = "",
        request_id: str = "",
        command: str = "",
    ) -> None:
        with self._state_lock:
            workspace_id = self._active_workspace_id
        self._dispatch_event(
            ProtocolErrorEvent(
                run_id=run_id,
                workspace_id=workspace_id,
                request_id=request_id,
                command=command,
                error=message,
            )
        )

    @staticmethod
    def _next_viewer_request_id() -> str:
        return f"viewer_{uuid.uuid4().hex[:8]}"

    def _track_viewer_request(self, pending: _PendingViewerRequest) -> None:
        generation_token = self._catalog_generation_token_value()
        with self._viewer_request_lock:
            if pending.generation_token != generation_token:
                pending = replace(
                    pending,
                    generation_token=generation_token,
                )
            self._pending_viewer_requests[pending.request_id] = pending

    def _complete_viewer_request(self, request_id: str) -> _PendingViewerRequest | None:
        if not request_id:
            return None
        with self._viewer_request_lock:
            return self._pending_viewer_requests.pop(request_id, None)

    def _record_viewer_response_state(
        self,
        payload: Mapping[str, Any],
        *,
        default_generation_token: int,
        expected_generation_token: int | None = None,
    ) -> int:
        event_type = str(payload.get("type", "") or "")
        workspace_id = str(payload.get("workspace_id", "") or "").strip()
        session_id = str(payload.get("session_id", "") or "").strip()
        request_id = str(payload.get("request_id", "") or "").strip()
        state_context = (
            self._state_lock
            if expected_generation_token is not None
            else nullcontext()
        )
        with state_context:
            if (
                expected_generation_token is not None
                and (
                    self._catalog_generation_token
                    != expected_generation_token
                    or self._accepted_physical_generation_token
                    != expected_generation_token
                )
            ):
                return -1
            with self._viewer_request_lock:
                pending = self._pending_viewer_requests.get(request_id)
                generation_token = (
                    pending.generation_token
                    if pending is not None
                    else self._viewer_session_generations.get(
                        (workspace_id, session_id),
                        default_generation_token,
                    )
                )
                if workspace_id and session_id:
                    session_key = (workspace_id, session_id)
                    if event_type == "viewer_session_closed":
                        self._viewer_session_ids.discard(session_key)
                        self._viewer_session_generations.pop(session_key, None)
                    elif event_type != "viewer_session_failed":
                        self._viewer_session_ids.add(session_key)
                        self._viewer_session_generations[session_key] = (
                            generation_token
                        )
                if request_id:
                    self._pending_viewer_requests.pop(request_id, None)
        return generation_token

    def _event_generation_token(self, payload: Mapping[str, Any]) -> int:
        event_type = str(payload.get("type", "") or "")
        run_id = str(payload.get("run_id", "") or "").strip()
        request_id = str(payload.get("request_id", "") or "").strip()
        workspace_id = str(payload.get("workspace_id", "") or "").strip()
        session_id = str(payload.get("session_id", "") or "").strip()
        with self._state_lock:
            current_generation = self._catalog_generation_token
            run_generation = self._run_generation_tokens.get(run_id, 0)
        if run_id:
            return run_generation
        with self._viewer_request_lock:
            pending = self._pending_viewer_requests.get(request_id)
            if pending is not None:
                return pending.generation_token
            if workspace_id and session_id:
                return self._viewer_session_generations.get(
                    (workspace_id, session_id),
                    0,
                )
        if (
            event_type in VIEWER_RESPONSE_EVENT_TYPES
            or run_id
            or request_id
            or workspace_id
            or session_id
        ):
            return 0
        return current_generation

    def _dispatch_viewer_request_failure(
        self,
        pending: _PendingViewerRequest,
        error: str,
        *,
        generation_token: int | None = None,
    ) -> None:
        self._dispatch_event(
            ViewerSessionFailedEvent(
                request_id=pending.request_id,
                workspace_id=pending.workspace_id,
                node_id=pending.node_id,
                session_id=pending.session_id,
                command=pending.command,
                error=error,
            ),
            generation_token=(
                pending.generation_token
                if generation_token is None and pending.generation_token
                else generation_token
            ),
        )

    def _viewer_protocol_error_failure(
        self,
        payload: dict[str, Any],
        *,
        expected_generation_token: int | None = None,
    ) -> ViewerSessionFailedEvent | None:
        command = str(payload.get("command", ""))
        if command not in VIEWER_COMMAND_TYPES:
            return None
        request_id = str(payload.get("request_id", ""))
        if expected_generation_token is None:
            pending = self._complete_viewer_request(request_id)
        else:
            with self._state_lock:
                if (
                    self._catalog_generation_token
                    != expected_generation_token
                    or self._accepted_physical_generation_token
                    != expected_generation_token
                ):
                    return None
                pending = self._complete_viewer_request(request_id)
        if pending is None:
            return None
        return ViewerSessionFailedEvent(
            request_id=pending.request_id,
            workspace_id=pending.workspace_id or str(payload.get("workspace_id", "")),
            node_id=pending.node_id,
            session_id=pending.session_id,
            command=command,
            error=str(payload.get("error", "")),
        )

    def pause_run(self, run_id: str) -> None:
        if run_id:
            self._post_command(PauseRunCommand(run_id=run_id))

    def resume_run(self, run_id: str) -> None:
        if run_id:
            self._post_command(ResumeRunCommand(run_id=run_id))

    def stop_run(self, run_id: str) -> None:
        if run_id:
            self._post_command(StopRunCommand(run_id=run_id))

    @_registry_admitted
    def open_viewer_session(
        self,
        workspace_id: str,
        node_id: str,
        *,
        session_id: str = "",
        backend_id: str = "",
        data_refs: dict[str, Any] | None = None,
        transport: dict[str, Any] | None = None,
        transport_revision: int = 0,
        live_open_status: str = "",
        live_open_blocker: dict[str, Any] | None = None,
        camera_state: dict[str, Any] | None = None,
        playback_state: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        _request_id: str = "",
    ) -> str:
        return self._send_viewer_command(
            OpenViewerSessionCommand(
                request_id=_request_id or self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                backend_id=backend_id,
                data_refs=dict(data_refs or {}),
                transport=dict(transport or {}),
                transport_revision=int(transport_revision),
                live_open_status=live_open_status,
                live_open_blocker=dict(live_open_blocker or {}),
                camera_state=dict(camera_state or {}),
                playback_state=dict(playback_state or {}),
                summary=dict(summary or {}),
                options=dict(options or {}),
            )
        )

    def update_viewer_session(
        self,
        workspace_id: str,
        node_id: str,
        session_id: str,
        *,
        backend_id: str = "",
        data_refs: dict[str, Any] | None = None,
        transport: dict[str, Any] | None = None,
        transport_revision: int = 0,
        live_open_status: str = "",
        live_open_blocker: dict[str, Any] | None = None,
        camera_state: dict[str, Any] | None = None,
        playback_state: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        return self._send_viewer_command(
            UpdateViewerSessionCommand(
                request_id=self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                backend_id=backend_id,
                data_refs=dict(data_refs or {}),
                transport=dict(transport or {}),
                transport_revision=int(transport_revision),
                live_open_status=live_open_status,
                live_open_blocker=dict(live_open_blocker or {}),
                camera_state=dict(camera_state or {}),
                playback_state=dict(playback_state or {}),
                summary=dict(summary or {}),
                options=dict(options or {}),
            ),
            require_session_id=True,
        )

    def close_viewer_session(
        self,
        workspace_id: str,
        node_id: str,
        session_id: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> str:
        return self._send_viewer_command(
            CloseViewerSessionCommand(
                request_id=self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                options=dict(options or {}),
            ),
            require_session_id=True,
        )

    def materialize_viewer_data(
        self,
        workspace_id: str,
        node_id: str,
        session_id: str,
        *,
        backend_id: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        return self._send_viewer_command(
            MaterializeViewerDataCommand(
                request_id=self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                backend_id=backend_id,
                options=dict(options or {}),
            ),
            require_session_id=True,
        )

    def query_viewer_session(
        self,
        workspace_id: str,
        node_id: str,
        session_id: str,
        *,
        backend_id: str = "",
        query_type: str,
        payload: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        return self._send_viewer_command(
            QueryViewerSessionCommand(
                request_id=self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                backend_id=backend_id,
                query_type=str(query_type or "").strip(),
                payload=dict(payload or {}),
                options=dict(options or {}),
            ),
            require_session_id=True,
        )


class ProcessExecutionClient(_ExecutionClientCommon):
    def __init__(self) -> None:
        self._data_types: DataTypeCatalog | None = None
        self._catalog_generation_fingerprint = ""
        self._plugin_bundles: tuple[PluginBundleRef, ...] = ()
        self._plugin_fingerprint = EMPTY_PLUGIN_FINGERPRINT
        self._runtime_registry_generation_fingerprint = ""
        self._registry_contract_generation_fingerprint = ""
        self._addon_runtime_config: tuple[tuple[str, bool], ...] = ()
        self._catalog_generation_token = 0
        self._physical_generation_token = 0
        self._accepted_physical_generation_token = 0
        self._run_generation_tokens: dict[str, int] = {}
        self._ctx = mp.get_context("spawn")
        self._command_queue: mp.Queue = self._ctx.Queue()
        self._event_queue: mp.Queue = self._ctx.Queue()
        self._process: mp.Process | None = None
        self._start_lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._generation_callbacks: list[Callable[..., None]] = []
        self._active_run_id = ""
        self._active_workspace_id = ""
        self._start_run_pending_id = ""
        self._active_node_id = ""
        self._active_node_deadline = 0.0
        self._active_node_timeout_sec = 0.0
        self._script_timeout_by_node_id: dict[str, float] = {}
        self._viewer_request_lock = threading.Lock()
        self._pending_viewer_requests: dict[str, _PendingViewerRequest] = {}
        self._viewer_session_ids: set[tuple[str, str]] = set()
        self._viewer_session_generations: dict[tuple[str, str], int] = {}
        self._listener_thread = threading.Thread(
            target=self._event_listener,
            args=(self._event_queue, None, 0),
            daemon=True,
            name="execution-event-listener",
        )
        self._running = True
        self._listener_thread.start()

    def _viewer_generation_is_live(self) -> bool:
        with self._state_lock:
            process = self._process
            physical_generation = self._physical_generation_token
            accepted_generation = self._accepted_physical_generation_token
        return bool(
            process is not None
            and physical_generation > 0
            and accepted_generation == physical_generation
            and process.is_alive()
        )

    def _ensure_process(self) -> None:
        with self._start_lock:
            with self._state_lock:
                process = self._process
                physical_generation = self._physical_generation_token
            if process is not None and process.is_alive():
                return
            if process is not None:
                self._check_worker_health(process, physical_generation)
            retiring_generation = self._invalidate_physical_generation()
            try:
                if physical_generation > 0:
                    self._drop_stale_viewer_generation(
                        "The execution worker generation ended before the viewer "
                        "request completed."
                    )
                if process is not None:
                    process.join(timeout=0.1)
                self._retire_process_resources(process)
            except Exception:
                self._restore_physical_generation(retiring_generation)
                raise

            command_queue = self._ctx.Queue()
            event_queue = self._ctx.Queue()
            new_process = self._ctx.Process(
                target=worker_main,
                args=(command_queue, event_queue),
                daemon=True,
                name="ea-node-exec-worker",
            )
            try:
                new_process.start()
            except Exception:
                self._close_queue(command_queue)
                self._close_queue(event_queue)
                raise
            generation_token = self._install_physical_generation()
            listener_thread = threading.Thread(
                target=self._event_listener,
                args=(event_queue, new_process, generation_token),
                daemon=True,
                name="execution-event-listener",
            )
            with self._state_lock:
                self._command_queue = command_queue
                self._event_queue = event_queue
                self._process = new_process
                self._listener_thread = listener_thread
            listener_thread.start()

    def _recycle_catalog_generation(self) -> None:
        with self._start_lock:
            with self._state_lock:
                process = self._process
                with self._viewer_request_lock:
                    if (
                        self._pending_viewer_requests
                        or self._viewer_session_ids
                    ):
                        raise DataTypeCatalogError(
                            "Cannot recycle the execution worker while viewer "
                            "requests or sessions remain active."
                        )
                    retiring_generation = self._physical_generation_token
                    self._accepted_physical_generation_token = -1
            try:
                if process is not None and process.is_alive():
                    self._post_command(ShutdownCommand())
                    process.join(timeout=1.5)
                if process is not None and process.is_alive():
                    process.terminate()
                    process.join(timeout=0.5)
                if process is not None and process.is_alive():
                    try:
                        process.kill()
                        process.join(timeout=0.5)
                    except Exception:
                        pass
                if process is not None and process.is_alive():
                    raise DataTypeCatalogError(
                        "the previous execution worker did not terminate"
                    )
                self._retire_process_resources(process)
            except Exception:
                self._restore_physical_generation(retiring_generation)
                raise

    def _try_post_command(self, command: WorkerCommand) -> tuple[bool, str]:
        try:
            payload = self._encode_command(command)
            with self._state_lock:
                command_queue = self._command_queue
            if command_queue is None:
                raise RuntimeError("Execution worker is not running.")
            command_queue.put(payload)
            return True, ""
        except Exception as exc:  # noqa: BLE001
            message = f"Failed to dispatch command: {exc}"
            self._emit_protocol_error(
                message,
                run_id=getattr(command, "run_id", ""),
                request_id=getattr(command, "request_id", ""),
                command=getattr(command, "type", ""),
            )
            return False, message

    def _post_command(self, command: WorkerCommand) -> bool:
        success, _message = self._try_post_command(command)
        return success

    def _send_viewer_command(
        self,
        command: WorkerCommand,
        *,
        require_session_id: bool = False,
    ) -> str:
        try:
            command = self._decode_command(self._encode_command(command))
        except (TypeError, ValueError) as exc:
            request_id = str(getattr(command, "request_id", ""))
            pending = _PendingViewerRequest(
                request_id=request_id,
                command=str(getattr(command, "type", "")),
                workspace_id=str(getattr(command, "workspace_id", "")),
                node_id=str(getattr(command, "node_id", "")),
                session_id=str(getattr(command, "session_id", "")),
            )
            self._dispatch_viewer_request_failure(pending, str(exc))
            return request_id
        request_id = str(getattr(command, "request_id", ""))
        pending = _PendingViewerRequest(
            request_id=request_id,
            command=str(getattr(command, "type", "")),
            workspace_id=str(getattr(command, "workspace_id", "")),
            node_id=str(getattr(command, "node_id", "")),
            session_id=str(getattr(command, "session_id", "")),
        )
        if require_session_id and not pending.session_id:
            self._dispatch_viewer_request_failure(pending, "session_id is required.")
            return request_id
        with self._start_lock:
            try:
                self._ensure_process()
            except Exception as exc:  # noqa: BLE001
                self._dispatch_viewer_request_failure(
                    pending,
                    f"Failed to start worker process: {exc}",
                )
                return request_id
            self._track_viewer_request(pending)
            success, error_message = self._try_post_command(command)
            if not success:
                self._complete_viewer_request(request_id)
                self._dispatch_viewer_request_failure(pending, error_message)
        return request_id

    @_registry_admitted
    def start_run(
        self,
        project_path: str,
        workspace_id: str,
        trigger: dict[str, Any] | None = None,
        *,
        execution_backend: ExecutionBackendSelection | dict[str, Any] | None = None,
        target_node_ids: tuple[str, ...] | list[str] | None = None,
        trigger_publications: dict[str, SettledPortResult] | None = None,
        trigger_captures: dict[str, SettledPortResult] | None = None,
        clicked_trigger_node_id: str = "",
        data_types: DataTypeCatalog | None = None,
        plugin_bundles: tuple[PluginBundleRef, ...] = (),
        plugin_fingerprint: str = EMPTY_PLUGIN_FINGERPRINT,
        registry_contract_fingerprint: str = EMPTY_REGISTRY_CONTRACT_FINGERPRINT,
        addon_runtime_config: tuple[tuple[str, bool], ...] = (),
        _reserved_run_id: str = "",
        _reservation_prepared: bool = False,
        _prepared_command: StartRunCommand | None = None,
    ) -> str:
        trigger_payload = dict(trigger or {})
        run_id = _reserved_run_id or f"run_{uuid.uuid4().hex[:8]}"
        runtime_snapshot = trigger_payload.pop("runtime_snapshot", None)
        command_target_node_ids = trigger_payload.pop(
            "target_node_ids", target_node_ids or ()
        )
        command_trigger_publications = trigger_payload.pop(
            "trigger_publications", trigger_publications or {}
        )
        command_trigger_captures = trigger_payload.pop(
            "trigger_captures", trigger_captures or {}
        )
        command_clicked_trigger_node_id = trigger_payload.pop(
            "clicked_trigger_node_id", clicked_trigger_node_id
        )
        command_developer_mode = trigger_payload.pop("developer_mode", False)
        selection = coerce_execution_backend_selection(execution_backend)
        try:
            prepared_start = _reservation_prepared or self._prepare_start_run(
                run_id,
                workspace_id,
                data_types,
                plugin_bundles,
                plugin_fingerprint,
                registry_contract_fingerprint,
                addon_runtime_config,
            )
        except (TypeError, ValueError) as exc:
            self._emit_protocol_error(str(exc), run_id=run_id, command="start_run")
            return ""
        if not prepared_start:
            self._emit_protocol_error(
                "Execution worker already has an active run.",
                run_id=run_id,
                command="start_run",
            )
            return ""
        try:
            catalog_fingerprint, catalog_revisions = self._catalog_agreement()
            command_plugin_bundles, command_plugin_fingerprint, runtime_fingerprint = (
                self._plugin_agreement()
            )
            contract_fingerprint, command_addon_runtime_config = (
                self._registry_contract_agreement()
            )
            command_source: StartRunCommand | dict[str, Any] = (
                _prepared_command
                if _prepared_command is not None
                else {
                    "run_id": run_id,
                    "project_path": project_path,
                    "workspace_id": workspace_id,
                    "trigger": trigger_payload,
                    "runtime_snapshot": runtime_snapshot,
                    "execution_backend": selection.to_payload(),
                    "target_node_ids": command_target_node_ids,
                    "trigger_publications": command_trigger_publications,
                    "trigger_captures": command_trigger_captures,
                    "clicked_trigger_node_id": command_clicked_trigger_node_id,
                    "developer_mode": command_developer_mode,
                    "catalog_fingerprint": catalog_fingerprint,
                    "catalog_revisions": catalog_revisions,
                    "plugin_bundles": command_plugin_bundles,
                    "plugin_fingerprint": command_plugin_fingerprint,
                    "runtime_registry_fingerprint": runtime_fingerprint,
                    "registry_contract_fingerprint": contract_fingerprint,
                    "addon_runtime_config": command_addon_runtime_config,
                }
            )
            command = coerce_start_run_command(
                command_source,
                catalog=self._data_types,
            )
            if (
                command.run_id != run_id
                or command.workspace_id != workspace_id
                or command.execution_backend != selection
            ):
                raise ValueError("prepared command does not match reserved process run")
        except (TypeError, ValueError) as exc:
            self._release_start_run(run_id)
            self._emit_protocol_error(str(exc), run_id=run_id, command="start_run")
            return ""

        with self._start_lock:
            try:
                self._ensure_process()
            except Exception as exc:  # noqa: BLE001
                self._release_start_run(run_id)
                self._emit_protocol_error(
                    f"Failed to start worker process: {exc}", command="start_run"
                )
                return ""
            with self._state_lock:
                self._script_timeout_by_node_id = _python_script_timeout_by_node_id(
                    command.runtime_snapshot,
                    workspace_id,
                )
                self._clear_active_node_state_locked()
            if not self._post_command(command):
                self._release_start_run(run_id)
                return ""
            self._mark_start_run_dispatched(run_id)
        return run_id

    def shutdown(self) -> None:
        with self._start_lock:
            with self._state_lock:
                process = self._process
                self._clear_active_run_state_locked()
            self._invalidate_physical_generation()
            if process and process.is_alive():
                self._post_command(ShutdownCommand())
                process.join(timeout=1.5)
            if process and process.is_alive():
                process.terminate()
                process.join(timeout=0.5)
            if process and process.is_alive():
                try:
                    process.kill()
                    process.join(timeout=0.5)
                except Exception:
                    pass
            self._running = False
            if process is None or not process.is_alive():
                self._retire_process_resources(process)
        with self._viewer_request_lock:
            self._pending_viewer_requests.clear()
            self._viewer_session_ids.clear()
            self._viewer_session_generations.clear()

    def _check_worker_health(
        self,
        process: mp.Process | None,
        generation_token: int,
    ) -> None:
        with self._state_lock:
            if (
                process is None
                or self._process is not process
                or self._physical_generation_token != generation_token
                or self._accepted_physical_generation_token != generation_token
            ):
                return
            active_run_id = self._active_run_id
            if active_run_id and self._start_run_pending_id == active_run_id:
                return
            workspace_id = self._active_workspace_id
            active_node_id = self._active_node_id
            active_deadline = self._active_node_deadline
            active_timeout_sec = self._active_node_timeout_sec
        if process is None:
            return
        if process.is_alive():
            if (
                active_run_id
                and active_node_id
                and active_deadline > 0.0
                and time.monotonic() >= active_deadline
            ):
                self._terminate_timed_out_worker(
                    process,
                    run_id=active_run_id,
                    workspace_id=workspace_id,
                    node_id=active_node_id,
                    timeout_sec=active_timeout_sec,
                    generation_token=generation_token,
                )
            return

        process.join(timeout=0.1)
        with self._state_lock:
            if (
                self._process is not process
                or self._physical_generation_token != generation_token
                or self._accepted_physical_generation_token != generation_token
            ):
                return
            run_id = self._active_run_id
            run_workspace = self._active_workspace_id
            failed_node_id = self._active_node_id
            self._accepted_physical_generation_token = -1
            self._clear_active_run_state_locked()

        self._notify_generation_change(
            reason="worker_terminated",
            generation_token=generation_token,
        )

        if active_run_id and run_id == active_run_id:
            self._dispatch_event(
                RunFailedEvent(
                    run_id=active_run_id,
                    workspace_id=workspace_id or run_workspace,
                    node_id=failed_node_id,
                    error="Execution worker terminated unexpectedly.",
                    traceback="",
                    fatal=True,
                ),
                generation_token=generation_token,
            )
            self._dispatch_event(
                RunStateEvent(
                    run_id=active_run_id,
                    workspace_id=workspace_id or run_workspace,
                    state="error",
                    transition="fail",
                    reason="worker_terminated",
                ),
                generation_token=generation_token,
            )

    def _terminate_timed_out_worker(
        self,
        process: mp.Process,
        *,
        run_id: str,
        workspace_id: str,
        node_id: str,
        timeout_sec: float,
        generation_token: int,
    ) -> None:
        with self._start_lock:
            with self._state_lock:
                if (
                    self._active_run_id != run_id
                    or self._process is not process
                    or self._physical_generation_token != generation_token
                    or self._accepted_physical_generation_token
                    != generation_token
                ):
                    return
                self._accepted_physical_generation_token = -1
            try:
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=0.5)
            except Exception:
                pass
            if process.is_alive():
                self._restore_physical_generation(generation_token)
                self._emit_protocol_error(
                    "Failed to terminate timed-out execution worker.",
                    run_id=run_id,
                    command="start_run",
                )
                return
            with self._state_lock:
                if (
                    self._active_run_id != run_id
                    or self._process is not process
                    or self._physical_generation_token != generation_token
                    or self._accepted_physical_generation_token != -1
                ):
                    return
                run_workspace = self._active_workspace_id
                self._clear_active_run_state_locked()

        error = f"Python Script timed out after {timeout_sec:.2f} seconds."
        self._dispatch_event(
            RunFailedEvent(
                run_id=run_id,
                workspace_id=workspace_id or run_workspace,
                node_id=node_id,
                error=error,
                traceback="",
                fatal=True,
            ),
            generation_token=generation_token,
        )
        self._dispatch_event(
            RunStateEvent(
                run_id=run_id,
                workspace_id=workspace_id or run_workspace,
                state="error",
                transition="fail",
                reason="python_script_timeout",
            ),
            generation_token=generation_token,
        )

    def _event_listener(
        self,
        event_queue: mp.Queue,
        process: mp.Process | None,
        generation_token: int,
    ) -> None:
        while self._running:
            try:
                event = event_queue.get(timeout=0.2)
            except queue.Empty:
                self._check_worker_health(process, generation_token)
                continue
            except (EOFError, OSError):
                self._check_worker_health(process, generation_token)
                continue

            if event == _LISTENER_SHUTDOWN_SENTINEL:
                break
            if not self._source_generation_is_current(generation_token):
                continue
            if not isinstance(event, dict):
                self._emit_protocol_error("Received non-dictionary event from worker.")
                continue

            try:
                typed_event = self._decode_event(dict(event))
            except (TypeError, ValueError) as exc:
                if self._source_generation_is_current(generation_token):
                    self._emit_protocol_error(f"Received invalid worker event: {exc}")
                continue

            if not self._source_generation_is_current(generation_token):
                continue
            payload = event_to_dict(typed_event, catalog=self._data_types)
            event_type = payload.get("type", "")
            event_run_id = payload.get("run_id", "")
            viewer_failure_event = None
            if event_type == "protocol_error":
                viewer_failure_event = self._viewer_protocol_error_failure(
                    payload,
                    expected_generation_token=generation_token,
                )
            elif event_type in VIEWER_RESPONSE_EVENT_TYPES:
                response_generation = self._record_viewer_response_state(
                    payload,
                    default_generation_token=generation_token,
                    expected_generation_token=generation_token,
                )
                if response_generation != generation_token:
                    continue
            self._record_execution_event_state(
                payload,
                expected_generation_token=generation_token,
            )
            if not self._source_generation_is_current(generation_token):
                continue
            self._dispatch_event(
                typed_event,
                generation_token=generation_token,
            )
            if viewer_failure_event is not None:
                self._dispatch_event(
                    viewer_failure_event,
                    generation_token=generation_token,
                )

            if event_type in self._TERMINAL_EVENT_TYPES:
                with self._state_lock:
                    if (
                        self._accepted_physical_generation_token
                        == generation_token
                        and (
                            not self._active_run_id
                            or self._active_run_id == event_run_id
                        )
                    ):
                        self._clear_active_run_state_locked()

    def _retire_process_resources(self, process: mp.Process | None) -> None:
        with self._state_lock:
            command_queue = self._command_queue
            event_queue = self._event_queue
            listener_thread = self._listener_thread
        try:
            event_queue.put_nowait(dict(_LISTENER_SHUTDOWN_SENTINEL))
        except Exception:
            pass
        if listener_thread is not None and listener_thread.is_alive():
            listener_thread.join(timeout=1.0)
        if listener_thread is not None and listener_thread.is_alive():
            raise DataTypeCatalogError(
                "the previous execution worker listener did not terminate"
            )
        self._close_queue(command_queue)
        self._close_queue(event_queue)
        with self._state_lock:
            if self._process is process:
                self._process = None
            if self._command_queue is command_queue:
                self._command_queue = None
            if self._event_queue is event_queue:
                self._event_queue = None
            if self._listener_thread is listener_thread:
                self._listener_thread = None

    @staticmethod
    def _close_queue(queue_obj: mp.Queue | None) -> None:
        if queue_obj is None:
            return
        try:
            queue_obj.close()
        except Exception:
            pass
        try:
            queue_obj.join_thread()
        except Exception:
            pass


class ExternalPythonExecutionClient(_ExecutionClientCommon):
    _RUNTIME_IMPORT_CHECK = "import ea_node_editor.execution.stdio_worker"

    def __init__(self) -> None:
        self._data_types: DataTypeCatalog | None = None
        self._catalog_generation_fingerprint = ""
        self._plugin_bundles: tuple[PluginBundleRef, ...] = ()
        self._plugin_fingerprint = EMPTY_PLUGIN_FINGERPRINT
        self._runtime_registry_generation_fingerprint = ""
        self._registry_contract_generation_fingerprint = ""
        self._addon_runtime_config: tuple[tuple[str, bool], ...] = ()
        self._catalog_generation_token = 0
        self._physical_generation_token = 0
        self._accepted_physical_generation_token = 0
        self._run_generation_tokens: dict[str, int] = {}
        self._process: subprocess.Popen | None = None
        self._python_executable = ""
        self._stdin_lock = threading.Lock()
        self._start_lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._generation_callbacks: list[Callable[..., None]] = []
        self._active_run_id = ""
        self._active_workspace_id = ""
        self._start_run_pending_id = ""
        self._active_node_id = ""
        self._active_node_deadline = 0.0
        self._active_node_timeout_sec = 0.0
        self._script_timeout_by_node_id: dict[str, float] = {}
        self._viewer_request_lock = threading.Lock()
        self._pending_viewer_requests: dict[str, _PendingViewerRequest] = {}
        self._viewer_session_ids: set[tuple[str, str]] = set()
        self._viewer_session_generations: dict[tuple[str, str], int] = {}
        self._stderr_tail: deque[str] = deque(maxlen=40)
        self._running = True
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="external-python-monitor",
        )
        self._monitor_thread.start()

    def _viewer_generation_is_live(self) -> bool:
        with self._state_lock:
            process = self._process
            physical_generation = self._physical_generation_token
            accepted_generation = self._accepted_physical_generation_token
        return bool(
            process is not None
            and physical_generation > 0
            and accepted_generation == physical_generation
            and process.poll() is None
        )

    def _verify_runtime_available(self, python_executable: str) -> None:
        try:
            result = subprocess.run(
                [python_executable, "-c", self._RUNTIME_IMPORT_CHECK],
                capture_output=True,
                check=False,
                text=True,
                timeout=10.0,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "Configured Python executable timed out while checking "
                "for the COREX runtime package."
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                "Failed to launch configured Python executable: "
                f"{str(exc)[:1200]}"
            ) from exc
        if result.returncode != 0:
            stderr_tail = (result.stderr or result.stdout or "").strip()[-1200:]
            detail = f" Details: {stderr_tail}" if stderr_tail else ""
            raise RuntimeError(
                "Configured Python executable cannot import "
                "ea_node_editor.execution.stdio_worker. Install a compatible "
                "COREX runtime package in that environment, or use Workflow "
                "Settings > Environment > Create / Repair Managed Runtime to create a "
                f"managed environment.{detail}"
            )

    def _process_start_required(
        self,
        python_executable: str,
        registry_contract_fingerprint: str,
    ) -> bool:
        with self._state_lock:
            process = self._process
            current_python = self._python_executable
            pinned_contract = self._registry_contract_generation_fingerprint
        return bool(
            process is None
            or process.poll() is not None
            or current_python != python_executable
            or (
                pinned_contract
                and pinned_contract != str(registry_contract_fingerprint)
            )
        )

    def _assert_process_transition_allowed(self) -> None:
        with self._state_lock:
            process = self._process
        if process is None or process.poll() is not None:
            return
        with self._viewer_request_lock:
            if self._pending_viewer_requests or self._viewer_session_ids:
                raise RuntimeError(
                    "Cannot replace the external Python worker while viewer "
                    "requests or sessions remain active."
                )

    def _ensure_process(self, python_executable: str) -> None:
        normalized_python = str(python_executable or "").strip()
        if not normalized_python:
            raise RuntimeError("External Python execution requires python_executable.")
        with self._start_lock:
            with self._state_lock:
                process = self._process
                current_python = self._python_executable
                physical_generation = self._physical_generation_token
            if (
                process is not None
                and process.poll() is None
                and current_python == normalized_python
            ):
                return
            if process is not None and process.poll() is None:
                with self._state_lock:
                    with self._viewer_request_lock:
                        if (
                            self._pending_viewer_requests
                            or self._viewer_session_ids
                        ):
                            raise RuntimeError(
                                "Cannot replace the external Python worker while "
                                "viewer requests or sessions remain active."
                            )
                        retiring_generation = (
                            self._physical_generation_token
                        )
                        self._accepted_physical_generation_token = -1
                try:
                    self._stop_external_process(process, graceful=True)
                except Exception:
                    self._restore_physical_generation(retiring_generation)
                    raise
            else:
                if process is not None:
                    self._check_worker_health_locked()
                retiring_generation = self._invalidate_physical_generation()
                try:
                    if physical_generation > 0:
                        self._drop_stale_viewer_generation(
                            "The external Python worker generation ended before "
                            "the viewer request completed."
                        )
                    self._retire_external_resources(process)
                except Exception:
                    self._restore_physical_generation(retiring_generation)
                    raise

            from ea_node_editor.execution.managed_runtime import (
                ADDON_RUNTIME_PYTHON_ENV,
                resolve_addon_runtime_paths,
            )

            worker_environment = os.environ.copy()
            worker_environment[ADDON_RUNTIME_PYTHON_ENV] = str(
                resolve_addon_runtime_paths().python_executable
            )
            try:
                new_process = subprocess.Popen(
                    [
                        normalized_python,
                        "-u",
                        "-m",
                        "ea_node_editor.execution.stdio_worker",
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=worker_environment,
                )
            except OSError as exc:
                raise RuntimeError(
                    "Failed to start external Python workflow worker: "
                    f"{str(exc)[:1200]}"
                ) from exc
            generation_token = self._install_physical_generation()
            stdout_thread = threading.Thread(
                target=self._stdout_listener,
                args=(new_process, generation_token),
                daemon=True,
                name="external-python-stdout-listener",
            )
            stderr_thread = threading.Thread(
                target=self._stderr_listener,
                args=(new_process, generation_token),
                daemon=True,
                name="external-python-stderr-listener",
            )
            with self._state_lock:
                self._process = new_process
                self._python_executable = normalized_python
                self._stderr_tail.clear()
                self._stdout_thread = stdout_thread
                self._stderr_thread = stderr_thread
            stdout_thread.start()
            stderr_thread.start()

    def _recycle_catalog_generation(self) -> None:
        with self._start_lock:
            with self._state_lock:
                process = self._process
                with self._viewer_request_lock:
                    if (
                        self._pending_viewer_requests
                        or self._viewer_session_ids
                    ):
                        raise DataTypeCatalogError(
                            "Cannot recycle the external Python worker while "
                            "viewer requests or sessions remain active."
                        )
                    retiring_generation = self._physical_generation_token
                    self._accepted_physical_generation_token = -1
            try:
                self._stop_external_process(process, graceful=True)
            except Exception:
                self._restore_physical_generation(retiring_generation)
                raise

    def _try_post_command(self, command: WorkerCommand) -> tuple[bool, str]:
        try:
            payload = self._encode_command(command)
            line = json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n"
            with self._stdin_lock:
                process = self._process
                if (
                    process is None
                    or process.poll() is not None
                    or process.stdin is None
                ):
                    raise RuntimeError(
                        "External Python workflow worker is not running."
                    )
                process.stdin.write(line)
                process.stdin.flush()
            return True, ""
        except Exception as exc:  # noqa: BLE001
            message = f"Failed to dispatch command to external Python worker: {exc}"
            self._emit_protocol_error(
                message,
                run_id=getattr(command, "run_id", ""),
                request_id=getattr(command, "request_id", ""),
                command=getattr(command, "type", ""),
            )
            return False, message

    def _post_command(self, command: WorkerCommand) -> bool:
        success, _message = self._try_post_command(command)
        return success

    @_registry_admitted
    def start_run(
        self,
        project_path: str,
        workspace_id: str,
        trigger: dict[str, Any] | None = None,
        *,
        execution_backend: ExecutionBackendSelection | dict[str, Any] | None = None,
        target_node_ids: tuple[str, ...] | list[str] | None = None,
        trigger_publications: dict[str, SettledPortResult] | None = None,
        trigger_captures: dict[str, SettledPortResult] | None = None,
        clicked_trigger_node_id: str = "",
        data_types: DataTypeCatalog | None = None,
        plugin_bundles: tuple[PluginBundleRef, ...] = (),
        plugin_fingerprint: str = EMPTY_PLUGIN_FINGERPRINT,
        registry_contract_fingerprint: str = EMPTY_REGISTRY_CONTRACT_FINGERPRINT,
        addon_runtime_config: tuple[tuple[str, bool], ...] = (),
        _reserved_run_id: str = "",
        _reservation_prepared: bool = False,
        _prepared_command: StartRunCommand | None = None,
    ) -> str:
        trigger_payload = dict(trigger or {})
        run_id = _reserved_run_id or f"run_{uuid.uuid4().hex[:8]}"
        runtime_snapshot = trigger_payload.pop("runtime_snapshot", None)
        command_target_node_ids = trigger_payload.pop(
            "target_node_ids", target_node_ids or ()
        )
        command_trigger_publications = trigger_payload.pop(
            "trigger_publications", trigger_publications or {}
        )
        command_trigger_captures = trigger_payload.pop(
            "trigger_captures", trigger_captures or {}
        )
        command_clicked_trigger_node_id = trigger_payload.pop(
            "clicked_trigger_node_id", clicked_trigger_node_id
        )
        command_developer_mode = trigger_payload.pop("developer_mode", False)
        selection = coerce_execution_backend_selection(execution_backend)
        python_executable = str(selection.python_executable or "").strip()
        if not python_executable:
            self._emit_protocol_error(
                "External Python workflow execution requires python_executable.",
                run_id=run_id,
                command="start_run",
            )
            return ""
        with self._start_lock:
            with self._state_lock:
                active_run = bool(self._active_run_id)
            if active_run and not _reservation_prepared:
                self._emit_protocol_error(
                    "External Python worker already has an active run.",
                    run_id=run_id,
                    command="start_run",
                )
                return ""
            try:
                if self._process_start_required(
                    python_executable,
                    registry_contract_fingerprint,
                ):
                    self._assert_process_transition_allowed()
                    self._verify_runtime_available(python_executable)
                prepared_start = _reservation_prepared or self._prepare_start_run(
                    run_id,
                    workspace_id,
                    data_types,
                    plugin_bundles,
                    plugin_fingerprint,
                    registry_contract_fingerprint,
                    addon_runtime_config,
                )
            except (RuntimeError, TypeError, ValueError) as exc:
                self._emit_protocol_error(str(exc), run_id=run_id, command="start_run")
                return ""
            if not prepared_start:
                self._emit_protocol_error(
                    "External Python worker already has an active run.",
                    run_id=run_id,
                    command="start_run",
                )
                return ""
            try:
                catalog_fingerprint, catalog_revisions = self._catalog_agreement()
                command_plugin_bundles, command_plugin_fingerprint, runtime_fingerprint = (
                    self._plugin_agreement()
                )
                contract_fingerprint, command_addon_runtime_config = (
                    self._registry_contract_agreement()
                )
                command_source: StartRunCommand | dict[str, Any] = (
                    _prepared_command
                    if _prepared_command is not None
                    else {
                        "run_id": run_id,
                        "project_path": project_path,
                        "workspace_id": workspace_id,
                        "trigger": trigger_payload,
                        "runtime_snapshot": runtime_snapshot,
                        "execution_backend": selection.to_payload(),
                        "target_node_ids": command_target_node_ids,
                        "trigger_publications": command_trigger_publications,
                        "trigger_captures": command_trigger_captures,
                        "clicked_trigger_node_id": command_clicked_trigger_node_id,
                        "developer_mode": command_developer_mode,
                        "catalog_fingerprint": catalog_fingerprint,
                        "catalog_revisions": catalog_revisions,
                        "plugin_bundles": command_plugin_bundles,
                        "plugin_fingerprint": command_plugin_fingerprint,
                        "runtime_registry_fingerprint": runtime_fingerprint,
                        "registry_contract_fingerprint": contract_fingerprint,
                        "addon_runtime_config": command_addon_runtime_config,
                    }
                )
                command = coerce_start_run_command(
                    command_source,
                    catalog=self._data_types,
                )
                if (
                    command.run_id != run_id
                    or command.workspace_id != workspace_id
                    or command.execution_backend != selection
                ):
                    raise ValueError(
                        "prepared command does not match reserved external run"
                    )
            except (TypeError, ValueError) as exc:
                self._release_start_run(run_id)
                self._emit_protocol_error(str(exc), run_id=run_id, command="start_run")
                return ""
            try:
                self._ensure_process(python_executable)
            except RuntimeError as exc:
                self._release_start_run(run_id)
                self._emit_protocol_error(str(exc), run_id=run_id, command="start_run")
                return ""

            with self._state_lock:
                self._script_timeout_by_node_id = _python_script_timeout_by_node_id(
                    command.runtime_snapshot,
                    workspace_id,
                )
                self._clear_active_node_state_locked()
            if not self._post_command(command):
                self._release_start_run(run_id)
                return ""
            self._mark_start_run_dispatched(run_id)
        return run_id

    def _send_viewer_command(
        self,
        command: WorkerCommand,
        *,
        require_session_id: bool = False,
    ) -> str:
        try:
            command = self._decode_command(self._encode_command(command))
        except (TypeError, ValueError) as exc:
            request_id = str(getattr(command, "request_id", ""))
            pending = _PendingViewerRequest(
                request_id=request_id,
                command=str(getattr(command, "type", "")),
                workspace_id=str(getattr(command, "workspace_id", "")),
                node_id=str(getattr(command, "node_id", "")),
                session_id=str(getattr(command, "session_id", "")),
            )
            self._dispatch_viewer_request_failure(pending, str(exc))
            return request_id
        request_id = str(getattr(command, "request_id", ""))
        pending = _PendingViewerRequest(
            request_id=request_id,
            command=str(getattr(command, "type", "")),
            workspace_id=str(getattr(command, "workspace_id", "")),
            node_id=str(getattr(command, "node_id", "")),
            session_id=str(getattr(command, "session_id", "")),
        )
        if require_session_id and not pending.session_id:
            self._dispatch_viewer_request_failure(pending, "session_id is required.")
            return request_id
        with self._start_lock:
            self._track_viewer_request(pending)
            if not self._post_command(command):
                self._complete_viewer_request(request_id)
                self._dispatch_viewer_request_failure(
                    pending, "Failed to dispatch command."
                )
        return request_id

    def _stdout_listener(
        self,
        process: subprocess.Popen,
        generation_token: int,
    ) -> None:
        stdout = process.stdout
        if stdout is None:
            return
        while self._running:
            try:
                line = stdout.readline()
            except OSError:
                return
            if line == "":
                return
            self._handle_stdout_line(
                line,
                generation_token=generation_token,
            )

    def _stderr_listener(
        self,
        process: subprocess.Popen,
        generation_token: int,
    ) -> None:
        stderr = process.stderr
        if stderr is None:
            return
        while self._running:
            try:
                line = stderr.readline()
            except OSError:
                return
            if line == "":
                return
            text = line.strip()
            if (
                text
                and self._source_generation_is_current(generation_token)
            ):
                with self._state_lock:
                    self._stderr_tail.append(text)

    def _handle_stdout_line(
        self,
        line: str,
        *,
        generation_token: int | None = None,
    ) -> None:
        source_generation = (
            self._catalog_generation_token_value()
            if generation_token is None
            else int(generation_token)
        )
        if not self._source_generation_is_current(source_generation):
            return
        text = line.strip()
        if not text:
            return
        try:
            event = json.loads(text)
        except json.JSONDecodeError as exc:
            if self._source_generation_is_current(source_generation):
                self._emit_protocol_error(
                    "Received invalid JSON event from external Python worker: "
                    f"{exc}"
                )
            return
        if not isinstance(event, dict):
            if self._source_generation_is_current(source_generation):
                self._emit_protocol_error(
                    "Received non-dictionary event from external Python worker."
                )
            return
        try:
            typed_event = self._decode_event(dict(event))
        except (TypeError, ValueError) as exc:
            if self._source_generation_is_current(source_generation):
                self._emit_protocol_error(
                    f"Received invalid external Python worker event: {exc}"
                )
            return

        if not self._source_generation_is_current(source_generation):
            return
        payload = event_to_dict(typed_event, catalog=self._data_types)
        event_type = payload.get("type", "")
        event_run_id = payload.get("run_id", "")
        viewer_failure_event = None
        if event_type == "protocol_error":
            viewer_failure_event = self._viewer_protocol_error_failure(
                payload,
                expected_generation_token=source_generation,
            )
        elif event_type in VIEWER_RESPONSE_EVENT_TYPES:
            response_generation = self._record_viewer_response_state(
                payload,
                default_generation_token=source_generation,
                expected_generation_token=source_generation,
            )
            if response_generation != source_generation:
                return
        self._record_execution_event_state(
            payload,
            expected_generation_token=source_generation,
        )
        if not self._source_generation_is_current(source_generation):
            return
        self._dispatch_event(
            typed_event,
            generation_token=source_generation,
        )
        if viewer_failure_event is not None:
            self._dispatch_event(
                viewer_failure_event,
                generation_token=source_generation,
            )

        if event_type in self._TERMINAL_EVENT_TYPES:
            with self._state_lock:
                if (
                    self._accepted_physical_generation_token
                    == source_generation
                    and (
                        not self._active_run_id
                        or self._active_run_id == event_run_id
                    )
                ):
                    self._clear_active_run_state_locked()

    def _stderr_tail_text(self) -> str:
        with self._state_lock:
            return "\n".join(self._stderr_tail)[-2000:]

    def _monitor_loop(self) -> None:
        while self._running:
            self._check_worker_health()
            time.sleep(0.2)

    def _check_worker_health(self) -> None:
        with self._start_lock:
            self._check_worker_health_locked()

    def _check_worker_health_locked(self) -> None:
        with self._state_lock:
            process = self._process
            generation_token = self._physical_generation_token
            if (
                process is not None
                and self._accepted_physical_generation_token
                != generation_token
            ):
                return
            active_run_id = self._active_run_id
            if active_run_id and self._start_run_pending_id == active_run_id:
                return
            workspace_id = self._active_workspace_id
            active_node_id = self._active_node_id
            active_deadline = self._active_node_deadline
            active_timeout_sec = self._active_node_timeout_sec
        if process is None:
            return
        if process.poll() is None:
            if (
                active_run_id
                and active_node_id
                and active_deadline > 0.0
                and time.monotonic() >= active_deadline
            ):
                self._terminate_timed_out_worker(
                    process,
                    run_id=active_run_id,
                    workspace_id=workspace_id,
                    node_id=active_node_id,
                    timeout_sec=active_timeout_sec,
                    generation_token=generation_token,
                )
            return

        with self._state_lock:
            if (
                self._process is not process
                or self._physical_generation_token != generation_token
                or self._accepted_physical_generation_token != generation_token
            ):
                return
            run_id = self._active_run_id
            run_workspace = self._active_workspace_id
            failed_node_id = self._active_node_id
            self._accepted_physical_generation_token = -1
            self._clear_active_run_state_locked()

        self._notify_generation_change(
            reason="external_python_worker_terminated",
            generation_token=generation_token,
        )

        if active_run_id and run_id == active_run_id:
            stderr_tail = self._stderr_tail_text()
            detail = f"\n{stderr_tail}" if stderr_tail else ""
            self._dispatch_event(
                RunFailedEvent(
                    run_id=active_run_id,
                    workspace_id=workspace_id or run_workspace,
                    node_id=failed_node_id,
                    error="External Python workflow worker terminated unexpectedly.",
                    traceback=detail,
                    fatal=True,
                ),
                generation_token=generation_token,
            )
            self._dispatch_event(
                RunStateEvent(
                    run_id=active_run_id,
                    workspace_id=workspace_id or run_workspace,
                    state="error",
                    transition="fail",
                    reason="external_python_worker_terminated",
                ),
                generation_token=generation_token,
            )

    def _terminate_timed_out_worker(
        self,
        process: subprocess.Popen,
        *,
        run_id: str,
        workspace_id: str,
        node_id: str,
        timeout_sec: float,
        generation_token: int,
    ) -> None:
        with self._state_lock:
            if (
                self._active_run_id != run_id
                or self._process is not process
                or self._physical_generation_token != generation_token
                or self._accepted_physical_generation_token != generation_token
            ):
                return
            self._accepted_physical_generation_token = -1
        try:
            self._terminate_process(process)
        except RuntimeError as exc:
            self._restore_physical_generation(generation_token)
            self._emit_protocol_error(
                f"Failed to terminate timed-out external Python worker: {exc}",
                run_id=run_id,
                command="start_run",
            )
            return
        with self._state_lock:
            if (
                self._active_run_id != run_id
                or self._process is not process
                or self._physical_generation_token != generation_token
                or self._accepted_physical_generation_token != -1
            ):
                return
            run_workspace = self._active_workspace_id
            self._clear_active_run_state_locked()

        error = f"Python Script timed out after {timeout_sec:.2f} seconds."
        self._dispatch_event(
            RunFailedEvent(
                run_id=run_id,
                workspace_id=workspace_id or run_workspace,
                node_id=node_id,
                error=error,
                traceback="",
                fatal=True,
            ),
            generation_token=generation_token,
        )
        self._dispatch_event(
            RunStateEvent(
                run_id=run_id,
                workspace_id=workspace_id or run_workspace,
                state="error",
                transition="fail",
                reason="python_script_timeout",
            ),
            generation_token=generation_token,
        )

    def _terminate_process(self, process: subprocess.Popen) -> None:
        try:
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=0.5)
        except Exception as exc:
            raise RuntimeError(
                "the external Python worker could not be terminated"
            ) from exc
        if process.poll() is None:
            raise RuntimeError(
                "the external Python worker did not terminate"
            )

    def _retire_external_resources(
        self,
        process: subprocess.Popen | None,
    ) -> None:
        if process is not None and process.poll() is None:
            raise RuntimeError(
                "cannot retire a live external Python worker"
            )
        with self._state_lock:
            stdout_thread = self._stdout_thread
            stderr_thread = self._stderr_thread
        for thread in (stdout_thread, stderr_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=1.0)
        if any(
            thread is not None and thread.is_alive()
            for thread in (stdout_thread, stderr_thread)
        ):
            raise RuntimeError(
                "the external Python worker listeners did not terminate"
            )
        with self._state_lock:
            if self._process is process:
                self._process = None
            if self._stdout_thread is stdout_thread:
                self._stdout_thread = None
            if self._stderr_thread is stderr_thread:
                self._stderr_thread = None

    def _stop_external_process(
        self,
        process: subprocess.Popen | None,
        *,
        graceful: bool,
    ) -> None:
        retiring_generation = self._invalidate_physical_generation()
        try:
            if process is None:
                self._retire_external_resources(None)
                return
            if process.poll() is None and graceful:
                self._post_command(ShutdownCommand())
                try:
                    process.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    self._terminate_process(process)
            elif process.poll() is None:
                self._terminate_process(process)
            if process.poll() is None:
                raise RuntimeError(
                    "the previous external Python worker did not terminate"
                )
            self._retire_external_resources(process)
        except Exception:
            self._restore_physical_generation(retiring_generation)
            raise

    def shutdown(self) -> None:
        with self._start_lock:
            with self._state_lock:
                process = self._process
                self._clear_active_run_state_locked()
            try:
                self._stop_external_process(process, graceful=True)
            except RuntimeError:
                pass
            self._running = False
        with self._viewer_request_lock:
            self._pending_viewer_requests.clear()
            self._viewer_session_ids.clear()
            self._viewer_session_generations.clear()
        for thread in (self._stdout_thread, self._stderr_thread, self._monitor_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=1.0)


class TrustedInProcessExecutionClient(_ExecutionClientCommon):
    def __init__(self, *, worker_services: WorkerServices | None = None) -> None:
        self._data_types: DataTypeCatalog | None = None
        self._catalog_generation_fingerprint = ""
        self._plugin_bundles: tuple[PluginBundleRef, ...] = ()
        self._plugin_fingerprint = EMPTY_PLUGIN_FINGERPRINT
        self._runtime_registry_generation_fingerprint = ""
        self._registry_contract_generation_fingerprint = ""
        self._addon_runtime_config: tuple[tuple[str, bool], ...] = ()
        self._catalog_generation_token = 0
        self._accepted_physical_generation_token = 0
        self._run_generation_tokens: dict[str, int] = {}
        self._command_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._event_queue: queue.Queue[Any] = queue.Queue()
        self._worker_services = worker_services or WorkerServices()
        self._run_thread: threading.Thread | None = None
        self._start_lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._generation_callbacks: list[Callable[..., None]] = []
        self._active_run_id = ""
        self._active_workspace_id = ""
        self._start_run_pending_id = ""
        self._active_node_id = ""
        self._active_node_deadline = 0.0
        self._active_node_timeout_sec = 0.0
        self._script_timeout_by_node_id: dict[str, float] = {}
        self._viewer_request_lock = threading.Lock()
        self._pending_viewer_requests: dict[str, _PendingViewerRequest] = {}
        self._viewer_session_ids: set[tuple[str, str]] = set()
        self._viewer_session_generations: dict[tuple[str, str], int] = {}
        self._listener_thread = threading.Thread(
            target=self._event_listener,
            daemon=True,
            name="trusted-execution-event-listener",
        )
        self._running = True
        self._listener_thread.start()

    def _post_command(self, command: WorkerCommand) -> bool:
        try:
            self._command_queue.put(self._encode_command(command))
            return True
        except Exception as exc:  # noqa: BLE001
            self._emit_protocol_error(
                f"Failed to dispatch command: {exc}",
                run_id=getattr(command, "run_id", ""),
                request_id=getattr(command, "request_id", ""),
                command=getattr(command, "type", ""),
            )
            return False

    def _drain_command_queue(self) -> None:
        while True:
            try:
                self._command_queue.get_nowait()
            except queue.Empty:
                return

    def _recycle_catalog_generation(self) -> None:
        with self._state_lock:
            run_thread = self._run_thread
            retiring_generation = self._catalog_generation_token
        if run_thread is not None and run_thread.is_alive():
            raise DataTypeCatalogError(
                "trusted worker generation cannot be recycled during an active run"
            )
        with self._state_lock:
            if self._catalog_generation_token == retiring_generation:
                self._accepted_physical_generation_token = -1
        try:
            self._worker_services.reset()
            DEFAULT_RUNTIME_PREPARATION_CACHE.clear()
        except BaseException:
            with self._state_lock:
                if self._catalog_generation_token == retiring_generation:
                    self._accepted_physical_generation_token = retiring_generation
            raise
        with self._state_lock:
            self._run_thread = None

    @_registry_admitted
    def start_run(
        self,
        project_path: str,
        workspace_id: str,
        trigger: dict[str, Any] | None = None,
        *,
        execution_backend: ExecutionBackendSelection | dict[str, Any] | None = None,
        target_node_ids: tuple[str, ...] | list[str] | None = None,
        trigger_publications: dict[str, SettledPortResult] | None = None,
        trigger_captures: dict[str, SettledPortResult] | None = None,
        clicked_trigger_node_id: str = "",
        data_types: DataTypeCatalog | None = None,
        plugin_bundles: tuple[PluginBundleRef, ...] = (),
        plugin_fingerprint: str = EMPTY_PLUGIN_FINGERPRINT,
        registry_contract_fingerprint: str = EMPTY_REGISTRY_CONTRACT_FINGERPRINT,
        addon_runtime_config: tuple[tuple[str, bool], ...] = (),
        _reserved_run_id: str = "",
        _reservation_prepared: bool = False,
        _prepared_command: StartRunCommand | None = None,
    ) -> str:
        trigger_payload = dict(trigger or {})
        run_id = _reserved_run_id or f"run_{uuid.uuid4().hex[:8]}"
        runtime_snapshot = trigger_payload.pop("runtime_snapshot", None)
        command_target_node_ids = trigger_payload.pop(
            "target_node_ids", target_node_ids or ()
        )
        command_trigger_publications = trigger_payload.pop(
            "trigger_publications", trigger_publications or {}
        )
        command_trigger_captures = trigger_payload.pop(
            "trigger_captures", trigger_captures or {}
        )
        command_clicked_trigger_node_id = trigger_payload.pop(
            "clicked_trigger_node_id", clicked_trigger_node_id
        )
        command_developer_mode = trigger_payload.pop("developer_mode", False)
        external_function_bundles = tuple(
            bundle
            for bundle in plugin_bundles
            if bundle.owner_id != INTERNAL_BUILTIN_FUNCTION_OWNER_ID
        )
        if external_function_bundles:
            self._emit_protocol_error(
                "External function nodes require process-isolated execution; "
                "trusted in-process execution is unavailable while external "
                "function generations are active.",
                run_id=run_id,
                command="start_run",
            )
            return ""
        selection = coerce_execution_backend_selection(
            execution_backend
            or ExecutionBackendSelection(
                backend_id=TRUSTED_IN_PROCESS_BACKEND,
                isolation="in_process",
                reason="trusted_in_process_opt_in",
                trusted_in_process=True,
            )
        )
        try:
            prepared_start = _reservation_prepared or self._prepare_start_run(
                run_id,
                workspace_id,
                data_types,
                plugin_bundles,
                plugin_fingerprint,
                registry_contract_fingerprint,
                addon_runtime_config,
            )
        except (TypeError, ValueError) as exc:
            self._emit_protocol_error(str(exc), run_id=run_id, command="start_run")
            return ""
        if not prepared_start:
            self._emit_protocol_error(
                "Trusted in-process execution already has an active run.",
                run_id=run_id,
                command="start_run",
            )
            return ""
        with self._state_lock:
            generation_token = self._catalog_generation_token
            self._accepted_physical_generation_token = generation_token
        try:
            catalog_fingerprint, catalog_revisions = self._catalog_agreement()
            command_plugin_bundles, command_plugin_fingerprint, runtime_fingerprint = (
                self._plugin_agreement()
            )
            contract_fingerprint, command_addon_runtime_config = (
                self._registry_contract_agreement()
            )
            command_source: StartRunCommand | dict[str, Any] = (
                _prepared_command
                if _prepared_command is not None
                else {
                    "run_id": run_id,
                    "project_path": project_path,
                    "workspace_id": workspace_id,
                    "trigger": trigger_payload,
                    "runtime_snapshot": runtime_snapshot,
                    "execution_backend": selection.to_payload(),
                    "target_node_ids": command_target_node_ids,
                    "trigger_publications": command_trigger_publications,
                    "trigger_captures": command_trigger_captures,
                    "clicked_trigger_node_id": command_clicked_trigger_node_id,
                    "developer_mode": command_developer_mode,
                    "catalog_fingerprint": catalog_fingerprint,
                    "catalog_revisions": catalog_revisions,
                    "plugin_bundles": command_plugin_bundles,
                    "plugin_fingerprint": command_plugin_fingerprint,
                    "runtime_registry_fingerprint": runtime_fingerprint,
                    "registry_contract_fingerprint": contract_fingerprint,
                    "addon_runtime_config": command_addon_runtime_config,
                }
            )
            command = coerce_start_run_command(
                command_source,
                catalog=self._data_types,
            )
            if (
                command.run_id != run_id
                or command.workspace_id != workspace_id
                or command.execution_backend != selection
            ):
                raise ValueError("prepared command does not match reserved trusted run")
            command = self._decode_command(self._encode_command(command))
        except (TypeError, ValueError) as exc:
            self._release_start_run(run_id)
            self._emit_protocol_error(str(exc), run_id=run_id, command="start_run")
            return ""

        script_timeouts = _python_script_timeout_by_node_id(
            command.runtime_snapshot,
            workspace_id,
        )
        if script_timeouts:
            self._release_start_run(run_id)
            self._emit_protocol_error(
                "Python Script timeouts require process-isolated execution; "
                "trusted in-process execution cannot force-stop Python threads.",
                run_id=run_id,
                command="start_run",
            )
            return ""

        try:
            with self._state_lock:
                self._script_timeout_by_node_id = {}
                self._clear_active_node_state_locked()
                self._drain_command_queue()
                self._run_thread = threading.Thread(
                    target=self._run_workflow_thread,
                    args=(command, generation_token),
                    daemon=True,
                    name=f"trusted-execution-{run_id}",
                )
                self._run_thread.start()
                self._start_run_pending_id = ""
        except Exception as exc:  # noqa: BLE001
            self._release_start_run(run_id)
            self._emit_protocol_error(
                f"Failed to start trusted execution thread: {exc}",
                run_id=run_id,
                command="start_run",
            )
            return ""
        return run_id

    def _run_workflow_thread(
        self,
        command,  # noqa: ANN001
        generation_token: int,
    ) -> None:
        event_sink = _GenerationTaggedEventSink(
            self._event_queue,
            generation_token,
        )
        try:
            run_workflow(
                command,
                event_sink,
                command_queue=self._command_queue,
                worker_services=self._worker_services,
            )
        except BaseException as exc:  # noqa: BLE001
            error = str(exc)
            traceback_text = traceback.format_exc()
            with self._start_lock:
                with self._state_lock:
                    if (
                        self._catalog_generation_token != generation_token
                        or self._accepted_physical_generation_token
                        != generation_token
                    ):
                        return
                    failed_node_id = self._active_node_id
                    self._accepted_physical_generation_token = -1
                try:
                    self._worker_services.reset()
                except BaseException as reset_exc:  # noqa: BLE001
                    error = f"{error} (worker reset failed: {reset_exc})"
                with self._state_lock:
                    if self._catalog_generation_token != generation_token:
                        return
                    successor_generation = generation_token + 1
                    self._catalog_generation_token = successor_generation
                    self._accepted_physical_generation_token = (
                        successor_generation
                    )
                    self._run_generation_tokens.clear()
                    self._run_generation_tokens[command.run_id] = (
                        successor_generation
                    )
                    self._run_thread = None
                    with self._viewer_request_lock:
                        stale_pending = tuple(
                            pending
                            for pending in self._pending_viewer_requests.values()
                            if pending.generation_token == generation_token
                        )
                        for pending in stale_pending:
                            self._pending_viewer_requests.pop(
                                pending.request_id,
                                None,
                            )
                        stale_session_keys = tuple(
                            session_key
                            for session_key in (
                                self._viewer_session_ids
                                | self._viewer_session_generations.keys()
                            )
                            if self._viewer_session_generations.get(
                                session_key, generation_token
                            )
                            == generation_token
                        )
                        for session_key in stale_session_keys:
                            self._viewer_session_ids.discard(session_key)
                            self._viewer_session_generations.pop(
                                session_key,
                                None,
                            )
            for pending in stale_pending:
                self._dispatch_viewer_request_failure(
                    pending,
                    "The trusted worker generation reset before the viewer "
                    "request completed.",
                    generation_token=successor_generation,
                )
            successor_sink = _GenerationTaggedEventSink(
                self._event_queue,
                successor_generation,
            )
            successor_sink.put(
                event_to_dict(
                    RunFailedEvent(
                        run_id=command.run_id,
                        workspace_id=command.workspace_id,
                        node_id=failed_node_id,
                        error=error,
                        traceback=traceback_text,
                    ),
                    catalog=self._data_types,
                )
            )
            successor_sink.put(
                event_to_dict(
                    RunStateEvent(
                        run_id=command.run_id,
                        workspace_id=command.workspace_id,
                        state="error",
                        transition="fail",
                        reason="trusted_in_process_exception",
                    ),
                    catalog=self._data_types,
                )
            )

    def _send_viewer_command(
        self,
        command: WorkerCommand,
        *,
        require_session_id: bool = False,
    ) -> str:
        try:
            command = self._decode_command(self._encode_command(command))
        except (TypeError, ValueError) as exc:
            request_id = str(getattr(command, "request_id", ""))
            pending = _PendingViewerRequest(
                request_id=request_id,
                command=str(getattr(command, "type", "")),
                workspace_id=str(getattr(command, "workspace_id", "")),
                node_id=str(getattr(command, "node_id", "")),
                session_id=str(getattr(command, "session_id", "")),
            )
            self._dispatch_viewer_request_failure(pending, str(exc))
            return request_id
        request_id = str(getattr(command, "request_id", ""))
        pending = _PendingViewerRequest(
            request_id=request_id,
            command=str(getattr(command, "type", "")),
            workspace_id=str(getattr(command, "workspace_id", "")),
            node_id=str(getattr(command, "node_id", "")),
            session_id=str(getattr(command, "session_id", "")),
        )
        with self._start_lock:
            self._track_viewer_request(pending)
            if require_session_id and not pending.session_id:
                self._complete_viewer_request(request_id)
                self._dispatch_viewer_request_failure(
                    pending,
                    "session_id is required.",
                )
                return request_id
            with self._state_lock:
                active_thread = self._run_thread
                generation_token = self._catalog_generation_token
            if active_thread is not None and active_thread.is_alive():
                if not self._post_command(command):
                    self._complete_viewer_request(request_id)
                    self._dispatch_viewer_request_failure(
                        pending, "Failed to dispatch command."
                    )
                return request_id
            dispatch_viewer_command(
                command,
                event_queue=_GenerationTaggedEventSink(
                    self._event_queue,
                    generation_token,
                ),
                worker_services=self._worker_services,
            )
        return request_id

    def shutdown(self) -> None:
        self._running = False
        self._event_queue.put(dict(_LISTENER_SHUTDOWN_SENTINEL))
        with self._state_lock:
            run_id = self._active_run_id
            thread = self._run_thread
        if run_id:
            self._post_command(ShutdownCommand())
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)
        with self._state_lock:
            self._clear_active_run_state_locked()
            self._run_thread = None
        with self._viewer_request_lock:
            self._pending_viewer_requests.clear()
            self._viewer_session_ids.clear()
            self._viewer_session_generations.clear()
        if self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)
        self._worker_services.reset()

    def _check_worker_health(self) -> None:
        with self._state_lock:
            thread = self._run_thread
            active_run_id = self._active_run_id
            workspace_id = self._active_workspace_id
            active_node_id = self._active_node_id
        if thread is None or thread.is_alive() or not active_run_id:
            return
        thread.join(timeout=0.1)
        with self._state_lock:
            if self._active_run_id != active_run_id:
                return
            failed_node_id = self._active_node_id or active_node_id
            self._clear_active_run_state_locked()
            self._run_thread = None
        self._dispatch_event(
            RunFailedEvent(
                run_id=active_run_id,
                workspace_id=workspace_id,
                node_id=failed_node_id,
                error="Trusted in-process execution terminated unexpectedly.",
                traceback="",
                fatal=True,
            )
        )
        self._dispatch_event(
            RunStateEvent(
                run_id=active_run_id,
                workspace_id=workspace_id,
                state="error",
                transition="fail",
                reason="trusted_in_process_terminated",
            )
        )

    def _event_listener(self) -> None:
        while self._running:
            try:
                source_event = self._event_queue.get(timeout=0.2)
            except queue.Empty:
                self._check_worker_health()
                continue

            if source_event == _LISTENER_SHUTDOWN_SENTINEL:
                break
            if (
                not isinstance(source_event, tuple)
                or len(source_event) != 2
                or not isinstance(source_event[0], int)
            ):
                continue
            generation_token, event = source_event
            if not self._source_generation_is_current(generation_token):
                continue
            if not isinstance(event, dict):
                self._emit_protocol_error(
                    "Received non-dictionary event from trusted worker."
                )
                continue

            try:
                typed_event = self._decode_event(dict(event))
            except (TypeError, ValueError) as exc:
                if self._source_generation_is_current(generation_token):
                    self._emit_protocol_error(
                        f"Received invalid worker event: {exc}"
                    )
                continue

            if not self._source_generation_is_current(generation_token):
                continue
            payload = event_to_dict(typed_event, catalog=self._data_types)
            event_type = payload.get("type", "")
            event_run_id = payload.get("run_id", "")
            viewer_failure_event = None
            if event_type == "protocol_error":
                viewer_failure_event = self._viewer_protocol_error_failure(
                    payload,
                    expected_generation_token=generation_token,
                )
            elif event_type in VIEWER_RESPONSE_EVENT_TYPES:
                response_generation = self._record_viewer_response_state(
                    payload,
                    default_generation_token=generation_token,
                    expected_generation_token=generation_token,
                )
                if response_generation != generation_token:
                    continue
            self._record_execution_event_state(
                payload,
                expected_generation_token=generation_token,
            )
            if not self._source_generation_is_current(generation_token):
                continue
            self._dispatch_event(
                typed_event,
                generation_token=generation_token,
            )
            if viewer_failure_event is not None:
                self._dispatch_event(
                    viewer_failure_event,
                    generation_token=generation_token,
                )

            if event_type in self._TERMINAL_EVENT_TYPES:
                with self._state_lock:
                    if (
                        self._accepted_physical_generation_token
                        == generation_token
                        and (
                            not self._active_run_id
                            or self._active_run_id == event_run_id
                        )
                    ):
                        self._clear_active_run_state_locked()


class ExecutionBackendClient:
    _TERMINAL_EVENT_TYPES = {"run_completed", "run_failed", "run_stopped"}
    _RETAINED_VIEWER_RUN_LIMIT = 64

    def __init__(
        self, *, orchestrator: ExecutionBackendOrchestrator | None = None
    ) -> None:
        self._orchestrator = orchestrator or ExecutionBackendOrchestrator()
        self._process_client = ProcessExecutionClient()
        self._trusted_client = TrustedInProcessExecutionClient()
        self._external_python_client = ExternalPythonExecutionClient()
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._generation_callbacks: list[
            Callable[[dict[str, Any], ExecutionGenerationSnapshot], None]
        ] = []
        self._published_registry: NodeRegistry | None = None
        self._run_reservations: dict[str, tuple[ExecutionRunReservation, Any]] = {}
        self._client_selections: dict[int, ExecutionBackendSelection] = {
            id(self._process_client): ExecutionBackendSelection(),
            id(self._trusted_client): ExecutionBackendSelection(
                backend_id=TRUSTED_IN_PROCESS_BACKEND,
                isolation="in_process",
                reason="trusted_in_process_opt_in",
                trusted_in_process=True,
            ),
            id(self._external_python_client): ExecutionBackendSelection(
                backend_id=EXTERNAL_SUBPROCESS_BACKEND,
                isolation="external_subprocess",
                reason="external_runtime_contract",
                external_subprocess=True,
            ),
        }
        self._active_clients: dict[str, Any] = {}
        self._run_clients: dict[str, Any] = {}
        self._run_client_generations: dict[str, int] = {}
        self._run_generation_snapshots: dict[
            str,
            ExecutionGenerationSnapshot,
        ] = {}
        self._run_workspace_ids: dict[str, str] = {}
        self._workspace_clients: dict[str, Any] = {}
        self._workspace_client_generations: dict[str, int] = {}
        self._session_clients: dict[tuple[str, str], Any] = {}
        self._session_client_generations: dict[tuple[str, str], int] = {}
        self._provisional_viewer_routes: dict[
            tuple[str, str],
            _ProvisionalViewerRoute,
        ] = {}
        self._provisional_request_sessions: dict[
            str,
            tuple[str, str],
        ] = {}
        self._next_viewer_request_order = 0
        self._terminal_run_ids_seen: set[str] = set()
        self._active_lock = threading.Lock()
        self._registry_publication_lock = threading.RLock()
        self._process_client.subscribe(
            lambda event, generation: self._dispatch_client_event(
                self._process_client,
                event,
                generation_token=generation,
            ),
            include_generation=True,
        )
        self._trusted_client.subscribe(
            lambda event, generation: self._dispatch_client_event(
                self._trusted_client,
                event,
                generation_token=generation,
            ),
            include_generation=True,
        )
        self._external_python_client.subscribe(
            lambda event, generation: self._dispatch_client_event(
                self._external_python_client,
                event,
                generation_token=generation,
            ),
            include_generation=True,
        )

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._callbacks.append(callback)

    def subscribe_generation_events(
        self,
        callback: Callable[[dict[str, Any], ExecutionGenerationSnapshot], None],
    ) -> None:
        self._generation_callbacks.append(callback)

    def _client_for_selection(self, selection: ExecutionBackendSelection) -> Any:
        if selection.backend_id == EXTERNAL_SUBPROCESS_BACKEND:
            return self._external_python_client
        if selection.backend_id == TRUSTED_IN_PROCESS_BACKEND:
            return self._trusted_client
        return self._process_client

    def resolve_execution_selection(
        self,
        policy: Any,
        runtime_snapshot: Any = None,
    ) -> ExecutionBackendSelection:
        workflow_python_path = workflow_python_path_from_snapshot(runtime_snapshot)
        raw_policy = policy
        if raw_policy is None and workflow_python_path:
            raw_policy = {
                "requested_backend": EXTERNAL_SUBPROCESS_BACKEND,
                "allow_external_subprocess": True,
                "python_executable": workflow_python_path,
                "reason": "workflow_python_path",
            }
        selection = self._orchestrator.select(raw_policy)
        if selection.backend_id != EXTERNAL_SUBPROCESS_BACKEND:
            return selection
        python_executable = normalize_path_text(selection.python_executable)
        if not python_executable:
            python_executable = workflow_python_path
        if not python_executable:
            raise ValueError(
                "External Python workflow execution requires python_executable or "
                "Workflow Settings > Environment > Workflow Override."
            )
        python_environment = resolve_python_environment(python_executable)
        if not python_environment.valid:
            raise ValueError(python_environment.error)
        return replace(
            selection,
            python_executable=python_environment.python_executable,
            reason=selection.reason
            or ("workflow_python_path" if workflow_python_path else ""),
        )

    def _generation_snapshot_for_client(
        self,
        client: Any,
        selection: ExecutionBackendSelection,
        *,
        registry_contract_fingerprint: str = "",
    ) -> ExecutionGenerationSnapshot:
        with client._state_lock:  # noqa: SLF001
            backend_generation = int(
                getattr(client, "_catalog_generation_token", 0)
            )
            runtime_generation = int(
                getattr(client, "_physical_generation_token", backend_generation)
            )
            accepted_generation = int(
                getattr(
                    client,
                    "_accepted_physical_generation_token",
                    runtime_generation,
                )
            )
            registry_fingerprint = str(
                getattr(client, "_registry_contract_generation_fingerprint", "")
            )
            concrete_environment_digest = str(
                getattr(client, "_execution_environment_digest", "")
            )
            environment_registry_fingerprint = str(
                getattr(
                    client,
                    "_execution_environment_registry_fingerprint",
                    "",
                )
            )
            environment_selection_digest = str(
                getattr(
                    client,
                    "_execution_environment_selection_digest",
                    "",
                )
            )
        live = bool(client._viewer_generation_is_live())  # noqa: SLF001
        available = bool(
            backend_generation > 0
            and runtime_generation > 0
            and backend_generation == runtime_generation == accepted_generation
            and live
        )
        if registry_contract_fingerprint:
            registry_fingerprint = _registry_contract_digest(
                registry_contract_fingerprint
            )
        expected_registry = getattr(self, "_published_registry", None)
        if not registry_fingerprint and expected_registry is not None:
            registry_fingerprint = expected_registry.contract_fingerprint()
        expected_registry_fingerprint = (
            registry_fingerprint or EMPTY_REGISTRY_CONTRACT_FINGERPRINT
        )
        environment_ready = bool(
            len(concrete_environment_digest) == 64
            and environment_registry_fingerprint == expected_registry_fingerprint
            and environment_selection_digest
            == canonical_digest(_result_affecting_selection_payload(selection))
        )
        environment_digest = (
            concrete_environment_digest
            if environment_ready
            else canonical_digest(
                {
                    "kind": "execution_environment_unavailable",
                    "backend_id": selection.backend_id,
                    "isolation": selection.isolation,
                    "runtime_backend_ids": selection.runtime_backend_ids,
                    "registry_contract_fingerprint": expected_registry_fingerprint,
                }
            )
        )
        available = available and environment_ready
        return ExecutionGenerationSnapshot(
            selection=selection,
            backend_generation=backend_generation,
            runtime_generation=runtime_generation,
            environment_digest=environment_digest,
            available=available,
            reason=(
                ""
                if available
                else (
                    "execution_environment_unavailable"
                    if live and backend_generation > 0
                    else "execution_generation_unavailable"
                )
            ),
        )

    def _bind_route_environment(
        self,
        client: Any,
        selection: ExecutionBackendSelection,
        registry: NodeRegistry,
        *,
        publish: bool = True,
    ) -> str:
        registry_fingerprint = registry.contract_fingerprint()
        selection_payload = _result_affecting_selection_payload(selection)
        selection_digest = canonical_digest(selection_payload)
        with client._state_lock:  # noqa: SLF001
            if (
                len(getattr(client, "_execution_environment_digest", "")) == 64
                and getattr(
                    client,
                    "_execution_environment_registry_fingerprint",
                    "",
                )
                == registry_fingerprint
                and getattr(
                    client,
                    "_execution_environment_selection_digest",
                    "",
                )
                == selection_digest
            ):
                return str(client._execution_environment_digest)  # noqa: SLF001
        declared_facts = registry.execution_environment_facts()
        package_names = tuple(declared_facts.get("python_packages", ()))
        if selection.backend_id == EXTERNAL_SUBPROCESS_BACKEND:
            result = subprocess.run(
                [
                    selection.python_executable,
                    "-c",
                    _EXTERNAL_RUNTIME_IDENTITY_PROBE,
                    json.dumps(package_names, separators=(",", ":")),
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=10.0,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "External Python runtime identity handshake failed."
                )
            try:
                runtime_facts = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "External Python runtime identity handshake was invalid."
                ) from exc
            if not isinstance(runtime_facts, Mapping):
                raise RuntimeError(
                    "External Python runtime identity handshake was invalid."
                )
        else:
            runtime_facts = _local_runtime_identity(package_names)
        environment_digest = canonical_digest(
            {
                "schema_version": 1,
                "selection": selection_payload,
                "runtime": dict(runtime_facts),
                "declared": declared_facts,
                "registry_contract_fingerprint": registry_fingerprint,
            }
        )
        if publish:
            with client._state_lock:  # noqa: SLF001
                client._execution_environment_digest = environment_digest  # noqa: SLF001
                client._execution_environment_registry_fingerprint = (  # noqa: SLF001
                    registry_fingerprint
                )
                client._execution_environment_selection_digest = (  # noqa: SLF001
                    selection_digest
                )
        return environment_digest

    def execution_generation_snapshot(
        self,
        selection: ExecutionBackendSelection,
        *,
        registry_contract_fingerprint: str = "",
    ) -> ExecutionGenerationSnapshot:
        if not isinstance(selection, ExecutionBackendSelection):
            raise TypeError("selection must be an ExecutionBackendSelection")
        client = self._client_for_selection(selection)
        return self._generation_snapshot_for_client(
            client,
            selection,
            registry_contract_fingerprint=registry_contract_fingerprint,
        )

    def preview_execution_environment(
        self,
        selection: ExecutionBackendSelection,
        registry: NodeRegistry,
    ) -> str:
        """Compute the exact result-affecting environment without starting a run."""

        if not isinstance(registry, NodeRegistry):
            raise TypeError("registry must be a NodeRegistry")
        client = self._client_for_selection(selection)
        return self._bind_route_environment(
            client,
            selection,
            registry,
            publish=False,
        )

    @_registry_admitted
    def reserve_run(
        self,
        selection: ExecutionBackendSelection,
        workspace_id: str,
    ) -> ExecutionRunReservation:
        registry = self._published_registry
        if registry is None:
            raise RuntimeError("reserve_run requires a published registry")
        client = self._client_for_selection(selection)
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        normalized_workspace_id = str(workspace_id).strip()
        if not normalized_workspace_id:
            raise ValueError("workspace_id must be non-empty")
        try:
            if client is self._process_client:
                client._ensure_process()  # noqa: SLF001
            elif client is self._external_python_client:
                python_executable = str(selection.python_executable).strip()
                client._assert_process_transition_allowed()  # noqa: SLF001
                client._verify_runtime_available(python_executable)  # noqa: SLF001
                client._ensure_process(python_executable)  # noqa: SLF001
            prepared = client._prepare_start_run(  # noqa: SLF001
                run_id,
                normalized_workspace_id,
                registry.data_types,
                registry.plugin_bundle_refs(),
                registry.plugin_fingerprint(),
                registry.contract_fingerprint(),
                registry.addon_runtime_config(),
            )
            if not prepared:
                raise RuntimeError("execution backend already has an active run")
            if client is self._trusted_client:
                with client._state_lock:  # noqa: SLF001
                    client._accepted_physical_generation_token = (  # noqa: SLF001
                        client._catalog_generation_token  # noqa: SLF001
                    )
            self._bind_route_environment(client, selection, registry)
            self._client_selections[id(client)] = selection
            snapshot = self._generation_snapshot_for_client(client, selection)
            if not snapshot.available:
                raise RuntimeError(snapshot.reason)
        except Exception:
            client._release_start_run(run_id)  # noqa: SLF001
            raise
        reservation = ExecutionRunReservation(
            run_id=run_id,
            workspace_id=normalized_workspace_id,
            selection=selection,
            generation_snapshot=snapshot,
        )
        with self._active_lock:
            self._run_reservations[run_id] = (reservation, client)
        return reservation

    def release_run_reservation(
        self,
        reservation: ExecutionRunReservation,
        reason: str,
    ) -> None:
        del reason
        with self._active_lock:
            stored = self._run_reservations.pop(reservation.run_id, None)
        if stored is not None:
            stored[1]._release_start_run(reservation.run_id)  # noqa: SLF001

    @_registry_admitted
    def start_reserved_run(
        self,
        reservation: ExecutionRunReservation,
        command: Any,
    ) -> str:
        from ea_node_editor.execution.protocol import StartRunCommand

        if not isinstance(reservation, ExecutionRunReservation):
            raise TypeError("reservation must be an ExecutionRunReservation")
        if not isinstance(command, StartRunCommand):
            raise TypeError("command must be a StartRunCommand")
        with self._active_lock:
            stored = self._run_reservations.pop(reservation.run_id, None)
        if stored is None or stored[0] != reservation:
            raise ValueError("run reservation is unknown or already consumed")
        client = stored[1]
        registry = self._published_registry
        if registry is None:
            client._release_start_run(reservation.run_id)  # noqa: SLF001
            raise RuntimeError("start_reserved_run requires a published registry")
        if (
            command.run_id != reservation.run_id
            or command.workspace_id != reservation.workspace_id
            or command.execution_backend != reservation.selection
        ):
            client._release_start_run(reservation.run_id)  # noqa: SLF001
            raise ValueError("reserved command does not match the reservation")
        current_generation = self._generation_snapshot_for_client(
            client,
            reservation.selection,
        )
        if not current_generation.compatible_with(reservation.generation_snapshot):
            client._release_start_run(reservation.run_id)  # noqa: SLF001
            raise ValueError("reserved execution generation changed before start")
        if (
            command.dispatch_runtime_generation
            != reservation.generation_snapshot.runtime_generation
            or command.execution_environment_digest
            != reservation.generation_snapshot.environment_digest
            or command.dispatch_runtime_generation
            != current_generation.runtime_generation
            or command.execution_environment_digest
            != current_generation.environment_digest
        ):
            client._release_start_run(reservation.run_id)  # noqa: SLF001
            raise ValueError(
                "prepared command generation does not match the reserved execution"
            )
        with self._active_lock:
            self._active_clients[reservation.run_id] = client
            self._run_clients[reservation.run_id] = client
            self._run_client_generations[reservation.run_id] = (
                reservation.generation_snapshot.backend_generation
            )
            self._run_generation_snapshots[reservation.run_id] = (
                reservation.generation_snapshot
            )
            self._run_workspace_ids[reservation.run_id] = reservation.workspace_id
        try:
            run_id = client.start_run(
                command.project_path,
                command.workspace_id,
                trigger={
                    **dict(command.trigger),
                    "runtime_snapshot": command.runtime_snapshot,
                    "developer_mode": command.developer_mode,
                },
                execution_backend=command.execution_backend,
                target_node_ids=command.target_node_ids,
                trigger_publications=command.trigger_publications,
                trigger_captures=command.trigger_captures,
                clicked_trigger_node_id=command.clicked_trigger_node_id,
                data_types=registry.data_types,
                plugin_bundles=registry.plugin_bundle_refs(),
                plugin_fingerprint=registry.plugin_fingerprint(),
                registry_contract_fingerprint=registry.contract_fingerprint(),
                addon_runtime_config=registry.addon_runtime_config(),
                _reserved_run_id=reservation.run_id,
                _reservation_prepared=True,
                _prepared_command=command,
            )
        except Exception:
            client._release_start_run(reservation.run_id)  # noqa: SLF001
            with self._active_lock:
                self._active_clients.pop(reservation.run_id, None)
                self._run_clients.pop(reservation.run_id, None)
                self._run_client_generations.pop(reservation.run_id, None)
                self._run_generation_snapshots.pop(reservation.run_id, None)
                self._run_workspace_ids.pop(reservation.run_id, None)
            raise
        if run_id == reservation.run_id:
            return run_id
        client._release_start_run(reservation.run_id)  # noqa: SLF001
        with self._active_lock:
            self._active_clients.pop(reservation.run_id, None)
            self._run_clients.pop(reservation.run_id, None)
            self._run_client_generations.pop(reservation.run_id, None)
            self._run_generation_snapshots.pop(reservation.run_id, None)
            self._run_workspace_ids.pop(reservation.run_id, None)
        return ""

    @staticmethod
    def _client_generation_token(client: Any) -> int:
        getter = getattr(client, "_catalog_generation_token_value", None)
        if not callable(getter):
            return 0
        try:
            return int(getter())
        except (TypeError, ValueError):
            return 0

    def _ensure_route_generation_maps_locked(self) -> None:
        if not hasattr(self, "_run_client_generations"):
            self._run_client_generations = {}
        if not hasattr(self, "_run_generation_snapshots"):
            self._run_generation_snapshots = {}
        if not hasattr(self, "_workspace_client_generations"):
            self._workspace_client_generations = {}
        if not hasattr(self, "_session_client_generations"):
            self._session_client_generations = {}
        if not hasattr(self, "_provisional_viewer_routes"):
            self._provisional_viewer_routes = {}
        if not hasattr(self, "_provisional_request_sessions"):
            self._provisional_request_sessions = {}
        if not hasattr(self, "_next_viewer_request_order"):
            self._next_viewer_request_order = 0

    def _apply_provisional_viewer_route_locked(
        self,
        route: _ProvisionalViewerRoute,
    ) -> None:
        session_key = route.session_key
        retained_requests: list[tuple[int, str, Any, int]] = []
        for request_order, request_id, client, generation in route.requests:
            if generation != self._client_generation_token(client):
                self._provisional_request_sessions.pop(request_id, None)
                continue
            retained_requests.append(
                (request_order, request_id, client, generation)
            )
        route.requests = retained_requests
        eligible_requests = [
            record
            for record in retained_requests
            if record[0] > route.baseline_request_order
        ]
        if eligible_requests:
            _order, _request_id, client, generation = eligible_requests[-1]
            self._session_clients[session_key] = client
            self._session_client_generations[session_key] = generation
            return
        baseline_client = route.baseline_client
        if (
            baseline_client is not None
            and route.baseline_generation
            == self._client_generation_token(baseline_client)
        ):
            self._session_clients[session_key] = baseline_client
            self._session_client_generations[session_key] = (
                route.baseline_generation
            )
            return
        self._session_clients.pop(session_key, None)
        self._session_client_generations.pop(session_key, None)

    def _resolve_provisional_viewer_route_locked(
        self,
        *,
        request_id: str,
        succeeded: bool,
        client: Any,
        generation_token: int,
    ) -> None:
        session_key = self._provisional_request_sessions.pop(
            request_id,
            None,
        )
        if session_key is None:
            return
        route = self._provisional_viewer_routes.get(session_key)
        if route is None:
            return
        request_record = next(
            (
                record
                for record in route.requests
                if record[1] == request_id
            ),
            None,
        )
        route.requests = [
            record for record in route.requests if record[1] != request_id
        ]
        if (
            succeeded
            and request_record is not None
            and request_record[2] is client
            and request_record[3] == generation_token
            and request_record[0] > route.baseline_request_order
        ):
            route.baseline_client = client
            route.baseline_generation = generation_token
            route.baseline_request_order = request_record[0]
            workspace_id, _session_id = session_key
            self._workspace_clients[workspace_id] = client
            self._workspace_client_generations[workspace_id] = (
                generation_token
            )
        self._apply_provisional_viewer_route_locked(route)
        if not route.requests:
            self._provisional_viewer_routes.pop(session_key, None)

    def _refresh_provisional_request_generation_locked(
        self,
        *,
        request_id: str,
        client: Any,
        generation_token: int,
    ) -> None:
        session_key = self._provisional_request_sessions.get(request_id)
        if session_key is None:
            return
        route = self._provisional_viewer_routes.get(session_key)
        if route is None:
            return
        route.requests = [
            (
                request_order,
                record_request_id,
                record_client,
                (
                    generation_token
                    if (
                        record_request_id == request_id
                        and record_client is client
                    )
                    else record_generation
                ),
            )
            for (
                request_order,
                record_request_id,
                record_client,
                record_generation,
            ) in route.requests
        ]

    def _prune_provisional_viewer_routes_locked(self, client: Any) -> None:
        current_generation = self._client_generation_token(client)
        for session_key, route in tuple(self._provisional_viewer_routes.items()):
            retained_requests = []
            for request_order, request_id, owner, generation in route.requests:
                if owner is client and generation != current_generation:
                    self._provisional_request_sessions.pop(request_id, None)
                    continue
                retained_requests.append(
                    (request_order, request_id, owner, generation)
                )
            route.requests = retained_requests
            if (
                route.baseline_client is client
                and route.baseline_generation != current_generation
            ):
                route.baseline_client = None
                route.baseline_generation = 0
                route.baseline_request_order = 0
            self._apply_provisional_viewer_route_locked(route)
            if not route.requests:
                self._provisional_viewer_routes.pop(session_key, None)

    def _trim_viewer_run_owners_locked(self) -> None:
        self._ensure_route_generation_maps_locked()
        if len(self._run_clients) <= self._RETAINED_VIEWER_RUN_LIMIT:
            return
        active_run_ids = set(self._active_clients)
        for run_id in tuple(self._run_clients):
            if len(self._run_clients) <= self._RETAINED_VIEWER_RUN_LIMIT:
                break
            workspace_id = self._run_workspace_ids.get(run_id, "")
            if run_id in active_run_ids:
                continue
            client = self._run_clients.pop(run_id, None)
            self._run_client_generations.pop(run_id, None)
            self._run_generation_snapshots.pop(run_id, None)
            self._run_workspace_ids.pop(run_id, None)
            if (
                workspace_id
                and self._workspace_clients.get(workspace_id) is client
                and not any(
                    candidate_workspace_id == workspace_id
                    for candidate_workspace_id in self._run_workspace_ids.values()
                )
                and not any(
                    session_workspace_id == workspace_id
                    for session_workspace_id, _session_id in self._session_clients
                )
            ):
                self._workspace_clients.pop(workspace_id, None)
                self._workspace_client_generations.pop(workspace_id, None)

    def _forget_client_generation_locked(self, client: Any) -> None:
        self._ensure_route_generation_maps_locked()
        current_generation = self._client_generation_token(client)
        stale_run_ids = tuple(
            run_id
            for run_id, owner in self._run_clients.items()
            if owner is client
            and self._run_client_generations.get(
                run_id,
                current_generation,
            )
            != current_generation
        )
        for run_id in stale_run_ids:
            self._active_clients.pop(run_id, None)
            self._run_clients.pop(run_id, None)
            self._run_client_generations.pop(run_id, None)
            self._run_generation_snapshots.pop(run_id, None)
            self._run_workspace_ids.pop(run_id, None)
            self._terminal_run_ids_seen.discard(run_id)
        stale_session_keys = tuple(
            session_key
            for session_key, owner in self._session_clients.items()
            if owner is client
            and self._session_client_generations.get(
                session_key,
                current_generation,
            )
            != current_generation
        )
        for session_key in stale_session_keys:
            self._session_clients.pop(session_key, None)
            self._session_client_generations.pop(session_key, None)
        for workspace_id, owner in tuple(self._workspace_clients.items()):
            if (
                owner is client
                and self._workspace_client_generations.get(
                    workspace_id,
                    current_generation,
                )
                != current_generation
            ):
                self._workspace_clients.pop(workspace_id, None)
                self._workspace_client_generations.pop(workspace_id, None)
        self._prune_provisional_viewer_routes_locked(client)

    def _release_closed_session_owner_locked(
        self,
        *,
        session_id: str,
        workspace_id: str,
    ) -> None:
        self._ensure_route_generation_maps_locked()
        if session_id and workspace_id:
            session_key = (workspace_id, session_id)
            self._session_clients.pop(session_key, None)
            self._session_client_generations.pop(session_key, None)
        if not workspace_id:
            return
        remaining_session_client = None
        remaining_session_generation = 0
        for session_key, session_client in self._session_clients.items():
            session_workspace_id, _session_id = session_key
            if session_workspace_id != workspace_id:
                continue
            session_generation = self._session_client_generations.get(
                session_key,
                self._client_generation_token(session_client),
            )
            if session_generation != self._client_generation_token(session_client):
                continue
            remaining_session_client = session_client
            remaining_session_generation = session_generation
            break
        if remaining_session_client is not None:
            self._workspace_clients[workspace_id] = remaining_session_client
            self._workspace_client_generations[workspace_id] = (
                remaining_session_generation
            )
            return
        if workspace_id in {
            self._run_workspace_ids.get(run_id, "") for run_id in self._active_clients
        }:
            return
        self._workspace_clients.pop(workspace_id, None)
        self._workspace_client_generations.pop(workspace_id, None)
        for run_id, run_workspace_id in tuple(self._run_workspace_ids.items()):
            if run_workspace_id == workspace_id and run_id not in self._active_clients:
                self._run_workspace_ids.pop(run_id, None)
                self._run_clients.pop(run_id, None)
                self._run_client_generations.pop(run_id, None)
                self._run_generation_snapshots.pop(run_id, None)

    def _dispatch_client_event(
        self,
        client: Any,
        event: dict[str, Any],
        *,
        generation_token: int | None = None,
    ) -> None:
        event_type = str(event.get("type", ""))
        run_id = str(event.get("run_id", ""))
        workspace_id = str(event.get("workspace_id", "")).strip()
        session_id = str(event.get("session_id", "")).strip()
        request_id = str(event.get("request_id", "")).strip()
        failed_open = (
            event_type == "viewer_session_failed"
            and str(event.get("command", "")).strip() == "open_viewer_session"
        )
        opened_session = event_type == "viewer_session_opened"
        releases_session = event_type == "viewer_session_closed"
        retains_route = not releases_session and not failed_open
        pinned_generation_snapshot = None
        with self._active_lock:
            self._ensure_route_generation_maps_locked()
            if run_id:
                pinned_generation_snapshot = self._run_generation_snapshots.get(
                    run_id
                )
            tracked_open = bool(
                opened_session
                and request_id
                and request_id in self._provisional_request_sessions
            )
            current_generation = self._client_generation_token(client)
            event_generation = (
                current_generation
                if generation_token is None
                else int(generation_token)
            )
            if client is not None and event_generation != current_generation:
                return
            if client is not None and request_id:
                self._refresh_provisional_request_generation_locked(
                    request_id=request_id,
                    client=client,
                    generation_token=event_generation,
                )
            if client is not None:
                self._forget_client_generation_locked(client)
            if event_type in self._TERMINAL_EVENT_TYPES and run_id:
                self._active_clients.pop(run_id, None)
                self._terminal_run_ids_seen.add(run_id)
                while (
                    len(self._terminal_run_ids_seen) > self._RETAINED_VIEWER_RUN_LIMIT
                ):
                    self._terminal_run_ids_seen.pop()
            if (
                client is not None
                and workspace_id
                and retains_route
                and not tracked_open
            ):
                self._workspace_clients[workspace_id] = client
                self._workspace_client_generations[workspace_id] = event_generation
            if (
                client is not None
                and session_id
                and workspace_id
                and event_type in VIEWER_RESPONSE_EVENT_TYPES
                and retains_route
                and not tracked_open
            ):
                session_key = (workspace_id, session_id)
                self._session_clients[session_key] = client
                self._session_client_generations[session_key] = event_generation
            if client is not None and releases_session:
                self._release_closed_session_owner_locked(
                    session_id=session_id,
                    workspace_id=workspace_id,
                )
            if client is not None and request_id and (opened_session or failed_open):
                self._resolve_provisional_viewer_route_locked(
                    request_id=request_id,
                    succeeded=opened_session,
                    client=client,
                    generation_token=event_generation,
                )
            self._trim_viewer_run_owners_locked()
        generation_callbacks = tuple(getattr(self, "_generation_callbacks", ()))
        if client is not None and generation_callbacks:
            generation_snapshot = pinned_generation_snapshot
            if generation_snapshot is not None:
                current_snapshot = self._generation_snapshot_for_client(
                    client,
                    generation_snapshot.selection,
                )
                if not current_snapshot.available:
                    generation_snapshot = current_snapshot
            if generation_snapshot is None:
                selection = getattr(self, "_client_selections", {}).get(
                    id(client),
                    ExecutionBackendSelection(),
                )
                generation_snapshot = self._generation_snapshot_for_client(
                    client,
                    selection,
                )
            for callback in generation_callbacks:
                try:
                    callback(dict(event), generation_snapshot)
                except Exception:
                    continue
        if event_type == "execution_generation_changed":
            return
        for callback in list(self._callbacks):
            try:
                callback(dict(event))
            except Exception:
                continue

    def _dispatch_event(self, event: dict[str, Any]) -> None:
        self._dispatch_client_event(None, event, generation_token=0)

    def _require_start_catalog(
        self,
        data_types: DataTypeCatalog | None,
    ) -> bool:
        if not isinstance(data_types, DataTypeCatalog):
            self._emit_protocol_error(
                "start_run requires the authoritative data-type catalog"
            )
            return False
        if not data_types.is_frozen:
            self._emit_protocol_error("data-type catalog must be frozen")
            return False
        return True

    @staticmethod
    def _viewer_route_ids(
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> tuple[str, str, str]:
        run_id = str(kwargs.pop("run_id", "") or "").strip()
        workspace_id = str(
            kwargs.get("workspace_id", args[0] if args else "") or ""
        ).strip()
        session_id = str(
            kwargs.get("session_id", args[2] if len(args) > 2 else "") or ""
        ).strip()
        return run_id, workspace_id, session_id

    def _remember_requested_session_owner(
        self,
        *,
        client: Any,
        workspace_id: str,
        session_id: str,
        request_id: str = "",
    ) -> None:
        if not workspace_id or not session_id:
            return
        with self._active_lock:
            self._ensure_route_generation_maps_locked()
            session_key = (workspace_id, session_id)
            if request_id:
                route = self._provisional_viewer_routes.get(session_key)
                if route is None:
                    previous_client = self._session_clients.get(session_key)
                    previous_generation = self._session_client_generations.get(
                        session_key,
                        (
                            self._client_generation_token(previous_client)
                            if previous_client is not None
                            else 0
                        ),
                    )
                    if (
                        previous_client is not None
                        and previous_generation
                        != self._client_generation_token(previous_client)
                    ):
                        previous_client = None
                        previous_generation = 0
                    route = _ProvisionalViewerRoute(
                        session_key=session_key,
                        baseline_client=previous_client,
                        baseline_generation=previous_generation,
                        baseline_request_order=0,
                        requests=[],
                    )
                    self._provisional_viewer_routes[session_key] = route
                generation = self._client_generation_token(client)
                self._next_viewer_request_order += 1
                route.requests.append(
                    (
                        self._next_viewer_request_order,
                        request_id,
                        client,
                        generation,
                    )
                )
                self._provisional_request_sessions[request_id] = session_key
                self._apply_provisional_viewer_route_locked(route)
            else:
                self._session_clients[session_key] = client
                self._session_client_generations[session_key] = (
                    self._client_generation_token(client)
                )

    def _viewer_client(
        self,
        *,
        run_id: str = "",
        workspace_id: str = "",
        session_id: str = "",
        allow_unowned_fallback: bool = False,
    ) -> Any | None:
        with self._active_lock:
            self._ensure_route_generation_maps_locked()
            if run_id and run_id in self._run_clients:
                client = self._run_clients[run_id]
                route_generation = self._run_client_generations.get(
                    run_id,
                    self._client_generation_token(client),
                )
                if route_generation == self._client_generation_token(client):
                    return client
                self._active_clients.pop(run_id, None)
                self._run_clients.pop(run_id, None)
                self._run_client_generations.pop(run_id, None)
                self._run_generation_snapshots.pop(run_id, None)
                self._run_workspace_ids.pop(run_id, None)
                if not allow_unowned_fallback:
                    return None
            session_key = (workspace_id, session_id)
            if (
                workspace_id
                and session_id
                and session_key in self._session_clients
            ):
                client = self._session_clients[session_key]
                route_generation = self._session_client_generations.get(
                    session_key,
                    self._client_generation_token(client),
                )
                if route_generation == self._client_generation_token(client):
                    return client
                self._session_clients.pop(session_key, None)
                self._session_client_generations.pop(session_key, None)
                if not allow_unowned_fallback:
                    return None
            if workspace_id and workspace_id in self._workspace_clients:
                client = self._workspace_clients[workspace_id]
                route_generation = self._workspace_client_generations.get(
                    workspace_id,
                    self._client_generation_token(client),
                )
                if route_generation == self._client_generation_token(client):
                    return client
                self._workspace_clients.pop(workspace_id, None)
                self._workspace_client_generations.pop(workspace_id, None)
                if not allow_unowned_fallback:
                    return None
            if not allow_unowned_fallback:
                return None
            active_clients = tuple(
                {
                    id(client): client for client in self._active_clients.values()
                }.values()
            )
        if len(active_clients) == 1:
            return active_clients[0]
        return self._process_client

    def _clear_viewer_owners(self) -> None:
        with self._active_lock:
            self._ensure_route_generation_maps_locked()
            self._active_clients.clear()
            self._run_clients.clear()
            self._run_client_generations.clear()
            self._run_generation_snapshots.clear()
            self._run_workspace_ids.clear()
            self._workspace_clients.clear()
            self._workspace_client_generations.clear()
            self._session_clients.clear()
            self._session_client_generations.clear()
            self._provisional_viewer_routes.clear()
            self._provisional_request_sessions.clear()
            self._next_viewer_request_order = 0
            self._terminal_run_ids_seen.clear()

    def _assert_registry_replaceable_locked(self) -> None:
        self._ensure_route_generation_maps_locked()
        if self._active_clients:
            raise DataTypeCatalogError(
                "Cannot replace the registry during an active run"
            )
        if self._session_clients or self._provisional_viewer_routes:
            raise DataTypeCatalogError(
                "Cannot replace the registry while viewer routes remain active"
            )

    @contextmanager
    def registry_publication_guard(self):  # noqa: ANN201
        lock = getattr(self, "_registry_publication_lock", None)
        if lock is None:
            lock = self._registry_publication_lock = threading.RLock()
        with lock:
            yield

    @_registry_admitted
    def assert_registry_replaceable(self) -> None:
        with self._active_lock:
            self._assert_registry_replaceable_locked()
        for client in (
            self._process_client,
            self._external_python_client,
            self._trusted_client,
        ):
            client.assert_registry_replaceable()

    @_registry_admitted
    def replace_registry(self, registry: NodeRegistry) -> bool:
        if not isinstance(registry, NodeRegistry):
            raise TypeError("registry must be a NodeRegistry")
        with self._active_lock:
            self._assert_registry_replaceable_locked()
        retirement_results = tuple(
            client.replace_registry(registry)
            for client in (
                self._process_client,
                self._external_python_client,
                self._trusted_client,
            )
        )
        retired = any(retirement_results)
        self._published_registry = registry
        if retired:
            self._clear_viewer_owners()
        return retired

    def _emit_protocol_error(self, message: str, *, command: str = "start_run") -> None:
        self._dispatch_event(
            event_to_dict(
                ProtocolErrorEvent(
                    command=command,
                    error=message,
                ),
                catalog=None,
            )
        )

    @_registry_admitted
    def start_run(
        self,
        project_path: str,
        workspace_id: str,
        trigger: dict[str, Any] | None = None,
        *,
        execution_backend: Any = None,
        target_node_ids: tuple[str, ...] | list[str] | None = None,
        trigger_publications: dict[str, SettledPortResult] | None = None,
        trigger_captures: dict[str, SettledPortResult] | None = None,
        clicked_trigger_node_id: str = "",
        data_types: DataTypeCatalog | None = None,
        plugin_bundles: tuple[PluginBundleRef, ...] = (),
        plugin_fingerprint: str = EMPTY_PLUGIN_FINGERPRINT,
        registry_contract_fingerprint: str = EMPTY_REGISTRY_CONTRACT_FINGERPRINT,
        addon_runtime_config: tuple[tuple[str, bool], ...] = (),
    ) -> str:
        if not self._require_start_catalog(data_types):
            return ""
        trigger_payload = dict(trigger or {})
        command_target_node_ids = trigger_payload.pop(
            "target_node_ids", target_node_ids or ()
        )
        command_trigger_publications = trigger_payload.pop(
            "trigger_publications", trigger_publications or {}
        )
        command_trigger_captures = trigger_payload.pop(
            "trigger_captures", trigger_captures or {}
        )
        command_clicked_trigger_node_id = trigger_payload.pop(
            "clicked_trigger_node_id", clicked_trigger_node_id
        )
        raw_backend_policy = execution_backend
        explicit_backend = raw_backend_policy is not None
        if raw_backend_policy is None:
            if "execution_backend" in trigger_payload:
                raw_backend_policy = trigger_payload.pop("execution_backend", None)
                explicit_backend = True
        else:
            trigger_payload.pop("execution_backend", None)

        runtime_snapshot = trigger_payload.get("runtime_snapshot")
        workflow_python_path = workflow_python_path_from_snapshot(runtime_snapshot)
        if not explicit_backend:
            if workflow_python_path:
                raw_backend_policy = {
                    "requested_backend": EXTERNAL_SUBPROCESS_BACKEND,
                    "allow_external_subprocess": True,
                    "python_executable": workflow_python_path,
                    "reason": "workflow_python_path",
                }
        try:
            selection = self._orchestrator.select(raw_backend_policy)
        except (TypeError, ValueError) as exc:
            self._emit_protocol_error(str(exc))
            return ""

        if selection.backend_id == EXTERNAL_SUBPROCESS_BACKEND:
            python_executable = normalize_path_text(selection.python_executable)
            if not python_executable:
                if workflow_python_path:
                    python_executable = workflow_python_path
                else:
                    self._emit_protocol_error(
                        "External Python workflow execution requires python_executable "
                        "or Workflow Settings > Environment > Workflow Override. "
                        "Use Create / Repair Managed Runtime to create a managed "
                        "Python environment."
                    )
                    return ""
            python_environment = resolve_python_environment(python_executable)
            if not python_environment.valid:
                self._emit_protocol_error(python_environment.error)
                return ""
            selection = replace(
                selection,
                python_executable=python_environment.python_executable,
                reason=(
                    selection.reason
                    or ("workflow_python_path" if workflow_python_path else "")
                ),
            )

        if selection.backend_id == EXTERNAL_SUBPROCESS_BACKEND:
            client = self._external_python_client
        elif selection.backend_id == TRUSTED_IN_PROCESS_BACKEND:
            client = self._trusted_client
        else:
            client = self._process_client
        self._client_selections[id(client)] = selection
        previous_catalog_generation = self._client_generation_token(client)
        run_id = client.start_run(
            project_path,
            workspace_id,
            trigger=trigger_payload,
            execution_backend=selection,
            target_node_ids=command_target_node_ids,
            trigger_publications=command_trigger_publications,
            trigger_captures=command_trigger_captures,
            clicked_trigger_node_id=command_clicked_trigger_node_id,
            data_types=data_types,
            plugin_bundles=plugin_bundles,
            plugin_fingerprint=plugin_fingerprint,
            registry_contract_fingerprint=registry_contract_fingerprint,
            addon_runtime_config=addon_runtime_config,
        )
        current_catalog_generation = self._client_generation_token(client)
        run_generation_snapshot = (
            self._generation_snapshot_for_client(
                client,
                selection,
                registry_contract_fingerprint=registry_contract_fingerprint,
            )
            if run_id
            else None
        )
        with self._active_lock:
            self._ensure_route_generation_maps_locked()
            if previous_catalog_generation != current_catalog_generation:
                self._forget_client_generation_locked(client)
            if run_id:
                if run_id not in self._terminal_run_ids_seen:
                    self._active_clients[run_id] = client
                else:
                    self._terminal_run_ids_seen.discard(run_id)
                self._run_clients[run_id] = client
                self._run_client_generations[run_id] = current_catalog_generation
                if run_generation_snapshot is not None:
                    self._run_generation_snapshots[run_id] = (
                        run_generation_snapshot
                    )
                self._run_workspace_ids[run_id] = str(workspace_id).strip()
                if str(workspace_id).strip():
                    self._workspace_clients[str(workspace_id).strip()] = client
                    self._workspace_client_generations[
                        str(workspace_id).strip()
                    ] = current_catalog_generation
                self._trim_viewer_run_owners_locked()
        return run_id

    def _client_for_run(self, run_id: str) -> Any:
        with self._active_lock:
            self._ensure_route_generation_maps_locked()
            client = self._active_clients.get(run_id)
            if client is None:
                return None
            route_generation = self._run_client_generations.get(
                run_id,
                self._client_generation_token(client),
            )
            if route_generation == self._client_generation_token(client):
                return client
            self._active_clients.pop(run_id, None)
            self._run_clients.pop(run_id, None)
            self._run_client_generations.pop(run_id, None)
            self._run_generation_snapshots.pop(run_id, None)
            self._run_workspace_ids.pop(run_id, None)
        return None

    def lease_solution_resource(
        self,
        run_id: str,
        value: Any,
        *,
        owner_scope: str,
    ) -> tuple[Any, ExecutionResourceLease] | None:
        if not isinstance(value, RuntimeHandleRef):
            return None
        with self._active_lock:
            self._ensure_route_generation_maps_locked()
            client = self._run_clients.get(str(run_id).strip())
            snapshot = self._run_generation_snapshots.get(str(run_id).strip())
        if (
            client is not self._trusted_client
            or snapshot is None
            or value.worker_generation != snapshot.runtime_generation
        ):
            return None
        try:
            leased = client._worker_services.lease_handle(  # noqa: SLF001
                value,
                owner_scope=str(owner_scope).strip(),
            )
        except (LookupError, RuntimeError, TypeError, ValueError):
            return None
        return leased, ExecutionResourceLease(client=client, value=leased)

    @staticmethod
    def release_solution_resource(lease: Any) -> None:
        if not isinstance(lease, ExecutionResourceLease):
            return
        try:
            lease.client._worker_services.release_handle(lease.value)  # noqa: SLF001
        except (LookupError, RuntimeError, TypeError, ValueError):
            return

    def pause_run(self, run_id: str) -> None:
        client = self._client_for_run(run_id)
        if client is not None:
            client.pause_run(run_id)

    def resume_run(self, run_id: str) -> None:
        client = self._client_for_run(run_id)
        if client is not None:
            client.resume_run(run_id)

    def stop_run(self, run_id: str) -> None:
        client = self._client_for_run(run_id)
        if client is not None:
            client.stop_run(run_id)

    @_registry_admitted
    def open_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        run_id, workspace_id, session_id = self._viewer_route_ids(args, kwargs)
        client = self._viewer_client(
            run_id=run_id,
            workspace_id=workspace_id,
            session_id=session_id,
            allow_unowned_fallback=True,
        )
        if client is None:
            return ""
        request_id_factory = getattr(client, "_next_viewer_request_id", None)
        request_id = (
            str(request_id_factory())
            if callable(request_id_factory)
            else ""
        )
        self._remember_requested_session_owner(
            client=client,
            workspace_id=workspace_id,
            session_id=session_id,
            request_id=request_id,
        )
        if request_id:
            kwargs["_request_id"] = request_id
        result = client.open_viewer_session(*args, **kwargs)
        if request_id:
            with self._active_lock:
                self._refresh_provisional_request_generation_locked(
                    request_id=request_id,
                    client=client,
                    generation_token=self._client_generation_token(client),
                )
        return result

    def update_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        run_id, workspace_id, session_id = self._viewer_route_ids(args, kwargs)
        client = self._viewer_client(
            run_id=run_id,
            workspace_id=workspace_id,
            session_id=session_id,
        )
        if client is None:
            return ""
        return client.update_viewer_session(*args, **kwargs)

    def close_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        run_id, workspace_id, session_id = self._viewer_route_ids(args, kwargs)
        client = self._viewer_client(
            run_id=run_id,
            workspace_id=workspace_id,
            session_id=session_id,
        )
        if client is None:
            return ""
        return client.close_viewer_session(*args, **kwargs)

    def materialize_viewer_data(self, *args: Any, **kwargs: Any) -> str:
        run_id, workspace_id, session_id = self._viewer_route_ids(args, kwargs)
        client = self._viewer_client(
            run_id=run_id,
            workspace_id=workspace_id,
            session_id=session_id,
        )
        if client is None:
            return ""
        return client.materialize_viewer_data(*args, **kwargs)

    def query_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        run_id, workspace_id, session_id = self._viewer_route_ids(args, kwargs)
        client = self._viewer_client(
            run_id=run_id,
            workspace_id=workspace_id,
            session_id=session_id,
        )
        if client is None:
            return ""
        return client.query_viewer_session(*args, **kwargs)

    def shutdown(self) -> None:
        with self._active_lock:
            reservation_map = getattr(self, "_run_reservations", {})
            reservations = tuple(reservation_map.values())
            reservation_map.clear()
        for reservation, client in reservations:
            client._release_start_run(reservation.run_id)  # noqa: SLF001
        self._process_client.shutdown()
        self._trusted_client.shutdown()
        self._external_python_client.shutdown()
        self._clear_viewer_owners()


__all__ = [
    "ExecutionBackendClient",
    "ExecutionGenerationSnapshot",
    "ExecutionResourceLease",
    "ExecutionRunReservation",
    "ExternalPythonExecutionClient",
    "ProcessExecutionClient",
    "TrustedInProcessExecutionClient",
]
