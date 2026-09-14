# Purpose: Detach execution requests before they leave the caller's thread.
# Map: subsystems/execution.md
# Tests: tests/test_execution_submission.py
from __future__ import annotations

from dataclasses import dataclass
import json

from ea_node_editor.execution.backends import (
    ExecutionBackendPolicy,
    ExecutionBackendSelection,
)
from ea_node_editor.execution.prepared_execution import RecomputeMode
from ea_node_editor.execution.runtime_requests import ExecutionRequest
from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot
from ea_node_editor.execution.solution_store import PreparationState
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import DataTypeCatalog
from ea_node_editor.runtime_contracts.settled_results import (
    settled_output_mapping_from_payload,
    settled_outputs_to_payload,
)
from ea_node_editor.runtime_contracts.value_codec import (
    deserialize_runtime_value,
    serialize_runtime_value,
)


@dataclass(frozen=True, slots=True, init=False)
class CapturedExecutionRequest:
    """Owned JSON bytes, never a shared live graph, mapping or Qt object."""

    _payload: bytes
    project_id: str
    workspace_id: str
    project_path: str

    def __init__(
        self, request: ExecutionRequest, *, catalog: DataTypeCatalog | None
    ) -> None:
        if not isinstance(request, ExecutionRequest):
            raise TypeError("request must be an ExecutionRequest")
        trigger, snapshot, backend = request.trigger_without_runtime_snapshot()
        if isinstance(snapshot, RuntimeSnapshot):
            snapshot = snapshot.to_document(catalog=catalog)
        elif snapshot is not None:
            snapshot = serialize_runtime_value(snapshot, catalog=catalog)
        if isinstance(backend, (ExecutionBackendPolicy, ExecutionBackendSelection)):
            backend = backend.to_payload()
        payload = {
            "project_path": str(request.project_path),
            "workspace_id": str(request.workspace_id),
            "trigger": serialize_runtime_value(trigger, catalog=catalog),
            "runtime_snapshot": snapshot,
            "execution_backend": backend,
            "target_node_ids": list(request.target_node_ids),
            "trigger_publications": settled_outputs_to_payload(
                request.trigger_publications, catalog=catalog
            ),
            "trigger_captures": settled_outputs_to_payload(
                request.trigger_captures, catalog=catalog
            ),
            "clicked_trigger_node_id": request.clicked_trigger_node_id,
            "recompute_mode": RecomputeMode(request.recompute_mode).value,
        }
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        object.__setattr__(self, "_payload", encoded)
        object.__setattr__(
            self, "project_id", str(snapshot.get("project_id", "")) if snapshot else ""
        )
        object.__setattr__(
            self,
            "workspace_id",
            str(
                request.workspace_id
                or (snapshot.get("active_workspace_id", "") if snapshot else "")
            ),
        )
        object.__setattr__(self, "project_path", str(request.project_path))

    def materialize(self, catalog: DataTypeCatalog | None) -> ExecutionRequest:
        payload = json.loads(self._payload)
        snapshot = payload["runtime_snapshot"]
        payload["runtime_snapshot"] = (
            RuntimeSnapshot.from_mapping(snapshot, catalog=catalog)
            if snapshot is not None
            else None
        )
        payload["trigger"] = deserialize_runtime_value(
            payload["trigger"], catalog=catalog
        )
        for name in ("trigger_publications", "trigger_captures"):
            payload[name] = settled_output_mapping_from_payload(
                payload[name], catalog=catalog
            )
        payload["target_node_ids"] = tuple(payload["target_node_ids"])
        payload["recompute_mode"] = RecomputeMode(payload["recompute_mode"])
        return ExecutionRequest(**payload)


@dataclass(frozen=True, slots=True)
class PreparationCapture:
    """The request and state commitments observed before background handoff."""

    request: CapturedExecutionRequest
    registry: NodeRegistry | None
    binding_revision: int
    solution_state: PreparationState | None
