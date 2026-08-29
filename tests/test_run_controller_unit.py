from __future__ import annotations

import base64
import hashlib
import unittest
from unittest import mock
from types import SimpleNamespace

from ea_node_editor.execution.backends import EXTERNAL_SUBPROCESS_BACKEND
from ea_node_editor.execution.execution_plan import ExecutionPlan
from ea_node_editor.execution.prepared_execution import InvalidationResult
from ea_node_editor.execution.protocol import (
    NodeSettledEvent,
    TriggerCaptureSettledEvent,
    event_to_dict,
)
from ea_node_editor.runtime_contracts.settled_results import (
    RootExecutionError,
    SettledPortResult,
)
from ea_node_editor.runtime_contracts.solution_records import (
    NodeSolutionFact,
    SolutionDisposition,
    SolutionFreshness,
    SolutionResidency,
)
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec
from ea_node_editor.nodes.runtime_refs import RuntimeHandleRef
from ea_node_editor.ui.shell.controllers.run_controller import RunController
from ea_node_editor.ui.shell.state import ShellRunState
from ea_node_editor.ui.support.port_flow_state import resolve_runtime_port_flow_states
from ea_node_editor.ui.support.solution_output_cache import (
    cache_accepted_output_record,
    retained_output_record,
    retained_output_records_by_node,
)
from ea_node_editor.ui_qml.graph_scene_payload import GraphScenePayloadBuilder
from ea_node_editor.runtime_contracts import DataTree, ImageValue


_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg=="
)


def _value_outputs(**values: object) -> dict[str, SettledPortResult]:
    return {
        key: SettledPortResult(status="value", value=DataTree.from_item(value))
        for key, value in values.items()
    }


def _value_result(value: object) -> SettledPortResult:
    return SettledPortResult(status="value", value=DataTree.from_item(value))


def _accepted_settlement(
    host,
    *,
    workspace_id: str,
    node_id: str,
    run_id: str,
    outputs: dict[str, SettledPortResult],
    status: str = "completed",
) -> dict:
    solution_key = hashlib.sha256(node_id.encode("utf-8")).hexdigest()
    result_digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
    record_id = f"record_{run_id}_{node_id}"
    existing = {
        fact.node_id: fact
        for fact in host.execution_client.solution_facts_by_workspace.get(
            workspace_id, ()
        )
    }
    existing[node_id] = NodeSolutionFact(
        project_id=host.model.project.project_id,
        workspace_id=workspace_id,
        node_id=node_id,
        freshness=SolutionFreshness.CURRENT,
        revision=int(getattr(existing.get(node_id), "revision", 0)),
        retained_record_id=record_id,
        retained_solution_key=solution_key,
        residency=SolutionResidency.SESSION,
        last_disposition=SolutionDisposition.RECOMPUTED,
    )
    host.execution_client.solution_facts_by_workspace[workspace_id] = tuple(
        existing.values()
    )
    return {
        "type": "node_settled",
        "status": status,
        "run_id": run_id,
        "workspace_id": workspace_id,
        "node_id": node_id,
        "outputs": outputs,
        "accepted_solution_record": True,
        "record_id": record_id,
        "solution_key": solution_key,
        "result_digest": result_digest,
        "disposition": "recomputed",
        "solution_fact_revision": existing[node_id].revision,
    }


def _script_result(expression: str) -> str:
    return (
        "@corex.node\n"
        "@corex.input(\"payload\", value_type=corex.Any)\n"
        "@corex.output(\"result\", value_type=corex.Any)\n"
        "def run(ctx, payload):\n"
        f"    return {{\"result\": {expression}}}\n"
    )


class _ConsoleStub:
    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []
        self.warning_count = 0
        self.error_count = 0
        self.clear_count = 0

    def append_log(self, level: str, message: str) -> None:
        self.logs.append((str(level), str(message)))
        if level == "warning":
            self.warning_count += 1
        if level == "error":
            self.error_count += 1

    def clear_all(self) -> None:
        self.logs.clear()
        self.warning_count = 0
        self.error_count = 0
        self.clear_count += 1


class _ActionStub:
    def __init__(self) -> None:
        self.enabled = True
        self.text = ""
        self.icon = None

    def setEnabled(self, value: bool) -> None:  # noqa: N802
        self.enabled = bool(value)

    def setText(self, value: str) -> None:  # noqa: N802
        self.text = str(value)

    def setIcon(self, value) -> None:  # noqa: ANN001, N802
        self.icon = value


class _SignalCounter:
    def __init__(self) -> None:
        self.calls = 0

    def emit(self) -> None:
        self.calls += 1


class _WorkspaceManagerStub:
    def __init__(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id

    def active_workspace_id(self) -> str:
        return self._workspace_id

    def set_active_workspace(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id


class _SerializerStub:
    def to_document(self, project) -> dict:  # noqa: ANN001
        return {
            "project_id": project.project_id,
            "workspace_count": len(project.workspaces),
        }


class _ProjectSessionControllerStub:
    def workflow_settings_payload(self) -> dict:
        return {"general": {"project_name": "Demo"}}


class _ExecutionClientStub:
    def __init__(self, registry) -> None:  # noqa: ANN001
        self.registry = registry
        self.next_run_id = "run_live"
        self.start_calls: list[dict] = []
        self.pause_calls: list[str] = []
        self.resume_calls: list[str] = []
        self.stop_calls: list[str] = []
        self.solution_facts_by_workspace: dict[str, tuple] = {}
        self.solution_revisions: dict[str, int] = {}
        self.invalidate_calls: list[dict] = []

    def prepare_execution(self, request):  # noqa: ANN001, ANN201
        return SimpleNamespace(
            request=request,
            recompute_node_ids=tuple(request.target_node_ids),
        )

    def dispatch_prepared(self, prepared) -> str:  # noqa: ANN001
        request = prepared.request
        trigger = dict(request.trigger)
        trigger["runtime_snapshot"] = request.runtime_snapshot
        self.start_calls.append(
            {
                "project_path": str(request.project_path),
                "workspace_id": request.workspace_id,
                "trigger": trigger,
                "execution_backend": request.execution_backend,
                "target_node_ids": tuple(request.target_node_ids),
                "trigger_publications": dict(request.trigger_publications),
                "trigger_captures": dict(request.trigger_captures),
                "clicked_trigger_node_id": request.clicked_trigger_node_id,
            }
        )
        return self.next_run_id

    def solution_facts(self, project_id: str, workspace_id: str):  # noqa: ANN201
        del project_id
        return self.solution_facts_by_workspace.get(workspace_id, ())

    def invalidate_solution(
        self,
        project_id: str,
        workspace_id: str,
        runtime_snapshot,
        changed_root_node_ids,
        reason_code: str,
    ) -> InvalidationResult:
        plan = ExecutionPlan(runtime_snapshot.workspace(workspace_id), self.registry)
        closure = plan.affected_downstream_closure(tuple(changed_root_node_ids))
        active_ids = {
            node_id
            for node_id in plan.execution_order
            if plan.node_specs[node_id].runtime_behavior == "active"
        }
        removed = tuple(
            fact.node_id
            for fact in self.solution_facts_by_workspace.get(workspace_id, ())
            if fact.node_id not in active_ids
        )
        self.solution_revisions[workspace_id] = (
            self.solution_revisions.get(workspace_id, 0) + 1
        )
        result = InvalidationResult(
            project_id=project_id,
            workspace_id=workspace_id,
            solution_revision=self.solution_revisions[workspace_id],
            changed_root_node_ids=tuple(changed_root_node_ids),
            expired_node_ids=tuple(closure),
            removed_node_ids=removed,
            reason_code=reason_code,
        )
        updated_facts = []
        for fact in self.solution_facts_by_workspace.get(workspace_id, ()):
            if fact.node_id in removed:
                continue
            if fact.node_id in closure:
                fact = NodeSolutionFact(
                    project_id=fact.project_id,
                    workspace_id=fact.workspace_id,
                    node_id=fact.node_id,
                    freshness=SolutionFreshness.EXPIRED,
                    revision=fact.revision + 1,
                    retained_record_id=fact.retained_record_id,
                    retained_solution_key=fact.retained_solution_key,
                    residency=fact.residency,
                    expiration_reason_code=reason_code,
                    expiration_root_node_ids=closure[fact.node_id],
                    last_disposition=fact.last_disposition,
                )
            updated_facts.append(fact)
        self.solution_facts_by_workspace[workspace_id] = tuple(updated_facts)
        self.invalidate_calls.append(result.to_payload())
        return result

    def pause_run(self, run_id: str) -> None:
        self.pause_calls.append(run_id)

    def resume_run(self, run_id: str) -> None:
        self.resume_calls.append(run_id)

    def stop_run(self, run_id: str) -> None:
        self.stop_calls.append(run_id)


class _WorkspaceLibraryControllerStub:
    def __init__(self) -> None:
        self.focus_calls: list[tuple[str, str]] = []

    def focus_failed_node(self, workspace_id: str, node_id: str) -> None:
        self.focus_calls.append((workspace_id, node_id))


class _AppPreferencesControllerStub:
    def __init__(
        self,
        preview_before_run: bool = True,
        default_mode: str = "auto",
        default_python_executable: str = "",
    ) -> None:
        self.preview_before_run = bool(preview_before_run)
        self.default_mode = default_mode
        self.python_executable = default_python_executable

    def selected_run_preview_before_run(self) -> bool:
        return bool(self.preview_before_run)

    def solution_default_mode(self) -> str:
        return self.default_mode

    def default_python_executable(self) -> str:
        return self.python_executable


class _ScriptEditorStub:
    def __init__(self) -> None:
        self.dirty = False
        self.apply_calls = 0
        self.apply_result = True
        self.apply_callback = None

    def apply(self) -> bool:
        self.apply_calls += 1
        if callable(self.apply_callback):
            self.apply_callback()
        if self.apply_result:
            self.dirty = False
        return self.apply_result


class _PassthroughDependencyPlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="test.passthrough_dependency",
            display_name="Passthrough Dependency",
            category_path=("Test",),
            icon="core/data_object.svg",
            ports=(
                PortSpec(
                    "value",
                    "in",
                    "data",
                    "COREX.DataTypes.Any",
                    required=False,
                ),
                PortSpec(
                    "result",
                    "out",
                    "data",
                    "COREX.DataTypes.Any",
                    exposed=True,
                ),
            ),
            properties=(),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"result": ctx.inputs.get("value")})


