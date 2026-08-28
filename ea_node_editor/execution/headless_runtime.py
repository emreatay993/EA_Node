# Purpose: Expose the Qt-free COREX runtime, preparation, and CLI entry points.
# Map: subsystems/execution.md
# Tests: tests/test_headless_runtime.py, tests/test_execution_client.py
# Landmarks: ExecutionRequest; CorexRuntime.prepare_execution; dispatch_prepared; run

"""Qt-free Corex runtime API and CLI entry point."""

from __future__ import annotations

import argparse
import copy
import json
import queue
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from ea_node_editor.execution.backends import (
    PROCESS_ISOLATED_BACKEND,
    TRUSTED_IN_PROCESS_BACKEND,
    ExecutionBackendPolicy,
)
from ea_node_editor.execution.client import ExecutionBackendClient
from ea_node_editor.execution.execution_plan import ExecutionPlan
from ea_node_editor.execution.prepared_execution import (
    MAX_ACCEPTED_NODE_PAYLOADS_PER_PREPARATION,
    MAX_ACCEPTED_OUTPUT_PAYLOAD_BYTES,
    MAX_ACCEPTED_PORT_RESULTS_PER_PREPARATION,
    InvalidationResult,
    PreparedAction,
    PreparedDispatchEnvelope,
    PreparedExecution,
    PreparedNodeDecision,
    RecomputeMode,
    SolutionStateChangedEvent,
)
from ea_node_editor.execution.protocol import (
    StartRunCommand,
    catalog_agreement,
    coerce_start_run_command,
    runtime_registry_fingerprint,
)
from ea_node_editor.runtime_contracts.settled_results import (
    SettledPortResult,
    settled_output_mapping_from_payload,
)
from ea_node_editor.runtime_contracts.solution_records import (
    NodeSolutionFact,
    SolutionRecord,
)
from ea_node_editor.execution.solution_identity import (
    assemble_node_solution,
    canonical_digest,
)
from ea_node_editor.execution.solution_store import (
    CapturedNodeSolution,
    SolutionStore,
)
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    RuntimeSnapshotContext,
    build_runtime_snapshot,
    coerce_runtime_snapshot,
)
from ea_node_editor.execution.worker_runtime import RuntimeArtifactService
from ea_node_editor.graph.project_state import ProjectData
from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.runtime_contracts import (
    ArrayDataRef,
    ArraySlice2DRef,
    DataTree,
    RuntimeArtifactRef,
    RuntimeHandleRef,
    TabularDataRef,
    TabularWindowRef,
)

ExecutionStatus = Literal["completed", "failed", "stopped", "timeout"]
ExecutionEvent = dict[str, Any]
ExecutionEventCallback = Callable[[ExecutionEvent], None]

TERMINAL_EVENT_TYPES = frozenset({"run_completed", "run_failed", "run_stopped"})
RUN_SCOPED_EVENT_TYPES = frozenset(
    {
        "run_started",
        "run_state",
        "run_completed",
        "run_failed",
        "run_stopped",
        "node_started",
        "node_settled",
        "trigger_capture_settled",
        "trigger_published",
        "log",
        "protocol_error",
    }
)


@dataclass(frozen=True, slots=True)
class ProjectLoadRequest:
    project_path: str | Path
    extra_plugin_dirs: tuple[Path, ...] = field(default_factory=tuple)

    def normalized_path(self) -> Path:
        return Path(self.project_path).expanduser()


@dataclass(frozen=True, slots=True)
class LoadedProject:
    project_path: Path
    project: ProjectData
    registry: NodeRegistry

    def select_workspace(
        self, selection: "WorkspaceSelection | str | None" = None
    ) -> WorkspaceData:
        return select_workspace(self, selection)


@dataclass(frozen=True, slots=True)
class WorkspaceSelection:
    workspace_id: str = ""


@dataclass(frozen=True, slots=True)
class CancellationRequest:
    run_id: str
    reason: str = "user"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    project_path: str | Path = ""
    workspace_id: str = ""
    trigger: Mapping[str, Any] = field(default_factory=dict)
    runtime_snapshot: RuntimeSnapshot | Mapping[str, Any] | None = None
    execution_backend: ExecutionBackendPolicy | Mapping[str, Any] | str | None = None
    target_node_ids: tuple[str, ...] = field(default_factory=tuple)
    trigger_publications: Mapping[str, SettledPortResult] = field(default_factory=dict)
    trigger_captures: Mapping[str, SettledPortResult] = field(default_factory=dict)
    clicked_trigger_node_id: str = ""
    recompute_mode: RecomputeMode = RecomputeMode.REUSE_VALID

    def trigger_without_runtime_snapshot(
        self,
    ) -> tuple[
        dict[str, Any],
        RuntimeSnapshot | Mapping[str, Any] | None,
        ExecutionBackendPolicy | Mapping[str, Any] | str | None,
    ]:
        trigger_source = dict(self.trigger)
        snapshot = self.runtime_snapshot
        if snapshot is None:
            snapshot = trigger_source.pop("runtime_snapshot", None)
        else:
            trigger_source.pop("runtime_snapshot", None)
        execution_backend = self.execution_backend
        if execution_backend is None:
            execution_backend = trigger_source.pop("execution_backend", None)
        else:
            trigger_source.pop("execution_backend", None)
        trigger = copy.deepcopy(trigger_source)
        return trigger, snapshot, execution_backend


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    run_id: str
    workspace_id: str
    status: ExecutionStatus
    events: tuple[ExecutionEvent, ...] = field(default_factory=tuple)
    terminal_event: ExecutionEvent = field(default_factory=dict)
    error: str = ""
    traceback: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "error": self.error,
            "traceback": self.traceback,
            "terminal_event": copy.deepcopy(self.terminal_event),
            "events": [copy.deepcopy(event) for event in self.events],
        }


class ExecutionEventStream:
    def __init__(self) -> None:
        self._events: queue.Queue[ExecutionEvent] = queue.Queue()
        self._callbacks: list[ExecutionEventCallback] = []
        self._lock = threading.RLock()

    def subscribe(self, callback: ExecutionEventCallback) -> Callable[[], None]:
        with self._lock:
            self._callbacks.append(callback)

        def _unsubscribe() -> None:
            with self._lock:
                try:
                    self._callbacks.remove(callback)
                except ValueError:
                    return

        return _unsubscribe

    def publish(self, event: Mapping[str, Any]) -> None:
        payload = copy.deepcopy(dict(event))
        self._events.put(payload)
        with self._lock:
            callbacks = tuple(self._callbacks)
        for callback in callbacks:
            try:
                callback(copy.deepcopy(payload))
            except Exception:
                continue

    def next_event(self, timeout: float | None = None) -> ExecutionEvent:
        return self._events.get(timeout=timeout)

    def iter_events(
        self,
        *,
        timeout: float | None = None,
        stop_after_terminal: bool = False,
    ) -> Iterator[ExecutionEvent]:
        while True:
            event = self.next_event(timeout=timeout)
            yield event
            if (
                stop_after_terminal
                and str(event.get("type", "")) in TERMINAL_EVENT_TYPES
            ):
                return


