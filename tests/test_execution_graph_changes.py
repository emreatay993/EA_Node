# Purpose: Prove computational snapshot comparison, including history and hierarchy equivalence.
# Map: subsystems/execution.md
# Tests: this file
from types import SimpleNamespace
from dataclasses import replace

import pytest

from ea_node_editor.execution.graph_changes import compare_execution_graphs
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import NodeCommentRecord, NodeLinkRecord
from ea_node_editor.graph.transform_grouping_ops import (
    group_selection_into_subnode,
    ungroup_subnode,
)
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec


@pytest.fixture
def graph():
    registry = build_builtin_registry().fork()
    registry.register_descriptor(
        NodeTypeSpec(
            "tests.display",
            "Display",
            ("Tests",),
            "",
            (
                PortSpec("input", "in", "data", "COREX.DataTypes.Any", required=False),
                PortSpec("output", "out", "data", "COREX.DataTypes.Any"),
            ),
            (
                PropertySpec("value", "str", "a", "Value"),
                PropertySpec(
                    "ornament", "str", "plain", "Ornament", affects_execution=False
                ),
            ),
        ),
        lambda: None,
    )
    model = GraphModel()
    workspace = model.active_workspace
    nodes = [
        model.add_node(workspace.workspace_id, "tests.display", str(i), i * 200, 0)
        for i in range(4)
    ]
    edges = [
        model.add_edge(
            workspace.workspace_id,
            nodes[i].node_id,
            "output",
            nodes[i + 1].node_id,
            "input",
        )
        for i in range(2)
    ]

    def compare(before):
        registry.freeze()
        return compare_execution_graphs(
            workspace.workspace_id,
            registry=registry,
            before_snapshot=before,
            after_snapshot=workspace.capture_snapshot(),
        )

    return SimpleNamespace(
        model=model,
        workspace=workspace,
        registry=registry,
        nodes=nodes,
        edges=edges,
        compare=compare,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("x", 34),
        ("y", 82),
        ("custom_width", 500),
        ("custom_height", 400),
        ("collapsed", True),
        ("expanded_settings_group_ids", ("settings",)),
        ("locked", True),
        ("held_member_ids", ("node_member",)),
        ("title", "Renamed"),
        ("visual_style", {"color": "blue"}),
        ("port_labels", {"input": "New label"}),
        ("comments", [NodeCommentRecord("c", "Note", "A", "now", "now")]),
    ],
)
def test_cosmetic_records_skip_compilation(graph, monkeypatch, field, value):
    before = graph.workspace.capture_snapshot()
    setattr(graph.nodes[0], field, value)

    def unexpected(*args, **kwargs):
        pytest.fail("presentation edit compiled the workflow")

    monkeypatch.setattr(
        "ea_node_editor.execution.graph_changes.compile_runtime_workspace_snapshot",
        unexpected,
    )
    assert not graph.compare(before).affects_execution


def test_static_property_edits_identify_exact_roots_without_compiling(graph, monkeypatch):
    before = graph.workspace.capture_snapshot()
    graph.nodes[1].properties["value"] = "changed"
    def unexpected(*args, **kwargs):
        pytest.fail("fixed-declaration property edit compiled the workflow")
    monkeypatch.setattr("ea_node_editor.execution.graph_changes.compile_runtime_workspace_snapshot", unexpected)
    change = graph.compare(before)
    assert change.changed_root_node_ids == (graph.nodes[1].node_id,)
    assert not change.removed_node_ids


def test_static_property_change_roots_follow_the_new_authored_order(graph):
    before = graph.workspace.capture_snapshot()
    graph.nodes[0].properties["value"] = "first"
    graph.nodes[1].properties["value"] = "second"
    after = graph.workspace.capture_snapshot()
    after = replace(after, nodes=dict(reversed(tuple(after.nodes.items()))))
    change = compare_execution_graphs(graph.workspace.workspace_id, before_snapshot=before,
        after_snapshot=after, registry=graph.registry)
    assert change.changed_root_node_ids == (graph.nodes[1].node_id, graph.nodes[0].node_id)


def test_unfamiliar_presentation_property_and_mixed_edit(graph, monkeypatch):
    before = graph.workspace.capture_snapshot()
    graph.nodes[0].properties["ornament"] = "fancy"
    assert not graph.compare(before).affects_execution
    graph.nodes[1].properties["value"] = "changed"
    graph.nodes[3].x += 50
    change = graph.compare(before)
    assert change.changed_root_node_ids == (graph.nodes[1].node_id,)
    assert not change.removed_node_ids


