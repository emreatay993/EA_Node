from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from ea_node_editor import pytest_defaults


REPO_ROOT = Path(__file__).resolve().parents[1]


class PytestDefaultsTests(unittest.TestCase):
    def test_empty_invocation_uses_fast_slice_parallel_defaults(self) -> None:
        decision = pytest_defaults.decide_default_parallelism(
            args=(),
            rootdir=REPO_ROOT,
            markexpr="",
        )

        self.assertTrue(decision.enable_xdist)
        self.assertEqual("not gui and not slow", decision.markexpr)
        self.assertEqual(
            (
                "tests/test_main_window_shell.py",
                "tests/test_script_editor_dock.py",
                "tests/test_shell_run_controller.py",
                "tests/test_shell_project_session_controller.py",
                "tests/test_shell_isolation_phase.py",
            ),
            decision.ignored_paths,
        )

    def test_tests_directory_invocation_uses_fast_slice_parallel_defaults(self) -> None:
        decision = pytest_defaults.decide_default_parallelism(
            args=("tests",),
            rootdir=REPO_ROOT,
            markexpr="",
        )

        self.assertTrue(decision.enable_xdist)
        self.assertEqual("not gui and not slow", decision.markexpr)

    def test_focused_non_gui_file_enables_parallelism_without_rewriting_markexpr(self) -> None:
        decision = pytest_defaults.decide_default_parallelism(
            args=("tests/test_icon_registry.py",),
            rootdir=REPO_ROOT,
            markexpr="",
        )

        self.assertTrue(decision.enable_xdist)
        self.assertIsNone(decision.markexpr)
        self.assertEqual((), decision.ignored_paths)

    def test_nodeid_target_is_normalized_to_its_test_file(self) -> None:
        decision = pytest_defaults.decide_default_parallelism(
            args=("tests/test_icon_registry.py::test_icon_map_contains_expected_entries",),
            rootdir=REPO_ROOT,
            markexpr="",
        )

        self.assertTrue(decision.enable_xdist)
        self.assertEqual(
            ("tests/test_icon_registry.py",),
            pytest_defaults.selected_test_paths(
                ("tests/test_icon_registry.py::test_icon_map_contains_expected_entries",),
                REPO_ROOT,
            ),
        )

    def test_gui_targets_stay_off_the_default_parallel_path(self) -> None:
        decision = pytest_defaults.decide_default_parallelism(
            args=("tests/test_viewer_surface_host.py",),
            rootdir=REPO_ROOT,
            markexpr="",
        )

        self.assertFalse(decision.enable_xdist)

    def test_slow_targets_stay_off_the_default_parallel_path(self) -> None:
        decision = pytest_defaults.decide_default_parallelism(
            args=("tests/test_track_h_perf_harness.py",),
            rootdir=REPO_ROOT,
            markexpr="",
        )

        self.assertFalse(decision.enable_xdist)

    def test_shell_targets_stay_off_the_default_parallel_path(self) -> None:
        decision = pytest_defaults.decide_default_parallelism(
            args=("tests/test_shell_isolation_phase.py",),
            rootdir=REPO_ROOT,
            markexpr="",
        )

        self.assertFalse(decision.enable_xdist)

    def test_explicit_marker_expression_disables_automatic_defaults(self) -> None:
        decision = pytest_defaults.decide_default_parallelism(
            args=(),
            rootdir=REPO_ROOT,
            markexpr="gui",
        )

        self.assertFalse(decision.enable_xdist)

    def test_worker_count_prefers_physical_core_count(self) -> None:
        with patch("ea_node_editor.pytest_defaults.psutil.cpu_count", side_effect=[4, 8]):
            self.assertEqual(4, pytest_defaults.resolve_default_worker_count())

    def test_worker_count_falls_back_to_logical_when_physical_count_is_missing(self) -> None:
        with patch("ea_node_editor.pytest_defaults.psutil.cpu_count", side_effect=[None, 8]):
            self.assertEqual(8, pytest_defaults.resolve_default_worker_count())


if __name__ == "__main__":
    unittest.main()
