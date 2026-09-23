# Purpose: Slow end-to-end proof: spawn a private headless COREX via the launcher and drive the whole authoring loop over the public client.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_e2e_private_instance.py
"""Spawned private-instance end-to-end test (``slow`` suite, see scripts/verification_manifest.py).

One real COREX process is launched with ``CorexClient.launch("private", headless=True)``
(offscreen, isolated ``COREX_SESSION_STATE_DIR``, isolated discovery dir) and driven only
through the public client: build a flowchart with ``graph.apply`` + ``$refs``, style it,
group and collapse part of it into a subnode, annotate it, save, reopen, screenshot, and
quit. Nothing here touches Qt objects of the spawned app; the screenshot is decoded
locally only to prove it is not blank.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ea_node_editor.automation.client import CorexClient
from ea_node_editor.automation.discovery import ENV_DISCOVERY_DIR
from ea_node_editor.automation.errors import AutomationOpError

STARTUP_TIMEOUT_S = 180.0


def _distinct_sampled_colors(path: Path) -> int:
    from PyQt6.QtGui import QImage

    image = QImage(str(path))
    if image.isNull():
        return 0
    colors: set[int] = set()
    step_x = max(1, image.width() // 48)
    step_y = max(1, image.height() // 48)
    for y in range(0, image.height(), step_y):
        for x in range(0, image.width(), step_x):
            colors.add(image.pixel(x, y))
    return len(colors)


class PrivateInstanceEndToEndTests(unittest.TestCase):
    client: CorexClient
    _env_patch = None
    _temp: tempfile.TemporaryDirectory | None = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="corex-e2e-")
        root = Path(cls._temp.name)
        cls._env_patch = patch.dict(os.environ, {ENV_DISCOVERY_DIR: str(root / "discovery")})
        cls._env_patch.start()
        try:
            cls.client = CorexClient.launch("private", headless=True, startup_timeout_s=STARTUP_TIMEOUT_S)
        except AutomationOpError as exc:
            cls._env_patch.stop()
            cls._temp.cleanup()
            raise AssertionError(f"private COREX failed to start: {exc.code} {exc.message}\n{exc.details.get('log_tail', '')}") from exc
        cls.root = root

    @classmethod
    def tearDownClass(cls) -> None:
        handle = getattr(cls, "client", None) and cls.client.handle
        try:
            cls.client.close(quit_owned_instance=True)
        finally:
            if handle is not None and handle.process is not None:
                try:
                    handle.process.wait(timeout=30)
                except Exception:  # noqa: BLE001 - best effort; terminate() already ran
                    pass
            if cls._env_patch is not None:
                cls._env_patch.stop()
            if cls._temp is not None:
                cls._temp.cleanup()

    def test_full_authoring_loop_round_trips_and_renders(self) -> None:
        corex = self.client
        status = corex.call("app.status", {})
        self.assertEqual(status["mode"], "private")
        self.assertTrue(status["qt_platform"].startswith("offscreen"))
        self.assertFalse(any(status["busy"].values()), status["busy"])

        batch = corex.call(
            "graph.apply",
            {
                "label": "e2e flowchart",
                "ops": [
                    {"id": "start", "op": "node.add", "params": {"type_id": "passive.flowchart.start", "x": 0, "y": 0, "title": "Start"}},
                    {"id": "mesh", "op": "node.add", "params": {"type_id": "passive.flowchart.process", "x": 320, "y": 0, "title": "Mesh the part"}},
                    {"id": "solve", "op": "node.add", "params": {"type_id": "passive.flowchart.process", "x": 640, "y": 0, "title": "Solve"}},
                    {"id": "ok", "op": "node.add", "params": {"type_id": "passive.flowchart.decision", "x": 960, "y": 0, "title": "Converged?"}},
                    {"id": "done", "op": "node.add", "params": {"type_id": "passive.flowchart.end", "x": 1280, "y": 0, "title": "Report $100 budget"}},
                    {"op": "edge.connect", "params": {"source_node_id": "$start", "source_port": "right", "target_node_id": "$mesh", "target_port": "left"}},
                    {"op": "edge.connect", "params": {"source_node_id": "$mesh", "source_port": "right", "target_node_id": "$solve", "target_port": "left"}},
                    {"op": "edge.connect", "params": {"source_node_id": "$solve", "source_port": "right", "target_node_id": "$ok", "target_port": "left"}},
                    {"op": "edge.connect", "params": {"source_node_id": "$ok", "source_port": "right", "target_node_id": "$done", "target_port": "left", "label": "yes"}},
                    {"op": "node.set_style", "params": {"node_id": "$solve", "style": {"fill_color": "#ff8800"}}},
                ],
            },
        )
        ids = batch["ids"]
        self.assertEqual(batch["applied"], 10)
        self.assertEqual(corex.call("app.history", {"action": "status"})["undo_depth"], 1)

        mesh = corex.call("graph.get_node", {"node_id": ids["mesh"]})
        self.assertEqual(mesh["node"]["title"], "Mesh the part")
        # Flowchart shapes draw ``body``; the title must drive it (see the flowchart body trap).
        self.assertEqual(mesh["properties"].get("body"), "Mesh the part")
        done = corex.call("graph.get_node", {"node_id": ids["done"]})
        self.assertEqual(done["node"]["title"], "Report $100 budget")  # titles never get $ref substitution

        group = corex.call("group.wrap", {"node_ids": [ids["start"], ids["mesh"]], "title": "Pre-processing"})
        self.assertTrue(group["group_node_id"])
        comment = corex.call("comment.upsert", {"node_id": ids["solve"], "body": "Check contact settings"})
        self.assertTrue(comment["comment_id"])
        link = corex.call("link.upsert", {"node_id": ids["solve"], "kind": "url", "title": "Solver notes", "target": "https://example.com/notes"})
        self.assertTrue(link["link_id"])
        subnode = corex.call("subnode.create", {"node_ids": [ids["ok"], ids["done"]], "title": "Post-processing"})
        self.assertTrue(subnode["shell_node_id"])

        project_path = self.root / "e2e_flowchart.cxproj"
        saved = corex.call("project.save", {"path": str(project_path)})
        self.assertEqual(saved["status"], "saved", saved)
        self.assertTrue(project_path.is_file())

        corex.call("project.open", {"new": True, "discard_unsaved": True})
        self.assertEqual(corex.call("graph.get", {"scope": "all"})["nodes"], [])
        reopened = corex.call("project.open", {"path": str(project_path)})
        self.assertEqual(Path(reopened["project_path"]).resolve(), project_path.resolve())
        graph = corex.call("graph.get", {"scope": "all"})
        titles = {node["title"] for node in graph["nodes"]}
        self.assertTrue({"Mesh the part", "Solve", "Pre-processing", "Post-processing"} <= titles, titles)
        solve_after = corex.call("graph.find_nodes", {"title": "Solve"})["nodes"]
        self.assertEqual(len(solve_after), 1)
        solve_detail = corex.call("graph.get_node", {"node_id": solve_after[0]["node_id"]})
        self.assertEqual(solve_detail["visual_style"].get("fill_color"), "#ff8800")
        self.assertEqual(len(solve_detail["comments"]), 1)
        self.assertEqual(len(solve_detail["links"]), 1)

        corex.call("view.set_camera", {"frame": "all"})
        shot = corex.call("capture.screenshot", {"inline": False, "output_dir": str(self.root / "shots")})
        self.assertEqual(shot["fidelity"], "offscreen_layout")
        self.assertTrue(shot["images"])
        image_path = Path(shot["images"][0]["path"])
        self.assertTrue(image_path.is_file())
        self.assertGreater(image_path.stat().st_size, 2000)
        self.assertGreater(_distinct_sampled_colors(image_path), 8, "screenshot looks blank")


if __name__ == "__main__":
    unittest.main()
