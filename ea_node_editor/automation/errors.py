# Purpose: Frozen automation error codes, the handler-raised AutomationOpError, and agent-hint constructors.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_protocol.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# Frozen error-code contract (protocol 1). Every error carries an imperative
# ``hint`` telling an agent what to do next. Do not rename codes; add new ones
# at the end and document them in docs/AUTOMATION_API_GUIDE.md.
INVALID_PARAMS = "INVALID_PARAMS"
UNKNOWN_OP = "UNKNOWN_OP"
NOT_FOUND = "NOT_FOUND"
UNKNOWN_NODE_TYPE = "UNKNOWN_NODE_TYPE"
WRONG_SCOPE = "WRONG_SCOPE"
WRONG_WORKSPACE = "WRONG_WORKSPACE"
PORT_INCOMPATIBLE = "PORT_INCOMPATIBLE"
NOT_PASSIVE = "NOT_PASSIVE"
PROPERTY_LOCKED_BY_PORT = "PROPERTY_LOCKED_BY_PORT"
NO_EFFECT = "NO_EFFECT"
PROJECT_DIRTY = "PROJECT_DIRTY"
LAST_WORKSPACE = "LAST_WORKSPACE"
LAST_VIEW = "LAST_VIEW"
SAVE_FAILED = "SAVE_FAILED"
OPEN_FAILED = "OPEN_FAILED"
CAPTURE_FAILED = "CAPTURE_FAILED"
RUN_ACTIVE = "RUN_ACTIVE"
TIMEOUT = "TIMEOUT"
APPLY_FAILED = "APPLY_FAILED"
APP_BUSY = "APP_BUSY"
APP_BUSY_MODAL = "APP_BUSY_MODAL"
APP_SHUTTING_DOWN = "APP_SHUTTING_DOWN"
UNEXPECTED_DIALOG = "UNEXPECTED_DIALOG"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
INTERNAL = "INTERNAL"
AUTH_FAILED = "AUTH_FAILED"
PROTOCOL_ERROR = "PROTOCOL_ERROR"

ERROR_CODES: tuple[str, ...] = (
    INVALID_PARAMS,
    UNKNOWN_OP,
    NOT_FOUND,
    UNKNOWN_NODE_TYPE,
    WRONG_SCOPE,
    WRONG_WORKSPACE,
    PORT_INCOMPATIBLE,
    NOT_PASSIVE,
    PROPERTY_LOCKED_BY_PORT,
    NO_EFFECT,
    PROJECT_DIRTY,
    LAST_WORKSPACE,
    LAST_VIEW,
    SAVE_FAILED,
    OPEN_FAILED,
    CAPTURE_FAILED,
    RUN_ACTIVE,
    TIMEOUT,
    APPLY_FAILED,
    APP_BUSY,
    APP_BUSY_MODAL,
    APP_SHUTTING_DOWN,
    UNEXPECTED_DIALOG,
    NOT_IMPLEMENTED,
    INTERNAL,
    AUTH_FAILED,
    PROTOCOL_ERROR,
)

# Codes an agent may simply retry after a short delay.
RETRYABLE_CODES: frozenset[str] = frozenset({APP_BUSY, APP_BUSY_MODAL, TIMEOUT})

_DEFAULT_HINTS: dict[str, str] = {
    INVALID_PARAMS: "Fix the listed parameter problems and resend the request.",
    UNKNOWN_OP: "Read the corex://ops resource (or catalog docs) to list valid operation names.",
    NOT_FOUND: "Refresh ids with graph.get or workspace.list; the id no longer exists in the active workspace.",
    UNKNOWN_NODE_TYPE: "Use catalog.list_node_types (or the suggestions in details) to pick a valid type_id.",
    WRONG_SCOPE: "Navigate with scope.navigate to the scope that owns the node, then retry.",
    WRONG_WORKSPACE: "Activate the owning workspace with workspace.update(activate=true), then retry.",
    PORT_INCOMPATIBLE: "Inspect both nodes with graph.get_node and choose compatible ports (kind and data type).",
    NOT_PASSIVE: "This op only applies to passive nodes (flowchart, annotation, media); use node.update for others.",
    PROPERTY_LOCKED_BY_PORT: "Disconnect or unexpose the port that drives this property before editing it.",
    NO_EFFECT: "The owner rejected or ignored the change; check the details and current node state.",
    PROJECT_DIRTY: "Save with project.save or pass discard_unsaved=true to proceed without saving.",
    LAST_WORKSPACE: "Create another workspace first; the last workspace cannot be closed.",
    LAST_VIEW: "Create another view first; the last view cannot be closed.",
    SAVE_FAILED: "Check the path is writable and ends with .cxproj, then retry project.save.",
    OPEN_FAILED: "Check the path exists and is a readable .cxproj, then retry project.open.",
    CAPTURE_FAILED: "Ensure the canvas has content and the app is idle, then retry capture.screenshot.",
    RUN_ACTIVE: "A run (or the auto-run your edits queued) is in flight: wait with run.status(wait=true) or stop it with run.control(stop), then start again.",
    TIMEOUT: "Retry with a larger timeout_s, or poll run.status without wait.",
    APPLY_FAILED: "Fix the failing op in the batch; atomic batches were rolled back.",
    APP_BUSY: "The app is saving or loading a project; retry shortly.",
    APP_BUSY_MODAL: "A dialog is open in the COREX window; ask the user to close it, then retry.",
    APP_SHUTTING_DOWN: "COREX is closing; reconnect to another instance or relaunch.",
    UNEXPECTED_DIALOG: "An unexpected dialog appeared and was dismissed; inspect the app state before retrying.",
    NOT_IMPLEMENTED: "This op is declared but not implemented in this build.",
    INTERNAL: "Report the details; retry once after checking app state.",
    AUTH_FAILED: "Reconnect using the token from the instance discovery file.",
    PROTOCOL_ERROR: "Send one NDJSON object per line with id, op, and params.",
}


