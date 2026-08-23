# Purpose: Parse decorator-defined Python Script node metadata without executing user code.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_python_script_declaration.py

from __future__ import annotations

import ast
import keyword
import math
import re
from collections import OrderedDict
from dataclasses import dataclass, replace
from functools import lru_cache
from types import SimpleNamespace
from typing import Any, Mapping

from ea_node_editor.nodes.builtins.core_values import (
    COLOR_DATA_TYPE_ID,
    IMAGE_DATA_TYPE_ID,
)
from ea_node_editor.nodes.node_specs import (
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
    SettingsGroupItemSpec,
    SettingsGroupSpec,
)
from ea_node_editor.runtime_contracts import (
    BOOLEAN_DATA_TYPE_ID,
    DOUBLE_DATA_TYPE_ID,
    GRAPH_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
    PATH_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
    Interval1D,
)

_MAX_SOURCE_BYTES = 256 * 1024
_MAX_AST_NODES = 20_000
_MAX_DECORATORS = 128
_MAX_LITERAL_ITEMS = 2_048
_MAX_LITERAL_DEPTH = 12
_BASE_PROPERTY_KEYS = frozenset({"script", "timeout_sec"})
_CONTROL_DECORATORS = frozenset(
    {
        "text",
        "number",
        "switch",
        "dropdown",
        "slider",
        "color",
        "path",
        "text_area",
        "interval",
        "list",
    }
)
_KNOWN_DECORATORS = _CONTROL_DECORATORS | {"node", "input", "output"}
_TYPE_ALIASES = {
    "Any": GRAPH_DATA_TYPE_ID,
    "Image": IMAGE_DATA_TYPE_ID,
    "Color": COLOR_DATA_TYPE_ID,
    "Interval": INTERVAL_1D_GRAPH_DATA_TYPE_ID,
}
_BUILTIN_TYPES = {
    "bool": BOOLEAN_DATA_TYPE_ID,
    "int": INTEGER_DATA_TYPE_ID,
    "float": DOUBLE_DATA_TYPE_ID,
    "str": STRING_DATA_TYPE_ID,
}


