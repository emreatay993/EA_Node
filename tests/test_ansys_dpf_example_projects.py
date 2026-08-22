from __future__ import annotations

import json
import queue
import unittest
from pathlib import Path
from typing import Any

import pytest

from ea_node_editor.execution.protocol import coerce_start_run_command
from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.runtime_contracts import DataTree, deserialize_runtime_value


_EXAMPLE_RELATIVE_PATH = (
    Path("examples") / "ansys_dpf" / "named_selection_time_result_viewer.cxproj"
)
_CURATED_EXAMPLE_RELATIVE_PATH = (
    Path("examples") / "ansys_dpf" / "curated_result_viewer.cxproj"
)
_MIN_MAX_EXAMPLE_RELATIVE_PATH = (
    Path("examples") / "ansys_dpf" / "displacement_min_max.cxproj"
)
_STRESS_XY_EXAMPLE_RELATIVE_PATH = (
    Path("examples") / "ansys_dpf" / "stress_xy_named_selection_add_fc.cxproj"
)
_MODE_SHAPE_EXAMPLE_RELATIVE_PATH = (
    Path("examples") / "ansys_dpf" / "mode_shape_viewer.cxproj"
)
_TIME_HISTORY_EXAMPLE_RELATIVE_PATH = (
    Path("examples") / "ansys_dpf" / "time_history_probe_line_plot.cxproj"
)
_STRESS_INVARIANTS_EXAMPLE_RELATIVE_PATH = (
    Path("examples") / "ansys_dpf" / "stress_invariants_table_export.cxproj"
)
_FIXTURE_RESULT_RELATIVE_PATH = Path(
    "..",
    "..",
    "tests",
    "ansys_dpf_core",
    "example_outputs",
    "static_analysis_1_bolted_joint",
    "file.rst",
)
_MODAL_FIXTURE_RESULT_RELATIVE_PATH = Path(
    "..",
    "..",
    "tests",
    "ansys_dpf_core",
    "example_outputs",
    "modal_analysis_1_bolted_joint",
    "file.rst",
)


class AnsysDpfExampleProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.project_path = cls.repo_root / _EXAMPLE_RELATIVE_PATH
        cls.registry = build_default_registry()
        cls.serializer = JsonProjectSerializer(cls.registry)
        cls.project = cls.serializer.load(str(cls.project_path))
        cls.workspace = cls.project.workspaces[cls.project.active_workspace_id]

    def _node_by_type(self, type_id: str) -> Any:
        matches = [
            node for node in self.workspace.nodes.values() if node.type_id == type_id
        ]
        self.assertEqual(
            len(matches),
            1,
            f"Expected exactly one {type_id!r} node in {_EXAMPLE_RELATIVE_PATH}, got {matches!r}",
        )
        return matches[0]

    def _node_by_type_in_workspace(
        self, workspace: Any, type_id: str, example_path: Path
    ) -> Any:
        matches = [node for node in workspace.nodes.values() if node.type_id == type_id]
        self.assertEqual(
            len(matches),
            1,
            f"Expected exactly one {type_id!r} node in {example_path}, got {matches!r}",
        )
        return matches[0]

    def test_all_committed_dpf_examples_use_current_dataflow_format(self) -> None:
        retired_type_ids = {
            "core.start",
            "core.end",
            "core.branch",
            "core.on_failure",
            "hpc.on_status",
        }
        retired_port_keys = {
            "exec",
            "exec_in",
            "exec_out",
            "completed",
            "completed_in",
            "completed_out",
            "failed",
            "failed_in",
            "failed_out",
            "on_failed",
        }

        for project_path in sorted(
            (self.repo_root / "examples" / "ansys_dpf").glob("*.cxproj")
        ):
            with self.subTest(project=project_path.name):
                document = json.loads(project_path.read_text(encoding="utf-8"))
                self.assertEqual(document["schema_version"], 5)
                for workspace_doc in document["workspaces"]:
                    self.assertTrue(
                        retired_type_ids.isdisjoint(
                            node_doc["type_id"] for node_doc in workspace_doc["nodes"]
                        )
                    )
                    for node_doc in workspace_doc["nodes"]:
                        for metadata_key in ("exposed_ports", "port_labels"):
                            self.assertTrue(
                                retired_port_keys.isdisjoint(
                                    node_doc.get(metadata_key, {})
                                )
                            )
                    input_orders: dict[tuple[str, str], list[int]] = {}
                    for edge_doc in workspace_doc["edges"]:
                        self.assertNotIn(edge_doc["source_port_key"], retired_port_keys)
                        self.assertNotIn(edge_doc["target_port_key"], retired_port_keys)
                        self.assertTrue(edge_doc["enabled"])
                        input_key = (
                            edge_doc["target_node_id"],
                            edge_doc["target_port_key"],
                        )
                        input_orders.setdefault(input_key, []).append(
                            edge_doc["input_order"]
                        )
                    for orders in input_orders.values():
                        self.assertEqual(sorted(orders), list(range(len(orders))))

                self.serializer.load(str(project_path))

    def test_named_selection_time_result_viewer_example_is_discoverable_and_focused(
        self,
    ) -> None:
        self.assertEqual(
            self.project.name, "DPF Named Selection Time Result Viewer Example"
        )
        self.assertEqual(self.workspace.name, "DPF Named Selection Time Result Viewer")
        self.assertEqual(len(self.project.workspaces), 1)

        result_file = self._node_by_type("dpf.result_file")
        model = self._node_by_type("dpf.model")
        mesh_scoping = self._node_by_type("dpf.scoping.mesh")
        mesh_extract = self._node_by_type("dpf.mesh_extract")
        result_field = self._node_by_type("dpf.result_field")
        viewer = self._node_by_type("dpf.viewer")

        self.assertEqual(
            result_file.properties["path"],
            _FIXTURE_RESULT_RELATIVE_PATH.as_posix(),
        )
        fixture_path = (
            self.project_path.parent / _FIXTURE_RESULT_RELATIVE_PATH
        ).resolve()
        self.assertTrue(fixture_path.exists())

        self.assertEqual(mesh_scoping.properties["selection_mode"], "named_selection")
        self.assertEqual(mesh_scoping.properties["named_selection"], "BOLT_NODES")
        self.assertEqual(mesh_scoping.properties["time_values"], "2.0")

        self.assertEqual(result_field.properties["result_name"], "displacement")
        self.assertEqual(result_field.properties.get("set_ids", ""), "")
        self.assertEqual(result_field.properties["time_values"], "2.0")

        edge_signatures = {
            (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
            )
            for edge in self.workspace.edges.values()
        }
        self.assertIn(
            (result_file.node_id, "result_file", model.node_id, "result_file"),
            edge_signatures,
        )
        self.assertIn(
            (mesh_scoping.node_id, "scoping", result_field.node_id, "mesh_scoping"),
            edge_signatures,
        )
        self.assertIn(
            (mesh_scoping.node_id, "scoping", mesh_extract.node_id, "mesh_scoping"),
            edge_signatures,
        )
        self.assertIn(
            (result_field.node_id, "field", viewer.node_id, "field"), edge_signatures
        )
        self.assertIn(
            (mesh_extract.node_id, "mesh", viewer.node_id, "mesh"), edge_signatures
        )
        self.assertIn(
            (model.node_id, "model", viewer.node_id, "model"), edge_signatures
        )

    def test_curated_result_viewer_example_is_discoverable_and_focused(self) -> None:
        project_path = self.repo_root / _CURATED_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]

        self.assertEqual(project.name, "DPF Curated Result Viewer Example")
        self.assertEqual(workspace.name, "DPF Curated Result Viewer")
        self.assertEqual(len(project.workspaces), 1)

        viewer = self._node_by_type_in_workspace(
            workspace,
            "dpf.workflow.result_viewer",
            _CURATED_EXAMPLE_RELATIVE_PATH,
        )

        self.assertEqual(
            viewer.properties["path"], _FIXTURE_RESULT_RELATIVE_PATH.as_posix()
        )
        fixture_path = (project_path.parent / _FIXTURE_RESULT_RELATIVE_PATH).resolve()
        self.assertTrue(fixture_path.exists())
        self.assertEqual(viewer.properties["result_name"], "displacement")
        self.assertEqual(viewer.properties["selection_mode"], "named_selection")
        self.assertEqual(viewer.properties["named_selection"], "BOLT_NODES")
        self.assertEqual(viewer.properties["location"], "nodal")
        self.assertEqual(viewer.properties["time_scope_mode"], "time_values")
        self.assertEqual(viewer.properties.get("set_ids", ""), "")
        self.assertEqual(viewer.properties["time_values"], "2.0")
        self.assertTrue(viewer.properties["show_mesh_edges"])

        edge_signatures = {
            (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
            )
            for edge in workspace.edges.values()
        }
        self.assertEqual(edge_signatures, set())

    def _edge_signatures(self, workspace: Any) -> set[tuple[str, str, str, str]]:
        return {
            (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
            )
            for edge in workspace.edges.values()
        }

    def _run_example(
        self, project_path: Path, project: Any, workspace: Any, run_id: str
    ) -> list[dict[str, Any]]:
        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = build_runtime_snapshot(
            project,
            workspace_id=workspace.workspace_id,
            registry=self.registry,
        )
        run_workflow(
            coerce_start_run_command(
                {
                    "run_id": run_id,
                    "project_path": str(project_path),
                    "workspace_id": workspace.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                },
                catalog=self.registry.data_types,
            ),
            event_queue,
        )
        events: list[dict[str, Any]] = []
        while not event_queue.empty():
            events.append(event_queue.get())
        event_types = [str(event.get("type", "")) for event in events]
        self.assertIn("run_started", event_types)
        self.assertIn("run_completed", event_types)
        self.assertNotIn("run_failed", event_types)
        failed_settlements = [
            (
                str(event.get("node_id", "")),
                str(event.get("status", "")),
                event.get("errors", ()),
            )
            for event in events
            if str(event.get("type", "")) == "node_settled"
            and str(event.get("status", "")) in {"failed", "blocked"}
        ]
        self.assertFalse(
            failed_settlements,
            f"Example emitted failed or blocked node results: {failed_settlements!r}",
        )
        return events

    def _node_outputs(
        self, events: list[dict[str, Any]], node_id: str
    ) -> dict[str, Any]:
        settled = next(
            event
            for event in events
            if str(event.get("type", "")) == "node_settled"
            and str(event.get("node_id", "")) == node_id
        )
        self.assertEqual(settled.get("status"), "completed")
        outputs: dict[str, Any] = {}
        for port_key, result in dict(settled.get("outputs", {})).items():
            self.assertIsInstance(result, dict)
            if result.get("status") != "value":
                continue
            tree = deserialize_runtime_value(
                result["value"],
                catalog=self.registry.data_types,
            )
            self.assertIsInstance(tree, DataTree)
            self.assertEqual(tree.branch_count, 1)
            self.assertEqual(len(tree.branches[0][1]), 1)
            outputs[port_key] = tree.branches[0][1][0]
        return outputs

    def test_displacement_min_max_example_uses_envelope_workflow_node(self) -> None:
        project_path = self.repo_root / _MIN_MAX_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]

        source = self._node_by_type_in_workspace(
            workspace, "dpf.workflow.result_source", _MIN_MAX_EXAMPLE_RELATIVE_PATH
        )
        envelope = self._node_by_type_in_workspace(
            workspace, "dpf.workflow.min_max_envelope", _MIN_MAX_EXAMPLE_RELATIVE_PATH
        )

        self.assertEqual(
            source.properties["path"], _FIXTURE_RESULT_RELATIVE_PATH.as_posix()
        )
        self.assertEqual(envelope.properties["result_name"], "displacement")
        self.assertEqual(envelope.properties["selection_mode"], "all")
        self.assertEqual(envelope.properties["time_scope_mode"], "all_sets")
        self.assertEqual(envelope.properties.get("set_ids", ""), "")

        edge_signatures = self._edge_signatures(workspace)
        self.assertIn(
            (source.node_id, "model", envelope.node_id, "model"),
            edge_signatures,
        )

    def test_stress_xy_example_adds_fields_through_field_math_node(self) -> None:
        project_path = self.repo_root / _STRESS_XY_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]

        stress_x = self._node_by_type_in_workspace(
            workspace, "dpf.op.result.stress_x", _STRESS_XY_EXAMPLE_RELATIVE_PATH
        )
        stress_y = self._node_by_type_in_workspace(
            workspace, "dpf.op.result.stress_y", _STRESS_XY_EXAMPLE_RELATIVE_PATH
        )
        field_math = self._node_by_type_in_workspace(
            workspace, "dpf.workflow.field_math", _STRESS_XY_EXAMPLE_RELATIVE_PATH
        )
        self.assertFalse(
            [
                node
                for node in workspace.nodes.values()
                if node.type_id == "dpf.op.math.add_fc"
            ],
            "The raw add_fc mirror should be replaced by DPF Field Math",
        )

        self.assertEqual(field_math.properties["operation"], "add")
        edge_signatures = self._edge_signatures(workspace)
        self.assertIn(
            (stress_x.node_id, "fields_container_2", field_math.node_id, "a"),
            edge_signatures,
        )
        self.assertIn(
            (stress_y.node_id, "fields_container_2", field_math.node_id, "b"),
            edge_signatures,
        )

    def test_mode_shape_viewer_example_is_discoverable_and_focused(self) -> None:
        project_path = self.repo_root / _MODE_SHAPE_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]

        viewer = self._node_by_type_in_workspace(
            workspace,
            "dpf.workflow.mode_shape_viewer",
            _MODE_SHAPE_EXAMPLE_RELATIVE_PATH,
        )

        self.assertEqual(
            viewer.properties["path"], _MODAL_FIXTURE_RESULT_RELATIVE_PATH.as_posix()
        )
        fixture_path = (
            project_path.parent / _MODAL_FIXTURE_RESULT_RELATIVE_PATH
        ).resolve()
        self.assertTrue(fixture_path.exists())
        self.assertEqual(viewer.properties["mode"], "2")
        self.assertEqual(viewer.properties["deform_scale"], "auto")

        self.assertEqual(self._edge_signatures(workspace), set())

    def test_time_history_probe_example_feeds_line_plot_with_all_frames(self) -> None:
        project_path = self.repo_root / _TIME_HISTORY_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]

        source = self._node_by_type_in_workspace(
            workspace, "dpf.workflow.result_source", _TIME_HISTORY_EXAMPLE_RELATIVE_PATH
        )
        probe = self._node_by_type_in_workspace(
            workspace,
            "dpf.workflow.time_history_probe",
            _TIME_HISTORY_EXAMPLE_RELATIVE_PATH,
        )
        plot = self._node_by_type_in_workspace(
            workspace, "dpf.plot.line", _TIME_HISTORY_EXAMPLE_RELATIVE_PATH
        )

        self.assertEqual(probe.properties["selection_mode"], "named_selection")
        self.assertEqual(probe.properties["named_selection"], "BOLT_NODES")
        self.assertEqual(probe.properties["time_scope_mode"], "all_sets")
        self.assertEqual(plot.properties["frame_selector"], "all")

        edge_signatures = self._edge_signatures(workspace)
        self.assertIn(
            (source.node_id, "model", probe.node_id, "model"), edge_signatures
        )
        self.assertIn(
            (probe.node_id, "series", plot.node_id, "series"), edge_signatures
        )

    def test_stress_invariants_example_exports_von_mises_table(self) -> None:
        project_path = self.repo_root / _STRESS_INVARIANTS_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]

        source = self._node_by_type_in_workspace(
            workspace,
            "dpf.workflow.result_source",
            _STRESS_INVARIANTS_EXAMPLE_RELATIVE_PATH,
        )
        invariants = self._node_by_type_in_workspace(
            workspace,
            "dpf.workflow.stress_invariants",
            _STRESS_INVARIANTS_EXAMPLE_RELATIVE_PATH,
        )
        export = self._node_by_type_in_workspace(
            workspace,
            "dpf.workflow.table_export",
            _STRESS_INVARIANTS_EXAMPLE_RELATIVE_PATH,
        )

        self.assertEqual(invariants.properties["invariant"], "von_mises")
        self.assertEqual(invariants.properties["named_selection"], "BOLT_NODES")
        self.assertEqual(invariants.properties["location"], "nodal")
        self.assertEqual(invariants.properties["time_scope_mode"], "set_ids")

        edge_signatures = self._edge_signatures(workspace)
        self.assertIn(
            (source.node_id, "model", invariants.node_id, "model"), edge_signatures
        )
        self.assertIn(
            (invariants.node_id, "fields", export.node_id, "fields"), edge_signatures
        )
        self.assertIn(
            (source.node_id, "model", export.node_id, "model"), edge_signatures
        )

    def test_displacement_min_max_example_runs_when_dpf_dependencies_exist(
        self,
    ) -> None:
        pytest.importorskip("ansys.dpf.core")

        project_path = self.repo_root / _MIN_MAX_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]
        envelope = self._node_by_type_in_workspace(
            workspace, "dpf.workflow.min_max_envelope", _MIN_MAX_EXAMPLE_RELATIVE_PATH
        )

        events = self._run_example(
            project_path, project, workspace, "run_dpf_min_max_example"
        )
        outputs = self._node_outputs(events, envelope.node_id)
        self.assertIn("envelope_min", outputs)
        self.assertIn("envelope_max", outputs)
        self.assertIn("summary", outputs)
        self.assertEqual(len(outputs.get("per_set_table", [])), 2)

    def test_mode_shape_viewer_example_runs_when_dpf_dependencies_exist(self) -> None:
        pytest.importorskip("ansys.dpf.core")
        pytest.importorskip("pyvista")

        project_path = self.repo_root / _MODE_SHAPE_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]
        viewer = self._node_by_type_in_workspace(
            workspace,
            "dpf.workflow.mode_shape_viewer",
            _MODE_SHAPE_EXAMPLE_RELATIVE_PATH,
        )

        events = self._run_example(
            project_path, project, workspace, "run_dpf_mode_shape_example"
        )
        outputs = self._node_outputs(events, viewer.node_id)
        self.assertIn("session", outputs)
        self.assertGreater(float(outputs.get("frequency", 0.0)), 0.0)

    def test_named_selection_time_result_viewer_example_runs_when_dpf_dependencies_exist(
        self,
    ) -> None:
        pytest.importorskip("ansys.dpf.core")
        pytest.importorskip("pyvista")

        viewer = self._node_by_type("dpf.viewer")
        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = build_runtime_snapshot(
            self.project,
            workspace_id=self.workspace.workspace_id,
            registry=self.registry,
        )
        run_workflow(
            coerce_start_run_command(
                {
                    "run_id": "run_dpf_named_selection_time_result_viewer",
                    "project_path": str(self.project_path),
                    "workspace_id": self.workspace.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                },
                catalog=self.registry.data_types,
            ),
            event_queue,
        )

        events: list[dict[str, Any]] = []
        while not event_queue.empty():
            events.append(event_queue.get())
        event_types = [str(event.get("type", "")) for event in events]

        self.assertIn("run_started", event_types)
        self.assertIn("run_completed", event_types)
        self.assertNotIn("run_failed", event_types)
        self.assertFalse(
            any(
                str(event.get("type", "")) == "node_settled"
                and str(event.get("status", "")) in {"failed", "blocked"}
                for event in events
            ),
            f"Example emitted failed or blocked node results: {events!r}",
        )

        self.assertIn("session", self._node_outputs(events, viewer.node_id))

    def test_curated_result_viewer_example_runs_when_dpf_dependencies_exist(
        self,
    ) -> None:
        pytest.importorskip("ansys.dpf.core")
        pytest.importorskip("pyvista")

        project_path = self.repo_root / _CURATED_EXAMPLE_RELATIVE_PATH
        project = self.serializer.load(str(project_path))
        workspace = project.workspaces[project.active_workspace_id]
        viewer = self._node_by_type_in_workspace(
            workspace,
            "dpf.workflow.result_viewer",
            _CURATED_EXAMPLE_RELATIVE_PATH,
        )
        event_queue: queue.Queue = queue.Queue()
        runtime_snapshot = build_runtime_snapshot(
            project,
            workspace_id=workspace.workspace_id,
            registry=self.registry,
        )
        run_workflow(
            coerce_start_run_command(
                {
                    "run_id": "run_dpf_curated_result_viewer",
                    "project_path": str(project_path),
                    "workspace_id": workspace.workspace_id,
                    "runtime_snapshot": runtime_snapshot,
                    "trigger": {},
                },
                catalog=self.registry.data_types,
            ),
            event_queue,
        )

        events: list[dict[str, Any]] = []
        while not event_queue.empty():
            events.append(event_queue.get())
        event_types = [str(event.get("type", "")) for event in events]

        self.assertIn("run_started", event_types)
        self.assertIn("run_completed", event_types)
        self.assertNotIn("run_failed", event_types)
        self.assertFalse(
            any(
                str(event.get("type", "")) == "node_settled"
                and str(event.get("status", "")) in {"failed", "blocked"}
                for event in events
            ),
            f"Example emitted failed or blocked node results: {events!r}",
        )

        outputs = self._node_outputs(events, viewer.node_id)
        self.assertIn("session", outputs)
        self.assertIn("fields", outputs)
        self.assertNotIn("field", outputs)


if __name__ == "__main__":
    unittest.main()
