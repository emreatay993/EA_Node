from __future__ import annotations

import json

import pytest

from ea_node_editor.addons.mars.function_nodes import SOURCE as MARS_SOURCE
from ea_node_editor.addons.mars.metadata import MARS_ADDON_ID
from ea_node_editor.addons.tabular_data.catalog import TABULAR_DATA_FUNCTION_TYPE_IDS
from ea_node_editor.nodes.bootstrap import build_builtin_registry, build_default_registry
from ea_node_editor.nodes.plugin_declaration import discover_plugin_declarations
from ea_node_editor.nodes.registry import resolve_instance_ports
from tests.non_dpf_catalog_fixture import (
    DOCUMENTATION_OVERLAY_PATH,
    load_effective_non_dpf_catalog,
)


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


def test_t17_documentation_overlay_has_exact_scope() -> None:
    overlay = json.loads(DOCUMENTATION_OVERLAY_PATH.read_text(encoding="utf-8"))

    assert len(overlay["keyword_patches"]) == 6
    assert sum(
        len(descriptions)
        for descriptions in overlay["port_description_patches"].values()
    ) == 105
    assert overlay["python_script_default_source"]["type_id"] == "core.python_script"
    assert overlay["python_script_default_source"]["property_key"] == "script"
    assert len(load_effective_non_dpf_catalog()) == 133


def test_t17_documentation_overlay_rejects_unknown_duplicate_and_non_doc_patches(
    tmp_path,
) -> None:  # noqa: ANN001
    original_text = DOCUMENTATION_OVERLAY_PATH.read_text(encoding="utf-8")
    original = json.loads(original_text)

    unknown = dict(original)
    unknown["keyword_patches"] = {
        **original["keyword_patches"],
        "unknown.node": ["unknown"],
    }
    overlay_path = tmp_path / "unknown.json"
    overlay_path.write_text(json.dumps(unknown), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown keyword patch target"):
        load_effective_non_dpf_catalog(overlay_path=overlay_path)

    duplicate_path = tmp_path / "duplicate.json"
    duplicate_path.write_text(
        original_text.replace(
            '"math.field_vector_container":',
            '"math.field_vector_container": ["duplicate"],\n'
            '    "math.field_vector_container":',
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate overlay patch or field"):
        load_effective_non_dpf_catalog(overlay_path=duplicate_path)

    non_doc = {**original, "display_name_patches": {}}
    non_doc_path = tmp_path / "non_doc.json"
    non_doc_path.write_text(json.dumps(non_doc), encoding="utf-8")
    with pytest.raises(ValueError, match="Documentation overlay must contain only"):
        load_effective_non_dpf_catalog(overlay_path=non_doc_path)
