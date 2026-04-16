from __future__ import annotations

import queue
import sys
import unittest
from pathlib import Path
from typing import Any

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

pytest.importorskip("ansys.dpf.core")
pytest.importorskip("pyvista")

from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer

_SHOWCASE_WORKSPACES: tuple[dict[str, Any], ...] = (
    {
        "name": "Demo 1 - Static Displacement Viewer",
        "final_type": "dpf.viewer",
        "output_key": "session",
        "completed_types": ("dpf.viewer",),
    },
    {
        "name": "Demo 2 - Static Stress Norm Export",
        "final_type": "dpf.export",
        "output_key": "dataset",
        "completed_types": ("dpf.export",),
    },
    {
        "name": "Demo 3 - Static Named Selection Mesh Viewer",
        "final_type": "dpf.viewer",
        "output_key": "session",
        "completed_types": ("dpf.viewer",),
    },
    {
        "name": "Demo 4 - Thermal Temperature Export",
        "final_type": "dpf.export",
        "output_key": "dataset",
        "completed_types": ("dpf.export",),
    },
    {
        "name": "Demo 5 - Generated Operator Displacement MinMax Viewer",
        "final_type": "dpf.viewer",
        "output_key": "session",
        "completed_types": (
            "dpf.op.result.displacement",
            "dpf.op.min_max.min_max_fc",
            "dpf.viewer",
        ),
    },
)


class Dene3DpfShowcaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.project_path = cls.repo_root / "dene3.sfe"
        cls.registry = build_default_registry()
        cls.serializer = JsonProjectSerializer(cls.registry)

    def _drain_events(self, event_queue: queue.Queue) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while not event_queue.empty():
            events.append(event_queue.get())
        return events

    def _workspace_node_id_by_type(self, workspace: Any, type_id: str) -> str:
        matches = [node.node_id for node in workspace.nodes.values() if node.type_id == type_id]
        self.assertEqual(
            len(matches),
            1,
            f"Expected exactly one node of type {type_id!r} in workspace {workspace.name!r}, got {matches!r}",
        )
        return matches[0]

    def test_saved_dene3_showcase_workspaces_run_from_project_path(self) -> None:
        self.assertTrue(self.project_path.exists(), f"Missing showcase file: {self.project_path}")
        project = self.serializer.load(str(self.project_path))

        workspace_by_name = {workspace.name: workspace for workspace in project.workspaces.values()}
        expected_names = [item["name"] for item in _SHOWCASE_WORKSPACES]
        for workspace_name in expected_names:
            self.assertIn(workspace_name, workspace_by_name, f"Missing showcase workspace {workspace_name!r}")

        first_demo_workspace = workspace_by_name[expected_names[0]]
        self.assertEqual(project.active_workspace_id, first_demo_workspace.workspace_id)

        for expectation in _SHOWCASE_WORKSPACES:
            workspace = workspace_by_name[expectation["name"]]
            final_node_id = self._workspace_node_id_by_type(workspace, expectation["final_type"])
            expected_completed_node_ids = {
                self._workspace_node_id_by_type(workspace, type_id)
                for type_id in expectation["completed_types"]
            }

            with self.subTest(workspace=workspace.name):
                event_queue: queue.Queue = queue.Queue()
                run_workflow(
                    {
                        "run_id": f"run_{workspace.workspace_id}",
                        "project_path": str(self.project_path),
                        "workspace_id": workspace.workspace_id,
                        "trigger": {},
                    },
                    event_queue,
                )
                events = self._drain_events(event_queue)
                event_types = [str(event.get("type", "")) for event in events]

                self.assertIn("run_started", event_types)
                self.assertIn("run_completed", event_types)
                self.assertNotIn("run_failed", event_types)
                self.assertFalse(
                    any(str(event.get("type", "")) == "node_failed" for event in events),
                    f"Workspace {workspace.name!r} emitted node_failed events: {events!r}",
                )

                completed_node_ids = {
                    str(event.get("node_id", ""))
                    for event in events
                    if str(event.get("type", "")) == "node_completed"
                }
                self.assertTrue(
                    expected_completed_node_ids.issubset(completed_node_ids),
                    f"Workspace {workspace.name!r} missing node completions for "
                    f"{expected_completed_node_ids - completed_node_ids!r}",
                )

                final_completion = next(
                    event
                    for event in events
                    if str(event.get("type", "")) == "node_completed"
                    and str(event.get("node_id", "")) == final_node_id
                )
                outputs = dict(final_completion.get("outputs", {}))
                self.assertIn(
                    expectation["output_key"],
                    outputs,
                    f"Workspace {workspace.name!r} final node outputs were {outputs!r}",
                )


if __name__ == "__main__":
    unittest.main()
