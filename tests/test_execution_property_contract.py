# Purpose: Prove presentation-property declaration, admission, and projection contracts.
# Map: subsystems/nodes_registry_builtins.md
# Tests: this file
from dataclasses import replace

import pytest

from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.node_specs import (
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
    ReadinessRequirementSpec,
)
from ea_node_editor.nodes.plugin_declaration import (
    PluginDeclarationError,
    discover_plugin_declarations,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.solution_provenance import SolutionProvenanceInputSpec
from ea_node_editor.nodes.spec_validation import validate_node_spec


@pytest.mark.parametrize(
    "control,arguments",
    [
        ("text", 'default="a"'),
        ("text_area", 'default="a"'),
        ("color", 'default="#ffffff"'),
        ("path", 'default=""'),
        ("switch", "default=True"),
        ("number", "default=2"),
        ("slider", "default=2, minimum=0, maximum=5"),
        ("dropdown", 'options=("a", "b")'),
        ("dropdown", 'options=("a", "b"), codes=(1, 2)'),
        ("interval", "default=(0, 1)"),
        ("list", 'default=["a"]'),
    ],
)
def test_all_control_declarations_preserve_execution_impact(control, arguments):
    source = f"""import corex
@corex.node(id="custom.display.a7c31e9b", name="Display", category=("Tests",))
@corex.{control}("ornament", {arguments}, affects_execution=False)
@corex.number("amount", default=3)
def display(ctx, settings):
    return {{}}
"""
    (declaration,) = discover_plugin_declarations(source)
    properties = {prop.key: prop for prop in declaration.spec.properties}
    assert properties["ornament"].affects_execution is False
    assert properties["amount"].affects_execution is True
    registry = NodeRegistry()
    registry.register_descriptor(declaration.spec, lambda: None)
    assert registry.execution_properties(declaration.spec.type_id, {}) == {"amount": 3}
    assert "ornament" in registry.default_properties(declaration.spec.type_id)


@pytest.mark.parametrize(
    "flag,extra", [('"false"', ""), ("0", ""), ("None", ""), ("False", ", port=True")]
)
def test_public_declarations_reject_invalid_presentation_contract(flag, extra):
    source = f"""import corex
@corex.node(id="custom.display.a7c31e9b", name="Display", category=("Tests",))
@corex.number("ornament", default=1, affects_execution={flag}{extra})
def display(ctx, settings):
    return {{}}
"""
    with pytest.raises(PluginDeclarationError):
        discover_plugin_declarations(source)


def test_python_script_instance_uses_the_same_projection():
    registry = build_builtin_registry()
    script = """@corex.node
@corex.text("ornament", default="a", affects_execution=False)
@corex.number("amount", default=3)
def run(ctx, ornament, amount):
    return {}
"""
    authored = registry.normalize_properties(
        "code.python_script", {"script": script, "ornament": "b"}
    )
    projected = registry.execution_properties("code.python_script", authored)
    assert authored["ornament"] == "b"
    assert "ornament" not in projected
    assert projected["amount"] == 3
    assert projected["script"] == script


@pytest.mark.parametrize(
    "dependency", ["input", "readiness", "condition", "provenance", "invalid_bool"]
)
def test_registry_rejects_known_execution_dependencies(dependency):
    prop = PropertySpec("path", "path", "", "Path", affects_execution=False)
    spec = NodeTypeSpec("tests.contract", "Contract", ("Tests",), "", (), (prop,))
    if dependency == "input":
        spec = replace(
            spec,
            ports=(
                PortSpec("path", "in", "data", "COREX.DataTypes.Path", required=False),
            ),
        )
    elif dependency == "readiness":
        spec = replace(
            spec,
            readiness_requirements=(
                ReadinessRequirementSpec(any_of_properties=("path",)),
            ),
        )
    elif dependency == "condition":
        from ea_node_editor.nodes.node_specs import PropertyConditionSpec

        spec = replace(
            spec,
            properties=(prop, PropertySpec("value", "str", "", "Value")),
            readiness_requirements=(
                ReadinessRequirementSpec(
                    any_of_properties=("value",),
                    when_properties=(PropertyConditionSpec("path", ("x",)),),
                ),
            ),
        )
    elif dependency == "provenance":
        spec = replace(
            spec,
            solution_provenance_inputs=(SolutionProvenanceInputSpec("path", "file"),),
        )
    else:
        spec = replace(spec, properties=(prop.with_changes(affects_execution=0),))
    with pytest.raises((ValueError, TypeError), match="affects.execution"):
        validate_node_spec(spec, data_types=NodeRegistry().data_types)


def test_registry_agreement_binds_execution_impact():
    prop = PropertySpec("ornament", "str", "a", "Ornament")
    spec = NodeTypeSpec("tests.contract", "Contract", ("Tests",), "", (), (prop,))
    first, second = NodeRegistry(), NodeRegistry()
    first.register_descriptor(spec, lambda: None)
    second.register_descriptor(
        replace(spec, properties=(prop.with_changes(affects_execution=False),)),
        lambda: None,
    )
    assert first.contract_fingerprint() != second.contract_fingerprint()


def test_shipped_catalogue_has_explicit_presentation_inventory():
    from ea_node_editor.nodes.bootstrap import build_default_registry

    registry = build_default_registry(include_public_plugins=False)
    expected = {
        "data.panel": {"font_size", "alignment", "auto_resize"},
        "tabular.input": {"tabular_table_view_state", "data_view_name", "data_view_migration_notice"},
        "model.viewer": {
            "show_mesh_edges",
            "representation",
            "show_attribute_colors",
            "show_orientation_triad",
            "show_view_cube",
            "show_world_axes",
            "scene_styles",
            "clip_enabled",
            "clip_axis",
            "clip_offset",
            "parallel_projection",
            "viewer_background",
            "camera_bookmarks",
        },
        "media.panel": {
            "fit_mode",
            "animation_playback_mode",
            "lock_aspect_ratio",
            "show_title",
            "show_frame",
            "crop_x",
            "crop_y",
            "crop_w",
            "crop_h",
            "rotation_degrees",
            "mirror_horizontal",
            "mirror_vertical",
            "page_number",
            "auto_play",
            "loop",
            "muted",
            "volume",
            "playback_rate",
            "position_ms",
            "timeline_bookmarks",
            "clip_enabled",
            "clip_start_ms",
            "clip_end_ms",
        },
    }
    actual = {
        spec.type_id: {
            prop.key for prop in spec.properties if not prop.affects_execution
        }
        for spec in registry.all_specs()
        if any(not prop.affects_execution for prop in spec.properties)
    }
    assert actual == expected
    for type_id in ("plot.signal", "data.number_slider"):
        assert all(
            prop.affects_execution for prop in registry.get_spec(type_id).properties
        )
