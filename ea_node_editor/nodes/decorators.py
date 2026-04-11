from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ea_node_editor.nodes.node_specs import (
    CategoryPath,
    NodeRenderQualitySpec,
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.nodes.plugin_contracts import NodePlugin


def in_port(
    key: str,
    *,
    kind: str = "data",
    data_type: str = "any",
    required: bool = False,
    exposed: bool = True,
    allow_multiple_connections: bool = False,
) -> PortSpec:
    return PortSpec(
        key=key,
        direction="in",
        kind=kind,  # type: ignore[arg-type]
        data_type=data_type,
        required=required,
        exposed=exposed,
        allow_multiple_connections=allow_multiple_connections,
    )


def out_port(
    key: str,
    *,
    kind: str = "data",
    data_type: str = "any",
    required: bool = False,
    exposed: bool = True,
    allow_multiple_connections: bool = False,
) -> PortSpec:
    return PortSpec(
        key=key,
        direction="out",
        kind=kind,  # type: ignore[arg-type]
        data_type=data_type,
        required=required,
        exposed=exposed,
        allow_multiple_connections=allow_multiple_connections,
    )


def prop_str(
    key: str,
    default: str,
    label: str,
    *,
    expose_port_toggle: bool = False,
    inline_editor: str = "",
    inspector_editor: str = "",
) -> PropertySpec:
    return PropertySpec(
        key=key,
        type="str",
        default=default,
        label=label,
        expose_port_toggle=expose_port_toggle,
        inline_editor=inline_editor,
        inspector_editor=inspector_editor,
    )


def prop_int(
    key: str,
    default: int,
    label: str,
    *,
    expose_port_toggle: bool = False,
    inline_editor: str = "",
    inspector_editor: str = "",
) -> PropertySpec:
    return PropertySpec(
        key=key,
        type="int",
        default=default,
        label=label,
        expose_port_toggle=expose_port_toggle,
        inline_editor=inline_editor,
        inspector_editor=inspector_editor,
    )


def prop_float(
    key: str,
    default: float,
    label: str,
    *,
    expose_port_toggle: bool = False,
    inline_editor: str = "",
    inspector_editor: str = "",
) -> PropertySpec:
    return PropertySpec(
        key=key,
        type="float",
        default=default,
        label=label,
        expose_port_toggle=expose_port_toggle,
        inline_editor=inline_editor,
        inspector_editor=inspector_editor,
    )


def prop_bool(
    key: str,
    default: bool,
    label: str,
    *,
    expose_port_toggle: bool = False,
    inline_editor: str = "",
    inspector_editor: str = "",
) -> PropertySpec:
    return PropertySpec(
        key=key,
        type="bool",
        default=default,
        label=label,
        expose_port_toggle=expose_port_toggle,
        inline_editor=inline_editor,
        inspector_editor=inspector_editor,
    )


def prop_enum(
    key: str,
    default: str,
    label: str,
    *,
    values: Iterable[str],
    expose_port_toggle: bool = False,
    inline_editor: str = "",
    inspector_editor: str = "",
) -> PropertySpec:
    return PropertySpec(
        key=key,
        type="enum",
        default=default,
        label=label,
        expose_port_toggle=expose_port_toggle,
        enum_values=tuple(values),
        inline_editor=inline_editor,
        inspector_editor=inspector_editor,
    )


def prop_json(
    key: str,
    default: Any,
    label: str,
    *,
    expose_port_toggle: bool = False,
    inline_editor: str = "",
    inspector_editor: str = "",
) -> PropertySpec:
    return PropertySpec(
        key=key,
        type="json",
        default=default,
        label=label,
        expose_port_toggle=expose_port_toggle,
        inline_editor=inline_editor,
        inspector_editor=inspector_editor,
    )


def node_type(
    *,
    type_id: str,
    display_name: str,
    category_path: CategoryPath,
    icon: str,
    ports: tuple[PortSpec, ...] | list[PortSpec],
    properties: tuple[PropertySpec, ...] | list[PropertySpec],
    collapsible: bool = True,
    description: str = "",
    runtime_behavior: str = "active",
    surface_family: str = "standard",
    surface_variant: str = "",
    render_quality: NodeRenderQualitySpec | dict[str, Any] | None = None,
) -> Callable[[type[NodePlugin]], type[NodePlugin]]:
    spec = NodeTypeSpec(
        type_id=type_id,
        display_name=display_name,
        category_path=category_path,
        icon=icon,
        ports=tuple(ports),
        properties=tuple(properties),
        collapsible=collapsible,
        description=description,
        runtime_behavior=runtime_behavior,  # type: ignore[arg-type]
        surface_family=surface_family,  # type: ignore[arg-type]
        surface_variant=surface_variant,
        render_quality=render_quality,  # type: ignore[arg-type]
    )

    def decorator(cls: type[NodePlugin]) -> type[NodePlugin]:
        def spec_method(self) -> NodeTypeSpec:  # noqa: ANN001
            return spec

        setattr(cls, "spec", spec_method)
        return cls

    return decorator
