# Purpose: graph.apply batch handler: static validation, $ref resolution, one undo step, atomic snapshot rollback (T11).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_apply.py
"""``graph.apply``: run many ``apply_allowed`` ops as one undo step.

Flow:

1. Static validation (no mutation yet): op names, ``apply_allowed``, batch
   ids, ``$ref`` tokens in declared ``ref_fields`` (only earlier ids, bare
   ``$id`` only for ops with a ``primary_id_field``), and each op's params
   against its ``OpSpec`` with refs replaced by a placeholder id. Every
   problem is collected into one ``INVALID_PARAMS`` (unknown op names raise
   ``UNKNOWN_OP`` right away).
2. Execution: ``dispatch.py`` already wraps the whole call in one
   ``grouped_action``; each op runs through ``dispatch.execute_op`` so its own
   grouped action folds into the outer one.
3. Failure: the first ``AutomationOpError`` stops the batch. ``atomic=true``
   restores the pre-batch workspace snapshot inside the open group (so the
   group commits nothing) plus the saved scope and selection, and the call
   raises ``APPLY_FAILED``. ``atomic=false`` keeps what applied and returns
   ``ok`` with the failing row's error when at least one op applied; when the
   very first op fails it raises ``APPLY_FAILED`` (``rolled_back=false``).

Owner limits: staged files and the title-driven artifact folder rename are
outside the workspace snapshot and do not roll back.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from ea_node_editor.automation.errors import (
    APPLY_FAILED,
    INVALID_PARAMS,
    UNKNOWN_OP,
    AutomationOpError,
)
from ea_node_editor.automation.op_catalog import op_by_name, validate_op_params
from ea_node_editor.automation.op_model import Deferred, OpSpec
from ea_node_editor.automation.ops.apply import MAX_APPLY_OPS, REF_PATTERN
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.dispatch import execute_op

OP_NAME = "graph.apply"
PLACEHOLDER_ID = "ref_placeholder"
BATCH_ID_PATTERN = r"^[A-Za-z_][A-Za-z0-9_\-]*$"

_REF_RE = re.compile(REF_PATTERN)
_BATCH_ID_RE = re.compile(BATCH_ID_PATTERN)

# One-element holder for the merged handler table. Filled on first use (never
# at import time) because registry.build_handler_table imports this module.
_HANDLER_TABLE: list[Mapping[str, Any]] = []

RefVisitor = Callable[[str, str], Any]


# ------------------------------------------------------------------ helpers


def _handler_table() -> Mapping[str, Any]:
    if not _HANDLER_TABLE:
        from ea_node_editor.ui.shell.automation.registry import build_handler_table

        _HANDLER_TABLE.append(build_handler_table())
    return _HANDLER_TABLE[0]


def _split_ref_field(ref_field: str) -> list[tuple[str, bool]]:
    """``'node_ids[]'`` -> ``[('node_ids', True)]``; ``'a.b'`` -> ``[('a', False), ('b', False)]``."""
    segments: list[tuple[str, bool]] = []
    for raw in str(ref_field).split("."):
        each = raw.endswith("[]")
        segments.append((raw[:-2] if each else raw, each))
    return segments


def _map_ref_strings(value: Any, segments: list[tuple[str, bool]], position: int, path: str, visit: RefVisitor) -> Any:
    """Return a copy of ``value`` with ``visit(path, text)`` applied to every string at the ref path."""
    if position >= len(segments):
        return visit(path, value) if isinstance(value, str) else value
    key, each = segments[position]
    if not isinstance(value, Mapping) or key not in value:
        return value
    child = value[key]
    child_path = f"{path}.{key}"
    if each:
        if isinstance(child, (list, tuple)):
            new_child: Any = [
                _map_ref_strings(item, segments, position + 1, f"{child_path}[{index}]", visit)
                for index, item in enumerate(child)
            ]
        else:
            new_child = child
    else:
        new_child = _map_ref_strings(child, segments, position + 1, child_path, visit)
    copied = dict(value)
    copied[key] = new_child
    return copied


def _transform_ref_fields(spec: OpSpec, params: Mapping[str, Any], visit: RefVisitor) -> dict[str, Any]:
    """Apply ``visit`` to the strings in ``spec.ref_fields`` only; everything else is returned untouched."""
    transformed: Any = dict(params)
    for ref_field in spec.ref_fields:
        transformed = _map_ref_strings(transformed, _split_ref_field(ref_field), 0, "params", visit)
    return dict(transformed)


def _unescape(text: str) -> str:
    return text[1:] if text.startswith("$$") else text


def _ref_parts(text: str) -> tuple[str, str] | None:
    """``'$sub.shell_node_id'`` -> ``('sub', 'shell_node_id')``; ``None`` when ``text`` is not a ref token."""
    match = _REF_RE.match(text)
    if match is None:
        return None
    return match.group(1), match.group(2) or ""


def _lookup_path(source: Any, subpath: str) -> Any:
    """Walk ``a.b.0`` through mappings and lists; raises KeyError / IndexError / TypeError on a miss."""
    current = source
    for segment in subpath.split("."):
        if isinstance(current, Mapping):
            current = current[segment]
        elif isinstance(current, (list, tuple)):
            current = current[int(segment)]
        else:
            raise TypeError(f"cannot index {type(current).__name__} with '{segment}'")
    return current


# -------------------------------------------------------- static validation


def _plan_batch(ops: Any) -> list[dict[str, Any]]:
    """Validate the whole batch before any mutation and return the execution plan.

    Each plan step is ``{"index", "id", "op", "spec", "params", "refs"}`` where
    ``params`` are the raw request params (``$ref`` tokens and ``$$`` escapes
    still in place; they are resolved right before the op runs).
    """
    if not isinstance(ops, (list, tuple)) or not 1 <= len(ops) <= MAX_APPLY_OPS:
        raise AutomationOpError(
            INVALID_PARAMS,
            f"graph.apply needs between 1 and {MAX_APPLY_OPS} ops.",
            details={"problems": [f"params.ops: must contain between 1 and {MAX_APPLY_OPS} items"], "op": OP_NAME},
        )
    problems: list[str] = []
    blocked_ops: list[str] = []
    defined: dict[str, int] = {}
    spec_by_id: dict[str, OpSpec] = {}
    plan: list[dict[str, Any]] = []
    for index, entry in enumerate(ops):
        prefix = f"ops[{index}]"
        if not isinstance(entry, Mapping):
            problems.append(f"{prefix}: expected object, got {type(entry).__name__}")
            continue
        op_name = str(entry.get("op") or "").strip()
        try:
            spec = op_by_name(op_name)
        except AutomationOpError as exc:
            raise AutomationOpError(
                UNKNOWN_OP,
                f"{prefix}.op: {exc.message}",
                hint=exc.hint,
                details={**exc.details, "index": index},
            ) from exc
        if not spec.apply_allowed:
            problems.append(f"{prefix}.op: '{spec.name}' is not allowed inside graph.apply; run it as a separate call")
            blocked_ops.append(spec.name)

        batch_id = ""
        raw_id = entry.get("id")
        if raw_id is not None:
            batch_id = str(raw_id)
            if not _BATCH_ID_RE.match(batch_id):
                problems.append(f"{prefix}.id: must match {BATCH_ID_PATTERN} (got {batch_id!r})")
                batch_id = ""
            elif batch_id in defined:
                problems.append(f"{prefix}.id: '{batch_id}' is already used by ops[{defined[batch_id]}]")
                batch_id = ""

        raw_params = entry.get("params")
        if raw_params is None:
            raw_params = {}
        if not isinstance(raw_params, Mapping):
            problems.append(f"{prefix}.params: expected object, got {type(raw_params).__name__}")
            raw_params = {}
        refs: list[dict[str, str]] = []

        def visit(path: str, text: str, _refs: list[dict[str, str]] = refs, _prefix: str = prefix) -> Any:
            if text.startswith("$$"):
                return _unescape(text)
            parts = _ref_parts(text)
            if parts is None:
                return text
            name, subpath = parts
            location = f"{_prefix}.{path}"
            if name not in defined:
                problems.append(f"{location}: '{text}' references '{name}', which is not defined by an earlier op")
            elif not subpath and not spec_by_id[name].primary_id_field:
                problems.append(
                    f"{location}: '{text}' refers to op '{spec_by_id[name].name}' which has no primary id; use '{text}.<field>'"
                )
            _refs.append({"path": location, "token": text, "id": name, "subpath": subpath})
            return PLACEHOLDER_ID

        placeholder = _transform_ref_fields(spec, raw_params, visit)
        try:
            validate_op_params(spec, placeholder)
        except AutomationOpError as exc:
            listed = exc.details.get("problems") if isinstance(exc.details, Mapping) else None
            for problem in listed if isinstance(listed, list) and listed else [exc.message]:
                problems.append(f"{prefix}.{problem}")

        if batch_id:
            defined[batch_id] = index
            spec_by_id[batch_id] = spec
        plan.append({"index": index, "id": batch_id, "op": spec.name, "spec": spec, "params": dict(raw_params), "refs": refs})

    if problems:
        hint = "Fix the listed problems and resend the batch; nothing was applied."
        if blocked_ops:
            hint = "Remove the ops that are not apply_allowed and run them as separate calls, then resend the batch."
        raise AutomationOpError(
            INVALID_PARAMS,
            f"Invalid parameters for {OP_NAME}: " + "; ".join(problems),
            hint=hint,
            details={"problems": problems, "op": OP_NAME, "blocked_ops": blocked_ops},
        )
    return plan


# --------------------------------------------------------------- execution


def _resolve_params(step: Mapping[str, Any], results_by_id: Mapping[str, Mapping[str, Any]], primary_ids: Mapping[str, str]) -> dict[str, Any]:
    """Replace ``$ref`` tokens with earlier results and unescape ``$$`` in the op's ref fields."""

    def visit(path: str, text: str) -> Any:
        if text.startswith("$$"):
            return _unescape(text)
        parts = _ref_parts(text)
        if parts is None:
            return text
        name, subpath = parts
        location = f"ops[{step['index']}].{path}"
        if name not in results_by_id:
            raise AutomationOpError(
                APPLY_FAILED,
                f"{location}: '{text}' references '{name}', which produced no result.",
                details={"index": step["index"], "token": text, "path": location},
            )
        if not subpath:
            primary = primary_ids.get(name)
            if primary is None:
                raise AutomationOpError(
                    APPLY_FAILED,
                    f"{location}: '{text}' has no primary id to resolve to.",
                    details={"index": step["index"], "token": text, "path": location},
                )
            return primary
        try:
            return _lookup_path(results_by_id[name], subpath)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AutomationOpError(
                APPLY_FAILED,
                f"{location}: '{text}' does not resolve in the result of '{name}' ({type(exc).__name__}: {exc}).",
                hint="Check the earlier op's result shape (see its result schema) and fix the $ref path.",
                details={
                    "index": step["index"],
                    "token": text,
                    "path": location,
                    "available": sorted(results_by_id[name]) if isinstance(results_by_id[name], Mapping) else [],
                },
            ) from exc

    return _transform_ref_fields(step["spec"], step["params"], visit)


