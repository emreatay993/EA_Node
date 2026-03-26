from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

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
from ea_node_editor.execution.dpf_runtime.base import DpfRuntimeBase
from ea_node_editor.execution.dpf_runtime.materialization import DpfRuntimeMaterializationMixin
from ea_node_editor.execution.dpf_runtime.operations import DpfRuntimeOperationsMixin
from ea_node_editor.execution.dpf_runtime.optional_imports import (
    load_dpf_module,
    load_pyvista_module,
)

if TYPE_CHECKING:
    from ea_node_editor.execution.worker_services import WorkerServices


class DpfRuntimeService(
    DpfRuntimeOperationsMixin,
    DpfRuntimeMaterializationMixin,
    DpfRuntimeBase,
):
    """Compatibility facade over the packet-owned DPF runtime package."""

    def __init__(self, worker_services: WorkerServices) -> None:
        self._worker_services = worker_services
        self._result_file_cache: dict[str, Any] = {}
        self._model_cache: dict[str, Any] = {}

    @staticmethod
    def _pyvista_module() -> Any:
        return load_pyvista_module(importlib.import_module)

    @staticmethod
    def _dpf_module() -> Any:
        return load_dpf_module(importlib.import_module)


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
