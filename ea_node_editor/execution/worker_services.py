from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any
from typing import TYPE_CHECKING

from ea_node_editor.addons.catalog import create_live_execution_viewer_backends
from ea_node_editor.execution.dpf_runtime import create_dpf_runtime_service
from ea_node_editor.execution.handle_registry import HandleRegistry
from ea_node_editor.execution.viewer_backend import ViewerBackendRegistry
from ea_node_editor.runtime_contracts.value_refs import (
    RuntimeHandleRef,
    coerce_runtime_handle_ref,
)
from ea_node_editor.runtime_contracts import DataTypeCatalog

if TYPE_CHECKING:
    from ea_node_editor.execution.dpf_runtime_service import DpfRuntimeService
    from ea_node_editor.execution.prepared_scene_runtime import PreparedSceneRuntime
    from ea_node_editor.execution.viewer_session_service import ViewerSessionService


@dataclass(slots=True)
class WorkerServices:
    handle_registry: HandleRegistry = field(default_factory=HandleRegistry)
    _dpf_runtime_service: DpfRuntimeService | None = field(default=None, init=False, repr=False)
    _prepared_scene_runtime: PreparedSceneRuntime | None = field(default=None, init=False, repr=False)
    _viewer_backend_registry: ViewerBackendRegistry | None = field(default=None, init=False, repr=False)
    _viewer_session_service: ViewerSessionService | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_dpf_runtime_service", None)
        object.__setattr__(self, "_prepared_scene_runtime", None)
        object.__setattr__(self, "_viewer_backend_registry", None)
        object.__setattr__(self, "_viewer_session_service", None)

    @property
    def worker_generation(self) -> int:
        return self.handle_registry.worker_generation

    @property
    def data_types(self) -> DataTypeCatalog:
        return self.handle_registry.data_types

    @property
    def dpf_runtime_service(self) -> DpfRuntimeService:
        if self._dpf_runtime_service is None:
            self._dpf_runtime_service = create_dpf_runtime_service(self)
        return self._dpf_runtime_service

    @property
    def prepared_scene_runtime(self) -> PreparedSceneRuntime:
        if self._prepared_scene_runtime is None:
            from ea_node_editor.execution.prepared_scene_runtime import PreparedSceneRuntime

            self._prepared_scene_runtime = PreparedSceneRuntime(self)
        return self._prepared_scene_runtime

    @property
    def viewer_backend_registry(self) -> ViewerBackendRegistry:
        if self._viewer_backend_registry is None:
            self._viewer_backend_registry = self._build_viewer_backend_registry()
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

    def bind_data_types(self, data_types: DataTypeCatalog) -> None:
        self.handle_registry.bind_data_types(data_types)

    def register_handle(
        self,
        value: Any,
        *,
        data_type_id: str,
        kind: str,
        run_id: str = "",
        owner_scope: str = "",
        metadata: Mapping[str, Any] | None = None,
        dispose: Callable[[], None] | None = None,
    ) -> RuntimeHandleRef:
        resolved_owner_scope = owner_scope or self.run_owner_scope(run_id)
        return self.handle_registry.register(
            value,
            data_type_id=data_type_id,
            kind=kind,
            owner_scope=resolved_owner_scope,
            metadata=metadata,
            dispose=dispose,
        )

    def lease_handle(
        self,
        value: Any,
        *,
        owner_scope: str,
    ) -> RuntimeHandleRef:
        runtime_ref = coerce_runtime_handle_ref(
            value,
            catalog=self.data_types,
        )
        if runtime_ref is None:
            raise TypeError("lease_handle requires a RuntimeHandleRef payload")
        return self.handle_registry.lease(
            runtime_ref,
            owner_scope=owner_scope,
        )

    def resolve_handle(
        self,
        value: Any,
        *,
        expected_data_type: str | None = None,
        expected_kind: str = "",
    ) -> Any:
        return self.handle_registry.resolve(
            value,
            expected_data_type=expected_data_type,
            expected_kind=expected_kind,
        )

    def release_handle(self, value: Any) -> bool:
        return self.handle_registry.release(value)

    def cleanup_run(
        self,
        run_id: str,
        *,
        warn: Callable[[str], None] | None = None,
    ) -> int:
        owner_scope = self.run_owner_scope(run_id)
        released_count = self.handle_registry.release_owner_scope(
            owner_scope,
            warn=warn,
        )
        if self._dpf_runtime_service is not None:
            self._dpf_runtime_service.cleanup_owner_scope(owner_scope)
        return released_count

    def reset(
        self,
        *,
        warn: Callable[[str], None] | None = None,
    ) -> int:
        prepared_scene_guard = (
            self._prepared_scene_runtime.lifecycle_guard()
            if self._prepared_scene_runtime is not None
            else nullcontext()
        )
        with prepared_scene_guard:
            released_count = self.handle_registry.active_handle_count
            if self._viewer_session_service is not None:
                self._viewer_session_service.reset(warn=warn)
            if self._prepared_scene_runtime is not None:
                self._prepared_scene_runtime.reset(warn=warn)
            if self._dpf_runtime_service is not None:
                self._dpf_runtime_service.reset(warn=warn)
            self.handle_registry.reset(warn=warn)
            return released_count

    def rebuild_addon_runtime(self, *, preferences_document: Any = None) -> int:
        released_count = self.reset()
        self._viewer_backend_registry = self._build_viewer_backend_registry(
            preferences_document=preferences_document
        )
        return released_count

    def _build_viewer_backend_registry(
        self,
        *,
        preferences_document: Any = None,
    ) -> ViewerBackendRegistry:
        from ea_node_editor.execution.viewer_backend_engineering import EngineeringViewerBackend

        registry = ViewerBackendRegistry()
        registry.register(EngineeringViewerBackend(self))
        for backend in create_live_execution_viewer_backends(
            self,
            preferences_document=preferences_document,
        ):
            registry.register(backend)
        return registry


__all__ = [
    "WorkerServices",
]
