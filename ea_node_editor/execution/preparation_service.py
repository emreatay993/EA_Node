# Purpose: Compute execution candidates without holding runtime lifecycle locks.
# Map: subsystems/execution.md
# Tests: tests/test_execution_submission.py, tests/test_runtime.py, tests/test_runtime_current_results.py
from __future__ import annotations

import copy
import json
import threading
import uuid
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from ea_node_editor.execution.compiled_snapshot_cache import CompiledSnapshotCache
from ea_node_editor.execution.execution_plan import ExecutionPlan
from ea_node_editor.execution.prepared_execution import (
    MAX_ACCEPTED_NODE_PAYLOADS_PER_PREPARATION,
    MAX_ACCEPTED_OUTPUT_PAYLOAD_BYTES,
    MAX_ACCEPTED_PORT_RESULTS_PER_PREPARATION,
    PreparedAction,
    PreparedDispatchEnvelope,
    PreparedExecution,
    PreparedNodeDecision,
    RecomputeMode,
)
from ea_node_editor.execution.project_loader import load_project
from ea_node_editor.execution.registry_agreement import (
    RegistryAgreement,
    runtime_registry_fingerprint,
)
from ea_node_editor.execution.runtime_requests import (
    ExecutionRequest,
    WorkspaceSelection,
)
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    RuntimeSnapshotContext,
    build_runtime_snapshot,
    coerce_runtime_snapshot,
)
from ea_node_editor.execution.solution_identity import assemble_node_solution
from ea_node_editor.execution.solution_store import (
    CapturedNodeSolution,
    PreparationState,
    SolutionStore,
)
from ea_node_editor.execution.worker_runtime import RuntimeArtifactService
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import DataTree, RuntimeArtifactRef


@dataclass(frozen=True, slots=True)
class PreparationCandidate:
    prepared: PreparedExecution
    registry: NodeRegistry
    plan: ExecutionPlan
    captured_nodes: tuple[CapturedNodeSolution, ...]
    generation_snapshot: Any
    encoded_size: int
    trigger_reservation_id: str