def default_hint(code: str) -> str:
    return _DEFAULT_HINTS.get(code, "Inspect the error details and adjust the request.")


class AutomationOpError(Exception):
    """Raised by handlers/bridge; serialized to the frozen error envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        hint: str = "",
        details: Mapping[str, Any] | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)
        self.hint = str(hint) or default_hint(self.code)
        self.details: dict[str, Any] = dict(details or {})
        self.retryable = bool(retryable) if retryable is not None else self.code in RETRYABLE_CODES

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "hint": self.hint,
            "details": dict(self.details),
            "retryable": bool(self.retryable),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AutomationOpError":
        details = payload.get("details")
        return cls(
            str(payload.get("code") or INTERNAL),
            str(payload.get("message") or ""),
            hint=str(payload.get("hint") or ""),
            details=details if isinstance(details, Mapping) else {},
            retryable=bool(payload.get("retryable", False)),
        )


def invalid_params(problems: list[str] | tuple[str, ...], *, op: str = "") -> AutomationOpError:
    listed = [str(problem) for problem in problems]
    message = f"Invalid parameters for {op}: " if op else "Invalid parameters: "
    message += "; ".join(listed) if listed else "unknown problem"
    return AutomationOpError(INVALID_PARAMS, message, details={"problems": listed, "op": op})


def not_found(kind: str, identifier: str, *, hint: str = "") -> AutomationOpError:
    return AutomationOpError(
        NOT_FOUND,
        f"{kind} '{identifier}' was not found in the active workspace.",
        hint=hint,
        details={"kind": kind, "id": identifier},
    )


def not_implemented(op: str) -> AutomationOpError:
    return AutomationOpError(NOT_IMPLEMENTED, f"Operation '{op}' is not implemented yet.", details={"op": op})


def no_effect(op: str, reason: str, *, details: Mapping[str, Any] | None = None) -> AutomationOpError:
    merged = {"op": op, **dict(details or {})}
    return AutomationOpError(NO_EFFECT, f"{op} had no effect: {reason}", details=merged)


__all__ = [
    "APPLY_FAILED",
    "APP_BUSY",
    "APP_BUSY_MODAL",
    "APP_SHUTTING_DOWN",
    "AUTH_FAILED",
    "AutomationOpError",
    "CAPTURE_FAILED",
    "ERROR_CODES",
    "INTERNAL",
    "INVALID_PARAMS",
    "LAST_VIEW",
    "LAST_WORKSPACE",
    "NOT_FOUND",
    "NOT_IMPLEMENTED",
    "NOT_PASSIVE",
    "NO_EFFECT",
    "OPEN_FAILED",
    "PORT_INCOMPATIBLE",
    "PROJECT_DIRTY",
    "PROPERTY_LOCKED_BY_PORT",
    "PROTOCOL_ERROR",
    "RETRYABLE_CODES",
    "RUN_ACTIVE",
    "SAVE_FAILED",
    "TIMEOUT",
    "UNEXPECTED_DIALOG",
    "UNKNOWN_NODE_TYPE",
    "UNKNOWN_OP",
    "WRONG_SCOPE",
    "WRONG_WORKSPACE",
    "default_hint",
    "invalid_params",
    "no_effect",
    "not_found",
    "not_implemented",
]