def load_project(
    request: ProjectLoadRequest | str | Path,
    *,
    registry: NodeRegistry | None = None,
    extra_plugin_dirs: Sequence[Path] | None = None,
) -> LoadedProject:
    if isinstance(request, ProjectLoadRequest):
        load_request = request
    else:
        load_request = ProjectLoadRequest(
            project_path=request,
            extra_plugin_dirs=tuple(extra_plugin_dirs or ()),
        )
    runtime_registry = registry or build_default_registry(
        extra_plugin_dirs=list(load_request.extra_plugin_dirs)
    )
    project_path = load_request.normalized_path()
    project = JsonProjectSerializer(runtime_registry).load(str(project_path))
    return LoadedProject(
        project_path=project_path,
        project=project,
        registry=runtime_registry,
    )


def select_workspace(
    project: LoadedProject | ProjectData,
    selection: WorkspaceSelection | str | None = None,
) -> WorkspaceData:
    project_data = project.project if isinstance(project, LoadedProject) else project
    if isinstance(selection, WorkspaceSelection):
        requested_workspace_id = str(selection.workspace_id or "").strip()
    else:
        requested_workspace_id = str(selection or "").strip()

    if not requested_workspace_id:
        return project_data.ensure_default_workspace()

    try:
        workspace = project_data.workspaces[requested_workspace_id]
    except KeyError as exc:
        raise KeyError(f"Workspace not found: {requested_workspace_id}") from exc
    project_data.active_workspace_id = requested_workspace_id
    return workspace


