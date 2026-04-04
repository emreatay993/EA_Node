from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import call
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

    def test_ensure_pytest_stack_ready_repairs_missing_direct_dependencies(self) -> None:
        with (
            patch.object(
                self.runner,
                "probe_pytest_startup",
                side_effect=[
                    (False, "No module named 'iniconfig'"),
                    (False, "No module named 'exceptiongroup'"),
                    (True, ""),
                ],
            ),
            patch.object(self.runner, "pytest_related_unmet_requirements", return_value=()),
            patch.object(self.runner, "install_python_packages", return_value=0) as install_mock,
            patch("builtins.print") as print_mock,
        ):
            repaired = self.runner.ensure_pytest_stack_ready("./venv/Scripts/python.exe")

        self.assertTrue(repaired)
        self.assertEqual(
            [
                call("./venv/Scripts/python.exe", "iniconfig"),
                call("./venv/Scripts/python.exe", "exceptiongroup"),
            ],
            install_mock.call_args_list,
        )
        self.assertEqual(2, print_mock.call_count)

    def test_ensure_pytest_stack_ready_raises_when_repairable_module_is_not_identified(self) -> None:
        with (
            patch.object(
                self.runner,
                "probe_pytest_startup",
                return_value=(False, "pytest startup exploded"),
            ),
            patch.object(self.runner, "pytest_related_unmet_requirements", return_value=()),
        ):
            with self.assertRaisesRegex(RuntimeError, "pytest is not startup-ready"):
                self.runner.ensure_pytest_stack_ready("./venv/Scripts/python.exe")

    def test_ensure_pytest_stack_ready_repairs_core_pip_check_gaps_before_startup(self) -> None:
        with (
            patch.object(
                self.runner,
                "probe_pytest_startup",
                return_value=(True, ""),
            ),
            patch.object(
                self.runner,
                "pytest_related_unmet_requirements",
                side_effect=[
                    ("colorama",),
                    (),
                ],
            ),
            patch.object(self.runner, "install_python_packages", return_value=0) as install_mock,
            patch("builtins.print") as print_mock,
        ):
            repaired = self.runner.ensure_pytest_stack_ready("./venv/Scripts/python.exe")

        self.assertTrue(repaired)
        install_mock.assert_called_once_with("./venv/Scripts/python.exe", "colorama")
        self.assertEqual(1, print_mock.call_count)

    def test_ensure_pytest_stack_ready_uses_pip_check_for_pytest_plugin_requirements(self) -> None:
        with (
            patch.object(
                self.runner,
                "probe_pytest_startup",
                side_effect=[
                    (False, "plugin import crashed"),
                    (True, ""),
                ],
            ),
            patch.object(
                self.runner,
                "pytest_related_unmet_requirements",
                side_effect=[
                    (),
                    ("execnet>=2.1", "coverage[toml]>=7.10.6"),
                    (),
                ],
            ),
            patch.object(self.runner, "install_python_packages", return_value=0) as install_mock,
            patch("builtins.print") as print_mock,
        ):
            repaired = self.runner.ensure_pytest_stack_ready("./venv/Scripts/python.exe")

        self.assertTrue(repaired)
        install_mock.assert_called_once_with(
            "./venv/Scripts/python.exe",
            "execnet>=2.1",
            "coverage[toml]>=7.10.6",
        )
        self.assertEqual(1, print_mock.call_count)

    def test_main_repairs_pytest_stack_before_running_commands(self) -> None:
        command = self.runner.CommandSpec(
            phase="fast.pytest",
            argv=("python", "-m", "pytest"),
            display_argv=("./venv/Scripts/python.exe", "-m", "pytest"),
            env={},
        )
        with (
            patch.object(
                self.runner,
                "resolve_python",
                return_value=("./venv/Scripts/python.exe", "./venv/Scripts/python.exe"),
            ),
            patch.object(self.runner, "ensure_pytest_stack_ready", return_value=True) as ensure_mock,
            patch.object(self.runner, "build_commands", return_value=[command]),
            patch.object(self.runner, "run_command", return_value=0) as run_mock,
        ):
            return_code = self.runner.main(["--mode", "fast"])

        self.assertEqual(0, return_code)
        ensure_mock.assert_called_once_with("./venv/Scripts/python.exe")
        run_mock.assert_called_once_with(command)

    def test_main_skips_pytest_stack_repair_on_dry_run(self) -> None:
        command = self.runner.CommandSpec(
            phase="fast.pytest",
            argv=("python", "-m", "pytest"),
            display_argv=("./venv/Scripts/python.exe", "-m", "pytest"),
            env={},
        )
        with (
            patch.object(
                self.runner,
                "resolve_python",
                return_value=("./venv/Scripts/python.exe", "./venv/Scripts/python.exe"),
            ),
            patch.object(self.runner, "ensure_pytest_stack_ready") as ensure_mock,
            patch.object(self.runner, "build_commands", return_value=[command]),
            patch.object(self.runner, "run_command") as run_mock,
        ):
            return_code = self.runner.main(["--mode", "fast", "--dry-run"])

        self.assertEqual(0, return_code)
        ensure_mock.assert_not_called()
        run_mock.assert_not_called()

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
            tuple(spec.module_name for spec in self.manifest.SHELL_ISOLATION_CATALOG_SPECS),
        )

    def test_shell_isolation_target_catalog_specs_own_target_prefixes(self) -> None:
        self.assertEqual(
            ("main_window__", "script_editor__", "run_controller__", "project_session__"),
            self.manifest.shell_isolation_target_id_prefixes(),
        )

    def test_pytest_marker_catalogs_follow_verification_manifest(self) -> None:
        self.assertEqual(frozenset(self.manifest.GUI_TEST_PATHS), self.packet_conftest._GUI_TEST_PATHS)
        self.assertEqual(
            frozenset(self.manifest.SLOW_TEST_PATHS),
            self.packet_conftest._SLOW_TEST_PATHS,
        )

    def test_context_budget_guardrail_metadata_matches_packet_contract(self) -> None:
        self.assertEqual(
            "scripts/check_context_budgets.py",
            self.manifest.CHECK_CONTEXT_BUDGETS_SCRIPT,
        )
        self.assertEqual(
            "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
            self.manifest.CONTEXT_BUDGET_RULES_PATH,
        )
        self.assertEqual(
            "tests/test_context_budget_guardrails.py",
            self.manifest.CONTEXT_BUDGET_GUARDRAILS_TEST,
        )
        self.assertEqual(
            "./venv/Scripts/python.exe scripts/check_context_budgets.py",
            self.manifest.CONTEXT_BUDGET_CHECK_COMMAND,
        )
        self.assertEqual(
            (
                "./venv/Scripts/python.exe scripts/check_context_budgets.py",
                "./venv/Scripts/python.exe -m pytest tests/test_context_budget_guardrails.py "
                "tests/test_run_verification.py --ignore=venv -q",
            ),
            self.manifest.P07_CONTEXT_BUDGET_VERIFICATION_COMMANDS,
        )
        self.assertEqual(
            "./venv/Scripts/python.exe scripts/check_context_budgets.py",
            self.manifest.P07_CONTEXT_BUDGET_REVIEW_GATE_COMMAND,
        )
        self.assertEqual(
            (
                "scripts/check_context_budgets.py",
                "docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json",
                "tests/test_context_budget_guardrails.py",
            ),
            self.manifest.P07_CONTEXT_BUDGET_ARTIFACTS,
        )


if __name__ == "__main__":
    unittest.main()
