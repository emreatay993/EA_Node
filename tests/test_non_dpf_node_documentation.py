from __future__ import annotations

from ea_node_editor.addons.mars.function_nodes import SOURCE as MARS_SOURCE
from ea_node_editor.addons.mars.metadata import MARS_ADDON_ID
from ea_node_editor.addons.tabular_data.catalog import TABULAR_DATA_FUNCTION_TYPE_IDS
from ea_node_editor.nodes.bootstrap import build_builtin_registry, build_default_registry
from ea_node_editor.nodes.plugin_declaration import discover_plugin_declarations
from ea_node_editor.nodes.registry import resolve_instance_ports


_TABULAR_DATA_REGISTRY = build_default_registry(include_public_plugins=False)
_MARS_SPECS = tuple(
    declaration.spec
    for declaration in discover_plugin_declarations(
        MARS_SOURCE,
        filename="mars_nodes.py",
        allow_reserved_ids=True,
        owner_id=MARS_ADDON_ID,
        allow_internal_metadata=True,
    )
)
NON_DPF_NODE_SPECS = (
    *build_builtin_registry().all_specs(),
    *(
        _TABULAR_DATA_REGISTRY.get_spec(type_id)
        for type_id in TABULAR_DATA_FUNCTION_TYPE_IDS
    ),
    *_MARS_SPECS,
)


def test_all_repo_owned_non_dpf_nodes_have_authored_documentation() -> None:
    specs = NON_DPF_NODE_SPECS
    resolved_ports = tuple((spec, resolve_instance_ports(spec, {})) for spec in specs)

    assert len(specs) == 133
    assert sum(len(ports) for _, ports in resolved_ports) == 519
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
