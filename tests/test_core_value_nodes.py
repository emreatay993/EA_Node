from __future__ import annotations


import pytest

from ea_node_editor.nodes.builtins.math_interval import (
    DECONSTRUCT_INTERVAL_TYPE_ID,
)
from ea_node_editor.nodes.builtins.core_values import (
    COLOR_DATA_TYPE_ID,
)
from ea_node_editor.nodes.builtins.core_value_nodes import (
    DECONSTRUCT_COLOR_TYPE_ID,
    COREX_CORE_VALUE_NODE_BUNDLE_DESCRIPTORS,
    COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS,
)
from ea_node_editor.nodes.core_data_types import (
    DOUBLE_DATA_TYPE_ID,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
)
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.runtime_contracts import TypedInlineValue































def test_descriptor_shapes_are_exact() -> None:
    interval = COREX_CORE_VALUE_NODE_BUNDLE_DESCRIPTORS[0].spec
    assert (
        interval.type_id,
        interval.display_name,
        interval.category_path,
        interval.properties,
    ) == (
        DECONSTRUCT_INTERVAL_TYPE_ID,
        "Deconstruct Interval",
        ("Math", "Interval"),
        (),
    )
    assert [
        (
            port.key,
            port.direction,
            port.kind,
            port.data_type,
            port.data_access,
            port.required,
        )
        for port in interval.ports
    ] == [
        (
            "interval",
            "in",
            "data",
            INTERVAL_1D_GRAPH_DATA_TYPE_ID,
            "item",
            True,
        ),
        ("start", "out", "data", DOUBLE_DATA_TYPE_ID, "item", None),
        ("end", "out", "data", DOUBLE_DATA_TYPE_ID, "item", None),
    ]

    color = COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS[0].spec
    assert (
        color.type_id,
        color.display_name,
        color.category_path,
        color.properties,
    ) == (
        DECONSTRUCT_COLOR_TYPE_ID,
        "Deconstruct Color",
        ("Utilities", "Color"),
        (),
    )
    assert [
        (
            port.key,
            port.direction,
            port.kind,
            port.data_type,
            port.data_access,
            port.required,
        )
        for port in color.ports
    ] == [
        ("color", "in", "data", COLOR_DATA_TYPE_ID, "item", True),
        ("red", "out", "data", DOUBLE_DATA_TYPE_ID, "item", None),
        ("green", "out", "data", DOUBLE_DATA_TYPE_ID, "item", None),
        ("blue", "out", "data", DOUBLE_DATA_TYPE_ID, "item", None),
        ("alpha", "out", "data", DOUBLE_DATA_TYPE_ID, "item", None),
    ]


def test_color_execution_preserves_finite_channels_without_reinterpretation() -> None:
    value = TypedInlineValue(
        COLOR_DATA_TYPE_ID,
        1,
        {
            "R": -0.25,
            "G": 0.125,
            "B": 1.25,
            "A": 0.75,
            "IsValid": False,
        },
    )
    plugin = COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS[0].factory()
    result = plugin.execute(
        ExecutionContext(
            run_id="run",
            node_id="node",
            workspace_id="workspace",
            inputs={"color": value},
            properties={},
            emit_log=lambda _level, _message: None,
        )
    )
    assert result.outputs == {
        "red": -0.25,
        "green": 0.125,
        "blue": 1.25,
        "alpha": 0.75,
    }


@pytest.mark.parametrize(
    "value",
    (
        {"R": 0.0, "G": 0.0, "B": 0.0, "A": 1.0, "IsValid": True},
        TypedInlineValue(
            DOUBLE_DATA_TYPE_ID,
            1,
            {"R": 0.0, "G": 0.0, "B": 0.0, "A": 1.0, "IsValid": True},
        ),
        TypedInlineValue(
            COLOR_DATA_TYPE_ID,
            2,
            {"R": 0.0, "G": 0.0, "B": 0.0, "A": 1.0, "IsValid": True},
        ),
        TypedInlineValue(
            COLOR_DATA_TYPE_ID,
            1,
            {"R": 0.0, "G": 0.0, "B": "0", "A": 1.0, "IsValid": True},
        ),
    ),
    ids=("carrier", "type", "schema", "payload"),
)
def test_color_execution_rejects_invalid_typed_values(value: object) -> None:
    plugin = COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS[0].factory()
    with pytest.raises(ValueError, match="^Color input is invalid$"):
        plugin.execute(
            ExecutionContext(
                run_id="run",
                node_id="node",
                workspace_id="workspace",
                inputs={"color": value},
                properties={},
                emit_log=lambda _level, _message: None,
            )
        )
