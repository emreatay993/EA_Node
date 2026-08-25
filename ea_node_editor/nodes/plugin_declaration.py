# Purpose: Discover novice function-plugin declarations statically without importing source.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_plugin_declaration.py

from __future__ import annotations

import ast
import re
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping

from corex import _unknown_setting_message
from ea_node_editor.nodes import declaration_engine as _engine
from ea_node_editor.nodes.function_plugin import INTERNAL_BUILTIN_FUNCTION_OWNER_ID
from ea_node_editor.nodes.node_specs import (
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
    SettingsGroupItemSpec,
    SettingsGroupSpec,
)
from ea_node_editor.runtime_contracts import GRAPH_DATA_TYPE_ID

_CUSTOM_TYPE_ID = re.compile(
    r"^custom\.[a-z0-9]+(?:[._-][a-z0-9]+)*\.[0-9a-f]{8}$"
)
_NODE_FIELDS = frozenset(
    {"id", "name", "category", "description", "keywords", "icon"}
)
_REQUIRED_NODE_FIELDS = frozenset({"id", "name", "category"})
_RESERVED_DECLARATION_NAMES = frozenset(
    {"ctx", "settings", "to_dict", "corex", "__builtins__"}
)
_INTROSPECTION_CALLS = frozenset({"dir", "getattr", "hasattr", "vars"})


class PluginDeclarationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        filename: str,
        line: int = 1,
        column: int = 1,
    ) -> None:
        self.message = str(message)
        self.filename = str(filename)
        self.line = max(1, int(line))
        self.column = max(1, int(column))
        super().__init__(
            f"{self.filename}:{self.line}:{self.column}: {self.message}"
        )


@dataclass(frozen=True, slots=True)
class PythonFunctionDeclaration:
    spec: NodeTypeSpec
    function_name: str
    input_keys: tuple[str, ...]
    output_keys: tuple[str, ...]
    control_keys: tuple[str, ...]
    is_async: bool


def _failure(filename: str):
    def fail(node: ast.AST | None, message: str) -> PluginDeclarationError:
        return PluginDeclarationError(
            message,
            filename=filename,
            line=getattr(node, "lineno", 1),
            column=getattr(node, "col_offset", 0) + 1,
        )

    return fail


def _literal_assignments(module: ast.Module) -> dict[str, ast.AST]:
    assignments: dict[str, ast.AST] = {}
    for statement in module.body:
        if (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
        ):
            assignments[statement.targets[0].id] = statement.value
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.value is not None
        ):
            assignments[statement.target.id] = statement.value
    return assignments


def _corex_aliases(module: ast.Module) -> set[str]:
    aliases: set[str] = set()
    for statement in module.body:
        if isinstance(statement, ast.Import):
            aliases.update(
                item.asname
                for item in statement.names
                if item.name == "corex" and item.asname and item.asname != "corex"
            )
        elif isinstance(statement, ast.ImportFrom) and statement.module == "corex":
            aliases.update(item.asname or item.name for item in statement.names)
    return aliases


def _has_corex_import(module: ast.Module) -> bool:
    return any(
        isinstance(statement, ast.Import)
        and any(
            item.name == "corex" and item.asname in {None, "corex"}
            for item in statement.names
        )
        for statement in module.body
    )


def _decorator_root_name(decorator: ast.AST) -> str | None:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
        return target.value.id
    return None


