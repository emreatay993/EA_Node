# Purpose: Analyze and edit Python Script interfaces without executing authored code.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_python_script_authoring.py

from __future__ import annotations

import ast
import keyword
import re
from dataclasses import dataclass
from typing import Any, Mapping

from ea_node_editor.nodes import declaration_engine as engine
from ea_node_editor.nodes.python_script_authoring_source import SourceDocument, SourceRange, apply_edits
from ea_node_editor.nodes.python_script_declaration import (
    PYTHON_SCRIPT_DECORATOR_FIELDS, PythonScriptDeclarationError, _fail, _parse,
)


@dataclass(frozen=True, slots=True)
class AuthoringDiagnostic:
    message: str
    line: int = 1
    column: int = 1
    code: str = "declaration"
    severity: str = "error"
    fix: str = ""


@dataclass(frozen=True, slots=True)
class InterfaceItem:
    key: str
    kind: str
    fields: dict[str, Any]
    expressions: dict[str, str]
    source_range: SourceRange
    data_type: str
    data_access: str
    label: str
    section: str
    has_port: bool


@dataclass(frozen=True, slots=True)
class AuthoringAnalysis:
    items: tuple[InterfaceItem, ...] = ()
    diagnostics: tuple[AuthoringDiagnostic, ...] = ()
    parameter_keys: tuple[str, ...] = ()
    output_keys: tuple[str, ...] = ()
    signature_keys: tuple[str, ...] = ()
    can_synchronize: bool = False

    @property
    def valid(self) -> bool:
        return not any(item.severity == "error" for item in self.diagnostics)


@dataclass(frozen=True, slots=True)
class GuidedRename:
    old_key: str
    new_key: str
    kind: str


@dataclass(frozen=True, slots=True)
class SourceChange:
    start: int
    end: int
    replacement: str
    line: int
    before: str


@dataclass(frozen=True, slots=True)
class SourceEditResult:
    source: str
    renames: tuple[GuidedRename, ...] = ()
    changes: tuple[SourceChange, ...] = ()
    selected_key: str = ""


def type_expression(value: str) -> str:
    """Accept a catalog ID or one of the parser's explicit type spellings."""
    if value in engine.BUILTIN_TYPES:
        return value
    if value.startswith("corex.") and value[6:] in engine.TYPE_ALIASES:
        return value
    for name, type_id in engine.BUILTIN_TYPES.items():
        if value == type_id:
            return name
    for name, type_id in engine.TYPE_ALIASES.items():
        if value == type_id:
            return "corex." + name
    return repr(value)


def _function(source: str) -> ast.FunctionDef:
    return next(
        node for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef)
        and any(engine.corex_decorator_name(item) == "node" for item in node.decorator_list)
    )


def _decorators(function: ast.FunctionDef) -> dict[str, ast.Call]:
    return {
        node.args[0].value: node for node in function.decorator_list
        if isinstance(node, ast.Call) and engine.corex_decorator_name(node) != "node"
    }


def _diagnostic(exc: Exception, source: str, *, fix: str = "") -> AuthoringDiagnostic:
    match = re.search(r"\(line (\d+), column (\d+)\)", str(exc))
    line = int(match[1]) if match else getattr(exc, "line", 1)
    column = int(match[2]) if match else getattr(exc, "column", 1)
    if getattr(exc, "column_is_utf8", False):
        lines = source.split("\n")
        if 0 < line <= len(lines):
            column = len(lines[line - 1].encode("utf-8")[:column - 1].decode("utf-8", errors="ignore")) + 1
    return AuthoringDiagnostic(
        str(exc), line, column,
        "signature" if fix else "declaration", fix=fix,
    )


