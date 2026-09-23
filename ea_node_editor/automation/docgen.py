# Purpose: Render the generated op / tool / error reference (markdown) from the op catalog for docs/AUTOMATION_API_GUIDE.md and corex://ops.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_docgen.py
"""Deterministic markdown generation from the automation op catalog.

Three renderers, each returning markdown that ends with exactly one newline:

- :func:`render_tool_index_markdown` -- one table ``MCP tool -> op -> summary``.
- :func:`render_op_reference_markdown` -- one ``### <domain>`` section per
  domain in catalog order; per op a ``#### <op name>`` block with the MCP tool
  name, flags, summary, description, a one-level params table, the result keys,
  and the example JSON when the spec carries one.
- :func:`render_error_reference_markdown` -- the frozen error codes with their
  retryable flag and default hint.

:func:`render_generated_reference_markdown` joins the three with a blank line;
that exact text sits between :data:`GENERATED_BLOCK_BEGIN` and
:data:`GENERATED_BLOCK_END` in ``docs/AUTOMATION_API_GUIDE.md``
(``tests/automation/test_docgen.py`` fails on drift). Regenerate with::

    python -m ea_node_editor.automation.docgen --update-guide

Stdlib only; never imports Qt or the UI package.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ea_node_editor.automation import op_catalog
from ea_node_editor.automation.errors import ERROR_CODES, RETRYABLE_CODES, default_hint
from ea_node_editor.automation.op_model import OpSpec

GENERATED_BLOCK_BEGIN = "<!-- BEGIN GENERATED OP REFERENCE -->"
GENERATED_BLOCK_END = "<!-- END GENERATED OP REFERENCE -->"
DEFAULT_GUIDE_PATH = Path(__file__).resolve().parents[2] / "docs" / "AUTOMATION_API_GUIDE.md"
REGENERATE_COMMAND = "python -m ea_node_editor.automation.docgen --update-guide"

_SECTIONS = ("tool-index", "ops", "errors")


# ------------------------------------------------------------------ helpers


def _prose(text: Any) -> str:
    """Escape ``<`` and ``*`` so renderers never read ``ops[i].<path>`` as HTML or ``passive.*`` as emphasis."""
    value = "" if text is None else str(text)
    return value.replace("<", "\\<").replace("*", "\\*")


def _escape_cell(text: Any) -> str:
    """Make prose safe inside a markdown table cell (backslashes, pipes, newlines, ``<``)."""
    value = "" if text is None else str(text)
    return _prose(value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip())


def _code_cell(text: Any) -> str:
    """A code span inside a table cell; only pipes need escaping there."""
    return _code(text).replace("|", "\\|")


def _code(text: Any) -> str:
    value = "" if text is None else str(text)
    return f"`{value}`" if value else ""


def _declared_types(schema: Mapping[str, Any]) -> list[str]:
    declared = schema.get("type")
    if declared is None:
        types: list[str] = []
    elif isinstance(declared, str):
        types = [declared]
    else:
        types = [str(item) for item in declared]
    if schema.get("nullable") and "null" not in types:
        types.append("null")
    return types


def _type_label(schema: Mapping[str, Any], *, depth: int = 0) -> str:
    """Compact type label: nested objects are ``object``, arrays are ``array<item>``."""
    if not isinstance(schema, Mapping):
        return "any"
    branches = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(branches, Sequence) and branches and not isinstance(branches, (str, bytes)):
        return " or ".join(_type_label(branch, depth=depth + 1) for branch in branches if isinstance(branch, Mapping))
    types = _declared_types(schema)
    if not types:
        return "string" if schema.get("enum") else "any"
    labels: list[str] = []
    for name in types:
        if name == "array":
            items = schema.get("items")
            item_label = _type_label(items, depth=depth + 1) if isinstance(items, Mapping) and depth == 0 else "any"
            labels.append(f"array<{item_label}>")
        else:
            labels.append(name)
    return " or ".join(labels)


def _default_label(schema: Mapping[str, Any]) -> str:
    if "default" not in schema:
        return ""
    return _code(json.dumps(schema["default"], ensure_ascii=False, sort_keys=True))


def _notes_label(schema: Mapping[str, Any]) -> str:
    notes: list[str] = []
    description = str(schema.get("description") or "").strip()
    if description:
        notes.append(description)
    enum = schema.get("enum")
    if isinstance(enum, Sequence) and not isinstance(enum, (str, bytes)) and enum:
        notes.append("one of: " + ", ".join(str(item) for item in enum))
    items = schema.get("items")
    if isinstance(items, Mapping):
        item_enum = items.get("enum")
        if isinstance(item_enum, Sequence) and not isinstance(item_enum, (str, bytes)) and item_enum:
            notes.append("items one of: " + ", ".join(str(item) for item in item_enum))
    ranges: list[str] = []
    if "minimum" in schema:
        ranges.append(f">= {schema['minimum']}")
    if "maximum" in schema:
        ranges.append(f"<= {schema['maximum']}")
    if ranges:
        notes.append(" and ".join(ranges))
    if "minItems" in schema:
        notes.append(f"min {schema['minItems']} item(s)")
    if "maxItems" in schema:
        notes.append(f"max {schema['maxItems']} item(s)")
    if "minLength" in schema and int(schema["minLength"]) > 0:
        notes.append("non-empty")
    return "; ".join(notes)


def _flags_label(op: OpSpec) -> str:
    flags: list[str] = []
    flags.append("undo step" if op.mutates_graph else "read-only")
    if op.apply_allowed:
        flags.append("apply-allowed")
    if op.deferred:
        flags.append("deferred")
    return ", ".join(flags)


def _params_table(op: OpSpec) -> list[str]:
    properties = op.params.get("properties")
    if not isinstance(properties, Mapping) or not properties:
        return ["No parameters.", ""]
    required = {str(key) for key in (op.params.get("required") or ())}
    lines = [
        "| Param | Type | Required | Default | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key, schema in properties.items():
        sub = schema if isinstance(schema, Mapping) else {}
        lines.append(
            "| "
            + " | ".join(
                (
                    _code(key),
                    _code_cell(_type_label(sub)),
                    "yes" if key in required else "no",
                    _default_label(sub).replace("|", "\\|"),
                    _escape_cell(_notes_label(sub)),
                )
            )
            + " |"
        )
    lines.append("")
    return lines


def _result_line(op: OpSpec) -> str:
    properties = op.result.get("properties")
    if not isinstance(properties, Mapping) or not properties:
        return "Result: object."
    keys = ", ".join(_code(key) for key in properties)
    return f"Result keys: {keys}."


def _example_lines(op: OpSpec) -> list[str]:
    lines: list[str] = []
    for index, example in enumerate(op.examples, start=1):
        label = "Example" if len(op.examples) == 1 else f"Example {index}"
        lines.append(f"{label}:")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(dict(example), indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
    return lines


def _op_block(op: OpSpec) -> list[str]:
    lines = [f"#### {op.name}", ""]
    tool = _code(op.mcp_tool) if op.mcp_tool else "none (protocol only)"
    lines.append(f"MCP tool: {tool}. Flags: {_flags_label(op)}.")
    lines.append("")
    lines.append(_prose(op.summary.strip()))
    lines.append("")
    description = op.description.strip()
    if description:
        lines.append(_prose(description))
        lines.append("")
    lines.extend(_params_table(op))
    lines.append(_result_line(op))
    lines.append("")
    lines.extend(_example_lines(op))
    return lines


# ---------------------------------------------------------------- renderers


def render_tool_index_markdown() -> str:
    """Table of every MCP tool with its wire op and summary, in catalog order."""
    lines = [
        "### MCP tool index",
        "",
        "| MCP tool | Op | Summary |",
        "| --- | --- | --- |",
    ]
    for op in op_catalog.mcp_tool_ops():
        lines.append(f"| {_code(op.mcp_tool)} | {_code(op.name)} | {_escape_cell(op.summary)} |")
    return "\n".join(lines) + "\n"


def render_op_reference_markdown() -> str:
    """One ``### <domain>`` section per domain (catalog order) with a ``####`` block per op."""
    lines: list[str] = []
    for domain, ops in op_catalog.ops_by_domain().items():
        lines.append(f"### {domain}")
        lines.append("")
        for op in ops:
            lines.extend(_op_block(op))
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def render_error_reference_markdown() -> str:
    """Frozen error codes with retryable flag and default hint."""
    lines = [
        "### Error codes",
        "",
        "| Code | Retryable | Default hint |",
        "| --- | --- | --- |",
    ]
    for code in ERROR_CODES:
        retryable = "yes" if code in RETRYABLE_CODES else "no"
        lines.append(f"| {_code(code)} | {retryable} | {_escape_cell(default_hint(code))} |")
    return "\n".join(lines) + "\n"


