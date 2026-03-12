from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Protocol

PortDirection = Literal["in", "out"]
PortKind = Literal["exec", "completed", "failed", "data"]
PropertyType = Literal["str", "int", "float", "bool", "path", "enum", "json"]
InlineEditorType = Literal["", "text", "number", "toggle", "enum"]


@dataclass(slots=True, frozen=True)
class PortSpec:
    key: str
    direction: PortDirection
    kind: PortKind
    data_type: str
    required: bool = False
    exposed: bool = True


@dataclass(slots=True, frozen=True)
class PropertySpec:
    key: str
    type: PropertyType
    default: Any
    label: str
    expose_port_toggle: bool = False
    enum_values: tuple[str, ...] = ()
    inline_editor: InlineEditorType = ""


@dataclass(slots=True, frozen=True)
class NodeTypeSpec:
    type_id: str
    display_name: str
    category: str
    icon: str
    ports: tuple[PortSpec, ...]
    properties: tuple[PropertySpec, ...]
    collapsible: bool = True
    description: str = ""
    is_async: bool = False


@dataclass(slots=True)
class ExecutionContext:
    run_id: str
    node_id: str
    workspace_id: str
    inputs: dict[str, Any]
    properties: dict[str, Any]
    emit_log: Callable[[str, str], None]
    trigger: dict[str, Any] = field(default_factory=dict)
    should_stop: Callable[[], bool] = field(default=lambda: False)
    register_cancel: Callable[[Callable[[], None]], None] = field(default=lambda _callback: None)

    def log_info(self, message: str) -> None:
        self.emit_log("info", message)

    def log_warning(self, message: str) -> None:
        self.emit_log("warning", message)

    def log_error(self, message: str) -> None:
        self.emit_log("error", message)


@dataclass(slots=True)
class NodeResult:
    outputs: dict[str, Any] = field(default_factory=dict)
    completed: bool = True
    warnings: tuple[str, ...] = ()


class NodePlugin(Protocol):
    def spec(self) -> NodeTypeSpec:
        ...

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        ...


class AsyncNodePlugin(NodePlugin, Protocol):
    """Extended protocol for nodes that support non-blocking execution.

    Set ``is_async=True`` in the NodeTypeSpec and implement ``async_execute``
    instead of (or in addition to) ``execute``.  The worker will run async
    nodes in a thread pool so they don't block the rest of the pipeline.
    """

    async def async_execute(self, ctx: ExecutionContext) -> NodeResult:
        ...


def property_has_inline_editor(property_spec: PropertySpec) -> bool:
    return bool(str(property_spec.inline_editor).strip())


def inline_property_specs(spec: NodeTypeSpec) -> tuple[PropertySpec, ...]:
    return tuple(
        property_spec
        for property_spec in spec.properties
        if property_has_inline_editor(property_spec)
    )