def analyze_source(source: str) -> AuthoringAnalysis:
    """Inventory valid declarations even when manually edited parameters mismatch."""
    try:
        declaration = _parse(source, validate_signature=False)
        function = _function(source)
        document = SourceDocument(source)
        items: list[InterfaceItem] = []
        for key, decorator in _decorators(function).items():
            kind = engine.corex_decorator_name(decorator)
            assert kind is not None
            _, values, nodes = engine.call_values(
                decorator, kind, allowed=PYTHON_SCRIPT_DECORATOR_FIELDS[kind], fail=_fail,
            )
            if kind in engine.CONTROL_DECORATORS:
                prop, data_type, _accepted, access = engine.control_spec(kind, key, values)
                label = prop.label
            else:
                data_type, access = values["value_type"], values.get("structure", "item")
                label = engine.label_value(key, values)
            items.append(InterfaceItem(
                key, kind, values, {name: document.text(node) for name, node in nodes.items()},
                document.decorator_range(decorator), data_type, access, label,
                str(values.get("section", "")), kind in {"input", "output"} or bool(values.get("port")),
            ))
        diagnostics: tuple[AuthoringDiagnostic, ...] = ()
        try:
            _parse(source)
        except PythonScriptDeclarationError as exc:
            diagnostics = (_diagnostic(exc, source, fix="synchronize_parameters"),)
        return AuthoringAnalysis(
            tuple(items), diagnostics, declaration.parameter_keys, declaration.output_keys,
            tuple(arg.arg for arg in function.args.args), bool(diagnostics),
        )
    except (ValueError, SyntaxError, RecursionError, OverflowError) as exc:
        return AuthoringAnalysis(diagnostics=(_diagnostic(exc, source),))


def _validate_key(key: str) -> None:
    if not key.isidentifier() or keyword.iskeyword(key) or key in {
        "ctx", "corex", "__builtins__", "script", "timeout_sec",
    }:
        raise PythonScriptDeclarationError("Choose an unreserved Python variable name")


def _field_expression(name: str, value: Any) -> str:
    if name in {"value_type", "item_type"}:
        if not isinstance(value, str) or not value.strip():
            raise PythonScriptDeclarationError("Select an explicit data type")
        return type_expression(value)
    expression = repr(value)
    if len(expression.encode("utf-8")) > engine.MAX_SOURCE_BYTES:
        raise PythonScriptDeclarationError("Decorator literal is too large")
    try:
        node = ast.parse(expression, mode="eval").body
        engine.bounded_literal(node, fail=_fail)
    except (SyntaxError, RecursionError) as exc:
        raise PythonScriptDeclarationError("Use a simple Python literal for this field") from exc
    return expression


def _new_decorator(kind: str, key: str, fields: Mapping[str, Any]) -> str:
    if kind not in PYTHON_SCRIPT_DECORATOR_FIELDS or kind == "node":
        raise PythonScriptDeclarationError("Choose an input, output, or supported control")
    unknown = set(fields) - PYTHON_SCRIPT_DECORATOR_FIELDS[kind]
    if unknown:
        raise PythonScriptDeclarationError(f"Unsupported {kind} fields: {', '.join(sorted(unknown))}")
    if kind in {"input", "output"} and "value_type" not in fields:
        raise PythonScriptDeclarationError("Select an explicit data type")
    arguments = [repr(key)] + [f"{name}={_field_expression(name, value)}" for name, value in fields.items()]
    return f"@corex.{kind}({', '.join(arguments)})"


def _update_fields(
    document: SourceDocument, decorator: ast.Call, fields: Mapping[str, Any], remove_fields: tuple[str, ...],
) -> list[tuple[int, int, str]]:
    kind = engine.corex_decorator_name(decorator)
    allowed = PYTHON_SCRIPT_DECORATOR_FIELDS[kind]
    if set(fields) & set(remove_fields):
        raise PythonScriptDeclarationError("A field cannot be set and omitted in the same edit")
    if (set(fields) | set(remove_fields)) - allowed:
        raise PythonScriptDeclarationError(f"Unsupported fields for {kind}")
    existing = {node.arg: node for node in decorator.keywords}
    edits: list[tuple[int, int, str]] = []
    for name, value in fields.items():
        if name in existing:
            node = existing[name].value
            edits.append((document.start(node), document.end(node), _field_expression(name, value)))
    preceding: ast.AST = decorator.args[0]
    for node in decorator.keywords:
        if node.arg in remove_fields:
            comma = document.comma_between(document.end(preceding), document.start(node))
            if comma is not None:
                edits.append((comma, comma + 1, ""))
            edits.append((document.start(node), document.end(node), ""))
        preceding = node
    added = [(name, value) for name, value in fields.items() if name not in existing]
    if added:
        surviving = [node for node in decorator.keywords if node.arg not in remove_fields]
        position = document.end(surviving[-1] if surviving else decorator.args[0])
        text = "".join(f", {name}={_field_expression(name, value)}" for name, value in added)
        edits.append((position, position, text))
    return edits


