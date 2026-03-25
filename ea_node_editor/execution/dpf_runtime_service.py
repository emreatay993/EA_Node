from __future__ import annotations

import hashlib
import importlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.nodes.types import RuntimeHandleRef, coerce_runtime_handle_ref

if TYPE_CHECKING:
    from ea_node_editor.execution.worker_services import WorkerServices

DPF_RESULT_FILE_HANDLE_KIND = "dpf.result_file"
DPF_MODEL_HANDLE_KIND = "dpf.model"
DPF_MESH_SCOPING_HANDLE_KIND = "dpf.mesh_scoping"
DPF_TIME_SCOPING_HANDLE_KIND = "dpf.time_scoping"

_SUPPORTED_RESULT_EXTENSIONS = frozenset({".rst", ".rth"})
_DEFAULT_TIME_SCOPING_LOCATION = "TimeFreq"
_MESH_LOCATION_ALIASES = {
    "nodal": "Nodal",
    "node": "Nodal",
    "nodes": "Nodal",
    "elemental": "Elemental",
    "element": "Elemental",
    "elements": "Elemental",
}


class DpfRuntimeUnavailableError(RuntimeError):
    """Raised when optional ansys.dpf.core dependencies are not available."""


class UnsupportedDpfResultFileError(ValueError):
    """Raised when a requested result file is not a supported Mechanical result."""


@dataclass(slots=True, frozen=True)
class DpfResultFile:
    path: Path
    extension: str
    cache_key: str


