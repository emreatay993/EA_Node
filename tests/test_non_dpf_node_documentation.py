from __future__ import annotations

from ea_node_editor.addons.mars.nodes import MARS_NODE_DESCRIPTORS
from ea_node_editor.addons.tabular_data.catalog import TABULAR_DATA_FUNCTION_TYPE_IDS
from ea_node_editor.nodes.bootstrap import BUILTIN_NODE_DESCRIPTORS, build_default_registry
from ea_node_editor.nodes.registry import resolve_instance_ports


_TABULAR_DATA_REGISTRY = build_default_registry(include_public_plugins=False)
NON_DPF_NODE_SPECS = (
    *(descriptor.spec for descriptor in BUILTIN_NODE_DESCRIPTORS),
    *(
        _TABULAR_DATA_REGISTRY.get_spec(type_id)
        for type_id in TABULAR_DATA_FUNCTION_TYPE_IDS
    ),
    *(descriptor.spec for descriptor in MARS_NODE_DESCRIPTORS),
)


def test_all_repo_owned_non_dpf_nodes_have_authored_documentation() -> None:
    specs = NON_DPF_NODE_SPECS
    resolved_ports = tuple((spec, resolve_instance_ports(spec, {})) for spec in specs)

    assert len(specs) == 87
    assert sum(len(ports) for _, ports in resolved_ports) == 336
    assert len({spec.type_id for spec in specs}) == len(specs)

    missing_node_descriptions = [spec.type_id for spec in specs if not spec.description.strip()]
    missing_keywords = [spec.type_id for spec in specs if not spec.keywords]
    missing_port_descriptions = [
        f"{spec.type_id}.{port.key}"
        for spec, ports in resolved_ports
        for port in ports
        if not port.description.strip()
    ]

    assert missing_node_descriptions == []
    assert missing_keywords == []
    assert missing_port_descriptions == []
