from __future__ import annotations

import hashlib
import importlib
import re
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from ea_node_editor.execution.handle_registry import StaleHandleError
from ea_node_editor.nodes.types import RuntimeArtifactRef, RuntimeHandleRef, coerce_runtime_handle_ref
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore

if TYPE_CHECKING:
    from ea_node_editor.execution.worker_services import WorkerServices

DPF_RESULT_FILE_HANDLE_KIND = "dpf.result_file"
DPF_MODEL_HANDLE_KIND = "dpf.model"
DPF_MESH_SCOPING_HANDLE_KIND = "dpf.mesh_scoping"
DPF_TIME_SCOPING_HANDLE_KIND = "dpf.time_scoping"
DPF_FIELDS_CONTAINER_HANDLE_KIND = "dpf.fields_container"
DPF_FIELD_HANDLE_KIND = "dpf.field"
DPF_MESH_HANDLE_KIND = "dpf.mesh"
DPF_VIEWER_DATASET_HANDLE_KIND = "dpf.viewer_dataset"

_SUPPORTED_RESULT_EXTENSIONS = frozenset({".rst", ".rth"})
_DEFAULT_TIME_SCOPING_LOCATION = "TimeFreq"
_DEFAULT_EXPORT_SUBDIRECTORY = PurePosixPath("artifacts") / "dpf"
_DEFAULT_VTU_BASENAME = "dataset"
_DEFAULT_VTM_FILENAME = "dataset.vtm"
_MESH_LOCATION_ALIASES = {
    "nodal": "Nodal",
    "node": "Nodal",
    "nodes": "Nodal",
    "elemental": "Elemental",
    "element": "Elemental",
    "elements": "Elemental",
}
_FIELD_LOCATION_ALIASES = {
    **_MESH_LOCATION_ALIASES,
    "elemental_nodal": "ElementalNodal",
    "elementalnodal": "ElementalNodal",
}
_SUPPORTED_OUTPUT_PROFILES = frozenset({"memory", "stored", "both"})
_SUPPORTED_EXPORT_FORMATS = frozenset({"csv", "png", "vtu", "vtm"})
_INVALID_ARTIFACT_TOKEN_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


class DpfRuntimeUnavailableError(RuntimeError):
    """Raised when optional ansys.dpf.core dependencies are not available."""


class UnsupportedDpfResultFileError(ValueError):
    """Raised when a requested result file is not a supported Mechanical result."""


@dataclass(slots=True, frozen=True)
class DpfResultFile:
    path: Path
    extension: str
    cache_key: str


@dataclass(slots=True, frozen=True)
class DpfFieldRange:
    minimum: RuntimeHandleRef
    maximum: RuntimeHandleRef


