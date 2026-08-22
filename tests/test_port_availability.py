from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ea_node_editor.addons.tabular_data.input_node import (
    TABULAR_DATA_ARRAY_OUTPUT_KEY,
    TABULAR_DATA_INPUT_NODE_TYPE_ID,
    TABULAR_DATA_TABLE_OUTPUT_KEY,
    TabularDataInputNodePlugin,
)
from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.node_specs import (
    DynamicPortGroupSpec,
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import (
    ARRAY_DATA_REF_TYPE_ID,
    DOUBLE_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
)
from ea_node_editor.ui.graph_interactions import GraphInteractions
from ea_node_editor.ui.port_availability import (
    clear_port_availability_runtime_workspace,
    observe_node_outputs,
    port_availability_for_node,
)
from ea_node_editor.ui_qml.graph_scene_payload import GraphScenePayloadBuilder


class _GraphScene:
    def __init__(self, model: GraphModel, workspace_id: str) -> None:
        self.model = model
        self.workspace_id = workspace_id

    def current_workspace(self):
        return self.model.project.workspaces[self.workspace_id]

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        return self.model.add_edge(
            self.workspace_id,
            source_node_id,
            source_port,
            target_node_id,
            target_port,
        ).edge_id

    def remove_edge(self, edge_id: str) -> None:
        self.model.remove_edge(self.workspace_id, edge_id)

    def move_edge_endpoint(
        self,
        edge_id: str,
        endpoint: str,
        node_id: str,
        port_key: str,
        append_requested: bool = False,
    ) -> bool:
        return self.model.validated_mutations(
            self.workspace_id,
            _registry(),
        ).move_edge_endpoint(
            edge_id,
            endpoint,
            node_id,
            port_key,
            append_requested,
        )

    def remove_node(self, node_id: str) -> None:
        self.model.remove_node(self.workspace_id, node_id)

    def set_node_title(self, node_id: str, title: str) -> None:
        self.model.set_node_title(self.workspace_id, node_id, title)

    def selectedItems(self) -> list[Any]:
        return []


class _ArraySinkPlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="tests.array_sink",
            display_name="Array Sink",
            category_path=("Tests",),
            icon="test",
            ports=(
                PortSpec(
                    "array",
                    "in",
                    "data",
                    ARRAY_DATA_REF_TYPE_ID,
                    required=False,
                ),
            ),
            properties=(),
        )

    def execute(self, _ctx):  # noqa: ANN001
        raise NotImplementedError


def _resolved_test_outputs(properties) -> tuple[PortSpec, ...]:  # noqa: ANN001
    return tuple(
        PortSpec(
            key,
            "out",
            "data",
            DOUBLE_DATA_TYPE_ID,
            label="Resolved label",
            data_access="list",
            exposed=False,
            accepted_data_types=(DOUBLE_DATA_TYPE_ID, INTEGER_DATA_TYPE_ID),
            display_tier="advanced",
            description="Resolved dynamic output.",
        )
        for key in properties["output_names"]
    )


def _next_test_output(_properties) -> str:  # noqa: ANN001
    return "next_output"


def _registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register_descriptor(TabularDataInputNodePlugin().spec(), TabularDataInputNodePlugin)
    registry.register(_ArraySinkPlugin)
    return registry


def _tabular_node(model: GraphModel, path: Path | str = ""):
    workspace = model.active_workspace
    return model.add_node(
        workspace.workspace_id,
        TABULAR_DATA_INPUT_NODE_TYPE_ID,
        "Tabular Data Input",
        0,
        0,
        properties={"path": str(path)},
    )


def test_tabular_static_table_marks_array_output_unavailable(tmp_path: Path) -> None:
    source = tmp_path / "rows.csv"
    source.write_text("name,value\nalpha,1\n", encoding="utf-8")
    model = GraphModel()
    workspace = model.active_workspace
    node = _tabular_node(model, source)
    spec = TabularDataInputNodePlugin().spec()

    availability = port_availability_for_node(workspace=workspace, node=node, spec=spec)

    assert availability[TABULAR_DATA_TABLE_OUTPUT_KEY].availability == "available"
    assert availability[TABULAR_DATA_ARRAY_OUTPUT_KEY].availability == "unavailable"
    assert availability[TABULAR_DATA_ARRAY_OUTPUT_KEY].blocks_new_connections is True
    assert availability[TABULAR_DATA_ARRAY_OUTPUT_KEY].warns_existing_connection is True


