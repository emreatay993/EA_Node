from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from ea_node_editor.execution.dpf_runtime.contracts import (
    DEFAULT_EXPORT_SUBDIRECTORY,
    DEFAULT_TIME_SCOPING_LOCATION,
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
    FIELD_LOCATION_ALIASES,
    INVALID_ARTIFACT_TOKEN_CHARS,
    MESH_LOCATION_ALIASES,
    SUPPORTED_EXPORT_FORMATS,
    SUPPORTED_OUTPUT_PROFILES,
    SUPPORTED_RESULT_EXTENSIONS,
    DpfResultFile,
    UnsupportedDpfResultFileError,
)
from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.nodes.types import RuntimeHandleRef, coerce_runtime_handle_ref

if TYPE_CHECKING:
    from ea_node_editor.execution.worker_services import WorkerServices


class DpfRuntimeBase:
    _worker_services: WorkerServices
    _result_file_cache: dict[str, RuntimeHandleRef]
    _model_cache: dict[str, RuntimeHandleRef]

    def _dpf_module(self) -> Any:
        raise NotImplementedError

    def _pyvista_module(self) -> Any:
        raise NotImplementedError

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
        if extension not in SUPPORTED_RESULT_EXTENSIONS:
            raise UnsupportedDpfResultFileError(
                "DPF runtime service only supports Mechanical .rst and .rth files."
            )
        return resolved_path

    def _time_scoping_location(self, model: Any | None) -> str:
        if model is None:
            return DEFAULT_TIME_SCOPING_LOCATION
        runtime_ref = self.load_model(model)  # type: ignore[attr-defined]
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
        alias = MESH_LOCATION_ALIASES.get(normalized.casefold())
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

    def _resolve_handle_owner_scope(self, *, run_id: str, owner_scope: str) -> str:
        return self._resolve_scoping_owner_scope(run_id=run_id, owner_scope=owner_scope)

    def _resolve_model_handle_and_object(self, value: Any) -> tuple[RuntimeHandleRef, Any]:
        model_ref = self.load_model(value)  # type: ignore[attr-defined]
        model = self._worker_services.resolve_handle(model_ref, expected_kind=DPF_MODEL_HANDLE_KIND)
        return model_ref, model

    def _resolve_fields_container_handle_and_object(self, value: Any) -> tuple[RuntimeHandleRef, Any]:
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is None or runtime_ref.kind != DPF_FIELDS_CONTAINER_HANDLE_KIND:
            raise TypeError(
                "DpfRuntimeService field operations require a dpf.fields_container handle ref."
            )
        fields_container = self._worker_services.resolve_handle(
            runtime_ref,
            expected_kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
        )
        return runtime_ref, fields_container

    def _resolve_mesh_object(self, value: Any | None, *, model: Any) -> Any:
        if value is None:
            return model.metadata.meshed_region
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is None or runtime_ref.kind != DPF_MESH_HANDLE_KIND:
            raise TypeError("mesh must be a dpf.mesh handle ref when provided.")
        return self._worker_services.resolve_handle(runtime_ref, expected_kind=DPF_MESH_HANDLE_KIND)

    def _resolve_time_scoping_input(
        self,
        value: Any | None,
        *,
        set_ids: Iterable[Any] | None,
        model: Any,
    ) -> Any | None:
        if value is None and set_ids is None:
            return None
        if value is not None:
            runtime_ref = coerce_runtime_handle_ref(value)
            if runtime_ref is not None:
                return self._worker_services.resolve_handle(
                    runtime_ref,
                    expected_kind=DPF_TIME_SCOPING_HANDLE_KIND,
                )
            if hasattr(value, "ids") and hasattr(value, "location"):
                return value
            raise TypeError("time_scoping must be a dpf.time_scoping handle ref or DPF scoping object.")

        dpf = self._dpf_module()
        normalized_ids = self._normalize_ids("set_ids", set_ids if set_ids is not None else ())
        location = self._time_scoping_location(model)
        return dpf.Scoping(ids=list(normalized_ids), location=location)

    def _resolve_mesh_scoping_input(self, value: Any | None) -> Any | None:
        if value is None:
            return None
        runtime_ref = coerce_runtime_handle_ref(value)
        if runtime_ref is not None:
            return self._worker_services.resolve_handle(
                runtime_ref,
                expected_kind=DPF_MESH_SCOPING_HANDLE_KIND,
            )
        if hasattr(value, "ids") and hasattr(value, "location"):
            return value
        raise TypeError("mesh_scoping must be a dpf.mesh_scoping handle ref or DPF scoping object.")

    def _convert_fields_container_location(self, fields_container: Any, *, location: str, mesh: Any) -> Any:
        dpf = self._dpf_module()
        if location == "Nodal":
            operator = dpf.operators.averaging.to_nodal_fc()
            operator.inputs.fields_container(fields_container)
            operator.inputs.mesh(mesh)
            return operator.outputs.fields_container()
        if location == "Elemental":
            operator = dpf.operators.averaging.to_elemental_fc()
            operator.inputs.fields_container(fields_container)
            operator.inputs.mesh(mesh)
            return operator.outputs.fields_container()
        if location == "ElementalNodal":
            if self._fields_container_location(fields_container) != "ElementalNodal":
                raise ValueError("Conversion to ElementalNodal is not supported for this fields container.")
            return fields_container
        raise ValueError(f"Unsupported field location conversion: {location}")

    def _build_fields_container_metadata(
        self,
        fields_container: Any,
        *,
        result_name: str = "",
        model_ref: RuntimeHandleRef | None = None,
        mesh_scoping: Any = None,
        time_scoping: Any = None,
    ) -> dict[str, Any]:
        metadata = self._build_field_metadata(fields_container[0]) if len(fields_container) else {
            "location": "",
            "component_count": 0,
            "entity_count": 0,
            "unit": "",
        }
        metadata["field_count"] = len(fields_container)
        metadata["set_ids"] = list(self._fields_container_set_ids(fields_container))
        if result_name:
            metadata["result_name"] = result_name
        if model_ref is not None:
            metadata["model_handle_id"] = model_ref.handle_id
        mesh_scoping_handle_id = self._handle_id_or_empty(mesh_scoping)
        if mesh_scoping_handle_id:
            metadata["mesh_scoping_handle_id"] = mesh_scoping_handle_id
        time_scoping_handle_id = self._handle_id_or_empty(time_scoping)
        if time_scoping_handle_id:
            metadata["time_scoping_handle_id"] = time_scoping_handle_id
        return metadata

    @staticmethod
    def _build_field_metadata(field_value: Any) -> dict[str, Any]:
        return {
            "location": str(getattr(field_value, "location", "")),
            "component_count": int(getattr(field_value, "component_count", 0)),
            "entity_count": int(getattr(getattr(field_value, "scoping", None), "size", 0)),
            "unit": str(getattr(field_value, "unit", "") or ""),
        }

    @staticmethod
    def _build_mesh_metadata(mesh: Any) -> dict[str, Any]:
        return {
            "node_count": int(getattr(getattr(mesh, "nodes", None), "n_nodes", 0)),
            "element_count": int(getattr(getattr(mesh, "elements", None), "n_elements", 0)),
            "unit": str(getattr(mesh, "unit", "") or ""),
        }

    @staticmethod
    def _fields_container_location(fields_container: Any) -> str:
        if len(fields_container) == 0:
            return ""
        return str(getattr(fields_container[0], "location", ""))

    @staticmethod
    def _fields_container_set_ids(fields_container: Any) -> tuple[int, ...]:
        labels = tuple(getattr(fields_container, "labels", ()) or ())
        if "time" not in labels:
            return ()
        set_ids: list[int] = []
        for index in range(len(fields_container)):
            try:
                label_space = fields_container.get_label_space(index)
            except Exception:
                continue
            if "time" not in label_space:
                continue
            set_ids.append(int(label_space["time"]))
        return tuple(set_ids)

    @staticmethod
    def _normalize_result_name(value: object) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("result_name must be a non-empty string")
        return normalized

    @staticmethod
    def _normalize_field_location(value: object, *, allow_empty: bool = False) -> str:
        normalized = str(value).strip()
        if not normalized:
            if allow_empty:
                return ""
            raise ValueError("location must be a non-empty string")
        alias = FIELD_LOCATION_ALIASES.get(normalized.casefold())
        if alias is not None:
            return alias
        if normalized in {"Nodal", "Elemental", "ElementalNodal"}:
            return normalized
        raise ValueError("location must resolve to Nodal, Elemental, or ElementalNodal")

    @staticmethod
    def _normalize_output_profile(value: object) -> str:
        normalized = str(value).strip().casefold()
        if normalized not in SUPPORTED_OUTPUT_PROFILES:
            raise ValueError("output_profile must be one of memory, stored, or both")
        return normalized

    @staticmethod
    def _normalize_export_formats(value: Iterable[str] | str) -> tuple[str, ...]:
        if isinstance(value, str):
            raw_values: Iterable[str] = (value,)
        else:
            raw_values = value
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_value in raw_values:
            token = str(raw_value).strip().casefold()
            if not token:
                continue
            if token not in SUPPORTED_EXPORT_FORMATS:
                raise ValueError(f"Unsupported export format: {raw_value!r}")
            if token in seen:
                continue
            normalized.append(token)
            seen.add(token)
        return tuple(normalized)

    @staticmethod
    def _normalize_artifact_key(value: object) -> str:
        normalized = INVALID_ARTIFACT_TOKEN_CHARS.sub("_", str(value).strip()).strip("._-")
        if not normalized:
            raise ValueError("artifact_key must contain at least one valid token character")
        return normalized

    @staticmethod
    def _artifact_id(artifact_key: str, export_format: str) -> str:
        return f"dpf.{artifact_key}.{export_format}"

    @staticmethod
    def _artifact_slot(artifact_key: str, export_format: str) -> str:
        return f"dpf.materialization.{artifact_key}.{export_format}"

    @staticmethod
    def _artifact_relative_path(artifact_key: str, export_format: str) -> str:
        base = DEFAULT_EXPORT_SUBDIRECTORY / artifact_key
        if export_format == "csv":
            return (base / "field.csv").as_posix()
        if export_format == "png":
            return (base / "preview.png").as_posix()
        return (base / export_format).as_posix()

    @staticmethod
    def _dataset_kind(dataset: Any) -> str:
        if hasattr(dataset, "n_blocks"):
            return "multi_block"
        return "unstructured_grid"

    @staticmethod
    def _dataset_array_names(dataset: Any) -> list[str]:
        if hasattr(dataset, "array_names"):
            return [str(name) for name in dataset.array_names]
        if hasattr(dataset, "n_blocks") and getattr(dataset, "n_blocks", 0):
            first_block = dataset[0]
            return [str(name) for name in getattr(first_block, "array_names", ())]
        return []

    @staticmethod
    def _preview_dataset(dataset: Any) -> Any:
        if hasattr(dataset, "n_blocks") and getattr(dataset, "n_blocks", 0):
            return dataset[0]
        return dataset

    @staticmethod
    def _preferred_array_name(dataset: Any) -> str | None:
        array_names = [str(name) for name in getattr(dataset, "array_names", ())]
        for name in array_names:
            if name.casefold() in {"node_id", "element_id"}:
                continue
            return name
        return array_names[0] if array_names else None

    @staticmethod
    def _handle_id_or_empty(value: Any) -> str:
        runtime_ref = coerce_runtime_handle_ref(value)
        return runtime_ref.handle_id if runtime_ref is not None else ""


__all__ = [
    "DpfRuntimeBase",
]
