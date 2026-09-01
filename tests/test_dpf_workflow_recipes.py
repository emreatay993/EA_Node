from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

from ea_node_editor.addons import catalog as addon_catalog
from ea_node_editor.addons.ansys_dpf.curated_catalog import (
    load_ansys_dpf_curated_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.metadata import (
    ANSYS_DPF_ADDON_ID,
    ANSYS_DPF_ADDON_MANIFEST,
)
from ea_node_editor.addons.ansys_dpf.plot_catalog import (
    load_ansys_dpf_plot_plugin_descriptors,
)
from ea_node_editor.addons.ansys_dpf.workflow_recipes import (
    DPF_RECIPE_CATEGORY_PATH,
    DPF_RECIPE_WORKFLOW_IDS,
    create_ansys_dpf_workflow_definitions,
)
from ea_node_editor.app_preferences import (
    default_app_preferences_document,
    set_addon_state,
)
from ea_node_editor.custom_workflows.codec import (
    custom_workflow_library_items,
)
from ea_node_editor.graph.fragment_payloads import graph_fragment_payload_is_valid
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import GRAPH_DATA_TYPE_ID
from ea_node_editor.ui.shell.controllers import workflow_library_controller as workflow_controller_module
from ea_node_editor.ui.shell.controllers.workflow_library_controller import WorkflowLibraryController
from ea_node_editor.ui.shell.quick_insert_projection import build_connection_quick_insert_items


def _definitions_by_id() -> dict[str, dict[str, object]]:
    return {
        definition["workflow_id"]: definition
        for definition in create_ansys_dpf_workflow_definitions()
    }


def _nodes_by_ref(definition: dict[str, object]) -> dict[str, dict[str, object]]:
    fragment = definition["fragment"]
    assert isinstance(fragment, dict)
    return {node["ref_id"]: node for node in fragment["nodes"]}


def _edge_keys(definition: dict[str, object]) -> set[tuple[str, str, str, str]]:
    fragment = definition["fragment"]
    assert isinstance(fragment, dict)
    return {
        (
            edge["source_ref_id"],
            edge["source_port_key"],
            edge["target_ref_id"],
            edge["target_port_key"],
        )
        for edge in fragment["edges"]
    }


def test_dpf_recipe_provider_publishes_five_bundled_fragments_with_empty_paths() -> None:
    definitions = create_ansys_dpf_workflow_definitions()

    assert tuple(definition["workflow_id"] for definition in definitions) == DPF_RECIPE_WORKFLOW_IDS
    assert all(definition["workflow_scope"] == "bundled" for definition in definitions)
    assert all(tuple(definition["category_path"]) == DPF_RECIPE_CATEGORY_PATH for definition in definitions)
    assert all(definition["revision"] == 1 for definition in definitions)

    for definition in definitions:
        assert definition["ports"] == []
        for node in _nodes_by_ref(definition).values():
            if node["type_id"] in {"dpf.workflow.result_source", "dpf.workflow.result_viewer"}:
                assert node["properties"]["path"] == ""


def test_dpf_recipe_fragments_follow_curated_ports_and_are_registry_valid() -> None:
    registry = NodeRegistry()
    registry.register_plugin_bundle(
        ANSYS_DPF_ADDON_MANIFEST.contract_manifest,
        (
            *load_ansys_dpf_curated_plugin_descriptors(),
            *load_ansys_dpf_plot_plugin_descriptors(),
        ),
        owner_id=ANSYS_DPF_ADDON_ID,
    )

    for definition in create_ansys_dpf_workflow_definitions():
        assert graph_fragment_payload_is_valid(
            fragment_payload=definition["fragment"],
            registry=registry,
        )


def test_dpf_recipe_wiring_encodes_each_task() -> None:
    definitions = _definitions_by_id()

    viewer_nodes = _nodes_by_ref(definitions[DPF_RECIPE_WORKFLOW_IDS[0]])
    assert [node["type_id"] for node in viewer_nodes.values()] == ["dpf.workflow.result_viewer"]
    assert viewer_nodes["viewer"]["properties"]["time_scope_mode"] == "first_set"

    peak_nodes = _nodes_by_ref(definitions[DPF_RECIPE_WORKFLOW_IDS[1]])
    assert peak_nodes["envelope"]["properties"]["time_scope_mode"] == "all_sets"
    assert ("source", "model", "envelope", "model") in _edge_keys(definitions[DPF_RECIPE_WORKFLOW_IDS[1]])

    probe_nodes = _nodes_by_ref(definitions[DPF_RECIPE_WORKFLOW_IDS[2]])
    assert probe_nodes["probe"]["properties"]["selection_mode"] == "choose_scope"
    assert probe_nodes["probe"]["properties"]["time_scope_mode"] == "all_sets"
    assert probe_nodes["plot"]["type_id"] == "dpf.plot.line"
    assert ("probe", "series", "plot", "series") in _edge_keys(definitions[DPF_RECIPE_WORKFLOW_IDS[2]])

    stress_edges = _edge_keys(definitions[DPF_RECIPE_WORKFLOW_IDS[3]])
    assert ("stress", "fields", "export", "fields") in stress_edges
    assert ("source", "model", "export", "model") in stress_edges

    compare_nodes = _nodes_by_ref(definitions[DPF_RECIPE_WORKFLOW_IDS[4]])
    assert compare_nodes["first"]["properties"]["time_scope_mode"] == "first_set"
    assert compare_nodes["last"]["properties"]["time_scope_mode"] == "last_set"
    assert compare_nodes["subtract"]["properties"]["operation"] == "subtract"
    assert {
        ("last", "fields", "subtract", "a"),
        ("first", "fields", "subtract", "b"),
    }.issubset(_edge_keys(definitions[DPF_RECIPE_WORKFLOW_IDS[4]]))


def test_dpf_recipe_nodes_have_readable_canvas_spacing() -> None:
    definitions = _definitions_by_id()

    for workflow_id in DPF_RECIPE_WORKFLOW_IDS[1:4]:
        x_positions = sorted(
            float(node["x"])
            for node in _nodes_by_ref(definitions[workflow_id]).values()
        )
        assert all(right - left >= 400.0 for left, right in zip(x_positions, x_positions[1:]))

    compare_nodes = _nodes_by_ref(definitions[DPF_RECIPE_WORKFLOW_IDS[4]])
    assert float(compare_nodes["first"]["x"]) - float(compare_nodes["source"]["x"]) >= 400.0
    assert float(compare_nodes["subtract"]["x"]) - float(compare_nodes["first"]["x"]) >= 400.0
    assert float(compare_nodes["last"]["y"]) - float(compare_nodes["first"]["y"]) >= 400.0
    middle_y = (float(compare_nodes["first"]["y"]) + float(compare_nodes["last"]["y"])) / 2
    assert float(compare_nodes["source"]["y"]) == middle_y
    assert float(compare_nodes["subtract"]["y"]) == middle_y


def test_live_workflow_aggregation_follows_dpf_addon_enabled_state() -> None:
    registration = addon_catalog.registered_addon_registration_by_id(ANSYS_DPF_ADDON_ID)
    assert registration is not None
    assert registration.workflow_definition_factory_attr == "create_ansys_dpf_workflow_definitions"

    enabled = addon_catalog.create_live_workflow_definitions(
        preferences_document=default_app_preferences_document(),
    )
    assert tuple(definition["workflow_id"] for definition in enabled) == DPF_RECIPE_WORKFLOW_IDS

    disabled_document = set_addon_state(
        default_app_preferences_document(),
        ANSYS_DPF_ADDON_ID,
        enabled=False,
        pending_restart=False,
    )
    assert addon_catalog.create_live_workflow_definitions(
        preferences_document=disabled_document,
    ) == ()


def test_dpf_recipes_without_declared_ports_are_not_connection_quick_insert_candidates() -> None:
    items = custom_workflow_library_items(list(create_ansys_dpf_workflow_definitions()))
    data_types = NodeRegistry().data_types

    after_output = build_connection_quick_insert_items(
        combined_items=items,
        data_types=data_types,
        query="",
        source_direction="out",
        source_kind="data",
        source_data_type=GRAPH_DATA_TYPE_ID,
        limit=12,
    )
    before_input = build_connection_quick_insert_items(
        combined_items=items,
        data_types=data_types,
        query="",
        source_direction="in",
        source_kind="data",
        source_data_type=GRAPH_DATA_TYPE_ID,
        limit=12,
    )

    assert after_output == []
    assert before_input == []


def test_workflow_library_resolves_local_then_global_then_bundled(monkeypatch) -> None:
    bundled = list(create_ansys_dpf_workflow_definitions())
    local_override = copy.deepcopy(bundled[0])
    local_override["name"] = "Local Override"
    global_override = copy.deepcopy(bundled[1])
    global_override["name"] = "Global Override"

    host = SimpleNamespace(
        model=GraphModel(),
        app_preferences_controller=SimpleNamespace(document=default_app_preferences_document),
    )
    host.model.project.metadata["custom_workflows"] = [local_override]
    controller = WorkflowLibraryController(host, SimpleNamespace())  # type: ignore[arg-type]
    monkeypatch.setattr(controller, "global_custom_workflow_definitions", lambda: [global_override])
    monkeypatch.setattr(
        workflow_controller_module,
        "create_live_workflow_definitions",
        lambda **_kwargs: tuple(bundled),
    )

    items = {item["workflow_id"]: item for item in controller.custom_workflow_library_items()}
    assert items[DPF_RECIPE_WORKFLOW_IDS[0]]["display_name"] == "Local Override"
    assert items[DPF_RECIPE_WORKFLOW_IDS[0]]["workflow_scope"] == "local"
    assert items[DPF_RECIPE_WORKFLOW_IDS[1]]["display_name"] == "Global Override"
    assert items[DPF_RECIPE_WORKFLOW_IDS[1]]["workflow_scope"] == "global"
    assert items[DPF_RECIPE_WORKFLOW_IDS[2]]["workflow_scope"] == "bundled"
    assert items[DPF_RECIPE_WORKFLOW_IDS[2]]["read_only"] is True
    assert tuple(items[DPF_RECIPE_WORKFLOW_IDS[2]]["category_path"]) == DPF_RECIPE_CATEGORY_PATH

    assert controller.resolve_custom_workflow_definition(DPF_RECIPE_WORKFLOW_IDS[0])["name"] == "Local Override"
    assert controller.resolve_custom_workflow_definition(DPF_RECIPE_WORKFLOW_IDS[1])["name"] == "Global Override"
    assert controller.resolve_custom_workflow_definition(DPF_RECIPE_WORKFLOW_IDS[2])["name"] == bundled[2]["name"]


def test_bundled_workflow_context_popup_has_no_edit_actions() -> None:
    qml_path = (
        Path(__file__).resolve().parents[1]
        / "ea_node_editor"
        / "ui_qml"
        / "components"
        / "shell"
        / "LibraryWorkflowContextPopup.qml"
    )
    source = qml_path.read_text(encoding="utf-8")

    assert 'libraryContextWorkflowScope === "bundled"' in source
    assert 'String(workflowScope || "").toLowerCase() === "bundled"' in source
    assert "libraryContextWorkflowReadOnly ? [] : editableContextMenuActions" in source
