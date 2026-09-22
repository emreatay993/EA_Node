# Purpose: Validate params, run one handler inside a single grouped undo step, and translate failures into the error envelope.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from contextlib import nullcontext
from typing import Any

from ea_node_editor.automation.errors import INTERNAL, AutomationOpError
from ea_node_editor.automation.op_catalog import op_by_name, validate_op_params
from ea_node_editor.automation.op_model import Deferred, OpSpec
from ea_node_editor.ui.shell.automation.context import AutomationContext

logger = logging.getLogger(__name__)

Handler = Callable[[AutomationContext, Mapping[str, Any]], "dict[str, Any] | Deferred"]
HandlerTable = Mapping[str, Handler]

HISTORY_ACTION_PREFIX = "automation:"


def history_action_type(op: OpSpec, label: str = "") -> str:
    suffix = str(label or "").strip()
    return f"{HISTORY_ACTION_PREFIX}{op.name}" + (f" ({suffix})" if suffix else "")


def grouped_history_scope(context: AutomationContext, op: OpSpec, *, label: str = "") -> Any:
    """Return the context manager that makes a mutating op one undo step."""
    if not op.mutates_graph or context.runtime_history is None:
        return nullcontext()
    workspace = context.active_workspace()
    return context.runtime_history.grouped_action(
        workspace.workspace_id,
        history_action_type(op, label),
        workspace,
    )


def execute_op(
    context: AutomationContext,
    handlers: HandlerTable,
    op_name: str,
    params: Mapping[str, Any] | None,
) -> dict[str, Any] | Deferred:
    """Run ``op_name`` synchronously on the current thread (GUI thread in production).

    Raises ``AutomationOpError`` for every failure so callers only need one
    translation point. Unexpected exceptions become ``INTERNAL`` with the
    exception type in ``details``.
    """
    op = op_by_name(op_name)
    handler = handlers.get(op.name)
    if handler is None:
        raise AutomationOpError(INTERNAL, f"No handler registered for {op.name}.", details={"op": op.name})
    filled = validate_op_params(op, params)
    try:
        with grouped_history_scope(context, op, label=str(filled.get("label", "")) if op.name == "graph.apply" else ""):
            result = handler(context, filled)
    except AutomationOpError:
        raise
    except Exception as exc:  # noqa: BLE001 - translated into the frozen envelope
        logger.exception("automation op %s failed", op.name)
        raise AutomationOpError(
            INTERNAL,
            f"{op.name} raised {type(exc).__name__}: {exc}",
            details={"op": op.name, "exception": type(exc).__name__},
        ) from exc
    if isinstance(result, Deferred):
        return result
    if not isinstance(result, Mapping):
        raise AutomationOpError(INTERNAL, f"{op.name} returned {type(result).__name__} instead of a result object.")
    return dict(result)


__all__ = ["HISTORY_ACTION_PREFIX", "Handler", "HandlerTable", "execute_op", "grouped_history_scope", "history_action_type"]