def _rollback(
    context: AutomationContext,
    workspace: Any,
    workspace_id: str,
    before: Any,
    saved_scope: list[str],
    saved_selection: list[str],
) -> None:
    """Restore the pre-batch snapshot, then the scope path and selection, inside the open history group."""
    workspace.restore_snapshot(before)
    scene = context.scene
    scene.refresh_workspace_from_model(workspace_id)
    scene.navigate_scope_root()
    for shell_id in saved_scope:
        if context.node_or_none(shell_id) is None:
            break
        if not scene.open_subnode_scope(shell_id):
            break
    scene.clear_selection()
    for node_id in saved_selection:
        if context.node_or_none(node_id) is not None:
            scene.select_node(node_id, True)


def _failure_error(
    failure: AutomationOpError,
    step: Mapping[str, Any],
    *,
    rolled_back: bool,
    applied: int,
    rows: list[dict[str, Any]],
    ids: Mapping[str, str],
) -> AutomationOpError:
    index = int(step["index"])
    if rolled_back:
        hint = f"The batch was rolled back; fix ops[{index}] ({step['op']}) and resend the whole batch."
    else:
        hint = f"Nothing was applied; fix ops[{index}] ({step['op']}) and resend the batch."
    return AutomationOpError(
        APPLY_FAILED,
        f"graph.apply failed at ops[{index}] ({step['op']}): {failure.message}",
        hint=hint,
        details={
            "failed_index": index,
            "failed_id": step["id"],
            "failed_op": step["op"],
            "error": failure.to_dict(),
            "rolled_back": bool(rolled_back),
            "applied": int(applied),
            "results": rows,
            "ids": dict(ids),
        },
    )


