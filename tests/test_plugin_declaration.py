from __future__ import annotations

from collections import UserList
from pathlib import Path

import pytest

import corex
from corex import _Settings
from ea_node_editor.nodes.plugin_declaration import (
    PluginDeclarationError,
    discover_plugin_declarations as _discover_plugin_declarations,
)
from ea_node_editor.runtime_contracts import Interval1D


PUBLIC_EXPORTS = [
    "node",
    "input",
    "output",
    "text",
    "text_area",
    "number",
    "switch",
    "dropdown",
    "slider",
    "color",
    "path",
    "interval",
    "list",
    "Any",
    "Image",
    "Color",
    "Interval",
]


def discover_plugin_declarations(source: str, **kwargs):
    return _discover_plugin_declarations("import corex\n" + source, **kwargs)


def test_corex_public_exports_and_runtime_decorators_are_exact() -> None:
    assert corex.__all__ == PUBLIC_EXPORTS
    assert corex.Any == "COREX.DataTypes.Any"
    assert corex.Image == "COREX.DataTypes.Image"
    assert corex.Color == "COREX.DataTypes.Color"
    assert corex.Interval == "COREX.DataTypes.Interval1D"

    @corex.node(id="custom.identity.a7c31e9b", name="Identity", category=("Core",))
    @corex.input("value")
    @corex.output("result")
    def identity(ctx, value):
        return {"result": value}

    assert identity(None, 3) == {"result": 3}


def test_multiple_sync_async_nodes_and_literal_constants_are_discovered() -> None:
    source = '''
CATEGORY = ("Math", "Transforms")
KEYWORDS = ("scale", "multiply")
FACTOR = 2.0

@corex.node(
    id="custom.scale.a7c31e9b",
    name="Scale",
    category=CATEGORY,
    description="Scale a number.",
    keywords=KEYWORDS,
)
@corex.input("value", value_type=float, required=True, section="Data")
@corex.output("scaled", value_type=float)
@corex.slider("factor", default=FACTOR, minimum=0.0, maximum=10.0, section="Settings", port=True)
def scale(ctx, value, settings):
    return {"scaled": value * settings.factor}

@corex.node(id="custom.negate.b8d42f0a", name="Negate", category=("Math",))
@corex.input("value", value_type=float)
@corex.output("negated", value_type=float)
async def negate(ctx, value):
    return {"negated": -value}
'''

    scale, negate = discover_plugin_declarations(source, filename="nodes.py")

    assert scale.function_name == "scale"
    assert scale.input_keys == ("value",)
    assert scale.output_keys == ("scaled",)
    assert scale.control_keys == ("factor",)
    assert scale.spec.category_path == ("Math", "Transforms")
    assert scale.spec.keywords == ("scale", "multiply")
    assert [port.key for port in scale.spec.ports] == ["value", "scaled", "factor"]
    assert scale.spec.properties[0].default == 2.0
    assert [(group.group_id, group.label) for group in scale.spec.settings_groups] == [
        ("data", "Data"),
        ("settings", "Settings"),
    ]
    assert not scale.is_async
    assert negate.function_name == "negate"
    assert negate.is_async
    assert negate.spec.is_async


def test_every_control_uses_shared_metadata_and_one_settings_parameter() -> None:
    source = '''
OPTIONS = ("Mean", "Maximum")

@corex.node(id="custom.controls.1234abcd", name="Controls", category=("Tests",))
@corex.output("result", value_type=str)
@corex.text("title", default="Plot", section="Text")
@corex.text_area("notes", default="", section="Text")
@corex.number("count", default=2)
@corex.switch("enabled", default=True)
@corex.dropdown("mode", default="Mean", options=OPTIONS)
@corex.slider("factor", default=2.0, minimum=0.0, maximum=10.0, port=True)
@corex.color("accent", default="#336699")
@corex.path("folder", default="", file_filter="All files (*)")
@corex.interval("bounds", default=(0.0, 1.0), minimum=0.0, maximum=2.0)
@corex.list("labels", default=["A"], item_type=str)
def controls(ctx, settings):
    values = settings.to_dict()
    return {"result": values["title"]}
'''

    (declaration,) = discover_plugin_declarations(source)

    assert declaration.control_keys == (
        "title",
        "notes",
        "count",
        "enabled",
        "mode",
        "factor",
        "accent",
        "folder",
        "bounds",
        "labels",
    )
    assert [prop.inline_editor for prop in declaration.spec.properties] == [
        "text",
        "textarea",
        "number",
        "toggle",
        "enum",
        "slider",
        "color",
        "path",
        "interval_slider",
        "list",
    ]
    assert declaration.spec.properties[8].default == Interval1D(0.0, 1.0)
    factor = next(port for port in declaration.spec.ports if port.key == "factor")
    assert factor.uses_property_default


