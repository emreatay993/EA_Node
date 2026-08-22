from __future__ import annotations

import pytest

from ea_node_editor.nodes.bootstrap import build_builtin_registry, build_default_registry
from ea_node_editor.nodes.builtins.core import (
    DEFAULT_PYTHON_SCRIPT_INPUT_NAMES,
    DEFAULT_PYTHON_SCRIPT_OUTPUT_NAMES,
    DEFAULT_STREAM_GATE_OUTPUT_IDS,
    PYTHON_SCRIPT_DEFAULT_SOURCE,
    PYTHON_SCRIPT_INPUT_NAMES_PROPERTY,
    PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY,
    STREAM_GATE_OUTPUT_IDS_PROPERTY,
    IfNodePlugin,
    PythonScriptNodePlugin,
    StreamGateNodePlugin,
    TriggerNodePlugin,
    normalize_stream_gate_output_ids,
    stream_gate_index,
)
from ea_node_editor.nodes.builtins.icon_catalog import BUILTIN_NODE_ICONS
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.subnode_contract import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_DATA_ACCESS_PROPERTY,
    SUBNODE_PIN_DATA_ACCESS_VALUES,
)
from ea_node_editor.graph.validated_mutation import ValidatedGraphMutation
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.nodes.registry import resolve_instance_ports
from ea_node_editor.runtime_contracts import DataTree


def _context(
    *,
    inputs: dict[str, object] | None = None,
    properties: dict[str, object] | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        run_id="run",
        node_id="node",
        workspace_id="workspace",
        inputs=dict(inputs or {}),
        properties=dict(properties or {}),
        emit_log=lambda _level, _message: None,
    )


def test_builtin_catalog_contains_only_data_and_passive_flow_ports() -> None:
    registry = build_builtin_registry()
    specs = registry.all_specs()
    type_ids = {spec.type_id for spec in specs}

    assert {"core.trigger", "core.if", "core.stream_gate"} <= type_ids
    retired = {"core.start", "core.end", "core.branch", "core.on_failure", "hpc.on_status"}
    assert not retired & type_ids
    assert not retired & set(BUILTIN_NODE_ICONS)
    assert "core.trigger" not in BUILTIN_NODE_ICONS
    assert {port.kind for spec in specs for port in spec.ports} <= {"data", "flow"}


def test_full_default_registry_has_no_control_ports_or_active_multi_connection_flags() -> None:
    specs = build_default_registry().all_specs()
    ports = tuple(port for spec in specs for port in spec.ports)

    assert {port.kind for port in ports} <= {"data", "flow"}
    assert all(not port.allow_multiple_connections or port.kind == "flow" for port in ports)


def test_trigger_is_iconless_compact_tree_boundary() -> None:
    plugin = TriggerNodePlugin()
    spec = plugin.spec()
    ports = {port.key: port for port in spec.ports}

    assert spec.icon == ""
    assert spec.collapsible is False
    assert spec.surface_variant == "trigger"
    assert ports["input"].data_access == "tree"
    assert ports["input"].required is False
    assert ports["output"].data_access == "tree"

    unconnected = plugin.execute(_context()).outputs["output"]
    assert unconnected == DataTree.from_item(True)
    tree = DataTree({(2,): ("latest",)})
    assert plugin.execute(_context(inputs={"input": tree})).outputs == {"output": tree}


def test_subnode_pin_descriptors_publish_hidden_data_access_metadata() -> None:
    registry = build_builtin_registry()

    for type_id in (SUBNODE_INPUT_TYPE_ID, SUBNODE_OUTPUT_TYPE_ID):
        spec = registry.get_spec(type_id)
        properties = {prop.key: prop for prop in spec.properties}
        access = properties[SUBNODE_PIN_DATA_ACCESS_PROPERTY]
        assert access.type == "enum"
        assert access.default == "item"
        assert access.enum_values == SUBNODE_PIN_DATA_ACCESS_VALUES
        assert access.inspector_visible is False


def test_if_selects_tree_and_omits_absent_optional_branch() -> None:
    plugin = IfNodePlugin()
    ports = {port.key: port for port in plugin.spec().ports}
    assert ports["condition"].data_access == "item"
    assert ports["true_value"].data_access == "tree"
    assert ports["false_value"].data_access == "tree"
    assert ports["result"].data_access == "tree"

    true_tree = DataTree({(0,): (1, 2)})
    false_tree = DataTree({(1,): (3,)})
    assert plugin.execute(
        _context(inputs={"condition": True, "true_value": true_tree, "false_value": false_tree})
    ).outputs == {"result": true_tree}
    assert plugin.execute(
        _context(inputs={"condition": False, "true_value": true_tree})
    ).outputs == {}


