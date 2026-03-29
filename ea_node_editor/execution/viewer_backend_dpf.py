from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from ea_node_editor.execution.dpf_runtime.viewer_session_backend import (
    DpfViewerSessionMaterializationBackend,
    ViewerSessionMaterializationRequest,
)
from ea_node_editor.execution.viewer_backend import (
    ViewerBackendMaterializationRequest,
    ViewerBackendMaterializationResult,
)

if TYPE_CHECKING:
    from ea_node_editor.execution.worker_services import WorkerServices


DPF_EXECUTION_VIEWER_BACKEND_ID = "dpf_embedded"
DPF_EXECUTION_VIEWER_TRANSPORT_KIND = "dpf_handle_refs"


class DpfExecutionViewerBackend:
    backend_id = DPF_EXECUTION_VIEWER_BACKEND_ID

    def __init__(self, worker_services: "WorkerServices") -> None:
        self._materialization_backend = DpfViewerSessionMaterializationBackend(worker_services)

    def materialize(
        self,
        request: ViewerBackendMaterializationRequest,
    ) -> ViewerBackendMaterializationResult:
        result = self._materialization_backend.materialize(
            ViewerSessionMaterializationRequest(
                workspace_id=request.workspace_id,
                node_id=request.node_id,
                session_id=request.session_id,
                owner_scope=request.owner_scope,
                source_refs=request.source_refs,
                session_options=request.session_options,
                request_options=request.request_options,
                output_profile=request.output_profile,
                export_formats=request.export_formats,
                project_path=request.project_path,
                runtime_snapshot=request.runtime_snapshot,
                runtime_snapshot_context=request.runtime_snapshot_context,
            )
        )
        transport = {
            "kind": DPF_EXECUTION_VIEWER_TRANSPORT_KIND,
            "version": 1,
            "backend_id": self.backend_id,
            "data_refs": copy.deepcopy(result.data_refs),
        }
        has_live_dataset = "dataset" in result.data_refs
        live_open_status = "ready" if has_live_dataset else "blocked"
        live_open_blocker = {}
        if not has_live_dataset:
            live_open_blocker = {
                "code": "transport_not_ready",
                "reason": "Live viewer transport is not materialized.",
            }
        return ViewerBackendMaterializationResult(
            backend_id=self.backend_id,
            data_refs=copy.deepcopy(result.data_refs),
            transport=transport,
            live_open_status=live_open_status,
            live_open_blocker=live_open_blocker,
            summary=copy.deepcopy(result.summary),
        )


__all__ = [
    "DPF_EXECUTION_VIEWER_BACKEND_ID",
    "DPF_EXECUTION_VIEWER_TRANSPORT_KIND",
    "DpfExecutionViewerBackend",
]