class DpfRuntimeService:
    def __init__(self, worker_services: WorkerServices) -> None:
        self._worker_services = worker_services
        self._result_file_cache: dict[str, RuntimeHandleRef] = {}
        self._model_cache: dict[str, RuntimeHandleRef] = {}

    def load_result_file(self, value: Any) -> RuntimeHandleRef:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is not None:
            if runtime_ref.kind != DPF_RESULT_FILE_HANDLE_KIND:
                raise TypeError(
                    "DpfRuntimeService.load_result_file requires a path-like value or "
                    "dpf.result_file handle ref."
                )
            self._worker_services.resolve_handle(runtime_ref, expected_kind=DPF_RESULT_FILE_HANDLE_KIND)
            return runtime_ref

        result_path = self._coerce_result_path(value)
        cache_key = self._cache_key(result_path)
        cached_ref = self._resolve_cached_ref(
            self._result_file_cache,
            cache_key,
            expected_kind=DPF_RESULT_FILE_HANDLE_KIND,
        )
        if cached_ref is not None:
            return cached_ref

        result_file = DpfResultFile(
            path=result_path,
            extension=result_path.suffix.lower(),
            cache_key=cache_key,
        )
        handle_ref = self._worker_services.register_handle(
            result_file,
            kind=DPF_RESULT_FILE_HANDLE_KIND,
            owner_scope=self._cache_owner_scope("result_file", cache_key),
            metadata={
                "path": str(result_path),
                "extension": result_file.extension,
                "cache_key": cache_key,
            },
        )
        self._result_file_cache[cache_key] = handle_ref
        return handle_ref

    def load_model(self, value: Any) -> RuntimeHandleRef:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is not None:
            if runtime_ref.kind == DPF_MODEL_HANDLE_KIND:
                self._worker_services.resolve_handle(runtime_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
                return runtime_ref
            if runtime_ref.kind != DPF_RESULT_FILE_HANDLE_KIND:
                raise TypeError(
                    "DpfRuntimeService.load_model requires a path-like value, dpf.result_file "
                    "handle ref, or dpf.model handle ref."
                )

        result_file_ref = self.load_result_file(value)
        result_file = self._worker_services.resolve_handle(
            result_file_ref,
            expected_kind=DPF_RESULT_FILE_HANDLE_KIND,
        )
        if not isinstance(result_file, DpfResultFile):
            raise TypeError("Resolved dpf.result_file handle does not carry a DpfResultFile record.")

        cached_ref = self._resolve_cached_ref(
            self._model_cache,
            result_file.cache_key,
            expected_kind=DPF_MODEL_HANDLE_KIND,
        )
        if cached_ref is not None:
            return cached_ref

        dpf = self._dpf_module()
        model = dpf.Model(str(result_file.path))
        handle_ref = self._worker_services.register_handle(
            model,
            kind=DPF_MODEL_HANDLE_KIND,
            owner_scope=self._cache_owner_scope("model", result_file.cache_key),
            metadata={
                "path": str(result_file.path),
                "extension": result_file.extension,
                "cache_key": result_file.cache_key,
                "result_file_handle_id": result_file_ref.handle_id,
            },
        )
        self._model_cache[result_file.cache_key] = handle_ref
        return handle_ref

    def create_mesh_scoping(
        self,
        ids: Iterable[Any],
        *,
        location: str,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        dpf = self._dpf_module()
        normalized_ids = self._normalize_ids("ids", ids)
        normalized_location = self._normalize_mesh_location(location)
        scoping = dpf.Scoping(ids=list(normalized_ids), location=normalized_location)
        return self._worker_services.register_handle(
            scoping,
            kind=DPF_MESH_SCOPING_HANDLE_KIND,
            owner_scope=self._resolve_scoping_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata={
                "ids": list(normalized_ids),
                "location": normalized_location,
            },
        )

    def create_time_scoping(
        self,
        set_ids: Iterable[Any],
        *,
        model: Any | None = None,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        dpf = self._dpf_module()
        normalized_ids = self._normalize_ids("set_ids", set_ids)
        location = self._time_scoping_location(model)
        scoping = dpf.Scoping(ids=list(normalized_ids), location=location)
        return self._worker_services.register_handle(
            scoping,
            kind=DPF_TIME_SCOPING_HANDLE_KIND,
            owner_scope=self._resolve_scoping_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata={
                "ids": list(normalized_ids),
                "location": location,
            },
        )

    def cleanup_owner_scope(self, owner_scope: str) -> None:
        self._drop_cached_owner_scope(self._result_file_cache, owner_scope)
        self._drop_cached_owner_scope(self._model_cache, owner_scope)

    def reset(self) -> None:
        self._result_file_cache.clear()
        self._model_cache.clear()

    @staticmethod
    def _cache_key(path: Path) -> str:
        return str(path).casefold()

    @staticmethod
    def _cache_owner_scope(prefix: str, cache_key: str) -> str:
        digest = hashlib.sha1(cache_key.encode("utf-8")).hexdigest()
        return f"cache:dpf:{prefix}:{digest}"

    def _resolve_cached_ref(
        self,
        cache: dict[str, RuntimeHandleRef],
        cache_key: str,
        *,
        expected_kind: str,
    ) -> RuntimeHandleRef | None:
        cached_ref = cache.get(cache_key)
        if cached_ref is None:
            return None
        try:
            self._worker_services.resolve_handle(cached_ref, expected_kind=expected_kind)
        except StaleHandleError:
            cache.pop(cache_key, None)
            return None
        return cached_ref

    @staticmethod
    def _drop_cached_owner_scope(cache: dict[str, RuntimeHandleRef], owner_scope: str) -> None:
        stale_keys = [
            cache_key
            for cache_key, handle_ref in cache.items()
            if handle_ref.owner_scope == owner_scope
        ]
        for cache_key in stale_keys:
            cache.pop(cache_key, None)

    def _coerce_result_path(self, value: Any) -> Path:
        if isinstance(value, DpfResultFile):
            return value.path

        path_value = value
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is not None:
            if runtime_ref.kind == DPF_RESULT_FILE_HANDLE_KIND:
                resolved = self._worker_services.resolve_handle(
                    runtime_ref,
                    expected_kind=DPF_RESULT_FILE_HANDLE_KIND,
                )
                if not isinstance(resolved, DpfResultFile):
                    raise TypeError(
                        "Resolved dpf.result_file handle does not carry a DpfResultFile record."
                    )
                return resolved.path
            if runtime_ref.kind == DPF_MODEL_HANDLE_KIND:
                path_value = runtime_ref.metadata.get("path", "")
            else:
                raise TypeError(
                    "DpfRuntimeService paths may only be resolved from dpf.result_file or "
                    "dpf.model handles."
                )

        if not isinstance(path_value, (str, Path)):
            raise TypeError("Result file paths must be path-like strings or Path instances.")

        resolved_path = Path(path_value).expanduser().resolve(strict=True)
        extension = resolved_path.suffix.lower()
        if extension not in _SUPPORTED_RESULT_EXTENSIONS:
            raise UnsupportedDpfResultFileError(
                "DPF runtime service only supports Mechanical .rst and .rth files."
            )
        return resolved_path

    def _time_scoping_location(self, model: Any | None) -> str:
        if model is None:
            return _DEFAULT_TIME_SCOPING_LOCATION
        runtime_ref = self.load_model(model)
        resolved_model = self._worker_services.resolve_handle(
            runtime_ref,
            expected_kind=DPF_MODEL_HANDLE_KIND,
        )
        return str(resolved_model.metadata.time_freq_support.time_frequencies.scoping.location)

    @staticmethod
    def _normalize_ids(field_name: str, values: Iterable[Any]) -> tuple[int, ...]:
        normalized_ids: list[int] = []
        for raw_value in values:
            if isinstance(raw_value, bool):
                raise TypeError(f"{field_name} values must be integers")
            try:
                normalized_ids.append(int(raw_value))
            except (TypeError, ValueError) as exc:
                raise TypeError(f"{field_name} values must be integers") from exc
        if not normalized_ids:
            raise ValueError(f"{field_name} must contain at least one id")
        return tuple(normalized_ids)

    @staticmethod
    def _normalize_mesh_location(value: object) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("location must be a non-empty string")
        alias = _MESH_LOCATION_ALIASES.get(normalized.casefold())
        if alias is not None:
            return alias
        if normalized in {"Nodal", "Elemental"}:
            return normalized
        raise ValueError("location must resolve to either Nodal or Elemental")

    def _resolve_scoping_owner_scope(self, *, run_id: str, owner_scope: str) -> str:
        if str(owner_scope).strip():
            return str(owner_scope).strip()
        if str(run_id).strip():
            return self._worker_services.run_owner_scope(run_id)
        raise ValueError("run_id or owner_scope is required for scoping handles")

    @staticmethod
    def _dpf_module() -> Any:
        try:
            return importlib.import_module("ansys.dpf.core")
        except ModuleNotFoundError as exc:
            raise DpfRuntimeUnavailableError(
                "ansys.dpf.core is not available; DPF runtime features remain optional until used."
            ) from exc


__all__ = [
    "DPF_MESH_SCOPING_HANDLE_KIND",
    "DPF_MODEL_HANDLE_KIND",
    "DPF_RESULT_FILE_HANDLE_KIND",
    "DPF_TIME_SCOPING_HANDLE_KIND",
    "DpfResultFile",
    "DpfRuntimeService",
    "DpfRuntimeUnavailableError",
    "UnsupportedDpfResultFileError",
]
