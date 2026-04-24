from __future__ import annotations

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
DPF_EXECUTION_VIEWER_TRANSPORT_KIND = "dpf_transport_bundle"


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
                camera_state=request.session_summary.get("camera_state", {}),
                export_formats=request.export_formats,
                project_path=request.project_path,
                runtime_snapshot=request.runtime_snapshot,
                runtime_snapshot_context=request.runtime_snapshot_context,
            )
        )
        transport = dict(result.transport)
        if transport:
            transport["backend_id"] = self.backend_id
        return ViewerBackendMaterializationResult(
            backend_id=self.backend_id,
            data_refs=dict(result.data_refs),
            transport=transport,
            transport_revision=int(result.transport_revision),
            live_open_status=str(result.live_open_status).strip(),
            live_open_blocker=dict(result.live_open_blocker),
            summary=dict(result.summary),
        )

    def release_session_transport(self, *, workspace_id: str, session_id: str) -> None:
        self._materialization_backend.release_session_transport(
            workspace_id=workspace_id,
            session_id=session_id,
        )

    def release_workspace_transport(self, *, workspace_id: str) -> None:
        self._materialization_backend.release_workspace_transport(workspace_id=workspace_id)

    def reset(self) -> None:
        self._materialization_backend.reset()


__all__ = [
    "DPF_EXECUTION_VIEWER_BACKEND_ID",
    "DPF_EXECUTION_VIEWER_TRANSPORT_KIND",
    "DpfExecutionViewerBackend",
]