def test_disabled_edges_and_informational_links_are_not_computational(graph):
    graph.edges[0].enabled = False
    before = graph.workspace.capture_snapshot()
    graph.edges[0].input_order = 20
    graph.nodes[1].links.append(
        NodeLinkRecord("help", "url", "Help", "https://example.com")
    )
    assert not graph.compare(before).affects_execution


def test_rewire_marks_old_and_new_consumers(graph):
    before = graph.workspace.capture_snapshot()
    graph.edges[0].target_node_id = graph.nodes[3].node_id
    change = graph.compare(before)
    assert set(change.changed_root_node_ids) == {
        graph.nodes[1].node_id,
        graph.nodes[3].node_id,
    }


@pytest.mark.parametrize("field,value", [
    ("port_modifiers", {"input": ("flatten",)}),
    ("principal_input_port_id", "input"),
    ("exposed_ports", {"input": False}),
])
def test_computational_interface_edits_invalidate_the_edited_consumer(graph, field, value):
    before = graph.workspace.capture_snapshot()
    setattr(graph.nodes[1], field, value)
    change = graph.compare(before)
    assert change.affects_execution
    assert change.changed_root_node_ids == (graph.nodes[1].node_id,)


def test_removal_and_reverse_snapshots_normalize_roots(graph):
    before = graph.workspace.capture_snapshot()
    removed = graph.nodes[1].node_id
    graph.model.remove_node(graph.workspace.workspace_id, removed)
    after = graph.workspace.capture_snapshot()
    change = graph.compare(before)
    assert change.removed_node_ids == (removed,)
    assert change.changed_root_node_ids == (graph.nodes[2].node_id,)
    undo = compare_execution_graphs(
        graph.workspace.workspace_id,
        registry=graph.registry,
        before_snapshot=after,
        after_snapshot=before,
    )
    assert set(undo.changed_root_node_ids) == {removed, graph.nodes[2].node_id}
    assert undo.removed_node_ids == ()


def test_group_and_ungroup_preserve_computation(graph):
    before = graph.workspace.capture_snapshot()
    grouped = group_selection_into_subnode(
        model=graph.model,
        registry=graph.registry,
        workspace_id=graph.workspace.workspace_id,
        selected_node_ids=[node.node_id for node in graph.nodes[:2]],
        scope_path=[],
        shell_x=100,
        shell_y=100,
    )
    assert grouped is not None
    assert not graph.compare(before).affects_execution
    grouped_snapshot = graph.workspace.capture_snapshot()
    ungroup_subnode(
        model=graph.model,
        workspace_id=graph.workspace.workspace_id,
        shell_node_id=grouped.shell_node_id,
    )
    assert not graph.compare(grouped_snapshot).affects_execution


def test_cosmetic_change_on_invalid_script_does_not_resolve_or_compile(
    graph, monkeypatch
):
    script = graph.model.add_node(
        graph.workspace.workspace_id,
        "code.python_script",
        "Broken",
        0,
        300,
        properties={"script": "def invalid("},
    )
    before = graph.workspace.capture_snapshot()
    script.collapsed = True
    monkeypatch.setattr(
        graph.registry,
        "execution_properties",
        lambda *args: pytest.fail("resolved invalid script"),
    )
    assert not graph.compare(before).affects_execution


def test_passive_node_addition_does_not_invalidate(graph):
    before = graph.workspace.capture_snapshot()
    graph.model.add_node(
        graph.workspace.workspace_id, "passive.annotation.sticky_note", "Note", 0, 0
    )
    assert not graph.compare(before).affects_execution


def test_recovery_from_invalid_before_snapshot_never_targets_compile_only_nodes(graph):
    grouped = group_selection_into_subnode(
        model=graph.model,
        registry=graph.registry,
        workspace_id=graph.workspace.workspace_id,
        selected_node_ids=[node.node_id for node in graph.nodes[:2]],
        scope_path=[],
        shell_x=100,
        shell_y=100,
    )
    unavailable = graph.model.add_node(
        graph.workspace.workspace_id, "unavailable.node", "Missing", 0, 0
    )
    before = graph.workspace.capture_snapshot()
    graph.model.remove_node(graph.workspace.workspace_id, unavailable.node_id)
    change = graph.compare(before)
    assert change.affects_execution
    assert set(change.changed_root_node_ids) == {node.node_id for node in graph.nodes}
    assert grouped.shell_node_id not in change.changed_root_node_ids


