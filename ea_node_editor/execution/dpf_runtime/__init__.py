from __future__ import annotations

from typing import TYPE_CHECKING

from ea_node_editor.execution.dpf_runtime.contracts import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
    DPF_FIELD_HANDLE_KIND,
    DPF_MESH_SCOPING_HANDLE_KIND,
    DPF_MESH_HANDLE_KIND,
    DPF_MODEL_HANDLE_KIND,
    DPF_RESULT_FILE_HANDLE_KIND,
    DPF_TIME_SCOPING_HANDLE_KIND,
    DPF_VIEWER_DATASET_HANDLE_KIND,
    DpfFieldRange,
    DpfMaterializationResult,
    DpfResultFile,
    DpfRuntimeUnavailableError,
    UnsupportedDpfResultFileError,
)

if TYPE_CHECKING:
    from ea_node_editor.execution.dpf_runtime_service import DpfRuntimeService
    from ea_node_editor.execution.worker_services import WorkerServices


def create_dpf_runtime_service(worker_services: WorkerServices) -> DpfRuntimeService:
    from ea_node_editor.execution.dpf_runtime_service import DpfRuntimeService

    return DpfRuntimeService(worker_services)


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
    "DpfRuntimeUnavailableError",
    "UnsupportedDpfResultFileError",
    "create_dpf_runtime_service",
]