class _RequiredPureDataPlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="test.required_pure_data",
            display_name="Required Pure Data",
            category_path=("Test",),
            icon="core/data_object.svg",
            ports=(
                PortSpec(
                    "value",
                    "in",
                    "data",
                    "COREX.DataTypes.Int",
                    required=True,
                ),
                PortSpec(
                    "result", "out", "data", "COREX.DataTypes.Int", exposed=True
                ),
            ),
            properties=(PropertySpec("value", "int", 0, "Value"),),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(
            outputs={"result": ctx.inputs.get("value", ctx.properties.get("value", 0))}
        )


class _RunHostStub:
    _RUN_SCOPED_EVENT_TYPES = {
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
    }

    def __init__(self, *, default_mode: str = "manual") -> None:
        self.run_state = ShellRunState()
        self.project_path = "demo.cxproj"
        self.model = GraphModel()
        self.workspace_manager = _WorkspaceManagerStub(
            self.model.active_workspace.workspace_id
        )
        self.serializer = _SerializerStub()
        self.registry = build_default_registry()
        self.project_session_controller = _ProjectSessionControllerStub()
        self.app_preferences_controller = _AppPreferencesControllerStub(
            default_mode=default_mode
        )
        self.console_panel = _ConsoleStub()
        self.execution_client = _ExecutionClientStub(self.registry)
        self.script_editor = _ScriptEditorStub()
        self.workspace_library_controller = _WorkspaceLibraryControllerStub()
        self.action_run = _ActionStub()
        self.action_stop = _ActionStub()
        self.action_pause = _ActionStub()
        self.run_controls_changed = _SignalCounter()
        self.run_failure_changed = _SignalCounter()
        self.node_execution_state_changed = _SignalCounter()
        self._notifications = (0, 0)
        self._engine_status = ("ready", "")
        self._job_counters = (0, 0, 0, 0)
        self._failure_clear_count = 0
        self.selected_run_settings_dialog_open_count = 0

    def update_notification_counters(self, warnings: int, errors: int) -> None:
        self._notifications = (warnings, errors)

    def update_engine_status(self, state: str, details: str = "") -> None:
        self._engine_status = (state, details)

    def update_job_counters(
        self, running: int, queued: int, done: int, failed: int
    ) -> None:
        self._job_counters = (running, queued, done, failed)

    def clear_run_failure_focus(self) -> None:
        self._failure_clear_count += 1

    def show_selected_run_settings_dialog(self) -> None:
        self.selected_run_settings_dialog_open_count += 1