def test_python_script_declares_normalized_named_dynamic_ports() -> None:
    registry = build_builtin_registry()
    spec = registry.get_spec("core.python_script")
    properties = {prop.key: prop for prop in spec.properties}

    assert spec.ports == ()
    assert properties[PYTHON_SCRIPT_INPUT_NAMES_PROPERTY].default == list(
        DEFAULT_PYTHON_SCRIPT_INPUT_NAMES
    )
    assert properties[PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY].default == list(
        DEFAULT_PYTHON_SCRIPT_OUTPUT_NAMES
    )
    assert properties[PYTHON_SCRIPT_INPUT_NAMES_PROPERTY].inspector_visible is False
    assert properties[PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY].inspector_visible is False
    assert PYTHON_SCRIPT_DEFAULT_SOURCE == "result = payload\n"
    assert [
        (
            group.group_id,
            group.property_key,
            group.direction,
            group.minimum,
            group.maximum,
            group.rename_mode,
        )
        for group in spec.dynamic_port_groups
    ] == [
        ("inputs", PYTHON_SCRIPT_INPUT_NAMES_PROPERTY, "in", 0, None, "key"),
        ("outputs", PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY, "out", 0, None, "key"),
    ]

    defaults = registry.default_properties("core.python_script")
    assert defaults[PYTHON_SCRIPT_INPUT_NAMES_PROPERTY] == ["payload"]
    assert defaults[PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY] == ["result"]
    assert [port.key for port in resolve_instance_ports(spec, defaults)] == [
        "payload",
        "result",
    ]

    explicit_empty = registry.normalize_properties(
        "core.python_script",
        {
            PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: [],
            PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: [],
        },
    )
    assert explicit_empty[PYTHON_SCRIPT_INPUT_NAMES_PROPERTY] == []
    assert explicit_empty[PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY] == []
    assert resolve_instance_ports(spec, explicit_empty) == ()

    non_lists = registry.normalize_properties(
        "core.python_script",
        {
            PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: {"not": "a list"},
            PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: "not a list",
        },
    )
    assert non_lists[PYTHON_SCRIPT_INPUT_NAMES_PROPERTY] == ["payload"]
    assert non_lists[PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY] == ["result"]

    normalized = registry.normalize_properties(
        "core.python_script",
        {
            PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: [
                " payload ",
                "Δ",
                "Case",
                "case",
                "for",
                "ctx",
                "__builtins__",
                "Δ",
                3,
                "bad-name",
                "result",
            ],
            PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: [
                " result ",
                "Case",
                "RESULT",
                "for",
                "ctx",
                "__builtins__",
                "RESULT",
                None,
                "out value",
                "Δ",
            ],
        },
    )
    assert normalized[PYTHON_SCRIPT_INPUT_NAMES_PROPERTY] == [
        "payload",
        "Δ",
        "Case",
        "case",
        "result",
    ]
    assert normalized[PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY] == ["RESULT"]
    resolved = resolve_instance_ports(spec, normalized)
    assert [port.key for port in resolved] == [
        "payload",
        "Δ",
        "Case",
        "case",
        "result",
        "RESULT",
    ]
    assert all(port.label == port.key for port in resolved)
    assert all(port.exposed and port.data_access == "item" for port in resolved)
    assert all(port.required is False for port in resolved if port.direction == "in")


def test_python_script_graph_mutations_use_node_owned_names() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    node = mutations.add_node(
        type_id="core.python_script",
        title="Script",
        x=0,
        y=0,
        properties={
            PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: ["input1", "output1"],
            PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: ["input2", "result"],
        },
    )

    assert mutations.insert_dynamic_port(node.node_id, "inputs", 2) == "input3"
    assert mutations.insert_dynamic_port(node.node_id, "outputs", 2) == "output2"
    assert mutations.rename_dynamic_port(
        node.node_id,
        "inputs",
        "input3",
        " Δelta ",
    ) == ("Δelta", ())
    with pytest.raises(ValueError, match="key rename failed"):
        mutations.rename_dynamic_port(node.node_id, "outputs", "output2", "Δelta")
    with pytest.raises(ValueError, match="key rename failed"):
        mutations.rename_dynamic_port(node.node_id, "outputs", "output2", "for")