class ExecutionPreparationService:
    def __init__(
        self,
        *,
        client: Any,
        solution_store: SolutionStore,
        compiled_snapshots: CompiledSnapshotCache,
    ) -> None:
        self._client = client
        self._solution_store = solution_store
        self._compiled_snapshots = compiled_snapshots
        self._registry_agreement_cache: (
            tuple[NodeRegistry, RegistryAgreement] | None
        ) = None
        self._agreement_lock = threading.Lock()

    def _agreement_for_registry(self, registry: NodeRegistry) -> RegistryAgreement:
        cached = self._registry_agreement_cache
        if cached is not None and cached[0] is registry:
            return cached[1]
        with self._agreement_lock:
            cached = self._registry_agreement_cache
            if cached is not None and cached[0] is registry:
                return cached[1]
            registry.freeze()
            agreement = RegistryAgreement.from_registry(registry)
            self._registry_agreement_cache = (registry, agreement)
            return agreement

    @staticmethod
    def resolve_request(
        request: ExecutionRequest,
        *,
        registry: NodeRegistry | None,
    ) -> tuple[ExecutionRequest, NodeRegistry]:
        trigger, raw_snapshot, execution_backend = (
            request.trigger_without_runtime_snapshot()
        )
        candidate_registry = registry
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

    def compute(
        self,
        prepared_request: ExecutionRequest,
        candidate_registry: NodeRegistry,
        captured_state: PreparationState,
        *,
        cancellation: threading.Event | None = None,
        initialize_current_generation: bool = False,
    ) -> PreparationCandidate:
        self._check_cancelled(cancellation)
        runtime_snapshot = prepared_request.runtime_snapshot
        assert isinstance(runtime_snapshot, RuntimeSnapshot)
        project_id = runtime_snapshot.project_id
        namespace_id = captured_state.namespace_id
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
        initialize = getattr(self._client, "prepare_current_generation", None)
        initialized_generation = (
            initialize(selection, candidate_registry)
            if initialize_current_generation and callable(initialize)
            else None
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
        generation_snapshot = (
            initialized_generation
            or self._client.execution_generation_snapshot(
                selection,
                registry_contract_fingerprint=(
                    candidate_registry.contract_fingerprint()
                ),
            )
        )
        if not generation_snapshot.available and preview_environment_digest:
            generation_snapshot = replace(
                generation_snapshot,
                environment_digest=preview_environment_digest,
            )
        compiled = self._compiled_snapshots.get(
            runtime_snapshot,
            workspace_id=prepared_request.workspace_id,
            registry=candidate_registry,
        )
        workspace = compiled.workspace
        plan = ExecutionPlan(
            workspace,
            candidate_registry,
            target_node_ids=prepared_request.target_node_ids,
            clicked_trigger_node_id=prepared_request.clicked_trigger_node_id,
            trigger_capture_node_ids=tuple(sorted(prepared_request.trigger_captures)),
        )
        interface_plan = (
            plan
            if not prepared_request.target_node_ids
            and not prepared_request.clicked_trigger_node_id
            else ExecutionPlan(workspace, candidate_registry)
        )
        preparation_id = f"preparation_{uuid.uuid4().hex}"
        trigger_reservation_id = ""
        reserved_trigger_generation: int | None = None
        if prepared_request.clicked_trigger_node_id and plan.is_trigger(
            prepared_request.clicked_trigger_node_id
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
            agreement = self._agreement_for_registry(candidate_registry)
            catalog_fingerprint = agreement.catalog_fingerprint
            catalog_revisions = agreement.catalog_revisions
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
                plugin_bundles=agreement.plugin_bundles,
                plugin_fingerprint=plugin_fingerprint,
                runtime_registry_fingerprint=runtime_registry_fingerprint(
                    catalog_fingerprint,
                    plugin_fingerprint,
                ),
                registry_contract_fingerprint=registry_fingerprint,
                addon_runtime_config=agreement.addon_runtime_config,
                catalog=candidate_registry.data_types,
                agreement=agreement,
            )
            decisions, accepted, captures = self._prepare_node_decisions(
                cancellation=cancellation,
                preparation_id=preparation_id,
                namespace_id=namespace_id,
                project_id=project_id,
                plan=plan,
                registry=candidate_registry,
                generation_snapshot=generation_snapshot,
                recompute_mode=RecomputeMode(prepared_request.recompute_mode),
                trigger_publication_generations=dict(trigger_publication_generations),
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
                    captured_state.workspace_revision
                ),
                runtime_snapshot_fingerprint=compiled.snapshot_fingerprint,
                execution_plan_fingerprint=plan.fingerprint,
                registry_contract_fingerprint=registry_fingerprint,
                workflow_interface_revision=(
                    interface_plan.workflow_interface_revision
                ),
                workflow_interface_digest=(interface_plan.workflow_interface_digest),
                execution_environment_digest=generation_snapshot.environment_digest,
                trigger_publication_generations=(trigger_publication_generations),
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
                    if item.action.uses_accepted_output
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
            return PreparationCandidate(
                prepared,
                candidate_registry,
                plan,
                captures,
                generation_snapshot,
                encoded_size,
                trigger_reservation_id,
            )
        except Exception:
            self._solution_store.release_trigger_reservation(trigger_reservation_id)
            raise

    @staticmethod
    def _check_cancelled(cancellation: threading.Event | None) -> None:
        if cancellation is not None and cancellation.is_set():
            raise ValueError("preparation_cancelled")

    def _prepare_node_decisions(
        self,
        *,
        preparation_id: str,
        cancellation: threading.Event | None = None,
        namespace_id: str,
        project_id: str,
        plan: ExecutionPlan,
        registry: NodeRegistry,
        generation_snapshot: Any,
        recompute_mode: RecomputeMode,
        trigger_publication_generations: Mapping[str, int],
        artifact_service: RuntimeArtifactService,
    ) -> tuple[
        tuple[PreparedNodeDecision, ...],
        tuple[Any, ...],
        tuple[CapturedNodeSolution, ...],
    ]:
        workspace_id = plan.workspace.workspace_id
        solution_revision = self._solution_store.workspace_revision(
            project_id, workspace_id
        )
        captures: dict[str, CapturedNodeSolution] = {}
        identity_reasons: dict[str, str] = {}
        keys_by_node: dict[str, str] = {}
        reusable_keys: dict[str, bool] = {}
        for node_id in plan.execution_order:
            self._check_cancelled(cancellation)
            if plan.node_specs[node_id].runtime_behavior != "active":
                continue
            capture, identity_reasons[node_id] = self._captured_node_solution(
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
            )
            # Volatile lineage cannot promise repeatable computations. Its detached
            # completed values remain available as CURRENT observations.
            capture = replace(
                capture,
                identity_reuse_eligible=(
                    capture.identity_reuse_eligible
                    and all(
                        reusable_keys[key] for key in capture.dependency_solution_keys
                    )
                ),
            )
            captures[node_id] = capture
            keys_by_node[node_id] = capture.solution_key
            reusable_keys[capture.solution_key] = capture.identity_reuse_eligible

        dependencies = {node_id: [] for node_id in plan.execution_order}
        successors = {node_id: [] for node_id in plan.execution_order}
        for target in plan.execution_order:
            for edge in plan.incoming_edges_for(target):
                if edge.source_node_id in dependencies:
                    dependencies[target].append(
                        (edge.source_node_id, edge.source_port_key)
                    )
                    if not plan.is_trigger(edge.source_node_id):
                        successors[edge.source_node_id].append(target)
        for source, target in plan.hidden_ordering_pairs:
            if source in dependencies and target in dependencies:
                dependencies[target].append((source, None))
                successors[source].append(target)
        for node_id in dependencies:
            if plan.is_trigger(node_id) and (
                node_id != plan.clicked_trigger_node_id
                and node_id not in plan.target_nodes
                or node_id == plan.clicked_trigger_node_id
                and node_id in plan.trigger_capture_node_ids
            ):
                dependencies[node_id] = []

        allow_current = (
            bool(plan.target_nodes)
            and not plan.clicked_trigger_node_id
            and recompute_mode is RecomputeMode.REUSE_VALID
        )
        pending = deque()
        queued: set[str] = set()
        requested_ports: dict[str, set[str]] = {}
        effect_required: set[str] = set()
        recomputed = deque()
        required: set[str] = set()
        tainted: set[str] = set()
        actions: dict[str, PreparedAction] = {}
        reasons: dict[str, str] = {}
        accepted: dict[str, Any] = {}
        sizes: dict[str, int] = {}
        accepted_ports = 0
        accepted_bytes = 0

        def require(node_id: str, port_key: str | None = None) -> None:
            if port_key is None:
                changed = node_id not in effect_required
                effect_required.add(node_id)
            else:
                ports = requested_ports.setdefault(node_id, set())
                changed = port_key not in ports
                ports.add(port_key)
            if (changed or node_id not in required) and node_id not in queued:
                queued.add(node_id)
                pending.append(node_id)

        def require_dependencies(node_id: str) -> None:
            for source, port_key in dependencies[node_id]:
                require(source, port_key)

        for node_id in plan.target_nodes if allow_current else plan.execution_order:
            if node_id in dependencies:
                require(node_id)

        def discard_output(node_id: str) -> None:
            nonlocal accepted_ports, accepted_bytes
            payload = accepted.pop(node_id, None)
            if payload is not None:
                accepted_ports -= payload.output_count
                accepted_bytes -= sizes.pop(node_id)

        def retain_output(node_id: str, payload: Any) -> bool:
            nonlocal accepted_ports, accepted_bytes
            self._validate_prepared_artifacts(
                payload,
                artifact_service=artifact_service,
                catalog=registry.data_types,
            )
            size = len(
                json.dumps(
                    payload.to_payload(catalog=registry.data_types),
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            )
            if (
                len(accepted) + 1 > MAX_ACCEPTED_NODE_PAYLOADS_PER_PREPARATION
                or accepted_ports + payload.output_count
                > MAX_ACCEPTED_PORT_RESULTS_PER_PREPARATION
                or accepted_bytes + size > MAX_ACCEPTED_OUTPUT_PAYLOAD_BYTES
            ):
                return False
            accepted[node_id] = payload
            sizes[node_id] = size
            accepted_ports += payload.output_count
            accepted_bytes += size
            return True

        def execution_reason(node_id: str) -> str:
            if recompute_mode is RecomputeMode.FORCE_RECOMPUTE:
                return "force_recompute"
            if identity_reasons[node_id]:
                return identity_reasons[node_id]
            if plan.node_specs[node_id].solution_reuse_scope == "never":
                return "solution_reuse_scope_never"
            if not generation_snapshot.available:
                return generation_snapshot.reason or "execution_generation_unavailable"
            if node_id in tainted:
                return "upstream_recompute_required"
            if not captures[node_id].identity_reuse_eligible:
                return "volatile_dependency"
            return ""

        # Demand moves upstream; recomputation moves downstream. Each flag changes
        # once, so a shared executing branch deoptimizes boundaries without rescans.
        while pending or recomputed:
            self._check_cancelled(cancellation)
            if recomputed:
                node_id = recomputed.popleft()
                if node_id in tainted:
                    continue
                tainted.add(node_id)
                recomputed.extend(successors[node_id])
                if node_id in required and node_id in captures:
                    if actions[node_id] is PreparedAction.READ_CURRENT:
                        require_dependencies(node_id)
                    discard_output(node_id)
                    actions[node_id] = PreparedAction.EXECUTE
                continue
            node_id = pending.popleft()
            queued.discard(node_id)
            if (
                node_id in required
                and actions.get(node_id) is not PreparedAction.READ_CURRENT
            ):
                continue
            required.add(node_id)
            if node_id not in captures:
                require_dependencies(node_id)
                continue
            discard_output(node_id)
            capture = captures[node_id]
            lookup = dict(
                solution_key=capture.solution_key,
                project_id=project_id,
                workspace_id=workspace_id,
                node_id=node_id,
                runtime_generation=generation_snapshot.runtime_generation,
                catalog=registry.data_types,
            )
            if (
                allow_current
                and node_id not in effect_required
                and not plan.is_trigger(node_id)
                and node_id not in tainted
                and generation_snapshot.available
                and not identity_reasons[node_id]
            ):
                try:
                    current = self._solution_store.current_outputs(
                        **lookup,
                        artifact_context=artifact_service.store,
                        port_keys=tuple(sorted(requested_ports[node_id])),
                    )
                    if current is not None and retain_output(node_id, current[1]):
                        actions[node_id] = PreparedAction.READ_CURRENT
                        continue
                except (KeyError, OSError, TypeError, ValueError):
                    pass  # Invalid or evicted observations require ordinary execution.
            require_dependencies(node_id)
            reason = execution_reason(node_id)
            if not reason:
                record = self._solution_store.select_record(**lookup)
                reason = "no_reusable_record"
                if record is not None:
                    try:
                        payload = self._solution_store.accepted_outputs(
                            record,
                            catalog=registry.data_types,
                            runtime_generation=generation_snapshot.runtime_generation,
                            artifact_context=artifact_service.store,
                        )
                        if retain_output(node_id, payload):
                            actions[node_id] = PreparedAction.REUSE
                            continue
                        reason = "reuse_payload_budget_exceeded"
                    except (KeyError, OSError, TypeError, ValueError):
                        reason = "accepted_output_invalid"
            actions[node_id] = PreparedAction.EXECUTE
            reasons[node_id] = reason
            recomputed.extend(successors[node_id])

        boundaries = frozenset(
            node_id
            for node_id, action in actions.items()
            if action is PreparedAction.READ_CURRENT
        )
        if required != plan.required_node_ids(boundaries):
            raise RuntimeError(
                "current-result demand does not match the execution plan"
            )
        if plan.current_result_ports(boundaries) != {
            node_id: tuple(sorted(requested_ports[node_id])) for node_id in boundaries
        }:
            raise RuntimeError("current-result ports do not match execution demand")
        decisions = []
        for node_id, capture in captures.items():
            action = actions.get(node_id, PreparedAction.PRUNE)
            if action is PreparedAction.READ_CURRENT:
                reason = "current_result_accepted"
            elif action is PreparedAction.REUSE:
                reason = "reusable_record_accepted"
            elif action is PreparedAction.PRUNE:
                reason = "dependency_not_required"
            else:
                reason = execution_reason(node_id) or reasons[node_id]
            decisions.append(
                PreparedNodeDecision(
                    node_id=node_id,
                    action=action,
                    reason_code=reason,
                    solution_key=capture.solution_key,
                    dependency_solution_keys=capture.dependency_solution_keys,
                    accepted_record_id=accepted[node_id].record_id
                    if node_id in accepted
                    else None,
                    accepted_payload_digest=accepted[node_id].commitment_digest()
                    if node_id in accepted
                    else None,
                )
            )
        return (
            tuple(decisions),
            tuple(accepted[node_id] for node_id in captures if node_id in accepted),
            tuple(captures.values()),
        )

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
                node_interface_revision=assembled.node_interface_revision,
                node_interface_digest=assembled.node_interface_digest,
                node_contract_digest=assembled.node_contract_digest,
                input_provenance_digest=assembled.input_provenance_digest,
                execution_policy_digest=assembled.execution_policy_digest,
                implementation_digest=assembled.implementation_digest,
                execution_environment_digest=generation_snapshot.environment_digest,
                output_specs=assembled.output_specs,
                solution_reuse_scope=spec.solution_reuse_scope,
                identity_reuse_eligible=(
                    not assembled.reason_code
                    and generation_snapshot.available
                    and spec.solution_reuse_scope != "never"
                ),
            ),
            assembled.reason_code,
        )
