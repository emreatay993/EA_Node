from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from PyQt6.QtCore import QObject
from PyQt6.QtQuick import QQuickItem

from ea_node_editor.telemetry.frame_rate import FrameRateSampler
from ea_node_editor.ui.shell.runtime_clipboard import build_graph_fragment_payload, serialize_graph_fragment_payload
from tests.main_window_shell.base import MainWindowShellTestBase
from tests.main_window_shell.shell_basics_and_search import *  # noqa: F401,F403
from tests.main_window_shell.drop_connect_and_workflow_io import *  # noqa: F401,F403
from tests.main_window_shell.edit_clipboard_history import *  # noqa: F401,F403
from tests.main_window_shell.passive_style_context_menus import *  # noqa: F401,F403
from tests.main_window_shell.passive_property_editors import *  # noqa: F401,F403
from tests.main_window_shell.passive_image_nodes import *  # noqa: F401,F403
from tests.main_window_shell.passive_pdf_nodes import *  # noqa: F401,F403
from tests.main_window_shell.view_library_inspector import *  # noqa: F401,F403

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_TEST_RUNNER = (
    "import sys, unittest; "
    "target = sys.argv[1]; "
    "suite = unittest.defaultTestLoader.loadTestsFromName(target); "
    "result = unittest.TextTestRunner(verbosity=2).run(suite); "
    "sys.exit(0 if result.wasSuccessful() else 1)"
)


def _named_child_items(root: QObject, object_name: str) -> list[QQuickItem]:
    matches: list[QQuickItem] = []

    def _visit(item: QObject) -> None:
        if not isinstance(item, QQuickItem):
            return
        if item.objectName() == object_name:
            matches.append(item)
        for child in item.childItems():
            _visit(child)

    _visit(root)
    return matches


class FrameRateSamplerTests(unittest.TestCase):
    def test_snapshot_is_zero_without_enough_frames(self) -> None:
        sampler = FrameRateSampler(window_seconds=1.0)

        self.assertEqual(sampler.snapshot(timestamp=1.0).fps, 0.0)

        sampler.record_frame(timestamp=1.25)
        sample = sampler.snapshot(timestamp=1.25)
        self.assertEqual(sample.fps, 0.0)
        self.assertEqual(sample.sample_count, 1)

    def test_snapshot_reports_average_fps_within_recent_window(self) -> None:
        sampler = FrameRateSampler(window_seconds=1.0)
        for timestamp in (10.0, 10.2, 10.4, 10.6):
            sampler.record_frame(timestamp=timestamp)

        sample = sampler.snapshot(timestamp=10.6)

        self.assertAlmostEqual(sample.fps, 5.0, places=4)
        self.assertEqual(sample.sample_count, 4)

    def test_snapshot_drops_stale_frames_and_returns_idle_zero(self) -> None:
        sampler = FrameRateSampler(window_seconds=0.5)
        for timestamp in (20.0, 20.1, 20.2):
            sampler.record_frame(timestamp=timestamp)

        self.assertGreater(sampler.snapshot(timestamp=20.2).fps, 0.0)
        self.assertEqual(sampler.snapshot(timestamp=20.8).fps, 0.0)


class MainWindowShellTelemetryTests(MainWindowShellTestBase):
    def test_update_system_metrics_can_render_explicit_fps_value(self) -> None:
        self.window.update_system_metrics(37.0, 4.3, 16.0, fps=58.0)
        self.app.processEvents()

        self.assertEqual(self.window.status_metrics.text(), "FPS:58 CPU:37% RAM:4.3/16.0 GB")


class MainWindowShellGraphCanvasHostTests(MainWindowShellTestBase):
    def test_graph_canvas_keeps_graph_node_card_discoverability_after_host_refactor(self) -> None:
        graph_canvas = self._graph_canvas_item()
        self.window.scene.add_node_from_type("core.logger", 180.0, 120.0)
        self.app.processEvents()

        node_cards = _named_child_items(graph_canvas, "graphNodeCard")
        self.assertGreaterEqual(len(node_cards), 1)
        self.assertIsNotNone(node_cards[0].findChild(QObject, "graphNodeStandardSurface"))

    def test_plain_text_graph_fragment_payload_is_ignored_by_paste(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.scene.add_node_from_type("core.start", x=25.0, y=35.0)
        before_state = self._workspace_state()
        before_depth = self.window.runtime_history.undo_depth(workspace_id)
        clipboard = self.app.clipboard()

        valid_text_payload = serialize_graph_fragment_payload(
            build_graph_fragment_payload(
                nodes=[
                    {
                        "ref_id": "ref-start",
                        "type_id": "core.start",
                        "title": "Start",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {},
                        "visual_style": {},
                        "parent_node_id": None,
                    }
                ],
                edges=[],
            )
        )
        self.assertIsNotNone(valid_text_payload)
        clipboard.setText(str(valid_text_payload))

        pasted = self.window.request_paste_selected_nodes()
        self.assertFalse(pasted)
        self.assertEqual(self._workspace_state(), before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_depth)


class _SubprocessShellWindowTest(unittest.TestCase):
    def __init__(self, target: str) -> None:
        super().__init__(methodName="runTest")
        self._target = target

    def id(self) -> str:
        return self._target

    def __str__(self) -> str:
        return self._target

    def shortDescription(self) -> str:
        return self._target

    def runTest(self) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        result = subprocess.run(
            [sys.executable, "-c", _SHELL_TEST_RUNNER, self._target],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        output = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        self.fail(
            f"Subprocess shell test failed for {self._target} "
            f"(exit={result.returncode}).\n{output}"
        )


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(FrameRateSamplerTests))

    shell_classes: list[type[MainWindowShellTestBase]] = []
    for candidate in globals().values():
        if not isinstance(candidate, type):
            continue
        if not issubclass(candidate, MainWindowShellTestBase):
            continue
        if candidate is MainWindowShellTestBase:
            continue
        shell_classes.append(candidate)

    for case_type in sorted(shell_classes, key=lambda item: (item.__module__, item.__name__)):
        for test_name in loader.getTestCaseNames(case_type):
            target = f"{case_type.__module__}.{case_type.__qualname__}.{test_name}"
            suite.addTest(_SubprocessShellWindowTest(target))
    return suite


if __name__ == "__main__":
    import unittest

    unittest.main()
