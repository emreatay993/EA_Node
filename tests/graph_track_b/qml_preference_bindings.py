from __future__ import annotations

import unittest

from tests.graph_track_b import (
    qml_preference_performance_suite as _performance_suite,
    qml_preference_rendering_suite as _rendering_suite,
)
from tests.graph_track_b.qml_support import build_graph_canvas_qml_preference_subprocess_suite


class GraphCanvasQmlPreferenceBindingTests(
    _rendering_suite.GraphCanvasQmlPreferenceRenderingTests,
    _performance_suite.GraphCanvasQmlPreferencePerformanceTests,
):
    """Stable regression entrypoint for packetized Track-B QML preference coverage."""

    __test__ = True


def build_graph_canvas_qml_preference_binding_subprocess_suite(
    loader: unittest.TestLoader,
) -> unittest.TestSuite:
    return build_graph_canvas_qml_preference_subprocess_suite(
        loader,
        GraphCanvasQmlPreferenceBindingTests,
    )


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    return build_graph_canvas_qml_preference_binding_subprocess_suite(loader)


__all__ = [
    "GraphCanvasQmlPreferenceBindingTests",
    "build_graph_canvas_qml_preference_binding_subprocess_suite",
]


if __name__ == "__main__":
    unittest.main()
