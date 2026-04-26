from __future__ import annotations

import time
import unittest
from unittest import mock

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.controllers.run_controller import RunController
from ea_node_editor.ui.shell.state import ShellRunState

_EXECUTION_EDGE_PORT_KINDS = frozenset({"exec", "completed", "failed"})


def _coerce_nonnegative_timing_ms(value: object) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return 0.0
    return normalized if normalized >= 0.0 else 0.0


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
        return {"project_id": project.project_id, "workspace_count": len(project.workspaces)}


class _ProjectSessionControllerStub:
    def workflow_settings_payload(self) -> dict:
        return {"general": {"project_name": "Demo"}}


class _ExecutionClientStub:
    def __init__(self) -> None:
        self.next_run_id = "run_live"
        self.start_calls: list[dict] = []
        self.pause_calls: list[str] = []
        self.resume_calls: list[str] = []
        self.stop_calls: list[str] = []

    def start_run(self, *, project_path: str, workspace_id: str, trigger: dict) -> str:
        self.start_calls.append(
            {
                "project_path": project_path,
                "workspace_id": workspace_id,
                "trigger": trigger,
            }
        )
        return self.next_run_id

    def pause_run(self, run_id: str) -> None:
        self.pause_calls.append(run_id)

    def resume_run(self, run_id: str) -> None:
        self.resume_calls.append(run_id)

    def stop_run(self, run_id: str) -> None:
        self.stop_calls.append(run_id)


class _WorkspaceLibraryControllerStub:
    def __init__(self) -> None:
        self.focus_calls: list[tuple[str, str, str]] = []

    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        self.focus_calls.append((workspace_id, node_id, error))


