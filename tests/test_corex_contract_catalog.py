from __future__ import annotations

from ea_node_editor.nodes.bootstrap import build_builtin_registry


def test_builtin_registry_contains_retained_corex_contract_families() -> None:
    registry = build_builtin_registry()

    assert len(registry.all_specs()) == 123
    for type_id in (
        "plot.signal",
        "geometry.cylinder",
        "reference.construct_point",
        "security.windows_authentication",
        "reporting.markdown_flowchart",
    ):
        assert registry.spec_or_none(type_id) is not None

    for data_type_id in (
        "COREX.DataTypes.Image",
        "COREX.DataTypes.Color",
        "COREX.DataTypes.Point3D",
        "COREX.Geometry.OCPBody",
        "COREX.DataTree.Path",
    ):
        assert registry.data_types.require(data_type_id).type_id == data_type_id