def _result(
    source: str, edits: list[tuple[int, int, str]], *, selected_key: str = "",
    renames: tuple[GuidedRename, ...] = (), synchronize: bool = True,
) -> SourceEditResult:
    result = apply_edits(source, edits)
    if synchronize:
        declaration = _parse(result, validate_signature=False)
        function = _function(result)
        document = SourceDocument(result)
        result = apply_edits(result, document.argument_edits(function, ("ctx", *declaration.parameter_keys)))
    _parse(result)
    # A whole-result replacement is unnecessary for source editing. UI consumers
    # use this list for the rename review and the source string for one undo unit.
    changes = tuple(SourceChange(
        start, end, value, source.count("\n", 0, start) + 1, source[start:end],
    ) for start, end, value in sorted(edits))
    return SourceEditResult(result, renames, changes, selected_key)


def edit_source(
    source: str, operation: str, *, key: str = "", kind: str = "",
    fields: Mapping[str, Any] | None = None, remove_fields: tuple[str, ...] = (),
    index: int | None = None, new_key: str = "",
) -> SourceEditResult:
    """Create one validated edit. Omit fields via remove_fields; None is a literal.

    Supported operations: add, update, duplicate, remove, move, rename,
    synchronize_parameters. Section assignment is update(fields={"section": ...}).
    Move index is a zero-based index into the full interface inventory.
    """
    _parse(source, validate_signature=False)
    function = _function(source)
    document = SourceDocument(source)
    decorators = _decorators(function)
    fields = {} if fields is None else fields
    edits: list[tuple[int, int, str]] = []
    if operation == "synchronize_parameters":
        desired = ("ctx", *_parse(source, validate_signature=False).parameter_keys)
        return _result(source, document.argument_edits(function, desired), synchronize=False)
    if operation == "add":
        from ea_node_editor.nodes.python_script_authoring_rename import used_python_names
        _validate_key(key)
        if key in decorators or kind != "output" and key in used_python_names(function):
            raise PythonScriptDeclarationError(f"The Python name {key!r} is already used")
        items = list(decorators.values())
        ordinal = len(items) if index is None else max(0, min(index, len(items)))
        position = document.decorator_span(items[ordinal])[0] if ordinal < len(items) else document.offsets[function.lineno - 1]
        edits.append((position, position, _new_decorator(kind, key, fields) + document.newline))
        return _result(source, edits, selected_key=key)
    if key not in decorators:
        raise PythonScriptDeclarationError(f"No declaration named {key!r}")
    decorator = decorators[key]
    if operation == "update":
        edits = _update_fields(document, decorator, fields, remove_fields)
    elif operation == "remove":
        first, last = document.decorator_span(decorator)
        edits.append((first, last, ""))
    elif operation == "duplicate":
        _validate_key(new_key)
        analysis = analyze_source(source)
        item = next(item for item in analysis.items if item.key == key)
        combined = {**item.fields, **fields}
        return edit_source(source, "add", key=new_key, kind=item.kind, fields=combined,
                           index=list(decorators).index(key) + 1 if index is None else index)
    elif operation == "move":
        if index is None or not 0 <= index < len(decorators):
            raise PythonScriptDeclarationError("Choose a valid interface position")
        keys = list(decorators)
        keys.remove(key)
        keys.insert(index, key)
        # Swap complete authored decorator lines, including their inline comments.
        spans = []
        for node in decorators.values():
            first, last = document.decorator_span(node)
            line_end = source.find("\n", last)
            spans.append((source.rfind("\n", 0, first) + 1,
                          len(source) if line_end < 0 else line_end + 1))
        blocks = {item_key: source[first:last] for item_key, (first, last) in zip(decorators, spans)}
        edits = [(first, last, blocks[item_key]) for (first, last), item_key in zip(spans, keys)]
    elif operation == "rename":
        from ea_node_editor.nodes.python_script_authoring_rename import rename_edits
        _validate_key(new_key)
        if new_key == key:
            return SourceEditResult(source, selected_key=key)
        if new_key in decorators:
            raise PythonScriptDeclarationError(f"A declaration named {new_key!r} already exists")
        kind = engine.corex_decorator_name(decorator)
        edits = rename_edits(source, document, function, decorator, key, new_key)
        return _result(source, edits, selected_key=new_key, renames=(GuidedRename(key, new_key, kind),))
    else:
        raise PythonScriptDeclarationError(f"Unknown authoring operation {operation!r}")
    return _result(source, edits, selected_key="" if operation == "remove" else key)


__all__ = [
    "AuthoringAnalysis", "AuthoringDiagnostic", "GuidedRename", "InterfaceItem", "SourceEditResult",
    "analyze_source", "edit_source", "type_expression",
]
