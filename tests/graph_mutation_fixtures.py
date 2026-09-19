# Purpose: Construct shared dynamic-port registry fixtures without test assertions.
# Map: subsystems/graph_domain.md
# Tests: tests/test_graph_node_reconciliation.py, tests/test_graph_registry_normalization.py, tests/test_dataflow_graph_persistence.py
from __future__ import annotations

from ea_node_editor.nodes.builtins.core import StreamGateNodePlugin
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import (
    DynamicPortGroupSpec,
    DynamicPortRenameMode,
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import (
    INTEGER_DATA_TYPE_ID,
)


class _Plugin:
    def __init__(self, spec: NodeTypeSpec) -> None:
        self._spec = spec

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, _ctx) -> NodeResult:  # noqa: ANN001
        return NodeResult()


def _dynamic_input_ports(properties) -> tuple[PortSpec, ...]:  # noqa: ANN001
    return tuple(
        PortSpec(
            str(key),
            "in",
            "data",
            INTEGER_DATA_TYPE_ID,
            label=f"Variable {key}",
            required=False,
        )
        for key in properties["input_names"]
    )


def _dynamic_input_key_factory(properties) -> str:  # noqa: ANN001
    used = set(properties["input_names"])
    suffix = 1
    while f"input{suffix}" in used:
        suffix += 1
    return f"input{suffix}"


def _colliding_dynamic_input_key_factory(_properties) -> str:  # noqa: ANN001
    return "alpha"


def _dynamic_input_key_renamer(
    _properties,
    _old_key: str,
    value: str,
) -> str:  # noqa: ANN001
    return value.strip()


def _dynamic_input_spec(
    *,
    type_id: str = "tests.dynamic_inputs",
    key_factory=_dynamic_input_key_factory,  # noqa: ANN001
    rename_mode: DynamicPortRenameMode = "key",
) -> NodeTypeSpec:
    return NodeTypeSpec(
        type_id=type_id,
        display_name="Dynamic Inputs",
        category_path=("Tests",),
        icon="",
        ports=(),
        properties=(
            PropertySpec(
                "input_names",
                "json",
                ["alpha", "beta"],
                "Inputs",
                inspector_visible=False,
            ),
            PropertySpec("mode", "str", "unchanged", "Mode"),
        ),
        dynamic_port_groups=(
            DynamicPortGroupSpec(
                "inputs",
                "input_names",
                "in",
                _dynamic_input_ports,
                key_factory,
                rename_mode=rename_mode,
                key_renamer=(
                    _dynamic_input_key_renamer
                    if rename_mode == "key"
                    else None
                ),
            ),
        ),
    )


def dynamic_registry() -> NodeRegistry:
    registry = NodeRegistry()
    specs = (
        NodeTypeSpec(
            type_id="tests.source",
            display_name="Source",
            category_path=("Tests",),
            icon="",
            ports=(PortSpec("value", "out", "data", INTEGER_DATA_TYPE_ID),),
            properties=(),
        ),
        NodeTypeSpec(
            type_id="tests.sink",
            display_name="Sink",
            category_path=("Tests",),
            icon="",
            ports=(
                PortSpec(
                    "value",
                    "in",
                    "data",
                    INTEGER_DATA_TYPE_ID,
                    required=True,
                ),
            ),
            properties=(),
        ),
        NodeTypeSpec(
            type_id="core.subnode",
            display_name="Subnode",
            category_path=("Core",),
            icon="",
            ports=(),
            properties=(),
        ),
        StreamGateNodePlugin().spec(),
        _dynamic_input_spec(),
        _dynamic_input_spec(
            type_id="tests.dynamic_collision",
            key_factory=_colliding_dynamic_input_key_factory,
        ),
        _dynamic_input_spec(
            type_id="tests.dynamic_no_rename",
            rename_mode="none",
        ),
    )
    for spec in specs:
        registry.register(lambda spec=spec: _Plugin(spec))
    return registry
