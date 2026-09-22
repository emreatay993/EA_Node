# Purpose: Declarative op specification (OpSpec), the stdlib JSON-schema-subset validator, and the Deferred result type.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py, tests/automation/test_protocol.py
"""Operation model shared by the catalog, bridge, client, MCP server, and docs.

``OpSpec`` is a frozen description of one automation operation. Param and
result shapes use a small JSON-Schema subset validated by
:func:`validate_params` without any third-party dependency (``jsonschema`` is
not a COREX dependency). Supported keywords:

``type`` (string | number | integer | boolean | object | array | null, or a
list of those), ``required``, ``properties``, ``additionalProperties`` (bool),
``enum``, ``minimum``, ``maximum``, ``minLength``, ``maxLength``, ``pattern``,
``items``, ``minItems``, ``maxItems``, ``default`` (applied by
:func:`apply_defaults`), ``description``, ``oneOf`` (first branch that
validates wins), ``anyOf`` (same), ``nullable`` (shorthand for ``type`` union
with null).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

Schema = Mapping[str, Any]

_TYPE_CHECKS: dict[str, Callable[[Any], bool]] = {
    "string": lambda value: isinstance(value, str),
    "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "boolean": lambda value: isinstance(value, bool),
    "object": lambda value: isinstance(value, Mapping),
    "array": lambda value: isinstance(value, (list, tuple)),
    "null": lambda value: value is None,
}


@dataclass(frozen=True, slots=True)
class OpSpec:
    """One automation operation.

    ``name`` is the wire op (``domain.verb``); ``mcp_tool`` is the MCP tool name
    (``None`` keeps the op protocol-only). ``ref_fields`` lists the param paths
    (dotted, ``[]`` for array items) in which ``graph.apply`` resolves ``$ref``
    tokens; nothing else is ever substituted so markdown ``$100`` stays safe.
    """

    name: str
    domain: str
    summary: str
    params: dict[str, Any]
    result: dict[str, Any]
    description: str = ""
    mutates_graph: bool = False
    apply_allowed: bool = False
    deferred: bool = False
    ref_fields: tuple[str, ...] = ()
    primary_id_field: str = ""
    mcp_tool: str | None = None
    examples: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "summary": self.summary,
            "description": self.description,
            "params": _copy_schema(self.params),
            "result": _copy_schema(self.result),
            "mutates_graph": bool(self.mutates_graph),
            "apply_allowed": bool(self.apply_allowed),
            "deferred": bool(self.deferred),
            "ref_fields": list(self.ref_fields),
            "primary_id_field": self.primary_id_field,
            "mcp_tool": self.mcp_tool,
            "examples": [dict(example) for example in self.examples],
        }


@dataclass(slots=True)
class Deferred:
    """A handler result that completes later.

    The bridge calls ``poll()`` on the GUI thread every ``poll_interval_s``
    while it is *not* busy with another op, until it returns a result dict or
    ``timeout_s`` elapses (then ``on_timeout()`` decides the error/result).
    """

    poll: Callable[[], dict[str, Any] | None]
    timeout_s: float
    on_timeout: Callable[[], dict[str, Any]] | None = None
    poll_interval_s: float = 0.05
    label: str = ""


def object_schema(
    properties: Mapping[str, Any] | None = None,
    *,
    required: Sequence[str] = (),
    additional: bool = False,
    description: str = "",
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {key: dict(value) for key, value in (properties or {}).items()},
        "additionalProperties": bool(additional),
    }
    if required:
        schema["required"] = list(required)
    if description:
        schema["description"] = description
    return schema


def string_schema(description: str = "", *, enum: Sequence[str] = (), min_length: int | None = None, pattern: str = "", default: Any = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string"}
    if description:
        schema["description"] = description
    if enum:
        schema["enum"] = list(enum)
    if min_length is not None:
        schema["minLength"] = int(min_length)
    if pattern:
        schema["pattern"] = pattern
    if default is not None:
        schema["default"] = default
    return schema


def number_schema(description: str = "", *, minimum: float | None = None, maximum: float | None = None, default: Any = None, integer: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "integer" if integer else "number"}
    if description:
        schema["description"] = description
    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    if default is not None:
        schema["default"] = default
    return schema


def boolean_schema(description: str = "", *, default: bool | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "boolean"}
    if description:
        schema["description"] = description
    if default is not None:
        schema["default"] = bool(default)
    return schema


def array_schema(items: Mapping[str, Any], description: str = "", *, min_items: int | None = None, max_items: int | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "array", "items": dict(items)}
    if description:
        schema["description"] = description
    if min_items is not None:
        schema["minItems"] = int(min_items)
    if max_items is not None:
        schema["maxItems"] = int(max_items)
    return schema


def any_schema(description: str = "") -> dict[str, Any]:
    schema: dict[str, Any] = {}
    if description:
        schema["description"] = description
    return schema


def id_list_schema(description: str, *, min_items: int = 1, max_items: int | None = None) -> dict[str, Any]:
    return array_schema(string_schema(min_length=1), description, min_items=min_items, max_items=max_items)


def validate_params(schema: Schema, value: Any, *, path: str = "params") -> list[str]:
    """Return a list of human-readable problems (empty when valid)."""
    problems: list[str] = []
    _validate(schema, value, path, problems)
    return problems


def apply_defaults(schema: Schema, value: Any) -> Any:
    """Return a copy of ``value`` with schema ``default`` values filled in."""
    if isinstance(value, Mapping) and _schema_type_allows(schema, "object"):
        result = dict(value)
        properties = schema.get("properties")
        if isinstance(properties, Mapping):
            for key, sub_schema in properties.items():
                if not isinstance(sub_schema, Mapping):
                    continue
                if key in result:
                    result[key] = apply_defaults(sub_schema, result[key])
                elif "default" in sub_schema:
                    result[key] = _copy_value(sub_schema["default"])
        return result
    if isinstance(value, (list, tuple)) and _schema_type_allows(schema, "array"):
        items = schema.get("items")
        if isinstance(items, Mapping):
            return [apply_defaults(items, item) for item in value]
        return list(value)
    return value


def _schema_type_allows(schema: Schema, type_name: str) -> bool:
    declared = schema.get("type")
    if declared is None:
        return True
    if isinstance(declared, str):
        return declared == type_name
    return type_name in list(declared)


def _declared_types(schema: Schema) -> list[str]:
    declared = schema.get("type")
    types: list[str]
    if declared is None:
        types = []
    elif isinstance(declared, str):
        types = [declared]
    else:
        types = [str(item) for item in declared]
    if schema.get("nullable") and "null" not in types:
        types.append("null")
    return types


def _validate(schema: Schema, value: Any, path: str, problems: list[str]) -> None:
    if not isinstance(schema, Mapping):
        return
    branches = schema.get("oneOf") or schema.get("anyOf")
    if isinstance(branches, Sequence) and branches:
        for branch in branches:
            if isinstance(branch, Mapping) and not validate_params(branch, value, path=path):
                break
        else:
            problems.append(f"{path}: value matches none of the allowed shapes")
            return
    types = _declared_types(schema)
    if types:
        if not any(_TYPE_CHECKS.get(name, lambda _value: True)(value) for name in types):
            problems.append(f"{path}: expected {' or '.join(types)}, got {_type_label(value)}")
            return
    if value is None:
        return
    enum = schema.get("enum")
    if isinstance(enum, Sequence) and not isinstance(enum, (str, bytes)):
        if value not in list(enum):
            problems.append(f"{path}: must be one of {list(enum)!r}")
            return
    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            problems.append(f"{path}: must be at least {min_length} characters")
        max_length = schema.get("maxLength")
        if isinstance(max_length, int) and len(value) > max_length:
            problems.append(f"{path}: must be at most {max_length} characters")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and pattern and re.search(pattern, value) is None:
            problems.append(f"{path}: does not match pattern {pattern!r}")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and value < minimum:
            problems.append(f"{path}: must be >= {minimum}")
        maximum = schema.get("maximum")
        if isinstance(maximum, (int, float)) and value > maximum:
            problems.append(f"{path}: must be <= {maximum}")
    elif isinstance(value, Mapping):
        properties = schema.get("properties")
        properties = properties if isinstance(properties, Mapping) else {}
        for key in schema.get("required", ()) or ():
            if key not in value:
                problems.append(f"{path}.{key}: is required")
        for key, item in value.items():
            sub_schema = properties.get(key)
            if isinstance(sub_schema, Mapping):
                _validate(sub_schema, item, f"{path}.{key}", problems)
            elif schema.get("additionalProperties", True) is False:
                problems.append(f"{path}.{key}: unexpected parameter")
    elif isinstance(value, (list, tuple)):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            problems.append(f"{path}: must contain at least {min_items} items")
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            problems.append(f"{path}: must contain at most {max_items} items")
        items = schema.get("items")
        if isinstance(items, Mapping):
            for index, item in enumerate(value):
                _validate(items, item, f"{path}[{index}]", problems)


def _type_label(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, (list, tuple)):
        return "array"
    return type(value).__name__


def _copy_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    return _copy_value(dict(schema))


def _copy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _copy_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_copy_value(item) for item in value]
    return value


__all__ = [
    "Deferred",
    "OpSpec",
    "Schema",
    "any_schema",
    "apply_defaults",
    "array_schema",
    "boolean_schema",
    "id_list_schema",
    "number_schema",
    "object_schema",
    "string_schema",
    "validate_params",
]