def test_resolver_cannot_hide_structural_change_behind_presentation_metadata(graph):
    def resolve(spec, properties):
        return replace(
            spec,
            instance_spec_resolver=None,
            ports=(
                PortSpec(
                    "output",
                    "out",
                    "data",
                    "COREX.DataTypes.String"
                    if properties.get("ornament") == "fancy"
                    else "COREX.DataTypes.Any",
                ),
            ),
        )

    graph.registry.register_descriptor(
        NodeTypeSpec(
            "tests.resolved",
            "Resolved",
            ("Tests",),
            "",
            (),
            (
                PropertySpec(
                    "ornament", "str", "plain", "Ornament", affects_execution=False
                ),
            ),
            instance_spec_resolver=resolve,
        ),
        lambda: None,
    )
    node = graph.model.add_node(
        graph.workspace.workspace_id, "tests.resolved", "Resolved", 0, 0
    )
    before = graph.workspace.capture_snapshot()
    node.properties["ornament"] = "fancy"
    assert graph.compare(before).changed_root_node_ids == (node.node_id,)


def test_solution_key_preserves_presentation_but_snapshot_still_attests_it():
    from ea_node_editor.execution.runtime import CorexRuntime
    from ea_node_editor.execution.runtime_requests import ExecutionRequest
    from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
    from tests.test_runtime import _PreparedClient

    registry = build_builtin_registry()
    model = GraphModel()
    node = model.add_node(
        model.active_workspace.workspace_id,
        "data.panel",
        "Panel",
        0,
        0,
        properties={"value": "original"},
    )
    runtime = CorexRuntime(client=_PreparedClient(), registry=registry)

    def prepare():
        return runtime.prepare_execution(
            ExecutionRequest(
                runtime_snapshot=build_runtime_snapshot(
                    model.project,
                    registry=registry,
                    workspace_id=model.active_workspace.workspace_id,
                ),
                workspace_id=model.active_workspace.workspace_id,
            )
        )

    first = prepare()
    node.properties["font_size"] = 24
    second = prepare()
    assert first.node_decisions[0].solution_key == second.node_decisions[0].solution_key
    assert first.runtime_snapshot_fingerprint != second.runtime_snapshot_fingerprint
    node.properties["value"] = "changed"
    third = prepare()
    assert second.node_decisions[0].solution_key != third.node_decisions[0].solution_key
    runtime.shutdown()


def test_execution_links_invalidate_old_and_new_pool_consumers(graph):
    from ea_node_editor.common.optimization_links import (
        OPTIMIZATION_PARAMETER_SETUP_TYPE_ID,
        OPTIMIZATION_PARAMETER_POOL_TYPE_ID,
        PARAMETER_SETUP_PARAMETER_POOL_LINK_ID,
        PARAMETER_SETUP_PARAMETER_POOL_LINK_TITLE,
    )

    workspace_id = graph.workspace.workspace_id
    setup = graph.model.add_node(
        workspace_id, OPTIMIZATION_PARAMETER_SETUP_TYPE_ID, "Setup", 0, 0
    )
    pools = [
        graph.model.add_node(
            workspace_id, OPTIMIZATION_PARAMETER_POOL_TYPE_ID, "Pool", 0, 0
        )
        for _ in range(2)
    ]

    def link(pool):
        return NodeLinkRecord(
            PARAMETER_SETUP_PARAMETER_POOL_LINK_ID,
            "node",
            PARAMETER_SETUP_PARAMETER_POOL_LINK_TITLE,
            pool.node_id,
            target_workspace_id=workspace_id,
            target_node_id=pool.node_id,
        )

    setup.links = [link(pools[0])]
    before = graph.workspace.capture_snapshot()
    setup.links = [link(pools[1])]
    change = graph.compare(before)
    assert set(change.changed_root_node_ids) == {pool.node_id for pool in pools}


def test_save_reopen_retains_appearance_without_changing_computation(tmp_path):
    from ea_node_editor.persistence.serializer import JsonProjectSerializer

    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    node = model.add_node(workspace.workspace_id, "media.panel", "Media", 0, 0)
    before = workspace.capture_snapshot()
    node.properties.update(
        {"show_title": False, "show_frame": False, "rotation_degrees": 90}
    )
    serializer = JsonProjectSerializer(registry)
    path = str(tmp_path / "presentation.cxproj")
    serializer.save(path, model.project)
    reopened = serializer.load(path).workspaces[workspace.workspace_id]
    assert reopened.nodes[node.node_id].properties["show_title"] is False
    assert reopened.nodes[node.node_id].properties["rotation_degrees"] == 90
    assert not compare_execution_graphs(
        workspace.workspace_id,
        registry=registry,
        before_snapshot=before,
        after_snapshot=reopened.capture_snapshot(),
    ).affects_execution
