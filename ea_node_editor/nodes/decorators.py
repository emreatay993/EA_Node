from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ea_node_editor.nodes.types import NodePlugin, NodeTypeSpec, PortSpec, PropertySpec


def in_port(
    key: str,
    *,
    kind: str = "data",
    data_type: str = "any",
    required: bool = False,
    exposed: bool = True,
) -> PortSpec:
    return PortSpec(
        key=key,
        direction="in",
        kind=kind,  # type: ignore[arg-type]
        data_type=data_type,
        required=required,
        exposed=exposed,
    )


def out_port(
    key: str,
    *,
    kind: str = "data",
    data_type: str = "any",
    required: bool = False,
    exposed: bool = True,
) -> PortSpec:
    return PortSpec(
        key=key,
        direction="out",
        kind=kind,  # type: ignore[arg-type]
        data_type=data_type,
        required=required,
        exposed=exposed,
    )


def prop_str(key: str, default: str, label: str, *, expose_port_toggle: bool = False) -> PropertySpec:
    return PropertySpec(key=key, type="str", default=default, label=label, expose_port_toggle=expose_port_toggle)


def prop_int(key: str, default: int, label: str, *, expose_port_toggle: bool = False) -> PropertySpec:
    return PropertySpec(key=key, type="int", default=default, label=label, expose_port_toggle=expose_port_toggle)


def prop_float(key: str, default: float, label: str, *, expose_port_toggle: bool = False) -> PropertySpec:
    return PropertySpec(key=key, type="float", default=default, label=label, expose_port_toggle=expose_port_toggle)


def prop_bool(key: str, default: bool, label: str, *, expose_port_toggle: bool = False) -> PropertySpec:
    return PropertySpec(key=key, type="bool", default=default, label=label, expose_port_toggle=expose_port_toggle)


def prop_enum(
    key: str,
    default: str,
    label: str,
    *,
    values: Iterable[str],
    expose_port_toggle: bool = False,
) -> PropertySpec:
    return PropertySpec(
        key=key,
        type="enum",
        default=default,
        label=label,
        expose_port_toggle=expose_port_toggle,
        enum_values=tuple(values),
    )


def prop_json(key: str, default: Any, label: str, *, expose_port_toggle: bool = False) -> PropertySpec:
    return PropertySpec(key=key, type="json", default=default, label=label, expose_port_toggle=expose_port_toggle)


def node_type(
    *,
    type_id: str,
    display_name: str,
    category: str,
    icon: str,
    ports: tuple[PortSpec, ...] | list[PortSpec],
    properties: tuple[PropertySpec, ...] | list[PropertySpec],
    collapsible: bool = True,
    description: str = "",
) -> Callable[[type[NodePlugin]], type[NodePlugin]]:
    spec = NodeTypeSpec(
        type_id=type_id,
        display_name=display_name,
        category=category,
        icon=icon,
        ports=tuple(ports),
        properties=tuple(properties),
        collapsible=collapsible,
        description=description,
    )

    def decorator(cls: type[NodePlugin]) -> type[NodePlugin]:
        def spec_method(self) -> NodeTypeSpec:  # noqa: ANN001
            return spec

        setattr(cls, "spec", spec_method)
        return cls

    return decorator

