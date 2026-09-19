# Purpose: Verify Script settings and section state through documents and fragments.
# Map: subsystems/persistence.md
# Tests: this file
from __future__ import annotations

from ea_node_editor.graph.fragment_payloads import build_graph_fragment_payload
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.transform_fragment_ops import (
    build_subtree_fragment_payload_data,
    insert_graph_fragment,
)
from ea_node_editor.graph.validated_mutation import ValidatedGraphMutation
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.runtime_contracts import Interval1D


def test_fragment_copy_preserves_decorator_section_expansion() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    node = mutations.add_node(
        type_id="core.python_script", title="Script", x=0.0, y=0.0
    )
    source = """@corex.node
@corex.output("result", value_type=str)
@corex.text("title", default="Plot", section="Style")
def run(ctx, title):
    return {"result": title}
"""
    mutations.apply_python_script(node.node_id, source)
    node.expanded_settings_group_ids = ("style",)
    fragment_data = build_subtree_fragment_payload_data(
        workspace=workspace,
        selected_node_ids=(node.node_id,),
    )
    assert fragment_data is not None
    pasted_ids = insert_graph_fragment(
        model=model,
        workspace_id=workspace.workspace_id,
        fragment_payload=build_graph_fragment_payload(**fragment_data),
        delta_x=200.0,
        delta_y=0.0,
        registry=registry,
    )

    assert len(pasted_ids) == 1
    assert workspace.nodes[pasted_ids[0]].expanded_settings_group_ids == ("style",)


def test_decorated_script_settings_round_trip_without_a_manifest_copy() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    node = mutations.add_node(
        type_id="core.python_script", title="Script", x=0.0, y=0.0
    )
    source = """@corex.node
@corex.output("result", value_type=corex.Interval)
@corex.interval("bounds", default=(0.0, 1.0), section="Ranges")
def run(ctx, bounds):
    return {"result": bounds}
"""
    mutations.apply_python_script(node.node_id, source)
    node.properties["bounds"] = Interval1D(2.0, 3.0)
    model.set_node_expanded_settings_group_ids(
        workspace.workspace_id,
        node.node_id,
        ("ranges",),
    )

    serializer = JsonProjectSerializer(registry)
    document = serializer.to_persistent_document(model.project)
    node_document = document["workspaces"][0]["nodes"][0]
    assert set(node_document["properties"]) == {
        "script",
        "timeout_sec",
        "bounds",
    }
    loaded = serializer.from_document(document)
    loaded_node = loaded.workspaces[workspace.workspace_id].nodes[node.node_id]
    assert loaded_node.properties["script"] == source
    assert loaded_node.properties["bounds"] == Interval1D(2.0, 3.0)
    assert loaded_node.expanded_settings_group_ids == ("ranges",)
