# Purpose: Verify Script settings and section state through documents and fragments.
# Map: subsystems/persistence.md
# Tests: this file
from __future__ import annotations

import json

import pytest

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
from ea_node_editor.settings import SCHEMA_VERSION


def test_fragment_copy_preserves_decorator_section_expansion() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    node = mutations.add_node(
        type_id="code.python_script", title="Script", x=0.0, y=0.0
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
        type_id="code.python_script", title="Script", x=0.0, y=0.0
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


@pytest.mark.parametrize("schema_version", [SCHEMA_VERSION - 1, SCHEMA_VERSION])
def test_old_python_script_type_migrates_when_project_is_opened_and_saved(
    tmp_path, schema_version: int,
) -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    source = '''@corex.node
@corex.output("result", value_type=str)
def run(ctx):
    return {"result": "saved value"}
'''
    sink = '''@corex.node
@corex.input("payload", value_type=str)
def run(ctx, payload):
    return {}
'''
    source_node = mutations.add_node(
        type_id="code.python_script", title="Custom source", x=0.0, y=0.0,
        properties={"script": source},
    )
    sink_node = mutations.add_node(
        type_id="code.python_script", title="Custom sink", x=240.0, y=0.0,
        properties={"script": sink},
    )
    edge = mutations.add_edge(
        source_node_id=source_node.node_id, source_port_key="result",
        target_node_id=sink_node.node_id, target_port_key="payload",
    )

    serializer = JsonProjectSerializer(registry)
    document = serializer.to_persistent_document(model.project)
    document["schema_version"] = schema_version
    for node_doc in document["workspaces"][0]["nodes"]:
        node_doc["type_id"] = "core.python_script"
    document["metadata"]["custom_workflows"] = [{
        "workflow_id": "script_workflow",
        "name": "Script workflow",
        "fragment": {
            "kind": "ea-node-editor/graph-fragment",
            "version": 2,
            "nodes": [{
                "ref_id": "script",
                "type_id": "core.python_script",
                "title": "Custom source",
                "x": 0.0,
                "y": 0.0,
                "properties": {"script": source},
            }],
            "edges": [],
        },
    }]
    path = tmp_path / "old_script.cxproj"
    path.write_text(json.dumps(document), encoding="utf-8")

    loaded = serializer.load(str(path))
    loaded_workspace = loaded.workspaces[workspace.workspace_id]
    assert loaded_workspace.dirty
    assert any("code.python_script" in item for item in loaded.migration_report)
    assert {node.type_id for node in loaded_workspace.nodes.values()} == {"code.python_script"}
    assert loaded_workspace.nodes[source_node.node_id].title == "Custom source"
    assert loaded_workspace.nodes[source_node.node_id].properties["script"] == source
    assert edge.edge_id in loaded_workspace.edges
    loaded_workflow_node = loaded.metadata["custom_workflows"][0]["fragment"]["nodes"][0]
    assert loaded_workflow_node["type_id"] == "code.python_script"
    assert "core.python_script" in path.read_text(encoding="utf-8")

    serializer.save(str(path), loaded)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == SCHEMA_VERSION
    assert {node["type_id"] for node in saved["workspaces"][0]["nodes"]} == {
        "code.python_script"
    }
    saved_workflow_node = saved["metadata"]["custom_workflows"][0]["fragment"]["nodes"][0]
    assert saved_workflow_node["type_id"] == "code.python_script"
    assert {edge_doc["edge_id"] for edge_doc in saved["workspaces"][0]["edges"]} == {
        edge.edge_id
    }
    assert "core.python_script" not in path.read_text(encoding="utf-8")

    reopened = serializer.load(str(path))
    assert not reopened.migration_report
    reopened_nodes = reopened.workspaces[workspace.workspace_id].nodes.values()
    assert {node.type_id for node in reopened_nodes} == {"code.python_script"}


def test_old_script_only_in_embedded_workflow_marks_project_for_resave() -> None:
    serializer = JsonProjectSerializer(build_builtin_registry())
    document = serializer.to_persistent_document(GraphModel().project)
    document["metadata"]["custom_workflows"] = [{
        "workflow_id": "script_workflow",
        "name": "Script workflow",
        "fragment": {
            "kind": "ea-node-editor/graph-fragment",
            "version": 2,
            "nodes": [{
                "ref_id": "script", "type_id": "core.python_script", "title": "Script",
            }],
            "edges": [],
        },
    }]

    loaded = serializer.from_document(document)
    assert loaded.migration_report
    assert loaded.workspaces[loaded.active_workspace_id].dirty
    saved = serializer.to_persistent_document(loaded)
    saved_workflow_node = saved["metadata"]["custom_workflows"][0]["fragment"]["nodes"][0]
    assert saved_workflow_node["type_id"] == "code.python_script"