def test_hostile_source_is_never_executed_during_discovery(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    source = f'''
from pathlib import Path
Path({str(marker)!r}).write_text("executed", encoding="utf-8")

@corex.node(id="custom.safe.1234abcd", name="Safe", category=("Tests",))
@corex.output("result")
def safe(ctx):
    return {{"result": True}}
'''

    assert len(discover_plugin_declarations(source, filename="hostile.py")) == 1
    assert not marker.exists()


@pytest.mark.parametrize(
    ("source", "message"),
    (
        (
            '''
@corex.input("value")
@corex.node(id="custom.order.1234abcd", name="Order", category=("Tests",))
def order(ctx, value): return {}
''',
            "first decorator",
        ),
        (
            '''
@corex.node(id="plot.signal", name="Reserved", category=("Tests",))
def reserved(ctx): return {}
''',
            "External node ids",
        ),
        (
            '''
@corex.node(id="custom.unknown.1234abcd", name="Unknown", category=("Tests",))
@corex.mystery("value")
def unknown(ctx): return {}
''',
            "Unknown corex decorator",
        ),
        (
            '''
@corex.node(id="custom.field.1234abcd", name="Field", category=("Tests",), extra=True)
def field(ctx): return {}
''',
            "does not accept 'extra'",
        ),
        (
            '''
def outer():
    @corex.node(id="custom.nested.1234abcd", name="Nested", category=("Tests",))
    def nested(ctx): return {}
''',
            "top-level",
        ),
        (
            '''
class Owner:
    @corex.node(id="custom.method.1234abcd", name="Method", category=("Tests",))
    def method(self, ctx): return {}
''',
            "top-level",
        ),
        (
            '''
generated = corex.node(id="custom.lambda.1234abcd", name="Lambda", category=("Tests",))(lambda ctx: {})
''',
            "Dynamically generated",
        ),
        (
            '''
from corex import node
@node(id="custom.alias.1234abcd", name="Alias", category=("Tests",))
def alias(ctx): return {}
''',
            "aliases are unsupported",
        ),
    ),
)
def test_invalid_declaration_locations_are_actionable(
    source: str,
    message: str,
) -> None:
    with pytest.raises(PluginDeclarationError, match=message) as caught:
        discover_plugin_declarations(source, filename="bad.py")

    assert caught.value.filename == "bad.py"
    assert caught.value.line >= 1
    assert caught.value.column >= 1


def test_plugin_source_requires_an_explicit_unaliased_corex_import() -> None:
    source = '''
@corex.node(id="custom.import.1234abcd", name="Import", category=("Tests",))
def imported(ctx): return {}
'''
    with pytest.raises(PluginDeclarationError, match="import corex"):
        _discover_plugin_declarations(source)


@pytest.mark.parametrize(
    ("signature", "decorators"),
    (
        ("ctx, settings", '@corex.input("value")'),
        ("ctx, value", '@corex.slider("factor", default=1.0, minimum=0.0, maximum=2.0)'),
        ("ctx, second, first", '@corex.input("first")\n@corex.input("second")'),
        ("ctx, value=None", '@corex.input("value")'),
        ("ctx, *, value", '@corex.input("value")'),
    ),
)
def test_signature_must_match_inputs_and_settings_exactly(
    signature: str,
    decorators: str,
) -> None:
    source = f'''
@corex.node(id="custom.signature.1234abcd", name="Signature", category=("Tests",))
{decorators}
def signature({signature}): return {{}}
'''
    with pytest.raises(PluginDeclarationError, match="plain required|exactly"):
        discover_plugin_declarations(source)


def test_duplicate_ids_names_and_cross_direction_keys_reject() -> None:
    duplicate_id = '''
@corex.node(id="custom.duplicate.1234abcd", name="One", category=("Tests",))
def one(ctx): return {}
@corex.node(id="custom.duplicate.1234abcd", name="Two", category=("Tests",))
def two(ctx): return {}
'''
    with pytest.raises(PluginDeclarationError, match="id .* duplicated"):
        discover_plugin_declarations(duplicate_id)

    duplicate_name = '''
@corex.node(id="custom.one.1234abcd", name="One", category=("Tests",))
def same(ctx): return {}
@corex.node(id="custom.two.1234abcd", name="Two", category=("Tests",))
def same(ctx): return {}
'''
    with pytest.raises(PluginDeclarationError, match="function name .* unique"):
        discover_plugin_declarations(duplicate_name)

    collision = '''
@corex.node(id="custom.collision.1234abcd", name="Collision", category=("Tests",))
@corex.input("value")
@corex.output("value")
def collision(ctx, value): return {"value": value}
'''
    with pytest.raises(PluginDeclarationError, match="cross-direction"):
        discover_plugin_declarations(collision)


@pytest.mark.parametrize(
    "shadow",
    (
        "def target(ctx): return {'unsafe': True}",
        "class target: pass",
        "target = lambda ctx: {'unsafe': True}",
        "from math import sin as target",
        "try:\n    raise RuntimeError\nexcept RuntimeError as target:\n    pass",
        "match 1:\n    case target:\n        pass",
        "match {'value': 1}:\n    case {'value': value, **target}:\n        pass",
    ),
)
def test_node_function_symbol_cannot_be_shadowed(shadow: str) -> None:
    source = f'''
@corex.node(id="custom.target.1234abcd", name="Target", category=("Tests",))
def target(ctx): return {{}}
{shadow}
'''
    with pytest.raises(PluginDeclarationError, match="must be unique"):
        discover_plugin_declarations(source)


def test_star_imports_reject_before_they_can_shadow_node_symbols() -> None:
    source = '''
from math import *
@corex.node(id="custom.star.1234abcd", name="Star", category=("Tests",))
def star(ctx): return {}
'''
    with pytest.raises(PluginDeclarationError, match="Star imports"):
        discover_plugin_declarations(source)


def test_nonliteral_constants_calls_and_reserved_names_reject() -> None:
    nonliteral = '''
DEFAULT = make_default()
@corex.node(id="custom.nonliteral.1234abcd", name="Nonliteral", category=("Tests",))
@corex.number("factor", default=DEFAULT)
def nonliteral(ctx, settings): return {}
'''
    with pytest.raises(PluginDeclarationError, match="must be literals"):
        discover_plugin_declarations(nonliteral)

    reserved = '''
@corex.node(id="custom.reserved.1234abcd", name="Reserved", category=("Tests",))
@corex.text("to_dict")
def reserved(ctx, settings): return {}
'''
    with pytest.raises(PluginDeclarationError, match="reserved"):
        discover_plugin_declarations(reserved)


def test_settings_access_is_validated_with_runtime_matching_diagnostics() -> None:
    typo = '''
@corex.node(id="custom.typo.1234abcd", name="Typo", category=("Tests",))
@corex.number("factor", default=2.0)
def typo(ctx, settings):
    return {"value": settings.factro}
'''
    with pytest.raises(PluginDeclarationError) as caught:
        discover_plugin_declarations(typo, filename="typo.py")

    settings = _Settings({"factor": 2.0})
    with pytest.raises(AttributeError) as runtime_error:
        _ = settings.factro
    assert runtime_error.value.args[0] in str(caught.value)
    assert "Did you mean 'factor'?" in str(caught.value)

    introspection = typo.replace("settings.factro", "getattr(settings, 'factor')")
    with pytest.raises(PluginDeclarationError, match="introspection"):
        discover_plugin_declarations(introspection)

    no_controls = '''
@corex.node(id="custom.no_controls.1234abcd", name="No Controls", category=("Tests",))
def no_controls(ctx): return {"value": settings.to_dict()}
'''
    with pytest.raises(PluginDeclarationError, match="only when controls"):
        discover_plugin_declarations(no_controls)


def test_settings_are_deeply_immutable_and_to_dict_is_defensive() -> None:
    authored_sequence = UserList([1, {"value": 2}])
    settings = _Settings(
        {
            "factor": 2.0,
            "nested": {"items": [1, {"value": 2}]},
            "flags": {"a", "b"},
            "sequence": authored_sequence,
        }
    )

    assert settings.factor == 2.0
    assert settings.nested["items"] == (1, {"value": 2})
    assert settings.flags == frozenset({"a", "b"})
    assert settings.sequence == (1, {"value": 2})
    authored_sequence[1]["value"] = 77
    assert settings.sequence[1]["value"] == 2
    with pytest.raises(AttributeError, match="immutable"):
        settings.factor = 3.0
    with pytest.raises(TypeError):
        settings.nested["items"] = ()

    mutable = settings.to_dict()
    mutable["nested"]["items"][1]["value"] = 99
    mutable["flags"].add("c")
    mutable["sequence"][1]["value"] = 88
    assert settings.nested["items"][1]["value"] == 2
    assert settings.flags == frozenset({"a", "b"})
    assert settings.sequence[1]["value"] == 2


def test_builtin_ids_require_explicit_trusted_parser_mode() -> None:
    source = '''
@corex.node(id="plot.signal", name="Signal Plot", category=("Plot",))
def signal(ctx): return {}
'''
    with pytest.raises(PluginDeclarationError, match="External node ids"):
        discover_plugin_declarations(source)

    (declaration,) = discover_plugin_declarations(source, allow_reserved_ids=True)
    assert declaration.spec.type_id == "plot.signal"


def test_source_and_decorator_counts_are_bounded() -> None:
    with pytest.raises(PluginDeclarationError, match="source is too large"):
        discover_plugin_declarations("#" * (256 * 1024 + 1))

    decorators = "\n".join(f'@corex.input("value_{index}")' for index in range(129))
    parameters = ", ".join(f"value_{index}" for index in range(129))
    source = f'''
@corex.node(id="custom.large.1234abcd", name="Large", category=("Tests",))
{decorators}
def large(ctx, {parameters}): return {{}}
'''
    with pytest.raises(PluginDeclarationError, match="too many decorators"):
        discover_plugin_declarations(source)
