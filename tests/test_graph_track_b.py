from __future__ import annotations

import importlib
import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from tests.graph_track_b.qml_preference_bindings import (
    GraphCanvasQmlPreferenceBindingTests,
    build_graph_canvas_qml_preference_binding_subprocess_suite,
)
from tests.graph_track_b.runtime_history import RuntimeGraphHistoryTrackBTests
from tests.graph_track_b.scene_and_model import GraphModelTrackBTests, GraphSceneBridgeTrackBTests
from tests.graph_track_b.viewport import ViewportBridgeTrackBTests

_REPO_ROOT = Path(__file__).resolve().parents[1]


class TrackBPacketBoundaryTests(unittest.TestCase):
    def test_track_b_entrypoints_stay_thin_and_route_suites_through_packet_modules(self) -> None:
        qml_module = importlib.import_module("tests.graph_track_b.qml_preference_bindings")
        scene_module = importlib.import_module("tests.graph_track_b.scene_and_model")
        package_root = _REPO_ROOT / "tests" / "graph_track_b"

        self.assertLessEqual(
            len((package_root / "scene_and_model.py").read_text(encoding="utf-8").splitlines()),
            200,
        )
        for relative_path in (
            "qml_support.py",
            "theme_support.py",
            "qml_preference_rendering_suite.py",
            "qml_preference_performance_suite.py",
            "scene_model_graph_model_suite.py",
            "scene_model_graph_scene_suite.py",
        ):
            with self.subTest(path=relative_path):
                self.assertTrue((package_root / relative_path).is_file())

        self.assertEqual(
            {base.__module__ for base in qml_module.GraphCanvasQmlPreferenceBindingTests.__bases__},
            {
                "tests.graph_track_b.qml_preference_rendering_suite",
                "tests.graph_track_b.qml_preference_performance_suite",
            },
        )
        self.assertEqual(
            qml_module.build_graph_canvas_qml_preference_binding_subprocess_suite.__module__,
            "tests.graph_track_b.qml_preference_bindings",
        )
        self.assertEqual(
            scene_module.GraphModelTrackBTests.__module__,
            "tests.graph_track_b.scene_model_graph_model_suite",
        )
        self.assertEqual(
            scene_module.GraphSceneBridgeTrackBTests.__module__,
            "tests.graph_track_b.scene_model_graph_scene_suite",
        )
        self.assertEqual(
            scene_module._GraphCanvasPreferenceBridge.__module__,
            "tests.graph_track_b.qml_support",
        )


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TrackBPacketBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(GraphModelTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(GraphSceneBridgeTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(ViewportBridgeTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(RuntimeGraphHistoryTrackBTests))
    suite.addTests(build_graph_canvas_qml_preference_binding_subprocess_suite(loader))
    return suite


if __name__ == "__main__":
    unittest.main()
