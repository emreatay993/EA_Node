# Purpose: Shell run controller — drives workspace run/execution flow and
#          run-failure focus for the selected workspace.
# Map: feature_routes/run_controller_selected_workspace_state
# Tests: tests/test_run_controller_unit.py
# Landmarks: RunController
from __future__ import annotations

from collections.abc import Mapping
import time
from typing import Any, Iterable, Literal, Protocol

from ea_node_editor.addons.ansys_dpf.ui_summary import project_dpf_workflow_summary
from ea_node_editor.developer_mode import developer_mode_capability_enabled
from ea_node_editor.execution.backends import EXTERNAL_SUBPROCESS_BACKEND
from ea_node_editor.execution.headless_runtime import ExecutionRequest
from ea_node_editor.execution.prepared_execution import SolutionStateChangedEvent
from ea_node_editor.execution.protocol import (
    normalize_root_execution_errors,
    normalize_settled_output_mapping,
    normalize_settled_port_result,
)
from ea_node_editor.runtime_contracts.settled_results import (
    RootExecutionError,
    SettledPortResult,
)
from ea_node_editor.execution.python_environment import (
    workflow_python_path_from_snapshot,
)
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.graph.hierarchy import root_node_ids_for_fragment, subtree_node_ids
from ea_node_editor.ui.icon_registry import qicon
from ea_node_editor.ui.port_availability import (
    clear_port_availability_runtime_node,
    clear_port_availability_runtime_workspace,
    observe_node_outputs,
)
from ea_node_editor.ui.shell.runtime_history import (
    classify_history_execution_change,
)
from ea_node_editor.ui.shell.run_flow import (
    event_targets_active_run,
    selected_workspace_run_control_state,
)
from ea_node_editor.ui.shell.state import ShellRunState
from ea_node_editor.ui.support.solution_output_cache import (
    cache_accepted_output_record,
    remove_cached_nodes,
)


class _WorkflowSettingsSourceProtocol(Protocol):
    def workflow_settings_payload(self) -> dict[str, Any]: ...


class _RunFailureFocusProtocol(Protocol):
    def focus_failed_node(self, workspace_id: str, node_id: str) -> None: ...


class _RunControllerHostProtocol(Protocol):
    run_state: ShellRunState
    project_path: str
    workspace_manager: Any
    serializer: Any
    model: Any
    registry: Any
    project_session_controller: _WorkflowSettingsSourceProtocol
    app_preferences_controller: Any
    console_panel: Any
    execution_client: Any
    script_editor: Any
    workspace_library_controller: _RunFailureFocusProtocol
    action_run: Any
    action_stop: Any
    action_pause: Any
    run_controls_changed: Any
    run_failure_changed: Any
    node_execution_state_changed: Any
    _RUN_SCOPED_EVENT_TYPES: set[str]

    def update_notification_counters(
        self, warning_count: int, error_count: int
    ) -> None: ...

    def update_engine_status(self, state: str, details: str) -> None: ...

    def update_job_counters(
        self, running: int, queued: int, done: int, failed: int
    ) -> None: ...

    def show_selected_run_settings_dialog(self) -> None: ...


