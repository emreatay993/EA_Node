# Purpose: Verify graph-owned node reconciliation and mutation contracts.
# Map: subsystems/graph_domain.md
# Tests: this file
from __future__ import annotations

from dataclasses import replace

import pytest

from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.node_port_state import reconcile_script_port_state
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.graph.validated_mutation import ValidatedGraphMutation
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.node_specs import PortSpec
from ea_node_editor.nodes.python_script_declaration import PythonScriptDeclarationError
from ea_node_editor.nodes.spec_validation import validate_node_spec
from tests.graph_mutation_fixtures import dynamic_registry as _registry


def test_canvas_port_handles_edit_declarations_and_signature_without_rewriting_body() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    mutations = ValidatedGraphMutation(model, model.active_workspace.workspace_id, registry)
    source = '''# Keep café and formatting.
@corex.node
@corex.input("payload", value_type=float, required=True, section="Data")  # keep me
@corex.output("result", value_type=float)
@corex.slider("scale", default=2.0, minimum=0.0, maximum=5.0, port=True, section="Style")
def run(ctx, payload: float, scale,):  # signature comment
    # Keep this logic even when an interface change needs a manual body edit.
    return {"result": payload * scale}
'''
    node = mutations.add_node(type_id="core.python_script", title="Script", x=0, y=0,
                              properties={"script": source})
    mutations.set_node_property(node.node_id, "scale", 3.0)
    before_spec = registry.resolve_spec(node.type_id, node.properties)
    assert [group.group_id for group in before_spec.dynamic_port_groups] == ["inputs", "outputs"]
    assert mutations.insert_dynamic_port(node.node_id, "inputs", 0) == "input1"
    assert mutations.insert_dynamic_port(node.node_id, "outputs", 1) == "output1"
    edited = node.properties["script"]
    assert '@corex.input("input1", value_type=corex.Any)' in edited
    assert '@corex.output("output1", value_type=corex.Any)' in edited
    assert 'def run(ctx, payload: float, scale, input1,):  # signature comment' in edited
    assert source.split("    # Keep this logic", 1)[1] == edited.split("    # Keep this logic", 1)[1]
    assert node.properties["scale"] == 3.0
    assert registry.resolve_spec(node.type_id, node.properties).settings_groups == before_spec.settings_groups
    mutations.remove_dynamic_port(node.node_id, "inputs", "input1")
    mutations.remove_dynamic_port(node.node_id, "outputs", "output1")
    mutations.remove_dynamic_port(node.node_id, "inputs", "payload")
    assert '@corex.input("payload"' not in node.properties["script"]
    assert 'return {"result": payload * scale}' in node.properties["script"]
    assert set(node.properties) == {"script", "timeout_sec", "scale"}


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_canvas_port_source_spans_preserve_multiline_unicode_and_parentheses(newline: str) -> None:
    source = '''# café
@corex.node
@(
    corex.input("payload", value_type=float, label="é")
)  # retain trailing comment
@(corex.output("result", value_type=float))
@corex.number("input1", default=2)
def run(
    ctx,
    payload: "é", # retain parameter comment, too
    input1,
):
    return {"result": payload * input1}
'''.replace("\n", newline)
    registry = build_builtin_registry()
    model = GraphModel()
    mutation = ValidatedGraphMutation(model, model.active_workspace.workspace_id, registry)
    node = mutation.add_node(type_id="core.python_script", title="Script", x=0, y=0,
                             properties={"script": source})
    assert mutation.insert_dynamic_port(node.node_id, "inputs", 0) == "input2"
    mutation.remove_dynamic_port(node.node_id, "inputs", "payload")
    mutation.remove_dynamic_port(node.node_id, "outputs", "result")
    updated = node.properties["script"]
    assert "# retain trailing comment" in updated
    assert "# retain parameter comment, too" in updated
    assert f'    return {{"result": payload * input1}}{newline}' in updated
    assert 'value_type=float' not in updated
    assert [port.key for port in registry.resolve_spec(node.type_id, node.properties).ports] == ["input2"]