class PythonScriptDeclarationError(ValueError):
    """Actionable, source-located Python Script declaration error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.user_traceback = (
            'Traceback (most recent call last):\n  File "<script>"\n'
            f"PythonScriptDeclarationError: {message}"
        )


@dataclass(frozen=True, slots=True)
class _Declaration:
    ports: tuple[PortSpec, ...]
    properties: tuple[PropertySpec, ...]
    settings_groups: tuple[SettingsGroupSpec, ...]
    parameter_keys: tuple[str, ...]
    output_keys: tuple[str, ...]


def _fail(node: ast.AST | None, message: str) -> PythonScriptDeclarationError:
    if node is None:
        return PythonScriptDeclarationError(message)
    return PythonScriptDeclarationError(
        f"{message} (line {getattr(node, 'lineno', 1)}, "
        f"column {getattr(node, 'col_offset', 0) + 1})"
    )


def _decorator_name(node: ast.AST) -> str | None:
    target = node.func if isinstance(node, ast.Call) else node
    if (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "corex"
    ):
        return target.attr
    return None


def _bounded_literal(node: ast.AST, *, depth: int = 0) -> Any:
    if depth > _MAX_LITERAL_DEPTH:
        raise _fail(node, "Decorator literal nesting is too deep")
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (str, int, float, bool)) or node.value is None:
            if isinstance(node.value, str) and len(node.value) > 16_384:
                raise _fail(node, "Decorator string literal is too long")
            return node.value
        raise _fail(node, "Decorator arguments must use simple literals")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _bounded_literal(node.operand, depth=depth + 1)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _fail(node, "Unary decorator literals must be numeric")
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, (ast.Tuple, ast.List)):
        if len(node.elts) > _MAX_LITERAL_ITEMS:
            raise _fail(node, "Decorator literal contains too many items")
        values = tuple(_bounded_literal(item, depth=depth + 1) for item in node.elts)
        return values if isinstance(node, ast.Tuple) else list(values)
    if isinstance(node, ast.Dict):
        if len(node.keys) > _MAX_LITERAL_ITEMS or any(key is None for key in node.keys):
            raise _fail(
                node, "Decorator mapping literal is too large or uses unpacking"
            )
        result: dict[Any, Any] = {}
        for key_node, value_node in zip(node.keys, node.values, strict=True):
            assert key_node is not None
            key = _bounded_literal(key_node, depth=depth + 1)
            if not isinstance(key, (str, int, float, bool)) or key in result:
                raise _fail(
                    key_node, "Decorator mapping keys must be unique scalar literals"
                )
            result[key] = _bounded_literal(value_node, depth=depth + 1)
        return result
    raise _fail(node, "Decorator arguments must be literals")


def _type_id(node: ast.AST) -> str:
    if isinstance(node, ast.Name) and node.id in _BUILTIN_TYPES:
        return _BUILTIN_TYPES[node.id]
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "corex"
        and node.attr in _TYPE_ALIASES
    ):
        return _TYPE_ALIASES[node.attr]
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.strip()
    ):
        return node.value.strip()
    raise _fail(
        node,
        "value_type must be bool, int, float, str, a supported corex alias, or a type-ID string",
    )


def _call_values(
    decorator: ast.AST,
    name: str,
    *,
    allowed: set[str],
) -> tuple[str, dict[str, Any], dict[str, ast.AST]]:
    if not isinstance(decorator, ast.Call):
        raise _fail(decorator, f"@corex.{name} requires parentheses")
    if len(decorator.args) != 1:
        raise _fail(decorator, f"@corex.{name} requires one positional name")
    key = _bounded_literal(decorator.args[0])
    if not isinstance(key, str) or not key.isidentifier() or keyword.iskeyword(key):
        raise _fail(
            decorator.args[0], "Decorator name must be a valid Python identifier"
        )
    if key in {"ctx", "corex", "__builtins__"}:
        raise _fail(decorator.args[0], f"Decorator name {key!r} is reserved")
    values: dict[str, Any] = {}
    nodes: dict[str, ast.AST] = {}
    for keyword_node in decorator.keywords:
        if keyword_node.arg is None:
            raise _fail(
                keyword_node.value, "Decorator keyword unpacking is not allowed"
            )
        if keyword_node.arg not in allowed:
            raise _fail(
                keyword_node.value,
                f"@corex.{name} does not accept {keyword_node.arg!r}",
            )
        if keyword_node.arg in values:
            raise _fail(
                keyword_node.value, f"Duplicate decorator argument {keyword_node.arg!r}"
            )
        nodes[keyword_node.arg] = keyword_node.value
        values[keyword_node.arg] = (
            _type_id(keyword_node.value)
            if keyword_node.arg in {"value_type", "item_type"}
            else _bounded_literal(keyword_node.value)
        )
        if keyword_node.arg in {
            "label",
            "description",
            "section",
            "structure",
            "file_filter",
            "direction",
        } and not isinstance(values[keyword_node.arg], str):
            raise _fail(
                keyword_node.value, f"{keyword_node.arg} must be a string literal"
            )
        if keyword_node.arg in {"required", "port", "searchable"} and not isinstance(
            values[keyword_node.arg], bool
        ):
            raise _fail(keyword_node.value, f"{keyword_node.arg} must be true or false")
    return key, values, nodes


def _string(values: Mapping[str, Any], key: str, default: str = "") -> str:
    value = values.get(key, default)
    if not isinstance(value, str):
        raise PythonScriptDeclarationError(f"{key} must be a string literal")
    normalized = value.strip()
    if not normalized and default:
        return default
    return normalized


def _bool(values: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = values.get(key, default)
    if not isinstance(value, bool):
        raise PythonScriptDeclarationError(f"{key} must be true or false")
    return value


def _label(key: str, values: Mapping[str, Any]) -> str:
    return _string(values, "label") or key.replace("_", " ").strip().title()


def _port(
    key: str,
    *,
    direction: str,
    data_type: str,
    label: str,
    description: str,
    required: bool | None = None,
    data_access: str = "item",
    uses_property_default: bool = False,
    accepted_data_types: tuple[str, ...] = (),
) -> PortSpec:
    return PortSpec(
        key,
        direction,  # type: ignore[arg-type]
        "data",
        data_type,
        label=label,
        description=description,
        required=required,
        data_access=data_access,  # type: ignore[arg-type]
        uses_property_default=uses_property_default,
        accepted_data_types=accepted_data_types,
    )


def _numeric_type(value: Any, *, field: str = "default") -> tuple[str, str]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PythonScriptDeclarationError(f"{field} must be an int or float literal")
    if not math.isfinite(float(value)):
        raise PythonScriptDeclarationError(f"{field} must be finite")
    return (
        ("int", INTEGER_DATA_TYPE_ID)
        if isinstance(value, int)
        else ("float", DOUBLE_DATA_TYPE_ID)
    )


def _numeric_metadata(values: Mapping[str, Any], *keys: str) -> None:
    for key in keys:
        value = values.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PythonScriptDeclarationError(f"{key} must be a number literal")
        if not math.isfinite(float(value)):
            raise PythonScriptDeclarationError(f"{key} must be finite")


def _control_spec(
    decorator_name: str,
    key: str,
    values: Mapping[str, Any],
) -> tuple[PropertySpec, str, tuple[str, ...], str]:
    label = _label(key, values)
    description = _string(values, "description")
    section = _string(values, "section")
    accepted: tuple[str, ...] = ()

    if decorator_name in {"text", "text_area", "color", "path"}:
        default = values.get("default", "")
        if not isinstance(default, str):
            raise PythonScriptDeclarationError("default must be a string literal")
        property_type = "path" if decorator_name == "path" else "str"
        editor = {
            "text": "text",
            "text_area": "textarea",
            "color": "color",
            "path": "path",
        }[decorator_name]
        data_type = {
            "color": COLOR_DATA_TYPE_ID,
            "path": PATH_DATA_TYPE_ID,
        }.get(decorator_name, STRING_DATA_TYPE_ID)
        if decorator_name in {"color", "path"}:
            accepted = (STRING_DATA_TYPE_ID,)
        prop = PropertySpec(
            key,
            property_type,  # type: ignore[arg-type]
            default,
            label,
            inline_editor=editor,  # type: ignore[arg-type]
            file_filter=_string(values, "file_filter"),
            description=description,
            group=section,
        )
        return prop, data_type, accepted, "item"

    if decorator_name == "switch":
        default = values.get("default", False)
        if not isinstance(default, bool):
            raise PythonScriptDeclarationError("default must be true or false")
        return (
            PropertySpec(
                key,
                "bool",
                default,
                label,
                inline_editor="toggle",
                description=description,
                group=section,
            ),
            BOOLEAN_DATA_TYPE_ID,
            (),
            "item",
        )

    if decorator_name in {"number", "slider"}:
        default = values.get("default", 0.0)
        property_type, data_type = _numeric_type(default)
        _numeric_metadata(values, "minimum", "maximum", "step")
        minimum = values.get("minimum")
        maximum = values.get("maximum")
        step = values.get("step", 0.0)
        if decorator_name == "slider" and (minimum is None or maximum is None):
            raise PythonScriptDeclarationError("slider requires minimum and maximum")
        if minimum is not None and float(default) < float(minimum):
            raise PythonScriptDeclarationError("default must be at least minimum")
        if maximum is not None and float(default) > float(maximum):
            raise PythonScriptDeclarationError("default must be at most maximum")
        prop = PropertySpec(
            key,
            property_type,  # type: ignore[arg-type]
            default,
            label,
            minimum=minimum,
            maximum=maximum,
            step=step,
            inline_editor="slider" if decorator_name == "slider" else "number",
            description=description,
            group=section,
        )
        return prop, data_type, (), "item"

    if decorator_name == "dropdown":
        options = values.get("options")
        if (
            not isinstance(options, (list, tuple))
            or not options
            or not all(isinstance(item, str) and item for item in options)
        ):
            raise PythonScriptDeclarationError(
                "dropdown options must be non-empty strings"
            )
        enum_values = tuple(options)
        if len(set(enum_values)) != len(enum_values):
            raise PythonScriptDeclarationError("dropdown options must be unique")
        codes_value = values.get("codes")
        searchable = _bool(values, "searchable")
        if codes_value is None:
            default = values.get("default", enum_values[0])
            if default not in enum_values:
                raise PythonScriptDeclarationError(
                    "dropdown default must be one of options"
                )
            prop = PropertySpec(
                key,
                "enum",
                default,
                label,
                enum_values=enum_values,
                inline_editor="enum",
                searchable=searchable,
                description=description,
                group=section,
            )
            return prop, STRING_DATA_TYPE_ID, (), "item"
        if not isinstance(codes_value, (list, tuple)) or len(codes_value) != len(
            enum_values
        ):
            raise PythonScriptDeclarationError("dropdown codes must match options")
        if searchable:
            raise PythonScriptDeclarationError(
                "searchable dropdowns cannot use integer-backed codes"
            )
        codes = tuple(codes_value)
        if len(set(codes)) != len(codes):
            raise PythonScriptDeclarationError("dropdown codes must be unique")
        if any(isinstance(code, bool) or not isinstance(code, int) for code in codes):
            raise PythonScriptDeclarationError(
                "dropdown codes must be integer literals"
            )
        default = values.get("default", codes[0])
        if default not in codes:
            raise PythonScriptDeclarationError("dropdown default must be one of codes")
        property_type, data_type = "int", INTEGER_DATA_TYPE_ID
        prop = PropertySpec(
            key,
            property_type,  # type: ignore[arg-type]
            default,
            label,
            enum_values=enum_values,
            enum_codes=codes,
            inline_editor="enum",
            searchable=searchable,
            description=description,
            group=section,
        )
        return prop, data_type, (), "item"

    if decorator_name == "interval":
        default = values.get("default")
        nullable = default is None
        if default is not None:
            if (
                not isinstance(default, (list, tuple))
                or len(default) != 2
                or any(
                    isinstance(item, bool) or not isinstance(item, (int, float))
                    for item in default
                )
            ):
                raise PythonScriptDeclarationError(
                    "interval default must be None or two numbers"
                )
            default = Interval1D(float(default[0]), float(default[1]))
        minimum = values.get("minimum")
        maximum = values.get("maximum")
        _numeric_metadata(values, "minimum", "maximum", "step")
        slider = minimum is not None or maximum is not None
        if not slider and "direction" in values:
            raise PythonScriptDeclarationError(
                "interval direction requires minimum and maximum"
            )
        if slider and (minimum is None or maximum is None or default is None):
            raise PythonScriptDeclarationError(
                "interval sliders require minimum, maximum, and a non-null default"
            )
        direction = _string(values, "direction", "increasing") if slider else ""
        prop = PropertySpec(
            key,
            "interval_1d",
            default,
            label,
            minimum=minimum,
            maximum=maximum,
            step=values.get("step", 0.0),
            inline_editor="interval_slider" if slider else "interval_fields",
            interval_direction=direction,  # type: ignore[arg-type]
            nullable=nullable,
            persistence_data_type_id=INTERVAL_1D_GRAPH_DATA_TYPE_ID,
            description=description,
            group=section,
        )
        return prop, INTERVAL_1D_GRAPH_DATA_TYPE_ID, (), "item"

    if decorator_name == "list":
        default = values.get("default", [])
        if not isinstance(default, list):
            raise PythonScriptDeclarationError("list default must be a list literal")
        options = values.get("options")
        codes = values.get("codes")
        if codes is not None and options is None:
            raise PythonScriptDeclarationError("list codes require options")
        item_type_id = values.get("item_type", STRING_DATA_TYPE_ID)
        item_type = {
            STRING_DATA_TYPE_ID: "str",
            INTEGER_DATA_TYPE_ID: "int",
            DOUBLE_DATA_TYPE_ID: "float",
            COLOR_DATA_TYPE_ID: "color",
        }.get(item_type_id)
        enum_values: tuple[str, ...] = ()
        enum_codes: tuple[Any, ...] = ()
        if options is not None:
            if (
                not isinstance(options, (list, tuple))
                or not options
                or not all(isinstance(item, str) and item for item in options)
            ):
                raise PythonScriptDeclarationError(
                    "list options must be non-empty strings"
                )
            enum_values = tuple(options)
            if len(set(enum_values)) != len(enum_values):
                raise PythonScriptDeclarationError("list options must be unique")
            enum_codes = tuple(options if codes is None else codes)
            if len(enum_codes) != len(enum_values):
                raise PythonScriptDeclarationError("list codes must match options")
            if len(set(enum_codes)) != len(enum_codes):
                raise PythonScriptDeclarationError("list codes must be unique")
            item_type = "enum"
            if not enum_codes:
                raise PythonScriptDeclarationError("list enum codes cannot be empty")
            sample = enum_codes[0]
            if codes is not None and any(
                isinstance(code, bool) or not isinstance(code, int)
                for code in enum_codes
            ):
                raise PythonScriptDeclarationError(
                    "list codes must be integer literals"
                )
            item_type_id = (
                INTEGER_DATA_TYPE_ID
                if isinstance(sample, int)
                else DOUBLE_DATA_TYPE_ID
                if isinstance(sample, float)
                else STRING_DATA_TYPE_ID
            )
        if item_type is None:
            raise PythonScriptDeclarationError(
                "list item_type must be str, int, float, or corex.Color"
            )
        _numeric_metadata(values, "minimum", "maximum", "step")
        if item_type == "enum":
            if any(item not in enum_codes for item in default):
                raise PythonScriptDeclarationError(
                    "list default contains an invalid code"
                )
        else:
            expected_type = {
                "str": str,
                "color": str,
                "int": int,
                "float": (int, float),
            }[item_type]
            if any(
                isinstance(item, bool) or not isinstance(item, expected_type)
                for item in default
            ):
                raise PythonScriptDeclarationError(
                    f"list default items must match {item_type}"
                )
        prop = PropertySpec(
            key,
            "json",
            default,
            label,
            inline_editor="list",
            list_item_type=item_type,  # type: ignore[arg-type]
            list_item_enum_values=enum_values,
            list_item_enum_codes=enum_codes,
            list_item_minimum=values.get("minimum"),
            list_item_maximum=values.get("maximum"),
            list_item_step=values.get("step", 0.0),
            description=description,
            group=section,
        )
        return (
            prop,
            str(item_type_id),
            (STRING_DATA_TYPE_ID,) if item_type_id == COLOR_DATA_TYPE_ID else (),
            "list",
        )

    raise PythonScriptDeclarationError(
        f"Unsupported control decorator: {decorator_name}"
    )


def _group_id(label: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "section"
    if not base[0].isalpha():
        base = f"section_{base}"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


@lru_cache(maxsize=128)
def _parse(source: str) -> _Declaration:
    if len(source.encode("utf-8")) > _MAX_SOURCE_BYTES:
        raise PythonScriptDeclarationError("Python Script source is too large")
    try:
        module = ast.parse(source, filename="<script>", mode="exec")
    except SyntaxError as exc:
        raise PythonScriptDeclarationError(
            f"{exc.msg} (line {exc.lineno or 1}, column {exc.offset or 1})"
        ) from exc
    if sum(1 for _ in ast.walk(module)) > _MAX_AST_NODES:
        raise PythonScriptDeclarationError("Python Script syntax tree is too large")

    entrypoints: list[ast.FunctionDef] = []
    for statement in module.body:
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        corex_decorators = [
            decorator
            for decorator in statement.decorator_list
            if _decorator_name(decorator) is not None
        ]
        unknown = [
            decorator
            for decorator in corex_decorators
            if _decorator_name(decorator) not in _KNOWN_DECORATORS
        ]
        if unknown:
            raise _fail(
                unknown[0], f"Unknown corex decorator @{_decorator_name(unknown[0])}"
            )
        if any(_decorator_name(decorator) == "node" for decorator in corex_decorators):
            if isinstance(statement, ast.AsyncFunctionDef):
                raise _fail(statement, "@corex.node run must be synchronous")
            entrypoints.append(statement)
    if len(entrypoints) != 1:
        raise _fail(
            entrypoints[1] if len(entrypoints) > 1 else module,
            "Python Script requires exactly one synchronous @corex.node function",
        )
    function = entrypoints[0]
    if function.name != "run":
        raise _fail(function, "@corex.node entrypoint must be named run")
    if len(function.decorator_list) > _MAX_DECORATORS:
        raise _fail(function, "Python Script declares too many decorators")

    ports: list[PortSpec] = []
    properties: list[PropertySpec] = []
    parameter_keys: list[str] = []
    output_keys: list[str] = []
    used_keys: set[str] = set()
    section_items: "OrderedDict[str, list[SettingsGroupItemSpec]]" = OrderedDict()

    common = {"default", "label", "description", "section", "port"}
    control_allowed = {
        "text": common,
        "text_area": common,
        "color": common,
        "path": common | {"file_filter"},
        "number": common | {"minimum", "maximum", "step"},
        "switch": common,
        "dropdown": common | {"options", "codes", "searchable"},
        "slider": common | {"minimum", "maximum", "step"},
        "interval": common | {"minimum", "maximum", "step", "direction"},
        "list": common
        | {"item_type", "options", "codes", "minimum", "maximum", "step"},
    }

    for decorator in function.decorator_list:
        name = _decorator_name(decorator)
        if name is None:
            raise _fail(decorator, "run decorators must use the corex namespace")
        if name == "node":
            if isinstance(decorator, ast.Call) and (
                decorator.args or decorator.keywords
            ):
                raise _fail(decorator, "@corex.node does not accept arguments")
            continue
        if name == "input":
            key, values, _nodes = _call_values(
                decorator,
                name,
                allowed={
                    "value_type",
                    "structure",
                    "required",
                    "label",
                    "description",
                    "section",
                },
            )
            data_type = values.get("value_type", GRAPH_DATA_TYPE_ID)
            structure = _string(values, "structure", "item")
            if structure not in {"item", "list", "tree"}:
                raise _fail(decorator, "structure must be 'item', 'list', or 'tree'")
            required = _bool(values, "required")
            label = _label(key, values)
            description = _string(values, "description")
            port = _port(
                key,
                direction="in",
                data_type=data_type,
                label=label,
                description=description,
                required=required,
                data_access=structure,
            )
            prop = None
            section = _string(values, "section")
        elif name == "output":
            key, values, _nodes = _call_values(
                decorator,
                name,
                allowed={"value_type", "structure", "label", "description", "section"},
            )
            if "section" in values:
                raise _fail(decorator, "@corex.output does not support section")
            data_type = values.get("value_type", GRAPH_DATA_TYPE_ID)
            structure = _string(values, "structure", "item")
            if structure not in {"item", "list", "tree"}:
                raise _fail(decorator, "structure must be 'item', 'list', or 'tree'")
            port = _port(
                key,
                direction="out",
                data_type=data_type,
                label=_label(key, values),
                description=_string(values, "description"),
                data_access=structure,
            )
            prop = None
            section = ""
        elif name in _CONTROL_DECORATORS:
            key, values, _nodes = _call_values(
                decorator,
                name,
                allowed=control_allowed[name],
            )
            try:
                prop, data_type, accepted, data_access = _control_spec(
                    name, key, values
                )
            except OverflowError as exc:
                raise _fail(
                    decorator,
                    "Decorator numeric literal is outside the supported range",
                ) from exc
            except PythonScriptDeclarationError as exc:
                if "(line " in str(exc):
                    raise
                raise _fail(decorator, str(exc)) from exc
            section = _string(values, "section")
            port = (
                _port(
                    key,
                    direction="in",
                    data_type=data_type,
                    label=prop.label,
                    description=prop.description,
                    required=False,
                    data_access=data_access,
                    uses_property_default=True,
                    accepted_data_types=accepted,
                )
                if _bool(values, "port")
                else None
            )
        else:
            raise _fail(decorator, f"Unsupported decorator @corex.{name}")

        if key in _BASE_PROPERTY_KEYS:
            raise _fail(decorator, f"Python Script key {key!r} is reserved")
        if key in used_keys:
            raise _fail(decorator, f"Duplicate Python Script key {key!r}")
        used_keys.add(key)
        if port is not None:
            ports.append(port)
        if prop is not None:
            properties.append(prop)
        if name == "output":
            output_keys.append(key)
        else:
            parameter_keys.append(key)
        if section:
            section_items.setdefault(section, []).append(
                SettingsGroupItemSpec(
                    port_key=key if port is not None else "",
                    property_key=key if prop is not None else "",
                )
            )

    args = function.args
    if (
        args.posonlyargs
        or args.kwonlyargs
        or args.vararg
        or args.kwarg
        or args.defaults
        or args.kw_defaults
    ):
        raise _fail(
            function,
            "run must use plain required parameters without *args, **kwargs, or defaults",
        )
    signature_keys = tuple(argument.arg for argument in args.args)
    if not signature_keys or signature_keys[0] != "ctx":
        raise _fail(function, "run's first parameter must be ctx")
    if len(signature_keys) != len(set(signature_keys)):
        raise _fail(function, "run parameters must be unique")
    if set(signature_keys[1:]) != set(parameter_keys) or len(signature_keys[1:]) != len(
        parameter_keys
    ):
        raise _fail(
            function,
            "run parameters after ctx must exactly match declared inputs and controls",
        )

    used_group_ids: set[str] = set()
    settings_groups = tuple(
        SettingsGroupSpec(
            _group_id(label, used_group_ids),
            label,
            tuple(items),
        )
        for label, items in section_items.items()
    )
    return _Declaration(
        ports=tuple(ports),
        properties=tuple(properties),
        settings_groups=settings_groups,
        parameter_keys=tuple(parameter_keys),
        output_keys=tuple(output_keys),
    )


def resolve_python_script_spec(
    base_spec: NodeTypeSpec,
    properties: Mapping[str, object],
) -> NodeTypeSpec:
    declaration = _parse(str(properties.get("script", "")))
    base_properties = tuple(
        prop for prop in base_spec.properties if prop.key in _BASE_PROPERTY_KEYS
    )
    return replace(
        base_spec,
        ports=declaration.ports,
        properties=base_properties + declaration.properties,
        settings_groups=declaration.settings_groups,
        dynamic_port_groups=(),
        instance_spec_resolver=None,
    )


def python_script_parameter_keys(spec: NodeTypeSpec) -> tuple[str, ...]:
    input_keys = [port.key for port in spec.ports if port.direction == "in"]
    input_keys.extend(
        prop.key
        for prop in spec.properties
        if prop.key not in _BASE_PROPERTY_KEYS and prop.key not in input_keys
    )
    return tuple(input_keys)


def python_script_output_keys(spec: NodeTypeSpec) -> tuple[str, ...]:
    return tuple(port.key for port in spec.ports if port.direction == "out")


def python_script_runtime_namespace() -> SimpleNamespace:
    def identity_decorator(*_args: Any, **_kwargs: Any):
        return lambda function: function

    def node(function=None):
        return identity_decorator() if function is None else function

    return SimpleNamespace(
        node=node,
        input=identity_decorator,
        output=identity_decorator,
        text=identity_decorator,
        number=identity_decorator,
        switch=identity_decorator,
        dropdown=identity_decorator,
        slider=identity_decorator,
        color=identity_decorator,
        path=identity_decorator,
        text_area=identity_decorator,
        interval=identity_decorator,
        list=identity_decorator,
        Any=GRAPH_DATA_TYPE_ID,
        Image=IMAGE_DATA_TYPE_ID,
        Color=COLOR_DATA_TYPE_ID,
        Interval=INTERVAL_1D_GRAPH_DATA_TYPE_ID,
    )


__all__ = [
    "PythonScriptDeclarationError",
    "python_script_output_keys",
    "python_script_parameter_keys",
    "python_script_runtime_namespace",
    "resolve_python_script_spec",
]
