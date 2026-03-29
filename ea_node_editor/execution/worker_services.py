from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from typing import TYPE_CHECKING

from ea_node_editor.execution.dpf_runtime import create_dpf_runtime_service
from ea_node_editor.execution.handle_registry import HandleRegistry
from ea_node_editor.execution.viewer_backend import ViewerBackendRegistry
from ea_node_editor.execution.viewer_backend_dpf import DpfExecutionViewerBackend
from ea_node_editor.nodes.types import RuntimeHandleRef, coerce_runtime_handle_ref

if TYPE_CHECKING:
    from ea_node_editor.execution.dpf_runtime_service import DpfRuntimeService
    from ea_node_editor.execution.viewer_session_service import ViewerSessionService


@dataclass(slots=True)
class WorkerServices:
    handle_registry: HandleRegistry = field(default_factory=HandleRegistry)
    _dpf_runtime_service: DpfRuntimeService | None = field(default=None, init=False, repr=False)
    _viewer_backend_registry: ViewerBackendRegistry | None = field(default=None, init=False, repr=False)
    _viewer_session_service: ViewerSessionService | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_dpf_runtime_service", None)
        object.__setattr__(self, "_viewer_backend_registry", None)
        object.__setattr__(self, "_viewer_session_service", None)

    @property
    def worker_generation(self) -> int:
        return self.handle_registry.worker_generation

    @property
    def dpf_runtime_service(self) -> DpfRuntimeService:
        if self._dpf_runtime_service is None:
            self._dpf_runtime_service = create_dpf_runtime_service(self)
        return self._dpf_runtime_service

    @property
    def viewer_backend_registry(self) -> ViewerBackendRegistry:
        if self._viewer_backend_registry is None:
            registry = ViewerBackendRegistry()
            registry.register(DpfExecutionViewerBackend(self))
            self._viewer_backend_registry = registry
        return self._viewer_backend_registry

    @property
    def viewer_session_service(self) -> ViewerSessionService:
        if self._viewer_session_service is None:
            from ea_node_editor.execution.viewer_session_service import ViewerSessionService

            self._viewer_session_service = ViewerSessionService(self)
        return self._viewer_session_service

    @staticmethod
    def run_owner_scope(run_id: str) -> str:
        return f"run:{str(run_id).strip()}"

    def register_handle(
        self,
        value: Any,
        *,
        kind: str,
        run_id: str = "",
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        resolved_owner_scope = owner_scope or self.run_owner_scope(run_id)
        return self.handle_registry.register(
            value,
            kind=kind,
            owner_scope=resolved_owner_scope,
            metadata=metadata,
        )

    def handle_ref(
        self,
        value: Any,
        *,
        kind: str = "",
        run_id: str = "",
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is not None:
            return self.handle_registry.acquire(runtime_ref)
        if not str(kind).strip():
            raise TypeError("kind is required when registering a new runtime handle")
        return self.register_handle(
            value,
            kind=kind,
            run_id=run_id,
            owner_scope=owner_scope,
            metadata=metadata,
        )

    def resolve_handle(self, value: Any, *, expected_kind: str = "") -> Any:
        return self.handle_registry.resolve(value, expected_kind=expected_kind)

    def release_handle(self, value: Any) -> bool:
        return self.handle_registry.release(value)

    def promote_handle(
        self,
        value: Any,
        *,
        owner_scope: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeHandleRef:
        return self.handle_registry.promote(value, owner_scope=owner_scope, metadata=metadata)

    def cleanup_run(self, run_id: str) -> int:
        owner_scope = self.run_owner_scope(run_id)
        released_count = self.handle_registry.release_owner_scope(owner_scope)
        if self._dpf_runtime_service is not None:
            self._dpf_runtime_service.cleanup_owner_scope(owner_scope)
        return released_count

    def reset(self) -> int:
        released_count = self.handle_registry.reset()
        if self._dpf_runtime_service is not None:
            self._dpf_runtime_service.reset()
        if self._viewer_session_service is not None:
            self._viewer_session_service.reset()
        return released_count


__all__ = [
    "WorkerServices",
]
