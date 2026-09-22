# Purpose: Aggregate the per-domain op specs into one validated, JSON-serialisable catalog (drives validation, MCP tools, client, docs).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

import importlib
import re
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from ea_node_editor.automation.errors import UNKNOWN_OP, AutomationOpError, invalid_params
from ea_node_editor.automation.op_model import OpSpec, apply_defaults, validate_params
from ea_node_editor.automation.ops import DOMAIN_MODULES

_OP_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _load_domain_ops(module_name: str) -> tuple[OpSpec, ...]:
    module = importlib.import_module(f"ea_node_editor.automation.ops.{module_name}")
    ops = module.OPS
    if not isinstance(ops, tuple) or not all(isinstance(op, OpSpec) for op in ops):
        raise TypeError(f"ea_node_editor.automation.ops.{module_name}.OPS must be a tuple of OpSpec")
    return ops


@lru_cache(maxsize=1)
def all_ops() -> tuple[OpSpec, ...]:
    """Return every op in catalog order, validating uniqueness and naming once."""
    collected: list[OpSpec] = []
    seen_names: set[str] = set()
    seen_tools: set[str] = set()
    for module_name in DOMAIN_MODULES:
        for op in _load_domain_ops(module_name):
            if not _OP_NAME_RE.match(op.name):
                raise ValueError(f"op name {op.name!r} must look like domain.verb")
            if op.name in seen_names:
                raise ValueError(f"duplicate op name {op.name!r}")
            seen_names.add(op.name)
            if op.mcp_tool is not None:
                if not _TOOL_NAME_RE.match(op.mcp_tool):
                    raise ValueError(f"mcp tool name {op.mcp_tool!r} for {op.name} is not snake_case")
                if op.mcp_tool in seen_tools:
                    raise ValueError(f"duplicate mcp tool name {op.mcp_tool!r}")
                seen_tools.add(op.mcp_tool)
            if op.apply_allowed and op.name == "graph.apply":
                raise ValueError("graph.apply cannot nest")
            collected.append(op)
    return tuple(collected)


@lru_cache(maxsize=1)
def _ops_by_name() -> dict[str, OpSpec]:
    return {op.name: op for op in all_ops()}


def op_names() -> tuple[str, ...]:
    return tuple(op.name for op in all_ops())


def op_by_name(name: str) -> OpSpec:
    """Return the op or raise UNKNOWN_OP with close suggestions."""
    normalized = str(name or "").strip()
    spec = _ops_by_name().get(normalized)
    if spec is None:
        suggestions = _suggest_ops(normalized)
        raise AutomationOpError(
            UNKNOWN_OP,
            f"Unknown operation '{normalized}'.",
            details={"op": normalized, "suggestions": suggestions},
        )
    return spec


def op_or_none(name: str) -> OpSpec | None:
    return _ops_by_name().get(str(name or "").strip())


def ops_by_domain() -> dict[str, tuple[OpSpec, ...]]:
    grouped: dict[str, list[OpSpec]] = {}
    for op in all_ops():
        grouped.setdefault(op.domain, []).append(op)
    return {domain: tuple(ops) for domain, ops in grouped.items()}


def mcp_tool_ops() -> tuple[OpSpec, ...]:
    return tuple(op for op in all_ops() if op.mcp_tool is not None)


def op_for_mcp_tool(tool_name: str) -> OpSpec | None:
    normalized = str(tool_name or "").strip()
    for op in all_ops():
        if op.mcp_tool == normalized:
            return op
    return None


def apply_allowed_ops() -> tuple[OpSpec, ...]:
    return tuple(op for op in all_ops() if op.apply_allowed)


def validate_op_params(op: OpSpec, params: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate ``params`` against ``op.params`` and return a defaults-filled copy."""
    raw = dict(params or {})
    problems = validate_params(op.params, raw)
    if problems:
        raise invalid_params(problems, op=op.name)
    filled = apply_defaults(op.params, raw)
    return dict(filled)


def catalog_json() -> dict[str, Any]:
    """JSON-serialisable snapshot of the whole catalog (used by docs and MCP resources)."""
    return {
        "protocol": 1,
        "ops": [op.to_dict() for op in all_ops()],
        "domains": {domain: [op.name for op in ops] for domain, ops in ops_by_domain().items()},
        "mcp_tools": {op.mcp_tool: op.name for op in mcp_tool_ops()},
    }


def _suggest_ops(name: str, *, limit: int = 5) -> list[str]:
    import difflib

    candidates = list(op_names())
    close = difflib.get_close_matches(name, candidates, n=limit, cutoff=0.4)
    if close:
        return close
    prefix = name.split(".", 1)[0]
    return [candidate for candidate in candidates if candidate.startswith(prefix + ".")][:limit]


__all__ = [
    "all_ops",
    "apply_allowed_ops",
    "catalog_json",
    "mcp_tool_ops",
    "op_by_name",
    "op_for_mcp_tool",
    "op_names",
    "op_or_none",
    "ops_by_domain",
    "validate_op_params",
]
