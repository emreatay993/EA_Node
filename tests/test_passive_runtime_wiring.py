from __future__ import annotations

import unittest

from ea_node_editor.execution.compiler import compile_runtime_workspace, compile_workspace_document
from ea_node_editor.execution.runtime_dto import RuntimeWorkspace
from ea_node_editor.graph.effective_ports import effective_ports
from ea_node_editor.graph.model import GraphModel
from ea_node_editor.graph.normalization import normalize_project_for_registry
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.decorators import in_port, node_type, out_port
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import ExecutionContext, NodeResult
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui.shell.runtime_clipboard import build_graph_fragment_payload
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


@node_type(
    type_id="tests.runtime_source",
    display_name="Runtime Source",
    category="Tests",
    icon="play_arrow",
    ports=(
        out_port("value", data_type="str"),
        out_port("exec_out", kind="exec"),
        out_port("flow_out", kind="flow"),
    ),
    properties=(),
)
class _RuntimeSourcePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"value": "ok"})


@node_type(
    type_id="tests.single_sink",
    display_name="Single Sink",
    category="Tests",
    icon="input",
    ports=(
        in_port("value", data_type="str"),
        in_port("exec_in", kind="exec"),
        in_port("flow_in", kind="flow"),
    ),
    properties=(),
)
class _SingleSinkPlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id="tests.multi_sink",
    display_name="Multi Sink",
    category="Tests",
    icon="input",
    ports=(
        in_port("value", data_type="str", allow_multiple_connections=True),
        in_port("exec_in", kind="exec", allow_multiple_connections=True),
    ),
    properties=(),
)
class _MultiSinkPlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id="tests.passive_note",
    display_name="Passive Note",
    category="Tests",
    icon="note",
    ports=(
        in_port("flow_in", kind="flow"),
        out_port("flow_out", kind="flow"),
    ),
    properties=(),
    runtime_behavior="passive",
    surface_family="annotation",
)
class _PassiveNotePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


def _build_runtime_registry() -> NodeRegistry:
    registry = NodeRegistry()
    for plugin in (
        _RuntimeSourcePlugin,
        _SingleSinkPlugin,
        _MultiSinkPlugin,
        _PassiveNotePlugin,
    ):
        registry.register(plugin)
    return registry


