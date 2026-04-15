from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_FIELD_OPS_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    normalize_dpf_descriptor_spec,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    operator_family_category_path,
    operator_family_path,
    operator_source_path,
)
from ea_node_editor.nodes.node_specs import DpfOperatorSourceSpec
from ea_node_editor.nodes.plugin_contracts import NodePlugin, PluginDescriptor


def _load_ansys_dpf_operator_plugin_factories() -> tuple[Callable[[], NodePlugin], ...]:
    from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
        DpfFieldOpsNodePlugin,
        DpfResultFieldNodePlugin,
    )

    return (DpfResultFieldNodePlugin, DpfFieldOpsNodePlugin)


_OPERATOR_DESCRIPTOR_OVERRIDES = {
    DPF_RESULT_FIELD_NODE_TYPE_ID: {
        "category_path": operator_family_category_path("result"),
        "source_path": operator_source_path("result"),
        "family_path": operator_family_path("result"),
        "stability": "core",
    },
    DPF_FIELD_OPS_NODE_TYPE_ID: {
        "category_path": operator_family_category_path("math"),
        "source_path": operator_source_path("math"),
        "family_path": operator_family_path("math"),
        "stability": "core",
    },
}


def _build_operator_descriptor(factory: Callable[[], NodePlugin]) -> PluginDescriptor:
    normalized_spec = normalize_dpf_descriptor_spec(factory().spec())
    overrides = _OPERATOR_DESCRIPTOR_OVERRIDES[normalized_spec.type_id]
    node_source = normalized_spec.source_metadata
    if not isinstance(node_source, DpfOperatorSourceSpec):
        raise TypeError(f"Expected DpfOperatorSourceSpec for {normalized_spec.type_id}")

    return PluginDescriptor(
        spec=replace(
            normalized_spec,
            category_path=overrides["category_path"],
            source_metadata=replace(
                node_source,
                source_path=overrides["source_path"],
                family_path=overrides["family_path"],
                stability=overrides["stability"],
            ),
        ),
        factory=factory,
    )


def load_ansys_dpf_operator_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    return tuple(_build_operator_descriptor(factory) for factory in _load_ansys_dpf_operator_plugin_factories())


__all__ = [
    "load_ansys_dpf_operator_plugin_descriptors",
]