def test_tabular_static_array_marks_table_output_unavailable(tmp_path: Path) -> None:
    numpy = pytest.importorskip("numpy")
    source = tmp_path / "array.npy"
    numpy.save(source, numpy.arange(4).reshape(2, 2))
    model = GraphModel()
    workspace = model.active_workspace
    node = _tabular_node(model, source)
    spec = TabularDataInputNodePlugin().spec()

    availability = port_availability_for_node(workspace=workspace, node=node, spec=spec)

    assert availability[TABULAR_DATA_TABLE_OUTPUT_KEY].availability == "unavailable"
    assert availability[TABULAR_DATA_ARRAY_OUTPUT_KEY].availability == "available"


def test_tabular_empty_path_and_dynamic_path_without_observation_stay_auto() -> None:
    model = GraphModel()
    workspace = model.active_workspace
    source = _tabular_node(model)
    path_source = model.add_node(workspace.workspace_id, "tests.path_source", "Path Source", -160, 0)
    model.add_edge(
        workspace.workspace_id,
        path_source.node_id,
        "path",
        source.node_id,
        "path",
    )
    spec = TabularDataInputNodePlugin().spec()

    availability = port_availability_for_node(workspace=workspace, node=source, spec=spec)

    assert availability[TABULAR_DATA_TABLE_OUTPUT_KEY].availability == "auto"
    assert availability[TABULAR_DATA_ARRAY_OUTPUT_KEY].availability == "auto"


def test_tabular_dynamic_path_uses_last_runtime_observation() -> None:
    model = GraphModel()
    workspace = model.active_workspace
    source = _tabular_node(model)
    path_source = model.add_node(workspace.workspace_id, "tests.path_source", "Path Source", -160, 0)
    model.add_edge(workspace.workspace_id, path_source.node_id, "path", source.node_id, "path")
    spec = TabularDataInputNodePlugin().spec()

    observe_node_outputs(
        workspace_id=workspace.workspace_id,
        node_id=source.node_id,
        node_type_id=source.type_id,
        outputs={TABULAR_DATA_ARRAY_OUTPUT_KEY: object()},
    )
    availability = port_availability_for_node(workspace=workspace, node=source, spec=spec)

    assert availability[TABULAR_DATA_TABLE_OUTPUT_KEY].availability == "unavailable"
    assert availability[TABULAR_DATA_ARRAY_OUTPUT_KEY].availability == "available"
    clear_port_availability_runtime_workspace(workspace.workspace_id)


def test_graph_payload_flags_unavailable_port_and_existing_edge(tmp_path: Path) -> None:
    source_path = tmp_path / "rows.csv"
    source_path.write_text("name,value\nalpha,1\n", encoding="utf-8")
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    source = _tabular_node(model, source_path)
    sink = model.add_node(workspace.workspace_id, "tests.array_sink", "Array Sink", 240, 0)
    model.add_edge(workspace.workspace_id, source.node_id, TABULAR_DATA_ARRAY_OUTPUT_KEY, sink.node_id, "array")

    nodes_payload, _backdrops, _minimap, edges_payload = GraphScenePayloadBuilder().rebuild_partitioned_models(
        model=model,
        registry=registry,
        workspace_id=workspace.workspace_id,
        scope_path=(),
        graph_theme_bridge=None,
    )
    tabular_payload = next(item for item in nodes_payload if item["node_id"] == source.node_id)
    array_port = next(port for port in tabular_payload["ports"] if port["key"] == TABULAR_DATA_ARRAY_OUTPUT_KEY)

    assert array_port["availability"] == "unavailable"
    assert array_port["inactive"] is True
    assert "Selected object is a table" in array_port["availability_reason"]
    assert edges_payload[0]["availability_warning"] is True
    assert "Selected object is a table" in edges_payload[0]["availability_reason"]
    assert len(workspace.edges) == 1