class PassiveRuntimeWiringTests(unittest.TestCase):
    def test_dynamic_subnode_ports_surface_allow_multiple_connections(self) -> None:
        registry = build_default_registry()
        model = GraphModel()
        workspace = model.active_workspace
        shell = model.add_node(workspace.workspace_id, "core.subnode", "Shell", 0.0, 0.0)
        pin = model.add_node(
            workspace.workspace_id,
            "core.subnode_input",
            "Input",
            0.0,
            0.0,
            properties={"label": "Input", "kind": "data", "data_type": "str"},
        )
        workspace.nodes[pin.node_id].parent_node_id = shell.node_id

        shell_ports = effective_ports(
            node=workspace.nodes[shell.node_id],
            spec=registry.get_spec("core.subnode"),
            workspace_nodes=workspace.nodes,
        )

        self.assertEqual(len(shell_ports), 1)
        self.assertFalse(shell_ports[0].allow_multiple_connections)

    def test_normalization_prunes_extra_incoming_edges_only_for_single_connection_ports(self) -> None:
        registry = _build_runtime_registry()
        model = GraphModel()
        workspace = model.active_workspace

        source_a = model.add_node(workspace.workspace_id, "tests.runtime_source", "A", 0.0, 0.0)
        source_b = model.add_node(workspace.workspace_id, "tests.runtime_source", "B", 0.0, 120.0)
        single_sink = model.add_node(workspace.workspace_id, "tests.single_sink", "Single", 280.0, 0.0)
        multi_sink = model.add_node(workspace.workspace_id, "tests.multi_sink", "Multi", 280.0, 160.0)

        model.add_edge(workspace.workspace_id, source_a.node_id, "value", single_sink.node_id, "value")
        model.add_edge(workspace.workspace_id, source_b.node_id, "value", single_sink.node_id, "value")
        model.add_edge(workspace.workspace_id, source_a.node_id, "value", multi_sink.node_id, "value")
        model.add_edge(workspace.workspace_id, source_b.node_id, "value", multi_sink.node_id, "value")

        normalize_project_for_registry(model.project, registry)

        single_incoming = [
            edge
            for edge in workspace.edges.values()
            if edge.target_node_id == single_sink.node_id and edge.target_port_key == "value"
        ]
        multi_incoming = [
            edge
            for edge in workspace.edges.values()
            if edge.target_node_id == multi_sink.node_id and edge.target_port_key == "value"
        ]

        self.assertEqual(len(single_incoming), 1)
        self.assertEqual(len(multi_incoming), 2)

    def test_compile_workspace_document_excludes_passive_nodes_and_flow_edges(self) -> None:
        registry = _build_runtime_registry()
        serializer = JsonProjectSerializer(registry)
        model = GraphModel()
        workspace = model.active_workspace

        source = model.add_node(workspace.workspace_id, "tests.runtime_source", "Source", 0.0, 0.0)
        target = model.add_node(workspace.workspace_id, "tests.single_sink", "Target", 320.0, 0.0)
        passive = model.add_node(workspace.workspace_id, "tests.passive_note", "Note", 160.0, 140.0)

        model.add_edge(workspace.workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        model.add_edge(workspace.workspace_id, source.node_id, "flow_out", target.node_id, "flow_in")
        model.add_edge(workspace.workspace_id, source.node_id, "flow_out", passive.node_id, "flow_in")

        workspace_doc = serializer.to_document(model.project)["workspaces"][0]
        compiled = compile_runtime_workspace(workspace_doc, registry=registry)
        self.assertIsInstance(compiled, RuntimeWorkspace)

        self.assertEqual(
            {node.node_id for node in compiled.nodes},
            {source.node_id, target.node_id},
        )
        self.assertEqual(
            [edge.to_document() for edge in compiled.edges],
            [
                {
                    "source_node_id": source.node_id,
                    "source_port_key": "exec_out",
                    "target_node_id": target.node_id,
                    "target_port_key": "exec_in",
                }
            ],
        )
        self.assertNotIn(passive.node_id, {node.node_id for node in compiled.nodes})
        self.assertEqual(compile_workspace_document(workspace_doc, registry=registry), compiled.to_document())

    def test_compile_workspace_document_respects_registry_multiplicity_and_port_resolution(self) -> None:
        registry = _build_runtime_registry()
        serializer = JsonProjectSerializer(registry)
        model = GraphModel()
        workspace = model.active_workspace

        source_a = model.add_node(workspace.workspace_id, "tests.runtime_source", "A", 0.0, 0.0)
        source_b = model.add_node(workspace.workspace_id, "tests.runtime_source", "B", 0.0, 120.0)
        single_sink = model.add_node(workspace.workspace_id, "tests.single_sink", "Single", 280.0, 0.0)
        multi_sink = model.add_node(workspace.workspace_id, "tests.multi_sink", "Multi", 280.0, 160.0)

        model.add_edge(workspace.workspace_id, source_a.node_id, "value", single_sink.node_id, "value")
        model.add_edge(workspace.workspace_id, source_b.node_id, "value", single_sink.node_id, "value")
        model.add_edge(workspace.workspace_id, source_a.node_id, "value", multi_sink.node_id, "value")
        model.add_edge(workspace.workspace_id, source_b.node_id, "value", multi_sink.node_id, "value")
        model.add_edge(workspace.workspace_id, source_a.node_id, "missing", multi_sink.node_id, "value")

        workspace_doc = serializer.to_document(model.project)["workspaces"][0]
        compiled = compile_runtime_workspace(workspace_doc, registry=registry)
        self.assertIsInstance(compiled, RuntimeWorkspace)

        self.assertEqual(
            {node.node_id for node in compiled.nodes},
            {source_a.node_id, source_b.node_id, single_sink.node_id, multi_sink.node_id},
        )
        compiled_edges = {
            (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
            )
            for edge in compiled.edges
        }
        self.assertEqual(
            {
                edge
                for edge in compiled_edges
                if edge[2] == multi_sink.node_id and edge[3] == "value"
            },
            {
                (source_a.node_id, "value", multi_sink.node_id, "value"),
                (source_b.node_id, "value", multi_sink.node_id, "value"),
            },
        )
        single_sink_edges = {
            edge
            for edge in compiled_edges
            if edge[2] == single_sink.node_id and edge[3] == "value"
        }
        self.assertEqual(len(single_sink_edges), 1)
        self.assertTrue(
            single_sink_edges
            <= {
                (source_a.node_id, "value", single_sink.node_id, "value"),
                (source_b.node_id, "value", single_sink.node_id, "value"),
            }
        )

    def test_compile_workspace_document_uses_subnode_contract_without_registry(self) -> None:
        registry = build_default_registry()
        serializer = JsonProjectSerializer(registry)
        model = GraphModel()
        workspace = model.active_workspace

        source = model.add_node(workspace.workspace_id, "core.start", "Start", 0.0, 0.0)
        shell = model.add_node(workspace.workspace_id, "core.subnode", "Shell", 260.0, 40.0)
        pin_in = model.add_node(
            workspace.workspace_id,
            "core.subnode_input",
            "Input",
            40.0,
            80.0,
            properties={"label": "In", "kind": "exec", "data_type": "str"},
        )
        inner = model.add_node(workspace.workspace_id, "core.logger", "Inner", 360.0, 100.0)
        pin_out = model.add_node(
            workspace.workspace_id,
            "core.subnode_output",
            "Output",
            520.0,
            80.0,
            properties={"label": "Out", "kind": "exec", "data_type": "str"},
        )
        target = model.add_node(workspace.workspace_id, "core.end", "End", 760.0, 40.0)

        workspace.nodes[pin_in.node_id].parent_node_id = shell.node_id
        workspace.nodes[inner.node_id].parent_node_id = shell.node_id
        workspace.nodes[pin_out.node_id].parent_node_id = shell.node_id

        model.add_edge(workspace.workspace_id, source.node_id, "exec_out", shell.node_id, pin_in.node_id)
        model.add_edge(workspace.workspace_id, pin_in.node_id, "pin", inner.node_id, "exec_in")
        model.add_edge(workspace.workspace_id, inner.node_id, "exec_out", pin_out.node_id, "pin")
        model.add_edge(workspace.workspace_id, shell.node_id, pin_out.node_id, target.node_id, "exec_in")

        workspace_doc = serializer.to_document(model.project)["workspaces"][0]
        compiled = compile_runtime_workspace(workspace_doc, registry=None)
        self.assertIsInstance(compiled, RuntimeWorkspace)

        self.assertEqual(
            {node.node_id for node in compiled.nodes},
            {source.node_id, inner.node_id, target.node_id},
        )
        self.assertCountEqual(
            [edge.to_document() for edge in compiled.edges],
            [
                {
                    "source_node_id": inner.node_id,
                    "source_port_key": "exec_out",
                    "target_node_id": target.node_id,
                    "target_port_key": "exec_in",
                },
                {
                    "source_node_id": source.node_id,
                    "source_port_key": "exec_out",
                    "target_node_id": inner.node_id,
                    "target_port_key": "exec_in",
                },
            ],
        )

    def test_fragment_validation_respects_registry_connection_multiplicity(self) -> None:
        registry = _build_runtime_registry()
        model = GraphModel()
        workspace = model.active_workspace
        scene = GraphSceneBridge()
        scene.set_workspace(model, registry, workspace.workspace_id)

        single_fragment = build_graph_fragment_payload(
            nodes=[
                {"ref_id": "src_a", "type_id": "tests.runtime_source", "title": "A", "x": 0.0, "y": 0.0},
                {"ref_id": "src_b", "type_id": "tests.runtime_source", "title": "B", "x": 0.0, "y": 120.0},
                {"ref_id": "sink", "type_id": "tests.single_sink", "title": "Sink", "x": 240.0, "y": 60.0},
            ],
            edges=[
                {
                    "source_ref_id": "src_a",
                    "source_port_key": "value",
                    "target_ref_id": "sink",
                    "target_port_key": "value",
                },
                {
                    "source_ref_id": "src_b",
                    "source_port_key": "value",
                    "target_ref_id": "sink",
                    "target_port_key": "value",
                },
            ],
        )
        multi_fragment = build_graph_fragment_payload(
            nodes=[
                {"ref_id": "src_a", "type_id": "tests.runtime_source", "title": "A", "x": 0.0, "y": 0.0},
                {"ref_id": "src_b", "type_id": "tests.runtime_source", "title": "B", "x": 0.0, "y": 120.0},
                {"ref_id": "sink", "type_id": "tests.multi_sink", "title": "Sink", "x": 240.0, "y": 60.0},
            ],
            edges=[
                {
                    "source_ref_id": "src_a",
                    "source_port_key": "value",
                    "target_ref_id": "sink",
                    "target_port_key": "value",
                },
                {
                    "source_ref_id": "src_b",
                    "source_port_key": "value",
                    "target_ref_id": "sink",
                    "target_port_key": "value",
                },
            ],
        )

        self.assertFalse(scene.paste_subgraph_fragment(single_fragment, 120.0, 120.0))
        self.assertEqual(len(workspace.nodes), 0)
        self.assertEqual(len(workspace.edges), 0)

        self.assertTrue(scene.paste_subgraph_fragment(multi_fragment, 120.0, 120.0))
        self.assertEqual(len(workspace.nodes), 3)
        self.assertEqual(len(workspace.edges), 2)


if __name__ == "__main__":
    unittest.main()
