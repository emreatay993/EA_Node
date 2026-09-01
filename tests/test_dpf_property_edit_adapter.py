from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ea_node_editor.addons.ansys_dpf.property_edit_adapter import (
    AnsysDpfPropertyEditAdapter,
    resolve_dpf_result_path,
)
from ea_node_editor.addons.property_edit_adapters import PropertyEditAdapterContext
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.inspector_projection import build_selected_node_property_items
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


_OPTIONS = {
    "result_name": ("displacement", "stress"),
    "set_ids": ("1", "2", "3"),
    "time_values": ("0.0", "1.0"),
    "named_selection": ("ROTOR", "CASING"),
}


def _fixture():  # noqa: ANN202
    registry = build_default_registry()
    model = GraphModel()
    workspace_id = model.active_workspace.workspace_id
    scene = GraphSceneBridge()
    scene.set_workspace(model, registry, workspace_id)
    adapter = AnsysDpfPropertyEditAdapter(metadata_provider=lambda _path: _OPTIONS)
    return registry, model, workspace_id, scene, adapter


def _items(registry, model, workspace_id, node_id, adapter, *, project_path=None):  # noqa: ANN001, ANN202
    workspace = model.project.workspaces[workspace_id]
    node = workspace.nodes[node_id]
    spec = registry.get_spec(node.type_id)
    return {
        item["key"]: item
        for item in build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=set(),
            workspace_id=workspace_id,
            workspace_nodes=workspace.nodes,
            workspace_edges=workspace.edges,
            project_path=project_path,
            property_edit_adapters=(adapter,),
        )
    }


def test_result_fields_projects_metadata_and_only_active_scope_controls() -> None:
    registry, model, workspace_id, scene, adapter = _fixture()
    source_id = scene.add_node_from_type("dpf.workflow.result_source", 0.0, 0.0)
    fields_id = scene.add_node_from_type("dpf.workflow.result_fields", 300.0, 0.0)
    scene.set_node_property(source_id, "path", "C:/tmp/demo.rst")
    scene.set_node_property(fields_id, "selection_mode", "named_selection")
    scene.set_node_property(fields_id, "named_selection", "ROTOR")
    scene.set_node_property(fields_id, "time_scope_mode", "set_ids")
    scene.set_node_property(fields_id, "set_ids", "1, 3")
    scene.add_edge(source_id, "model", fields_id, "model")

    items = _items(registry, model, workspace_id, fields_id, adapter)

    assert items["result_name"]["enum_values"] == ["displacement", "stress"]
    assert items["named_selection"]["enum_values"] == ["ROTOR", "CASING"]
    assert "node_ids" not in items and "element_ids" not in items
    assert items["set_ids"]["editor_mode"] == "chip_list"
    assert items["set_ids"]["value"] == ["1", "3"]
    assert "time_values" not in items
    assert "ROTOR" in items["dpf_workflow_summary"]["value"]
    assert "2 sets" in items["dpf_workflow_summary"]["value"]


def test_result_name_uses_common_options_until_file_metadata_is_ready() -> None:
    registry, model, workspace_id, scene, adapter = _fixture()
    node_id = scene.add_node_from_type("dpf.workflow.result_viewer", 0.0, 0.0)

    unloaded_items = _items(registry, model, workspace_id, node_id, adapter)
    assert unloaded_items["result_name"]["enum_values"] == [
        "displacement",
        "stress",
        "elastic_strain",
        "structural_temperature",
    ]

    scene.set_node_property(node_id, "path", "C:/tmp/demo.rst")
    loaded_items = _items(registry, model, workspace_id, node_id, adapter)
    assert loaded_items["result_name"]["enum_values"] == ["displacement", "stress"]


