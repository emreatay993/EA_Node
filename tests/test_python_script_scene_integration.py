# Purpose: Verify Python Script scene actions, runtime history, and settings payloads.
# Map: subsystems/graph_domain.md
# Tests: this file
from __future__ import annotations

import pytest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.validated_mutation import ValidatedGraphMutation
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.nodes.execution_context import ExecutionContext
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_scene_payload.builder import GraphScenePayloadBuilder


def test_canvas_port_edits_execute_and_undo_source_wires_and_port_state_together() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    scene = GraphSceneBridge()
    scene.set_workspace(model, registry, workspace.workspace_id)
    history = RuntimeGraphHistory()
    scene.bind_runtime_history(history)
    node_id = scene.add_node_from_type("core.python_script", 0, 0)
    peer_id = scene.add_node_from_type("core.python_script", 300, 0)
    assert scene.insert_dynamic_port(node_id, "inputs", 1) == "input1"
    assert scene.insert_dynamic_port(node_id, "outputs", 1) == "output1"
    node = workspace.nodes[node_id]
    ctx = ExecutionContext(run_id="test", node_id=node_id, workspace_id=workspace.workspace_id,
                           inputs={"payload": 42, "input1": 9}, properties=node.properties,
                           emit_log=lambda *_args: None)
    assert registry.create(node.type_id).execute(ctx).outputs == {"result": 42}
    input_edge = scene.add_edge(peer_id, "result", node_id, "input1")
    output_edge = scene.add_edge(node_id, "output1", peer_id, "payload")
    scene.set_port_modifiers(node_id, "input1", ["graft"])
    scene.set_principal_input_port(node_id, "input1")
    for group_id, port_key, edge_id in (("inputs", "input1", input_edge), ("outputs", "output1", output_edge)):
        before = history.capture_workspace(workspace)
        depth = history.undo_depth(workspace.workspace_id)
        result = scene.remove_dynamic_port(node_id, group_id, port_key)
        assert result["removed_edge_ids"] == [edge_id]
        assert edge_id not in workspace.edges
        assert history.undo_depth(workspace.workspace_id) == depth + 1
        after = history.capture_workspace(workspace)
        history.undo_workspace(workspace.workspace_id, workspace)
        assert history.capture_workspace(workspace) == before
        history.redo_workspace(workspace.workspace_id, workspace)
        assert history.capture_workspace(workspace) == after
    ctx.properties = workspace.nodes[node_id].properties
    assert registry.create(node.type_id).execute(ctx).outputs == {"result": 42}


def test_scene_bulk_apply_and_decorator_section_toggle_use_production_routes() -> None:
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
    scene = GraphSceneBridge()
    scene.set_workspace(model, registry, workspace.workspace_id)

    before = node.clone()
    with pytest.raises(ValueError, match="cannot be mixed"):
        scene.set_node_properties(
            node.node_id,
            {"script": source.replace("Plot", "Chart"), "timeout_sec": 1.0},
        )
    assert node == before
    assert scene.set_node_settings_group_expanded(node.node_id, "style", True)
    assert node.expanded_settings_group_ids == ("style",)

    document = JsonProjectSerializer(registry).to_persistent_document(model.project)
    saved_node = document["workspaces"][0]["nodes"][0]
    assert saved_node["expanded_settings_group_ids"] == ["style"]


def test_decorated_controls_use_the_shared_settings_group_payload() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    node = mutations.add_node(
        type_id="core.python_script", title="Script", x=0.0, y=0.0
    )
    source = """@corex.node
@corex.input("values", value_type=float, structure="tree", section="Data")
@corex.output("result", value_type=float)
@corex.switch("enabled", default=True, section="Display", port=True)
@corex.slider("width", default=2.0, minimum=0.5, maximum=8.0, section="Display")
def run(ctx, values, enabled, width):
    return {"result": width}
"""
    mutations.apply_python_script(node.node_id, source)

    payloads, _backdrops, _minimap = (
        GraphScenePayloadBuilder().build_node_payloads_for_ids(
            model=model,
            registry=registry,
            workspace_id=workspace.workspace_id,
            scope_path=(),
            node_ids={node.node_id},
            graph_theme_bridge=None,
        )
    )
    payload = payloads[0]
    assert [group["group_id"] for group in payload["settings_groups"]] == [
        "data",
        "display",
    ]
    assert payload["settings_groups"][1]["items"][0]["kind"] == "port"
    enabled_port = next(port for port in payload["ports"] if port["key"] == "enabled")
    assert enabled_port["default_property"]["inline_editor"] == "toggle"
    assert (
        payload["settings_groups"][1]["items"][1]["property"]["inline_editor"]
        == "slider"
    )
    assert payload["inline_properties"] == []
