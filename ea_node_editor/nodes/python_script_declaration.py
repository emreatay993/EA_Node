# Purpose: Parse decorator-defined Python Script node metadata without executing user code.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_python_script_declaration.py

from __future__ import annotations

import ast
from collections import OrderedDict
from dataclasses import dataclass, replace
from functools import lru_cache
from types import SimpleNamespace
from typing import Any, Mapping

from ea_node_editor.nodes import declaration_engine as _declaration_engine
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
    GRAPH_DATA_TYPE_ID,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
)

_BASE_PROPERTY_KEYS = frozenset({"script", "timeout_sec"})


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

@lru_cache(maxsize=128)
def _parse(source: str) -> _Declaration:
    if len(source.encode("utf-8")) > _declaration_engine.MAX_SOURCE_BYTES:
        raise PythonScriptDeclarationError("Python Script source is too large")
    try:
        module = ast.parse(source, filename="<script>", mode="exec")
    except SyntaxError as exc:
        raise PythonScriptDeclarationError(
            f"{exc.msg} (line {exc.lineno or 1}, column {exc.offset or 1})"
        ) from exc
    if sum(1 for _ in ast.walk(module)) > _declaration_engine.MAX_AST_NODES:
        raise PythonScriptDeclarationError("Python Script syntax tree is too large")

    entrypoints: list[ast.FunctionDef] = []
    for statement in module.body:
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        corex_decorators = [
            decorator
            for decorator in statement.decorator_list
            if _declaration_engine.corex_decorator_name(decorator) is not None
        ]
        unknown = [
            decorator
            for decorator in corex_decorators
            if _declaration_engine.corex_decorator_name(decorator)
            not in _declaration_engine.KNOWN_DECORATORS
        ]
        if unknown:
            raise _fail(
                unknown[0],
                "Unknown corex decorator "
                f"@{_declaration_engine.corex_decorator_name(unknown[0])}",
            )
        if any(
            _declaration_engine.corex_decorator_name(decorator) == "node"
            for decorator in corex_decorators
        ):
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
    if len(function.decorator_list) > _declaration_engine.MAX_DECORATORS:
        raise _fail(function, "Python Script declares too many decorators")

    ports: list[PortSpec] = []
    properties: list[PropertySpec] = []
    parameter_keys: list[str] = []
    output_keys: list[str] = []
    used_keys: set[str] = set()
    section_items: "OrderedDict[str, list[SettingsGroupItemSpec]]" = OrderedDict()

    for decorator in function.decorator_list:
        name = _declaration_engine.corex_decorator_name(decorator)
        if name is None:
            raise _fail(decorator, "run decorators must use the corex namespace")
        if name == "node":
            if isinstance(decorator, ast.Call) and (
                decorator.args or decorator.keywords
            ):
                raise _fail(decorator, "@corex.node does not accept arguments")
            continue
        if name == "input":
            key, values, _nodes = _declaration_engine.call_values(
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
                fail=_fail,
            )
            if "value_type" not in values:
                raise _fail(decorator, "@corex.input requires explicit value_type=")
            data_type = values["value_type"]
            structure = _declaration_engine.string_value(
                values, "structure", "item"
            )
            if structure not in {"item", "list", "tree"}:
                raise _fail(decorator, "structure must be 'item', 'list', or 'tree'")
            required = _declaration_engine.bool_value(values, "required")
            label = _declaration_engine.label_value(key, values)
            description = _declaration_engine.string_value(values, "description")
            port = _declaration_engine.port_spec(
                key,
                direction="in",
                data_type=data_type,
                label=label,
                description=description,
                required=required,
                data_access=structure,
            )
            prop = None
            section = _declaration_engine.string_value(values, "section")
        elif name == "output":
            key, values, _nodes = _declaration_engine.call_values(
                decorator,
                name,
                allowed={"value_type", "structure", "label", "description", "section"},
                fail=_fail,
            )
            if "section" in values:
                raise _fail(decorator, "@corex.output does not support section")
            if "value_type" not in values:
                raise _fail(decorator, "@corex.output requires explicit value_type=")
            data_type = values["value_type"]
            structure = _declaration_engine.string_value(
                values, "structure", "item"
            )
            if structure not in {"item", "list", "tree"}:
                raise _fail(decorator, "structure must be 'item', 'list', or 'tree'")
            port = _declaration_engine.port_spec(
                key,
                direction="out",
                data_type=data_type,
                label=_declaration_engine.label_value(key, values),
                description=_declaration_engine.string_value(values, "description"),
                data_access=structure,
            )
            prop = None
            section = ""
        elif name in _declaration_engine.CONTROL_DECORATORS:
            key, values, _nodes = _declaration_engine.call_values(
                decorator,
                name,
                allowed=_declaration_engine.CONTROL_ALLOWED_FIELDS[name],
                fail=_fail,
            )
            try:
                prop, data_type, accepted, data_access = (
                    _declaration_engine.control_spec(name, key, values)
                )
            except OverflowError as exc:
                raise _fail(
                    decorator,
                    "Decorator numeric literal is outside the supported range",
                ) from exc
            except _declaration_engine.DeclarationValueError as exc:
                if "(line " in str(exc):
                    raise
                raise _fail(decorator, str(exc)) from exc
            section = _declaration_engine.string_value(values, "section")
            port = (
                _declaration_engine.port_spec(
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
                if _declaration_engine.bool_value(values, "port")
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
            _declaration_engine.group_id(label, used_group_ids),
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
