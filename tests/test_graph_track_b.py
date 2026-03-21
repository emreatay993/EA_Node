from __future__ import annotations

import unittest

from tests.graph_track_b.qml_preference_bindings import (
    GraphCanvasQmlPreferenceBindingTests,
    build_graph_canvas_qml_preference_binding_subprocess_suite,
)
from tests.graph_track_b.runtime_history import RuntimeGraphHistoryTrackBTests
from tests.graph_track_b.scene_and_model import GraphModelTrackBTests, GraphSceneBridgeTrackBTests
from tests.graph_track_b.viewport import ViewportBridgeTrackBTests


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(GraphModelTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(GraphSceneBridgeTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(ViewportBridgeTrackBTests))
    suite.addTests(loader.loadTestsFromTestCase(RuntimeGraphHistoryTrackBTests))
    suite.addTests(build_graph_canvas_qml_preference_binding_subprocess_suite(loader))
    return suite


if __name__ == "__main__":
    unittest.main()
