from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ea_node_editor.execution.dpf_runtime.service import DpfRuntimeService
    from ea_node_editor.execution.worker_services import WorkerServices


def create_dpf_runtime_service(worker_services: WorkerServices) -> DpfRuntimeService:
    from ea_node_editor.execution.dpf_runtime.service import DpfRuntimeService

    return DpfRuntimeService(worker_services)


__all__ = [
    "create_dpf_runtime_service",
]
