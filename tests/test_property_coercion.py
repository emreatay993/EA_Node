from __future__ import annotations

import pytest

from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec
from ea_node_editor.nodes.property_coercion import coerce_property_value
from ea_node_editor.nodes.property_normalization import normalize_property_value
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.spec_validation import validate_node_spec


def test_invalid_enum_default_raises_exact_value_error() -> None:
    spec = NodeTypeSpec(
        type_id="tests.bad_enum",
        display_name="Bad Enum",
        category_path=("Tests",),
        icon="",
        ports=(PortSpec("value", "out", "data", "COREX.DataTypes.Any"),),
        properties=(
            PropertySpec(
                "level",
                "enum",
                "fatal",
                "Level",
                enum_values=("info", "warning", "error"),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"^Invalid default for property level \(enum\): 'fatal'$",
    ):
        validate_node_spec(spec, data_types=NodeRegistry().data_types)


def test_non_serializable_json_default_rejects_opaque_state_at_capture() -> None:
    with pytest.raises(TypeError, match=r"^Unsupported property default type: object$"):
        PropertySpec("payload", "json", {"obj": object()}, "Payload")


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        ('"C:\\media\\shot.png"', "C:\\media\\shot.png"),
        ("'C:\\media\\shot.png'", "C:\\media\\shot.png"),
        ('  "C:\\media\\shot.png"  ', "C:\\media\\shot.png"),
        ("C:\\media\\shot.png", "C:\\media\\shot.png"),
        ('"C:\\media\\shot.png', '"C:\\media\\shot.png'),
        ("", ""),
    ],
)
def test_path_property_accepts_windows_copy_as_path_quoting(
    written: str,
    expected: str,
) -> None:
    prop = PropertySpec("source", "path", "", "Source", inline_editor="path")

    assert coerce_property_value(prop, written, strict=False) == expected


def test_str_property_keeps_quotes_that_path_property_strips() -> None:
    prop = PropertySpec("label", "str", "", "Label")

    assert coerce_property_value(prop, '"quoted"', strict=False) == '"quoted"'


def test_registry_normalizes_quoted_media_panel_source() -> None:
    spec = NodeTypeSpec(
        type_id="tests.quoted_path",
        display_name="Quoted Path",
        category_path=("Tests",),
        icon="",
        ports=(PortSpec("value", "out", "data", "COREX.DataTypes.Any"),),
        properties=(PropertySpec("source", "path", "", "Source", inline_editor="path"),),
    )
    normalized = normalize_property_value(
        spec,
        "source",
        '"C:\\media\\report.pdf"',
        properties=None,
        data_types=NodeRegistry().data_types,
    )

    assert normalized == "C:\\media\\report.pdf"