def test_source_backed_group_validation_and_mutations_keep_backing_write_guards() -> None:
    registry = build_builtin_registry().fork()
    properties = registry.default_properties("core.python_script")
    spec = registry.resolve_spec("core.python_script", properties)
    group = spec.dynamic_port_groups[0]
    port = spec.ports[0]
    bad_group = replace(group, ports_resolver=lambda _properties: (port, port))
    with pytest.raises(ValueError, match="duplicate port key"):
        validate_node_spec(replace(spec, dynamic_port_groups=(bad_group,)), data_types=registry.data_types)
    bad_group = replace(group, property_editor="untrusted")
    with pytest.raises(TypeError, match="must be callable"):
        validate_node_spec(replace(spec, dynamic_port_groups=(bad_group,)), data_types=registry.data_types)

    base = registry.get_spec("core.python_script")
    custom = replace(spec, type_id="tests.source_backed", instance_spec_resolver=base.instance_spec_resolver)
    registry.register_descriptor(custom, lambda: None)
    registry.freeze()
    model = GraphModel()
    mutation = ValidatedGraphMutation(model, model.active_workspace.workspace_id, registry)
    node = mutation.add_node(type_id=custom.type_id, title="Source", x=0, y=0, properties=properties)
    with pytest.raises(ValueError, match="only through dynamic port mutations"):
        mutation.set_node_property(node.node_id, "script", properties["script"])
    assert mutation.insert_dynamic_port(node.node_id, "inputs", 0) == "input1"
    assert mutation.remove_dynamic_port(node.node_id, "inputs", "input1") == ("input1", ())
    assert [p.key for p in registry.resolve_spec(node.type_id, node.properties).ports] == ["payload", "result"]


def test_numeric_overflow_is_line_aware_and_apply_is_atomic() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    node = mutations.add_node(
        type_id="core.python_script", title="Script", x=0.0, y=0.0
    )
    before = node.clone()
    huge = "9" * 400
    source = f"""@corex.node
@corex.slider("scale", default={huge}, minimum=0.0, maximum=1.0)
def run(ctx, scale):
    return {{}}
"""

    with pytest.raises(PythonScriptDeclarationError, match="line") as caught:
        mutations.apply_python_script(node.node_id, source)

    assert "column" in str(caught.value)
    assert node == before


def test_apply_is_atomic_and_reconciles_values_wires_and_structure() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    source_node = mutations.add_node(
        type_id="core.python_script", title="Source", x=0.0, y=0.0
    )
    target_node = mutations.add_node(
        type_id="core.python_script", title="Target", x=300.0, y=0.0
    )
    edge = mutations.add_edge(
        source_node_id=source_node.node_id,
        source_port_key="result",
        target_node_id=target_node.node_id,
        target_port_key="payload",
    )
    item_source = """@corex.node
@corex.input("payload", value_type=corex.Any)
@corex.output("result", value_type=corex.Any)
@corex.slider("scale", default=2.0, minimum=0.5, maximum=8.0, step=0.5, section="Style")
def run(ctx, payload, scale):
    return {"result": payload}
"""
    assert mutations.apply_python_script(target_node.node_id, item_source) == ((), ())
    assert edge.edge_id in workspace.edges
    mutations.set_node_property(target_node.node_id, "scale", 7.0)

    narrowed_source = item_source.replace("maximum=8.0", "maximum=5.0")
    reset_keys, removed_edge_ids = mutations.apply_python_script(
        target_node.node_id,
        narrowed_source,
    )
    assert reset_keys == ("scale",)
    assert removed_edge_ids == ()
    assert target_node.properties["scale"] == 2.0

    before_node = target_node.clone()
    before_edges = dict(workspace.edges)
    with pytest.raises(PythonScriptDeclarationError):
        mutations.apply_python_script(target_node.node_id, "@corex.node\ndef run(")
    assert target_node == before_node
    assert workspace.edges == before_edges

    tree_source = narrowed_source.replace(
        '@corex.input("payload", value_type=corex.Any)',
        '@corex.input("payload", value_type=corex.Any, structure="tree")',
    )
    assert mutations.set_port_modifiers(target_node.node_id, "payload", ("graft",))
    assert mutations.set_principal_input_port(target_node.node_id, "payload")
    before_node = target_node.clone()
    before_edges = dict(workspace.edges)
    with pytest.raises(ValueError, match="cannot be mixed"):
        mutations.set_node_properties(
            target_node.node_id,
            {"script": tree_source, "scale": 3.0},
        )
    assert target_node == before_node
    assert workspace.edges == before_edges

    assert mutations.set_node_properties(
        target_node.node_id,
        {"script": tree_source},
    ) == {"script": tree_source}
    removed_edge_ids = tuple(set(before_edges) - set(workspace.edges))
    assert removed_edge_ids == (edge.edge_id,)
    assert edge.edge_id not in workspace.edges
    assert target_node.port_modifiers == {}
    assert target_node.principal_input_port_id is None


