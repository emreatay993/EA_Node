from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import lru_cache, partial

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_EXPORT_NODE_TYPE_ID,
    DPF_MESH_EXTRACT_NODE_TYPE_ID,
    DPF_MESH_SCOPING_NODE_TYPE_ID,
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FILE_NODE_TYPE_ID,
    DPF_TIME_SCOPING_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
    normalize_dpf_descriptor_spec,
)
from ea_node_editor.nodes.builtins.ansys_dpf_helper_adapters import (
    GeneratedDpfHelperDefinition,
    load_generated_dpf_helper_definitions,
)
from ea_node_editor.nodes.builtins.ansys_dpf_taxonomy import (
    DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_INPUTS_CATEGORY_PATH,
    DPF_VIEWER_CATEGORY_PATH,
    DPF_WORKFLOW_CATEGORY_PATH,
)
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.nodes.plugin_contracts import NodePlugin, PluginDescriptor


def _load_ansys_dpf_helper_plugin_factories() -> tuple[Callable[[], NodePlugin], ...]:
    from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
        DpfExportNodePlugin,
        DpfMeshExtractNodePlugin,
        DpfMeshScopingNodePlugin,
        DpfModelNodePlugin,
        DpfResultFileNodePlugin,
        DpfTimeScopingNodePlugin,
    )
    from ea_node_editor.nodes.builtins.ansys_dpf_viewer import DpfViewerNodePlugin

    return (
        DpfResultFileNodePlugin,
        DpfModelNodePlugin,
        DpfMeshScopingNodePlugin,
        DpfTimeScopingNodePlugin,
        DpfMeshExtractNodePlugin,
        DpfExportNodePlugin,
        DpfViewerNodePlugin,
    )


_HELPER_CATEGORY_PATHS = {
    DPF_RESULT_FILE_NODE_TYPE_ID: DPF_INPUTS_CATEGORY_PATH,
    DPF_MODEL_NODE_TYPE_ID: DPF_WORKFLOW_CATEGORY_PATH,
    DPF_MESH_SCOPING_NODE_TYPE_ID: DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_TIME_SCOPING_NODE_TYPE_ID: DPF_HELPERS_SCOPING_CATEGORY_PATH,
    DPF_MESH_EXTRACT_NODE_TYPE_ID: DPF_HELPERS_CONTAINERS_CATEGORY_PATH,
    DPF_EXPORT_NODE_TYPE_ID: DPF_HELPERS_SUPPORT_CATEGORY_PATH,
    DPF_VIEWER_NODE_TYPE_ID: DPF_VIEWER_CATEGORY_PATH,
}


@dataclass(slots=True)
class _GeneratedDpfHelperNodePlugin:
    _spec: NodeTypeSpec
    _execute_callback: Callable[[object], NodeResult]

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        return self._execute_callback(ctx)


def _build_helper_descriptor(factory: Callable[[], NodePlugin]) -> PluginDescriptor:
    normalized_spec = normalize_dpf_descriptor_spec(factory().spec())
    return PluginDescriptor(
        spec=replace(
            normalized_spec,
            category_path=_HELPER_CATEGORY_PATHS[normalized_spec.type_id],
        ),
        factory=factory,
    )


def _generated_helper_factory(
    definition: GeneratedDpfHelperDefinition,
) -> Callable[[], NodePlugin]:
    return partial(
        _GeneratedDpfHelperNodePlugin,
        definition.spec,
        definition.execute,
    )


@lru_cache(maxsize=1)
def _generated_helper_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    return tuple(
        PluginDescriptor(
            spec=definition.spec,
            factory=_generated_helper_factory(definition),
        )
        for definition in load_generated_dpf_helper_definitions()
    )


@lru_cache(maxsize=1)
def load_ansys_dpf_helper_plugin_descriptors() -> tuple[PluginDescriptor, ...]:
    foundational = tuple(
        _build_helper_descriptor(factory)
        for factory in _load_ansys_dpf_helper_plugin_factories()
    )
    return foundational + _generated_helper_plugin_descriptors()


__all__ = [
    "load_ansys_dpf_helper_plugin_descriptors",
]