def test_connect_ports_rejects_new_unavailable_output_connection(tmp_path: Path) -> None:
    source_path = tmp_path / "rows.csv"
    source_path.write_text("name,value\nalpha,1\n", encoding="utf-8")
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    source = _tabular_node(model, source_path)
    sink = model.add_node(workspace.workspace_id, "tests.array_sink", "Array Sink", 240, 0)

    result = GraphInteractions(_GraphScene(model, workspace.workspace_id), registry).connect_ports(
        source.node_id,
        TABULAR_DATA_ARRAY_OUTPUT_KEY,
        sink.node_id,
        "array",
    )

    assert result.ok is False
    assert "Selected object is a table" in result.message
    assert workspace.edges == {}


def test_move_edge_endpoint_rejects_existing_unavailable_connection(tmp_path: Path) -> None:
    source_path = tmp_path / "rows.csv"
    source_path.write_text("name,value\nalpha,1\n", encoding="utf-8")
    registry = _registry()
    model = GraphModel()
    workspace = model.active_workspace
    source = _tabular_node(model, source_path)
    sink_a = model.add_node(workspace.workspace_id, "tests.array_sink", "Array A", 240, 0)
    sink_b = model.add_node(workspace.workspace_id, "tests.array_sink", "Array B", 240, 120)
    edge = model.add_edge(
        workspace.workspace_id,
        source.node_id,
        TABULAR_DATA_ARRAY_OUTPUT_KEY,
        sink_a.node_id,
        "array",
    )

    result = GraphInteractions(_GraphScene(model, workspace.workspace_id), registry).move_edge_endpoint(
        edge.edge_id,
        "target",
        sink_b.node_id,
        "array",
    )

    assert result.ok is False
    assert "Selected object is a table" in result.message
    assert workspace.edges[edge.edge_id].target_node_id == sink_a.node_id

    disconnected = GraphInteractions(
        _GraphScene(model, workspace.workspace_id),
        registry,
    ).move_edge_endpoint(edge.edge_id, "target", "", "")

    assert disconnected.ok is True
    assert edge.edge_id not in workspace.edges


def test_effective_ports_project_dynamic_port_metadata_without_node_type_branches() -> None:
    spec = NodeTypeSpec(
        type_id="tests.dynamic_metadata",
        display_name="Dynamic Metadata",
        category_path=("Tests",),
        icon="",
        ports=(
            PortSpec(
                "static",
                "in",
                "data",
                STRING_DATA_TYPE_ID,
                required=False,
            ),
        ),
        properties=(
            PropertySpec(
                "output_names",
                "json",
                ["dynamic"],
                "Outputs",
                inspector_visible=False,
            ),
        ),
        dynamic_port_groups=(
            DynamicPortGroupSpec(
                "outputs",
                "output_names",
                "out",
                _resolved_test_outputs,
                _next_test_output,
                rename_mode="label",
            ),
        ),
    )
    node = NodeInstance(
        node_id="dynamic",
        type_id=spec.type_id,
        title="Dynamic",
        x=0,
        y=0,
        properties={"output_names": ["dynamic"]},
        exposed_ports={"dynamic": True},
        port_labels={"dynamic": "Instance label"},
    )

    dynamic = next(
        port
        for port in effective_ports(node=node, spec=spec, workspace_nodes={})
        if port.key == "dynamic"
    )

    assert dynamic.label == "Instance label"
    assert dynamic.direction == "out"
    assert dynamic.kind == "data"
    assert dynamic.data_type == DOUBLE_DATA_TYPE_ID
    assert dynamic.data_access == "list"
    assert dynamic.required is False
    assert dynamic.exposed is True
    assert dynamic.accepted_data_types == (
        DOUBLE_DATA_TYPE_ID,
        INTEGER_DATA_TYPE_ID,
    )
    assert dynamic.display_tier == "advanced"
    assert dynamic.description == "Resolved dynamic output."