class CorexRuntime:
    def __init__(
        self,
        *,
        client: Any | None = None,
        registry: NodeRegistry | None = None,
        solution_store: SolutionStore | None = None,
    ) -> None:
        self._client = client or ExecutionBackendClient()
        self._owns_client = client is None
        self._registry = registry
        self._lifecycle_lock = threading.RLock()
        self._registry_publication_lock = threading.RLock()
        self._solution_store = solution_store or SolutionStore()
        self._generation_snapshots: dict[str, Any] = {}
        self._run_artifact_services: dict[str, RuntimeArtifactService] = {}
        self._event_stream = ExecutionEventStream()
        self._generation_event_local = threading.local()
        self._client.subscribe(self._handle_client_event)
        subscribe_generation_events = getattr(
            self._client,
            "subscribe_generation_events",
            None,
        )
        if callable(subscribe_generation_events):
            subscribe_generation_events(self._handle_generation_event)

    @property
    def solution_store(self) -> SolutionStore:
        return self._solution_store

    @property
    def events(self) -> ExecutionEventStream:
        return self._event_stream

    def subscribe(self, callback: ExecutionEventCallback) -> Callable[[], None]:
        return self._event_stream.subscribe(callback)

    @contextmanager
    def registry_publication_guard(self) -> Iterator[None]:
        with self._lifecycle_lock:
            client_guard = getattr(self._client, "registry_publication_guard", None)
            if callable(
                getattr(type(self._client), "registry_publication_guard", None)
            ):
                with client_guard():
                    yield
                return
            with self._registry_publication_lock:
                yield

    def assert_registry_replaceable(self) -> None:
        with self.registry_publication_guard():
            assert_replaceable = getattr(
                self._client,
                "assert_registry_replaceable",
                None,
            )
            if callable(assert_replaceable):
                assert_replaceable()

    def replace_registry(self, registry: NodeRegistry) -> bool:
        if not isinstance(registry, NodeRegistry):
            raise TypeError("registry must be a NodeRegistry")
        solution_events: tuple[InvalidationResult, ...] = ()
        with self._lifecycle_lock, self.registry_publication_guard():
            previous_fingerprint = (
                self._registry.contract_fingerprint()
                if self._registry is not None
                else ""
            )
            replace_client_registry = getattr(self._client, "replace_registry", None)
            retired = (
                bool(replace_client_registry(registry))
                if callable(replace_client_registry)
                else False
            )
            self._registry = registry
            if (
                previous_fingerprint
                and previous_fingerprint != registry.contract_fingerprint()
            ):
                self._release_all_solution_resources()
                solution_events = self._solution_store.reset_runtime_generation(
                    "registry_generation_replaced"
                )
                self._run_artifact_services.clear()
        self._publish_solution_state_results(solution_events)
        return retired

    def load_project(
        self,
        project_path: str | Path,
        *,
        extra_plugin_dirs: Sequence[Path] | None = None,
    ) -> LoadedProject:
        return load_project(
            project_path,
            registry=self._registry,
            extra_plugin_dirs=extra_plugin_dirs,
        )

    def prepare_request(self, request: ExecutionRequest) -> ExecutionRequest:
        trigger, raw_snapshot, execution_backend = (
            request.trigger_without_runtime_snapshot()
        )
        if raw_snapshot is not None and self._registry is None:
            raise ValueError(
                "raw runtime snapshots require an authoritative node registry"
            )
        catalog = self._registry.data_types if self._registry is not None else None
        runtime_snapshot = coerce_runtime_snapshot(raw_snapshot, catalog=catalog)
        workspace_id = str(request.workspace_id or "").strip()
        project_path = str(request.project_path or "").strip()

        if runtime_snapshot is None:
            loaded_project = self.load_project(project_path)
            self.replace_registry(loaded_project.registry)
            workspace = loaded_project.select_workspace(
                WorkspaceSelection(workspace_id)
            )
            runtime_snapshot = build_runtime_snapshot(
                loaded_project.project,
                workspace_id=workspace.workspace_id,
                registry=loaded_project.registry,
            )
            workspace_id = workspace.workspace_id
            project_path = str(loaded_project.project_path)
        else:
            if not workspace_id:
                workspace_id = str(runtime_snapshot.active_workspace_id or "").strip()
            runtime_snapshot.workspace(workspace_id)

        return ExecutionRequest(
            project_path=project_path,
            workspace_id=workspace_id,
            trigger=trigger,
            runtime_snapshot=runtime_snapshot,
            execution_backend=execution_backend,
            target_node_ids=tuple(request.target_node_ids),
            trigger_publications=dict(request.trigger_publications),
            trigger_captures=dict(request.trigger_captures),
            clicked_trigger_node_id=str(request.clicked_trigger_node_id),
            recompute_mode=request.recompute_mode,
        )

    def prepare_execution(self, request: ExecutionRequest) -> PreparedExecution:
        with self._lifecycle_lock:
            prepared_request, candidate_registry = self._prepare_candidate_request(
                request
            )
            runtime_snapshot = prepared_request.runtime_snapshot
            assert isinstance(runtime_snapshot, RuntimeSnapshot)
            resolve_selection = getattr(
                self._client,
                "resolve_execution_selection",
                None,
            )
            if not callable(resolve_selection):
                raise RuntimeError(
                    "execution client does not support prepared generation routing"
                )
            selection = resolve_selection(
                prepared_request.execution_backend,
                runtime_snapshot,
            )
            preview_environment = getattr(
                self._client,
                "preview_execution_environment",
                None,
            )
            preview_environment_digest = ""
            if callable(preview_environment):
                preview_environment_digest = preview_environment(
                    selection,
                    candidate_registry,
                )
            generation_snapshot = self._client.execution_generation_snapshot(
                selection,
                registry_contract_fingerprint=(
                    candidate_registry.contract_fingerprint()
                ),
            )
            if not generation_snapshot.available and preview_environment_digest:
                generation_snapshot = replace(
                    generation_snapshot,
                    environment_digest=preview_environment_digest,
                )
            workspace = runtime_snapshot.workspace(prepared_request.workspace_id)
            plan = ExecutionPlan(
                workspace,
                candidate_registry,
                target_node_ids=prepared_request.target_node_ids,
                clicked_trigger_node_id=prepared_request.clicked_trigger_node_id,
                trigger_capture_node_ids=tuple(
                    sorted(prepared_request.trigger_captures)
                ),
            )
            interface_plan = (
                plan
                if not prepared_request.target_node_ids
                and not prepared_request.clicked_trigger_node_id
                else ExecutionPlan(workspace, candidate_registry)
            )
            project_id = str(runtime_snapshot.project_id).strip()
            namespace_id = self._solution_store.ensure_project(
                project_id,
                str(prepared_request.project_path),
            )
            preparation_id = f"preparation_{uuid.uuid4().hex}"
            trigger_reservation_id = ""
            reserved_trigger_generation: int | None = None
            if (
                prepared_request.clicked_trigger_node_id
                and plan.is_trigger(prepared_request.clicked_trigger_node_id)
            ):
                (
                    trigger_reservation_id,
                    reserved_trigger_generation,
                ) = self._solution_store.reserve_trigger_generation(
                    project_id=project_id,
                    workspace_id=workspace.workspace_id,
                    trigger_node_id=prepared_request.clicked_trigger_node_id,
                    preparation_id=preparation_id,
                )
            try:
                trigger = copy.deepcopy(dict(prepared_request.trigger))
                developer_mode = trigger.pop("developer_mode", False)
                if not isinstance(developer_mode, bool):
                    raise TypeError("developer_mode must be a boolean")
                catalog_fingerprint, catalog_revisions = catalog_agreement(
                    candidate_registry.data_types
                )
                plugin_fingerprint = candidate_registry.plugin_fingerprint()
                registry_fingerprint = candidate_registry.contract_fingerprint()
                trigger_publication_generations = tuple(
                    sorted(
                        (
                            node_id,
                            (
                                reserved_trigger_generation
                                if node_id == prepared_request.clicked_trigger_node_id
                                and reserved_trigger_generation is not None
                                else self._solution_store.trigger_generation(
                                    project_id,
                                    workspace.workspace_id,
                                    node_id,
                                )
                            ),
                        )
                        for node_id in plan.nodes
                        if plan.is_trigger(node_id)
                    )
                )
                envelope = PreparedDispatchEnvelope(
                    project_path=str(prepared_request.project_path),
                    project_id=project_id,
                    workspace_id=workspace.workspace_id,
                    trigger=trigger,
                    runtime_snapshot=runtime_snapshot,
                    execution_backend=selection,
                    target_node_ids=plan.target_nodes,
                    clicked_trigger_node_id=prepared_request.clicked_trigger_node_id,
                    trigger_capture_node_ids=tuple(
                        sorted(prepared_request.trigger_captures)
                    ),
                    trigger_publications=prepared_request.trigger_publications,
                    trigger_captures=prepared_request.trigger_captures,
                    recompute_mode=prepared_request.recompute_mode,
                    developer_mode=developer_mode,
                    catalog_fingerprint=catalog_fingerprint,
                    catalog_revisions=catalog_revisions,
                    plugin_bundles=candidate_registry.plugin_bundle_refs(),
                    plugin_fingerprint=plugin_fingerprint,
                    runtime_registry_fingerprint=runtime_registry_fingerprint(
                        catalog_fingerprint,
                        plugin_fingerprint,
                    ),
                    registry_contract_fingerprint=registry_fingerprint,
                    addon_runtime_config=candidate_registry.addon_runtime_config(),
                    catalog=candidate_registry.data_types,
                )
                decisions, accepted, captures = self._prepare_node_decisions(
                    preparation_id=preparation_id,
                    namespace_id=namespace_id,
                    project_id=project_id,
                    plan=plan,
                    registry=candidate_registry,
                    generation_snapshot=generation_snapshot,
                    recompute_mode=RecomputeMode(prepared_request.recompute_mode),
                    trigger_publication_generations=dict(
                        trigger_publication_generations
                    ),
                    workflow_interface_revision=(
                        interface_plan.workflow_interface_revision
                    ),
                    workflow_interface_digest=(
                        interface_plan.workflow_interface_digest
                    ),
                    artifact_service=RuntimeArtifactService(
                        runtime_context=RuntimeSnapshotContext.from_snapshot(
                            runtime_snapshot,
                            project_path=prepared_request.project_path,
                        ),
                        data_types=candidate_registry.data_types,
                    ),
                )
                prepared = PreparedExecution(
                    preparation_id=preparation_id,
                    dispatch_envelope=envelope,
                    solution_namespace_id=namespace_id,
                    execution_affecting_workspace_revision=(
                        self._solution_store.workspace_revision(
                            project_id,
                            workspace.workspace_id,
                        )
                    ),
                    runtime_snapshot_fingerprint=canonical_digest(
                        runtime_snapshot.to_document(
                            catalog=candidate_registry.data_types
                        )
                    ),
                    execution_plan_fingerprint=plan.fingerprint,
                    registry_contract_fingerprint=registry_fingerprint,
                    workflow_interface_revision=(
                        interface_plan.workflow_interface_revision
                    ),
                    workflow_interface_digest=(
                        interface_plan.workflow_interface_digest
                    ),
                    execution_environment_digest=generation_snapshot.environment_digest,
                    trigger_publication_generations=(
                        trigger_publication_generations
                    ),
                    node_decisions=decisions,
                    accepted_output_payloads=accepted,
                    recompute_node_ids=tuple(
                        item.node_id
                        for item in decisions
                        if item.action is PreparedAction.EXECUTE
                    ),
                    reused_node_ids=tuple(
                        item.node_id
                        for item in decisions
                        if item.action is PreparedAction.REUSE
                    ),
                )
                encoded_size = len(
                    json.dumps(
                        prepared.to_payload(catalog=candidate_registry.data_types),
                        allow_nan=False,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                )
                self._solution_store.register_preparation(
                    prepared,
                    candidate_registry=candidate_registry,
                    plan=plan,
                    captured_nodes=captures,
                    generation_snapshot=generation_snapshot,
                    encoded_size=encoded_size,
                    trigger_reservation_id=trigger_reservation_id,
                )
                return prepared
            except Exception:
                self._solution_store.release_trigger_reservation(
                    trigger_reservation_id
                )
                raise

    def _prepare_candidate_request(
        self,
        request: ExecutionRequest,
    ) -> tuple[ExecutionRequest, NodeRegistry]:
        trigger, raw_snapshot, execution_backend = (
            request.trigger_without_runtime_snapshot()
        )
        candidate_registry = self._registry
        if raw_snapshot is not None and candidate_registry is None:
            raise ValueError(
                "raw runtime snapshots require an authoritative node registry"
            )
        catalog = (
            candidate_registry.data_types if candidate_registry is not None else None
        )
        runtime_snapshot = coerce_runtime_snapshot(raw_snapshot, catalog=catalog)
        workspace_id = str(request.workspace_id or "").strip()
        project_path = str(request.project_path or "").strip()
        if runtime_snapshot is None:
            loaded_project = load_project(
                project_path,
                registry=candidate_registry,
            )
            candidate_registry = loaded_project.registry
            workspace = loaded_project.select_workspace(
                WorkspaceSelection(workspace_id)
            )
            runtime_snapshot = build_runtime_snapshot(
                loaded_project.project,
                workspace_id=workspace.workspace_id,
                registry=candidate_registry,
            )
            workspace_id = workspace.workspace_id
            project_path = str(loaded_project.project_path)
        else:
            assert candidate_registry is not None
            if not workspace_id:
                workspace_id = str(runtime_snapshot.active_workspace_id).strip()
            runtime_snapshot.workspace(workspace_id)
        assert candidate_registry is not None
        return (
            ExecutionRequest(
                project_path=project_path,
                workspace_id=workspace_id,
                trigger=trigger,
                runtime_snapshot=runtime_snapshot,
                execution_backend=execution_backend,
                target_node_ids=tuple(request.target_node_ids),
                trigger_publications=dict(request.trigger_publications),
                trigger_captures=dict(request.trigger_captures),
                clicked_trigger_node_id=str(request.clicked_trigger_node_id),
                recompute_mode=request.recompute_mode,
            ),
            candidate_registry,
        )

    def _prepare_node_decisions(
        self,
        *,
        preparation_id: str,
        namespace_id: str,
        project_id: str,
        plan: ExecutionPlan,
        registry: NodeRegistry,
        generation_snapshot: Any,
        recompute_mode: RecomputeMode,
        trigger_publication_generations: Mapping[str, int],
        workflow_interface_revision: int,
        workflow_interface_digest: str,
        artifact_service: RuntimeArtifactService,
    ) -> tuple[
        tuple[PreparedNodeDecision, ...],
        tuple[Any, ...],
        tuple[CapturedNodeSolution, ...],
    ]:
        workspace_id = plan.workspace.workspace_id
        solution_revision = self._solution_store.workspace_revision(
            project_id,
            workspace_id,
        )
        decisions: list[PreparedNodeDecision] = []
        accepted: list[Any] = []
        captures: list[CapturedNodeSolution] = []
        keys_by_node: dict[str, str] = {}
        actions_by_node: dict[str, PreparedAction] = {}
        accepted_port_count = 0
        accepted_payload_bytes = 0
        for node_id in plan.execution_order:
            spec = plan.node_specs[node_id]
            if spec.runtime_behavior != "active":
                continue
            capture, identity_reason = self._captured_node_solution(
                preparation_id=preparation_id,
                namespace_id=namespace_id,
                project_id=project_id,
                plan=plan,
                registry=registry,
                node_id=node_id,
                keys_by_node=keys_by_node,
                generation_snapshot=generation_snapshot,
                solution_revision=solution_revision,
                trigger_publication_generations=trigger_publication_generations,
                workflow_interface_revision=workflow_interface_revision,
                workflow_interface_digest=workflow_interface_digest,
            )
            keys_by_node[node_id] = capture.solution_key
            captures.append(capture)
            upstream_execute = any(
                actions_by_node.get(edge.source_node_id) is PreparedAction.EXECUTE
                for edge in plan.incoming_edges_for(node_id)
                if not plan.is_trigger(edge.source_node_id)
            ) or any(
                target == node_id
                and actions_by_node.get(source) is PreparedAction.EXECUTE
                for source, target in plan.hidden_ordering_pairs
            )
            reason = identity_reason
            action = PreparedAction.EXECUTE
            record_id: str | None = None
            output_payload = None
            if recompute_mode is RecomputeMode.FORCE_RECOMPUTE:
                reason = "force_recompute"
            elif reason:
                pass
            elif spec.solution_reuse_scope == "never":
                reason = "solution_reuse_scope_never"
            elif not generation_snapshot.available:
                reason = generation_snapshot.reason or "execution_generation_unavailable"
            elif upstream_execute:
                reason = "upstream_recompute_required"
            else:
                record = self._solution_store.select_record(
                    solution_key=capture.solution_key,
                    project_id=project_id,
                    workspace_id=workspace_id,
                    node_id=node_id,
                    runtime_generation=generation_snapshot.runtime_generation,
                )
                if record is None:
                    reason = "no_reusable_record"
                else:
                    try:
                        output_payload = self._solution_store.accepted_outputs(
                            record.record_id,
                            catalog=registry.data_types,
                            runtime_generation=generation_snapshot.runtime_generation,
                        )
                        self._validate_prepared_artifacts(
                            output_payload,
                            artifact_service=artifact_service,
                            catalog=registry.data_types,
                        )
                    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
                        reason = "accepted_output_invalid"
                    else:
                        payload_bytes = len(
                            json.dumps(
                                output_payload.to_payload(catalog=registry.data_types),
                                allow_nan=False,
                                ensure_ascii=False,
                                separators=(",", ":"),
                                sort_keys=True,
                            ).encode("utf-8")
                        )
                        if (
                            len(accepted) + 1
                            > MAX_ACCEPTED_NODE_PAYLOADS_PER_PREPARATION
                            or accepted_port_count + output_payload.output_count
                            > MAX_ACCEPTED_PORT_RESULTS_PER_PREPARATION
                            or accepted_payload_bytes + payload_bytes
                            > MAX_ACCEPTED_OUTPUT_PAYLOAD_BYTES
                        ):
                            reason = "reuse_payload_budget_exceeded"
                            output_payload = None
                        else:
                            action = PreparedAction.REUSE
                            reason = "reusable_record_accepted"
                            record_id = record.record_id
                            accepted.append(output_payload)
                            accepted_port_count += output_payload.output_count
                            accepted_payload_bytes += payload_bytes
            actions_by_node[node_id] = action
            decisions.append(
                PreparedNodeDecision(
                    node_id=node_id,
                    action=action,
                    reason_code=reason,
                    solution_key=capture.solution_key,
                    dependency_solution_keys=capture.dependency_solution_keys,
                    accepted_record_id=record_id,
                )
            )
        return tuple(decisions), tuple(accepted), tuple(captures)

    @staticmethod
    def _validate_prepared_artifacts(
        payload: Any,
        *,
        artifact_service: RuntimeArtifactService,
        catalog: Any,
    ) -> None:
        def validate(value: Any) -> None:
            if isinstance(value, RuntimeArtifactRef):
                artifact_service.resolve_path(value)
                return
            if isinstance(value, DataTree):
                for _path, items in value.branches:
                    for item in items:
                        validate(item)
                return
            if isinstance(value, Mapping):
                for item in value.values():
                    validate(item)
                return
            if isinstance(value, Sequence) and not isinstance(
                value,
                (str, bytes, bytearray),
            ):
                for item in value:
                    validate(item)

        for result in payload.decode_outputs(catalog=catalog).values():
            if result.status == "value":
                validate(result.value)

    def _captured_node_solution(
        self,
        *,
        preparation_id: str,
        namespace_id: str,
        project_id: str,
        plan: ExecutionPlan,
        registry: NodeRegistry,
        node_id: str,
        keys_by_node: Mapping[str, str],
        generation_snapshot: Any,
        solution_revision: int,
        trigger_publication_generations: Mapping[str, int],
        workflow_interface_revision: int,
        workflow_interface_digest: str,
    ) -> tuple[CapturedNodeSolution, str]:
        spec = plan.node_specs[node_id]
        assembled = assemble_node_solution(
            preparation_id=preparation_id,
            solution_namespace_id=namespace_id,
            workspace_solution_revision=solution_revision,
            plan=plan,
            registry=registry,
            node_id=node_id,
            keys_by_node=keys_by_node,
            execution_environment_digest=generation_snapshot.environment_digest,
            trigger_publication_generations=trigger_publication_generations,
            workflow_interface_revision=workflow_interface_revision,
            workflow_interface_digest=workflow_interface_digest,
        )
        return (
            CapturedNodeSolution(
                node_id=node_id,
                solution_key=assembled.solution_key,
                captured_revision=self._solution_store.node_revision(
                    project_id,
                    plan.workspace.workspace_id,
                    node_id,
                ),
                dependency_solution_keys=assembled.dependency_solution_keys,
                workflow_interface_revision=assembled.workflow_interface_revision,
                workflow_interface_digest=assembled.workflow_interface_digest,
                node_contract_digest=assembled.node_contract_digest,
                input_provenance_digest=assembled.input_provenance_digest,
                execution_policy_digest=assembled.execution_policy_digest,
                implementation_digest=assembled.implementation_digest,
                execution_environment_digest=generation_snapshot.environment_digest,
                output_specs=assembled.output_specs,
                reuse_eligible=(
                    not assembled.reason_code
                    and generation_snapshot.available
                    and spec.solution_reuse_scope != "never"
                ),
            ),
            assembled.reason_code,
        )

    def dispatch_prepared(self, prepared: PreparedExecution) -> str:
        if not isinstance(prepared, PreparedExecution):
            raise TypeError("prepared must be a PreparedExecution")
        solution_events: list[InvalidationResult] = []
        reservation: Any | None = None
        command: Any | None = None
        candidate_fingerprint = ""
        dispatch_workspace_revision = -1
        preparation_validated = False
        try:
            with self._lifecycle_lock, self.registry_publication_guard():
                entry = self._solution_store.preparation(prepared.preparation_id)
                if entry.prepared != prepared:
                    raise ValueError("prepared execution does not match registered state")
                preparation_validated = True
                candidate_registry = entry.candidate_registry
                previous_fingerprint = (
                    self._registry.contract_fingerprint()
                    if self._registry is not None
                    else ""
                )
                candidate_fingerprint = candidate_registry.contract_fingerprint()
                replace_client_registry = getattr(self._client, "replace_registry", None)
                if callable(replace_client_registry):
                    replace_client_registry(candidate_registry)
                self._registry = candidate_registry
                if previous_fingerprint and previous_fingerprint != candidate_fingerprint:
                    self._release_all_solution_resources()
                    solution_events.extend(
                        self._solution_store.adopt_expected_generation(
                            prepared.preparation_id,
                            "registry_generation_replaced",
                        )
                    )
                    self._run_artifact_services.clear()
                pre_reservation_snapshot = self._client.execution_generation_snapshot(
                    prepared.dispatch_envelope.execution_backend,
                    registry_contract_fingerprint=candidate_fingerprint,
                )
                if (
                    entry.generation_snapshot.available
                    and not pre_reservation_snapshot.compatible_with(
                        entry.generation_snapshot
                    )
                ):
                    raise ValueError("prepared_runtime_generation_changed")
                reservation = self._client.reserve_run(
                    prepared.dispatch_envelope.execution_backend,
                    prepared.dispatch_envelope.workspace_id,
                )
                if (
                    entry.generation_snapshot.available
                    and not reservation.generation_snapshot.compatible_with(
                        entry.generation_snapshot
                    )
                ):
                    raise ValueError("prepared_runtime_generation_changed")
                self._validate_prepared_dispatch(
                    prepared,
                    entry=entry,
                    generation_snapshot=reservation.generation_snapshot,
                )
                if not entry.generation_snapshot.available:
                    self._release_all_solution_resources()
                    solution_events.extend(
                        self._solution_store.adopt_expected_generation(
                            prepared.preparation_id,
                            "runtime_generation_replaced",
                        )
                    )
                    self._solution_store.adopt_preparation_generation(
                        prepared.preparation_id,
                        reservation.generation_snapshot,
                    )
                    self._run_artifact_services.clear()
                self._generation_snapshots[
                    reservation.selection.backend_id
                ] = reservation.generation_snapshot
                runtime_snapshot = prepared.dispatch_envelope.decode_runtime_snapshot(
                    catalog=candidate_registry.data_types
                )
                self._run_artifact_services[reservation.run_id] = RuntimeArtifactService(
                    runtime_context=RuntimeSnapshotContext.from_snapshot(
                        runtime_snapshot,
                        project_path=prepared.dispatch_envelope.project_path,
                    ),
                    data_types=candidate_registry.data_types,
                )
                self._solution_store.consume_preparation(
                    prepared.preparation_id,
                    run_id=reservation.run_id,
                    generation_snapshot=reservation.generation_snapshot,
                )
                envelope = prepared.dispatch_envelope
                command = coerce_start_run_command(
                    StartRunCommand(
                        run_id=reservation.run_id,
                        project_path=envelope.project_path,
                        workspace_id=envelope.workspace_id,
                        trigger=envelope.decode_trigger(catalog=candidate_registry.data_types),
                        runtime_snapshot=runtime_snapshot,
                        execution_backend=envelope.execution_backend,
                        target_node_ids=envelope.target_node_ids,
                        trigger_publications=envelope.decode_trigger_publications(
                            catalog=candidate_registry.data_types
                        ),
                        trigger_captures=envelope.decode_trigger_captures(
                            catalog=candidate_registry.data_types
                        ),
                        clicked_trigger_node_id=envelope.clicked_trigger_node_id,
                        developer_mode=envelope.developer_mode,
                        catalog_fingerprint=envelope.catalog_fingerprint,
                        catalog_revisions=envelope.catalog_revisions,
                        plugin_bundles=envelope.plugin_bundles,
                        plugin_fingerprint=envelope.plugin_fingerprint,
                        runtime_registry_fingerprint=envelope.runtime_registry_fingerprint,
                        registry_contract_fingerprint=envelope.registry_contract_fingerprint,
                        addon_runtime_config=envelope.addon_runtime_config,
                        preparation_id=prepared.preparation_id,
                        solution_namespace_id=prepared.solution_namespace_id,
                        execution_affecting_workspace_revision=(
                            prepared.execution_affecting_workspace_revision
                        ),
                        dispatch_runtime_generation=(
                            reservation.generation_snapshot.runtime_generation
                        ),
                        runtime_snapshot_fingerprint=prepared.runtime_snapshot_fingerprint,
                        execution_plan_fingerprint=prepared.execution_plan_fingerprint,
                        workflow_interface_revision=prepared.workflow_interface_revision,
                        workflow_interface_digest=prepared.workflow_interface_digest,
                        execution_environment_digest=prepared.execution_environment_digest,
                        trigger_publication_generations=(
                            prepared.trigger_publication_generations
                        ),
                        node_decisions=prepared.node_decisions,
                        accepted_output_payloads=prepared.accepted_output_payloads,
                    ),
                    catalog=candidate_registry.data_types,
                )
                dispatch_workspace_revision = self._solution_store.workspace_revision(
                    envelope.project_id,
                    envelope.workspace_id,
                )
        except Exception:
            if reservation is not None:
                with self._lifecycle_lock, self.registry_publication_guard():
                    self._solution_store.release_run(
                        reservation.run_id,
                        "dispatch_preparation_failed",
                    )
                    self._run_artifact_services.pop(reservation.run_id, None)
                    self._solution_store.discard_preparation(
                        prepared.preparation_id,
                        "prepared_dispatch_failed",
                    )
                    self._client.release_run_reservation(
                        reservation,
                        "dispatch_preparation_failed",
                    )
            elif preparation_validated:
                self._solution_store.discard_preparation(
                    prepared.preparation_id,
                    "prepared_dispatch_failed",
                )
            self._publish_solution_state_results(solution_events)
            raise

        self._publish_solution_state_results(solution_events)
        assert reservation is not None and command is not None
        started = False
        try:
            with self._lifecycle_lock, self.registry_publication_guard():
                envelope = prepared.dispatch_envelope
                current_generation = self._client.execution_generation_snapshot(
                    reservation.selection,
                    registry_contract_fingerprint=candidate_fingerprint,
                )
                if (
                    self._solution_store.workspace_revision(
                        envelope.project_id,
                        envelope.workspace_id,
                    )
                    != dispatch_workspace_revision
                    or not current_generation.compatible_with(
                        reservation.generation_snapshot
                    )
                ):
                    raise ValueError("prepared_dispatch_changed_before_start")
                started = True
                run_id = self._client.start_reserved_run(reservation, command)
                if run_id == reservation.run_id:
                    return run_id
        except Exception:
            reason = "start_failed" if started else "dispatch_changed_before_start"
            with self._lifecycle_lock, self.registry_publication_guard():
                self._solution_store.release_run(reservation.run_id, reason)
                self._run_artifact_services.pop(reservation.run_id, None)
                self._client.release_run_reservation(reservation, reason)
            raise

        with self._lifecycle_lock, self.registry_publication_guard():
            self._solution_store.release_run(reservation.run_id, "start_failed")
            self._run_artifact_services.pop(reservation.run_id, None)
            self._client.release_run_reservation(reservation, "start_failed")
        return ""

    def _validate_prepared_dispatch(
        self,
        prepared: PreparedExecution,
        *,
        entry: Any,
        generation_snapshot: Any,
    ) -> None:
        registry = entry.candidate_registry
        envelope = prepared.dispatch_envelope
        if registry.contract_fingerprint() != prepared.registry_contract_fingerprint:
            raise ValueError("prepared_registry_contract_changed")
        if not generation_snapshot.route_compatible_with(
            envelope.execution_backend
        ):
            raise ValueError("prepared_backend_route_changed")
        if not generation_snapshot.available:
            raise ValueError("prepared_runtime_generation_unavailable")
        if (
            entry.generation_snapshot.available
            and generation_snapshot.environment_digest
            != prepared.execution_environment_digest
        ):
            raise ValueError("prepared_execution_environment_changed")
        workspace_revision = self._solution_store.workspace_revision(
            envelope.project_id,
            envelope.workspace_id,
        )
        if (
            workspace_revision != prepared.execution_affecting_workspace_revision
            and entry.adopted_workspace_revision != workspace_revision
        ):
            raise ValueError("prepared_workspace_revision_changed")
        snapshot = envelope.decode_runtime_snapshot(catalog=registry.data_types)
        if (
            canonical_digest(snapshot.to_document(catalog=registry.data_types))
            != prepared.runtime_snapshot_fingerprint
        ):
            raise ValueError("prepared_runtime_snapshot_changed")
        plan = ExecutionPlan(
            snapshot.workspace(envelope.workspace_id),
            registry,
            target_node_ids=envelope.target_node_ids,
            clicked_trigger_node_id=envelope.clicked_trigger_node_id,
            trigger_capture_node_ids=envelope.trigger_capture_node_ids,
        )
        if plan.fingerprint != prepared.execution_plan_fingerprint:
            raise ValueError("prepared_execution_plan_changed")

    def invalidate_solution(
        self,
        project_id: str,
        workspace_id: str,
        runtime_snapshot: RuntimeSnapshot | Mapping[str, Any],
        changed_root_node_ids: Sequence[str],
        reason_code: str,
    ) -> InvalidationResult:
        released_leases: tuple[Any, ...] = ()
        with self._lifecycle_lock:
            registry = self._registry
            if registry is None:
                raise ValueError(
                    "solution invalidation requires an authoritative registry"
                )
            snapshot = coerce_runtime_snapshot(
                runtime_snapshot,
                catalog=registry.data_types,
            )
            if snapshot is None or snapshot.project_id != str(project_id).strip():
                raise ValueError("runtime snapshot project does not match project_id")
            workspace = snapshot.workspace(str(workspace_id).strip())
            self._solution_store.ensure_project(str(project_id).strip())
            plan = ExecutionPlan(workspace, registry)
            result, released_leases = self._solution_store.invalidate(
                project_id=str(project_id).strip(),
                workspace_id=workspace.workspace_id,
                plan=plan,
                changed_root_node_ids=changed_root_node_ids,
                reason_code=str(reason_code).strip(),
            )
        self._release_resource_leases(released_leases)
        self._publish_solution_state_results((result,))
        return result

    def solution_facts(
        self,
        project_id: str,
        workspace_id: str,
    ) -> tuple[NodeSolutionFact, ...]:
        return self._solution_store.facts(
            str(project_id).strip(),
            str(workspace_id).strip(),
        )

    def expired_node_ids(
        self,
        project_id: str,
        workspace_id: str,
    ) -> tuple[str, ...]:
        return self._solution_store.expired_node_ids(
            str(project_id).strip(),
            str(workspace_id).strip(),
        )

    def solution_record(self, record_id: str) -> SolutionRecord | None:
        return self._solution_store.record(record_id)

    def reset_project_session(self, project_id: str, project_path: str = "") -> str:
        with self._lifecycle_lock:
            self._generation_snapshots.clear()
            self._run_artifact_services.clear()
            self._release_all_solution_resources()
            namespace_id, solution_events = self._solution_store.reset_project_session(
                project_id,
                project_path,
            )
        self._publish_solution_state_results(solution_events)
        return namespace_id

    def _release_resource_leases(self, leases: Sequence[Any]) -> None:
        release = getattr(self._client, "release_solution_resource", None)
        if not callable(release):
            return
        for lease in leases:
            release(lease)

    def _release_all_solution_resources(self) -> None:
        self._release_resource_leases(
            self._solution_store.take_all_resource_leases()
        )

    def _validated_event_resources(
        self,
        event: Mapping[str, Any],
    ) -> tuple[dict[str, Any], bool, tuple[Any, ...]]:
        payload = dict(event)
        if str(payload.get("type", "")) != "node_settled" or self._registry is None:
            return payload, True, ()
        raw_outputs = payload.get("outputs", {})
        try:
            if isinstance(raw_outputs, Mapping) and all(
                isinstance(value, SettledPortResult)
                for value in raw_outputs.values()
            ):
                outputs = dict(raw_outputs)
            else:
                outputs = settled_output_mapping_from_payload(
                    raw_outputs,
                    catalog=self._registry.data_types,
                )
        except (TypeError, ValueError):
            return payload, False, ()
        run_id = str(payload.get("run_id", "")).strip()
        node_id = str(payload.get("node_id", "")).strip()
        owner_scope = f"solution:{run_id}:{node_id}:{uuid.uuid4().hex}"
        artifact_service = self._run_artifact_services.get(run_id)
        lease_resource = getattr(self._client, "lease_solution_resource", None)
        leases: list[Any] = []
        reused_event = str(payload.get("disposition", "")).strip() == "reused"

        def validate(value: Any) -> Any:
            if isinstance(value, RuntimeArtifactRef):
                if artifact_service is None:
                    raise ValueError("artifact resolver is unavailable")
                artifact_service.resolve_path(value)
                return value
            if isinstance(
                value,
                (
                    RuntimeHandleRef,
                    ArrayDataRef,
                    ArraySlice2DRef,
                    TabularDataRef,
                    TabularWindowRef,
                ),
            ):
                if not callable(lease_resource):
                    raise ValueError("session resource resolver is unavailable")
                leased = lease_resource(
                    run_id,
                    value,
                    owner_scope=owner_scope,
                )
                if leased is None:
                    raise ValueError("session resource is not live")
                normalized, lease = leased
                leases.append(lease)
                return value if reused_event else normalized
            if isinstance(value, DataTree):
                return DataTree(
                    (
                        path,
                        tuple(validate(item) for item in items),
                    )
                    for path, items in value.branches
                )
            if isinstance(value, Mapping):
                return {key: validate(item) for key, item in value.items()}
            if isinstance(value, tuple):
                return tuple(validate(item) for item in value)
            if isinstance(value, list):
                return [validate(item) for item in value]
            return value

        try:
            normalized_outputs = {
                port_key: replace(
                    result,
                    value=(
                        validate(result.value)
                        if result.status == "value"
                        else result.value
                    ),
                )
                for port_key, result in outputs.items()
            }
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
            self._release_resource_leases(leases)
            return payload, False, ()
        payload["outputs"] = normalized_outputs
        return payload, True, tuple(leases)

    def _handle_generation_event(
        self,
        event: Mapping[str, Any],
        generation_snapshot: Any,
    ) -> None:
        backend_id = generation_snapshot.selection.backend_id
        solution_events: tuple[InvalidationResult, ...] = ()
        diagnostics: tuple[dict[str, Any], ...] = ()
        enriched_event = dict(event)
        with self._lifecycle_lock:
            previous = self._generation_snapshots.get(backend_id)
            if previous is not None and not previous.compatible_with(
                generation_snapshot
            ):
                self._release_all_solution_resources()
                solution_events = self._solution_store.reset_runtime_generation(
                    "runtime_generation_replaced"
                )
                self._run_artifact_services.clear()
            self._generation_snapshots[backend_id] = generation_snapshot
            if self._registry is None:
                return
            validated_event, resources_reusable, resource_leases = (
                self._validated_event_resources(event)
            )
            diagnostics, released_leases, acceptance = self._solution_store.handle_event(
                validated_event,
                generation_snapshot,
                catalog=self._registry.data_types,
                resources_reusable=resources_reusable,
                resource_leases=resource_leases,
            )
            enriched_event = dict(validated_event)
            if str(enriched_event.get("type", "")) == "node_settled":
                enriched_event["accepted_solution_record"] = acceptance is not None
                enriched_event["record_id"] = (
                    acceptance.record_id if acceptance is not None else ""
                )
                enriched_event["result_digest"] = (
                    acceptance.result_digest if acceptance is not None else ""
                )
                if acceptance is not None:
                    enriched_event["solution_key"] = acceptance.solution_key
                    enriched_event["disposition"] = acceptance.disposition.value
                    enriched_event["solution_fact_revision"] = acceptance.fact_revision
            self._release_resource_leases(released_leases)
            if str(event.get("type", "")) in TERMINAL_EVENT_TYPES:
                self._run_artifact_services.pop(
                    str(event.get("run_id", "")).strip(),
                    None,
                )
        self._publish_solution_state_results(solution_events)
        if str(event.get("type", "")) != "execution_generation_changed":
            self._event_stream.publish(enriched_event)
        self._generation_event_local.forwarded = dict(event)
        for diagnostic in diagnostics:
            self._event_stream.publish(diagnostic)

    def _handle_client_event(self, event: Mapping[str, Any]) -> None:
        forwarded = getattr(self._generation_event_local, "forwarded", None)
        if isinstance(forwarded, Mapping) and dict(event) == dict(forwarded):
            self._generation_event_local.forwarded = None
            return
        self._event_stream.publish(dict(event))

    def _publish_solution_state_results(
        self, results: Sequence[InvalidationResult]
    ) -> None:
        for result in results:
            self._event_stream.publish(
                SolutionStateChangedEvent.from_invalidation(result).to_payload()
            )

    def start(self, request: ExecutionRequest) -> str:
        return self.dispatch_prepared(self.prepare_execution(request))

    def run(
        self,
        request: ExecutionRequest,
        *,
        timeout: float | None = None,
        on_event: ExecutionEventCallback | None = None,
    ) -> ExecutionResult:
        condition = threading.Condition()
        events: list[ExecutionEvent] = []
        terminal_event: ExecutionEvent | None = None
        run_id_holder = {"run_id": ""}

        def _capture(event: ExecutionEvent) -> None:
            nonlocal terminal_event
            event_type = str(event.get("type", ""))
            event_run_id = str(event.get("run_id", ""))
            active_run_id = run_id_holder["run_id"]
            if (
                active_run_id
                and event_type in RUN_SCOPED_EVENT_TYPES
                and event_run_id
                and event_run_id != active_run_id
            ):
                return
            payload = copy.deepcopy(dict(event))
            with condition:
                events.append(payload)
                if (
                    active_run_id
                    and event_type in TERMINAL_EVENT_TYPES
                    and event_run_id == active_run_id
                ):
                    terminal_event = payload
                condition.notify_all()
            if on_event is not None:
                on_event(copy.deepcopy(payload))

        unsubscribe = self.subscribe(_capture)
        try:
            prepared = self.prepare_execution(request)
            workspace_id = prepared.dispatch_envelope.workspace_id
            run_id = self.dispatch_prepared(prepared)
            run_id_holder["run_id"] = run_id
            if not run_id:
                terminal_event = self._start_failure_event(
                    events, workspace_id
                )
                return self._result_from_terminal(
                    run_id="",
                    workspace_id=workspace_id,
                    terminal_event=terminal_event,
                    events=events,
                )

            with condition:
                terminal_event = self._terminal_event_for_run(events, run_id)
            deadline = time.monotonic() + timeout if timeout is not None else None
            with condition:
                while terminal_event is None:
                    if deadline is None:
                        condition.wait(timeout=0.2)
                        continue
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    condition.wait(timeout=min(remaining, 0.2))

            if terminal_event is None:
                self.cancel(CancellationRequest(run_id=run_id, reason="timeout"))
                terminal_event = {
                    "type": "run_timeout",
                    "run_id": run_id,
                    "workspace_id": workspace_id,
                    "reason": "timeout",
                }
                with condition:
                    events.append(copy.deepcopy(terminal_event))

            return self._result_from_terminal(
                run_id=run_id,
                workspace_id=workspace_id,
                terminal_event=terminal_event,
                events=events,
            )
        finally:
            unsubscribe()

    def cancel(self, request: CancellationRequest) -> None:
        if request.run_id:
            self.stop_run(request.run_id)

    def pause_run(self, run_id: str) -> None:
        self._client.pause_run(run_id)

    def resume_run(self, run_id: str) -> None:
        self._client.resume_run(run_id)

    def stop_run(self, run_id: str) -> None:
        self._client.stop_run(run_id)

    def open_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        with self.registry_publication_guard():
            return self._client.open_viewer_session(*args, **kwargs)

    def update_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        return self._client.update_viewer_session(*args, **kwargs)

    def close_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        return self._client.close_viewer_session(*args, **kwargs)

    def materialize_viewer_data(self, *args: Any, **kwargs: Any) -> str:
        return self._client.materialize_viewer_data(*args, **kwargs)

    def shutdown(self) -> None:
        with self._lifecycle_lock:
            self._release_all_solution_resources()
            self._run_artifact_services.clear()
            self._solution_store.shutdown()
            if self._owns_client:
                self._client.shutdown()

    @staticmethod
    def _start_failure_event(
        events: list[ExecutionEvent], workspace_id: str
    ) -> ExecutionEvent:
        for event in reversed(events):
            if str(event.get("type", "")) == "protocol_error":
                return copy.deepcopy(event)
        return {
            "type": "run_failed",
            "run_id": "",
            "workspace_id": workspace_id,
            "error": "Execution client did not start a run.",
            "traceback": "",
        }

    @staticmethod
    def _terminal_event_for_run(
        events: list[ExecutionEvent], run_id: str
    ) -> ExecutionEvent | None:
        for event in events:
            if (
                str(event.get("type", "")) in TERMINAL_EVENT_TYPES
                and str(event.get("run_id", "")) == run_id
            ):
                return copy.deepcopy(event)
        return None

    @staticmethod
    def _result_from_terminal(
        *,
        run_id: str,
        workspace_id: str,
        terminal_event: ExecutionEvent,
        events: list[ExecutionEvent],
    ) -> ExecutionResult:
        event_type = str(terminal_event.get("type", ""))
        if event_type == "run_completed":
            status: ExecutionStatus = "completed"
        elif event_type == "run_stopped":
            status = "stopped"
        elif event_type == "run_timeout":
            status = "timeout"
        else:
            status = "failed"
        return ExecutionResult(
            run_id=str(terminal_event.get("run_id") or run_id),
            workspace_id=str(terminal_event.get("workspace_id") or workspace_id),
            status=status,
            events=tuple(copy.deepcopy(event) for event in events),
            terminal_event=copy.deepcopy(terminal_event),
            error=str(terminal_event.get("error", "")),
            traceback=str(terminal_event.get("traceback", "")),
        )


def _format_text_event(event: Mapping[str, Any]) -> str:
    parts = [
        f"type={event.get('type', '')}",
        f"run_id={event.get('run_id', '')}",
        f"workspace_id={event.get('workspace_id', '')}",
    ]
    node_id = str(event.get("node_id", ""))
    if node_id:
        parts.append(f"node_id={node_id}")
    message = str(event.get("message", "") or event.get("error", ""))
    if message:
        parts.append(f"message={message}")
    return "event " + " ".join(parts)


def _emit_cli_record(record: Mapping[str, Any], *, output_format: str) -> None:
    if output_format == "json":
        print(
            json.dumps(copy.deepcopy(dict(record)), sort_keys=True, ensure_ascii=True)
        )
        return
    record_type = str(record.get("record", ""))
    if record_type == "event":
        print(_format_text_event(dict(record.get("event", {}))))
    elif record_type == "result":
        result = dict(record.get("result", {}))
        print(
            "result "
            f"status={result.get('status', '')} "
            f"run_id={result.get('run_id', '')} "
            f"workspace_id={result.get('workspace_id', '')}"
        )
    else:
        print("error " + str(record.get("error", "")))


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="corex-runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run a Corex workspace without Qt.")
    run_parser.add_argument("project", help="Path to the .cxproj project.")
    run_parser.add_argument(
        "--workspace",
        "-w",
        default="",
        help="Workspace id to run. Defaults to the project's active workspace.",
    )
    run_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format for streamed events and the final result.",
    )
    run_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Maximum seconds to wait before requesting cancellation.",
    )
    run_parser.add_argument(
        "--execution-backend",
        choices=(PROCESS_ISOLATED_BACKEND, TRUSTED_IN_PROCESS_BACKEND),
        default=PROCESS_ISOLATED_BACKEND,
        help="Execution backend. Process isolation remains the default.",
    )
    run_parser.add_argument(
        "--trust-in-process",
        action="store_true",
        help="Required opt-in when --execution-backend=trusted_in_process.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.command != "run":
        return 2

    runtime = CorexRuntime()
    try:
        result = runtime.run(
            ExecutionRequest(
                project_path=args.project,
                workspace_id=args.workspace,
                trigger={"kind": "headless_cli"},
                execution_backend=ExecutionBackendPolicy(
                    requested_backend=args.execution_backend,
                    allow_trusted_in_process=bool(args.trust_in_process),
                    reason="headless_cli",
                ),
            ),
            timeout=args.timeout,
            on_event=lambda event: _emit_cli_record(
                {"record": "event", "event": event},
                output_format=args.format,
            ),
        )
        _emit_cli_record(
            {"record": "result", "result": result.to_dict()},
            output_format=args.format,
        )
        return 0 if result.status == "completed" else 1
    except Exception as exc:  # noqa: BLE001
        _emit_cli_record(
            {"record": "error", "error": str(exc)},
            output_format=getattr(args, "format", "json"),
        )
        return 2
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


__all__ = [
    "CancellationRequest",
    "CorexRuntime",
    "ExecutionEvent",
    "ExecutionEventCallback",
    "ExecutionEventStream",
    "ExecutionBackendPolicy",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
    "LoadedProject",
    "ProjectLoadRequest",
    "WorkspaceSelection",
    "load_project",
    "main",
    "select_workspace",
]