def test_dynamic_port_insert_remove_is_ordered_and_cleans_all_incident_state() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)
    gate = mutations.add_node(type_id="core.stream_gate", title="Gate", x=0, y=0)
    sink_a = mutations.add_node(type_id="tests.sink", title="Sink A", x=200, y=0)
    sink_b = mutations.add_node(type_id="tests.sink", title="Sink B", x=200, y=100)

    inserted = mutations.insert_dynamic_port(gate.node_id, "outputs", 1)
    assert inserted == "output_2"
    assert gate.properties["output_port_ids"] == ["output_0", inserted, "output_1"]
    enabled_edge = mutations.add_edge(
        source_node_id=gate.node_id,
        source_port_key=inserted,
        target_node_id=sink_a.node_id,
        target_port_key="value",
    )
    disabled_edge = mutations.add_edge(
        source_node_id=gate.node_id,
        source_port_key=inserted,
        target_node_id=sink_b.node_id,
        target_port_key="value",
    )
    assert mutations.set_edge_enabled(disabled_edge.edge_id, False)
    gate.exposed_ports[inserted] = False
    gate.port_labels[inserted] = "Temporary"
    gate.port_modifiers[inserted] = ("graft",)

    removed, removed_edges = mutations.remove_dynamic_port(
        gate.node_id,
        "outputs",
        inserted,
    )

    assert removed == inserted
    assert removed_edges == (enabled_edge.edge_id, disabled_edge.edge_id)
    assert not set(removed_edges).intersection(workspace.edges)
    assert gate.properties["output_port_ids"] == ["output_0", "output_1"]
    assert inserted not in gate.exposed_ports
    assert inserted not in gate.port_labels
    assert inserted not in gate.port_modifiers


def test_dynamic_port_label_rename_preserves_identity_wires_and_can_clear() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)
    gate = mutations.add_node(type_id="core.stream_gate", title="Gate", x=0, y=0)
    sink = mutations.add_node(type_id="tests.sink", title="Sink", x=200, y=0)
    edge = mutations.add_edge(
        source_node_id=gate.node_id,
        source_port_key="output_0",
        target_node_id=sink.node_id,
        target_port_key="value",
    )

    assert mutations.set_port_label(
        gate.node_id,
        "output_0",
        "Direct",
    )
    assert gate.port_labels["output_0"] == "Direct"
    assert mutations.rename_dynamic_port(
        gate.node_id,
        "outputs",
        "output_0",
        "Accepted",
    ) == ("output_0", ())
    assert gate.properties["output_port_ids"] == ["output_0", "output_1"]
    assert gate.port_labels["output_0"] == "Accepted"
    assert edge.edge_id in workspace.edges
    assert mutations.rename_dynamic_port(
        gate.node_id,
        "outputs",
        "output_0",
        "Accepted",
    ) is None
    assert mutations.rename_dynamic_port(
        gate.node_id,
        "outputs",
        "output_0",
        "",
    ) == ("output_0", ())
    assert "output_0" not in gate.port_labels


def test_key_rename_prunes_wires_and_old_sparse_state_without_transfer() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)
    source = mutations.add_node(type_id="tests.source", title="Source", x=0, y=0)
    dynamic = mutations.add_node(
        type_id="tests.dynamic_inputs",
        title="Dynamic",
        x=200,
        y=0,
    )
    edge = mutations.add_edge(
        source_node_id=source.node_id,
        source_port_key="value",
        target_node_id=dynamic.node_id,
        target_port_key="alpha",
    )
    dynamic.exposed_ports["alpha"] = False
    dynamic.port_labels["alpha"] = "Ignored"
    dynamic.port_modifiers["alpha"] = ("graft",)
    dynamic.principal_input_port_id = "alpha"

    renamed, removed_edges = mutations.rename_dynamic_port(
        dynamic.node_id,
        "inputs",
        "alpha",
        "gamma",
    )

    assert renamed == "gamma"
    assert removed_edges == (edge.edge_id,)
    assert dynamic.properties["input_names"] == ["gamma", "beta"]
    assert edge.edge_id not in workspace.edges
    assert "alpha" not in dynamic.exposed_ports
    assert "alpha" not in dynamic.port_labels
    assert "alpha" not in dynamic.port_modifiers
    assert dynamic.principal_input_port_id is None
    assert "gamma" not in dynamic.exposed_ports
    assert "gamma" not in dynamic.port_labels
    assert "gamma" not in dynamic.port_modifiers
    spec = registry.get_spec(dynamic.type_id)
    gamma = next(
        port
        for port in effective_ports(
            node=dynamic,
            spec=spec,
            workspace_nodes=workspace.nodes,
        )
        if port.key == "gamma"
    )
    assert gamma.label == "Variable gamma"