def test_python_script_executes_declared_variables_in_one_scope() -> None:
    plugin = PythonScriptNodePlugin()
    assert plugin.execute(
        _context(
            inputs={"payload": "default"},
            properties={"script": PYTHON_SCRIPT_DEFAULT_SOURCE},
        )
    ).outputs == {"result": "default"}

    properties = {
        "script": (
            "def scale(value):\n"
            "    return [value * factor for factor in range(3)]\n"
            "result = scale(payload)\n"
            "explicit_none = None\n"
            "ignored = 'local only'\n"
        ),
        PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: ["payload"],
        PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: [
            "result",
            "explicit_none",
            "unassigned",
        ],
    }
    assert plugin.execute(
        _context(inputs={"payload": 4}, properties=properties)
    ).outputs == {
        "result": [0, 4, 8],
        "explicit_none": None,
    }
    assert plugin.execute(
        _context(
            properties={
                "script": "result = 40 + 2",
                PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: [],
                PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: ["result"],
            }
        )
    ).outputs == {"result": 42}
    assert plugin.execute(
        _context(
            properties={
                "script": "result = ('input_data' in globals(), 'output_data' in globals())",
                PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: [],
                PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: ["result"],
            }
        )
    ).outputs == {"result": (False, False)}
    assert plugin.execute(
        _context(
            properties={
                "script": "ignored = 1",
                PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: [],
                PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: [],
            }
        )
    ).outputs == {}
    assert plugin.execute(
        _context(
            properties={
                "script": " \n\t",
                PYTHON_SCRIPT_INPUT_NAMES_PROPERTY: ["payload"],
                PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY: ["result"],
            }
        )
    ).outputs == {}


def test_stream_gate_uses_stable_output_ids_and_publishes_only_selected_tree() -> None:
    plugin = StreamGateNodePlugin()
    spec = plugin.spec()
    properties = {prop.key: prop for prop in spec.properties}
    ports = {
        port.key: port
        for port in resolve_instance_ports(
            spec,
            {STREAM_GATE_OUTPUT_IDS_PROPERTY: properties[STREAM_GATE_OUTPUT_IDS_PROPERTY].default},
        )
    }

    assert tuple(port_id for port_id in DEFAULT_STREAM_GATE_OUTPUT_IDS) == ("output_0", "output_1")
    assert properties[STREAM_GATE_OUTPUT_IDS_PROPERTY].default == ["output_0", "output_1"]
    assert properties[STREAM_GATE_OUTPUT_IDS_PROPERTY].inspector_visible is False
    assert tuple(port.key for port in spec.ports) == ("stream", "gate")
    assert len(spec.dynamic_port_groups) == 1
    group = spec.dynamic_port_groups[0]
    assert (group.group_id, group.property_key, group.direction) == (
        "outputs",
        STREAM_GATE_OUTPUT_IDS_PROPERTY,
        "out",
    )
    assert group.minimum == 1
    assert group.maximum is None
    assert group.rename_mode == "label"
    assert ports["stream"].data_access == "tree"
    assert ports["gate"].data_access == "item"
    assert ports["output_0"].data_access == "tree"
    assert ports["output_1"].data_access == "tree"
    assert ports["output_0"].label == "Output 0"
    assert ports["output_1"].label == "Output 1"
    assert normalize_stream_gate_output_ids(None) == DEFAULT_STREAM_GATE_OUTPUT_IDS
    assert normalize_stream_gate_output_ids(("only",)) == DEFAULT_STREAM_GATE_OUTPUT_IDS
    assert normalize_stream_gate_output_ids([]) == DEFAULT_STREAM_GATE_OUTPUT_IDS
    assert normalize_stream_gate_output_ids(["  "]) == DEFAULT_STREAM_GATE_OUTPUT_IDS
    assert normalize_stream_gate_output_ids(["only"]) == ("only",)

    tree = DataTree({(3, 2): ("value",)})
    result = plugin.execute(
        _context(
            inputs={"stream": tree, "gate": 1.5},
            properties={STREAM_GATE_OUTPUT_IDS_PROPERTY: ["stable-a", "stable-b", "stable-c"]},
        )
    )
    assert result.outputs == {"stable-c": tree}


@pytest.mark.parametrize(
    ("value", "expected"),
    ((0.49, 0), (0.5, 1), (1.5, 2), (-0.49, 0), (-0.5, -1), (-1.5, -2)),
)
def test_stream_gate_rounds_midpoints_away_from_zero(value: float, expected: int) -> None:
    assert stream_gate_index(value) == expected


@pytest.mark.parametrize("value", (True, False, float("inf"), float("nan"), "1", "not-a-number"))
def test_stream_gate_rejects_non_numeric_or_non_finite_gate(value: object) -> None:
    with pytest.raises(ValueError):
        stream_gate_index(value)


def test_stream_gate_fails_for_out_of_range_output() -> None:
    with pytest.raises(ValueError, match="outside 0..1"):
        StreamGateNodePlugin().execute(
            _context(inputs={"stream": DataTree.from_item("value"), "gate": -0.5})
        )