class RunController:
    def __init__(self, host: _RunControllerHostProtocol) -> None:
        self._host = host
        self._run_start_runtime_snapshots: dict[str, Any] = {}
        self._active_run_invalidated_node_ids: set[str] = set()
        self._solution_project_identity: int | None = None
        self._suppress_auto_run_for_script_apply = False

    @property
    def _state(self) -> ShellRunState:
        return self._host.run_state

    def _developer_mode_active(self) -> bool:
        return developer_mode_capability_enabled() and bool(
            self._state.developer_mode_active
        )

    def solution_mode(self, workspace_id: str = "") -> Literal["auto", "manual"]:
        normalized_workspace_id = str(
            workspace_id or self._host.workspace_manager.active_workspace_id()
        ).strip()
        if not normalized_workspace_id:
            return "manual"
        state = self._state
        mode = state.solution_mode_by_workspace_id.get(normalized_workspace_id)
        if mode is None:
            getter = getattr(
                self._host.app_preferences_controller, "solution_default_mode", None
            )
            mode = "auto" if callable(getter) and getter() == "auto" else "manual"
            state.solution_mode_by_workspace_id[normalized_workspace_id] = mode
        return mode

    def auto_run_enabled_for_workspace(self, workspace_id: str = "") -> bool:
        return self.solution_mode(workspace_id) == "auto"

    def set_auto_run_enabled(self, enabled: bool) -> None:
        workspace_id = str(
            self._host.workspace_manager.active_workspace_id() or ""
        ).strip()
        if not workspace_id:
            return
        mode: Literal["auto", "manual"] = "auto" if enabled else "manual"
        if self.solution_mode(workspace_id) == mode:
            return
        self._state.solution_mode_by_workspace_id[workspace_id] = mode
        if mode == "manual":
            self.clear_pending_auto_run()
        self._host.run_controls_changed.emit()

    def toggle_auto_run(self) -> None:
        if self.auto_run_enabled_for_workspace():
            self.set_auto_run_enabled(False)
            return
        self.set_auto_run_enabled(True)
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is not None:
            self._queue_auto_run(workspace_id, set(self._active_node_ids(workspace)))

    def clear_pending_auto_run(self) -> None:
        self._state.pending_auto_run_workspace_id = ""
        self._state.pending_auto_run_target_node_ids.clear()

    def reset_runtime_solution_state(self) -> None:
        from ea_node_editor.ui.image_value_preview_provider import clear_image_value_previews

        clear_image_value_previews()
        state = self._state
        for workspace_id in tuple(self._host.model.project.workspaces):
            clear_port_availability_runtime_workspace(workspace_id)
        self.clear_pending_auto_run()
        state.solution_mode_by_workspace_id.clear()
        state.latest_trigger_inputs_by_workspace_id.clear()
        state.trigger_publications_by_workspace_id.clear()
        state.current_trigger_capture_node_ids_by_workspace_id.clear()
        state.cached_node_output_records_by_workspace_id.clear()
        state.node_output_run_counts_by_workspace_id.clear()
        state.node_output_cache_sequence = 0
        state.cached_node_elapsed_ms_by_workspace_id.clear()
        state.solution_project_id = ""
        state.solution_revision_by_workspace_id.clear()
        state.node_solution_facts_by_workspace_id.clear()
        state.runtime_warning_messages_by_workspace_id.clear()
        self.clear_node_execution_visualization_state()
        self.clear_active_run()
        self._run_start_runtime_snapshots.clear()
        self._solution_project_identity = id(self._host.model.project)

    def prune_runtime_solution_state(self) -> None:
        state = self._state
        workspaces = self._host.model.project.workspaces
        workspace_ids = set(workspaces)
        for mapping in (
            state.solution_mode_by_workspace_id,
            state.latest_trigger_inputs_by_workspace_id,
            state.trigger_publications_by_workspace_id,
            state.current_trigger_capture_node_ids_by_workspace_id,
            state.cached_node_output_records_by_workspace_id,
            state.node_output_run_counts_by_workspace_id,
            state.cached_node_elapsed_ms_by_workspace_id,
            state.solution_revision_by_workspace_id,
            state.node_solution_facts_by_workspace_id,
            state.runtime_warning_messages_by_workspace_id,
        ):
            for workspace_id in tuple(mapping):
                if workspace_id not in workspace_ids:
                    mapping.pop(workspace_id, None)
        if state.pending_auto_run_workspace_id not in workspace_ids:
            self.clear_pending_auto_run()
        if (
            state.node_execution_workspace_id
            and state.node_execution_workspace_id not in workspace_ids
        ):
            self.clear_node_execution_visualization_state()
        for workspace_id, workspace in workspaces.items():
            trigger_ids = {
                node_id
                for node_id, node in workspace.nodes.items()
                if str(node.type_id) == "core.trigger"
            }
            for mapping in (
                state.latest_trigger_inputs_by_workspace_id,
                state.trigger_publications_by_workspace_id,
            ):
                workspace_mapping = mapping.get(workspace_id)
                if workspace_mapping is None:
                    continue
                for node_id in tuple(workspace_mapping):
                    if node_id not in trigger_ids:
                        workspace_mapping.pop(node_id, None)
                if not workspace_mapping:
                    mapping.pop(workspace_id, None)
            current_capture_ids = (
                state.current_trigger_capture_node_ids_by_workspace_id.get(workspace_id)
            )
            if current_capture_ids is not None:
                current_capture_ids.intersection_update(trigger_ids)
                if not current_capture_ids:
                    state.current_trigger_capture_node_ids_by_workspace_id.pop(
                        workspace_id, None
                    )

    def evaluate_workspace_on_open(self, workspace_id: str) -> None:
        if self._solution_project_identity != id(self._host.model.project):
            self.reset_runtime_solution_state()
        normalized_workspace_id = str(workspace_id or "").strip()
        if (
            self._state.pending_auto_run_workspace_id
            and self._state.pending_auto_run_workspace_id != normalized_workspace_id
        ):
            self.clear_pending_auto_run()
        workspace = self._host.model.project.workspaces.get(normalized_workspace_id)
        if workspace is None:
            return
        self.solution_mode(normalized_workspace_id)
        self._host.run_controls_changed.emit()
        if not self.auto_run_enabled_for_workspace(normalized_workspace_id):
            return
        target_node_ids = self._active_node_ids(workspace)
        if target_node_ids:
            self._queue_auto_run(normalized_workspace_id, set(target_node_ids))

    def run_workflow(self) -> None:
        if self._state.active_run_id:
            if self._state.engine_state_value == "paused":
                self.resume_workflow()
            else:
                self._host.console_panel.append_log(
                    "warning", "A workflow run is already active."
                )
                self._host.update_notification_counters(
                    self._host.console_panel.warning_count,
                    self._host.console_panel.error_count,
                )
            return

        if not self._apply_dirty_script_draft():
            return
        self.clear_run_failure_focus()
        workspace_id = self._host.workspace_manager.active_workspace_id()
        self.prune_runtime_solution_state()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return
        runtime_snapshot = build_runtime_snapshot(
            self._host.model.project,
            workspace_id=workspace_id,
            registry=self._host.registry,
        )
        self._host.console_panel.clear_all()
        self.clear_selected_run_preview()
        run_id = self._prepare_and_dispatch(
            workspace_id=workspace_id,
            runtime_snapshot=runtime_snapshot,
            trigger_kind="manual",
            target_node_ids=self._active_node_ids(workspace),
        )
        if not run_id:
            self._host.console_panel.append_log(
                "error", "Failed to start workflow run."
            )
            self._host.update_notification_counters(
                self._host.console_panel.warning_count,
                self._host.console_panel.error_count,
            )
            self.set_run_ui_state("error", "Start Failed", 0, 0, 0, 1, clear_run=True)
            return
        self.set_run_ui_state("running", "Starting", 1, 0, 0, 0)

    def run_selected_nodes(
        self,
        node_ids: Iterable[Any] | None = None,
        *,
        preview_only: bool = False,
        preview_confirmed: bool = False,
        trigger_kind: Literal["manual", "auto"] = "manual",
    ) -> None:
        normalized_trigger_kind = "auto" if trigger_kind == "auto" else "manual"
        if self._state.active_run_id:
            self._host.console_panel.append_log(
                "warning", "A workflow run is already active."
            )
            return
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            self._host.console_panel.append_log(
                "warning", "No active workspace is available."
            )
            return
        target_node_ids = (
            tuple(
                candidate
                for candidate in workspace.nodes
                if candidate
                in {
                    str(node_id or "").strip() for node_id in (node_ids or ())
                }
                and self._node_is_active(workspace, candidate)
            )
            if normalized_trigger_kind == "auto"
            else self._selected_run_target_node_ids(workspace, node_ids)
        )
        if not target_node_ids:
            self._host.console_panel.append_log(
                "warning", "Select an executable node or group to run."
            )
            return

        preview_payload = self._selected_run_preview_payload(
            workspace=workspace,
            target_node_ids=target_node_ids,
        )
        preview_text = self._selected_run_preview_text(preview_payload)
        preview_enabled = (
            normalized_trigger_kind == "manual" and self._selected_run_preview_enabled()
        )
        if preview_only or (preview_enabled and not preview_confirmed):
            self._set_selected_run_preview(
                workspace_id=workspace_id,
                target_node_ids=target_node_ids,
                preview_payload=preview_payload,
            )
            self._host.console_panel.append_log("info", preview_text)
        if preview_only:
            return
        if preview_enabled and not preview_confirmed:
            return
        if normalized_trigger_kind == "manual" and not self._apply_dirty_script_draft():
            return
        self.clear_run_failure_focus()
        self.prune_runtime_solution_state()
        runtime_snapshot = build_runtime_snapshot(
            self._host.model.project,
            workspace_id=workspace_id,
            registry=self._host.registry,
        )
        self._host.console_panel.clear_all()
        if preview_enabled:
            self._host.console_panel.append_log("info", preview_text)
        run_id = self._prepare_and_dispatch(
            workspace_id=workspace_id,
            runtime_snapshot=runtime_snapshot,
            trigger_kind=normalized_trigger_kind,
            target_node_ids=target_node_ids,
        )
        if not run_id:
            self._host.console_panel.append_log(
                "error", "Failed to start selected run."
            )
            self.set_run_ui_state("error", "Start Failed", 0, 0, 0, 1, clear_run=True)
            return
        self.clear_selected_run_preview()
        self.set_run_ui_state("running", "Starting", 1, 0, 0, 0)

    def trigger_node(self, node_id: str) -> bool:
        if self._state.active_run_id:
            self._host.console_panel.append_log(
                "warning", "A workflow run is already active."
            )
            return False
        workspace_id = str(
            self._host.workspace_manager.active_workspace_id() or ""
        ).strip()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        normalized_node_id = str(node_id or "").strip()
        node = (
            workspace.nodes.get(normalized_node_id) if workspace is not None else None
        )
        if node is None or str(node.type_id) != "core.trigger":
            return False

        if not self._apply_dirty_script_draft():
            return False
        self.clear_run_failure_focus()
        self.prune_runtime_solution_state()
        runtime_snapshot = build_runtime_snapshot(
            self._host.model.project,
            workspace_id=workspace_id,
            registry=self._host.registry,
        )
        latest_captures = self._state.latest_trigger_inputs_by_workspace_id.get(
            workspace_id, {}
        )
        current_capture_ids = (
            self._state.current_trigger_capture_node_ids_by_workspace_id.get(
                workspace_id, set()
            )
        )
        trigger_captures = (
            {normalized_node_id: latest_captures[normalized_node_id]}
            if normalized_node_id in current_capture_ids
            and normalized_node_id in latest_captures
            else {}
        )
        self._host.console_panel.clear_all()
        run_id = self._prepare_and_dispatch(
            workspace_id=workspace_id,
            runtime_snapshot=runtime_snapshot,
            trigger_kind="trigger",
            target_node_ids=(normalized_node_id,),
            trigger_captures=trigger_captures,
            clicked_trigger_node_id=normalized_node_id,
        )
        if not run_id:
            self._host.console_panel.append_log("error", "Failed to trigger node.")
            self.set_run_ui_state("error", "Start Failed", 0, 0, 0, 1, clear_run=True)
            return False
        self.set_run_ui_state("running", "Starting", 1, 0, 0, 0)
        return True

    def _prepare_and_dispatch(
        self,
        *,
        workspace_id: str,
        runtime_snapshot: Any,
        trigger_kind: str,
        target_node_ids: tuple[str, ...],
        trigger_captures: Mapping[str, SettledPortResult] | None = None,
        clicked_trigger_node_id: str = "",
    ) -> str:
        client = self._host.execution_client
        request = ExecutionRequest(
            project_path=self._host.project_path,
            workspace_id=workspace_id,
            trigger={
                "kind": str(trigger_kind),
                "workflow_settings": self._host.project_session_controller.workflow_settings_payload(),
                "developer_mode": self._developer_mode_active(),
            },
            runtime_snapshot=runtime_snapshot,
            execution_backend=self._execution_backend_policy_for_runtime_snapshot(
                runtime_snapshot
            ),
            target_node_ids=tuple(target_node_ids),
            trigger_publications=dict(
                self._state.trigger_publications_by_workspace_id.get(workspace_id, {})
            ),
            trigger_captures=dict(trigger_captures or {}),
            clicked_trigger_node_id=clicked_trigger_node_id,
        )
        try:
            prepared = client.prepare_execution(request)
            for node_id in prepared.recompute_node_ids:
                clear_port_availability_runtime_node(workspace_id, node_id)
            run_id = client.dispatch_prepared(prepared)
        except Exception as exc:  # noqa: BLE001
            self._host.console_panel.append_log("error", str(exc))
            run_id = ""
        self._sync_solution_facts(workspace_id)
        if not run_id:
            return ""
        self._state.active_run_id = run_id
        self._state.active_run_workspace_id = workspace_id
        self._run_start_runtime_snapshots[run_id] = runtime_snapshot
        return run_id

    def _execution_backend_policy_for_runtime_snapshot(
        self,
        runtime_snapshot: Any,
    ) -> dict[str, Any] | None:
        if workflow_python_path_from_snapshot(runtime_snapshot):
            return None
        python_executable = (
            self._host.app_preferences_controller.default_python_executable()
        )
        if not python_executable:
            return None
        return {
            "requested_backend": EXTERNAL_SUBPROCESS_BACKEND,
            "allow_external_subprocess": True,
            "python_executable": python_executable,
            "reason": "application_default_python_executable",
        }

    def preview_selected_run(
        self,
        node_ids: Iterable[Any] | None = None,
    ) -> None:
        self.run_selected_nodes(node_ids, preview_only=True)

    def confirm_selected_run_preview(self) -> None:
        state = self._state
        target_node_ids = tuple(state.selected_run_preview_target_node_ids)
        if not state.selected_run_preview_workspace_id or not target_node_ids:
            self._host.console_panel.append_log(
                "warning", "No selected run preview is waiting."
            )
            return
        self.run_selected_nodes(
            target_node_ids,
            preview_confirmed=True,
        )

    def clear_selected_run_preview(self) -> None:
        self._clear_selected_run_preview()

    def _apply_dirty_script_draft(self) -> bool:
        editor = self._host.script_editor
        if not bool(editor.dirty):
            return True
        self._suppress_auto_run_for_script_apply = True
        try:
            applied = bool(editor.apply())
        finally:
            self._suppress_auto_run_for_script_apply = False
        if not applied:
            self._host.console_panel.append_log(
                "error",
                "Apply the Python script draft before running.",
            )
        return applied

    def open_selected_run_settings(self) -> None:
        opener = getattr(self._host, "show_selected_run_settings_dialog", None)
        if callable(opener):
            opener()
            return
        state = "on" if self._selected_run_preview_enabled() else "off"
        self._host.console_panel.append_log(
            "info",
            f"Selected run settings: preview before run is {state}.",
        )

    def _selected_run_preview_enabled(self) -> bool:
        controller = getattr(self._host, "app_preferences_controller", None)
        getter = getattr(controller, "selected_run_preview_before_run", None)
        if callable(getter):
            return bool(getter())
        return True

    def toggle_pause_resume(self) -> None:
        if not self._state.active_run_id:
            return
        if self._state.engine_state_value == "paused":
            self.resume_workflow()
        elif self._state.engine_state_value == "running":
            self.pause_workflow()

    def pause_workflow(self) -> None:
        if not self._state.active_run_id or self._state.engine_state_value != "running":
            return
        self._host.execution_client.pause_run(self._state.active_run_id)
        self._host.update_engine_status("running", "Pausing")

    def resume_workflow(self) -> None:
        if not self._state.active_run_id or self._state.engine_state_value != "paused":
            return
        self._host.execution_client.resume_run(self._state.active_run_id)
        self._host.update_engine_status("running", "Resuming")

    def stop_workflow(self) -> None:
        if not self._state.active_run_id:
            return
        self.clear_pending_auto_run()
        self._host.execution_client.stop_run(self._state.active_run_id)
        if self._state.engine_state_value == "paused":
            self._host.update_engine_status("paused", "Stopping")
        else:
            self._host.update_engine_status("running", "Stopping")
        self.update_run_actions()

    def handle_execution_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        if event_type in {
            "run_preflight_accepted",
            "viewer_invalidation_committed",
        } and str(event.get("run_id", "")) != self._state.active_run_id:
            return
        if not event_targets_active_run(
            event,
            active_run_id=self._state.active_run_id,
            run_scoped_event_types=self._host._RUN_SCOPED_EVENT_TYPES,
        ):
            return
        if event_type == "solution_state_changed":
            self._handle_solution_state_changed(event)
            return
        if event_type == "viewer_invalidation_committed":
            self._adopt_committed_viewer_invalidation(event)
            return

        if event_type == "run_started":
            workspace_id = self._event_workspace_id(event)
            if workspace_id:
                self._state.active_run_workspace_id = workspace_id
            self.clear_node_execution_visualization_state()
            self.clear_run_failure_focus()
            self._take_run_start_runtime_snapshot(str(event.get("run_id", "")))
        elif event_type == "node_started":
            self.mark_node_execution_running(
                self._event_workspace_id(event),
                str(event.get("node_id", "")),
                started_at_epoch_ms=float(event.get("started_at_epoch_ms", 0.0) or 0.0),
            )
        elif event_type == "node_settled":
            workspace_id = self._event_workspace_id(event)
            node_id = str(event.get("node_id", ""))
            status = (
                str(event.get("status", "completed") or "completed").strip().lower()
            )
            warning_messages = self._normalize_warning_messages(
                event.get("warnings", ())
            )
            outputs = normalize_settled_output_mapping(
                event.get("outputs", {}),
                catalog=self._host.registry.data_types,
            )
            errors = normalize_root_execution_errors(event.get("errors", ()))
            settled_event = dict(event)
            settled_event["outputs"] = outputs
            self._sync_solution_facts(workspace_id, emit=False)
            if self._accepted_settlement_is_current(
                workspace_id,
                node_id,
                settled_event,
            ):
                self._observe_node_port_availability(
                    workspace_id, node_id, settled_event
                )
                self._cache_node_outputs(workspace_id, node_id, settled_event)
            self.mark_node_execution_settled(
                workspace_id,
                node_id,
                status=status,
                errors=errors,
                elapsed_ms=float(event.get("elapsed_ms", 0.0) or 0.0),
                warning=bool(warning_messages),
                warning_messages=warning_messages,
            )
            if status == "failed":
                self._host.workspace_library_controller.focus_failed_node(
                    workspace_id,
                    node_id,
                )
        elif event_type in {"trigger_capture_settled", "trigger_published"}:
            workspace_id = self._event_workspace_id(event)
            trigger_node_id = str(event.get("trigger_node_id", "") or "").strip()
            if workspace_id and trigger_node_id:
                result = normalize_settled_port_result(
                    event.get("result", {}),
                    catalog=self._host.registry.data_types,
                )
                if event_type == "trigger_capture_settled":
                    self._state.latest_trigger_inputs_by_workspace_id.setdefault(
                        workspace_id, {}
                    )[trigger_node_id] = result
                    current_capture_ids = self._state.current_trigger_capture_node_ids_by_workspace_id.setdefault(
                        workspace_id, set()
                    )
                    if trigger_node_id in self._active_run_invalidated_node_ids:
                        current_capture_ids.discard(trigger_node_id)
                    else:
                        current_capture_ids.add(trigger_node_id)
                    if not current_capture_ids:
                        self._state.current_trigger_capture_node_ids_by_workspace_id.pop(
                            workspace_id, None
                        )
                else:
                    self._state.trigger_publications_by_workspace_id.setdefault(
                        workspace_id, {}
                    )[trigger_node_id] = result
                self.commit_node_execution_state_change()

        if event_type == "run_started" or (
            event_type
            in {
                "node_started",
                "node_settled",
                "trigger_capture_settled",
                "trigger_published",
            }
            and self._state.engine_state_value != "paused"
        ):
            self.set_run_ui_state("running", "Running", 1, 0, 0, 0)

        if event_type == "log":
            self._host.console_panel.append_log(
                event.get("level", "info"), event.get("message", "")
            )
            self._host.update_notification_counters(
                self._host.console_panel.warning_count,
                self._host.console_panel.error_count,
            )
        elif event_type == "run_completed":
            self.set_run_ui_state("ready", "Completed", 0, 0, 1, 0, clear_run=True)
            self._drain_pending_auto_run()
        elif event_type == "run_failed":
            self.clear_node_execution_visualization_state()
            self.set_run_ui_state("error", "Failed", 0, 0, 0, 1)
            self._host.console_panel.append_log(
                "error", event.get("error", "Unknown failure")
            )
            self._host.console_panel.append_log("error", event.get("traceback", ""))
            self._host.update_notification_counters(
                self._host.console_panel.warning_count,
                self._host.console_panel.error_count,
            )
            self._host.workspace_library_controller.focus_failed_node(
                event.get("workspace_id", ""),
                event.get("node_id", ""),
            )
            fatal = bool(event.get("fatal", False))
            if fatal:
                self._invalidate_viewer_sessions_for_worker_reset()
            self.clear_active_run()
            self.update_run_actions()
            self.clear_pending_auto_run()
        elif event_type == "run_stopped":
            self.clear_node_execution_visualization_state()
            self.clear_pending_auto_run()
            self.set_run_ui_state("ready", "Stopped", 0, 0, 0, 0, clear_run=True)
        elif event_type == "run_state":
            state = event.get("state", "ready")
            transition = str(event.get("transition", ""))
            if state == "paused" or transition == "pause":
                self.set_run_ui_state("paused", "Paused", 1, 0, 0, 0)
            elif state == "running":
                self.set_run_ui_state("running", "Running", 1, 0, 0, 0)
            elif transition == "stop":
                self.clear_node_execution_visualization_state()
                self.clear_pending_auto_run()
                self.set_run_ui_state("ready", "Stopped", 0, 0, 0, 0, clear_run=True)
            elif state == "error":
                self.clear_pending_auto_run()
                self.set_run_ui_state("error", "Failed", 0, 0, 0, 1)
        elif event_type == "protocol_error":
            self.clear_pending_auto_run()
            self._host.console_panel.append_log(
                "error", event.get("error", "Execution protocol error.")
            )
            self._host.update_notification_counters(
                self._host.console_panel.warning_count,
                self._host.console_panel.error_count,
            )

    def clear_active_run(self) -> None:
        self._take_run_start_runtime_snapshot(self._state.active_run_id)
        self._state.active_run_id = ""
        self._state.active_run_workspace_id = ""
        self._active_run_invalidated_node_ids.clear()

    def _observe_node_port_availability(
        self, workspace_id: str, node_id: str, event: Mapping[str, Any]
    ) -> None:
        workspace = self._host.model.project.workspaces.get(
            str(workspace_id or "").strip()
        )
        if workspace is None:
            return
        node = workspace.nodes.get(str(node_id or "").strip())
        if node is None:
            return
        outputs = event.get("outputs")
        if not isinstance(outputs, Mapping):
            return
        value_outputs = {
            str(port_key): result
            for port_key, result in outputs.items()
            if isinstance(result, SettledPortResult) and result.status == "value"
        }
        observe_node_outputs(
            workspace_id=workspace.workspace_id,
            node_id=node.node_id,
            node_type_id=node.type_id,
            outputs=value_outputs,
        )

    def _accepted_settlement_is_current(
        self,
        workspace_id: str,
        node_id: str,
        event: Mapping[str, Any],
    ) -> bool:
        if not bool(event.get("accepted_solution_record", False)):
            return False
        expected_record_id = str(event.get("record_id", "") or "").strip()
        expected_solution_key = str(event.get("solution_key", "") or "").strip()
        expected_revision = event.get("solution_fact_revision")
        if (
            not expected_record_id
            or not expected_solution_key
            or isinstance(expected_revision, bool)
            or not isinstance(expected_revision, int)
        ):
            return False
        project_id = str(getattr(self._host.model.project, "project_id", "") or "")
        query = getattr(self._host.execution_client, "solution_facts", None)
        if not project_id or not callable(query):
            return False
        for fact in query(project_id, str(workspace_id or "").strip()):
            if str(getattr(fact, "node_id", "") or "") != str(node_id or ""):
                continue
            return (
                str(getattr(getattr(fact, "freshness", ""), "value", ""))
                == "current"
                and getattr(fact, "revision", None) == expected_revision
                and getattr(fact, "retained_record_id", None) == expected_record_id
                and getattr(fact, "retained_solution_key", None)
                == expected_solution_key
            )
        return False

    def _cache_node_outputs(
        self, workspace_id: str, node_id: str, event: Mapping[str, Any]
    ) -> None:
        normalized_workspace_id = str(workspace_id or "").strip()
        normalized_node_id = str(node_id or "").strip()
        if not normalized_workspace_id or not normalized_node_id:
            return
        outputs = event.get("outputs")
        if not isinstance(outputs, Mapping):
            return
        typed_outputs = normalize_settled_output_mapping(outputs)
        workspace = self._host.model.project.workspaces.get(normalized_workspace_id)
        node = (
            workspace.nodes.get(normalized_node_id) if workspace is not None else None
        )
        state = self._state
        observed_at_epoch_ms = self._current_epoch_ms()
        summary = project_dpf_workflow_summary(
            getattr(node, "type_id", ""),
            self._summary_output_values(typed_outputs),
            getattr(node, "properties", {}),
        )
        enriched_event = dict(event)
        enriched_event["observed_at_epoch_ms"] = observed_at_epoch_ms
        cache_accepted_output_record(
            state,
            workspace_id=normalized_workspace_id,
            node_id=normalized_node_id,
            event=enriched_event,
            outputs=typed_outputs,
            catalog=self._host.registry.data_types,
            dpf_workflow_summary=summary,
        )

    @staticmethod
    def _summary_output_values(
        outputs: Mapping[str, SettledPortResult],
    ) -> dict[str, Any]:
        projected: dict[str, Any] = {}
        for port_key, result in outputs.items():
            tree = result.value
            if result.status != "value" or tree is None or not tree.branches:
                continue
            first_branch = tree.branches[0][1]
            if first_branch:
                projected[str(port_key)] = first_branch[0]
        return projected

    def _selected_node_ids_from_scene(self, workspace: Any) -> tuple[str, ...]:
        scope_selection = getattr(
            getattr(self._host, "scene", None), "_scope_selection", None
        )
        selected_in_workspace = getattr(
            scope_selection, "selected_node_ids_in_workspace", None
        )
        if callable(selected_in_workspace):
            return tuple(selected_in_workspace(workspace))
        selected_ids = getattr(scope_selection, "selected_node_ids", None)
        if selected_ids is None:
            selected_ids = getattr(
                getattr(self._host, "scene", None), "_selected_node_ids", ()
            )
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_node_id in selected_ids or ():
            node_id = str(raw_node_id or "").strip()
            if node_id and node_id in workspace.nodes and node_id not in seen:
                seen.add(node_id)
                normalized.append(node_id)
        return tuple(normalized)

    def _selected_run_target_node_ids(
        self, workspace: Any, node_ids: Iterable[Any] | None
    ) -> tuple[str, ...]:
        raw_node_ids = (
            tuple(node_ids)
            if node_ids is not None
            else self._selected_node_ids_from_scene(workspace)
        )
        roots = root_node_ids_for_fragment(workspace, raw_node_ids)
        expanded = subtree_node_ids(workspace, roots or raw_node_ids)
        normalized: list[str] = []
        seen: set[str] = set()
        for node_id in expanded:
            node = workspace.nodes.get(node_id)
            if node is None or node_id in seen:
                continue
            try:
                spec = self._host.registry.get_spec(node.type_id)
            except Exception:  # noqa: BLE001
                continue
            runtime_behavior = (
                str(getattr(spec, "runtime_behavior", "") or "").strip().lower()
            )
            if runtime_behavior in {"passive", "compile_only"}:
                continue
            seen.add(node_id)
            normalized.append(node_id)
        return tuple(normalized)

    def _queue_auto_run(self, workspace_id: str, target_node_ids: set[str]) -> None:
        state = self._state
        normalized_workspace_id = str(workspace_id or "").strip()
        normalized_targets = {str(node_id or "").strip() for node_id in target_node_ids}
        normalized_targets.discard("")
        if (
            not self.auto_run_enabled_for_workspace(normalized_workspace_id)
            or not normalized_workspace_id
            or not normalized_targets
            or normalized_workspace_id
            != self._host.workspace_manager.active_workspace_id()
        ):
            return
        if state.pending_auto_run_workspace_id == normalized_workspace_id:
            state.pending_auto_run_target_node_ids.update(normalized_targets)
        else:
            state.pending_auto_run_workspace_id = normalized_workspace_id
            state.pending_auto_run_target_node_ids = normalized_targets
        if not state.active_run_id:
            self._drain_pending_auto_run()

    def _drain_pending_auto_run(self) -> None:
        state = self._state
        workspace_id = state.pending_auto_run_workspace_id
        target_node_ids = set(state.pending_auto_run_target_node_ids)
        self.clear_pending_auto_run()
        if (
            not self.auto_run_enabled_for_workspace(workspace_id)
            or state.active_run_id
            or not workspace_id
            or workspace_id != self._host.workspace_manager.active_workspace_id()
        ):
            return
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return
        ordered_target_node_ids = tuple(
            node_id
            for node_id in workspace.nodes
            if node_id in target_node_ids and self._node_is_active(workspace, node_id)
        )
        if not ordered_target_node_ids:
            return
        self.run_selected_nodes(
            ordered_target_node_ids,
            preview_confirmed=True,
            trigger_kind="auto",
        )

    def _active_node_ids(self, workspace: Any) -> tuple[str, ...]:
        return tuple(
            node_id
            for node_id in workspace.nodes
            if self._node_is_active(workspace, node_id)
        )

    def _node_is_active(self, workspace: Any, node_id: str) -> bool:
        node = workspace.nodes.get(str(node_id or "").strip())
        if node is None:
            return False
        try:
            spec = self._host.registry.get_spec(node.type_id)
        except Exception:  # noqa: BLE001
            return False
        runtime_behavior = (
            str(getattr(spec, "runtime_behavior", "") or "").strip().lower()
        )
        return runtime_behavior not in {"passive", "compile_only"}

    def _selected_run_preview_payload(
        self,
        *,
        workspace: Any,
        target_node_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        node_lookup: dict[str, str] = {}
        for node_id in target_node_ids:
            node = workspace.nodes.get(node_id)
            if node is None:
                continue
            title = str(getattr(node, "title", "") or node_id)
            rows.append(
                {
                    "section": "Will run",
                    "tone": "run",
                    "node_id": node_id,
                    "title": title,
                    "detail": "",
                }
            )
            node_lookup[node_id] = "run"
        return {
            "title": "Run Selected preview",
            "rows": rows,
            "node_lookup": node_lookup,
        }

    def _selected_run_preview_text(self, preview_payload: Mapping[str, Any]) -> str:
        lines = [f"{preview_payload.get('title', 'Selected run preview')}:"]
        current_section = ""
        rows = preview_payload.get("rows", ())
        if not isinstance(rows, (list, tuple)):
            return "\n".join(lines)
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            section = str(row.get("section", "") or "").strip()
            if section and section != current_section:
                lines.append(f"{section}:")
                current_section = section
            title = str(row.get("title", "") or row.get("node_id", "") or "").strip()
            detail = str(row.get("detail", "") or "").strip()
            lines.append(f"- {title}{f' ({detail})' if detail else ''}")
        return "\n".join(lines)

    def _set_selected_run_preview(
        self,
        *,
        workspace_id: str,
        target_node_ids: tuple[str, ...],
        preview_payload: Mapping[str, Any],
    ) -> None:
        state = self._state
        state.selected_run_preview_workspace_id = str(workspace_id or "").strip()
        state.selected_run_preview_target_node_ids = tuple(
            str(node_id) for node_id in target_node_ids
        )
        rows = preview_payload.get("rows", ())
        state.selected_run_preview_rows = (
            [dict(row) for row in rows if isinstance(row, Mapping)]
            if isinstance(rows, (list, tuple))
            else []
        )
        node_lookup = preview_payload.get("node_lookup", {})
        state.selected_run_preview_node_lookup = (
            {
                str(node_id): str(tone or "run")
                for node_id, tone in dict(node_lookup).items()
                if str(node_id).strip()
            }
            if isinstance(node_lookup, Mapping)
            else {}
        )
        state.selected_run_preview_revision += 1
        self.commit_node_execution_state_change()

    def _clear_selected_run_preview(self) -> None:
        state = self._state
        if not (
            state.selected_run_preview_workspace_id
            or state.selected_run_preview_target_node_ids
            or state.selected_run_preview_rows
            or state.selected_run_preview_node_lookup
        ):
            return
        state.selected_run_preview_workspace_id = ""
        state.selected_run_preview_target_node_ids = ()
        state.selected_run_preview_rows.clear()
        state.selected_run_preview_node_lookup.clear()
        state.selected_run_preview_revision += 1
        self.commit_node_execution_state_change()

    def set_run_ui_state(
        self,
        state: Literal["ready", "running", "paused", "error"],
        details: str,
        running: int,
        queued: int,
        done: int,
        failed: int,
        *,
        clear_run: bool = False,
    ) -> None:
        self._state.engine_state_value = state
        self._host.update_engine_status(state, details)
        self._host.update_job_counters(running, queued, done, failed)
        if clear_run:
            self.clear_active_run()
        self.update_run_actions()

    def update_run_actions(self) -> None:
        projection = selected_workspace_run_control_state(
            selected_workspace_id=self._host.workspace_manager.active_workspace_id(),
            active_run_id=self._state.active_run_id,
            active_run_workspace_id=self._state.active_run_workspace_id,
            engine_state=self._state.engine_state_value,
        )
        self._host.action_run.setEnabled(projection.can_run_active_workspace)
        self._host.action_stop.setEnabled(projection.can_stop_active_workspace)
        self._host.action_pause.setEnabled(projection.can_pause_active_workspace)
        self._host.action_pause.setText(projection.pause_label)
        if hasattr(self._host.action_pause, "setIcon"):
            self._host.action_pause.setIcon(
                qicon("resume" if projection.pause_label == "Resume" else "pause")
            )
        self._host.run_controls_changed.emit()

    def normalize_node_execution_workspace_id(self, workspace_id: str) -> str:
        normalized_workspace_id = str(workspace_id or "").strip()
        if normalized_workspace_id:
            return normalized_workspace_id
        state = self._state
        for candidate in (
            state.active_run_workspace_id,
            state.node_execution_workspace_id,
        ):
            normalized_candidate = str(candidate or "").strip()
            if normalized_candidate:
                return normalized_candidate
        return ""

    def commit_node_execution_state_change(self) -> None:
        self._state.node_execution_revision += 1
        self._host.node_execution_state_changed.emit()

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
        normalized_workspace_id = self.normalize_node_execution_workspace_id(
            workspace_id
        )
        if not normalized_workspace_id:
            return
        resolved_started_at_epoch_ms = self._coerce_nonnegative_timing_ms(
            started_at_epoch_ms
        )
        if resolved_started_at_epoch_ms <= 0.0:
            resolved_started_at_epoch_ms = self._current_epoch_ms()
        state = self._state
        changed = False
        workspace_warnings = state.runtime_warning_messages_by_workspace_id.get(
            normalized_workspace_id
        )
        if workspace_warnings is not None and self._discard_node_ids_from_mapping(
            workspace_warnings,
            {normalized_node_id},
        ):
            if not workspace_warnings:
                state.runtime_warning_messages_by_workspace_id.pop(
                    normalized_workspace_id, None
                )
            changed = True
        if state.node_execution_workspace_id != normalized_workspace_id:
            state.node_execution_workspace_id = normalized_workspace_id
            state.running_node_ids.clear()
            state.completed_node_ids.clear()
            state.empty_node_ids.clear()
            state.failed_node_ids.clear()
            state.blocked_node_ids.clear()
            state.root_errors_by_node_id.clear()
            state.warning_node_ids.clear()
            state.running_node_started_at_epoch_ms_by_node_id.clear()
            changed = True
        for settled_ids in (
            state.completed_node_ids,
            state.empty_node_ids,
            state.failed_node_ids,
            state.blocked_node_ids,
        ):
            if normalized_node_id in settled_ids:
                settled_ids.discard(normalized_node_id)
                changed = True
        if normalized_node_id in state.root_errors_by_node_id:
            state.root_errors_by_node_id.pop(normalized_node_id, None)
            changed = True
        if normalized_node_id in state.warning_node_ids:
            state.warning_node_ids.discard(normalized_node_id)
            changed = True
        if normalized_node_id not in state.running_node_ids:
            state.running_node_ids.add(normalized_node_id)
            changed = True
        if (
            state.running_node_started_at_epoch_ms_by_node_id.get(normalized_node_id)
            != resolved_started_at_epoch_ms
        ):
            state.running_node_started_at_epoch_ms_by_node_id[normalized_node_id] = (
                resolved_started_at_epoch_ms
            )
            changed = True
        if changed:
            self.commit_node_execution_state_change()

    def mark_node_execution_settled(
        self,
        workspace_id: str,
        node_id: str,
        *,
        status: str = "completed",
        errors: tuple[RootExecutionError, ...] = (),
        elapsed_ms: float = 0.0,
        warning: bool = False,
        warning_messages: object = (),
    ) -> None:
        normalized_node_id = str(node_id or "").strip()
        if not normalized_node_id:
            return
        normalized_workspace_id = self.normalize_node_execution_workspace_id(
            workspace_id
        )
        if not normalized_workspace_id:
            return
        state = self._state
        normalized_status = str(status or "completed").strip().lower()
        if normalized_status not in {"completed", "empty", "failed", "blocked"}:
            normalized_status = "completed"
        normalized_warning_messages = self._normalize_warning_messages(warning_messages)
        invalidated_during_run = (
            normalized_workspace_id == state.active_run_workspace_id
            and normalized_node_id in self._active_run_invalidated_node_ids
        )
        changed = False
        if state.node_execution_workspace_id != normalized_workspace_id:
            state.node_execution_workspace_id = normalized_workspace_id
            state.running_node_ids.clear()
            state.completed_node_ids.clear()
            state.empty_node_ids.clear()
            state.failed_node_ids.clear()
            state.blocked_node_ids.clear()
            state.root_errors_by_node_id.clear()
            state.warning_node_ids.clear()
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
        settled_ids_by_status = {
            "completed": state.completed_node_ids,
            "empty": state.empty_node_ids,
            "failed": state.failed_node_ids,
            "blocked": state.blocked_node_ids,
        }
        for candidate_status, settled_ids in settled_ids_by_status.items():
            should_contain = candidate_status == normalized_status
            if should_contain and normalized_node_id not in settled_ids:
                settled_ids.add(normalized_node_id)
                changed = True
            elif not should_contain and normalized_node_id in settled_ids:
                settled_ids.discard(normalized_node_id)
                changed = True
        if errors:
            if state.root_errors_by_node_id.get(normalized_node_id) != errors:
                state.root_errors_by_node_id[normalized_node_id] = errors
                changed = True
        elif normalized_node_id in state.root_errors_by_node_id:
            state.root_errors_by_node_id.pop(normalized_node_id, None)
            changed = True
        if warning and not invalidated_during_run:
            if normalized_node_id not in state.warning_node_ids:
                state.warning_node_ids.add(normalized_node_id)
                changed = True
        elif normalized_node_id in state.warning_node_ids:
            state.warning_node_ids.discard(normalized_node_id)
            changed = True
        workspace_warnings = state.runtime_warning_messages_by_workspace_id.get(
            normalized_workspace_id
        )
        if normalized_warning_messages and not invalidated_during_run:
            if workspace_warnings is None:
                workspace_warnings = {}
                state.runtime_warning_messages_by_workspace_id[
                    normalized_workspace_id
                ] = workspace_warnings
            if (
                workspace_warnings.get(normalized_node_id)
                != normalized_warning_messages
            ):
                workspace_warnings[normalized_node_id] = normalized_warning_messages
                changed = True
        elif workspace_warnings is not None and self._discard_node_ids_from_mapping(
            workspace_warnings,
            {normalized_node_id},
        ):
            if not workspace_warnings:
                state.runtime_warning_messages_by_workspace_id.pop(
                    normalized_workspace_id, None
                )
            changed = True
        worker_elapsed_ms = self._coerce_nonnegative_timing_ms(elapsed_ms)
        should_cache_elapsed = False
        resolved_elapsed_ms = 0.0
        if worker_elapsed_ms > 0.0:
            resolved_elapsed_ms = worker_elapsed_ms
            should_cache_elapsed = True
        elif started_at_epoch_ms > 0.0:
            resolved_elapsed_ms = max(
                0.0, self._current_epoch_ms() - started_at_epoch_ms
            )
            should_cache_elapsed = True
        if should_cache_elapsed and not invalidated_during_run:
            workspace_cache = state.cached_node_elapsed_ms_by_workspace_id.setdefault(
                normalized_workspace_id,
                {},
            )
            if workspace_cache.get(normalized_node_id) != resolved_elapsed_ms:
                workspace_cache[normalized_node_id] = resolved_elapsed_ms
                changed = True
        if changed:
            self.commit_node_execution_state_change()

    @staticmethod
    def _discard_node_ids_from_mapping(
        mapping: dict[str, Any], node_ids: set[str]
    ) -> bool:
        changed = False
        for node_id in tuple(node_ids):
            if node_id in mapping:
                mapping.pop(node_id, None)
                changed = True
        return changed

    def invalidate_solution_for_history_action(
        self,
        workspace_id: str,
        action_type: str,
        *,
        before_snapshot: object | None = None,
        after_snapshot: object | None = None,
    ) -> bool:
        normalized_workspace_id = str(workspace_id or "").strip()
        if not normalized_workspace_id:
            return False
        change = classify_history_execution_change(
            action_type,
            registry=self._host.registry,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        if not change.affects_execution:
            return False
        workspace = self._host.model.project.workspaces.get(normalized_workspace_id)
        if workspace is None:
            return False
        changed_root_node_ids = change.changed_root_node_ids
        if not changed_root_node_ids and not change.removed_node_ids:
            changed_root_node_ids = self._active_node_ids(workspace)
        runtime_snapshot = build_runtime_snapshot(
            self._host.model.project,
            workspace_id=normalized_workspace_id,
            registry=self._host.registry,
        )
        result = self._host.execution_client.invalidate_solution(
            runtime_snapshot.project_id,
            normalized_workspace_id,
            runtime_snapshot,
            changed_root_node_ids,
            "graph_changed",
        )
        affected_node_ids = set(result.expired_node_ids)
        self._handle_solution_state_changed(
            SolutionStateChangedEvent.from_invalidation(result).to_payload()
        )
        state = self._state
        current_capture_ids = (
            state.current_trigger_capture_node_ids_by_workspace_id.get(
                normalized_workspace_id
            )
        )
        if current_capture_ids is not None:
            stale_trigger_ids = {
                node_id
                for node_id in affected_node_ids
                if node_id in workspace.nodes
                and str(workspace.nodes[node_id].type_id) == "core.trigger"
            }
            if current_capture_ids.intersection(stale_trigger_ids):
                current_capture_ids.difference_update(stale_trigger_ids)
                if not current_capture_ids:
                    state.current_trigger_capture_node_ids_by_workspace_id.pop(
                        normalized_workspace_id, None
                    )
        if (
            state.active_run_id
            and state.active_run_workspace_id == normalized_workspace_id
        ):
            self._active_run_invalidated_node_ids.update(affected_node_ids)
        if (
            not self._suppress_auto_run_for_script_apply
            and result.expired_node_ids
        ):
            self._queue_auto_run(
                normalized_workspace_id,
                set(result.expired_node_ids),
            )
        return True

    def _handle_solution_state_changed(self, event: Mapping[str, Any]) -> None:
        try:
            changed = SolutionStateChangedEvent.from_payload(event)
        except (TypeError, ValueError):
            return
        project_id = str(getattr(self._host.model.project, "project_id", "") or "")
        if changed.project_id != project_id:
            return
        state = self._state
        previous_revision = int(
            state.solution_revision_by_workspace_id.get(changed.workspace_id, -1)
        )
        if changed.solution_revision <= previous_revision:
            return
        state.solution_project_id = changed.project_id
        state.solution_revision_by_workspace_id[changed.workspace_id] = (
            changed.solution_revision
        )
        self._sync_solution_facts(changed.workspace_id, emit=False)
        expired = set(changed.expired_node_ids)
        removed = set(changed.removed_node_ids)
        self._clear_node_projection_state(
            changed.workspace_id,
            expired | removed,
            removed_node_ids=removed,
        )
        for node_id in expired | removed:
            clear_port_availability_runtime_node(changed.workspace_id, node_id)
        self.commit_node_execution_state_change()
        if changed.reason_code == "project_session_reset":
            state.solution_revision_by_workspace_id.pop(changed.workspace_id, None)

    def _sync_solution_facts(self, workspace_id: str, *, emit: bool = True) -> None:
        workspace_key = str(workspace_id or "").strip()
        project_id = str(getattr(self._host.model.project, "project_id", "") or "")
        query = getattr(self._host.execution_client, "solution_facts", None)
        if not workspace_key or not project_id or not callable(query):
            return
        facts = tuple(query(project_id, workspace_key))
        self._state.solution_project_id = project_id
        if facts:
            self._state.node_solution_facts_by_workspace_id[workspace_key] = {
                fact.node_id: fact for fact in facts
            }
        else:
            self._state.node_solution_facts_by_workspace_id.pop(workspace_key, None)
        if emit:
            self.commit_node_execution_state_change()

    def _clear_node_projection_state(
        self,
        workspace_id: str,
        node_ids: set[str],
        *,
        removed_node_ids: set[str] | None = None,
    ) -> None:
        if not node_ids:
            return
        state = self._state
        if state.node_execution_workspace_id == workspace_id:
            self._discard_node_ids_from_mapping(
                state.running_node_started_at_epoch_ms_by_node_id, node_ids
            )
            for values in (
                state.running_node_ids,
                state.completed_node_ids,
                state.empty_node_ids,
                state.failed_node_ids,
                state.blocked_node_ids,
                state.warning_node_ids,
            ):
                values.difference_update(node_ids)
            self._discard_node_ids_from_mapping(state.root_errors_by_node_id, node_ids)
        warnings = state.runtime_warning_messages_by_workspace_id.get(workspace_id)
        if warnings is not None:
            self._discard_node_ids_from_mapping(warnings, node_ids)
            if not warnings:
                state.runtime_warning_messages_by_workspace_id.pop(workspace_id, None)
        elapsed = state.cached_node_elapsed_ms_by_workspace_id.get(workspace_id)
        if elapsed is not None:
            self._discard_node_ids_from_mapping(elapsed, node_ids)
            if not elapsed:
                state.cached_node_elapsed_ms_by_workspace_id.pop(workspace_id, None)
        if removed_node_ids:
            remove_cached_nodes(state, workspace_id, removed_node_ids)

    def clear_node_execution_visualization_state(self) -> None:
        state = self._state
        changed = False
        if (
            state.node_execution_workspace_id
            or state.running_node_ids
            or state.completed_node_ids
            or state.empty_node_ids
            or state.failed_node_ids
            or state.blocked_node_ids
            or state.root_errors_by_node_id
            or state.warning_node_ids
            or state.running_node_started_at_epoch_ms_by_node_id
        ):
            state.node_execution_workspace_id = ""
            state.running_node_ids.clear()
            state.completed_node_ids.clear()
            state.empty_node_ids.clear()
            state.failed_node_ids.clear()
            state.blocked_node_ids.clear()
            state.root_errors_by_node_id.clear()
            state.warning_node_ids.clear()
            state.running_node_started_at_epoch_ms_by_node_id.clear()
            changed = True
        if changed:
            self.commit_node_execution_state_change()

    def set_run_failure_focus(
        self,
        workspace_id: str,
        node_id: str,
        *,
        node_title: str = "",
    ) -> None:
        normalized_workspace_id = str(workspace_id or "").strip()
        normalized_node_id = str(node_id or "").strip()
        normalized_node_title = str(node_title or "").strip()
        state = self._state
        if (
            state.failed_workspace_id == normalized_workspace_id
            and state.failed_node_id == normalized_node_id
            and state.failed_node_title == normalized_node_title
        ):
            return
        state.failed_workspace_id = normalized_workspace_id
        state.failed_node_id = normalized_node_id
        state.failed_node_title = normalized_node_title
        self._host.run_failure_changed.emit()

    def clear_run_failure_focus(self) -> None:
        state = self._state
        if not (
            state.failed_workspace_id or state.failed_node_id or state.failed_node_title
        ):
            return
        state.failed_workspace_id = ""
        state.failed_node_id = ""
        state.failed_node_title = ""
        self._host.run_failure_changed.emit()

    def _event_workspace_id(self, event: dict[str, Any]) -> str:
        workspace_id = str(event.get("workspace_id", "") or "").strip()
        if workspace_id:
            return workspace_id
        return str(self._state.active_run_workspace_id or "").strip()

    @staticmethod
    def _normalize_warning_messages(warnings: object) -> tuple[str, ...]:
        if isinstance(warnings, str):
            values: Iterable[object] = (warnings,)
        elif isinstance(warnings, (list, tuple, set, frozenset)):
            values = warnings
        else:
            return ()
        normalized: list[str] = []
        for warning in values:
            message = " ".join(str(warning or "").split())
            if not message or message in normalized:
                continue
            normalized.append(message[:240])
            if len(normalized) == 3:
                break
        return tuple(normalized)

    def _adopt_committed_viewer_invalidation(
        self, event: Mapping[str, Any]
    ) -> None:
        viewer_session_bridge = getattr(self._host, "viewer_session_bridge", None)
        if viewer_session_bridge is None:
            return
        adopt = getattr(
            viewer_session_bridge, "adopt_committed_invalidation", None
        )
        if not callable(adopt):
            return
        adopt(
            workspace_id=str(event.get("workspace_id", "")),
            node_ids=event.get("viewer_invalidation_node_ids"),
            workspace_epoch=event.get(
                "viewer_workspace_invalidation_epoch", 0
            ),
            node_epochs=event.get("viewer_node_invalidation_epochs", ()),
            snapshot_digest=str(
                event.get("viewer_epoch_snapshot_digest", "")
            ),
            reason=str(event.get("reason", "workspace_rerun")),
            run_id=str(event.get("run_id", "")),
        )

    def _invalidate_viewer_sessions_for_worker_reset(self) -> None:
        viewer_session_bridge = getattr(self._host, "viewer_session_bridge", None)
        if viewer_session_bridge is None:
            return
        project_all_run_required = getattr(
            viewer_session_bridge, "project_all_run_required", None
        )
        if callable(project_all_run_required):
            project_all_run_required(reason="worker_reset")

    def _take_run_start_runtime_snapshot(self, run_id: str) -> Any:
        normalized_run_id = str(run_id or self._state.active_run_id).strip()
        if not normalized_run_id:
            return None
        return self._run_start_runtime_snapshots.pop(normalized_run_id, None)

    @staticmethod
    def _coerce_nonnegative_timing_ms(value: object) -> float:
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return 0.0
        return normalized if normalized >= 0.0 else 0.0

    @staticmethod
    def _current_epoch_ms() -> float:
        return time.time() * 1000.0
