from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_VERIFICATION_PATH = REPO_ROOT / "scripts" / "run_verification.py"
VERIFICATION_MANIFEST_PATH = REPO_ROOT / "scripts" / "verification_manifest.py"
CONFTEST_PATH = REPO_ROOT / "tests" / "conftest.py"
SHELL_ISOLATION_RUNTIME_PATH = REPO_ROOT / "tests" / "shell_isolation_runtime.py"


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RunVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_module("verification_manifest_under_test", VERIFICATION_MANIFEST_PATH)
        cls.runner = load_module("run_verification_under_test", RUN_VERIFICATION_PATH)
        cls.packet_conftest = load_module("packet_conftest_under_test", CONFTEST_PATH)
        cls.shell_runtime = load_module(
            "shell_isolation_runtime_under_test",
            SHELL_ISOLATION_RUNTIME_PATH,
        )

    def assert_pytest_phase_command(
        self,
        command,
        *,
        phase_spec,
        worker_count: int | None,
        use_xdist: bool,
    ) -> None:
        expected = [
            "./venv/Scripts/python.exe",
            "-m",
            "pytest",
        ]
        if use_xdist:
            expected.extend(["-n", str(worker_count), "--dist", "load"])
        expected.extend(["-m", phase_spec.marker_expression])
        expected.extend(self.manifest.worktree_pytest_ignore_args())
        expected.extend(self.manifest.non_shell_pytest_ignore_args())
        self.assertEqual(phase_spec.phase, command.phase)
        self.assertEqual(tuple(expected), command.display_argv)

    def assert_shell_isolation_command(
        self,
        command,
        *,
        worker_count: int | None,
        use_xdist: bool,
    ) -> None:
        expected = [
            "./venv/Scripts/python.exe",
            *self.manifest.shell_isolation_phase_pytest_args(
                worker_count if use_xdist else None
            ),
        ]
        self.assertEqual(self.manifest.SHELL_ISOLATION_SPEC.phase, command.phase)
        self.assertEqual(tuple(expected), command.display_argv)

    def test_full_mode_enables_xdist_for_fast_gui_and_shell_when_available(self) -> None:
        with (
            patch.object(
                self.runner,
                "resolve_python",
                return_value=("./venv/Scripts/python.exe", "./venv/Scripts/python.exe"),
            ),
            patch.object(self.runner, "pytest_xdist_available", return_value=True),
            patch.object(self.runner, "resolve_max_parallel_workers", return_value=12),
        ):
            commands = self.runner.build_commands("full")

        expected_phase_order: list[str] = []
        for phase_key in self.manifest.RUN_VERIFICATION_MODE_SEQUENCE["full"]:
            if phase_key == self.manifest.SHELL_ISOLATION_PHASE_KEY:
                expected_phase_order.append(self.manifest.SHELL_ISOLATION_SPEC.phase)
            else:
                expected_phase_order.append(self.manifest.PYTEST_PHASE_SPECS_BY_MODE[phase_key].phase)

        self.assertEqual(
            expected_phase_order,
            [command.phase for command in commands],
        )

        fast_command, gui_command, slow_command, shell_command = commands
        self.assert_pytest_phase_command(
            fast_command,
            phase_spec=self.manifest.PYTEST_PHASE_SPECS_BY_MODE["fast"],
            worker_count=12,
            use_xdist=True,
        )
        self.assert_pytest_phase_command(
            gui_command,
            phase_spec=self.manifest.PYTEST_PHASE_SPECS_BY_MODE["gui"],
            worker_count=self.manifest.MAX_GUI_PARALLEL_WORKERS,
            use_xdist=True,
        )
        self.assert_pytest_phase_command(
            slow_command,
            phase_spec=self.manifest.PYTEST_PHASE_SPECS_BY_MODE["slow"],
            worker_count=None,
            use_xdist=False,
        )
        self.assert_shell_isolation_command(shell_command, worker_count=12, use_xdist=True)

    def test_gui_parallel_worker_count_is_capped_for_qml_heavy_phase(self) -> None:
        self.assertEqual(1, self.runner.resolve_gui_parallel_workers(1))
        self.assertEqual(4, self.runner.resolve_gui_parallel_workers(4))
        self.assertEqual(self.manifest.MAX_GUI_PARALLEL_WORKERS, self.runner.resolve_gui_parallel_workers(6))
        self.assertEqual(self.manifest.MAX_GUI_PARALLEL_WORKERS, self.runner.resolve_gui_parallel_workers(12))

    def test_gui_mode_falls_back_to_serial_with_notice_when_xdist_is_unavailable(self) -> None:
        with (
            patch.object(
                self.runner,
                "resolve_python",
                return_value=("./venv/Scripts/python.exe", "./venv/Scripts/python.exe"),
            ),
            patch.object(self.runner, "pytest_xdist_available", return_value=False),
            patch.object(self.runner, "resolve_max_parallel_workers", return_value=12),
        ):
            commands = self.runner.build_commands("gui")

        self.assertEqual(1, len(commands))
        gui_command = commands[0]
        self.assert_pytest_phase_command(
            gui_command,
            phase_spec=self.manifest.PYTEST_PHASE_SPECS_BY_MODE["gui"],
            worker_count=None,
            use_xdist=False,
        )
        self.assertEqual(
            "pytest-xdist is unavailable; falling back to serial pytest for gui mode.",
            gui_command.notice,
        )

    def test_resolve_python_falls_back_to_current_venv_when_worktree_helper_is_inaccessible(self) -> None:
        with (
            patch.object(self.runner, "local_venv_python_exists", return_value=False),
            patch.object(self.runner, "current_python_matches_project_venv", return_value=True),
            patch.object(self.runner.sys, "executable", "C:/real/project/venv/Scripts/python.exe"),
        ):
            python_exec, python_display = self.runner.resolve_python()

        self.assertEqual("C:/real/project/venv/Scripts/python.exe", python_exec)
        self.assertEqual("./venv/Scripts/python.exe", python_display)

    def test_shell_isolation_runtime_uses_manifest_owned_pytest_child_args(self) -> None:
        nodeid = "tests/main_window_shell/passive_image_nodes.py::MainWindowShellPassiveImageNodesTests"
        expected = (
            sys.executable,
            *self.manifest.shell_isolation_target_pytest_args(nodeid),
        )
        self.assertEqual(expected, self.shell_runtime.build_pytest_nodeid_command(nodeid))

    def test_shell_isolation_runtime_uses_manifest_owned_target_catalogs(self) -> None:
        self.assertEqual(
            self.manifest.shell_isolation_target_catalog_module_names(),
            ("tests.shell_isolation_main_window_targets", "tests.shell_isolation_controller_targets"),
        )

    def test_pytest_marker_catalogs_follow_verification_manifest(self) -> None:
        self.assertEqual(frozenset(self.manifest.GUI_TEST_PATHS), self.packet_conftest._GUI_TEST_PATHS)
        self.assertEqual(
            frozenset(self.manifest.SLOW_TEST_PATHS),
            self.packet_conftest._SLOW_TEST_PATHS,
        )


if __name__ == "__main__":
    unittest.main()
