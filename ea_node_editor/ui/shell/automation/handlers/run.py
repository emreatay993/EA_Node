# Purpose: Run automation handlers: start, deferred status/wait, control (T09); polls ShellRunState from the bridge-owned Deferred.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import RUN_ACTIVE, AutomationOpError, invalid_params
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext

DEFAULT_LOG_TAIL = 20
DEFAULT_WAIT_TIMEOUT_S = 120.0
POLL_INTERVAL_S = 0.05

# Outcome bookkeeping that ShellRunState does not keep: the last run id seen by a
# status poll and the run id a run.control(stop) request targeted. When the run
# state goes idle after a stop request for that same run, outcome is "stopped".
_run_tracker: dict[str, str] = {"last_run_id": "", "stop_requested_run_id": ""}


# ----------------------------------------------------------------- helpers


def run_state_idle(run_state: Any) -> bool:
    """Idle = no active run, no pending submission, no queued auto-run (matches app.status)."""
    if run_state is None:
        return True
    return not (
        str(run_state.active_run_id or "")
        or str(run_state.active_submission_id or "")
        or str(run_state.pending_auto_run_workspace_id or "")
    )


def run_summary(run_state: Any) -> dict[str, Any]:
    """The compact ``run`` block shared by app.status."""
    if run_state is None:
        return {"idle": True, "engine_state": "ready", "active_run_id": ""}
    return {
        "idle": run_state_idle(run_state),
        "engine_state": str(run_state.engine_state_value or "ready"),
        "active_run_id": str(run_state.active_run_id or ""),
    }


def console_log_tail(console: Any, count: int) -> list[str]:
    """Last ``count`` console lines (``output_text`` already contains every level)."""
    if console is None or count <= 0:
        return []
    lines = str(console.output_text or "").splitlines()
    return lines[-count:]


