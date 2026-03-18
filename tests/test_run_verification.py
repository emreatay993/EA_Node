from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_VERIFICATION_PATH = REPO_ROOT / "scripts" / "run_verification.py"


def load_run_verification_module():
    spec = importlib.util.spec_from_file_location("run_verification", RUN_VERIFICATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RunVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = load_run_verification_module()

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

        self.assertEqual(
            ["fast.pytest", "gui.pytest", "slow.pytest", "full.shell_isolation.pytest"],
            [command.phase for command in commands],
        )

        fast_command, gui_command, slow_command, shell_command = commands

        self.assertEqual(
            (
                "./venv/Scripts/python.exe",
                "-m",
                "pytest",
                "-n",
                "12",
                "--dist",
                "load",
                "-m",
                "not gui and not slow",
                "--ignore=tests/test_main_window_shell.py",
                "--ignore=tests/test_script_editor_dock.py",
                "--ignore=tests/test_shell_run_controller.py",
                "--ignore=tests/test_shell_project_session_controller.py",
                "--ignore=tests/test_shell_isolation_phase.py",
            ),
            fast_command.display_argv,
        )
        self.assertEqual(
            (
                "./venv/Scripts/python.exe",
                "-m",
                "pytest",
                "-n",
                "6",
                "--dist",
                "load",
                "-m",
                "gui and not slow",
                "--ignore=tests/test_main_window_shell.py",
                "--ignore=tests/test_script_editor_dock.py",
                "--ignore=tests/test_shell_run_controller.py",
                "--ignore=tests/test_shell_project_session_controller.py",
                "--ignore=tests/test_shell_isolation_phase.py",
            ),
            gui_command.display_argv,
        )
        self.assertNotIn("-n", slow_command.display_argv)
        self.assertEqual(
            (
                "./venv/Scripts/python.exe",
                "-m",
                "pytest",
                "tests/test_shell_isolation_phase.py",
                "-q",
                "-n",
                "12",
                "--dist",
                "load",
            ),
            shell_command.display_argv,
        )

    def test_gui_parallel_worker_count_is_capped_for_qml_heavy_phase(self) -> None:
        self.assertEqual(1, self.runner.resolve_gui_parallel_workers(1))
        self.assertEqual(4, self.runner.resolve_gui_parallel_workers(4))
        self.assertEqual(6, self.runner.resolve_gui_parallel_workers(6))
        self.assertEqual(6, self.runner.resolve_gui_parallel_workers(12))

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
        self.assertEqual("gui.pytest", gui_command.phase)
        self.assertNotIn("-n", gui_command.display_argv)
        self.assertEqual(
            "pytest-xdist is unavailable; falling back to serial pytest for gui mode.",
            gui_command.notice,
        )


if __name__ == "__main__":
    unittest.main()