class _ModuleBindingCounter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def _bind(self, name: str) -> None:
        self.counts[name] = self.counts.get(name, 0) + 1

    def _visit_function_header(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        self._bind(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_header(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_header(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._bind(node.name)
        for expression in (*node.decorator_list, *node.bases):
            self.visit(expression)
        for keyword_node in node.keywords:
            self.visit(keyword_node.value)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in (*node.args.defaults, *node.args.kw_defaults):
            if default is not None:
                self.visit(default)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self._bind(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for item in node.names:
            self._bind(item.asname or item.name.partition(".")[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for item in node.names:
            if item.name != "*":
                self._bind(item.asname or item.name)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self._bind(node.name)
        if node.type is not None:
            self.visit(node.type)
        for statement in node.body:
            self.visit(statement)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name:
            self._bind(node.name)
        if node.pattern is not None:
            self.visit(node.pattern)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name:
            self._bind(node.name)

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest:
            self._bind(node.rest)
        for key in node.keys:
            self.visit(key)
        for pattern in node.patterns:
            self.visit(pattern)


def _module_binding_counts(module: ast.Module) -> dict[str, int]:
    visitor = _ModuleBindingCounter()
    visitor.visit(module)
    return visitor.counts


def _node_metadata(
    decorator: ast.AST,
    *,
    fail,
    constants: Mapping[str, ast.AST],
    cache: dict[str, Any],
    allow_reserved_ids: bool,
) -> dict[str, Any]:
    if not isinstance(decorator, ast.Call):
        raise fail(decorator, "@corex.node requires parentheses and metadata")
    if decorator.args:
        raise fail(decorator.args[0], "@corex.node accepts keyword arguments only")
    values: dict[str, Any] = {}
    for keyword_node in decorator.keywords:
        if keyword_node.arg is None:
            raise fail(keyword_node.value, "@corex.node keyword unpacking is not allowed")
        if keyword_node.arg not in _NODE_FIELDS:
            raise fail(
                keyword_node.value,
                f"@corex.node does not accept {keyword_node.arg!r}",
            )
        if keyword_node.arg in values:
            raise fail(
                keyword_node.value,
                f"Duplicate @corex.node argument {keyword_node.arg!r}",
            )
        values[keyword_node.arg] = _engine.bounded_literal(
            keyword_node.value,
            fail=fail,
            constants=constants,
            cache=cache,
        )
    missing = sorted(_REQUIRED_NODE_FIELDS - values.keys())
    if missing:
        raise fail(decorator, "@corex.node is missing: " + ", ".join(missing))

    type_id = values["id"]
    if not isinstance(type_id, str) or type_id != type_id.strip():
        raise fail(decorator, "@corex.node id must be a trimmed string literal")
    if not allow_reserved_ids and _CUSTOM_TYPE_ID.fullmatch(type_id) is None:
        raise fail(
            decorator,
            "External node ids must match custom.<readable-slug>.<8-lowercase-hex>",
        )
    if allow_reserved_ids and not type_id:
        raise fail(decorator, "@corex.node id must not be empty")

    display_name = values["name"]
    if (
        not isinstance(display_name, str)
        or not display_name
        or display_name != display_name.strip()
    ):
        raise fail(decorator, "@corex.node name must be a non-empty trimmed string")
    category = values["category"]
    if (
        not isinstance(category, (list, tuple))
        or not category
        or not all(
            isinstance(item, str) and item and item == item.strip()
            for item in category
        )
    ):
        raise fail(
            decorator,
            "@corex.node category must contain non-empty trimmed strings",
        )
    description = values.get("description", "")
    icon = values.get("icon", "")
    if not isinstance(description, str) or not isinstance(icon, str):
        raise fail(decorator, "@corex.node description and icon must be strings")
    keywords = values.get("keywords", ())
    if (
        not isinstance(keywords, (list, tuple))
        or not all(
            isinstance(item, str) and item and item == item.strip()
            for item in keywords
        )
        or len(set(keywords)) != len(keywords)
    ):
        raise fail(decorator, "@corex.node keywords must be unique non-empty strings")
    return {
        "type_id": type_id,
        "display_name": display_name,
        "category_path": tuple(category),
        "description": description,
        "keywords": tuple(keywords),
        "icon": icon,
    }


def _validate_settings_body(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    control_names: tuple[str, ...],
    *,
    fail,
) -> None:
    allowed = frozenset(control_names)
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _INTROSPECTION_CALLS
            and any(isinstance(arg, ast.Name) and arg.id == "settings" for arg in node.args)
        ):
            raise fail(node, "Dynamic Settings introspection is unsupported")
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id == "settings":
                raise fail(node, "Settings supports attributes and to_dict() only")
        if isinstance(node, ast.Name) and node.id == "settings" and isinstance(
            node.ctx, ast.Store
        ):
            raise fail(node, "settings is immutable and cannot be rebound")
        if (
            not control_names
            and isinstance(node, ast.Name)
            and node.id == "settings"
            and isinstance(node.ctx, ast.Load)
        ):
            raise fail(node, "settings is available only when controls are declared")
        if not (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "settings"
        ):
            continue
        if not isinstance(node.ctx, ast.Load):
            raise fail(node, "Settings values are immutable")
        if node.attr.startswith("_"):
            raise fail(node, "Private Settings members are unsupported")
        if node.attr == "to_dict":
            continue
        if node.attr not in allowed:
            raise fail(node, _unknown_setting_message(node.attr, allowed))


def _parse_function(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    filename: str,
    constants: Mapping[str, ast.AST],
    cache: dict[str, Any],
    allow_reserved_ids: bool,
) -> PythonFunctionDeclaration:
    fail = _failure(filename)
    decorators = function.decorator_list
    if len(decorators) > _engine.MAX_DECORATORS:
        raise fail(function, "Node function declares too many decorators")
    names = tuple(_engine.corex_decorator_name(item) for item in decorators)
    if not names or names[0] != "node":
        raise fail(function, "Exactly one @corex.node must be the first decorator")
    if names.count("node") != 1:
        raise fail(function, "Node function must declare exactly one @corex.node")
    for decorator, name in zip(decorators, names, strict=True):
        if name is None:
            raise fail(decorator, "Node decorators must use the corex namespace")
        if name not in _engine.KNOWN_DECORATORS:
            raise fail(decorator, f"Unknown corex decorator @corex.{name}")

    metadata = _node_metadata(
        decorators[0],
        fail=fail,
        constants=constants,
        cache=cache,
        allow_reserved_ids=allow_reserved_ids,
    )
    ports: list[PortSpec] = []
    properties: list[PropertySpec] = []
    input_keys: list[str] = []
    output_keys: list[str] = []
    control_keys: list[str] = []
    used_keys: set[str] = set()
    section_items: OrderedDict[str, list[SettingsGroupItemSpec]] = OrderedDict()

    for decorator, name in zip(decorators[1:], names[1:], strict=True):
        assert name is not None
        if name == "input":
            key, values, _nodes = _engine.call_values(
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
                fail=fail,
                constants=constants,
                cache=cache,
                reserved=_RESERVED_DECLARATION_NAMES,
                reject_private=True,
            )
            structure = _engine.string_value(values, "structure", "item")
            if structure not in {"item", "list", "tree"}:
                raise fail(decorator, "structure must be 'item', 'list', or 'tree'")
            port = _engine.port_spec(
                key,
                direction="in",
                data_type=values.get("value_type", GRAPH_DATA_TYPE_ID),
                label=_engine.label_value(key, values),
                description=_engine.string_value(values, "description"),
                required=_engine.bool_value(values, "required"),
                data_access=structure,
            )
            prop = None
            section = _engine.string_value(values, "section")
            input_keys.append(key)
        elif name == "output":
            key, values, _nodes = _engine.call_values(
                decorator,
                name,
                allowed={"value_type", "structure", "label", "description"},
                fail=fail,
                constants=constants,
                cache=cache,
                reserved=_RESERVED_DECLARATION_NAMES,
                reject_private=True,
            )
            structure = _engine.string_value(values, "structure", "item")
            if structure not in {"item", "list", "tree"}:
                raise fail(decorator, "structure must be 'item', 'list', or 'tree'")
            port = _engine.port_spec(
                key,
                direction="out",
                data_type=values.get("value_type", GRAPH_DATA_TYPE_ID),
                label=_engine.label_value(key, values),
                description=_engine.string_value(values, "description"),
                data_access=structure,
            )
            prop = None
            section = ""
            output_keys.append(key)
        elif name in _engine.CONTROL_DECORATORS:
            key, values, _nodes = _engine.call_values(
                decorator,
                name,
                allowed=_engine.CONTROL_ALLOWED_FIELDS[name],
                fail=fail,
                constants=constants,
                cache=cache,
                reserved=_RESERVED_DECLARATION_NAMES,
                reject_private=True,
            )
            try:
                prop, data_type, accepted, data_access = _engine.control_spec(
                    name, key, values
                )
            except (OverflowError, _engine.DeclarationValueError) as exc:
                message = (
                    "Decorator numeric literal is outside the supported range"
                    if isinstance(exc, OverflowError)
                    else str(exc)
                )
                raise fail(decorator, message) from exc
            section = _engine.string_value(values, "section")
            port = (
                _engine.port_spec(
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
                if _engine.bool_value(values, "port")
                else None
            )
            control_keys.append(key)
        else:
            raise fail(decorator, f"Unsupported decorator @corex.{name}")

        if key in used_keys:
            raise fail(decorator, f"Duplicate or cross-direction key {key!r}")
        used_keys.add(key)
        if port is not None:
            ports.append(port)
        if prop is not None:
            properties.append(prop)
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
        raise fail(
            function,
            "Node functions use plain required parameters without defaults, positional-only, keyword-only, *args, or **kwargs",
        )
    signature = tuple(argument.arg for argument in args.args)
    expected = ("ctx", *input_keys, *(("settings",) if control_keys else ()))
    if signature != expected:
        raise fail(
            function,
            "Node function parameters must exactly be " + ", ".join(expected),
        )
    _validate_settings_body(function, tuple(control_keys), fail=fail)

    used_group_ids: set[str] = set()
    settings_groups = tuple(
        SettingsGroupSpec(
            _engine.group_id(label, used_group_ids),
            label,
            tuple(items),
        )
        for label, items in section_items.items()
    )
    is_async = isinstance(function, ast.AsyncFunctionDef)
    return PythonFunctionDeclaration(
        spec=NodeTypeSpec(
            type_id=metadata["type_id"],
            display_name=metadata["display_name"],
            category_path=metadata["category_path"],
            icon=metadata["icon"],
            ports=tuple(ports),
            properties=tuple(properties),
            description=metadata["description"],
            is_async=is_async,
            keywords=metadata["keywords"],
            settings_groups=settings_groups,
        ),
        function_name=function.name,
        input_keys=tuple(input_keys),
        output_keys=tuple(output_keys),
        control_keys=tuple(control_keys),
        is_async=is_async,
    )


@lru_cache(maxsize=128)
def _discover(
    source: str,
    filename: str,
    allow_reserved_ids: bool,
) -> tuple[PythonFunctionDeclaration, ...]:
    fail = _failure(filename)
    if len(source.encode("utf-8")) > _engine.MAX_SOURCE_BYTES:
        raise fail(None, "Plugin source is too large")
    try:
        module = ast.parse(source, filename=filename, mode="exec")
    except SyntaxError as exc:
        raise PluginDeclarationError(
            exc.msg,
            filename=filename,
            line=exc.lineno or 1,
            column=exc.offset or 1,
        ) from exc
    if sum(1 for _ in ast.walk(module)) > _engine.MAX_AST_NODES:
        raise fail(module, "Plugin syntax tree is too large")

    top_level_functions = tuple(
        item
        for item in module.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    if any(
        isinstance(statement, ast.ImportFrom)
        and any(item.name == "*" for item in statement.names)
        for statement in module.body
    ):
        raise fail(module, "Star imports are unsupported in plugin modules")
    aliases = _corex_aliases(module)
    for function in top_level_functions:
        for decorator in function.decorator_list:
            if _decorator_root_name(decorator) in aliases:
                raise fail(decorator, "Imported corex aliases are unsupported")
    top_level_ids = {id(item) for item in top_level_functions}
    decorator_ids = {
        id(decorator)
        for function in top_level_functions
        for decorator in function.decorator_list
    }
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if id(node) not in top_level_ids and any(
                _engine.corex_decorator_name(item) == "node"
                for item in node.decorator_list
            ):
                raise fail(node, "Node functions must be top-level")
        if (
            isinstance(node, ast.Call)
            and id(node) not in decorator_ids
            and _engine.corex_decorator_name(node) == "node"
        ):
            raise fail(node, "Dynamically generated node functions are unsupported")

    functions = tuple(
        function
        for function in top_level_functions
        if any(
            _engine.corex_decorator_name(item) == "node"
            for item in function.decorator_list
        )
    )
    if functions and not _has_corex_import(module):
        raise fail(functions[0], "Plugin source must contain `import corex`")
    if sum(len(function.decorator_list) for function in functions) > _engine.MAX_DECORATORS:
        raise fail(module, "Plugin source declares too many decorators")
    binding_counts = _module_binding_counts(module)
    for function in functions:
        if binding_counts.get(function.name) != 1:
            raise fail(
                function,
                f"Node function name {function.name!r} must be unique in its module",
            )

    constants = _literal_assignments(module)
    cache: dict[str, Any] = {}
    declarations = tuple(
        _parse_function(
            function,
            filename=filename,
            constants=constants,
            cache=cache,
            allow_reserved_ids=allow_reserved_ids,
        )
        for function in functions
    )
    type_ids = [declaration.spec.type_id for declaration in declarations]
    if len(type_ids) != len(set(type_ids)):
        duplicate = next(type_id for type_id in type_ids if type_ids.count(type_id) > 1)
        raise fail(module, f"Node id {duplicate!r} is duplicated")
    return declarations


def discover_plugin_declarations(
    source: str,
    *,
    filename: str = "<plugin>",
    allow_reserved_ids: bool = False,
    owner_id: str = "",
) -> tuple[PythonFunctionDeclaration, ...]:
    if allow_reserved_ids and owner_id != INTERNAL_BUILTIN_FUNCTION_OWNER_ID:
        raise ValueError("Reserved node ids require the internal built-in owner")
    return _discover(str(source), str(filename), bool(allow_reserved_ids))


__all__ = [
    "PluginDeclarationError",
    "PythonFunctionDeclaration",
    "discover_plugin_declarations",
]
