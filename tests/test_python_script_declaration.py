# Purpose: Verify Python Script parser, declarations, and source diagnostics.
# Map: subsystems/nodes_registry_builtins.md
# Tests: this file
from __future__ import annotations

import pytest

from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.python_script_declaration import PythonScriptDeclarationError
from ea_node_editor.runtime_contracts import Interval1D


def _resolve(source: str):
    registry = build_builtin_registry()
    properties = registry.normalize_properties(
        "core.python_script",
        {"script": source},
    )
    return registry, properties, registry.resolve_spec("core.python_script", properties)


def test_all_python_script_decorators_resolve_to_shared_metadata() -> None:
    source = """@corex.node
@corex.input("values", value_type=float, structure="tree", required=True, section="Data")
@corex.input("image", value_type=corex.Image)
@corex.output("result", value_type="COREX.DataTypes.String")
@corex.text("title", default="Plot", section="Style", port=True)
@corex.number("count", default=2, section="Style")
@corex.switch("enabled", default=True, section="Style", port=True)
@corex.dropdown("mode", default=1, options=("Mean", "Max"), codes=(0, 1), section="Style", port=True)
@corex.slider("width", default=2.0, minimum=0.5, maximum=8.0, step=0.5, section="Style", port=True)
@corex.color("accent", default="#336699", section="Style")
@corex.path("folder", default="", file_filter="All files (*)", section="Files", port=True)
@corex.text_area("notes", default="", section="Files")
@corex.interval("bounds", default=(0.0, 1.0), section="Ranges", port=True)
@corex.list("labels", default=["A"], item_type=str, section="Data", port=True)
def run(ctx, values, image, title, count, enabled, mode, width, accent, folder, notes, bounds, labels):
    return {"result": title}
"""
    _registry, properties, spec = _resolve(source)

    assert [port.key for port in spec.ports] == [
        "values",
        "image",
        "result",
        "title",
        "enabled",
        "mode",
        "width",
        "folder",
        "bounds",
        "labels",
    ]
    assert [prop.key for prop in spec.properties] == [
        "script",
        "timeout_sec",
        "title",
        "count",
        "enabled",
        "mode",
        "width",
        "accent",
        "folder",
        "notes",
        "bounds",
        "labels",
    ]
    assert properties["bounds"] == Interval1D(0.0, 1.0)
    assert [(group.group_id, group.label) for group in spec.settings_groups] == [
        ("data", "Data"),
        ("style", "Style"),
        ("files", "Files"),
        ("ranges", "Ranges"),
    ]


def test_python_script_labels_preserve_explicit_blank_and_derive_omitted() -> None:
    source = '''@corex.node
@corex.input("omitted_input", value_type=corex.Any)
@corex.input("blank_input", value_type=corex.Any, label="")
@corex.output("omitted_output", value_type=corex.Any)
@corex.output("blank_output", value_type=corex.Any, label="")
@corex.text("omitted_control")
@corex.text("blank_control", label="")
def run(ctx, omitted_input, blank_input, omitted_control, blank_control):
    return {}
'''

    _registry, _properties, spec = _resolve(source)
    ports = {port.key: port for port in spec.ports}
    properties = {prop.key: prop for prop in spec.properties}

    assert ports["omitted_input"].label == "Omitted Input"
    assert ports["blank_input"].label == ""
    assert ports["omitted_output"].label == "Omitted Output"
    assert ports["blank_output"].label == ""
    assert properties["omitted_control"].label == "Omitted Control"
    assert properties["blank_control"].label == ""


@pytest.mark.parametrize("direction", ("input", "output"))
def test_python_script_port_types_require_explicit_source_located_declarations(
    direction: str,
) -> None:
    parameters = "ctx, value" if direction == "input" else "ctx"
    source = f'''@corex.node
@corex.{direction}("value")
def run({parameters}): return {{}}
'''
    with pytest.raises(PythonScriptDeclarationError, match="requires explicit value_type=") as caught:
        _resolve(source)
    assert "line 2, column 2" in str(caught.value)
    explicit_source = source.replace('(\"value\")', '(\"value\", value_type=corex.Any)')
    _registry, _properties, spec = _resolve(explicit_source)
    assert spec.ports[0].data_type == "COREX.DataTypes.Any"


def test_decorator_discovery_rejects_expressions_without_executing_them() -> None:
    source = """
def explode():
    raise AssertionError("must not run")

@corex.node
@corex.text("title", default=explode())
def run(ctx, title):
    return {}
"""
    registry = build_builtin_registry()
    with pytest.raises(PythonScriptDeclarationError, match="must be literals"):
        registry.normalize_properties("core.python_script", {"script": source})


