from __future__ import annotations

import sys

import pytest

from tests.shell_isolation_runtime import format_child_output
from tests.shell_isolation_runtime import list_target_ids
from tests.shell_isolation_runtime import resolve_target
from tests.shell_isolation_runtime import run_shell_isolation_target


def _target_params():
    target_ids = list_target_ids()
    if target_ids:
        return [pytest.param(target_id, id=target_id) for target_id in target_ids]
    return [
        pytest.param(
            "",
            id="no-targets",
            marks=pytest.mark.skip(reason="Shell isolation target catalogs are empty in P01."),
        )
    ]


def test_shell_isolation_target_catalog_uses_pytest_nodeids_for_bridge_local_pack() -> None:
    target = resolve_target("main_window__bridge_local_pack")

    assert target.command[0] == sys.executable
    assert target.command[1:3] == ("-m", "pytest")
    assert "--ignore=venv" in target.command
    assert "tests/test_main_window_shell.py::ShellLibraryBridgeTests" in target.command
    assert "tests/test_main_window_shell.py::MainWindowShellTelemetryTests" in target.command


def test_shell_isolation_pytest_targets_ignore_worktree_venv() -> None:
    target = resolve_target("main_window__graph_canvas_host_subprocess")

    assert target.command == (
        sys.executable,
        "-m",
        "pytest",
        "--ignore=venv",
        "tests/test_main_window_shell.py::_MainWindowShellGraphCanvasHostDirectTests",
        "-q",
    )


@pytest.mark.parametrize(
    "target_id",
    _target_params(),
)
def test_shell_isolation_target(target_id: str) -> None:
    target = resolve_target(target_id)
    completed = run_shell_isolation_target(target)
    if completed.returncode == 0:
        return
    pytest.fail(
        "Shell isolation child process failed "
        f"for {target_id} (exit={completed.returncode}).\n"
        f"Command: {' '.join(target.command)}\n"
        f"{format_child_output(completed)}",
        pytrace=False,
    )
