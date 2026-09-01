# Purpose: Compose the concrete worker-local DPF runtime service.
# Map: feature_routes/ansys_dpf_operator_viewer_transport.md
# Tests: tests/test_dpf_runtime_service.py

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from ea_node_editor.execution.dpf_runtime.analysis import DpfRuntimeAnalysisMixin
from ea_node_editor.execution.dpf_runtime.base import DpfRuntimeBase
from ea_node_editor.execution.dpf_runtime.materialization import (
    DpfRuntimeMaterializationMixin,
)
from ea_node_editor.execution.dpf_runtime.operations import DpfRuntimeOperationsMixin
from ea_node_editor.execution.dpf_runtime.optional_imports import (
    load_dpf_module,
    load_pyvista_module,
)

if TYPE_CHECKING:
    from ea_node_editor.execution.worker_services import WorkerServices


class DpfRuntimeService(
    DpfRuntimeOperationsMixin,
    DpfRuntimeAnalysisMixin,
    DpfRuntimeMaterializationMixin,
    DpfRuntimeBase,
):
    """Concrete worker-local composition of the DPF runtime mixins."""

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


__all__ = ["DpfRuntimeService"]