def test_time_history_default_setup_is_attention_required() -> None:
    registry, model, workspace_id, scene, adapter = _fixture()
    node_id = scene.add_node_from_type("dpf.workflow.time_history_probe", 0.0, 0.0)

    items = _items(registry, model, workspace_id, node_id, adapter)

    assert items["selection_mode"]["attention_required"] is True
    assert "Choose a named selection" in items["selection_mode"]["help_text"]
    assert items["dpf_workflow_summary"]["attention_required"] is True
    assert items["dpf_workflow_summary"]["group_default_open"] is True
    assert "named_selection" not in items


def test_field_math_only_shows_scalar_for_scale_and_explains_missing_inputs() -> None:
    registry, model, workspace_id, scene, adapter = _fixture()
    node_id = scene.add_node_from_type("dpf.workflow.field_math", 0.0, 0.0)

    add_items = _items(registry, model, workspace_id, node_id, adapter)
    assert "scalar" not in add_items
    assert add_items["dpf_workflow_summary"]["attention_required"] is True

    scene.set_node_property(node_id, "operation", "scale")
    scale_items = _items(registry, model, workspace_id, node_id, adapter)
    assert scale_items["scalar"]["group"] == "Post"


def test_viewer_custom_range_and_output_mode_are_contextual() -> None:
    registry, model, workspace_id, scene, adapter = _fixture()
    node_id = scene.add_node_from_type("dpf.workflow.result_viewer", 0.0, 0.0)
    scene.set_node_property(node_id, "path", "C:/tmp/demo.rst")

    auto_items = _items(registry, model, workspace_id, node_id, adapter)
    assert "scalar_range_min" not in auto_items
    assert "scalar_range_max" not in auto_items
    assert auto_items["output_mode"]["group"] == "Advanced"

    scene.set_node_property(node_id, "scalar_range_mode", "custom")
    custom_items = _items(registry, model, workspace_id, node_id, adapter)
    assert "scalar_range_min" in custom_items
    assert "scalar_range_max" in custom_items


def test_upstream_model_path_is_resolved_against_project() -> None:
    registry, model, workspace_id, scene, adapter = _fixture()
    model_id = scene.add_node_from_type("dpf.model", 0.0, 0.0)
    fields_id = scene.add_node_from_type("dpf.workflow.result_fields", 300.0, 0.0)
    scene.set_node_property(model_id, "path", "results/demo.rst")
    scene.add_edge(model_id, "model", fields_id, "model")
    requested: list[str] = []
    adapter = AnsysDpfPropertyEditAdapter(
        metadata_provider=lambda path: requested.append(path) or _OPTIONS
    )

    _items(
        registry,
        model,
        workspace_id,
        fields_id,
        adapter,
        project_path="C:/workflows/project.cxproj",
    )

    assert requested == [str(Path("C:/workflows/results/demo.rst").resolve(strict=False))]


def test_chip_list_edits_rewrite_to_stable_string_properties() -> None:
    adapter = AnsysDpfPropertyEditAdapter(metadata_provider=lambda _path: _OPTIONS)
    rewrite = adapter.rewrite_property_edit(None, key="set_ids", value=["1", "3"])  # type: ignore[arg-type]
    assert rewrite is not None
    assert rewrite.key == "set_ids"
    assert rewrite.value == "1, 3"


def test_connected_path_takes_precedence_over_stale_local_property() -> None:
    source = SimpleNamespace(
        node_id="source",
        type_id="fixture.path_source",
        properties={"path": "C:/results/new.rst"},
    )
    viewer = SimpleNamespace(
        node_id="viewer",
        type_id="dpf.workflow.result_viewer",
        properties={"path": "C:/results/old.rst"},
    )
    edge = SimpleNamespace(
        source_node_id="source",
        source_port_key="path",
        target_node_id="viewer",
        target_port_key="path",
    )
    context = PropertyEditAdapterContext(
        node=viewer,
        workspace_nodes={"source": source, "viewer": viewer},
        workspace_edges={"edge": edge},
        source_path_resolver=lambda node, key: node.properties.get(key, ""),
    )

    assert resolve_dpf_result_path(context) == str(
        Path("C:/results/new.rst").resolve(strict=False)
    )