def render_generated_reference_markdown() -> str:
    """Tool index + op reference + error reference, separated by one blank line."""
    return "\n".join(
        (
            render_tool_index_markdown(),
            render_op_reference_markdown(),
            render_error_reference_markdown(),
        )
    )


def render_guide_block() -> str:
    """The exact text embedded in the guide, markers included."""
    return f"{GENERATED_BLOCK_BEGIN}\n{render_generated_reference_markdown()}{GENERATED_BLOCK_END}"


def extract_guide_block(text: str) -> str | None:
    """Return the text between the markers (newline after BEGIN included) or ``None``."""
    start = text.find(GENERATED_BLOCK_BEGIN)
    end = text.find(GENERATED_BLOCK_END)
    if start < 0 or end < 0 or end < start:
        return None
    return text[start + len(GENERATED_BLOCK_BEGIN) : end]


def update_guide(path: Path = DEFAULT_GUIDE_PATH) -> bool:
    """Rewrite the generated block in ``path``; returns ``True`` when the file changed."""
    text = path.read_text(encoding="utf-8")
    start = text.find(GENERATED_BLOCK_BEGIN)
    end = text.find(GENERATED_BLOCK_END)
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"{path} does not contain the generated block markers")
    updated = text[:start] + render_guide_block() + text[end + len(GENERATED_BLOCK_END) :]
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def render_section(section: str) -> str:
    if section == "tool-index":
        return render_tool_index_markdown()
    if section == "ops":
        return render_op_reference_markdown()
    if section == "errors":
        return render_error_reference_markdown()
    return render_generated_reference_markdown()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ea_node_editor.automation.docgen",
        description="Print the generated automation reference (markdown) or refresh it inside the guide.",
    )
    parser.add_argument("--section", choices=("all", *_SECTIONS), default="all")
    parser.add_argument(
        "--update-guide",
        nargs="?",
        const=str(DEFAULT_GUIDE_PATH),
        default=None,
        metavar="GUIDE_PATH",
        help="rewrite the generated block in docs/AUTOMATION_API_GUIDE.md (or the given file) instead of printing",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.update_guide:
        path = Path(args.update_guide)
        changed = update_guide(path)
        print(f"{'updated' if changed else 'unchanged'}: {path}")
        return 0
    sys.stdout.write(render_section(args.section))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DEFAULT_GUIDE_PATH",
    "GENERATED_BLOCK_BEGIN",
    "GENERATED_BLOCK_END",
    "REGENERATE_COMMAND",
    "extract_guide_block",
    "main",
    "render_error_reference_markdown",
    "render_generated_reference_markdown",
    "render_guide_block",
    "render_op_reference_markdown",
    "render_section",
    "render_tool_index_markdown",
    "update_guide",
]