def test_decorator_discovery_bounds_source_size() -> None:
    registry = build_builtin_registry()
    source = "#" * (256 * 1024 + 1)
    with pytest.raises(PythonScriptDeclarationError, match="too large"):
        registry.normalize_properties("core.python_script", {"script": source})


@pytest.mark.parametrize(
    ("source", "message"),
    (
        (
            "@corex.node\n@corex.input('value', value_type=corex.Any)\ndef run(ctx):\n    return {}\n",
            "exactly match",
        ),
        (
            "@corex.node\n@corex.unknown('value')\ndef run(ctx):\n    return {}\n",
            "Unknown corex decorator",
        ),
        (
            "@corex.node\n@corex.output('value', value_type=corex.Any, section='Bad')\ndef run(ctx):\n    return {}\n",
            "does not support section",
        ),
        (
            "@corex.node\nasync def run(ctx):\n    return {}\n",
            "must be synchronous",
        ),
    ),
)
def test_invalid_declarations_have_actionable_source_errors(
    source: str,
    message: str,
) -> None:
    registry = build_builtin_registry()
    with pytest.raises(PythonScriptDeclarationError, match=message) as caught:
        registry.normalize_properties("core.python_script", {"script": source})
    assert "line" in str(caught.value)
    assert "column" in str(caught.value)


def test_registered_type_id_validation_runs_after_literal_parsing() -> None:
    source = """@corex.node
@corex.output("value", value_type="Missing.Type")
def run(ctx):
    return {}
"""
    registry = build_builtin_registry()
    with pytest.raises(ValueError, match="unknown data-type ID"):
        registry.normalize_properties("core.python_script", {"script": source})


@pytest.mark.parametrize(
    "decorator",
    (
        '@corex.text("value", _port_description="Private")',
        '@corex.text("value", _section_order=0)',
        '@corex.interval("value", _persistence_type=None)',
        '@corex.text("value", _port_required=True)',
        '@corex.text("value", _port_label="")',
        '@corex.text("value", _port_structure="tree")',
        '@corex.text("value", _port_uses_property_default=False)',
        '@corex.text("value", _port_value_type="COREX.DataTypes.Any")',
        '@corex.text("value", _port_accepted_data_types=("COREX.DataTypes.Any",))',
        '@corex.text("value", _property_type="json")',
        '@corex.text("value", _property_default={})',
        '@corex.text("value", _inline_editor="secret")',
        '@corex.text("value", _inspector_editor="secret")',
        '@corex.text("value", _inspector_visible=False)',
        '@corex.text("value", _property_group="Internal")',
        '@corex.text("value", _sensitive=True)',
        '@corex.text("value", _sensitive_scope_key="scope")',
        '@corex.input("value", value_type=corex.Any, _accepted_data_types=("COREX.DataTypes.Any",))',
    ),
)
def test_python_script_rejects_internal_control_fields(decorator: str) -> None:
    source = f'''@corex.node
{decorator}
def run(ctx, value):
    return {{}}
'''

    registry = build_builtin_registry()
    with pytest.raises(
        PythonScriptDeclarationError,
        match="Private decorator field .* is reserved for internal built-ins",
    ):
        registry.normalize_properties("core.python_script", {"script": source})


def test_python_script_rejects_internal_node_readiness_metadata() -> None:
    source = '''@corex.node(_readiness_requirements=())
@corex.output("result", value_type=corex.Any)
def run(ctx):
    return {}
'''
    registry = build_builtin_registry()
    with pytest.raises(
        PythonScriptDeclarationError,
        match="@corex.node does not accept arguments",
    ):
        registry.normalize_properties("core.python_script", {"script": source})


@pytest.mark.parametrize(
    "field",
    (
        "_collapsible=False",
        '_property_output_collisions=("value",)',
        '_surface_family="viewer"',
        '_surface_variant="embedded"',
        '_render_quality_tiers=("full", "proxy")',
    ),
)
def test_python_script_rejects_internal_node_surface_metadata(field: str) -> None:
    source = f'''@corex.node({field})
@corex.output("result", value_type=corex.Any)
def run(ctx):
    return {{}}
'''
    registry = build_builtin_registry()
    with pytest.raises(
        PythonScriptDeclarationError,
        match="@corex.node does not accept arguments",
    ):
        registry.normalize_properties("core.python_script", {"script": source})