class RunControllerUnitTests(unittest.TestCase):
    def assert_run_controls(
        self,
        host: _RunHostStub,
        *,
        run_enabled: bool,
        pause_enabled: bool,
        stop_enabled: bool,
        pause_label: str,
    ) -> None:
        self.assertEqual(host.action_run.enabled, run_enabled)
        self.assertEqual(host.action_pause.enabled, pause_enabled)
        self.assertEqual(host.action_stop.enabled, stop_enabled)
        self.assertEqual(host.action_pause.text, pause_label)

    def test_ui_solution_cache_is_bounded_and_run_count_is_monotonic(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        node = host.model.add_node(
            workspace_id, "core.constant", "Cached", 0, 0
        )
        controller = RunController(host)  # type: ignore[arg-type]
        for run_id in ("run_1", "run_2", "run_3"):
            host.run_state.active_run_id = run_id
            host.run_state.active_run_workspace_id = workspace_id
            controller.handle_execution_event(
                _accepted_settlement(
                    host,
                    workspace_id=workspace_id,
                    node_id=node.node_id,
                    run_id=run_id,
                    outputs=_value_outputs(value=run_id),
                )
            )
        records = host.run_state.cached_node_output_records_by_workspace_id[
            workspace_id
        ][node.node_id]
        self.assertEqual(len(records), 2)
        self.assertEqual(
            host.run_state.node_output_run_counts_by_workspace_id[workspace_id][
                node.node_id
            ],
            3,
        )
        retained = retained_output_record(host.run_state, workspace_id, node.node_id)
        self.assertIsNotNone(retained)
        self.assertEqual(retained["run_id"], "run_3")

    def test_ui_solution_cache_global_eviction_and_metadata_only_fallback(self) -> None:
        state = ShellRunState()
        catalog = build_default_registry().data_types

        def cache(workspace_id: str, node_id: str, record_id: str) -> None:
            state.node_solution_facts_by_workspace_id[workspace_id] = {
                node_id: NodeSolutionFact(
                    project_id="project",
                    workspace_id=workspace_id,
                    node_id=node_id,
                    freshness=SolutionFreshness.CURRENT,
                    revision=1,
                    retained_record_id=record_id,
                    retained_solution_key="a" * 64,
                    residency=SolutionResidency.SESSION,
                    last_disposition=SolutionDisposition.RECOMPUTED,
                )
            }
            self.assertTrue(
                cache_accepted_output_record(
                    state,
                    workspace_id=workspace_id,
                    node_id=node_id,
                    event={
                        "record_id": record_id,
                        "solution_key": "a" * 64,
                        "result_digest": "b" * 64,
                        "disposition": "recomputed",
                        "run_id": record_id,
                    },
                    outputs=_value_outputs(value=record_id),
                    catalog=catalog,
                )
            )

        with mock.patch(
            "ea_node_editor.ui.support.solution_output_cache.MAX_RECORDS_GLOBAL", 2
        ):
            cache("ws_1", "node_1", "record_1")
            state.node_solution_facts_by_workspace_id["ws_1"] = {}
            cache("ws_2", "node_2", "record_2")
            state.node_solution_facts_by_workspace_id["ws_2"] = {}
            cache("ws_3", "node_3", "record_3")
        self.assertNotIn("ws_1", state.cached_node_output_records_by_workspace_id)
        self.assertEqual(
            set(state.cached_node_output_records_by_workspace_id), {"ws_2", "ws_3"}
        )

        metadata_state = ShellRunState()
        state = metadata_state
        with mock.patch(
            "ea_node_editor.ui.support.solution_output_cache.MAX_PAYLOAD_BYTES_GLOBAL",
            1,
        ):
            cache("ws_meta", "node_meta", "record_meta")
        metadata = metadata_state.cached_node_output_records_by_workspace_id[
            "ws_meta"
        ]["node_meta"]["record_meta"]
        self.assertFalse(metadata["outputs_available"])
        self.assertEqual(metadata["outputs"], {})
        self.assertFalse(
            retained_output_records_by_node(metadata_state, "ws_meta")["node_meta"][
                "record_meta"
            ]["outputs_available"]
        )

    def test_solution_state_events_filter_project_and_monotonic_revision(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        node = host.model.add_node(
            workspace_id, "core.constant", "State", 0, 0
        )
        controller = RunController(host)  # type: ignore[arg-type]
        fact = NodeSolutionFact(
            project_id=host.model.project.project_id,
            workspace_id=workspace_id,
            node_id=node.node_id,
            freshness=SolutionFreshness.CURRENT,
            revision=1,
            retained_record_id="record_current",
            retained_solution_key="a" * 64,
            residency=SolutionResidency.SESSION,
            last_disposition=SolutionDisposition.RECOMPUTED,
        )
        host.execution_client.solution_facts_by_workspace[workspace_id] = (fact,)
        event = {
            "type": "solution_state_changed",
            "project_id": host.model.project.project_id,
            "workspace_id": workspace_id,
            "solution_revision": 1,
            "expired_node_ids": [],
            "removed_node_ids": [],
            "reason_code": "registry_generation_replaced",
        }
        controller.handle_execution_event({**event, "project_id": "other"})
        self.assertNotIn(workspace_id, host.run_state.solution_revision_by_workspace_id)
        controller.handle_execution_event(event)
        self.assertIs(
            host.run_state.node_solution_facts_by_workspace_id[workspace_id][
                node.node_id
            ].freshness,
            SolutionFreshness.CURRENT,
        )
        host.execution_client.solution_facts_by_workspace[workspace_id] = (
            NodeSolutionFact(
                project_id=fact.project_id,
                workspace_id=workspace_id,
                node_id=node.node_id,
                freshness=SolutionFreshness.EXPIRED,
                revision=2,
                retained_record_id=fact.retained_record_id,
                retained_solution_key=fact.retained_solution_key,
                residency=fact.residency,
                expiration_reason_code="late_duplicate",
                expiration_root_node_ids=(node.node_id,),
                last_disposition=fact.last_disposition,
            ),
        )
        controller.handle_execution_event(
            {**event, "expired_node_ids": [node.node_id]}
        )
        self.assertIs(
            host.run_state.node_solution_facts_by_workspace_id[workspace_id][
                node.node_id
            ].freshness,
            SolutionFreshness.CURRENT,
        )

    def test_reset_before_settlement_keeps_current_cache_and_availability(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        node = host.model.add_node(workspace_id, "core.constant", "State", 0, 0)
        controller = RunController(host)  # type: ignore[arg-type]
        host.execution_client.solution_facts_by_workspace[workspace_id] = (
            NodeSolutionFact(
                project_id=host.model.project.project_id,
                workspace_id=workspace_id,
                node_id=node.node_id,
                freshness=SolutionFreshness.EXPIRED,
                revision=1,
                expiration_reason_code="runtime_generation_replaced",
                expiration_root_node_ids=(node.node_id,),
            ),
        )
        controller.handle_execution_event(
            {
                "type": "solution_state_changed",
                "project_id": host.model.project.project_id,
                "workspace_id": workspace_id,
                "solution_revision": 1,
                "expired_node_ids": [node.node_id],
                "removed_node_ids": [],
                "reason_code": "runtime_generation_replaced",
            }
        )
        host.run_state.active_run_id = "run_after_reset"
        host.run_state.active_run_workspace_id = workspace_id
        settled = _accepted_settlement(
            host,
            workspace_id=workspace_id,
            node_id=node.node_id,
            run_id="run_after_reset",
            outputs=_value_outputs(value="current"),
        )

        with mock.patch(
            "ea_node_editor.ui.shell.controllers.run_controller.observe_node_outputs"
        ) as observe:
            controller.handle_execution_event(settled)

        observe.assert_called_once()
        self.assertIn(node.node_id, host.run_state.completed_node_ids)
        self.assertIn(
            node.node_id,
            host.run_state.cached_node_output_records_by_workspace_id[workspace_id],
        )

    def test_history_classifier_ignores_passive_and_normalizes_removed_only(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        controller = RunController(host)  # type: ignore[arg-type]
        passive_before = host.model.active_workspace.capture_snapshot()
        host.model.add_node(
            workspace_id,
            "passive.annotation.sticky_note",
            "Note",
            0,
            0,
        )
        self.assertFalse(
            controller.invalidate_solution_for_history_action(
                workspace_id,
                "add-node",
                before_snapshot=passive_before,
                after_snapshot=host.model.active_workspace.capture_snapshot(),
            )
        )
        self.assertEqual(host.execution_client.invalidate_calls, [])

        active = host.model.add_node(
            workspace_id,
            "core.constant",
            "Removed",
            0,
            0,
        )
        fact = NodeSolutionFact(
            project_id=host.model.project.project_id,
            workspace_id=workspace_id,
            node_id=active.node_id,
            freshness=SolutionFreshness.CURRENT,
            revision=1,
            retained_record_id="record_removed",
            retained_solution_key="a" * 64,
            residency=SolutionResidency.SESSION,
            last_disposition=SolutionDisposition.RECOMPUTED,
        )
        host.execution_client.solution_facts_by_workspace[workspace_id] = (fact,)
        before_remove = host.model.active_workspace.capture_snapshot()
        host.model.remove_node(workspace_id, active.node_id)
        self.assertTrue(
            controller.invalidate_solution_for_history_action(
                workspace_id,
                "remove-node",
                before_snapshot=before_remove,
                after_snapshot=host.model.active_workspace.capture_snapshot(),
            )
        )
        invalidation = host.execution_client.invalidate_calls[-1]
        self.assertEqual(invalidation["changed_root_node_ids"], [])
        self.assertEqual(invalidation["expired_node_ids"], [])
        self.assertEqual(invalidation["removed_node_ids"], [active.node_id])

    def test_run_workflow_starts_new_run_with_manual_trigger_and_updates_state(
        self,
    ) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()

        self.assertEqual(host.console_panel.clear_count, 1)
        self.assertEqual(host.run_state.active_run_id, "run_live")
        self.assertEqual(
            host.run_state.active_run_workspace_id,
            host.model.active_workspace.workspace_id,
        )
        self.assertEqual(host.run_state.engine_state_value, "running")
        self.assertEqual(host._engine_status, ("running", "Starting"))
        self.assertEqual(host._job_counters, (1, 0, 0, 0))
        self.assert_run_controls(
            host,
            run_enabled=False,
            pause_enabled=True,
            stop_enabled=True,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

        start_call = host.execution_client.start_calls[-1]
        self.assertEqual(start_call["project_path"], "demo.cxproj")
        self.assertEqual(
            start_call["workspace_id"], host.model.active_workspace.workspace_id
        )
        self.assertEqual(start_call["trigger"]["kind"], "manual")
        self.assertEqual(start_call["target_node_ids"], ())
        self.assertEqual(start_call["trigger_publications"], {})
        self.assertEqual(
            start_call["trigger"]["workflow_settings"],
            {"general": {"project_name": "Demo"}},
        )
        self.assertNotIn("project_doc", start_call["trigger"])
        runtime_snapshot = start_call["trigger"]["runtime_snapshot"]
        self.assertEqual(
            runtime_snapshot.active_workspace_id,
            host.model.active_workspace.workspace_id,
        )
        self.assertEqual(len(runtime_snapshot.workspaces), 1)
        self.assertEqual(
            runtime_snapshot.to_document()["workspaces"][0]["document_fields"][
                "workspace_id"
            ],
            host.model.active_workspace.workspace_id,
        )

    def test_application_default_python_policy_obeys_project_and_blank_precedence(
        self,
    ) -> None:
        host = _RunHostStub()
        host.app_preferences_controller.python_executable = "application-python"
        controller = RunController(host)  # type: ignore[arg-type]
        workspace_id = host.model.active_workspace.workspace_id

        blank_snapshot = build_runtime_snapshot(
            host.model.project,
            workspace_id=workspace_id,
            registry=host.registry,
        )
        self.assertEqual(
            controller._execution_backend_policy_for_runtime_snapshot(  # noqa: SLF001
                blank_snapshot
            ),
            {
                "requested_backend": EXTERNAL_SUBPROCESS_BACKEND,
                "allow_external_subprocess": True,
                "python_executable": "application-python",
                "reason": "application_default_python_executable",
            },
        )

        host.model.project.metadata["workflow_settings"] = {
            "environment": {"python_path": "project-python"}
        }
        project_snapshot = build_runtime_snapshot(
            host.model.project,
            workspace_id=workspace_id,
            registry=host.registry,
        )
        self.assertIsNone(
            controller._execution_backend_policy_for_runtime_snapshot(  # noqa: SLF001
                project_snapshot
            )
        )

        host.app_preferences_controller.python_executable = ""
        self.assertIsNone(
            controller._execution_backend_policy_for_runtime_snapshot(  # noqa: SLF001
                blank_snapshot
            )
        )

    def test_application_default_python_policy_reaches_every_shell_dispatch(self) -> None:
        expected_policy = {
            "requested_backend": EXTERNAL_SUBPROCESS_BACKEND,
            "allow_external_subprocess": True,
            "python_executable": "application-python-sentinel",
            "reason": "application_default_python_executable",
        }
        calls: list[dict] = []

        host = _RunHostStub()
        host.app_preferences_controller.python_executable = expected_policy[
            "python_executable"
        ]
        RunController(host).run_workflow()  # type: ignore[arg-type]
        calls.append(host.execution_client.start_calls[-1])

        for trigger_kind in ("manual", "auto"):
            host = _RunHostStub()
            host.app_preferences_controller.preview_before_run = False
            host.app_preferences_controller.python_executable = expected_policy[
                "python_executable"
            ]
            workspace_id = host.model.active_workspace.workspace_id
            logger = host.model.add_node(
                workspace_id, "core.logger", "Logger", 0, 0
            )
            RunController(host).run_selected_nodes(  # type: ignore[arg-type]
                [logger.node_id],
                trigger_kind=trigger_kind,
            )
            calls.append(host.execution_client.start_calls[-1])

        host = _RunHostStub()
        host.app_preferences_controller.python_executable = expected_policy[
            "python_executable"
        ]
        workspace_id = host.model.active_workspace.workspace_id
        trigger = host.model.add_node(
            workspace_id, "core.trigger", "Trigger", 0, 0
        )
        self.assertTrue(
            RunController(host).trigger_node(trigger.node_id)  # type: ignore[arg-type]
        )
        calls.append(host.execution_client.start_calls[-1])

        self.assertEqual(
            [call["trigger"]["kind"] for call in calls],
            ["manual", "manual", "auto", "trigger"],
        )
        for call in calls:
            self.assertEqual(call["execution_backend"], expected_policy)
            self.assertNotIn("python_executable", repr(call["trigger"]))
            self.assertNotIn(
                "application-python-sentinel",
                repr(call["trigger"]["runtime_snapshot"].to_document()),
            )

    def test_run_workflow_applies_dirty_script_before_snapshot_without_duplicate_auto_run(
        self,
    ) -> None:
        host = _RunHostStub(default_mode="auto")
        workspace_id = host.model.active_workspace.workspace_id
        workspace = host.model.active_workspace
        script = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            0,
            0,
            properties={"script": _script_result("'old'")},
        )
        controller = RunController(host)  # type: ignore[arg-type]
        host.script_editor.dirty = True

        def apply_draft() -> None:
            before = workspace.capture_snapshot()
            host.model.set_node_property(
                workspace_id,
                script.node_id,
                "script",
                _script_result("'draft'"),
            )
            controller.invalidate_solution_for_history_action(
                workspace_id,
                "edit-node-property",
                before_snapshot=before,
                after_snapshot=workspace.capture_snapshot(),
            )

        host.script_editor.apply_callback = apply_draft

        controller.run_workflow()

        self.assertEqual(host.script_editor.apply_calls, 1)
        self.assertEqual(len(host.execution_client.start_calls), 1)
        runtime_workspace = host.execution_client.start_calls[0]["trigger"][
            "runtime_snapshot"
        ].workspace(workspace_id)
        runtime_script = next(
            node for node in runtime_workspace.nodes if node.node_id == script.node_id
        )
        self.assertEqual(runtime_script.properties["script"], _script_result("'draft'"))

        host.run_state.active_run_id = ""
        host.run_state.active_run_workspace_id = ""
        before = workspace.capture_snapshot()
        host.model.set_node_property(
            workspace_id,
            script.node_id,
            "timeout_sec",
            1.0,
        )
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "edit-node-property",
            before_snapshot=before,
            after_snapshot=workspace.capture_snapshot(),
        )
        self.assertEqual(len(host.execution_client.start_calls), 2)
        self.assertEqual(
            host.execution_client.start_calls[-1]["trigger"]["kind"],
            "auto",
        )

    def test_run_workflow_aborts_when_dirty_script_apply_fails(self) -> None:
        host = _RunHostStub()
        host.script_editor.dirty = True
        host.script_editor.apply_result = False
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()

        self.assertEqual(host.script_editor.apply_calls, 1)
        self.assertEqual(host.execution_client.start_calls, [])
        self.assertTrue(host.script_editor.dirty)

    def test_open_selected_run_settings_delegates_to_shell_dialog(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.open_selected_run_settings()

        self.assertEqual(host.selected_run_settings_dialog_open_count, 1)
        self.assertEqual(host.console_panel.logs, [])

    def test_run_selected_nodes_passes_only_explicit_targets_and_runtime_pulls_upstream(
        self,
    ) -> None:
        host = _RunHostStub()
        host.app_preferences_controller.preview_before_run = False
        workspace_id = host.model.active_workspace.workspace_id
        script = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            0,
            0,
            properties={"script": _script_result("'fresh'")},
        )
        logger = host.model.add_node(workspace_id, "core.logger", "Logger", 160, 0)
        host.model.add_edge(
            workspace_id, script.node_id, "result", logger.node_id, "message"
        )
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_selected_nodes([logger.node_id])

        start_call = host.execution_client.start_calls[-1]
        self.assertEqual(start_call["target_node_ids"], (logger.node_id,))
        self.assertNotIn("run_target_mode", start_call["trigger"])
        self.assertNotIn("target_node_ids", start_call["trigger"])
        self.assertNotIn("seed_node_outputs", start_call["trigger"])
        self.assertEqual(start_call["trigger_publications"], {})

    def test_solution_mode_is_runtime_only_per_workspace_and_open_auto_evaluates_all_active_nodes(
        self,
    ) -> None:
        host = _RunHostStub(default_mode="auto")
        workspace_id = host.model.active_workspace.workspace_id
        logger = host.model.add_node(workspace_id, "core.logger", "Logger", 0, 0)
        controller = RunController(host)  # type: ignore[arg-type]

        self.assertEqual(controller.solution_mode(workspace_id), "auto")
        controller.evaluate_workspace_on_open(workspace_id)

        self.assertEqual(
            host.run_state.solution_mode_by_workspace_id, {workspace_id: "auto"}
        )
        self.assertEqual(
            host.execution_client.start_calls[-1]["trigger"]["kind"], "auto"
        )
        self.assertEqual(
            host.execution_client.start_calls[-1]["target_node_ids"], (logger.node_id,)
        )

        host.run_state.active_run_id = ""
        host.run_state.active_run_workspace_id = ""
        controller.set_auto_run_enabled(False)
        second_workspace = host.model.create_workspace("Second")
        host.workspace_manager.set_active_workspace(second_workspace.workspace_id)

        self.assertEqual(controller.solution_mode(workspace_id), "manual")
        self.assertEqual(
            controller.solution_mode(second_workspace.workspace_id), "auto"
        )

    def test_toggling_auto_on_evaluates_all_active_nodes(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        logger = host.model.add_node(workspace_id, "core.logger", "Logger", 0, 0)
        controller = RunController(host)  # type: ignore[arg-type]

        controller.toggle_auto_run()

        self.assertEqual(
            host.execution_client.start_calls[-1]["trigger"]["kind"], "auto"
        )
        self.assertEqual(
            host.execution_client.start_calls[-1]["target_node_ids"], (logger.node_id,)
        )

    def test_trigger_click_sends_and_updates_typed_runtime_publication_atomically(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        source = host.model.add_node(
            workspace_id,
            "core.constant",
            "Source",
            -100,
            0,
            properties={"value": "latest"},
        )
        trigger = host.model.add_node(workspace_id, "core.trigger", "Trigger", 0, 0)
        host.model.add_edge(
            workspace_id, source.node_id, "value", trigger.node_id, "input"
        )
        controller = RunController(host)  # type: ignore[arg-type]
        old_publication = _value_result("old")
        latest_publication = _value_result("latest")
        host.run_state.trigger_publications_by_workspace_id = {
            workspace_id: {trigger.node_id: old_publication}
        }

        self.assertTrue(controller.trigger_node(trigger.node_id))
        start_call = host.execution_client.start_calls[-1]
        self.assertEqual(start_call["target_node_ids"], (trigger.node_id,))
        self.assertEqual(start_call["clicked_trigger_node_id"], trigger.node_id)
        self.assertEqual(
            start_call["trigger_publications"],
            {trigger.node_id: old_publication},
        )
        self.assertEqual(start_call["trigger_captures"], {})

        controller.handle_execution_event(
            {
                "type": "trigger_capture_settled",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "trigger_node_id": trigger.node_id,
                "result": latest_publication,
            }
        )
        self.assertEqual(
            host.run_state.latest_trigger_inputs_by_workspace_id[workspace_id][
                trigger.node_id
            ],
            latest_publication,
        )
        self.assertEqual(
            host.run_state.trigger_publications_by_workspace_id[workspace_id][
                trigger.node_id
            ],
            old_publication,
        )

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "error": "infrastructure failure",
                "fatal": True,
            }
        )
        self.assertEqual(
            host.run_state.trigger_publications_by_workspace_id[workspace_id][
                trigger.node_id
            ],
            old_publication,
        )

        self.assertTrue(controller.trigger_node(trigger.node_id))
        self.assertEqual(
            host.execution_client.start_calls[-1]["trigger_captures"],
            {trigger.node_id: latest_publication},
        )
        controller.handle_execution_event(
            {
                "type": "run_stopped",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )
        self.assertEqual(
            host.run_state.trigger_publications_by_workspace_id[workspace_id][
                trigger.node_id
            ],
            old_publication,
        )

        self.assertTrue(controller.trigger_node(trigger.node_id))

        revision_before_publish = host.run_state.node_execution_revision
        controller.handle_execution_event(
            {
                "type": "trigger_published",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "trigger_node_id": trigger.node_id,
                "result": latest_publication,
            }
        )
        self.assertEqual(
            host.run_state.latest_trigger_inputs_by_workspace_id[workspace_id][
                trigger.node_id
            ],
            latest_publication,
        )
        self.assertEqual(
            host.run_state.trigger_publications_by_workspace_id[workspace_id][
                trigger.node_id
            ],
            latest_publication,
        )
        self.assertEqual(
            host.run_state.node_execution_revision, revision_before_publish + 1
        )
        controller.handle_execution_event(
            {
                "type": "run_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        controller.run_workflow()
        self.assertEqual(
            host.execution_client.start_calls[-1]["trigger_publications"],
            {trigger.node_id: latest_publication},
        )
        controller.reset_runtime_solution_state()
        self.assertEqual(host.run_state.latest_trigger_inputs_by_workspace_id, {})
        self.assertEqual(host.run_state.trigger_publications_by_workspace_id, {})
        self.assertEqual(
            host.run_state.current_trigger_capture_node_ids_by_workspace_id, {}
        )

    def test_semantic_runtime_carrier_settlements_use_active_catalog(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        signal = host.model.add_node(
            workspace_id, "plot.signal", "Signal Plot", 0, 0
        )
        trigger = host.model.add_node(
            workspace_id, "core.trigger", "Trigger", 200, 0
        )
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id

        controller.handle_execution_event(
            {
                "type": "node_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": signal.node_id,
                "started_at_epoch_ms": 1.0,
            }
        )
        image_result = _value_result(ImageValue.from_png(_PNG_BYTES))
        controller.handle_execution_event(
            event_to_dict(
                NodeSettledEvent(
                    run_id="run_live",
                    workspace_id=workspace_id,
                    node_id=signal.node_id,
                    elapsed_ms=25.0,
                    outputs={"image": image_result},
                ),
                catalog=host.registry.data_types,
            )
        )

        self.assertNotIn(signal.node_id, host.run_state.running_node_ids)
        self.assertIn(signal.node_id, host.run_state.completed_node_ids)
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id[workspace_id][
                signal.node_id
            ],
            25.0,
        )

        controller.handle_execution_event(
            event_to_dict(
                TriggerCaptureSettledEvent(
                    run_id="run_live",
                    workspace_id=workspace_id,
                    trigger_node_id=trigger.node_id,
                    result=image_result,
                ),
                catalog=host.registry.data_types,
            )
        )
        self.assertEqual(
            host.run_state.latest_trigger_inputs_by_workspace_id[workspace_id][
                trigger.node_id
            ],
            image_result,
        )

    def test_trigger_applies_dirty_script_before_building_snapshot(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        script = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            0,
            0,
            properties={"script": _script_result("'old'")},
        )
        trigger = host.model.add_node(
            workspace_id,
            "core.trigger",
            "Trigger",
            160,
            0,
        )
        host.script_editor.dirty = True
        host.script_editor.apply_callback = lambda: host.model.set_node_property(
            workspace_id,
            script.node_id,
            "script",
            _script_result("'draft'"),
        )
        controller = RunController(host)  # type: ignore[arg-type]

        self.assertTrue(controller.trigger_node(trigger.node_id))

        self.assertEqual(host.script_editor.apply_calls, 1)
        runtime_workspace = host.execution_client.start_calls[0]["trigger"][
            "runtime_snapshot"
        ].workspace(workspace_id)
        runtime_script = next(
            node for node in runtime_workspace.nodes if node.node_id == script.node_id
        )
        self.assertEqual(runtime_script.properties["script"], _script_result("'draft'"))

    def test_prune_runtime_solution_state_removes_deleted_workspaces_and_triggers(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        trigger = host.model.add_node(workspace_id, "core.trigger", "Trigger", 0, 0)
        controller = RunController(host)  # type: ignore[arg-type]
        publication = _value_result("held")
        host.run_state.latest_trigger_inputs_by_workspace_id = {
            workspace_id: {trigger.node_id: publication},
            "ws_deleted": {"node_deleted": publication},
        }
        host.run_state.trigger_publications_by_workspace_id = {
            workspace_id: {trigger.node_id: publication},
            "ws_deleted": {"node_deleted": publication},
        }
        host.run_state.current_trigger_capture_node_ids_by_workspace_id = {
            workspace_id: {trigger.node_id},
            "ws_deleted": {"node_deleted"},
        }
        host.run_state.solution_mode_by_workspace_id["ws_deleted"] = "manual"
        host.run_state.cached_node_output_records_by_workspace_id["ws_deleted"] = {}
        host.run_state.cached_node_elapsed_ms_by_workspace_id["ws_deleted"] = {}
        host.run_state.node_output_run_counts_by_workspace_id["ws_deleted"] = {}
        host.run_state.solution_revision_by_workspace_id["ws_deleted"] = 1
        host.run_state.node_solution_facts_by_workspace_id["ws_deleted"] = {}
        host.run_state.runtime_warning_messages_by_workspace_id["ws_deleted"] = {}

        host.model.remove_node(workspace_id, trigger.node_id)
        controller.prune_runtime_solution_state()

        self.assertEqual(host.run_state.latest_trigger_inputs_by_workspace_id, {})
        self.assertEqual(host.run_state.trigger_publications_by_workspace_id, {})
        self.assertEqual(
            host.run_state.current_trigger_capture_node_ids_by_workspace_id, {}
        )
        self.assertNotIn("ws_deleted", host.run_state.solution_mode_by_workspace_id)
        self.assertNotIn(
            "ws_deleted", host.run_state.cached_node_output_records_by_workspace_id
        )
        self.assertNotIn(
            "ws_deleted", host.run_state.cached_node_elapsed_ms_by_workspace_id
        )
        self.assertNotIn(
            "ws_deleted", host.run_state.node_output_run_counts_by_workspace_id
        )
        self.assertNotIn(
            "ws_deleted", host.run_state.solution_revision_by_workspace_id
        )
        self.assertNotIn(
            "ws_deleted", host.run_state.node_solution_facts_by_workspace_id
        )
        self.assertNotIn(
            "ws_deleted", host.run_state.runtime_warning_messages_by_workspace_id
        )

    def test_auto_propagation_stops_at_disabled_edges_and_trigger_boundaries(
        self,
    ) -> None:
        host = _RunHostStub()
        host.registry.register(_PassthroughDependencyPlugin)
        workspace_id = host.model.active_workspace.workspace_id
        source = host.model.add_node(
            workspace_id, "test.passthrough_dependency", "Source", 0, 0
        )
        trigger = host.model.add_node(workspace_id, "core.trigger", "Trigger", 160, 0)
        after_trigger = host.model.add_node(
            workspace_id, "core.logger", "After Trigger", 320, 0
        )
        disabled_target = host.model.add_node(
            workspace_id, "core.logger", "Disabled", 160, 120
        )
        host.model.add_edge(
            workspace_id, source.node_id, "result", trigger.node_id, "input"
        )
        host.model.add_edge(
            workspace_id, trigger.node_id, "output", after_trigger.node_id, "message"
        )
        disabled_edge = host.model.add_edge(
            workspace_id,
            source.node_id,
            "result",
            disabled_target.node_id,
            "message",
        )
        host.model.validated_mutations(workspace_id, host.registry).set_edge_enabled(
            disabled_edge.edge_id,
            False,
        )
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)
        host.run_state.latest_trigger_inputs_by_workspace_id[workspace_id] = {
            trigger.node_id: _value_result("captured")
        }
        host.run_state.current_trigger_capture_node_ids_by_workspace_id[
            workspace_id
        ] = {trigger.node_id}

        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.set_node_property(workspace_id, source.node_id, "note", "changed")
        after_snapshot = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "edit-node-property",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

        self.assertEqual(
            set(host.execution_client.start_calls[-1]["target_node_ids"]),
            {source.node_id, trigger.node_id},
        )
        self.assertNotIn(
            after_trigger.node_id,
            host.execution_client.start_calls[-1]["target_node_ids"],
        )
        self.assertNotIn(
            disabled_target.node_id,
            host.execution_client.start_calls[-1]["target_node_ids"],
        )
        self.assertNotIn(
            trigger.node_id,
            host.run_state.current_trigger_capture_node_ids_by_workspace_id.get(
                workspace_id, set()
            ),
        )

    def test_auto_run_final_required_connection_starts_targeted_run_without_preview(
        self,
    ) -> None:
        host = _RunHostStub()
        host.registry.register(_PassthroughDependencyPlugin)
        host.registry.register(_RequiredPureDataPlugin)
        workspace_id = host.model.active_workspace.workspace_id
        source = host.model.add_node(
            workspace_id, "test.passthrough_dependency", "Source", 0, 0
        )
        target = host.model.add_node(
            workspace_id, "test.required_pure_data", "Target", 160, 0
        )
        controller = RunController(host)  # type: ignore[arg-type]

        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.add_edge(
            workspace_id, source.node_id, "result", target.node_id, "value"
        )
        after_snapshot = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "add-edge",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        self.assertEqual(host.execution_client.start_calls, [])

        controller.set_auto_run_enabled(True)
        rename_before = host.model.active_workspace.capture_snapshot()
        host.model.set_node_title(workspace_id, target.node_id, "Renamed Target")
        rename_after = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "rename-node",
            before_snapshot=rename_before,
            after_snapshot=rename_after,
        )
        self.assertEqual(host.execution_client.start_calls, [])

        disconnected_snapshot = before_snapshot
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "add-edge",
            before_snapshot=disconnected_snapshot,
            after_snapshot=after_snapshot,
        )

        start_call = host.execution_client.start_calls[-1]
        self.assertEqual(start_call["trigger"]["kind"], "auto")
        self.assertEqual(start_call["target_node_ids"], (target.node_id,))
        self.assertEqual(host.run_state.selected_run_preview_rows, [])

    def test_auto_run_targets_active_node_even_with_unresolved_required_input(
        self,
    ) -> None:
        host = _RunHostStub()
        host.registry.register(_RequiredPureDataPlugin)
        workspace_id = host.model.active_workspace.workspace_id
        target = host.model._add_node_record(
            workspace_id,
            type_id="test.required_pure_data",
            title="Target",
            properties={"value": 1},
        )
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)

        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.set_node_property(workspace_id, target.node_id, "value", 2)
        after_snapshot = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "edit-node-property",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        self.assertEqual(len(host.execution_client.start_calls), 1)
        self.assertEqual(
            host.execution_client.start_calls[0]["target_node_ids"], (target.node_id,)
        )

    def test_auto_run_edge_removal_targets_consumer_even_when_input_becomes_unresolved(
        self,
    ) -> None:
        host = _RunHostStub()
        host.registry.register(_PassthroughDependencyPlugin)
        host.registry.register(_RequiredPureDataPlugin)
        workspace_id = host.model.active_workspace.workspace_id
        first = host.model.add_node(
            workspace_id, "test.passthrough_dependency", "First", 0, 0
        )
        second = host.model.add_node(
            workspace_id, "test.passthrough_dependency", "Second", 0, 80
        )
        target = host.model.add_node(
            workspace_id, "test.required_pure_data", "Target", 160, 0
        )
        first_edge = host.model.add_edge(
            workspace_id, first.node_id, "result", target.node_id, "value"
        )
        second_edge = host.model.add_edge(
            workspace_id, second.node_id, "result", target.node_id, "value"
        )
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)

        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.remove_edge(workspace_id, first_edge.edge_id)
        after_snapshot = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "remove-edge",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        self.assertEqual(len(host.execution_client.start_calls), 1)

        host.run_state.active_run_id = ""
        host.run_state.active_run_workspace_id = ""
        host.execution_client.start_calls.clear()
        before_last_removal = host.model.active_workspace.capture_snapshot()
        host.model.remove_edge(workspace_id, second_edge.edge_id)
        after_last_removal = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "remove-edge",
            before_snapshot=before_last_removal,
            after_snapshot=after_last_removal,
        )
        self.assertEqual(len(host.execution_client.start_calls), 1)
        self.assertEqual(
            host.execution_client.start_calls[0]["target_node_ids"], (target.node_id,)
        )

    def test_auto_run_property_edit_targets_all_active_downstream_nodes(self) -> None:
        host = _RunHostStub()
        host.registry.register(_PassthroughDependencyPlugin)
        host.registry.register(_RequiredPureDataPlugin)
        workspace_id = host.model.active_workspace.workspace_id
        source = host.model.add_node(
            workspace_id, "test.passthrough_dependency", "Source", 0, 0
        )
        target = host.model.add_node(
            workspace_id, "test.required_pure_data", "Target", 160, 0
        )
        downstream = host.model.add_node(
            workspace_id,
            "test.passthrough_dependency",
            "Downstream",
            320,
            0,
        )
        unrelated = host.model.add_node(
            workspace_id,
            "test.passthrough_dependency",
            "Unrelated",
            0,
            160,
        )
        logger = host.model.add_node(workspace_id, "core.logger", "Logger", 480, 0)
        host.model.add_edge(
            workspace_id, source.node_id, "result", target.node_id, "value"
        )
        host.model.add_edge(
            workspace_id, target.node_id, "result", downstream.node_id, "value"
        )
        host.model.add_edge(
            workspace_id, downstream.node_id, "result", logger.node_id, "message"
        )
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)

        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.set_node_property(workspace_id, source.node_id, "note", "changed")
        after_snapshot = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "edit-node-property",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

        targets = set(host.execution_client.start_calls[-1]["target_node_ids"])
        self.assertEqual(
            targets,
            {source.node_id, target.node_id, downstream.node_id, logger.node_id},
        )
        self.assertNotIn(unrelated.node_id, targets)

    def test_auto_run_panel_property_edit_projects_current_output_as_flowing(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        panel = host.model.add_node(workspace_id, "data.panel", "Panel", 0, 0)
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)

        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.set_node_property(workspace_id, panel.node_id, "value", "1")
        after_snapshot = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "edit-node-property",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

        self.assertEqual(
            host.execution_client.start_calls[-1]["target_node_ids"], (panel.node_id,)
        )
        changes_before_settle = host.node_execution_state_changed.calls
        controller.handle_execution_event(
            _accepted_settlement(
                host,
                workspace_id=workspace_id,
                node_id=panel.node_id,
                run_id="run_live",
                outputs=_value_outputs(output="1"),
            )
        )

        nodes, _backdrops, _minimap, edges = (
            GraphScenePayloadBuilder().rebuild_partitioned_models(
                model=host.model,
                registry=host.registry,
                workspace_id=workspace_id,
                scope_path=(),
                graph_theme_bridge=None,
            )
        )
        flow_states = resolve_runtime_port_flow_states(
            node_payloads=nodes,
            edge_payloads=edges,
            output_records_by_node=host.run_state.cached_node_output_records_by_workspace_id[
                workspace_id
            ],
            solution_facts_by_node=host.run_state.node_solution_facts_by_workspace_id[
                workspace_id
            ],
        )
        self.assertGreater(
            host.node_execution_state_changed.calls, changes_before_settle
        )
        self.assertEqual(flow_states[panel.node_id]["output"], "flowing")

    def test_auto_run_covers_every_execution_semantic_history_action_family(
        self,
    ) -> None:
        action_types = (
            "add-node",
            "remove-node",
            "toggle-exposed-port",
            "edit-port-modifiers",
            "set-principal-input",
            "insert-dynamic-port",
            "remove-dynamic-port",
            "rename-dynamic-port",
            "duplicate-subgraph",
            "paste-subgraph",
            "group-selected-nodes",
            "ungroup-selected-subnode",
            "delete-selected",
        )
        for action_type in action_types:
            with self.subTest(action_type=action_type):
                host = _RunHostStub()
                workspace_id = host.model.active_workspace.workspace_id
                controller = RunController(host)  # type: ignore[arg-type]
                controller.set_auto_run_enabled(True)
                before_snapshot = host.model.active_workspace.capture_snapshot()
                node = host.model.add_node(
                    workspace_id,
                    "core.logger",
                    "Changed",
                    0,
                    0,
                )
                after_snapshot = host.model.active_workspace.capture_snapshot()
                controller.invalidate_solution_for_history_action(
                    workspace_id,
                    action_type,
                    before_snapshot=before_snapshot,
                    after_snapshot=after_snapshot,
                )

                self.assertEqual(len(host.execution_client.start_calls), 1)
                self.assertEqual(
                    host.execution_client.start_calls[0]["target_node_ids"],
                    (node.node_id,),
                )

    def test_auto_run_edge_enable_change_targets_the_consumer(self) -> None:
        host = _RunHostStub()
        host.registry.register(_PassthroughDependencyPlugin)
        workspace_id = host.model.active_workspace.workspace_id
        source = host.model.add_node(
            workspace_id,
            "test.passthrough_dependency",
            "Source",
            0,
            0,
        )
        target = host.model.add_node(
            workspace_id,
            "core.logger",
            "Target",
            160,
            0,
        )
        edge = host.model.add_edge(
            workspace_id,
            source.node_id,
            "result",
            target.node_id,
            "message",
        )
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)
        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.validated_mutations(workspace_id, host.registry).set_edge_enabled(
            edge.edge_id,
            False,
        )
        after_snapshot = host.model.active_workspace.capture_snapshot()

        controller.invalidate_solution_for_history_action(
            workspace_id,
            "toggle-edge-enabled",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

        self.assertEqual(
            host.execution_client.start_calls[0]["target_node_ids"],
            (target.node_id,),
        )

    def test_auto_run_history_replay_queues_once_for_undo_and_redo(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        node = host.model.add_node(
            workspace_id,
            "core.logger",
            "Changed",
            0,
            0,
        )
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)
        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.set_node_property(workspace_id, node.node_id, "note", "after")
        after_snapshot = host.model.active_workspace.capture_snapshot()

        for restored_snapshot in (before_snapshot, after_snapshot):
            with self.subTest(restored_snapshot=restored_snapshot):
                host.model.active_workspace.restore_snapshot(restored_snapshot)
                host.execution_client.start_calls.clear()
                controller.clear_active_run()
                controller.invalidate_solution_for_history_action(
                    workspace_id,
                    "edit-node-property",
                    before_snapshot=before_snapshot,
                    after_snapshot=after_snapshot,
                )

                self.assertEqual(len(host.execution_client.start_calls), 1)
                self.assertEqual(
                    host.execution_client.start_calls[0]["target_node_ids"],
                    (node.node_id,),
                )

    def test_auto_run_coalesces_active_run_edits_and_rejects_late_outputs(
        self,
    ) -> None:
        host = _RunHostStub()
        host.registry.register(_PassthroughDependencyPlugin)
        host.registry.register(_RequiredPureDataPlugin)
        workspace_id = host.model.active_workspace.workspace_id
        source = host.model.add_node(
            workspace_id, "test.passthrough_dependency", "Source", 0, 0
        )
        target = host.model.add_node(
            workspace_id, "test.required_pure_data", "Target", 160, 0
        )
        host.model.add_edge(
            workspace_id, source.node_id, "result", target.node_id, "value"
        )
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)
        host.run_state.active_run_id = "run_old"
        host.run_state.active_run_workspace_id = workspace_id

        for value in (1, 2):
            before_snapshot = host.model.active_workspace.capture_snapshot()
            host.model.set_node_property(workspace_id, target.node_id, "value", value)
            after_snapshot = host.model.active_workspace.capture_snapshot()
            controller.invalidate_solution_for_history_action(
                workspace_id,
                "edit-node-property",
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
            )

        self.assertEqual(host.execution_client.start_calls, [])
        self.assertEqual(
            host.run_state.pending_auto_run_target_node_ids, {target.node_id}
        )
        controller.handle_execution_event(
            {
                "type": "node_settled",
                "status": "completed",
                "run_id": "run_old",
                "workspace_id": workspace_id,
                "node_id": target.node_id,
                "outputs": _value_outputs(result=1),
                "elapsed_ms": 10.0,
            }
        )
        self.assertNotIn(
            target.node_id,
            host.run_state.cached_node_output_records_by_workspace_id.get(
                workspace_id, {}
            ),
        )

        controller.handle_execution_event(
            {
                "type": "run_completed",
                "run_id": "run_old",
                "workspace_id": workspace_id,
            }
        )
        self.assertEqual(len(host.execution_client.start_calls), 1)
        self.assertEqual(
            host.execution_client.start_calls[0]["trigger"]["kind"], "auto"
        )
        self.assertEqual(host.run_state.pending_auto_run_target_node_ids, set())

    def test_disabling_auto_run_clears_pending_without_stopping_active_run(
        self,
    ) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = (
            host.model.active_workspace.workspace_id
        )
        host.run_state.pending_auto_run_workspace_id = (
            host.model.active_workspace.workspace_id
        )
        host.run_state.pending_auto_run_target_node_ids = {"node_1"}

        controller.set_auto_run_enabled(False)

        self.assertEqual(host.run_state.active_run_id, "run_live")
        self.assertEqual(host.execution_client.stop_calls, [])
        self.assertEqual(host.run_state.pending_auto_run_workspace_id, "")
        self.assertEqual(host.run_state.pending_auto_run_target_node_ids, set())

        controller.set_auto_run_enabled(True)
        host.run_state.pending_auto_run_workspace_id = (
            host.model.active_workspace.workspace_id
        )
        host.run_state.pending_auto_run_target_node_ids = {"node_2"}
        controller.stop_workflow()
        self.assertEqual(host.execution_client.stop_calls, ["run_live"])
        self.assertEqual(host.run_state.pending_auto_run_workspace_id, "")
        self.assertEqual(host.run_state.pending_auto_run_target_node_ids, set())

    def test_fatal_failure_discards_pending_auto_run(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        controller.set_auto_run_enabled(True)
        workspace_id = host.model.active_workspace.workspace_id
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.pending_auto_run_workspace_id = workspace_id
        host.run_state.pending_auto_run_target_node_ids = {"node_1"}

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
                "error": "boom",
                "traceback": "traceback",
                "fatal": True,
            }
        )

        self.assertEqual(host.execution_client.start_calls, [])
        self.assertEqual(host.run_state.pending_auto_run_workspace_id, "")
        self.assertEqual(host.run_state.pending_auto_run_target_node_ids, set())

    def test_node_settled_caches_typed_outputs_by_workspace_node_and_run(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        script = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            0,
            0,
            properties={"script": _script_result("'fresh'")},
        )
        controller = RunController(host)  # type: ignore[arg-type]

        with mock.patch.object(
            controller, "_current_epoch_ms", side_effect=[1000.0, 2000.0]
        ):
            for run_id, result in (("run_1", "first"), ("run_2", "second")):
                host.run_state.active_run_id = run_id
                host.run_state.active_run_workspace_id = workspace_id
                controller.handle_execution_event(
                    _accepted_settlement(
                        host,
                        workspace_id=workspace_id,
                        node_id=script.node_id,
                        run_id=run_id,
                        outputs=_value_outputs(result=result),
                    )
                )

        records = host.run_state.cached_node_output_records_by_workspace_id[
            workspace_id
        ][script.node_id]
        self.assertEqual(len(records), 2)
        self.assertEqual(
            {next(iter(record["outputs"].values())).value.branches[0][1][0] for record in records.values()},
            {"first", "second"},
        )
        self.assertEqual(
            host.run_state.node_output_run_counts_by_workspace_id[workspace_id][
                script.node_id
            ],
            2,
        )

    def test_invalidated_accepted_settlement_cannot_restore_cache_or_availability(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        node = host.model.add_node(workspace_id, "core.constant", "Constant", 0, 0)
        controller = RunController(host)  # type: ignore[arg-type]
        event = _accepted_settlement(
            host,
            workspace_id=workspace_id,
            node_id=node.node_id,
            run_id="run_late",
            outputs=_value_outputs(value="late"),
        )
        accepted = host.execution_client.solution_facts_by_workspace[workspace_id][0]
        host.execution_client.solution_facts_by_workspace[workspace_id] = (
            NodeSolutionFact(
                project_id=accepted.project_id,
                workspace_id=accepted.workspace_id,
                node_id=accepted.node_id,
                freshness=SolutionFreshness.EXPIRED,
                revision=accepted.revision + 1,
                retained_record_id=accepted.retained_record_id,
                retained_solution_key=accepted.retained_solution_key,
                residency=accepted.residency,
                expiration_reason_code="graph_changed",
                expiration_root_node_ids=(node.node_id,),
                last_disposition=accepted.last_disposition,
            ),
        )

        with mock.patch(
            "ea_node_editor.ui.shell.controllers.run_controller.observe_node_outputs"
        ) as observe:
            controller.handle_execution_event(event)

        observe.assert_not_called()
        self.assertNotIn(
            workspace_id,
            host.run_state.cached_node_output_records_by_workspace_id,
        )

    def test_node_settled_caches_compact_dpf_workflow_summary(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        node = host.model.add_node(
            workspace_id,
            "dpf.workflow.result_fields",
            "DPF Result Fields",
            0,
            0,
            properties={"result_name": "stress"},
        )
        fields = RuntimeHandleRef(
            data_type_id="COREX.Ansys.DPF.FieldsContainer",
            schema_version=1,
            handle_id="fields",
            kind="dpf.fields_container",
            owner_scope="run:summary",
            worker_generation=0,
            metadata={
                "result_name": "stress",
                "location": "Nodal",
                "unit": "MPa",
                "field_count": 2,
                "set_ids": [1, 2],
            },
        )
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_summary"
        host.run_state.active_run_workspace_id = workspace_id

        controller.handle_execution_event(
            _accepted_settlement(
                host,
                workspace_id=workspace_id,
                node_id=node.node_id,
                run_id="run_summary",
                outputs=_value_outputs(fields=fields),
            )
        )

        record = next(
            iter(
                host.run_state.cached_node_output_records_by_workspace_id[
                    workspace_id
                ][node.node_id].values()
            )
        )
        self.assertEqual(
            record["dpf_workflow_summary"],
            {
                "state": "ready",
                "headline": "Stress · 2 fields",
                "detail": "Nodal · MPa",
                "facts": [
                    {"label": "Result", "value": "Stress"},
                    {"label": "Location", "value": "Nodal"},
                    {"label": "Unit", "value": "MPa"},
                    {"label": "Fields", "value": "2"},
                ],
            },
        )

    def test_graph_change_expires_fact_without_mutating_cached_records(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        script = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            0,
            0,
            properties={"script": _script_result("'fresh'")},
        )
        controller = RunController(host)  # type: ignore[arg-type]

        with mock.patch.object(
            controller, "_current_epoch_ms", side_effect=[1000.0, 2000.0]
        ):
            for run_id, result in (("run_1", "first"), ("run_2", "second")):
                host.run_state.active_run_id = run_id
                host.run_state.active_run_workspace_id = workspace_id
                controller.handle_execution_event(
                    _accepted_settlement(
                        host,
                        workspace_id=workspace_id,
                        node_id=script.node_id,
                        run_id=run_id,
                        outputs=_value_outputs(result=result),
                    )
                )
        host.run_state.active_run_id = ""
        host.run_state.active_run_workspace_id = ""

        changed = controller.invalidate_solution_for_history_action(
            workspace_id, "add-edge"
        )

        self.assertTrue(changed)
        records = host.run_state.cached_node_output_records_by_workspace_id[
            workspace_id
        ][script.node_id]
        self.assertTrue(all("stale" not in record for record in records.values()))
        projected = retained_output_record(
            host.run_state,
            workspace_id,
            script.node_id,
        )
        self.assertIsNotNone(projected)
        self.assertTrue(projected["stale"])
        self.assertEqual(projected["stale_reason"], "graph_changed")

    def test_graph_change_marks_changed_node_and_downstream_run_records_stale(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        upstream = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Upstream",
            0,
            0,
            properties={"script": _script_result("'upstream'")},
        )
        middle = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Middle",
            180,
            0,
            properties={"script": _script_result("'middle'")},
        )
        downstream = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Downstream",
            360,
            0,
            properties={"script": _script_result("'downstream'")},
        )
        unrelated = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Unrelated",
            0,
            180,
            properties={"script": _script_result("'unrelated'")},
        )
        host.model.add_edge(
            workspace_id, upstream.node_id, "result", middle.node_id, "payload"
        )
        host.model.add_edge(
            workspace_id, middle.node_id, "result", downstream.node_id, "payload"
        )
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_1"
        host.run_state.active_run_workspace_id = workspace_id
        for index, node in enumerate(
            (upstream, middle, downstream, unrelated), start=1
        ):
            event = _accepted_settlement(
                host,
                workspace_id=workspace_id,
                node_id=node.node_id,
                run_id="run_1",
                outputs=_value_outputs(result=node.title),
            )
            event["elapsed_ms"] = float(index * 100)
            controller.handle_execution_event(event)
        host.run_state.active_run_id = ""
        host.run_state.active_run_workspace_id = ""
        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.set_node_property(
            workspace_id, middle.node_id, "script", _script_result("'changed'")
        )
        after_snapshot = host.model.active_workspace.capture_snapshot()

        changed = controller.invalidate_solution_for_history_action(
            workspace_id,
            "edit-node-property",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

        self.assertTrue(changed)
        self.assertEqual(
            {
                node_id: fact.freshness
                for node_id, fact in host.run_state.node_solution_facts_by_workspace_id[
                    workspace_id
                ].items()
            },
            {
                upstream.node_id: SolutionFreshness.CURRENT,
                middle.node_id: SolutionFreshness.EXPIRED,
                downstream.node_id: SolutionFreshness.EXPIRED,
                unrelated.node_id: SolutionFreshness.CURRENT,
            },
        )
        self.assertEqual(
            set(host.run_state.cached_node_elapsed_ms_by_workspace_id[workspace_id]),
            {upstream.node_id, unrelated.node_id},
        )
        records_by_node = host.run_state.cached_node_output_records_by_workspace_id[
            workspace_id
        ]
        self.assertTrue(
            all(
                "stale" not in record
                for records in records_by_node.values()
                for record in records.values()
            )
        )
        self.assertTrue(
            retained_output_record(host.run_state, workspace_id, middle.node_id)[
                "stale"
            ]
        )
        self.assertFalse(
            retained_output_record(host.run_state, workspace_id, unrelated.node_id)[
                "stale"
            ]
        )

        cosmetic_before = host.model.active_workspace.capture_snapshot()
        host.model.set_node_title(workspace_id, upstream.node_id, "Renamed Upstream")
        cosmetic_after = host.model.active_workspace.capture_snapshot()
        cosmetic_changed = controller.invalidate_solution_for_history_action(
            workspace_id,
            "rename-node",
            before_snapshot=cosmetic_before,
            after_snapshot=cosmetic_after,
        )

        self.assertFalse(cosmetic_changed)
        self.assertIs(
            host.run_state.node_solution_facts_by_workspace_id[workspace_id][
                upstream.node_id
            ].freshness,
            SolutionFreshness.CURRENT,
        )

    def test_run_selected_group_targets_executable_contents_only(self) -> None:
        host = _RunHostStub()
        host.app_preferences_controller.preview_before_run = False
        workspace_id = host.model.active_workspace.workspace_id
        group = host.model.add_node(workspace_id, "core.subnode", "Group", 0, 0)
        logger = host.model._add_node_record(
            workspace_id,
            type_id="core.logger",
            title="Logger",
            x=40,
            y=40,
            parent_node_id=group.node_id,
        )
        host.model._add_node_record(
            workspace_id,
            type_id="passive.annotation.sticky_note",
            title="Note",
            x=70,
            y=70,
            parent_node_id=group.node_id,
        )
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_selected_nodes([group.node_id])

        start_call = host.execution_client.start_calls[-1]
        self.assertEqual(start_call["target_node_ids"], (logger.node_id,))

    def test_run_selected_nodes_preview_waits_for_confirmation_by_default(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        script = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            160,
            0,
        )
        host.script_editor.dirty = True
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_selected_nodes([script.node_id])

        self.assertEqual(host.execution_client.start_calls, [])
        self.assertEqual(host.script_editor.apply_calls, 0)
        self.assertEqual(host.run_state.selected_run_preview_workspace_id, workspace_id)
        self.assertEqual(
            host.run_state.selected_run_preview_target_node_ids, (script.node_id,)
        )
        self.assertEqual(
            host.run_state.selected_run_preview_node_lookup, {script.node_id: "run"}
        )
        controller.confirm_selected_run_preview()

        self.assertEqual(len(host.execution_client.start_calls), 1)
        self.assertEqual(host.script_editor.apply_calls, 1)
        self.assertEqual(host.run_state.selected_run_preview_rows, [])

    def test_auto_run_uses_applied_model_without_applying_dirty_script_draft(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        script = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            160,
            0,
            properties={"script": _script_result("'applied'")},
        )
        host.script_editor.dirty = True
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_selected_nodes(
            [script.node_id],
            trigger_kind="auto",
        )

        self.assertEqual(host.script_editor.apply_calls, 0)
        self.assertEqual(len(host.execution_client.start_calls), 1)
        runtime_workspace = host.execution_client.start_calls[0]["trigger"][
            "runtime_snapshot"
        ].workspace(workspace_id)
        runtime_script = next(
            node for node in runtime_workspace.nodes if node.node_id == script.node_id
        )
        self.assertEqual(runtime_script.properties["script"], _script_result("'applied'"))

    def test_run_workflow_logs_error_when_start_fails(self) -> None:
        host = _RunHostStub()
        host.execution_client.next_run_id = ""
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()

        self.assertEqual(
            host.console_panel.logs[-1], ("error", "Failed to start workflow run.")
        )
        self.assertEqual(host._notifications, (0, 1))
        self.assertEqual(host.run_state.active_run_id, "")
        self.assertEqual(host.run_state.engine_state_value, "error")
        self.assertEqual(host._engine_status, ("error", "Start Failed"))
        self.assertEqual(host._job_counters, (0, 0, 0, 1))
        self.assert_run_controls(
            host,
            run_enabled=True,
            pause_enabled=False,
            stop_enabled=False,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_update_run_actions_idle_selected_workspace_enables_only_run(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.update_run_actions()

        self.assert_run_controls(
            host,
            run_enabled=True,
            pause_enabled=False,
            stop_enabled=False,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_update_run_actions_selected_workspace_owner_running_disables_run_and_enables_pause_stop(
        self,
    ) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = (
            host.model.active_workspace.workspace_id
        )
        host.run_state.engine_state_value = "running"

        controller.update_run_actions()

        self.assert_run_controls(
            host,
            run_enabled=False,
            pause_enabled=True,
            stop_enabled=True,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_update_run_actions_selected_workspace_owner_paused_uses_resume_label(
        self,
    ) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = (
            host.model.active_workspace.workspace_id
        )
        host.run_state.engine_state_value = "paused"

        controller.update_run_actions()

        self.assert_run_controls(
            host,
            run_enabled=False,
            pause_enabled=True,
            stop_enabled=True,
            pause_label="Resume",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_update_run_actions_non_owning_selected_workspace_disables_pause_and_stop(
        self,
    ) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        owning_workspace_id = host.model.active_workspace.workspace_id
        other_workspace = host.model.create_workspace(name="Second Workspace")
        host.workspace_manager.set_active_workspace(other_workspace.workspace_id)
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = owning_workspace_id
        host.run_state.engine_state_value = "running"

        controller.update_run_actions()

        self.assert_run_controls(
            host,
            run_enabled=True,
            pause_enabled=False,
            stop_enabled=False,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_toggle_pause_resume_and_stop_route_to_execution_client(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.engine_state_value = "running"

        controller.toggle_pause_resume()
        self.assertEqual(host.execution_client.pause_calls, ["run_live"])
        self.assertEqual(host._engine_status, ("running", "Pausing"))

        host.run_state.engine_state_value = "paused"
        controller.toggle_pause_resume()
        self.assertEqual(host.execution_client.resume_calls, ["run_live"])
        self.assertEqual(host._engine_status, ("running", "Resuming"))

        controller.stop_workflow()
        self.assertEqual(host.execution_client.stop_calls, ["run_live"])
        self.assertEqual(host._engine_status, ("paused", "Stopping"))

    def test_stale_run_event_is_ignored(self) -> None:
        host = _RunHostStub()
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = (
            host.model.active_workspace.workspace_id
        )
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "log",
                "run_id": "run_stale",
                "workspace_id": host.model.active_workspace.workspace_id,
                "level": "error",
                "message": "should be ignored",
            }
        )

        self.assertEqual(host.console_panel.logs, [])
        self.assertEqual(host.run_state.active_run_id, "run_live")

    def test_run_failed_event_focuses_node_logs_traceback_and_clears_active_run(
        self,
    ) -> None:
        host = _RunHostStub()
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = (
            host.model.active_workspace.workspace_id
        )
        host.run_state.engine_state_value = "running"
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": host.model.active_workspace.workspace_id,
                "node_id": "node_1",
                "error": "boom",
                "traceback": "traceback: line 1",
            }
        )

        self.assertEqual(
            host.console_panel.logs[-2:],
            [("error", "boom"), ("error", "traceback: line 1")],
        )
        self.assertEqual(host._notifications, (0, 2))
        self.assertEqual(
            host.workspace_library_controller.focus_calls,
            [(host.model.active_workspace.workspace_id, "node_1")],
        )
        self.assertEqual(host.run_state.active_run_id, "")
        self.assertEqual(host.run_state.active_run_workspace_id, "")
        self.assertEqual(host.run_state.engine_state_value, "error")
        self.assert_run_controls(
            host,
            run_enabled=True,
            pause_enabled=False,
            stop_enabled=False,
            pause_label="Pause",
        )

    def test_protocol_error_is_logged(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {"type": "protocol_error", "error": "bad payload"}
        )

        self.assertEqual(host.console_panel.logs, [("error", "bad payload")])
        self.assertEqual(host._notifications, (0, 1))

    def test_node_execution_bridge_run_events_project_running_and_completed_nodes(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.running_node_ids.add("node_stale")
        host.run_state.failed_workspace_id = workspace_id
        host.run_state.failed_node_id = "node_failed"
        host.run_state.failed_node_title = "Failed Node"
        host.run_state.node_execution_revision = 4
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_failure_changed.calls, 1)
        self.assertEqual(host.run_state.failed_workspace_id, "")
        self.assertEqual(host.run_state.failed_node_id, "")
        self.assertEqual(host.run_state.failed_node_title, "")
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.node_execution_revision, 5)

        controller.handle_execution_event(
            {
                "type": "node_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, workspace_id)
        self.assertEqual(host.run_state.running_node_ids, {"node_1"})
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.node_execution_revision, 6)

        controller.handle_execution_event(
            {
                "type": "node_settled",
                "status": "completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
            }
        )

        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, {"node_1"})
        self.assertEqual(host.run_state.node_execution_revision, 7)
        self.assertEqual(host._engine_status, ("running", "Running"))

    def test_node_settled_projects_empty_failed_blocked_and_original_root_errors(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        node = host.model.add_node(workspace_id, "core.logger", "Logger", 0, 0)
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        controller = RunController(host)  # type: ignore[arg-type]
        root_error = RootExecutionError(
            node_id="node_root",
            error="root failure",
            traceback="root trace",
        )

        controller.handle_execution_event(
            {
                "type": "node_settled",
                "status": "failed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": node.node_id,
                "errors": (root_error,),
            }
        )
        self.assertEqual(host.run_state.failed_node_ids, {node.node_id})
        self.assertEqual(
            host.run_state.root_errors_by_node_id[node.node_id], (root_error,)
        )
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(
            host.workspace_library_controller.focus_calls,
            [(workspace_id, node.node_id)],
        )

        controller.handle_execution_event(
            {
                "type": "node_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": node.node_id,
            }
        )
        controller.handle_execution_event(
            {
                "type": "node_settled",
                "status": "empty",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": node.node_id,
            }
        )
        self.assertEqual(host.run_state.empty_node_ids, {node.node_id})
        self.assertNotIn(node.node_id, host.run_state.root_errors_by_node_id)
        self.assertEqual(
            host.workspace_library_controller.focus_calls,
            [(workspace_id, node.node_id)],
        )

        controller.handle_execution_event(
            {
                "type": "node_settled",
                "status": "blocked",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": node.node_id,
                "errors": (root_error,),
            }
        )
        self.assertEqual(host.run_state.blocked_node_ids, {node.node_id})
        self.assertEqual(
            host.run_state.root_errors_by_node_id[node.node_id], (root_error,)
        )
        self.assertEqual(host.run_state.empty_node_ids, set())
        self.assertEqual(
            host.workspace_library_controller.focus_calls,
            [(workspace_id, node.node_id)],
        )

    def test_runtime_warning_messages_persist_until_node_rerun_or_graph_invalidation(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        node = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            0,
            0,
            properties={"script": _script_result("1")},
        )
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_warning"
        host.run_state.active_run_workspace_id = workspace_id

        controller.handle_execution_event(
            {
                "type": "node_settled",
                "status": "completed",
                "run_id": "run_warning",
                "workspace_id": workspace_id,
                "node_id": node.node_id,
                "warnings": [
                    "  Mesh quality was reduced.  ",
                    "Mesh quality was reduced.",
                ],
            }
        )
        self.assertEqual(
            host.run_state.runtime_warning_messages_by_workspace_id,
            {workspace_id: {node.node_id: ("Mesh quality was reduced.",)}},
        )

        controller.handle_execution_event(
            {
                "type": "run_completed",
                "run_id": "run_warning",
                "workspace_id": workspace_id,
            }
        )
        self.assertIn(
            node.node_id,
            host.run_state.runtime_warning_messages_by_workspace_id[workspace_id],
        )

        controller.mark_node_execution_running(workspace_id, node.node_id)
        self.assertNotIn(
            workspace_id, host.run_state.runtime_warning_messages_by_workspace_id
        )

        controller.mark_node_execution_settled(
            workspace_id,
            node.node_id,
            status="completed",
            warning=True,
            warning_messages=("Review the result.",),
        )
        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.set_node_property(
            workspace_id, node.node_id, "script", _script_result("2")
        )
        after_snapshot = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "edit-node-property",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        self.assertNotIn(
            workspace_id, host.run_state.runtime_warning_messages_by_workspace_id
        )

        host.run_state.active_run_id = "run_invalidated"
        host.run_state.active_run_workspace_id = workspace_id
        controller.mark_node_execution_running(workspace_id, node.node_id)
        before_snapshot = host.model.active_workspace.capture_snapshot()
        host.model.set_node_property(
            workspace_id, node.node_id, "script", _script_result("3")
        )
        after_snapshot = host.model.active_workspace.capture_snapshot()
        controller.invalidate_solution_for_history_action(
            workspace_id,
            "edit-node-property",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        controller.handle_execution_event(
            {
                "type": "node_settled",
                "status": "completed",
                "run_id": "run_invalidated",
                "workspace_id": workspace_id,
                "node_id": node.node_id,
                "warnings": ("Stale warning must not survive.",),
            }
        )
        self.assertNotIn(
            workspace_id, host.run_state.runtime_warning_messages_by_workspace_id
        )
        self.assertNotIn(node.node_id, host.run_state.warning_node_ids)

    def test_persistent_node_elapsed_state_projects_fallback_started_at_and_cached_elapsed_by_workspace(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.running_node_ids.add("node_stale")
        host.run_state.running_node_started_at_epoch_ms_by_node_id["node_stale"] = 500.0
        host.run_state.cached_node_elapsed_ms_by_workspace_id = {
            "ws_previous": {
                "node_cached": 12.5,
            }
        }
        host.run_state.node_execution_revision = 4
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.running_node_started_at_epoch_ms_by_node_id, {})
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id,
            {"ws_previous": {"node_cached": 12.5}},
        )

        with mock.patch(
            "ea_node_editor.ui.shell.controllers.run_controller.time.time",
            return_value=100.0,
        ):
            controller.handle_execution_event(
                {
                    "type": "node_started",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": "node_1",
                    "started_at_epoch_ms": 0.0,
                }
            )

        self.assertEqual(
            host.run_state.running_node_started_at_epoch_ms_by_node_id,
            {"node_1": 100000.0},
        )

        with mock.patch(
            "ea_node_editor.ui.shell.controllers.run_controller.time.time",
            return_value=100.04525,
        ):
            controller.handle_execution_event(
                {
                    "type": "node_settled",
                    "status": "completed",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": "node_1",
                    "elapsed_ms": 0.0,
                }
            )

        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, {"node_1"})
        self.assertEqual(host.run_state.running_node_started_at_epoch_ms_by_node_id, {})
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id["ws_previous"],
            {"node_cached": 12.5},
        )
        self.assertAlmostEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id[workspace_id][
                "node_1"
            ],
            45.25,
            places=2,
        )

        controller.handle_execution_event(
            {
                "type": "run_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, workspace_id)
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, {"node_1"})
        self.assertEqual(host.run_state.running_node_started_at_epoch_ms_by_node_id, {})
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id["ws_previous"],
            {"node_cached": 12.5},
        )
        self.assertAlmostEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id[workspace_id][
                "node_1"
            ],
            45.25,
            places=2,
        )

    def test_node_settled_after_pause_preserves_paused_state_and_resume_action(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.engine_state_value = "running"
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_state",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "state": "paused",
                "transition": "pause",
            }
        )
        controller.handle_execution_event(
            {
                "type": "node_settled",
                "status": "completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
            }
        )

        self.assertEqual(host.run_state.engine_state_value, "paused")
        self.assertEqual(host._engine_status, ("paused", "Paused"))
        self.assert_run_controls(
            host,
            run_enabled=False,
            pause_enabled=True,
            stop_enabled=True,
            pause_label="Resume",
        )

        controller.toggle_pause_resume()

        self.assertEqual(host.execution_client.resume_calls, ["run_live"])
        self.assertEqual(host._engine_status, ("running", "Resuming"))

    def test_persistent_node_elapsed_state_nonfatal_run_failed_clears_transient_execution_state_and_preserves_cache(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.running_node_ids.add("node_1")
        host.run_state.running_node_started_at_epoch_ms_by_node_id["node_1"] = 1000.0
        host.run_state.cached_node_elapsed_ms_by_workspace_id = {
            workspace_id: {
                "node_cached": 33.0,
            }
        }
        host.run_state.node_execution_revision = 2
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
                "error": "boom",
                "traceback": "traceback: line 1",
                "fatal": False,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, "")
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.running_node_started_at_epoch_ms_by_node_id, {})
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id,
            {workspace_id: {"node_cached": 33.0}},
        )
        self.assertEqual(host.run_state.node_execution_revision, 3)
        self.assertEqual(host.run_state.active_run_id, "")

    def test_run_completed_preserves_settled_state_while_stop_and_failure_clear_it(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.cached_node_elapsed_ms_by_workspace_id = {
            workspace_id: {"node_cached": 12.5},
            "ws_other": {"node_other": 8.0},
        }

        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.completed_node_ids.add("node_1")
        host.run_state.node_execution_revision = 1

        controller.handle_execution_event(
            {
                "type": "run_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, workspace_id)
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, {"node_1"})
        self.assertEqual(host.run_state.running_node_started_at_epoch_ms_by_node_id, {})
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id,
            {
                workspace_id: {"node_cached": 12.5},
                "ws_other": {"node_other": 8.0},
            },
        )
        self.assertEqual(host.run_state.node_execution_revision, 1)

        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.completed_node_ids.add("node_2")
        host.run_state.running_node_started_at_epoch_ms_by_node_id["node_2"] = 2000.0

        controller.handle_execution_event(
            {
                "type": "run_stopped",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, "")
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.running_node_started_at_epoch_ms_by_node_id, {})
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id,
            {
                workspace_id: {"node_cached": 12.5},
                "ws_other": {"node_other": 8.0},
            },
        )
        self.assertEqual(host.run_state.node_execution_revision, 2)

        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.running_node_ids.add("node_3")
        host.run_state.running_node_started_at_epoch_ms_by_node_id["node_3"] = 3000.0

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_3",
                "error": "fatal boom",
                "traceback": "traceback: line 9",
                "fatal": True,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, "")
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.running_node_started_at_epoch_ms_by_node_id, {})
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id,
            {
                workspace_id: {"node_cached": 12.5},
                "ws_other": {"node_other": 8.0},
            },
        )
        self.assertEqual(host.run_state.node_execution_revision, 3)


if __name__ == "__main__":
    unittest.main()