def apply_graph_ops(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    atomic = bool(params.get("atomic", True))
    plan = _plan_batch(params.get("ops"))
    handlers = _handler_table()

    workspace = context.active_workspace()
    workspace_id = context.workspace_id()
    before = workspace.capture_snapshot()
    saved_scope = context.scope_path()
    saved_selection = context.selected_node_ids()

    results_by_id: dict[str, dict[str, Any]] = {}
    ids: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    failure: AutomationOpError | None = None
    failed_step: Mapping[str, Any] | None = None
    for step in plan:
        try:
            resolved = _resolve_params(step, results_by_id, ids)
            outcome = execute_op(context, handlers, step["op"], resolved)
            if isinstance(outcome, Deferred):
                raise AutomationOpError(
                    APPLY_FAILED,
                    f"{step['op']} returned a deferred result; deferred ops cannot run inside graph.apply.",
                    details={"index": step["index"], "op": step["op"]},
                )
        except AutomationOpError as exc:
            failure = exc
            failed_step = step
            rows.append({"index": step["index"], "id": step["id"], "op": step["op"], "ok": False, "error": exc.to_dict()})
            break
        rows.append({"index": step["index"], "id": step["id"], "op": step["op"], "ok": True, "result": outcome})
        if step["id"]:
            results_by_id[step["id"]] = outcome
            primary_field = step["spec"].primary_id_field
            if primary_field and primary_field in outcome:
                ids[step["id"]] = str(outcome[primary_field])

    if failure is None or failed_step is None:
        return {"results": rows, "applied": len(rows), "failed_index": -1, "rolled_back": False, "ids": ids}

    applied = len(rows) - 1
    failed_index = int(failed_step["index"])
    if atomic:
        _rollback(context, workspace, workspace_id, before, saved_scope, saved_selection)
        raise _failure_error(failure, failed_step, rolled_back=True, applied=0, rows=rows, ids={})
    if applied > 0:
        return {"results": rows, "applied": applied, "failed_index": failed_index, "rolled_back": False, "ids": ids}
    raise _failure_error(failure, failed_step, rolled_back=False, applied=0, rows=rows, ids=ids)


HANDLERS = {
    'graph.apply': apply_graph_ops,
}

__all__ = ["BATCH_ID_PATTERN", "HANDLERS", "OP_NAME", "PLACEHOLDER_ID"]
