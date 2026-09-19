# Purpose: Project Python Script form help and completion from the declaration contract and type catalog.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_python_script_authoring_completion.py

from __future__ import annotations

import io
import re
import tokenize
from typing import Any, Mapping

from ea_node_editor.nodes import declaration_engine as engine
from ea_node_editor.nodes.python_script_authoring import type_expression
from ea_node_editor.nodes.python_script_declaration import PYTHON_SCRIPT_DECORATOR_FIELDS
from ea_node_editor.runtime_contracts import DataTypeCatalog
from ea_node_editor.runtime_contracts.scientific_values import ARRAY_VALUE_TYPE_ID, TABLE_VALUE_TYPE_ID, SERIES_VALUE_TYPE_ID


_DECORATORS = {
    "input": ("Input", "Receive a connected value with an explicit type.", {}),
    "output": ("Output", "Expose a value returned under this output's key.", {}),
    "text": ("Text", "Enter a single line of text.", {"default": ""}),
    "text_area": ("Multiline text", "Enter notes or longer text.", {"default": ""}),
    "number": ("Number", "Enter an integer or decimal number.", {"default": 0.0}),
    "slider": ("Slider", "Adjust a number between two bounds.", {"default": 0.5, "minimum": 0.0, "maximum": 1.0, "step": 0.1}),
    "switch": ("Switch", "Turn a setting on or off.", {"default": False}),
    "dropdown": ("Dropdown", "Choose from named options.", {"options": ["First", "Second"], "default": "First"}),
    "color": ("Color", "Choose a color.", {"default": "#336699"}),
    "path": ("File path", "Choose a file path.", {"default": "", "file_filter": "All files (*)"}),
    "interval": ("Interval", "Enter lower and upper limits.", {"default": [0.0, 1.0]}),
    "list": ("List", "Edit a list of typed values.", {"default": [], "item_type": "str"}),
}

_FIELDS = {
    "label": ("Display label", "text", "Presentation only. Omit to derive it from the Python name; an empty label is allowed."),
    "description": ("Description", "textarea", "Shown as contextual help for this port or control."),
    "value_type": ("Data type", "type", "Choose the kind of value. An entire DataFrame or NumPy array normally travels as one value."),
    "item_type": ("Item type", "list_item_type", "List controls support text, integer, decimal, and color items."),
    "structure": ("Data access", "choice", "Single value passes one value; List and Tree describe the outer graph structure."),
    "default": ("Default for new values", "default", "Existing saved node values are retained when valid. This sets the default for new values."),
    "minimum": ("Minimum", "number", "Optional lower bound; required for a slider."),
    "maximum": ("Maximum", "number", "Optional upper bound; required for a slider."),
    "step": ("Step", "number", "Increment used when adjusting a number."),
    "required": ("Required connection", "boolean", "Wait for an input value before running."),
    "section": ("Section", "text", "Group related inputs and controls under a shared heading."),
    "port": ("Allow input connection", "boolean", "A connected value overrides this control's saved value."),
    "options": ("Options", "text_rows", "Add unique, non-empty display choices."),
    "codes": ("Integer codes", "integer_rows", "Optional unique integer values, one for each option."),
    "searchable": ("Search options", "boolean", "Enable text filtering. Unavailable with integer-backed dropdown codes."),
    "file_filter": ("File filter", "text", "For example: CSV files (*.csv);;All files (*)"),
    "direction": ("Interval direction", "choice", "Used by interval sliders with minimum and maximum bounds."),
    "affects_execution": ("Affects execution", "boolean", "Disable only for presentation settings. A presentation-only control cannot expose an input port."),
    "type_from_input": ("Follow input type", "input_key", "An Any output may follow an Any input with the same data access."),
}
_ADVANCED = {"affects_execution", "type_from_input", "codes", "searchable", "direction"}
_FIELD_ORDER = ("label", "value_type", "structure", "item_type", "default", "options", "minimum", "maximum", "step", "required", "section", "port", "description", "file_filter", "codes", "searchable", "direction", "type_from_input", "affects_execution")
_DEFAULT_EDITORS = {"text": "text", "text_area": "textarea", "number": "number", "slider": "number", "switch": "boolean", "dropdown": "choice", "color": "color", "path": "path", "interval": "interval", "list": "list"}
_ALIASES = {type_id: name for name, type_id in engine.BUILTIN_TYPES.items()}
_ALIASES.update({type_id: "corex." + name for name, type_id in engine.TYPE_ALIASES.items()})
_LIST_TYPES = {engine.BUILTIN_TYPES[name] for name in ("str", "int", "float")} | {engine.TYPE_ALIASES["Color"]}
_TYPE_HELP = {
    engine.BUILTIN_TYPES["int"]: ("3", "integer whole count"),
    engine.BUILTIN_TYPES["float"]: ("3.14", "decimal float double real number"),
    engine.BUILTIN_TYPES["str"]: ('"Example"', "text string label"),
    engine.BUILTIN_TYPES["bool"]: ("True", "boolean bool switch true false"),
    engine.TYPE_ALIASES["Any"]: ("Any connected value", "any generic unknown flexible"),
    engine.TYPE_ALIASES["Image"]: ("An image value", "image picture bitmap png"),
    engine.TYPE_ALIASES["Color"]: ('"#336699"', "color colour rgb hex"),
    engine.TYPE_ALIASES["Interval"]: ("A lower and upper bound", "range interval bounds"),
    ARRAY_VALUE_TYPE_ID: ("np.array([1.0, 2.0])", "numpy ndarray array matrix scientific"),
    TABLE_VALUE_TYPE_ID: ('pd.DataFrame({"value": [1.0, 2.0]})', "pandas dataframe table tabular scientific"),
    SERIES_VALUE_TYPE_ID: ("pd.Series([1.0, 2.0])", "pandas series scientific column"),
}
_COMMON = [engine.BUILTIN_TYPES[name] for name in ("float", "int", "str", "bool")] + [
    TABLE_VALUE_TYPE_ID, ARRAY_VALUE_TYPE_ID, engine.TYPE_ALIASES["Image"], engine.TYPE_ALIASES["Any"],
]


