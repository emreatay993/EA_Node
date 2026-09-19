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


@pytest.mark.parametrize("ports", [False, True])
def test_unsectioned_controls_keep_compact_settings_layout_below_main_ports(ports: bool) -> None:
    from ea_node_editor.ui_qml.graph_geometry.standard_metrics import (
        standard_inline_label_anchor_offset,
        standard_inline_property_row_height,
    )

    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    mutations = ValidatedGraphMutation(model, workspace.workspace_id, registry)
    node = mutations.add_node(type_id="core.python_script", title="Script", x=0.0, y=0.0)
    source = f'''@corex.node
@corex.input("payload", value_type=corex.Any)
@corex.output("result", value_type=corex.Any)
@corex.switch("enabled", default=False, label="", port={ports})
@corex.slider("amount", default=0.5, minimum=0.0, maximum=1.0, port={ports})
@corex.dropdown("mode", default="First", options=("First", "Second"), port={ports})
@corex.text("title", default="Example", section="Display", port=True)
def run(ctx, payload, enabled, amount, mode, title):
    return {{"result": payload}}
'''
    mutations.apply_python_script(node.node_id, source)

    def payload():
        return GraphScenePayloadBuilder().build_node_payloads_for_ids(
            model=model, registry=registry, workspace_id=workspace.workspace_id,
            scope_path=(), node_ids={node.node_id}, graph_theme_bridge=None,
        )[0][0]

    before = node.clone()
    first = payload()
    assert node == before
    assert node.expanded_settings_group_ids == ()
    assert first["inline_properties"] == []
    assert first["surface_metrics"]["body_height"] == 0.0
    loose, named = first["settings_groups"]
    assert loose["expanded"] and not loose["show_header"]
    assert loose["header"]["height"] == 0.0
    assert loose["aggregate_anchor"] is None
    assert not named["expanded"] and named["show_header"]
    assert all(item["visible"] for item in loose["items"])
    assert [item["height"] for item in loose["items"]] == [
        standard_inline_property_row_height(editor) for editor in ("toggle", "slider", "enum")
    ]
    assert [item["height"] for item in loose["items"]] == [26.0, 66.0, 56.0]
    assert loose["items"][1]["y"] == loose["items"][0]["y"] + 26.0
    assert loose["items"][2]["y"] == loose["items"][1]["y"] + 66.0
    assert named["header"]["y"] == loose["items"][-1]["y"] + 56.0
    main_port_bottom = first["surface_metrics"]["port_top"] + first["surface_metrics"]["port_height"]
    assert loose["items"][0]["y"] >= main_port_bottom
    if ports:
        for item, key in zip(loose["items"], ("enabled", "amount", "mode")):
            port = next(port for port in first["ports"] if port["key"] == key)
            assert port["handle_visible"]
            assert port["presentation_anchor"]["y"] == item["y"] + standard_inline_label_anchor_offset()
        assert next(port for port in first["ports"] if port["key"] == "enabled")["default_property"]["label"] == ""
    else:
        assert loose["items"][0]["property"]["label"] == ""
        assert {port["key"] for port in first["ports"]} == {"payload", "result", "title"}

    # A socket toggle changes only connection capability, not row positions,
    # sizing, main-port geometry, or user section state.
    mutations.apply_python_script(node.node_id, source.replace(f"port={ports})", f"port={not ports})", 3))
    second = payload()
    assert (second["width"], second["height"]) == (first["width"], first["height"])
    assert second["surface_metrics"] == first["surface_metrics"]
    assert [(item["y"], item["height"]) for item in second["settings_groups"][0]["items"]] == [
        (item["y"], item["height"]) for item in loose["items"]
    ]
    assert next(port for port in second["ports"] if port["key"] == "payload") == first["ports"][0]
    node.expanded_settings_group_ids = ("display",)
    expanded = payload()
    assert expanded["settings_groups"][1]["expanded"]
    assert expanded["settings_groups"][0] == second["settings_groups"][0]
    assert node.expanded_settings_group_ids == ("display",)


def test_guided_script_apply_uses_scene_history_and_preserves_wire_identity() -> None:
    from ea_node_editor.nodes.python_script_authoring import edit_source

    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    scene = GraphSceneBridge()
    scene.set_workspace(model, registry, workspace.workspace_id)
    history = RuntimeGraphHistory()
    scene.bind_runtime_history(history)
    node_id = scene.add_node_from_type("core.python_script", 0, 0)
    peer_id = scene.add_node_from_type("core.python_script", 300, 0)
    edge_id = scene.add_edge(peer_id, "result", node_id, "payload")
    scene.set_node_port_label(node_id, "payload", "Measured data")
    scene.set_port_modifiers(node_id, "payload", ["graft"])
    scene.set_principal_input_port(node_id, "payload")
    before = history.capture_workspace(workspace)
    depth = history.undo_depth(workspace.workspace_id)
    source = edit_source(workspace.nodes[node_id].properties["script"], "rename",
                         key="payload", new_key="measurements").source
    prepared = scene.prepare_python_script(node_id, source, renamed_keys={"payload": "measurements"},
                                           source_revision=3)
    assert history.capture_workspace(workspace) == before
    assert history.undo_depth(workspace.workspace_id) == depth
    scene.apply_python_script(node_id, source, renamed_keys={"payload": "measurements"},
                              source_revision=3, prepared=prepared)
    node = workspace.nodes[node_id]
    assert workspace.edges[edge_id].target_port_key == "measurements"
    assert node.port_labels["measurements"] == "Measured data"
    assert node.port_modifiers["measurements"] == ("graft",)
    assert node.principal_input_port_id == "measurements"
    assert history.undo_depth(workspace.workspace_id) == depth + 1
    after = history.capture_workspace(workspace)
    history.undo_workspace(workspace.workspace_id, workspace)
    assert history.capture_workspace(workspace) == before
    history.redo_workspace(workspace.workspace_id, workspace)
    assert history.capture_workspace(workspace) == after


def test_stale_scene_script_apply_records_no_history_and_changes_no_source() -> None:
    registry = build_builtin_registry()
    model = GraphModel()
    workspace = model.active_workspace
    scene = GraphSceneBridge()
    scene.set_workspace(model, registry, workspace.workspace_id)
    history = RuntimeGraphHistory()
    scene.bind_runtime_history(history)
    node_id = scene.add_node_from_type("core.python_script", 0, 0)
    source = workspace.nodes[node_id].properties["script"] + "\n# draft\n"
    prepared = scene.prepare_python_script(node_id, source, source_revision=2)
    scene.add_node_from_type("core.python_script", 300, 0)
    before = history.capture_workspace(workspace)
    depth = history.undo_depth(workspace.workspace_id)
    with pytest.raises(ValueError, match="stale"):
        scene.apply_python_script(node_id, source, source_revision=2, prepared=prepared)
    assert history.capture_workspace(workspace) == before
    assert history.undo_depth(workspace.workspace_id) == depth
