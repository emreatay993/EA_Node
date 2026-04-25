from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from ea_node_editor.runtime_contracts import (
    RuntimeArtifactRef,
    RuntimeHandleRef,
    coerce_runtime_artifact_ref,
    coerce_runtime_handle_ref,
)

class ExecutionHandleServices(Protocol):
    def register_handle(
        self,
        value: Any,
        *,
        kind: str,
        run_id: str = "",
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef: ...

    def resolve_handle(self, value: Any, *, expected_kind: str = "") -> Any: ...

    def release_handle(self, value: Any) -> bool: ...

    def handle_ref(
        self,
        value: Any,
        *,
        kind: str = "",
        run_id: str = "",
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef: ...


class RuntimeSnapshotPort(Protocol):
    metadata: Mapping[str, Any]


class RuntimeSnapshotContextPort(Protocol):
    artifact_store: Any

    def project_metadata(self) -> dict[str, Any]: ...


@dataclass(slots=True)
class ExecutionContext:
    run_id: str
    node_id: str
    workspace_id: str
    inputs: dict[str, Any]
    properties: dict[str, Any]
    emit_log: Callable[[str, str], None]
    trigger: dict[str, Any] = field(default_factory=dict)
    should_stop: Callable[[], bool] = field(default=lambda: False)
    register_cancel: Callable[[Callable[[], None]], None] = field(default=lambda _callback: None)
    project_path: str = ""
    runtime_snapshot: RuntimeSnapshotPort | None = None
    runtime_snapshot_context: RuntimeSnapshotContextPort | None = None
    path_resolver: Callable[[Any], Path | None] = field(default=lambda _value: None)
    worker_services: ExecutionHandleServices | None = None

    @property
    def artifact_store(self) -> Any | None:
        context = self.runtime_snapshot_context
        if context is None:
            return None
        return context.artifact_store

    def runtime_project_metadata(self) -> dict[str, Any]:
        context = self.runtime_snapshot_context
        if context is not None:
            return context.project_metadata()
        if self.runtime_snapshot is None:
            return {}
        return copy.deepcopy(self.runtime_snapshot.metadata)

    def log_info(self, message: str) -> None:
        self.emit_log("info", message)

    def log_warning(self, message: str) -> None:
        self.emit_log("warning", message)

    def log_error(self, message: str) -> None:
        self.emit_log("error", message)

    def runtime_artifact_ref(self, value: Any) -> RuntimeArtifactRef | None:
        return coerce_runtime_artifact_ref(value)

    def runtime_handle_ref(self, value: Any) -> RuntimeHandleRef | None:
        return coerce_runtime_handle_ref(value)

    def _require_worker_services(self) -> ExecutionHandleServices:
        if self.worker_services is None:
            raise RuntimeError("ExecutionContext does not have worker services.")
        return self.worker_services

    def register_handle(
        self,
        value: Any,
        *,
        kind: str,
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        return self._require_worker_services().register_handle(
            value,
            kind=kind,
            run_id=self.run_id,
            owner_scope=owner_scope,
            metadata=metadata,
        )

    def resolve_handle(self, value: Any, *, expected_kind: str = "") -> Any:
        runtime_ref = self.runtime_handle_ref(value)
        if runtime_ref is None:
            raise TypeError("ExecutionContext.resolve_handle requires a RuntimeHandleRef payload.")
        return self._require_worker_services().resolve_handle(runtime_ref, expected_kind=expected_kind)

    def release_handle(self, value: Any) -> bool:
        runtime_ref = self.runtime_handle_ref(value)
        if runtime_ref is None:
            raise TypeError("ExecutionContext.release_handle requires a RuntimeHandleRef payload.")
        return self._require_worker_services().release_handle(runtime_ref)

    def handle_ref(
        self,
        value: Any,
        *,
        kind: str = "",
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        return self._require_worker_services().handle_ref(
            value,
            kind=kind,
            run_id=self.run_id,
            owner_scope=owner_scope,
            metadata=metadata,
        )

    def resolve_path_value(self, value: Any) -> Path | None:
        runtime_ref = self.runtime_artifact_ref(value)
        candidate = runtime_ref.ref if runtime_ref is not None else value
        return self.path_resolver(candidate)

    def resolve_input_path(self, input_key: str, *, property_key: str = "") -> Path | None:
        candidates = [self.inputs.get(input_key)]
        if property_key:
            candidates.append(self.properties.get(property_key))
        for candidate in candidates:
            path = self.resolve_path_value(candidate)
            if path is not None:
                return path
        return None


@dataclass(slots=True)
class NodeResult:
    outputs: dict[str, Any] = field(default_factory=dict)
    completed: bool = True
    warnings: tuple[str, ...] = ()


__all__ = [
    "ExecutionContext",
    "ExecutionHandleServices",
    "NodeResult",
]