@dataclass(slots=True, frozen=True)
class DpfMaterializationResult:
    output_profile: str
    dataset_ref: RuntimeHandleRef | None = None
    artifacts: dict[str, RuntimeArtifactRef] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)


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

    def extract_result_fields(
        self,
        *,
        model: Any,
        result_name: str,
        set_ids: Iterable[Any] | None = None,
        time_scoping: Any | None = None,
        mesh_scoping: Any | None = None,
        location: str = "",
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        dpf = self._dpf_module()
        normalized_result_name = self._normalize_result_name(result_name)
        resolved_owner_scope = self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope)
        model_ref, resolved_model = self._resolve_model_handle_and_object(model)
        operator_factory = getattr(dpf.operators.result, normalized_result_name, None)
        if operator_factory is None:
            raise ValueError(f"Unsupported DPF result operator: {normalized_result_name}")

        operator = operator_factory()
        operator.inputs.data_sources(resolved_model.metadata.data_sources)

        resolved_time_scoping = self._resolve_time_scoping_input(
            time_scoping,
            set_ids=set_ids,
            model=model_ref,
        )
        if resolved_time_scoping is not None and hasattr(operator.inputs, "time_scoping"):
            operator.inputs.time_scoping(resolved_time_scoping)

        resolved_mesh_scoping = self._resolve_mesh_scoping_input(mesh_scoping)
        if resolved_mesh_scoping is not None and hasattr(operator.inputs, "mesh_scoping"):
            operator.inputs.mesh_scoping(resolved_mesh_scoping)

        requested_location = self._normalize_field_location(location, allow_empty=True)
        if requested_location and hasattr(operator.inputs, "requested_location"):
            operator.inputs.requested_location(requested_location)

        fields_container = operator.outputs.fields_container()
        if requested_location and self._fields_container_location(fields_container) != requested_location:
            fields_container = self._convert_fields_container_location(
                fields_container,
                location=requested_location,
                mesh=resolved_model.metadata.meshed_region,
            )

        return self._worker_services.register_handle(
            fields_container,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=resolved_owner_scope,
            metadata=self._build_fields_container_metadata(
                fields_container,
                result_name=normalized_result_name,
                model_ref=model_ref,
                mesh_scoping=mesh_scoping,
                time_scoping=time_scoping,
            ),
        )

    def convert_fields_location(
        self,
        value: Any,
        *,
        model: Any,
        location: str,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        normalized_location = self._normalize_field_location(location)
        if self._fields_container_location(fields_container) == normalized_location:
            return fields_ref

        model_ref, resolved_model = self._resolve_model_handle_and_object(model)
        converted = self._convert_fields_container_location(
            fields_container,
            location=normalized_location,
            mesh=resolved_model.metadata.meshed_region,
        )
        metadata = dict(fields_ref.metadata)
        metadata.update(
            self._build_fields_container_metadata(
                converted,
                result_name=str(metadata.get("result_name", "")).strip(),
                model_ref=model_ref,
                mesh_scoping=metadata.get("mesh_scoping_handle_id", ""),
                time_scoping=metadata.get("time_scoping_handle_id", ""),
            )
        )
        metadata["source_handle_id"] = fields_ref.handle_id
        metadata["operation"] = "convert_location"
        metadata["requested_location"] = normalized_location
        return self._worker_services.register_handle(
            converted,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata=metadata,
        )

    def compute_field_norm(
        self,
        value: Any,
        *,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        dpf = self._dpf_module()
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        operator = dpf.operators.math.norm_fc()
        operator.inputs.fields_container(fields_container)
        normalized = operator.outputs.fields_container()
        metadata = dict(fields_ref.metadata)
        metadata.update(self._build_fields_container_metadata(normalized, result_name=str(metadata.get("result_name", "")).strip()))
        metadata["source_handle_id"] = fields_ref.handle_id
        metadata["operation"] = "norm"
        return self._worker_services.register_handle(
            normalized,
            kind=DPF_FIELDS_CONTAINER_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata=metadata,
        )

    def reduce_fields_min_max(
        self,
        value: Any,
        *,
        run_id: str = "",
        owner_scope: str = "",
    ) -> DpfFieldRange:
        dpf = self._dpf_module()
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        operator = dpf.operators.min_max.min_max_fc()
        operator.inputs.fields_container(fields_container)
        resolved_owner_scope = self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope)
        base_metadata = {
            "source_handle_id": fields_ref.handle_id,
            "operation": "min_max",
            "result_name": str(fields_ref.metadata.get("result_name", "")).strip(),
        }
        minimum = self._worker_services.register_handle(
            operator.outputs.field_min(),
            kind=DPF_FIELD_HANDLE_KIND,
            owner_scope=resolved_owner_scope,
            metadata={
                **base_metadata,
                "reduction": "min",
                **self._build_field_metadata(operator.outputs.field_min()),
            },
        )
        maximum = self._worker_services.register_handle(
            operator.outputs.field_max(),
            kind=DPF_FIELD_HANDLE_KIND,
            owner_scope=resolved_owner_scope,
            metadata={
                **base_metadata,
                "reduction": "max",
                **self._build_field_metadata(operator.outputs.field_max()),
            },
        )
        return DpfFieldRange(minimum=minimum, maximum=maximum)

    def extract_mesh(
        self,
        *,
        model: Any,
        mesh_scoping: Any | None = None,
        nodes_only: bool = False,
        run_id: str = "",
        owner_scope: str = "",
    ) -> RuntimeHandleRef:
        dpf = self._dpf_module()
        model_ref, resolved_model = self._resolve_model_handle_and_object(model)
        mesh = resolved_model.metadata.meshed_region.deep_copy()
        if mesh_scoping is not None:
            scoping = self._resolve_mesh_scoping_input(mesh_scoping)
            if scoping is None:
                raise TypeError("mesh_scoping could not be resolved")
            operator = dpf.operators.mesh.from_scoping()
            operator.inputs.mesh(mesh)
            operator.inputs.scoping(scoping)
            if nodes_only:
                operator.inputs.nodes_only(True)
            mesh = operator.outputs.mesh()

        return self._worker_services.register_handle(
            mesh,
            kind=DPF_MESH_HANDLE_KIND,
            owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
            metadata={
                "model_handle_id": model_ref.handle_id,
                "mesh_scoping_handle_id": self._handle_id_or_empty(mesh_scoping),
                "nodes_only": bool(nodes_only),
                **self._build_mesh_metadata(mesh),
            },
        )

    def export_field_artifacts(
        self,
        value: Any,
        *,
        model: Any,
        artifact_store: ProjectArtifactStore,
        artifact_key: str,
        export_formats: Iterable[str],
        mesh: Any | None = None,
        temporary_root_parent: str | Path | None = None,
    ) -> dict[str, RuntimeArtifactRef]:
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        resolved_mesh = self._resolve_mesh_object(mesh, model=resolved_model)
        normalized_key = self._normalize_artifact_key(artifact_key)
        normalized_formats = self._normalize_export_formats(export_formats)
        if not normalized_formats:
            raise ValueError("export_formats must contain at least one supported format")

        staging_root = artifact_store.ensure_staging_root(temporary_root_parent=temporary_root_parent)
        artifact_refs: dict[str, RuntimeArtifactRef] = {}
        for export_format in normalized_formats:
            artifact_id = self._artifact_id(normalized_key, export_format)
            slot = self._artifact_slot(normalized_key, export_format)
            relative_path = self._artifact_relative_path(normalized_key, export_format)
            output_path = staging_root.joinpath(*PurePosixPath(relative_path).parts)
            self._clear_output_path(output_path)
            entry_metadata = {
                "format": export_format,
                "artifact_key": normalized_key,
                "source_handle_id": fields_ref.handle_id,
            }

            if export_format == "csv":
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_csv_export(fields_container, output_path)
                entry_metadata["entry_file"] = output_path.name
            elif export_format == "png":
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_png_export(fields_container, resolved_mesh, output_path)
                entry_metadata["entry_file"] = output_path.name
            elif export_format == "vtu":
                output_path.mkdir(parents=True, exist_ok=True)
                entry_metadata["files"] = self._write_vtu_bundle(fields_container, resolved_mesh, output_path)
            else:
                output_path.mkdir(parents=True, exist_ok=True)
                bundle_files = self._write_vtu_bundle(fields_container, resolved_mesh, output_path)
                bundle_files.extend(self._write_vtm_bundle(output_path))
                entry_metadata["entry_file"] = _DEFAULT_VTM_FILENAME
                entry_metadata["files"] = sorted(bundle_files)

            artifact_store.register_staged_entry(
                artifact_id,
                relative_path=relative_path,
                slot=slot,
                extra=entry_metadata,
            )
            artifact_refs[export_format] = RuntimeArtifactRef.staged(
                artifact_id,
                metadata={
                    "format": export_format,
                    "artifact_key": normalized_key,
                    "relative_path": relative_path,
                    **({"entry_file": entry_metadata["entry_file"]} if "entry_file" in entry_metadata else {}),
                },
            )

        return artifact_refs

    def materialize_viewer_dataset(
        self,
        value: Any,
        *,
        model: Any,
        output_profile: str,
        mesh: Any | None = None,
        artifact_store: ProjectArtifactStore | None = None,
        artifact_key: str = "",
        export_formats: Iterable[str] = (),
        temporary_root_parent: str | Path | None = None,
        run_id: str = "",
        owner_scope: str = "",
    ) -> DpfMaterializationResult:
        normalized_profile = self._normalize_output_profile(output_profile)
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        resolved_mesh = self._resolve_mesh_object(mesh, model=resolved_model)

        if normalized_profile == "memory" and tuple(export_formats):
            raise ValueError("export_formats are only valid for stored or both output profiles")
        if normalized_profile in {"stored", "both"} and artifact_store is None:
            raise ValueError("artifact_store is required for stored or both output profiles")

        summary = {
            **self._build_fields_container_metadata(
                fields_container,
                result_name=str(fields_ref.metadata.get("result_name", "")).strip(),
            ),
            **self._build_mesh_metadata(resolved_mesh),
            "source_handle_id": fields_ref.handle_id,
            "output_profile": normalized_profile,
        }

        dataset_ref: RuntimeHandleRef | None = None
        if normalized_profile in {"memory", "both"}:
            dataset = self._build_viewer_dataset(fields_container, resolved_mesh)
            summary["dataset_type"] = self._dataset_kind(dataset)
            summary["array_names"] = self._dataset_array_names(dataset)
            dataset_ref = self._worker_services.register_handle(
                dataset,
                kind=DPF_VIEWER_DATASET_HANDLE_KIND,
                owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
                metadata=summary,
            )

        artifacts: dict[str, RuntimeArtifactRef] = {}
        if normalized_profile in {"stored", "both"}:
            artifacts = self.export_field_artifacts(
                value,
                model=model,
                artifact_store=artifact_store if artifact_store is not None else ProjectArtifactStore(project_path=None),
                artifact_key=artifact_key,
                export_formats=export_formats,
                mesh=mesh,
                temporary_root_parent=temporary_root_parent,
            )

        return DpfMaterializationResult(
            output_profile=normalized_profile,
            dataset_ref=dataset_ref,
            artifacts=artifacts,
            summary=summary,
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

    def _resolve_handle_owner_scope(self, *, run_id: str, owner_scope: str) -> str:
        return self._resolve_scoping_owner_scope(run_id=run_id, owner_scope=owner_scope)

    def _resolve_model_handle_and_object(self, value: Any) -> tuple[RuntimeHandleRef, Any]:
        model_ref = self.load_model(value)
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
        alias = _FIELD_LOCATION_ALIASES.get(normalized.casefold())
        if alias is not None:
            return alias
        if normalized in {"Nodal", "Elemental", "ElementalNodal"}:
            return normalized
        raise ValueError("location must resolve to Nodal, Elemental, or ElementalNodal")

    @staticmethod
    def _normalize_output_profile(value: object) -> str:
        normalized = str(value).strip().casefold()
        if normalized not in _SUPPORTED_OUTPUT_PROFILES:
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
            if token not in _SUPPORTED_EXPORT_FORMATS:
                raise ValueError(f"Unsupported export format: {raw_value!r}")
            if token in seen:
                continue
            normalized.append(token)
            seen.add(token)
        return tuple(normalized)

    @staticmethod
    def _normalize_artifact_key(value: object) -> str:
        normalized = _INVALID_ARTIFACT_TOKEN_CHARS.sub("_", str(value).strip()).strip("._-")
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
        base = _DEFAULT_EXPORT_SUBDIRECTORY / artifact_key
        if export_format == "csv":
            return (base / "field.csv").as_posix()
        if export_format == "png":
            return (base / "preview.png").as_posix()
        return (base / export_format).as_posix()

    @staticmethod
    def _clear_output_path(path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return
        path.unlink(missing_ok=True)

    def _write_csv_export(self, fields_container: Any, output_path: Path) -> None:
        dpf = self._dpf_module()
        operator = dpf.operators.serialization.field_to_csv()
        operator.inputs.file_path(str(output_path))
        operator.inputs.field_or_fields_container(fields_container)
        operator.run()

    def _write_png_export(self, fields_container: Any, mesh: Any, output_path: Path) -> None:
        pyvista = self._pyvista_module()
        dataset = self._build_viewer_dataset(fields_container, mesh)
        preview_dataset = self._preview_dataset(dataset)
        plotter = pyvista.Plotter(off_screen=True)
        try:
            array_name = self._preferred_array_name(preview_dataset)
            plotter.add_mesh(preview_dataset, scalars=array_name)
            plotter.view_isometric()
            plotter.show(screenshot=str(output_path), auto_close=False)
        finally:
            plotter.close()

    def _write_vtu_bundle(self, fields_container: Any, mesh: Any, output_dir: Path) -> list[str]:
        dpf = self._dpf_module()
        operator = dpf.operators.serialization.vtu_export()
        operator.inputs.directory(str(output_dir))
        operator.inputs.base_name(_DEFAULT_VTU_BASENAME)
        operator.inputs.mesh(mesh)
        operator.inputs.fields1(fields_container)
        operator.outputs.path()
        return sorted(path.name for path in output_dir.glob("*.vtu"))

    def _write_vtm_bundle(self, output_dir: Path) -> list[str]:
        pyvista = self._pyvista_module()
        vtu_files = sorted(output_dir.glob("*.vtu"))
        multiblock = pyvista.MultiBlock([pyvista.read(path) for path in vtu_files])
        target_path = output_dir / _DEFAULT_VTM_FILENAME
        multiblock.save(target_path)
        return [target_path.name]

    def _build_viewer_dataset(self, fields_container: Any, mesh: Any) -> Any:
        pyvista = self._pyvista_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            if len(fields_container) == 1:
                vtk_path = temp_root / "dataset.vtk"
                dpf = self._dpf_module()
                operator = dpf.operators.serialization.vtk_export()
                operator.inputs.file_path(str(vtk_path))
                operator.inputs.mesh(mesh)
                operator.inputs.fields1(fields_container)
                operator.run()
                return pyvista.read(vtk_path)

            self._write_vtu_bundle(fields_container, mesh, temp_root)
            return pyvista.MultiBlock([pyvista.read(path) for path in sorted(temp_root.glob("*.vtu"))])

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

    @staticmethod
    def _pyvista_module() -> Any:
        try:
            return importlib.import_module("pyvista")
        except ModuleNotFoundError as exc:
            raise DpfRuntimeUnavailableError(
                "pyvista is not available; DPF materialization exports remain optional until used."
            ) from exc

    @staticmethod
    def _dpf_module() -> Any:
        try:
            return importlib.import_module("ansys.dpf.core")
        except ModuleNotFoundError as exc:
            raise DpfRuntimeUnavailableError(
                "ansys.dpf.core is not available; DPF runtime features remain optional until used."
            ) from exc


__all__ = [
    "DPF_FIELDS_CONTAINER_HANDLE_KIND",
    "DPF_FIELD_HANDLE_KIND",
    "DPF_MESH_SCOPING_HANDLE_KIND",
    "DPF_MESH_HANDLE_KIND",
    "DPF_MODEL_HANDLE_KIND",
    "DPF_RESULT_FILE_HANDLE_KIND",
    "DPF_TIME_SCOPING_HANDLE_KIND",
    "DPF_VIEWER_DATASET_HANDLE_KIND",
    "DpfFieldRange",
    "DpfMaterializationResult",
    "DpfResultFile",
    "DpfRuntimeService",
    "DpfRuntimeUnavailableError",
    "UnsupportedDpfResultFileError",
]