def test_dynamic_port_preflight_rejects_collisions_limits_and_backing_writes_atomically() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)
    dynamic = mutations.add_node(
        type_id="tests.dynamic_inputs",
        title="Dynamic",
        x=0,
        y=0,
    )
    inserted = mutations.insert_dynamic_port(dynamic.node_id, "inputs", 1)
    assert inserted == "input1"
    assert dynamic.properties["input_names"] == ["alpha", "input1", "beta"]
    before = dict(dynamic.properties)
    with pytest.raises(ValueError, match="already exists"):
        mutations.rename_dynamic_port(dynamic.node_id, "inputs", "alpha", "beta")
    assert dynamic.properties == before
    with pytest.raises(IndexError):
        mutations.insert_dynamic_port(dynamic.node_id, "inputs", 99)
    assert dynamic.properties == before
    with pytest.raises(ValueError, match="backing properties"):
        mutations.set_node_property(dynamic.node_id, "input_names", ["changed"])
    with pytest.raises(ValueError, match="backing properties"):
        mutations.set_node_properties(
            dynamic.node_id,
            {"mode": "changed", "input_names": ["changed"]},
        )
    assert dynamic.properties == before

    colliding = mutations.add_node(
        type_id="tests.dynamic_collision",
        title="Collision",
        x=0,
        y=100,
    )
    collision_before = dict(colliding.properties)
    with pytest.raises(ValueError, match="already exists"):
        mutations.insert_dynamic_port(colliding.node_id, "inputs", 1)
    assert colliding.properties == collision_before

    one_output = mutations.add_node(
        type_id="core.stream_gate",
        title="One",
        x=0,
        y=200,
        properties={"output_port_ids": ["only"]},
    )
    with pytest.raises(ValueError, match="retain at least 1"):
        mutations.remove_dynamic_port(one_output.node_id, "outputs", "only")
    assert one_output.properties["output_port_ids"] == ["only"]


def test_dynamic_port_key_rename_snapshot_restore_restores_exact_state() -> None:
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = model.validated_mutations(workspace.workspace_id, registry)
    source = mutations.add_node(type_id="tests.source", title="Source", x=0, y=0)
    dynamic = mutations.add_node(
        type_id="tests.dynamic_inputs",
        title="Dynamic",
        x=200,
        y=0,
    )
    edge = mutations.add_edge(
        source_node_id=source.node_id,
        source_port_key="value",
        target_node_id=dynamic.node_id,
        target_port_key="alpha",
    )
    dynamic.exposed_ports["alpha"] = True
    mutations.set_port_modifiers(dynamic.node_id, "alpha", ["graft"])
    mutations.set_principal_input_port(dynamic.node_id, "alpha")
    before = workspace.capture_snapshot()

    assert mutations.rename_dynamic_port(
        dynamic.node_id,
        "inputs",
        "alpha",
        "gamma",
    ) == ("gamma", (edge.edge_id,))
    assert dynamic.properties["input_names"] == ["gamma", "beta"]
    assert edge.edge_id not in workspace.edges
    assert "alpha" not in dynamic.exposed_ports
    assert "alpha" not in dynamic.port_modifiers
    assert dynamic.principal_input_port_id is None

    workspace.restore_snapshot(before)
    restored = workspace.nodes[dynamic.node_id]
    assert workspace.capture_snapshot() == before
    assert restored.properties["input_names"] == ["alpha", "beta"]
    assert restored.exposed_ports["alpha"] is True
    assert restored.port_modifiers == {"alpha": ("graft",)}
    assert restored.principal_input_port_id == "alpha"
    assert workspace.edges[edge.edge_id].target_port_key == "alpha"


def test_script_apply_preserves_instance_order_but_registry_load_canonicalizes_it(tmp_path):
    from ea_node_editor.graph.model import GraphModel
    from ea_node_editor.graph.registry_normalization import (
        normalize_project_for_registry,
    )

    source = '''@corex.node
@corex.input("payload", value_type=float, section="Data")
@corex.output("result", value_type=float)
@corex.number("gain", default=1.0, section="Style")
def run(ctx, payload, gain):
    return {"result": payload * gain}
'''
    registry = build_builtin_registry(generation_root=tmp_path / "plugin_generations")
    model = GraphModel()
    mutations = model.validated_mutations(model.active_workspace.workspace_id, registry)
    node = mutations.add_node(type_id="core.python_script", title="Script", x=0, y=0, properties={"script": source})
    spec = registry.resolve_spec(node.type_id, node.properties)
    declared_order = tuple(group.group_id for group in spec.settings_groups)
    assert len(declared_order) == 2
    instance_order = tuple(reversed(declared_order))
    node.expanded_settings_group_ids = instance_order + ("obsolete",)
    node.port_modifiers = {"payload": ("clean", "graft", "clean"), "result": ()}
    node.principal_input_port_id = "payload"
    mutations.apply_python_script(node.node_id, source + "# Body-only edit\n")
    assert node.expanded_settings_group_ids == instance_order
    assert node.port_modifiers == {"payload": ("clean", "graft", "clean"), "result": ()}
    assert node.principal_input_port_id == "payload"
    normalize_project_for_registry(model.project, registry)
    assert node.expanded_settings_group_ids == declared_order
    assert node.port_modifiers == {"payload": ("graft", "clean")}
    assert node.principal_input_port_id == "payload"