class _RunHostStub:
    _RUN_SCOPED_EVENT_TYPES = {
        "run_started",
        "run_state",
        "run_completed",
        "run_failed",
        "run_stopped",
        "node_started",
        "node_completed",
        "node_failed_handled",
        "log",
    }

    def __init__(self) -> None:
        self.run_state = ShellRunState()
        self.project_path = "demo.sfe"
        self.model = GraphModel()
        self.workspace_manager = _WorkspaceManagerStub(self.model.active_workspace.workspace_id)
        self.serializer = _SerializerStub()
        self.registry = build_default_registry()
        self.project_session_controller = _ProjectSessionControllerStub()
        self.console_panel = _ConsoleStub()
        self.execution_client = _ExecutionClientStub()
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

    def _normalize_node_execution_workspace_id(self, workspace_id: str) -> str:
        normalized_workspace_id = str(workspace_id or "").strip()
        if normalized_workspace_id:
            return normalized_workspace_id
        return str(self.run_state.active_run_workspace_id or self.run_state.node_execution_workspace_id or "").strip()

    def _normalize_execution_edge_workspace_id(self, workspace_id: str) -> str:
        normalized_workspace_id = str(workspace_id or "").strip()
        if normalized_workspace_id:
            return normalized_workspace_id
        return str(
            self.run_state.active_run_workspace_id
            or self.run_state.execution_edge_workspace_id
            or self.run_state.node_execution_workspace_id
            or ""
        ).strip()

    def _clear_execution_edge_progress_state_fields(self) -> bool:
        state = self.run_state
        if not (
            state.execution_edge_run_id
            or state.execution_edge_workspace_id
            or state.execution_edge_ids_by_source_node_id
            or state.progressed_execution_edge_ids
        ):
            return False
        state.execution_edge_run_id = ""
        state.execution_edge_workspace_id = ""
        state.execution_edge_ids_by_source_node_id.clear()
        state.progressed_execution_edge_ids.clear()
        return True

    def _build_execution_edge_progress_index(
        self,
        *,
        workspace_id: str,
        runtime_snapshot,
    ) -> tuple[str, dict[str, dict[str, tuple[str, ...]]]]:  # noqa: ANN001
        normalized_workspace_id = str(workspace_id or "").strip()
        if runtime_snapshot is None:
            return normalized_workspace_id, {}
        if not normalized_workspace_id:
            normalized_workspace_id = str(runtime_snapshot.active_workspace_id or "").strip()
        if not normalized_workspace_id:
            return "", {}
        try:
            workspace = runtime_snapshot.workspace(normalized_workspace_id)
        except KeyError:
            return normalized_workspace_id, {}

        nodes_by_id = workspace.nodes_by_id
        port_kinds_by_node_id: dict[str, dict[str, str]] = {}
        indexed_edge_ids: dict[str, dict[str, list[str]]] = {}
        for edge in workspace.edges:
            edge_id = str(edge.edge_id or "").strip()
            source_node_id = str(edge.source_node_id or "").strip()
            source_port_key = str(edge.source_port_key or "").strip()
            if not edge_id or not source_node_id or not source_port_key:
                continue
            port_kinds = port_kinds_by_node_id.get(source_node_id)
            if port_kinds is None:
                source_node = nodes_by_id.get(source_node_id)
                spec = self.registry.get_spec(source_node.type_id) if source_node is not None else None
                port_kinds = {
                    str(port.key): str(port.kind or "").strip().lower()
                    for port in getattr(spec, "ports", ())
                }
                port_kinds_by_node_id[source_node_id] = port_kinds
            port_kind = port_kinds.get(source_port_key, "")
            if port_kind not in _EXECUTION_EDGE_PORT_KINDS:
                continue
            indexed_edge_ids.setdefault(source_node_id, {}).setdefault(port_kind, []).append(edge_id)

        return normalized_workspace_id, {
            source_node_id: {
                port_kind: tuple(edge_ids)
                for port_kind, edge_ids in port_kind_map.items()
            }
            for source_node_id, port_kind_map in indexed_edge_ids.items()
        }

    def update_notification_counters(self, warnings: int, errors: int) -> None:
        self._notifications = (warnings, errors)

    def update_engine_status(self, state: str, details: str = "") -> None:
        self._engine_status = (state, details)

    def update_job_counters(self, running: int, queued: int, done: int, failed: int) -> None:
        self._job_counters = (running, queued, done, failed)

    def clear_run_failure_focus(self) -> None:
        self._failure_clear_count += 1

    def mark_node_execution_running(
        self,
        workspace_id: str,
        node_id: str,
        *,
        started_at_epoch_ms: float = 0.0,
    ) -> None:
        normalized_node_id = str(node_id or "").strip()
        if not normalized_node_id:
            return
        normalized_workspace_id = self._normalize_node_execution_workspace_id(workspace_id)
        if not normalized_workspace_id:
            return
        resolved_started_at_epoch_ms = _coerce_nonnegative_timing_ms(started_at_epoch_ms)
        if resolved_started_at_epoch_ms <= 0.0:
            resolved_started_at_epoch_ms = time.time() * 1000.0
        state = self.run_state
        changed = False
        if state.node_execution_workspace_id != normalized_workspace_id:
            state.node_execution_workspace_id = normalized_workspace_id
            state.running_node_ids.clear()
            state.completed_node_ids.clear()
            state.running_node_started_at_epoch_ms_by_node_id.clear()
            changed = True
        if normalized_node_id in state.completed_node_ids:
            state.completed_node_ids.discard(normalized_node_id)
            changed = True
        if normalized_node_id not in state.running_node_ids:
            state.running_node_ids.add(normalized_node_id)
            changed = True
        if (
            state.running_node_started_at_epoch_ms_by_node_id.get(normalized_node_id)
            != resolved_started_at_epoch_ms
        ):
            state.running_node_started_at_epoch_ms_by_node_id[normalized_node_id] = resolved_started_at_epoch_ms
            changed = True
        if changed:
            state.node_execution_revision += 1

    def mark_node_execution_completed(
        self,
        workspace_id: str,
        node_id: str,
        *,
        elapsed_ms: float = 0.0,
    ) -> None:
        normalized_node_id = str(node_id or "").strip()
        if not normalized_node_id:
            return
        normalized_workspace_id = self._normalize_node_execution_workspace_id(workspace_id)
        if not normalized_workspace_id:
            return
        state = self.run_state
        changed = False
        if state.node_execution_workspace_id != normalized_workspace_id:
            state.node_execution_workspace_id = normalized_workspace_id
            state.running_node_ids.clear()
            state.completed_node_ids.clear()
            state.running_node_started_at_epoch_ms_by_node_id.clear()
            changed = True
        started_at_lookup = state.running_node_started_at_epoch_ms_by_node_id
        had_started_at = normalized_node_id in started_at_lookup
        started_at_epoch_ms = started_at_lookup.pop(normalized_node_id, 0.0)
        if had_started_at:
            changed = True
        if normalized_node_id in state.running_node_ids:
            state.running_node_ids.discard(normalized_node_id)
            changed = True
        if normalized_node_id not in state.completed_node_ids:
            state.completed_node_ids.add(normalized_node_id)
            changed = True
        worker_elapsed_ms = _coerce_nonnegative_timing_ms(elapsed_ms)
        should_cache_elapsed = False
        resolved_elapsed_ms = 0.0
        if worker_elapsed_ms > 0.0:
            resolved_elapsed_ms = worker_elapsed_ms
            should_cache_elapsed = True
        elif started_at_epoch_ms > 0.0:
            resolved_elapsed_ms = max(0.0, (time.time() * 1000.0) - started_at_epoch_ms)
            should_cache_elapsed = True
        if should_cache_elapsed:
            workspace_cache = state.cached_node_elapsed_ms_by_workspace_id.setdefault(
                normalized_workspace_id,
                {},
            )
            if workspace_cache.get(normalized_node_id) != resolved_elapsed_ms:
                workspace_cache[normalized_node_id] = resolved_elapsed_ms
                changed = True
        if changed:
            state.node_execution_revision += 1

    def seed_execution_edge_progress_state(
        self,
        *,
        run_id: str,
        workspace_id: str,
        runtime_snapshot,
    ) -> None:  # noqa: ANN001
        normalized_run_id = str(run_id or "").strip()
        normalized_workspace_id, edge_index = self._build_execution_edge_progress_index(
            workspace_id=workspace_id,
            runtime_snapshot=runtime_snapshot,
        )
        state = self.run_state
        changed = self._clear_execution_edge_progress_state_fields()
        if state.execution_edge_run_id != normalized_run_id:
            state.execution_edge_run_id = normalized_run_id
            changed = True
        if state.execution_edge_workspace_id != normalized_workspace_id:
            state.execution_edge_workspace_id = normalized_workspace_id
            changed = True
        if state.execution_edge_ids_by_source_node_id != edge_index:
            state.execution_edge_ids_by_source_node_id = edge_index
            changed = True
        if changed:
            state.node_execution_revision += 1

    def mark_execution_edges_progressed(
        self,
        workspace_id: str,
        node_id: str,
        source_port_kinds: tuple[str, ...],
    ) -> None:
        normalized_node_id = str(node_id or "").strip()
        if not normalized_node_id:
            return
        normalized_workspace_id = self._normalize_execution_edge_workspace_id(workspace_id)
        state = self.run_state
        if not normalized_workspace_id or state.execution_edge_workspace_id != normalized_workspace_id:
            return
        node_edge_ids = state.execution_edge_ids_by_source_node_id.get(normalized_node_id)
        if not node_edge_ids:
            return
        changed = False
        for source_port_kind in source_port_kinds:
            normalized_port_kind = str(source_port_kind or "").strip().lower()
            if normalized_port_kind not in _EXECUTION_EDGE_PORT_KINDS:
                continue
            for edge_id in node_edge_ids.get(normalized_port_kind, ()):
                if edge_id in state.progressed_execution_edge_ids:
                    continue
                state.progressed_execution_edge_ids.add(edge_id)
                changed = True
        if changed:
            state.node_execution_revision += 1

    def clear_node_execution_visualization_state(self) -> None:
        state = self.run_state
        changed = False
        if (
            state.node_execution_workspace_id
            or state.running_node_ids
            or state.completed_node_ids
            or state.running_node_started_at_epoch_ms_by_node_id
        ):
            state.node_execution_workspace_id = ""
            state.running_node_ids.clear()
            state.completed_node_ids.clear()
            state.running_node_started_at_epoch_ms_by_node_id.clear()
            changed = True
        if self._clear_execution_edge_progress_state_fields():
            changed = True
        if changed:
            state.node_execution_revision += 1


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

    def test_run_workflow_starts_new_run_with_manual_trigger_and_updates_state(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()

        self.assertEqual(host.console_panel.clear_count, 1)
        self.assertEqual(host.run_state.active_run_id, "run_live")
        self.assertEqual(host.run_state.active_run_workspace_id, host.model.active_workspace.workspace_id)
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
        self.assertEqual(start_call["project_path"], "demo.sfe")
        self.assertEqual(start_call["workspace_id"], host.model.active_workspace.workspace_id)
        self.assertEqual(start_call["trigger"]["kind"], "manual")
        self.assertEqual(start_call["trigger"]["workflow_settings"], {"general": {"project_name": "Demo"}})
        self.assertNotIn("project_doc", start_call["trigger"])
        runtime_snapshot = start_call["trigger"]["runtime_snapshot"]
        self.assertEqual(runtime_snapshot.active_workspace_id, host.model.active_workspace.workspace_id)
        self.assertEqual(len(runtime_snapshot.workspaces), 1)
        self.assertEqual(
            runtime_snapshot.to_document()["workspaces"][0]["document_fields"]["workspace_id"],
            host.model.active_workspace.workspace_id,
        )

    def test_execution_edge_progress_projection_run_started_seeds_edge_index_and_progresses_exec_and_completed_edges(
        self,
    ) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        start = host.model.add_node(workspace_id, "core.start", "Start", 0, 0)
        end = host.model.add_node(workspace_id, "core.end", "End", 180, 0)
        logger = host.model.add_node(workspace_id, "core.logger", "Logger", 360, 0)
        exec_edge = host.model.add_edge(workspace_id, start.node_id, "exec_out", end.node_id, "exec_in")
        completed_edge = host.model.add_edge(workspace_id, end.node_id, "done", logger.node_id, "exec_in")
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()
        controller.handle_execution_event(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.execution_edge_run_id, "run_live")
        self.assertEqual(host.run_state.execution_edge_workspace_id, workspace_id)
        self.assertEqual(
            host.run_state.execution_edge_ids_by_source_node_id[start.node_id]["exec"],
            (exec_edge.edge_id,),
        )
        self.assertEqual(
            host.run_state.execution_edge_ids_by_source_node_id[end.node_id]["completed"],
            (completed_edge.edge_id,),
        )
        self.assertEqual(host.run_state.progressed_execution_edge_ids, set())

        seeded_revision = host.run_state.node_execution_revision
        controller.handle_execution_event(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": start.node_id,
            }
        )

        self.assertEqual(host.run_state.completed_node_ids, {start.node_id})
        self.assertIn(exec_edge.edge_id, host.run_state.progressed_execution_edge_ids)
        self.assertGreater(host.run_state.node_execution_revision, seeded_revision)

        exec_revision = host.run_state.node_execution_revision
        controller.handle_execution_event(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": end.node_id,
            }
        )

        self.assertIn(completed_edge.edge_id, host.run_state.progressed_execution_edge_ids)
        self.assertGreater(host.run_state.node_execution_revision, exec_revision)

    def test_execution_edge_progress_projection_node_failed_handled_progresses_failed_edges(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        start = host.model.add_node(workspace_id, "core.start", "Start", 0, 0)
        script = host.model.add_node(
            workspace_id,
            "core.python_script",
            "Script",
            180,
            0,
            properties={"script": "raise RuntimeError('boom handled')"},
        )
        on_failure = host.model.add_node(workspace_id, "core.on_failure", "On Failure", 360, 0)
        host.model.add_edge(workspace_id, start.node_id, "exec_out", script.node_id, "exec_in")
        failed_edge = host.model.add_edge(workspace_id, script.node_id, "on_failed", on_failure.node_id, "failed_in")
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()
        host.run_state.execution_edge_run_id = "run_stale"
        host.run_state.execution_edge_workspace_id = "ws_stale"
        host.run_state.execution_edge_ids_by_source_node_id = {"node_stale": {"exec": ("edge_stale",)}}
        host.run_state.progressed_execution_edge_ids.add("edge_stale")

        controller.handle_execution_event(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.execution_edge_run_id, "run_live")
        self.assertEqual(host.run_state.execution_edge_workspace_id, workspace_id)
        self.assertEqual(host.run_state.progressed_execution_edge_ids, set())
        self.assertEqual(
            host.run_state.execution_edge_ids_by_source_node_id[script.node_id]["failed"],
            (failed_edge.edge_id,),
        )

        seeded_revision = host.run_state.node_execution_revision
        controller.handle_execution_event(
            {
                "type": "node_failed_handled",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": script.node_id,
                "error": "boom handled",
            }
        )

        self.assertEqual(host.run_state.progressed_execution_edge_ids, {failed_edge.edge_id})
        self.assertGreater(host.run_state.node_execution_revision, seeded_revision)
        self.assertEqual(host._engine_status, ("running", "Running"))

    def test_execution_edge_progress_projection_terminal_events_clear_edge_projection_state(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        start = host.model.add_node(workspace_id, "core.start", "Start", 0, 0)
        end = host.model.add_node(workspace_id, "core.end", "End", 180, 0)
        exec_edge = host.model.add_edge(workspace_id, start.node_id, "exec_out", end.node_id, "exec_in")
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()
        controller.handle_execution_event(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )
        controller.handle_execution_event(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": start.node_id,
            }
        )
        self.assertIn(exec_edge.edge_id, host.run_state.progressed_execution_edge_ids)

        controller.handle_execution_event(
            {
                "type": "run_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.execution_edge_run_id, "")
        self.assertEqual(host.run_state.execution_edge_workspace_id, "")
        self.assertEqual(host.run_state.execution_edge_ids_by_source_node_id, {})
        self.assertEqual(host.run_state.progressed_execution_edge_ids, set())

    def test_run_workflow_logs_error_when_start_fails(self) -> None:
        host = _RunHostStub()
        host.execution_client.next_run_id = ""
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()

        self.assertEqual(host.console_panel.logs[-1], ("error", "Failed to start workflow run."))
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

    def test_update_run_actions_selected_workspace_owner_running_disables_run_and_enables_pause_stop(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = host.model.active_workspace.workspace_id
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

    def test_update_run_actions_selected_workspace_owner_paused_uses_resume_label(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = host.model.active_workspace.workspace_id
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

    def test_update_run_actions_non_owning_selected_workspace_disables_pause_and_stop(self) -> None:
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
        host.run_state.active_run_workspace_id = host.model.active_workspace.workspace_id
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

    def test_run_failed_event_focuses_node_logs_traceback_and_clears_active_run(self) -> None:
        host = _RunHostStub()
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = host.model.active_workspace.workspace_id
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

        self.assertEqual(host.console_panel.logs[-2:], [("error", "boom"), ("error", "traceback: line 1")])
        self.assertEqual(host._notifications, (0, 2))
        self.assertEqual(
            host.workspace_library_controller.focus_calls,
            [(host.model.active_workspace.workspace_id, "node_1", "boom")],
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

        controller.handle_execution_event({"type": "protocol_error", "error": "bad payload"})

        self.assertEqual(host.console_panel.logs, [("error", "bad payload")])
        self.assertEqual(host._notifications, (0, 1))

    def test_node_execution_bridge_run_events_project_running_and_completed_nodes(self) -> None:
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
        self.assertEqual(host.run_state.node_execution_revision, 6)

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
        self.assertEqual(host.run_state.node_execution_revision, 7)

        controller.handle_execution_event(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
            }
        )

        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, {"node_1"})
        self.assertEqual(host.run_state.node_execution_revision, 8)
        self.assertEqual(host._engine_status, ("running", "Running"))

    def test_persistent_node_elapsed_state_projects_fallback_started_at_and_cached_elapsed_by_workspace(self) -> None:
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

        with mock.patch("tests.test_run_controller_unit.time.time", return_value=100.0):
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

        with mock.patch("tests.test_run_controller_unit.time.time", return_value=100.04525):
            controller.handle_execution_event(
                {
                    "type": "node_completed",
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
            host.run_state.cached_node_elapsed_ms_by_workspace_id[workspace_id]["node_1"],
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

        self.assertEqual(host.run_state.node_execution_workspace_id, "")
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.running_node_started_at_epoch_ms_by_node_id, {})
        self.assertEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id["ws_previous"],
            {"node_cached": 12.5},
        )
        self.assertAlmostEqual(
            host.run_state.cached_node_elapsed_ms_by_workspace_id[workspace_id]["node_1"],
            45.25,
            places=2,
        )

    def test_node_completed_after_pause_preserves_paused_state_and_resume_action(self) -> None:
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
                "type": "node_completed",
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

    def test_persistent_node_elapsed_state_terminal_events_clear_transient_state_preserving_cache(self) -> None:
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
        host.run_state.running_node_ids.add("node_1")
        host.run_state.running_node_started_at_epoch_ms_by_node_id["node_1"] = 1000.0
        host.run_state.node_execution_revision = 1

        controller.handle_execution_event(
            {
                "type": "run_completed",
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
        self.assertEqual(host.run_state.node_execution_revision, 3)

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
        self.assertEqual(host.run_state.node_execution_revision, 4)


if __name__ == "__main__":
    unittest.main()
