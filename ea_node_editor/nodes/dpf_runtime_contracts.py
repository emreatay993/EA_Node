from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from ea_node_editor.nodes.runtime_refs import RuntimeArtifactRef, RuntimeHandleRef

DPF_RESULT_FILE_HANDLE_KIND = "dpf.result_file"
DPF_MODEL_HANDLE_KIND = "dpf.model"
DPF_MESH_SCOPING_HANDLE_KIND = "dpf.mesh_scoping"
DPF_TIME_SCOPING_HANDLE_KIND = "dpf.time_scoping"
DPF_FIELDS_CONTAINER_HANDLE_KIND = "dpf.fields_container"
DPF_FIELD_HANDLE_KIND = "dpf.field"
DPF_MESH_HANDLE_KIND = "dpf.mesh"
DPF_VIEWER_DATASET_HANDLE_KIND = "dpf.viewer_dataset"
DPF_OBJECT_HANDLE_KIND = "dpf_object_handle"


class DpfFieldRangePort(Protocol):
    minimum: RuntimeHandleRef
    maximum: RuntimeHandleRef


class DpfMaterializationResultPort(Protocol):
    output_profile: str
    dataset_ref: RuntimeHandleRef | None
    artifacts: Mapping[str, RuntimeArtifactRef]
    summary: Mapping[str, Any]


class DpfRuntimeServicePort(Protocol):
    def load_result_file(self, value: Any) -> RuntimeHandleRef: ...

    def load_model(self, value: Any) -> RuntimeHandleRef: ...

    def create_mesh_scoping(
        self,
        ids: Sequence[int],
        *,
        location: str,
        run_id: str = "",
    ) -> RuntimeHandleRef: ...

    def create_time_scoping(
        self,
        set_ids: Sequence[int],
        *,
        model: RuntimeHandleRef | None = None,
        run_id: str = "",
    ) -> RuntimeHandleRef: ...

    def extract_result_fields(
        self,
        *,
        model: RuntimeHandleRef,
        result_name: Any,
        set_ids: Sequence[int],
        time_scoping: Any = None,
        mesh_scoping: Any = None,
        location: str = "",
        run_id: str = "",
    ) -> RuntimeHandleRef: ...

    def compute_field_norm(
        self,
        fields_container: RuntimeHandleRef,
        *,
        run_id: str = "",
    ) -> RuntimeHandleRef: ...

    def convert_fields_location(
        self,
        fields_container: RuntimeHandleRef,
        *,
        model: RuntimeHandleRef,
        location: str,
        run_id: str = "",
    ) -> RuntimeHandleRef: ...

    def reduce_fields_min_max(
        self,
        fields_container: RuntimeHandleRef,
        *,
        run_id: str = "",
    ) -> DpfFieldRangePort: ...

    def extract_mesh(
        self,
        *,
        model: RuntimeHandleRef,
        mesh_scoping: Any = None,
        nodes_only: bool = False,
        run_id: str = "",
    ) -> RuntimeHandleRef: ...

    def materialize_viewer_dataset(
        self,
        fields_container: RuntimeHandleRef,
        *,
        model: RuntimeHandleRef,
        output_profile: str,
        mesh: Any = None,
        artifact_store: Any = None,
        artifact_key: str = "",
        export_formats: Sequence[str] = (),
        temporary_root_parent: Path | None = None,
        run_id: str = "",
    ) -> DpfMaterializationResultPort: ...


__all__ = [
    "DPF_FIELDS_CONTAINER_HANDLE_KIND",
    "DPF_FIELD_HANDLE_KIND",
    "DPF_MESH_SCOPING_HANDLE_KIND",
    "DPF_MESH_HANDLE_KIND",
    "DPF_MODEL_HANDLE_KIND",
    "DPF_OBJECT_HANDLE_KIND",
    "DPF_RESULT_FILE_HANDLE_KIND",
    "DPF_TIME_SCOPING_HANDLE_KIND",
    "DPF_VIEWER_DATASET_HANDLE_KIND",
    "DpfFieldRangePort",
    "DpfMaterializationResultPort",
    "DpfRuntimeServicePort",
]