def field_choices(kind: str, values: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Native form descriptors; values are ordinary strings/numbers/lists, not Python code."""
    values = {} if values is None else values
    result = []
    for name in _FIELD_ORDER:
        if name not in PYTHON_SCRIPT_DECORATOR_FIELDS.get(kind, ()):
            continue
        label, editor, help_text = _FIELDS[name]
        if name == "default":
            editor = _DEFAULT_EDITORS[kind]
        choices: list[dict[str, Any]] = []
        if name == "structure":
            choices = [{"label": label, "value": value} for label, value in (("Single value", "item"), ("List", "list"), ("Tree", "tree"))]
        elif name == "direction":
            choices = [{"label": value.title(), "value": value} for value in ("increasing", "decreasing")]
        elif name == "default" and kind == "dropdown":
            labels = values.get("options", ["First", "Second"])
            codes = values.get("codes", labels)
            choices = [{"label": label, "value": code} for label, code in zip(labels, codes)]
        result.append({"name": name, "label": label, "editor": editor, "help": help_text,
                       "advanced": name in _ADVANCED, "choices": choices,
                       "required": name == "value_type" or kind == "slider" and name in {"minimum", "maximum"},
                       "present": name in values, "value": values.get(name)})
    return result


def decorator_choices(query: str = "") -> list[dict[str, Any]]:
    result = []
    for kind, (label, description, initial) in _DECORATORS.items():
        if query.casefold() not in f"{kind} {label} {description}".casefold():
            continue
        fields = {name: list(value) if isinstance(value, list) else value for name, value in initial.items()}
        example_fields = {"value_type": "float"} if kind in {"input", "output"} else fields
        from ea_node_editor.nodes.python_script_authoring import _new_decorator
        result.append({"kind": kind, "label": label, "description": description,
                       "initial_fields": fields, "fields": field_choices(kind, fields),
                       "example": _new_decorator(kind, kind if kind not in {"list"} else "values", example_fields)})
    return result


def type_choices(
    catalog: DataTypeCatalog, query: str = "", *, list_items: bool = False,
    current_type: str = "",
) -> list[dict[str, Any]]:
    """Read the current catalog each time, including newly registered add-on types."""
    families = {record["family_id"]: record for record in catalog.snapshot() if record["kind"] == "family"}
    result: list[dict[str, Any]] = []
    for spec in catalog.all_specs():
        if list_items and spec.type_id not in _LIST_TYPES:
            continue
        family = families[spec.family_id]
        example, synonyms = _TYPE_HELP.get(spec.type_id, (f"A {spec.display_name} value", ""))
        expression = type_expression(spec.type_id)
        description = spec.description
        if spec.type_id == engine.TYPE_ALIASES["Any"]:
            description = "Accepts any connected value. Choose a specific type when your script requires one."
        if spec.type_id in {TABLE_VALUE_TYPE_ID, ARRAY_VALUE_TYPE_ID, SERIES_VALUE_TYPE_ID}:
            description += " Usually select Single value for the whole table, array, or series."
        search_text = " ".join((spec.type_id, spec.display_name, str(family["display_name"]), expression, description, synonyms))
        if not all(term in search_text.casefold() for term in query.casefold().split()):
            continue
        result.append({"type_id": spec.type_id, "label": spec.display_name, "expression": expression,
                       "description": description, "family": str(family["display_name"]), "family_id": spec.family_id,
                       "icon_key": str(family["icon_key"]), "color_token": str(family["color_token"]),
                       "example": example, "synonyms": synonyms, "common": spec.type_id in _COMMON,
                       "missing": False, "owner_id": catalog.owner_of(spec.type_id)})
    result.sort(key=lambda item: (0 if item["common"] else 1,
                                 _COMMON.index(item["type_id"]) if item["common"] else 0,
                                 item["family"].casefold(), item["label"].casefold()))
    if current_type and catalog.get(current_type) is None and not query:
        result.insert(0, {"type_id": current_type, "label": "Unavailable type", "expression": type_expression(current_type),
                          "description": "This type is not registered. Enable its add-on or choose an available type.",
                          "family": "Unavailable", "family_id": "", "icon_key": "", "color_token": "",
                          "example": "", "synonyms": "", "common": False, "missing": True, "owner_id": ""})
    return result


def _tokens(source: str) -> list[tokenize.TokenInfo]:
    result = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            result.append(token)
    except tokenize.TokenError as exc:
        if "multi-line string" in str(exc.args[0]) and len(exc.args) > 1:
            row, column = exc.args[1]
            lines = source.split("\n")
            start = sum(len(line) + 1 for line in lines[:row - 1]) + column
            result.append(tokenize.TokenInfo(tokenize.STRING, source[start:], (row, column),
                                             (len(lines), len(lines[-1])), lines[row - 1]))
    except (IndentationError, SyntaxError):
        pass
    return result


def _expression_end(source: str, start: int, cursor: int) -> int:
    value = source[start:cursor]
    if value.startswith(("'", '"')):
        if len(value) > 1 and value.endswith(value[0]):
            return cursor
        tail = source[cursor:]
        closing = tail.find(value[0])
        if closing >= 0 and not any(char in tail[:closing] for char in "\n,()"):
            return cursor + closing + 1
        return cursor
    return cursor + len(re.match(r"[\w.]*", source[cursor:])[0])


def completions(source: str, cursor: int, catalog: DataTypeCatalog) -> dict[str, Any]:
    """Context-aware suggestions for incomplete code. Offsets use Python characters."""
    empty = {"context": "", "start": cursor, "end": cursor, "items": [], "help": "",
             "catalog_fingerprint": catalog.fingerprint()}
    if not 0 <= cursor <= len(source) or len(source.encode("utf-8")) > engine.MAX_SOURCE_BYTES:
        return empty
    prefix = source[:cursor]
    parts = source.split("\n")
    lines = [part + "\n" for part in parts[:-1]] + [parts[-1]]
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    def offset(pos: tuple[int, int]) -> int:
        return offsets[min(pos[0] - 1, len(offsets) - 1)] + pos[1]
    tokens = _tokens(prefix)
    if any(token.type == tokenize.COMMENT and offset(token.start) <= cursor <= offset(token.end) for token in tokens):
        return empty
    direct = re.search(r"@corex\.([A-Za-z_]*)$", prefix)
    coverage = _tokens(source)
    def inside_string(position: int) -> bool:
        return any(token.type == tokenize.STRING and offset(token.start) <= position < offset(token.end) for token in coverage) or any(
            token.type == tokenize.ERRORTOKEN and token.string in {"'", '"'}
            and token.start[0] == prefix.count("\n") + 1 and offset(token.start) < position for token in tokens
        )
    if direct and not inside_string(direct.start()):
        query = direct[1]
        items = [{"label": "@corex." + item["kind"], "insert_text": item["kind"], "description": item["description"], "example": item["example"]}
                 for item in decorator_choices() if item["kind"].startswith(query)]
        if "node".startswith(query):
            items.insert(0, {"label": "@corex.node", "insert_text": "node", "description": "Declare the synchronous run entrypoint.", "example": "@corex.node"})
        end = cursor + len(re.match(r"[A-Za-z_]*", source[cursor:])[0])
        return {**empty, "context": "decorator", "start": direct.start(1), "end": end, "items": items}
    candidates = [candidate for candidate in re.finditer(r"@corex\.(\w+)\s*\(", prefix)
                  if not inside_string(candidate.start()) and not any(
                      token.type == tokenize.COMMENT and offset(token.start) <= candidate.start() < offset(token.end)
                      for token in tokens)]
    if not candidates:
        return empty
    match = candidates[-1]
    if match[1] not in PYTHON_SCRIPT_DECORATOR_FIELDS or inside_string(match.start()) or any(token.type == tokenize.COMMENT and offset(token.start) <= match.start() < offset(token.end) for token in tokens):
        return empty
    depth = 0
    argument_start = match.end()
    existing_fields: set[str] = set()
    for token_index, token in enumerate(tokens):
        if depth == 1 and token.type == tokenize.NAME and token_index + 1 < len(tokens) and tokens[token_index + 1].string == "=":
            existing_fields.add(token.string)
        if offset(token.start) < match.end() - 1 or token.type != tokenize.OP:
            continue
        if token.string in "([{":
            depth += 1
        elif token.string in ")]}":
            depth -= 1
            if depth == 0:
                return empty
        elif token.string == "," and depth == 1:
            argument_start = offset(token.end)
    if depth != 1:
        return empty
    argument = prefix[argument_start:]
    field = re.match(r"\s*(\w+)\s*=\s*(.*)$", argument, re.S)
    if field:
        name, value = field[1], field[2]
        start = argument_start + field.start(2)
        end = cursor
        if name in {"value_type", "item_type"}:
            if not re.fullmatch(r"['\"]?[\w.]*['\"]?", value):
                return empty
            query = value.strip("'\"")
            end = _expression_end(source, start, cursor)
            choices = type_choices(catalog, list_items=name == "item_type")
            items = [{**item, "insert_text": item["expression"]} for item in choices
                     if query.casefold() in " ".join(str(item[key]) for key in ("type_id", "label", "expression", "synonyms")).casefold()]
            return {**empty, "context": "type", "start": start, "end": end, "items": items, "help": _FIELDS[name][2]}
        if name in {"structure", "direction"}:
            choices = next((item["choices"] for item in field_choices(match[1]) if item["name"] == name), [])
            items = [{"label": item["label"], "insert_text": repr(item["value"]), "description": _FIELDS[name][2]}
                     for item in choices if value.strip("'\"").casefold() in str(item["value"]).casefold()]
            return {**empty, "context": "value", "start": start,
                    "end": _expression_end(source, start, cursor), "items": items, "help": _FIELDS[name][2]}
        return {**empty, "help": _FIELDS.get(name, ("", "", ""))[2]}
    # Keyword completion only after the key argument, never inside its string.
    if argument_start == match.end() or not re.fullmatch(r"\s*[A-Za-z_]*", argument):
        return empty
    query = argument.strip()
    items = [{"label": item["label"], "insert_text": item["name"] + "=", "description": item["help"]}
             for item in field_choices(match[1]) if item["name"].startswith(query) and item["name"] not in existing_fields]
    end = cursor + len(re.match(r"[A-Za-z_]*=?", source[cursor:])[0])
    return {**empty, "context": "keyword", "start": cursor - len(query), "end": end, "items": items}


__all__ = ["completions", "decorator_choices", "field_choices", "type_choices"]
