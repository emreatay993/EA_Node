# Purpose: Prove opt-in connected dynamic inputs share one conservative computational identity.
# Map: subsystems/execution.md
# Tests: this file
from dataclasses import replace
from types import SimpleNamespace

import pytest

from ea_node_editor.execution.compiler import compile_runtime_workspace_snapshot
from ea_node_editor.execution.execution_plan import ExecutionPlan
from ea_node_editor.execution.graph_changes import compare_execution_graphs
from ea_node_editor.execution.runtime_dto import RuntimeEdge, RuntimeNode, RuntimeWorkspace
from ea_node_editor.execution.solution_identity import assemble_node_solution
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.instance_resolution import resolve_instance_ports
from ea_node_editor.nodes.node_specs import (
    DynamicPortGroupSpec, NodeTypeSpec, PortSpec, PropertyConditionSpec,
    PropertySpec, ReadinessRequirementSpec,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.solution_provenance import SolutionProvenanceInputSpec


def _inputs(properties):
    return tuple(
        PortSpec(
            key, "in", "data",
            "COREX.DataTypes.String" if key.startswith("typed_empty") else "COREX.DataTypes.Any",
            required=False, label=f"Input {index}", allow_multiple_connections=True,
        )
        for index, key in enumerate(properties["port_ids"])
    )


def _new_key(_properties):
    return "new"


def _spec():
    return NodeTypeSpec(
        "tests.optional_collection", "Optional collection", ("Tests",), "",
        (PortSpec("result", "out", "data", "COREX.DataTypes.Any"),),
        (
            PropertySpec("port_ids", "json", ["left", "right"], "Ports", inspector_visible=False),
            PropertySpec("amount", "int", 1, "Amount"),
            PropertySpec("ornament", "str", "plain", "Ornament", affects_execution=False),
        ),
        dynamic_port_groups=(DynamicPortGroupSpec(
            "inputs", "port_ids", "in", _inputs, _new_key,
            execution_policy="connected_inputs",
        ),),
    )


def _plan(graph, snapshot=None):
    snapshot = snapshot or graph.workspace.capture_snapshot()
    workspace = RuntimeWorkspace(
        document_fields={"workspace_id": graph.workspace.workspace_id, "name": snapshot.name},
        nodes=tuple(RuntimeNode.from_node_instance(node) for node in snapshot.nodes.values()),
        edges=tuple(RuntimeEdge.from_edge_instance(edge) for edge in snapshot.edges.values()),
    )
    return ExecutionPlan(compile_runtime_workspace_snapshot(workspace, graph.registry), graph.registry)


def _solution(graph, plan, node_id, preparation_id="first"):
    result = assemble_node_solution(
        preparation_id=preparation_id,
        solution_namespace_id="test-namespace", workspace_solution_revision=0,
        plan=plan, registry=graph.registry, node_id=node_id,
        keys_by_node={node.node_id: "a" * 64 for node in graph.sources},
        execution_environment_digest="b" * 64, trigger_publication_generations={},
    )
    assert result.reason_code == ""
    return result


def _compare(graph, before, after=None):
    return compare_execution_graphs(
        graph.workspace.workspace_id, registry=graph.registry,
        before_snapshot=before,
        after_snapshot=after or graph.workspace.capture_snapshot(),
    )


@pytest.fixture
def graph(monkeypatch):
    registry = build_builtin_registry().fork()
    registry.register_descriptor(_spec(), lambda: None)
    registry.freeze()
    model = GraphModel()
    workspace = model.active_workspace
    sources = tuple(
        model.add_node(workspace.workspace_id, "core.constant", key, 0, index * 100)
        for index, key in enumerate(("first", "second"))
    )
    node = model.add_node(
        workspace.workspace_id, _spec().type_id, "Collection", 200, 0,
        properties={"port_ids": ["left", "right"]},
    )
    edges = tuple(
        model.add_edge(workspace.workspace_id, source.node_id, "value", node.node_id, key)
        for source, key in zip(sources, ("left", "right"))
    )
    # Synthetic trusted descriptors have no reusable implementation bundle. Hold
    # only that independent identity axis fixed to test real solution-key assembly.
    monkeypatch.setattr(
        "ea_node_editor.execution.solution_identity.implementation_digest",
        lambda registry, type_id: "c" * 64,
    )
    return SimpleNamespace(registry=registry, model=model, workspace=workspace,
                           node=node, sources=sources, edges=edges)


@pytest.mark.parametrize("ids", [
    ["empty", "left", "right"], ["left", "empty", "right"],
    ["left", "right", "empty"], ["typed_empty", "left", "right"],
])
def test_empty_insertion_and_removal_preserve_keys_at_every_position(graph, ids):
    before = graph.workspace.capture_snapshot()
    old_plan = _plan(graph, before)
    old_solution = _solution(graph, old_plan, graph.node.node_id)
    source_solution = _solution(graph, old_plan, graph.sources[0].node_id)
    graph.node.properties["port_ids"] = ids
    after = graph.workspace.capture_snapshot()
    new_plan = _plan(graph, after)
    new_solution = _solution(graph, new_plan, graph.node.node_id, "second")
    assert not _compare(graph, before, after).affects_execution
    assert not _compare(graph, after, before).affects_execution
    assert new_solution == old_solution
    assert _solution(graph, new_plan, graph.sources[0].node_id, "second") == source_solution
    assert new_plan.node_computation(graph.node.node_id).properties["port_ids"] == ["left", "right"]
    assert [port.key for port in new_plan.node_computation(graph.node.node_id).ports] == ["result", "left", "right"]
    assert [port.key for port in new_plan.node_ports[graph.node.node_id]] == ["result", *ids]
    assert new_plan.nodes[graph.node.node_id].properties["port_ids"] == ids
    assert new_plan.workflow_interface_digest != old_plan.workflow_interface_digest
    assert new_plan.fingerprint != old_plan.fingerprint
    assert graph.node.properties["port_ids"] == ids


def test_disabled_edge_does_not_make_a_dynamic_input_participate(graph):
    graph.node.properties["port_ids"] = ["left", "disabled", "right"]
    edge = graph.model.add_edge(graph.workspace.workspace_id, graph.sources[0].node_id,
                                "value", graph.node.node_id, "disabled")
    edge.enabled = False
    before = graph.workspace.capture_snapshot()
    old = _solution(graph, _plan(graph), graph.node.node_id)
    graph.model.remove_edge(graph.workspace.workspace_id, edge.edge_id)
    graph.node.properties["port_ids"] = ["left", "right"]
    assert not _compare(graph, before).affects_execution
    assert _solution(graph, _plan(graph), graph.node.node_id, "second") == old


def test_multiple_empty_inputs_on_disconnected_node_share_identity(graph):
    for edge in graph.edges:
        edge.enabled = False
    before = graph.workspace.capture_snapshot()
    old = _solution(graph, _plan(graph), graph.node.node_id)
    graph.node.properties["port_ids"] = ["typed_empty", "another"]
    assert not _compare(graph, before).affects_execution
    plan = _plan(graph)
    assert plan.node_computation(graph.node.node_id).properties["port_ids"] == []
    assert _solution(graph, plan, graph.node.node_id, "second") == old


@pytest.mark.parametrize("edit", ["connect", "disconnect", "reorder", "replace_id", "edge_order", "property", "principal", "modifier"])
def test_real_computational_edits_change_consumer_identity_in_both_directions(graph, edit):
    if edit == "connect":
        graph.edges[1].enabled = False
    before = graph.workspace.capture_snapshot()
    old_plan = _plan(graph)
    old = _solution(graph, old_plan, graph.node.node_id)
    if edit == "connect":
        graph.edges[1].enabled = True
    elif edit == "disconnect":
        graph.edges[1].enabled = False
    elif edit == "reorder":
        graph.node.properties["port_ids"] = ["right", "left"]
    elif edit == "replace_id":
        graph.node.properties["port_ids"] = ["left", "renamed"]
        graph.edges[1].target_port_key = "renamed"
    elif edit == "edge_order":
        graph.edges[1].input_order = 12
    elif edit == "property":
        graph.node.properties["amount"] = 2
    elif edit == "principal":
        graph.node.principal_input_port_id = "right"
    else:
        graph.node.port_modifiers = {"right": ["flatten"]}
    after = graph.workspace.capture_snapshot()
    assert _compare(graph, before, after).changed_root_node_ids == (graph.node.node_id,)
    assert _compare(graph, after, before).changed_root_node_ids == (graph.node.node_id,)
    new_plan = _plan(graph)
    assert _solution(graph, new_plan, graph.node.node_id).solution_key != old.solution_key
    assert new_plan.node_solution_interface_digest(graph.sources[0].node_id) == old_plan.node_solution_interface_digest(graph.sources[0].node_id)


@pytest.mark.parametrize("property_key,value", [
    ("scene_styles", {"scene_1": {"color": "#ff0000"}}),
    ("show_mesh_edges", False),
])
def test_viewer_appearance_still_skips_compilation(monkeypatch, property_key, value):
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    node = model.add_node(workspace.workspace_id, "model.viewer", "Viewer", 0, 0)
    before = workspace.capture_snapshot()
    node.properties[property_key] = value
    def unexpected(*args, **kwargs):
        pytest.fail("viewer appearance edit compiled the workflow")
    monkeypatch.setattr("ea_node_editor.execution.graph_changes.compile_runtime_workspace_snapshot", unexpected)
    assert not compare_execution_graphs(workspace.workspace_id, registry=registry,
        before_snapshot=before, after_snapshot=workspace.capture_snapshot()).affects_execution


def test_registry_binds_policy_and_keeps_backing_property_computational():
    spec = _spec()
    other = replace(spec, dynamic_port_groups=(replace(spec.dynamic_port_groups[0], execution_policy="all_ports"),))
    first, second = NodeRegistry(), NodeRegistry()
    for registry, declaration in ((first, spec), (second, other)):
        registry.register_descriptor(declaration, lambda: None)
    assert first.contract_fingerprint() != second.contract_fingerprint()
    assert first.execution_properties(spec.type_id, {})["port_ids"] == ["left", "right"]


@pytest.mark.parametrize("case", [
    "unknown", "not_string", "output", "source_backed", "not_list", "presentation",
    "required", "property_default", "readiness", "readiness_condition", "port_readiness",
    "static_input", "provenance", "sensitive", "sensitive_scope",
])
def test_connected_inputs_rejects_unsafe_declarations_atomically(case):
    spec = _spec()
    group = spec.dynamic_port_groups[0]
    props = spec.properties
    if case == "unknown":
        group = replace(group, execution_policy="sometimes")
    elif case == "not_string":
        group = replace(group, execution_policy=[])
    elif case == "output":
        group = replace(group, direction="out")
    elif case == "source_backed":
        group = replace(group, property_editor=lambda props, keys: "source")
        props = (props[0].with_changes(type="str", default="source"), *props[1:])
    elif case == "not_list":
        props = (props[0].with_changes(default={}), *props[1:])
    elif case == "presentation":
        props = (props[0].with_changes(affects_execution=False), *props[1:])
    elif case in {"required", "property_default"}:
        field = {"required": True} if case == "required" else {"uses_property_default": True}
        group = replace(group, ports_resolver=lambda p: tuple(replace(port, **field) for port in _inputs(p)))
    elif case == "readiness":
        spec = replace(spec, readiness_requirements=(ReadinessRequirementSpec(any_of_properties=("port_ids",)),))
    elif case == "readiness_condition":
        spec = replace(spec, readiness_requirements=(ReadinessRequirementSpec(
            any_of_properties=("amount",), when_properties=(PropertyConditionSpec("port_ids", (["left"],)),)),))
    elif case == "port_readiness":
        spec = replace(spec, readiness_requirements=(ReadinessRequirementSpec(any_of_ports=("left",)),))
    elif case == "static_input":
        spec = replace(spec, ports=(*spec.ports, PortSpec("port_ids", "in", "data", "COREX.DataTypes.Any", required=False)))
    elif case == "provenance":
        spec = replace(spec, solution_provenance_inputs=(SolutionProvenanceInputSpec("port_ids", "file"),))
    elif case == "sensitive":
        props = (props[0].with_changes(sensitive=True, inspector_editor="secret"), *props[1:])
    else:
        props = (*props, PropertySpec("secret", "json", {}, "Secret", sensitive=True,
                                     inspector_editor="secret", sensitive_scope_key="port_ids"))
    invalid = replace(spec, properties=props, dynamic_port_groups=(group,))
    registry = NodeRegistry()
    baseline = registry.contract_fingerprint()
    with pytest.raises((TypeError, ValueError)):
        registry.register_descriptor(invalid, lambda: None)
    assert registry.contract_fingerprint() == baseline
    assert registry.spec_or_none(invalid.type_id) is None


def test_instance_resolution_rejects_required_inputs_from_nondefault_properties():
    spec = _spec()
    group = replace(spec.dynamic_port_groups[0], ports_resolver=lambda p: tuple(
        replace(port, required=p["amount"] == 2) for port in _inputs(p)
    ))
    spec = replace(spec, dynamic_port_groups=(group,))
    registry = NodeRegistry()
    registry.register_descriptor(spec, lambda: None)
    with pytest.raises(ValueError, match="must be optional"):
        resolve_instance_ports(spec, {"amount": 2})


def test_invalid_dynamic_change_conservatively_invalidates(graph):
    before = graph.workspace.capture_snapshot()
    graph.node.properties["port_ids"] = ["left", "left"]
    assert _compare(graph, before).affects_execution


def test_instance_resolver_cannot_hide_contract_changes_behind_presentation_properties(graph):
    def resolve(spec, properties):
        return replace(spec, instance_spec_resolver=None,
                       is_async=properties.get("ornament") == "async")
    graph.registry = graph.registry.fork()
    spec = replace(_spec(), type_id="tests.resolved_collection", instance_spec_resolver=resolve)
    graph.registry.register_descriptor(spec, lambda: None)
    graph.registry.freeze()
    node = graph.model.add_node(graph.workspace.workspace_id, spec.type_id, "Resolved", 0, 0)
    before = graph.workspace.capture_snapshot()
    node.properties["ornament"] = "async"
    assert _compare(graph, before).changed_root_node_ids == (node.node_id,)


def test_builtin_model_viewer_preserves_solution_and_full_authored_inputs():
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    source = model.add_node(workspace.workspace_id, "engineering.fe_import", "Import", 0, 0)
    viewer = model.add_node(workspace.workspace_id, "model.viewer", "Viewer", 200, 0,
                            properties={"scene_input_ids": ["scene_1", "scene_2"]})
    model.add_edge(workspace.workspace_id, source.node_id, "scene", viewer.node_id, "scene_2")
    graph = SimpleNamespace(registry=registry, model=model, workspace=workspace, sources=(source,))
    before = workspace.capture_snapshot()
    old_plan = _plan(graph)
    old_solution = _solution(graph, old_plan, viewer.node_id)
    assert len(old_plan.incoming_edges_for(viewer.node_id)) == 1
    viewer.properties["scene_input_ids"] = ["scene_0", "scene_1", "scene_2"]
    new_plan = _plan(graph)
    assert not _compare(graph, before).affects_execution
    assert _solution(graph, new_plan, viewer.node_id, "second") == old_solution
    assert new_plan.node_computation(viewer.node_id).properties["scene_input_ids"] == ["scene_2"]
    assert new_plan.nodes[viewer.node_id].properties["scene_input_ids"] == ["scene_0", "scene_1", "scene_2"]
    assert len(new_plan.input_ports(viewer.node_id)) == len(old_plan.input_ports(viewer.node_id)) + 1
    assert new_plan.ports_by_key[viewer.node_id]["scene_2"].label != old_plan.ports_by_key[viewer.node_id]["scene_2"].label
    assert new_plan.workflow_interface_digest != old_plan.workflow_interface_digest
    assert new_plan.node_solution_interface_digest(source.node_id) == old_plan.node_solution_interface_digest(source.node_id)


@pytest.mark.parametrize("type_id", ["core.python_script", "core.stream_gate"])
def test_source_backed_inputs_and_dynamic_outputs_remain_computational(type_id):
    registry = build_builtin_registry()
    assert all(group.execution_policy == "all_ports" for group in registry.get_spec(type_id).dynamic_port_groups)
    model = GraphModel()
    workspace = model.active_workspace
    node = model.add_node(workspace.workspace_id, type_id, "Node", 0, 0)
    before = workspace.capture_snapshot()
    if type_id == "core.python_script":
        node.properties["script"] = '@corex.node\n@corex.input("extra", value_type=corex.Any, required=False)\ndef run(ctx, extra):\n    return {}\n'
    else:
        group = registry.get_spec(type_id).dynamic_port_groups[0]
        node.properties[group.property_key] = [*registry.default_properties(type_id)[group.property_key], "extra"]
    plan = _plan(SimpleNamespace(workspace=workspace, registry=registry))
    assert not plan.node_preflight_errors
    assert "extra" in plan.ports_by_key[node.node_id]
    assert compare_execution_graphs(workspace.workspace_id, registry=registry,
        before_snapshot=before, after_snapshot=workspace.capture_snapshot()).affects_execution


def test_invalid_script_identity_stays_execute_only(graph):
    node = graph.model.add_node(graph.workspace.workspace_id, "core.python_script", "Invalid", 0, 0,
                                properties={"script": "def invalid("})
    plan = _plan(graph)
    assert node.node_id in plan.node_preflight_errors
    result = assemble_node_solution(
        preparation_id="invalid", solution_namespace_id="test-namespace", workspace_solution_revision=0,
        plan=plan, registry=graph.registry, node_id=node.node_id, keys_by_node={},
        execution_environment_digest="b" * 64, trigger_publication_generations={},
    )
    assert result.reason_code