def test_script_port_projection_preserves_authored_order_and_detaches_state() -> None:
    node = NodeInstance(
        node_id="script", type_id="core.python_script", title="Script", x=0, y=0,
        exposed_ports={"payload": False, "required": False, "removed": True},
        port_labels={"payload": "Alias", "required": "Old", "removed": "Old"},
        port_modifiers={"payload": ("clean", "graft", "clean"), "required": ("graft",), "result": ()},
        principal_input_port_id="payload",
    )
    ports = {
        "payload": PortSpec("payload", "in", "data", "COREX.DataTypes.Double"),
        "required": PortSpec("required", "in", "data", "COREX.DataTypes.Double", required=True),
        "result": PortSpec("result", "out", "data", "COREX.DataTypes.Double"),
    }
    before = node.clone()
    state = reconcile_script_port_state(node, ports, semantic_changed_keys={"required"})
    assert node == before
    assert state.exposed_ports == {"payload": False, "required": True, "result": True}
    assert state.port_labels == {"payload": "Alias"}
    assert state.port_modifiers == {"payload": ("clean", "graft", "clean"), "result": ()}
    assert state.principal_input_port_id == "payload"
    state.exposed_ports.clear()
    state.port_labels.clear()
    state.port_modifiers.clear()
    assert node == before
    changed = reconcile_script_port_state(node, ports, semantic_changed_keys={"payload"})
    assert changed.principal_input_port_id is None
    assert "payload" not in changed.port_labels
    assert "payload" not in changed.port_modifiers
    assert changed.exposed_ports["payload"] is True


def test_script_semantic_type_change_resets_state_without_forcing_compatible_wire_removal(tmp_path) -> None:
    registry = build_builtin_registry(generation_root=tmp_path / "plugin_generations")
    model = GraphModel()
    workspace = model.active_workspace
    mutation = model.validated_mutations(workspace.workspace_id, registry)
    source_text = '@corex.node\n@corex.output("value", value_type=float)\ndef run(ctx): return {"value": 1.0}\n'
    target_text = '@corex.node\n@corex.input("value", value_type=corex.Any)\ndef run(ctx, value): return {}\n'
    source = mutation.add_node(type_id="core.python_script", title="Source", x=0, y=0, properties={"script": source_text})
    target = mutation.add_node(type_id="core.python_script", title="Target", x=200, y=0, properties={"script": target_text})
    edge = mutation.add_edge(source_node_id=source.node_id, source_port_key="value", target_node_id=target.node_id, target_port_key="value")
    target.port_labels = {"value": "Alias"}
    target.port_modifiers = {"value": ("graft",)}
    target.principal_input_port_id = "value"
    _, removed = mutation.apply_python_script(target.node_id, target_text.replace("corex.Any", "float"))
    assert removed == ()
    assert edge.edge_id in workspace.edges
    assert target.port_labels == {}
    assert target.port_modifiers == {}
    assert target.principal_input_port_id is None


def test_single_and_bulk_property_updates_keep_distinct_unknown_and_noop_contracts() -> None:
    model = GraphModel()
    workspace = model.active_workspace
    mutation = model.validated_mutations(workspace.workspace_id, _registry())
    node = mutation.add_node(type_id="tests.dynamic_inputs", title="Dynamic", x=0, y=0)
    before = workspace.capture_snapshot()
    revision = workspace.mutation_revision
    with pytest.raises(KeyError):
        mutation.set_node_property(node.node_id, "missing", "value")
    assert mutation.set_node_properties(node.node_id, {"": 1, "missing": 2}) == {}
    assert mutation.set_node_property(node.node_id, "mode", "unchanged") == "unchanged"
    assert mutation.set_node_properties(node.node_id, {"mode": "unchanged"}) == {}
    assert workspace.capture_snapshot() == before
    assert workspace.mutation_revision == revision
    assert mutation.set_node_properties(node.node_id, {"mode": "changed", "missing": 2}) == {"mode": "changed"}