def _root_error_rows(run_state: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node_id, errors in dict(run_state.root_errors_by_node_id).items():
        for error in errors:
            payload = error.to_payload()
            payload.setdefault("node_id", str(node_id))
            rows.append(payload)
    return rows


def _outcome(run_state: Any, idle: bool, failed: list[str], completed: list[str], empty: list[str]) -> str:
    if not idle:
        return "running"
    engine_state = str(run_state.engine_state_value or "")
    if failed or engine_state == "error":
        return "failed"
    if _run_tracker["last_run_id"] and _run_tracker["last_run_id"] == _run_tracker["stop_requested_run_id"]:
        return "stopped"
    if completed or empty:
        return "completed"
    return "idle"


def build_run_status(
    context: AutomationContext,
    *,
    log_tail: int = DEFAULT_LOG_TAIL,
    waited_s: float = 0.0,
    timed_out: bool = False,
) -> dict[str, Any]:
    """Snapshot ``ShellRunState`` into the RUN_STATUS_RESULT shape."""
    run_state = context.run_state
    if run_state is None:
        return {
            "idle": True,
            "engine_state": "ready",
            "active_run_id": "",
            "active_submission_id": "",
            "pending_auto_run": False,
            "outcome": "idle",
            "running_node_ids": [],
            "completed_node_ids": [],
            "empty_node_ids": [],
            "failed_node_ids": [],
            "blocked_node_ids": [],
            "warning_node_ids": [],
            "root_errors": [],
            "failed_node_id": "",
            "failed_node_title": "",
            "log_tail": [],
            "waited_s": round(float(waited_s), 3),
            "timed_out": bool(timed_out),
        }
    active_run_id = str(run_state.active_run_id or "")
    if active_run_id:
        _run_tracker["last_run_id"] = active_run_id
    idle = run_state_idle(run_state)
    failed = sorted(run_state.failed_node_ids)
    completed = sorted(run_state.completed_node_ids)
    empty = sorted(run_state.empty_node_ids)
    return {
        "idle": idle,
        "engine_state": str(run_state.engine_state_value or "ready"),
        "active_run_id": active_run_id,
        "active_submission_id": str(run_state.active_submission_id or ""),
        "pending_auto_run": bool(run_state.pending_auto_run_workspace_id),
        "outcome": _outcome(run_state, idle, failed, completed, empty),
        "running_node_ids": sorted(run_state.running_node_ids),
        "completed_node_ids": completed,
        "empty_node_ids": empty,
        "failed_node_ids": failed,
        "blocked_node_ids": sorted(run_state.blocked_node_ids),
        "warning_node_ids": sorted(run_state.warning_node_ids),
        "root_errors": _root_error_rows(run_state),
        "failed_node_id": str(run_state.failed_node_id or ""),
        "failed_node_title": str(run_state.failed_node_title or ""),
        "log_tail": console_log_tail(context.console, int(log_tail)),
        "waited_s": round(float(waited_s), 3),
        "timed_out": bool(timed_out),
    }


def _wait_for_idle(context: AutomationContext, *, timeout_s: float, log_tail: int, label: str, extra: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    """Return the status now when idle, else a Deferred the bridge polls until idle or timeout."""
    started = time.monotonic()
    if run_state_idle(context.run_state):
        return {**build_run_status(context, log_tail=log_tail), **extra}

    def poll() -> dict[str, Any] | None:
        if not run_state_idle(context.run_state):
            return None
        return {**build_run_status(context, log_tail=log_tail, waited_s=time.monotonic() - started), **extra}

    def on_timeout() -> dict[str, Any]:
        return {
            **build_run_status(context, log_tail=log_tail, waited_s=time.monotonic() - started, timed_out=True),
            **extra,
        }

    return Deferred(poll=poll, timeout_s=float(timeout_s), on_timeout=on_timeout, poll_interval_s=POLL_INTERVAL_S, label=label)


def _unique_ids(values: Any) -> list[str]:
    ordered: list[str] = []
    for value in values or ():
        node_id = str(value or "").strip()
        if node_id and node_id not in ordered:
            ordered.append(node_id)
    return ordered


# ---------------------------------------------------------------- handlers


def start_run(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "run.start"
    context.require_shell(op)
    run_state = context.run_state
    controller = context.run_controller
    # Only a run or submission in flight blocks a start. A queued auto-run (auto solution
    # mode queues one after every graph edit) is superseded by the manual run, exactly as
    # RunController._submit_run clears it for non-auto triggers.
    if run_state.active_run_id or run_state.active_submission_id:
        raise AutomationOpError(
            RUN_ACTIVE,
            "A workflow run is already active in this COREX instance.",
            details={
                "active_run_id": str(run_state.active_run_id or ""),
                "active_submission_id": str(run_state.active_submission_id or ""),
                "pending_auto_run_workspace_id": str(run_state.pending_auto_run_workspace_id or ""),
            },
        )
    scope = str(params.get("scope") or "workspace")
    log_tail = int(params.get("log_tail", DEFAULT_LOG_TAIL))
    node_ids: list[str] = []
    if scope == "nodes":
        node_ids = _unique_ids(params.get("node_ids"))
        if not node_ids:
            raise invalid_params(["node_ids: required and non-empty when scope=nodes"], op=op)
        context.require_nodes(node_ids)
        # preview_confirmed skips the "preview before run" summary (a preference that
        # defaults to on) which would otherwise only log the plan without running.
        controller.run_selected_nodes(node_ids, preview_confirmed=True)
    else:
        controller.run_workflow()
    # The controller may decline silently (nothing runnable, script draft not applied,
    # start failure); ``started`` tells the agent whether a submission exists.
    started = bool(run_state.active_run_id or run_state.active_submission_id)
    extra = {"started": started, "scope": scope, "target_node_ids": node_ids}
    if not bool(params.get("wait", False)):
        return {**build_run_status(context, log_tail=log_tail), **extra}
    return _wait_for_idle(
        context,
        timeout_s=float(params.get("timeout_s", DEFAULT_WAIT_TIMEOUT_S)),
        log_tail=log_tail,
        label=op,
        extra=extra,
    )


def run_status(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "run.status"
    if context.run_state is None:
        context.require_shell(op)
    log_tail = int(params.get("log_tail", DEFAULT_LOG_TAIL))
    if not bool(params.get("wait", False)):
        return build_run_status(context, log_tail=log_tail)
    return _wait_for_idle(
        context,
        timeout_s=float(params.get("timeout_s", DEFAULT_WAIT_TIMEOUT_S)),
        log_tail=log_tail,
        label=op,
        extra={},
    )


def control_run(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "run.control"
    context.require_shell(op)
    run_state = context.run_state
    controller = context.run_controller
    action = str(params["action"])
    active_run_id = str(run_state.active_run_id or "")
    engine_state = str(run_state.engine_state_value or "")
    if action == "stop":
        # stop_workflow cancels a preparing submission, stops the active run, or clears
        # a pending auto-run; with none of those it only refreshes the run controls.
        applied = bool(active_run_id or run_state.active_submission_id or run_state.pending_auto_run_workspace_id)
        if active_run_id:
            _run_tracker["last_run_id"] = active_run_id
            _run_tracker["stop_requested_run_id"] = active_run_id
        controller.stop_workflow()
    elif action == "pause":
        applied = bool(active_run_id) and engine_state == "running"
        controller.pause_workflow()
    else:
        applied = bool(active_run_id) and engine_state == "paused"
        controller.resume_workflow()
    return {
        "applied": applied,
        "action": action,
        "engine_state": str(run_state.engine_state_value or "ready"),
        "active_run_id": str(run_state.active_run_id or ""),
        "idle": run_state_idle(run_state),
    }


HANDLERS = {
    'run.start': start_run,
    'run.status': run_status,
    'run.control': control_run,
}

__all__ = ["HANDLERS", "build_run_status", "console_log_tail", "run_state_idle", "run_summary"]
